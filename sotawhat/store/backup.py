# sotawhat/store/backup.py
"""Backup of the SQLite store (P6, SDD G7, D12, D16).

- `backup` copies data/insight.db with the sqlite3 backup API (consistent even while the web interface or the
  vote listener have it open), checks the copy (`PRAGMA integrity_check`) and keeps the newest `keep` copies.
- `restore` checks a copy, saves the current database next to it and copies the backup over it. Stop the
  interface and the listener first (`Stop-ScheduledTask sotawhat-web, sotawhat-feedback`).
The Neo4j mirror needs no dump: `sotawhat graph sync --rebuild` rebuilds it from SQLite; the JSON/CSV export
(`sotawhat graph export`) is the copy without lock-in."""
import re
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

_NAME = re.compile(r"^insight-(\d{8})-(\d{4})\.db$")


class BackupError(Exception):
    pass


def _stamp(now) -> str:
    return (now or datetime.now(timezone.utc)).strftime("%Y%m%d-%H%M")


def _check(path) -> None:
    try:   # closing(): `with sqlite3.connect()` only commits, and an open file cannot be deleted on Windows
        with closing(sqlite3.connect(f"file:{Path(path).as_posix()}?mode=ro", uri=True)) as conn:
            result = conn.execute("PRAGMA integrity_check").fetchone()[0]
    except sqlite3.DatabaseError as exc:
        raise BackupError(f"{Path(path).name}: não é um banco SQLite válido ({exc})") from None
    if result != "ok":
        raise BackupError(f"{Path(path).name}: integridade falhou ({result})")


def _copy(source, target, standalone=True) -> None:
    src = sqlite3.connect(f"file:{Path(source).as_posix()}?mode=ro", uri=True)
    dst = sqlite3.connect(str(target))
    try:
        src.backup(dst)
        if standalone:      # one self-contained file: the copy must not depend on -wal/-shm companions
            dst.execute("PRAGMA journal_mode=DELETE")
    finally:
        dst.close()
        src.close()


def _remove(path) -> None:
    for extra in ("", "-wal", "-shm", "-journal"):
        Path(f"{path}{extra}").unlink(missing_ok=True)


def backup(db_path, out_dir, keep=8, now=None) -> Path:
    """-> the new copy, data/backups/insight-AAAAMMDD-HHMM.db (UTC)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"insight-{_stamp(now)}.db"
    _copy(db_path, target)
    _check(target)
    copies = sorted(p for p in out_dir.glob("insight-*.db") if _NAME.match(p.name))
    for old in copies[:-keep] if keep > 0 else []:
        _remove(old)
    return target


def last_backup(out_dir):
    """-> (path, when) of the newest copy, or None."""
    copies = sorted(p for p in Path(out_dir).glob("insight-*.db") if _NAME.match(p.name)) if Path(out_dir).exists() else []
    if not copies:
        return None
    day, time = _NAME.match(copies[-1].name).groups()
    return copies[-1], datetime.strptime(day + time, "%Y%m%d%H%M").replace(tzinfo=timezone.utc)


def restore(backup_path, db_path, now=None) -> Path:
    """Checks the copy, keeps the current database as insight.db.antes-de-restaurar-<stamp>, then restores.
    -> the path of the saved current database."""
    _check(backup_path)
    db_path = Path(db_path)
    previous = db_path.with_name(f"{db_path.name}.antes-de-restaurar-{_stamp(now)}")
    if db_path.exists():
        _copy(db_path, previous)
    _copy(backup_path, db_path, standalone=False)    # the store turns WAL back on when it opens
    _check(db_path)
    return previous


def main_backup(ns) -> int:
    import sys

    from sotawhat.config import load_settings

    settings = load_settings()
    if ns.restore:
        if not ns.yes:
            print(f"restaurar substitui {settings.db_path} por {ns.restore} (o banco atual fica salvo ao lado).\n"
                  "Pare antes a interface e o ouvinte: Stop-ScheduledTask sotawhat-web; Stop-ScheduledTask "
                  "sotawhat-feedback. Depois rode de novo com --yes.")
            return 0
        try:
            previous = restore(ns.restore, settings.db_path)
        except (BackupError, OSError, sqlite3.Error) as exc:
            print(f"[backup] {exc}", file=sys.stderr)
            return 1
        print(f"[backup] restaurado de {ns.restore}; o banco anterior ficou em {previous}")
        return 0
    try:
        path = backup(settings.db_path, settings.sotawhat_data_dir / "backups", keep=ns.keep)
    except (BackupError, OSError, sqlite3.Error) as exc:
        print(f"[backup] {exc}", file=sys.stderr)
        return 1
    print(f"[backup] {path} ({path.stat().st_size / 1024 / 1024:.1f} MB, integridade ok; guardando os {ns.keep} mais novos)")
    return 0

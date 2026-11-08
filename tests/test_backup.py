# tests/test_backup.py
"""Backup of the SQLite store (P6, SDD G7): consistent copy, integrity check, rotation, restore."""
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone

import pytest

from sotawhat.items import Item
from sotawhat.store.backup import BackupError, backup, last_backup, restore
from sotawhat.store.db import Store

NOW = datetime(2026, 11, 8, 20, 30, tzinfo=timezone.utc)


def _db(tmp_path, n=3):
    path = tmp_path / "insight.db"
    with Store(path) as st:
        run = st.start_run("daily")
        st.upsert_items([Item(id=f"pmid:{i}", kind="paper", source="pubmed", source_id=str(i), title=f"T{i}", url="u")
                         for i in range(n)], run)
    return path


def test_backup_is_a_consistent_copy_and_old_ones_rotate(tmp_path):
    db = _db(tmp_path)
    out = tmp_path / "backups"
    made = [backup(db, out, keep=2, now=NOW + timedelta(days=d)) for d in range(3)]
    assert [p.name for p in made] == ["insight-20261108-2030.db", "insight-20261109-2030.db", "insight-20261110-2030.db"]
    assert sorted(p.name for p in out.glob("insight-*.db")) == [made[1].name, made[2].name]   # the oldest went away
    with closing(sqlite3.connect(made[2])) as conn:
        assert conn.execute("SELECT COUNT(*) FROM items").fetchone()[0] == 3
    assert last_backup(out) == (made[2], datetime(2026, 11, 10, 20, 30, tzinfo=timezone.utc))
    assert last_backup(tmp_path / "none") is None


def test_restore_checks_integrity_and_keeps_the_current_database(tmp_path):
    db = _db(tmp_path)
    saved = backup(db, tmp_path / "backups", now=NOW)
    with Store(db) as st:                                     # changes after the backup
        st.conn.execute("DELETE FROM items")
        st.conn.commit()
    previous = restore(saved, db, now=NOW + timedelta(hours=1))
    assert previous.name == "insight.db.antes-de-restaurar-20261108-2130"
    with closing(sqlite3.connect(db)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM items").fetchone()[0] == 3
    with closing(sqlite3.connect(previous)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM items").fetchone()[0] == 0
    broken = tmp_path / "broken.db"
    broken.write_bytes(b"not a database" * 100)
    with pytest.raises(BackupError):
        restore(broken, db)


def test_check_backup_and_cli(tmp_path):
    from sotawhat.cli import parse_args
    from sotawhat.doctor import check_backup

    assert check_backup(tmp_path / "backups").status == "warn"
    backup(_db(tmp_path), tmp_path / "backups", now=NOW)
    assert check_backup(tmp_path / "backups", now=NOW + timedelta(days=2)).status == "ok"
    assert check_backup(tmp_path / "backups", now=NOW + timedelta(days=9)).status == "warn"
    ns = parse_args(["backup", "--restore", "x.db"])
    assert (ns.command, ns.restore, ns.yes, ns.keep) == ("backup", "x.db", False, 8)


def test_the_copy_is_one_file(tmp_path):
    db = _db(tmp_path)
    made = backup(db, tmp_path / "backups", now=NOW)
    assert sorted(p.name for p in (tmp_path / "backups").iterdir()) == [made.name]
    with closing(sqlite3.connect(made)) as conn:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "delete"

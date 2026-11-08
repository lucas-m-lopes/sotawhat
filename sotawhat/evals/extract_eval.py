# sotawhat/evals/extract_eval.py
"""Precision of the entity and relation extraction (P6, SDD G3, §12 "Eval · extração").

`sotawhat eval extract draft` samples approved items already extracted and writes one Markdown file in
tests/evals/extract/: every entity and relation of an item is a checked box. You read the item and uncheck what
is wrong (`- [ ]`); a wrong type counts as wrong. `sotawhat eval extract import` counts the boxes and writes the
precision per kind and per entity type to a JSON file that the goals report reads."""
import json
import random
import re
from collections import Counter
from pathlib import Path

from sotawhat.graph.query import RELATION_LABELS, TYPE_LABELS
from sotawhat.store.db import APPROVED

FOLDER = Path("tests/evals/extract")
_ITEM = re.compile(r"^## \d+\. `([^`]+)`", re.M)
_BOX = re.compile(r"^- \[( |x|X)\] (E|R) · ([^·]+?) · ", re.M)


def sample(store, n=40, seed=13) -> list:
    rows = store.conn.execute(
        "SELECT i.id, i.title, t.summary_pt FROM items i JOIN extractions x ON x.item_id = i.id AND x.status = 'ok' "
        f"JOIN triage t ON t.item_id = i.id WHERE t.decision IN ({','.join('?' * len(APPROVED))}) ORDER BY i.id",
        list(APPROVED)).fetchall()
    rows = [r for r in rows if store.conn.execute("SELECT 1 FROM entity_mentions WHERE item_id = ? AND role != 'tag' "
                                                  "LIMIT 1", (r["id"],)).fetchone()]
    return random.Random(seed).sample(rows, min(n, len(rows)))


def item_block(store, number, row) -> str:
    entities = store.conn.execute(
        "SELECT e.type, e.name, m.role FROM entity_mentions m JOIN entities e ON e.id = m.entity_id "
        "WHERE m.item_id = ? AND m.role != 'tag' ORDER BY m.role, e.type, e.name", (row["id"],)).fetchall()
    relations = store.conn.execute(
        "SELECT s.name, r.predicate, o.name FROM entity_relations r JOIN entities s ON s.id = r.subject_id "
        "JOIN entities o ON o.id = r.object_id WHERE r.item_id = ? AND r.predicate != 'in_category' ORDER BY 1, 2, 3",
        (row["id"],)).fetchall()
    lines = [f"## {number}. `{row['id']}` {row['title']}", "", f"> {(row['summary_pt'] or '').strip()}", ""]
    lines += [f"- [x] E · {e['type']} · {e['name']} ({TYPE_LABELS.get(e['type'], e['type'])}, {e['role']})" for e in entities]
    lines += [f"- [x] R · {r[1]} · {r[0]} —{RELATION_LABELS.get(r[1], r[1])}→ {r[2]}" for r in relations]
    return "\n".join(lines) + "\n"


def write_draft(store, folder=FOLDER, name="extract_v1", n=40, seed=13, force=False) -> Path:
    folder = Path(folder)
    path = folder / f"{name}.md"
    if path.exists() and not force:
        raise FileExistsError(f"{path} já existe (use --force para sobrescrever; suas marcações seriam perdidas)")
    folder.mkdir(parents=True, exist_ok=True)
    rows = sample(store, n, seed)
    head = (f"# Avaliação da extração · {name} · {len(rows)} itens\n\n"
            "Leia cada item e desmarque (`- [ ]`) toda entidade (E) ou relação (R) errada: nome, tipo ou direção "
            "errados contam como erro. Não apague linhas. Depois rode `sotawhat eval extract import`.\n\n")
    path.write_text(head + "\n".join(item_block(store, n + 1, row) for n, row in enumerate(rows)), encoding="utf-8")
    return path


def score(text) -> dict:
    """-> {"items", "entities": {"right", "total", "precision"}, "relations": {...}, "by_type": {type: [...]}}."""
    counts = {"E": Counter(), "R": Counter()}
    by_type = {}
    for mark, kind, what in _BOX.findall(text):
        right = mark.lower() == "x"
        counts[kind]["total"] += 1
        counts[kind]["right"] += right
        if kind == "E":
            right_total = by_type.setdefault(what.strip(), [0, 0])
            right_total[0] += right
            right_total[1] += 1

    def block(c):
        return {"right": c["right"], "total": c["total"],
                "precision": round(c["right"] / c["total"], 3) if c["total"] else None}

    return {"items": len(_ITEM.findall(text)), "entities": block(counts["E"]), "relations": block(counts["R"]),
            "by_type": {t: {"right": r, "total": n, "precision": round(r / n, 3)} for t, (r, n) in sorted(by_type.items())}}


def import_labels(folder=FOLDER, name="extract_v1") -> dict:
    path = Path(folder) / f"{name}.md"
    result = score(path.read_text(encoding="utf-8"))
    (Path(folder) / f"{name}.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    return result

# sotawhat/evals/golden.py
"""Triage golden set (SDD §6.7, §12). `draft` samples items from the SQLite store into a Markdown file
you edit by hand; `import` reads your labels back into the JSONL that `sotawhat eval models` uses.
Labels: incluir (main) · radar · excluir (reject). The v1 set also holds notes sampled from the old
sotawhat 2.0 notes (origin "vault"); they stay as evaluation data only (SDD §9)."""
import json
import random
import re
from pathlib import Path

from sotawhat.items import Item

LABELS = {"incluir": "main", "radar": "radar", "excluir": "reject"}
FOLDER = Path("tests/evals/triage")
_ID = re.compile(r"^`id: (.+?)`\s*$", re.M)
_LABEL = re.compile(r"^r[óo]tulo:[ \t]*(.*)$", re.M | re.I)


def _entry(item, origin) -> dict:
    return {"id": item.id, "profile": item.profile or "", "source": item.source, "title": item.title,
            "url": item.url, "published_at": item.published_at, "authors": item.authors, "text": item.text,
            "origin": origin, "label": None, "note": ""}


def from_store(store) -> list:
    from sotawhat.items import from_row

    return [_entry(from_row(row), "store") for row in store.conn.execute("SELECT * FROM items")]


def sample(candidates, n=60, seed=13, min_chars=300) -> list:
    """Half per profile; inside a profile, round-robin over sources, so no source dominates."""
    rng = random.Random(seed)
    unique = {}
    for c in candidates:
        if c["title"] and len(c["text"] or "") >= min_chars and "removido" not in c["title"]:
            unique.setdefault(c["id"], c)
    by_profile = {}
    for c in unique.values():
        by_profile.setdefault(c["profile"], {}).setdefault(c["source"], []).append(c)
    picks = []
    quota = max(1, n // max(1, len(by_profile)))
    for profile in sorted(by_profile):
        pools = [sorted(v, key=lambda c: c["id"]) for _, v in sorted(by_profile[profile].items())]
        for pool in pools:
            rng.shuffle(pool)
        taken = 0
        while taken < quota and any(pools):
            for pool in pools:
                if pool and taken < quota:
                    picks.append(pool.pop())
                    taken += 1
    rng.shuffle(picks)
    return picks[:n]


def _excerpt(text, n=700) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= n else text[:n - 1] + "…"


def write_draft(entries, folder=FOLDER, name="golden_v1") -> tuple:
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    jsonl, md = folder / f"{name}.jsonl", folder / f"{name}.md"
    jsonl.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in entries), encoding="utf-8")
    lines = [f"# Golden set da triagem — {name} ({len(entries)} itens)", "",
             'Como rotular: depois de "Rótulo:", escreva uma destas palavras:',
             "- **incluir**: vai para uma das seções principais do digest: IA ∩ Saúde (aplicação "
             "médico-hospitalar plausível) ou Fronteira de IA (avanço técnico forte, mesmo sem ligação com saúde);",
             "- **radar**: IA de nicho ou menos importante (vira 1 linha no radar);",
             "- **excluir**: ruído (pesquisa clínica sem IA, notícia de IA sem substância, marketing, opinião).",
             "Nota opcional depois de \" — \". Ex.: `Rótulo: excluir — só epidemiologia`. "
             "Itens sem rótulo ficam fora da avaliação.",
             f"Quando terminar: `sotawhat eval golden import` (atualiza `{name}.jsonl`).", ""]
    for n, e in enumerate(entries, 1):
        lines += ["---", "", f"## {n} · {e['profile']} · {e['source']}", f"**{e['title']}**",
                  f"{e['url']} · {e['published_at'] or 's/ data'}", f"> {_excerpt(e['text'])}",
                  f"`id: {e['id']}`", "Rótulo: ", ""]
    md.write_text("\n".join(lines), encoding="utf-8")
    return md, jsonl


def import_labels(folder=FOLDER, name="golden_v1") -> dict:
    folder = Path(folder)
    jsonl, md = folder / f"{name}.jsonl", folder / f"{name}.md"
    entries = [json.loads(line) for line in jsonl.read_text(encoding="utf-8").splitlines() if line.strip()]
    by_id = {e["id"]: e for e in entries}
    report = {"labeled": 0, "unlabeled": 0, "invalid": []}
    for block in md.read_text(encoding="utf-8").split("\n## ")[1:]:
        found_id, found_label = _ID.search(block), _LABEL.search(block)
        if not found_id or found_id.group(1) not in by_id:
            continue
        entry = by_id[found_id.group(1)]
        raw = (found_label.group(1) if found_label else "").strip()
        word, _, note = raw.partition(" — ")
        word = word.strip().lower().rstrip(".")
        if not word:
            entry["label"], entry["note"] = None, ""
            report["unlabeled"] += 1
        elif word in LABELS:
            entry["label"], entry["note"] = LABELS[word], note.strip()
            report["labeled"] += 1
        else:
            report["invalid"].append(f"{found_id.group(1)}: '{raw}'")
    jsonl.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in entries), encoding="utf-8")
    return report


def load_golden(path) -> list:
    path = Path(path)
    if not path.exists():
        return []
    entries = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [e for e in entries if e.get("label") in LABELS.values()]


def as_item(entry) -> Item:
    return Item(id=entry["id"], kind="paper", source=entry["source"], source_id="", title=entry["title"],
                url=entry["url"], authors=list(entry.get("authors") or []),
                published_at=entry.get("published_at") or "", text=entry.get("text") or "",
                profile=entry.get("profile"))

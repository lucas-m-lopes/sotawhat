# sotawhat/obsidian.py
import json
import re
from pathlib import Path

from sotawhat.summarize import extract_line

_INVALID = re.compile(r'[:/\\?*"<>|]+')

def sanitize_title(title):
    cleaned = _INVALID.sub("-", title).strip()
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -")
    return cleaned[:100]

def _yaml_list(values):
    return "[" + ", ".join(json.dumps(v) for v in values) + "]"

def render_note(result, tags, keywords, added):
    all_tags = list(tags) + [f"source/{result.source}"]
    extract, _ = extract_line(result.abstract, (keywords[0] if keywords else "").lower(), 280)
    body = extract or result.abstract
    front = (
        "---\n"
        f'title: {json.dumps(result.title)}\n'
        f"authors: {_yaml_list(result.authors)}\n"
        f"date: {json.dumps(result.date)}\n"
        f"source: {result.source}\n"
        f"url: {json.dumps(result.url)}\n"
        f"keywords: {_yaml_list(keywords)}\n"
        f"tags: {_yaml_list(all_tags)}\n"
        f"added: {json.dumps(added)}\n"
        "---\n\n"
    )
    return f"{front}# {result.title}\n\n{body}\n\n[Source]({result.url})\n"

def _load_seen(vault_path):
    f = vault_path / ".sotawhat_seen.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    return {}

def _save_seen(vault_path, seen):
    (vault_path / ".sotawhat_seen.json").write_text(
        json.dumps(seen, ensure_ascii=False, indent=2), encoding="utf-8")

def write_notes(results, vault, profile_name, tags, keywords, added="unknown"):
    vault_path = Path(vault)
    vault_path.mkdir(parents=True, exist_ok=True)
    seen = _load_seen(vault_path)
    written = 0
    for r in results:
        if r.id in seen:
            continue
        folder = vault_path / profile_name / r.source.replace(":", "-")
        folder.mkdir(parents=True, exist_ok=True)
        fname = f"{(r.date or added)[:10]}-{sanitize_title(r.title) or r.id}.md"
        path = folder / fname
        path.write_text(render_note(r, tags, keywords, added), encoding="utf-8")
        seen[r.id] = str(path.relative_to(vault_path))
        written += 1
    _save_seen(vault_path, seen)
    return written

# sotawhat/backfill.py
from pathlib import Path

from sotawhat.obsidian import ensure_concept_notes
from sotawhat.textmatch import contains_term

_CONCEPT_MARKER = "**Conceitos:**"

def _matches(text, keyword):
    return contains_term(text, keyword)

def _insert_concepts(content, concepts):
    line = f"{_CONCEPT_MARKER} " + " · ".join(f"[[{c}]]" for c in concepts)
    lines = content.splitlines()
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].startswith("[Source]"):
            # mirror the digest format: one blank line above and below
            lines.insert(i, line)
            lines.insert(i + 1, "")
            return "\n".join(lines) + "\n"
    return content.rstrip("\n") + f"\n\n{line}\n"

def backfill_profile(vault, profile_name, keywords):
    vault_path = Path(vault)
    profile_dir = vault_path / profile_name
    scanned = 0
    linked = 0
    all_concepts = []
    if not profile_dir.exists():
        return scanned, linked, 0
    for path in sorted(profile_dir.rglob("*.md")):
        scanned += 1
        content = path.read_text(encoding="utf-8")
        if _CONCEPT_MARKER in content:
            continue
        matched = [k for k in keywords if _matches(content, k)]
        if not matched:
            continue
        path.write_text(_insert_concepts(content, matched), encoding="utf-8")
        for c in matched:
            if c not in all_concepts:
                all_concepts.append(c)
        linked += 1
    stubs = ensure_concept_notes(vault_path, all_concepts)
    return scanned, linked, stubs

def run_backfill(ns):
    from sotawhat.profiles import PROFILES
    if ns.profile == "all":
        profiles = list(PROFILES)
    else:
        if ns.profile not in PROFILES:
            raise SystemExit(f"Unknown profile '{ns.profile}'. "
                             f"Choose from: {', '.join(PROFILES)}, all")
        profiles = [ns.profile]
    total_scanned = total_linked = total_stubs = 0
    for p in profiles:
        s, l, st = backfill_profile(ns.vault, p, PROFILES[p]["keywords"])
        total_scanned += s
        total_linked += l
        total_stubs += st
    print(f"Backfill: {total_scanned} scanned, {total_linked} linked, "
          f"{total_stubs} concept stubs ensured.")

# sotawhat/digest.py
import sys
from datetime import date

def collect(sources, keywords, limit, on_error=None):
    seen = set()
    out = []
    for source in sources:
        for kw in keywords:
            for r in source.safe_search(kw, limit, on_error=on_error):
                if r.id in seen:
                    continue
                seen.add(r.id)
                out.append(r)
    return out

def run_digest(ns):
    from sotawhat.profiles import PROFILES, build_sources
    from sotawhat.obsidian import write_notes  # Phase 4
    if ns.profile not in PROFILES:
        raise SystemExit(f"Unknown profile '{ns.profile}'. "
                         f"Choose from: {', '.join(PROFILES)}")
    profile = PROFILES[ns.profile]
    sources = build_sources(ns.profile)
    warnings = []
    results = collect(sources, profile["keywords"], ns.limit,
                      on_error=warnings.append)
    for w in warnings:
        print(w, file=sys.stderr)
    written = write_notes(results, vault=ns.vault, profile_name=ns.profile,
                          tags=profile["tags"], keywords=profile["keywords"],
                          added=date.today().isoformat())
    print(f"Digest '{ns.profile}': {len(results)} found, {written} new note(s) written.")

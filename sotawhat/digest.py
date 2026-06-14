# sotawhat/digest.py
import sys
from datetime import date
from sotawhat.textmatch import contains_any

def collect(sources, keywords, limit, on_error=None):
    by_id = {}
    out = []
    for source in sources:
        for kw in keywords:
            for r in source.safe_search(kw, limit, on_error=on_error):
                if r.id in by_id:
                    concepts = by_id[r.id].extra.setdefault("concepts", [])
                    if kw not in concepts:
                        concepts.append(kw)
                    continue
                r.extra.setdefault("concepts", [])
                if kw not in r.extra["concepts"]:
                    r.extra["concepts"].append(kw)
                by_id[r.id] = r
                out.append(r)
    return out

def filter_relevant(results, terms):
    return [r for r in results
            if contains_any(f"{r.title} {r.abstract}", terms)]

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
    require = profile.get("require_any")
    if require:
        before = len(results)
        results = filter_relevant(results, require)
        dropped = before - len(results)
        if dropped:
            print(f"[{ns.profile}] filtered out {dropped} non-AI result(s)",
                  file=sys.stderr)
    for w in warnings:
        print(w, file=sys.stderr)
    written = write_notes(results, vault=ns.vault, profile_name=ns.profile,
                          tags=profile["tags"], keywords=profile["keywords"],
                          added=date.today().isoformat())
    print(f"Digest '{ns.profile}': {len(results)} found, {written} new note(s) written.")

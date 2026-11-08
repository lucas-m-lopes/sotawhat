# sotawhat/pipeline/collect.py
"""Collection step of `run daily` (SDD §6.1): every source × every profile keyword, deduplicated by
result id, with the keyword that found each result kept as a concept."""
from sotawhat.textmatch import contains_any


def collect(sources, keywords, limit, on_error=None, on_source_error=None):
    by_id = {}
    out = []
    for source in sources:
        def handler(msg, _source=source):
            if on_error:
                on_error(msg)
            if on_source_error:
                on_source_error(_source, msg)
        for kw in keywords:
            for r in source.safe_search(kw, limit, on_error=handler):
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
    return [r for r in results if contains_any(f"{r.title} {r.abstract}", terms)]

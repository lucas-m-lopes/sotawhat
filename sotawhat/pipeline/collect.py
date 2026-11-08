# sotawhat/pipeline/collect.py
"""Collection step of `run daily` (SDD §6.1). Keyword sources run once per profile keyword, and the
keyword that found a result is kept as its concept. Channel sources (`keywordless`) run once, capped at
their `max_items`, and their name is the concept. Results are deduplicated by result id."""
from sotawhat.textmatch import contains_any


def collect(sources, keywords, limit, on_error=None, on_source_error=None):
    by_id = {}
    out = []

    def add(result, concept):
        known = by_id.get(result.id)
        if known is not None:
            concepts = known.extra.setdefault("concepts", [])
            if concept not in concepts:
                concepts.append(concept)
            return
        result.extra.setdefault("concepts", [])
        if concept not in result.extra["concepts"]:
            result.extra["concepts"].append(concept)
        by_id[result.id] = result
        out.append(result)

    for source in sources:
        def handler(msg, _source=source):
            if on_error:
                on_error(msg)
            if on_source_error:
                on_source_error(_source, msg)
        if getattr(source, "keywordless", False):
            for r in source.safe_fetch(getattr(source, "max_items", limit), on_error=handler):
                if getattr(source, "ai_specific", False):
                    r.extra["ai_source"] = True
                add(r, source.name)
            continue
        for kw in keywords:
            for r in source.safe_search(kw, limit, on_error=handler):
                add(r, kw)
    return out


def filter_relevant(results, terms):
    """Keep results that mention an AI term; channels that only carry AI content are kept as they are."""
    return [r for r in results if r.extra.get("ai_source") or contains_any(f"{r.title} {r.abstract}", terms)]

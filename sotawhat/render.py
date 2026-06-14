# sotawhat/render.py
from collections import OrderedDict
from sotawhat.summarize import extract_line

_SEP = "=" * 52

def _format_one(result, keyword):
    author = result.authors[0] if result.authors else "Unknown"
    headline = f"{result.title} ({author} - {result.date})"
    extract, _ = extract_line(result.abstract, keyword.lower(), 280)
    body = extract or result.abstract[:280]
    return f"{headline}\n{body}\nLink: {result.url}"

def render_grouped(results, keyword):
    by_source = OrderedDict()
    for r in results:
        by_source.setdefault(r.source, []).append(r)
    blocks = []
    for source, items in by_source.items():
        blocks.append(f"\n### {source} ({len(items)})\n")
        for item in items:
            blocks.append(_format_one(item, keyword))
            blocks.append(_SEP)
    return "\n".join(blocks).strip()

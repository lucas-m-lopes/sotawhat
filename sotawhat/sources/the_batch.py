# sotawhat/sources/the_batch.py
"""DeepLearning.AI's The Batch (SDD §5.2): no RSS, so the sitemap gives the issue pages and each issue is
split into its stories (one `<h1 id="slug">` per story, after the "News" heading). Issues already read are
kept in `data/state/` and never downloaded again."""
import json
import re
from html import unescape
from pathlib import Path

import httpx

from sotawhat.models import Result
from sotawhat.sources.base import Source

SITEMAP = "https://www.deeplearning.ai/sitemap.xml"
_ISSUE = re.compile(r"<loc>\s*(https://www\.deeplearning\.ai/the-batch/issue-(\d+))/?\s*</loc>")
_H1 = re.compile(r'<h1 id="([^"]+)"[^>]*>(.*?)</h1>', re.S)
_TAG = re.compile(r"<[^>]+>")
_SECTION_LABELS = {"news", "dear friends"}


def _text(fragment) -> str:
    fragment = re.sub(r"</(p|li|h\d)>", "\n", fragment)
    return "\n".join(" ".join(unescape(_TAG.sub(" ", line)).split()) for line in fragment.split("\n")).strip()


def split_issue(html, max_chars=3000):
    """-> (published date, [{slug, title, text, link}]) of the stories of one issue page."""
    published = re.search(r'<meta property="article:published_time" content="(\d{4}-\d{2}-\d{2})', html)
    end = html.find("</article>")
    body = html if end == -1 else html[:end]
    heads = list(_H1.finditer(body))
    stories = []
    for n, head in enumerate(heads):
        title = " ".join(unescape(_TAG.sub("", head.group(2))).split())
        if title.lower() in _SECTION_LABELS or len(title.split()) < 2:
            continue
        stop = heads[n + 1].start() if n + 1 < len(heads) else len(body)
        chunk = body[head.end():stop]
        cut = chunk.find("<h2")
        chunk = chunk if cut == -1 else chunk[:cut]
        link = re.search(r'<a href="(https?://[^"]+)"', chunk)
        text = re.sub(r"\n{2,}", "\n", _text(chunk))
        stories.append({"slug": head.group(1), "title": title, "text": text[:max_chars],
                        "link": link.group(1) if link else ""})
    return (published.group(1) if published else ""), stories


class TheBatchSource(Source):
    keywordless = True
    ai_specific = True

    def __init__(self, state_path, name="the-batch", max_issues=2, max_items=12, client=None, sitemap_url=SITEMAP):
        self.name, self.max_issues, self.max_items = name, max_issues, max_items
        self.state_path, self.sitemap_url = Path(state_path), sitemap_url
        self._client = client

    def _seen(self) -> set:
        if not self.state_path.exists():
            return set()
        return set(json.loads(self.state_path.read_text(encoding="utf-8")).get("issues", []))

    def fetch(self, limit):
        client = self._client or httpx.Client(timeout=40, follow_redirects=True)
        headers = {"User-Agent": "Mozilla/5.0 (sotawhat/3.0)"}
        seen, results, read = self._seen(), [], []
        try:
            r = client.get(self.sitemap_url, headers=headers)
            r.raise_for_status()
            issues = sorted({(int(n), url) for url, n in _ISSUE.findall(r.text)}, reverse=True)[:self.max_issues]
            for number, url in issues:
                if number in seen:
                    continue
                page = client.get(url, headers=headers)
                page.raise_for_status()
                published, stories = split_issue(page.text)
                read.append(number)
                for story in stories:
                    results.append(Result(id=f"{url}#{story['slug']}", title=story["title"], authors=["DeepLearning.AI"],
                                          date=published, url=f"{url}#{story['slug']}", abstract=story["text"],
                                          source="the-batch", extra={"kind": "newsletter_item", "link": story["link"],
                                                                     "issue": number,
                                                                     "canonical_id": f"thebatch:{number}#{story['slug']}"}))
        finally:
            if self._client is None:
                client.close()
        if read:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            self.state_path.write_text(json.dumps({"issues": sorted(seen | set(read))}), encoding="utf-8")
        return results[:limit] if limit else results

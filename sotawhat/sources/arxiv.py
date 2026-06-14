# sotawhat/sources/arxiv.py
import xml.etree.ElementTree as ET
import httpx
from sotawhat.models import Result
from sotawhat.sources.base import Source

_NS = {"atom": "http://www.w3.org/2005/Atom"}
_API = "https://export.arxiv.org/api/query"

def _arxiv_id(entry_id):
    # entry id looks like http://arxiv.org/abs/2401.00001v1
    tail = entry_id.rstrip("/").split("/abs/")[-1]
    return tail.split("v")[0]

def parse_atom(xml_text, source="arxiv"):
    root = ET.fromstring(xml_text)
    results = []
    for entry in root.findall("atom:entry", _NS):
        title = (entry.findtext("atom:title", default="", namespaces=_NS) or "").strip()
        summary = (entry.findtext("atom:summary", default="", namespaces=_NS) or "").strip()
        published = entry.findtext("atom:published", default="", namespaces=_NS) or ""
        entry_id = entry.findtext("atom:id", default="", namespaces=_NS) or ""
        authors = [a.findtext("atom:name", default="", namespaces=_NS).strip()
                   for a in entry.findall("atom:author", _NS)]
        url = ""
        for link in entry.findall("atom:link", _NS):
            if link.get("rel") == "alternate":
                url = link.get("href", "")
        url = url or entry_id
        results.append(Result(
            id=_arxiv_id(entry_id), title=" ".join(title.split()),
            authors=authors, date=published[:10], url=url,
            abstract=" ".join(summary.split()), source=source))
    return results

class ArxivSource(Source):
    name = "arxiv"

    def __init__(self, categories=("cs.LG", "cs.CL", "cs.AI")):
        self.categories = categories

    def _query(self, keyword):
        cats = " OR ".join(f"cat:{c}" for c in self.categories)
        return f"all:{keyword} AND ({cats})"

    def search(self, keyword, limit):
        params = {"search_query": self._query(keyword), "start": 0,
                  "max_results": limit, "sortBy": "submittedDate",
                  "sortOrder": "descending"}
        resp = httpx.get(_API, params=params, timeout=30, follow_redirects=True,
                         headers={"User-Agent": "sotawhat/2.0"})
        resp.raise_for_status()
        return parse_atom(resp.text, source=self.name)

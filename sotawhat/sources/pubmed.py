# sotawhat/sources/pubmed.py
import xml.etree.ElementTree as ET
import httpx
from sotawhat.models import Result
from sotawhat.sources.base import Source

_ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
_EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
_TOOL = "sotawhat"
_EMAIL = "lmlopes33@gmail.com"

def _text(node):
    return "".join(node.itertext()).strip() if node is not None else ""

def parse_efetch(xml_text):
    root = ET.fromstring(xml_text)
    results = []
    for art in root.findall(".//PubmedArticle"):
        pmid = _text(art.find(".//PMID"))
        title = _text(art.find(".//ArticleTitle"))
        abstract = " ".join(_text(a) for a in art.findall(".//Abstract/AbstractText")).strip()
        authors = []
        for a in art.findall(".//AuthorList/Author"):
            last = _text(a.find("LastName"))
            fore = _text(a.find("ForeName"))
            name = (f"{fore} {last}").strip()
            if name:
                authors.append(name)
        year = _text(art.find(".//PubDate/Year"))
        results.append(Result(
            id=pmid, title=title, authors=authors, date=year,
            url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            abstract=abstract, source="pubmed"))
    return results

class PubMedSource(Source):
    name = "pubmed"

    def __init__(self, and_clause=None):
        self.and_clause = and_clause

    def _term(self, keyword):
        if self.and_clause:
            return f"({keyword}) AND ({self.and_clause})"
        return keyword

    def search(self, keyword, limit):
        s = httpx.get(_ESEARCH, params={
            "db": "pubmed", "term": self._term(keyword), "retmax": limit,
            "retmode": "json", "sort": "date", "tool": _TOOL, "email": _EMAIL},
            timeout=30, follow_redirects=True)
        s.raise_for_status()
        ids = s.json().get("esearchresult", {}).get("idlist", [])
        if not ids:
            return []
        f = httpx.get(_EFETCH, params={
            "db": "pubmed", "id": ",".join(ids), "retmode": "xml",
            "tool": _TOOL, "email": _EMAIL}, timeout=30, follow_redirects=True)
        f.raise_for_status()
        return parse_efetch(f.text)

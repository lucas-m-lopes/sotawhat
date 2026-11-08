# sotawhat/items.py
"""Normalized `Item` (SDD §6.4) and canonical ids for exact dedup across sources."""
import hashlib
import json
import re
from dataclasses import dataclass, field
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_DOI_RE = re.compile(r"\b(10\.\d{4,9}/[^\s\"<>]+)", re.I)
_ARXIV_ID_RE = re.compile(r"^\d{4}\.\d{4,5}$")
_ARXIV_URL_RE = re.compile(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})", re.I)
_PMID_RE = re.compile(r"^\d{1,9}$")
_TRACKING = {"fbclid", "gclid", "ref", "ref_src", "_hsenc", "_hsmi", "mc_cid", "mc_eid", "_bhlid",
             "ck_subscriber_id"}


@dataclass
class Item:
    id: str
    kind: str
    source: str
    source_id: str
    title: str
    url: str
    authors: list = field(default_factory=list)
    published_at: str = ""
    text: str = ""
    doi: str | None = None
    arxiv_id: str | None = None
    pmid: str | None = None
    concepts: list = field(default_factory=list)
    profile: str | None = None

    @property
    def content_hash(self) -> str:
        basis = " ".join(f"{self.title} {self.text}".lower().split())
        return hashlib.sha1(basis.encode("utf-8")).hexdigest()


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
             if not k.lower().startswith("utm_") and k.lower() not in _TRACKING]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(query), ""))


def _clean_doi(doi: str) -> str:
    return doi.strip().rstrip(".,;)").lower()


def canonical_id(result) -> tuple[str, dict]:
    """Return (id, extra ids). Priority: a source-given canonical id > DOI > arXiv > PMID > URL > content hash.
    A source gives one when the URL alone is not unique (The Batch: every story of an issue shares the page URL,
    and normalization drops the #fragment)."""
    extra = result.extra or {}
    if extra.get("canonical_id"):
        return extra["canonical_id"], {}
    rid = (result.id or "").strip()
    url = (result.url or "").strip()

    doi = extra.get("doi")
    if not doi and rid.lower().startswith("doi:"):
        doi = rid[4:]
    if not doi:
        match = _DOI_RE.search(rid) or _DOI_RE.search(url)
        doi = match.group(1) if match else None
    if doi:
        doi = _clean_doi(doi)
        return f"doi:{doi}", {"doi": doi}

    arxiv = None
    if result.source in ("arxiv", "hf_papers") and _ARXIV_ID_RE.match(rid):
        arxiv = rid
    else:
        match = _ARXIV_URL_RE.search(url) or _ARXIV_URL_RE.search(rid)
        arxiv = match.group(1) if match else None
    if arxiv:
        return f"arxiv:{arxiv}", {"arxiv_id": arxiv}

    if result.source == "pubmed" and _PMID_RE.match(rid):
        return f"pmid:{rid}", {"pmid": rid}

    if url.startswith(("http://", "https://")):
        return f"url:{normalize_url(url)}", {}
    if rid:
        return f"{result.source}:{rid}", {}
    digest = hashlib.sha1(f"{result.title}|{result.source}".encode("utf-8")).hexdigest()[:16]
    return f"hash:{digest}", {}


def kind_for(source: str, extra=None) -> str:
    """repo | model | dataset | mcp_server | newsletter_item | regulation come from the source (P2)."""
    if (extra or {}).get("kind"):
        return extra["kind"]
    if source.startswith("rss:"):
        return "article"
    return "paper"


def to_item(result, profile: str | None = None) -> Item:
    iid, ids = canonical_id(result)
    return Item(
        id=iid, kind=kind_for(result.source, result.extra), source=result.source, source_id=result.id or "",
        title=result.title, url=result.url, authors=list(result.authors or []),
        published_at=result.date or "", text=result.abstract or "",
        doi=ids.get("doi"), arxiv_id=ids.get("arxiv_id"), pmid=ids.get("pmid"),
        concepts=list((result.extra or {}).get("concepts", [])), profile=profile)


def from_row(row) -> Item:
    """An `items` row from the store back into an `Item`."""
    return Item(
        id=row["id"], kind=row["kind"], source=row["source"], source_id=row["source_id"] or "",
        title=row["title"], url=row["canonical_url"] or "", authors=json.loads(row["authors_json"] or "[]"),
        published_at=row["published_at"] or "", text=row["text"] or "", doi=row["doi"],
        arxiv_id=row["arxiv_id"], pmid=row["pmid"], concepts=json.loads(row["concepts_json"] or "[]"),
        profile=row["profile"])

# tests/test_items.py
from sotawhat.items import canonical_id, normalize_url, to_item
from sotawhat.models import Result


def _r(rid, source, url="", **extra):
    return Result(id=rid, title="T", authors=["A"], date="2026-11-07", url=url,
                  abstract="abs", source=source, extra=extra)


def test_arxiv_and_hf_share_the_same_id():
    a = canonical_id(_r("2511.01234", "arxiv", "http://arxiv.org/abs/2511.01234v2"))
    h = canonical_id(_r("2511.01234", "hf_papers", "https://huggingface.co/papers/2511.01234"))
    assert a[0] == h[0] == "arxiv:2511.01234"


def test_doi_wins_over_url_and_is_lowercased():
    iid, ids = canonical_id(_r("10.1038/S41746-026-03450-3", "semantic_scholar", "https://x.org/p"))
    assert iid == "doi:10.1038/s41746-026-03450-3"
    assert ids == {"doi": "10.1038/s41746-026-03450-3"}
    assert canonical_id(_r("doi:10.1056/aie2601363", "crossref:nejm-ai"))[0] == "doi:10.1056/aie2601363"


def test_pubmed_pmid_and_url_fallback():
    assert canonical_id(_r("41234567", "pubmed"))[0] == "pmid:41234567"
    iid, _ = canonical_id(_r("https://Lab.example/Post/?utm_source=x&id=7#frag", "rss:lab",
                             "https://Lab.example/Post/?utm_source=x&id=7#frag"))
    assert iid == "url:https://lab.example/Post?id=7"


def test_normalize_url_strips_tracking_only():
    assert normalize_url("https://a.com/x/?fbclid=1&q=2") == "https://a.com/x?q=2"


def test_to_item_maps_fields_and_concepts():
    it = to_item(_r("2511.01234", "arxiv", "u", concepts=["agent"]), profile="geral")
    assert (it.id, it.kind, it.arxiv_id, it.concepts, it.profile) == (
        "arxiv:2511.01234", "paper", "2511.01234", ["agent"], "geral")
    assert to_item(_r("https://b.org/p", "rss:lab", "https://b.org/p")).kind == "article"
    assert len(it.content_hash) == 40

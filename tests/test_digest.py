# tests/test_digest.py
from sotawhat.models import Result
from sotawhat.digest import collect

class FakeSource:
    def __init__(self, name, items):
        self.name = name
        self._items = items
    def safe_search(self, keyword, limit, on_error=None):
        return self._items

def _r(rid, source):
    return Result(id=rid, title=rid, authors=[], date="2026-06-01",
                  url="u/" + rid, abstract="a", source=source)

def test_collect_dedupes_by_id_across_keywords():
    src = FakeSource("arxiv", [_r("1", "arxiv"), _r("1", "arxiv"), _r("2", "arxiv")])
    out = collect([src], keywords=["k1", "k2"], limit=10)
    ids = sorted(r.id for r in out)
    assert ids == ["1", "2"]

def test_collect_records_concepts_per_id():
    src = FakeSource("arxiv", [_r("1", "arxiv"), _r("2", "arxiv")])
    out = collect([src], keywords=["k1", "k2"], limit=10)
    by_id = {r.id: r for r in out}
    assert by_id["1"].extra["concepts"] == ["k1", "k2"]
    assert by_id["2"].extra["concepts"] == ["k1", "k2"]

def test_filter_relevant_keeps_ai_drops_others():
    from sotawhat.digest import filter_relevant
    keep = Result(id="1", title="Deep learning for sepsis", authors=[],
                  date="", url="", abstract="x", source="pubmed")
    drop = Result(id="2", title="Aspirin trial", authors=[],
                  date="", url="", abstract="no method here", source="pubmed")
    out = filter_relevant([keep, drop], ["deep learning", "machine learning"])
    assert [r.id for r in out] == ["1"]

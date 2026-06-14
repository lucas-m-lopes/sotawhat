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

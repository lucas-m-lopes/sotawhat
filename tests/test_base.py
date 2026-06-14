import pytest
from sotawhat.sources.base import Source

def test_source_requires_search():
    class Incomplete(Source):
        name = "x"
    with pytest.raises(NotImplementedError):
        Incomplete().search("k", 1)

def test_safe_search_swallows_errors():
    class Boom(Source):
        name = "boom"
        def search(self, keyword, limit):
            raise RuntimeError("down")
    warnings = []
    out = Boom().safe_search("k", 1, on_error=warnings.append)
    assert out == []
    assert "boom" in warnings[0]

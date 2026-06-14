from sotawhat.models import Result

def test_result_defaults_and_fields():
    r = Result(id="2401.00001", title="T", authors=["A"], date="2026-06-01",
               url="http://x/abs/2401.00001", abstract="abc", source="arxiv")
    assert r.id == "2401.00001"
    assert r.authors == ["A"]
    assert r.extra == {}

# tests/test_profiles.py
from sotawhat.profiles import PROFILES, build_sources

def test_profiles_exist():
    assert set(PROFILES) == {"geral", "medico"}
    assert PROFILES["medico"]["keywords"]

def test_build_sources_returns_source_objects():
    sources = build_sources("geral")
    names = [s.name for s in sources]
    assert "arxiv" in names
    assert all(hasattr(s, "search") for s in sources)

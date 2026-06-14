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

def test_medico_has_require_any():
    assert PROFILES["medico"]["require_any"]

def test_medico_pubmed_has_ai_clause():
    from sotawhat.profiles import MEDICAL_AI_CLAUSE
    sources = build_sources("medico")
    pub = [s for s in sources if s.name == "pubmed"][0]
    assert pub.and_clause == MEDICAL_AI_CLAUSE

def test_medical_feeds_curated():
    from sotawhat.profiles import MEDICAL_FEEDS
    labels = [name for name, _ in MEDICAL_FEEDS]
    assert "npj-digital-medicine" in labels
    assert "jmir-medinform" in labels
    assert "radiology-ai" not in labels

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
    assert "jmir-medinform" in labels
    assert "radiology-ai" not in labels
    assert "npj-digital-medicine" not in labels   # moved to Crossref (anti-bot HTML on nature.com RSS)

def test_nature_journals_come_from_crossref():
    from sotawhat.profiles import MEDICAL_JOURNALS
    sources = build_sources("medico", crossref_mailto="me@example.org")
    cr = [s for s in sources if s.name == "crossref"][0]
    assert cr.feeds == MEDICAL_JOURNALS
    assert ("npj-digital-medicine", "2398-6352") in MEDICAL_JOURNALS
    assert cr.mailto == "me@example.org"

def test_stalled_feeds_removed():
    from sotawhat.profiles import LAB_FEEDS
    assert "the-gradient" not in [name for name, _ in LAB_FEEDS]

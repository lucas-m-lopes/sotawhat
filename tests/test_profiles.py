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


def test_vendor_health_launches_reach_the_medical_profile():
    from sotawhat.profiles import HEALTH_AI_FEEDS
    news = [s for s in build_sources("medico") if s.name == "health-ai-news"][0]
    assert ("google-cloud-health", "https://cloudblog.withgoogle.com/topics/healthcare-life-sciences/rss/") in news.feeds
    assert news.feeds == HEALTH_AI_FEEDS and news.ai_specific and news.keywordless


def _names(sources):
    return [s.name for s in sources]


def test_p2_channel_sources_per_profile(tmp_path):
    from sotawhat.config import Settings

    settings = Settings(_env_file=None, sotawhat_data_dir=tmp_path, github_token="ghp_x", hf_token="hf_x",
                        gmail_address="eu@gmail.com", gmail_app_password="abcdefghijklmnop")
    medico = build_sources("medico", settings=settings)
    assert _names(medico) == ["pubmed", "arxiv", "medical", "crossref", "health-ai-news", "health-news", "google-news",
                              "medrxiv", "fda-ai-devices", "newsletters-saude", "github-med", "hf-medical", "mcp-health"]
    channels = [s for s in medico if s.keywordless]
    assert {s.name for s in channels} >= {"crossref", "medrxiv", "fda-ai-devices", "github-med", "google-news"}
    assert next(s for s in medico if s.name == "github-med").token == "ghp_x"
    assert str(next(s for s in medico if s.name == "fda-ai-devices").state_path).startswith(str(tmp_path))
    geral = build_sources("geral", settings=settings, segmenter=lambda *a: [])
    assert _names(geral) == ["arxiv", "semantic_scholar", "hf_papers", "labs", "ai-news", "the-batch", "gmail",
                             "newsletters-ia", "github-ai", "hf-trending", "mcp-recent"]
    assert next(s for s in geral if s.name == "hf-trending").token == "hf_x"
    assert next(s for s in geral if s.name == "labs").keywordless is False


def test_without_settings_the_stateful_channels_stay_out():
    assert not {"fda-ai-devices", "the-batch", "gmail", "newsletters-ia", "newsletters-saude"} & set(
        _names(build_sources("medico") + build_sources("geral")))
    assert "gmail" not in _names(build_sources("geral"))


def test_instagram_and_manual_capture_join_the_profiles(tmp_path):
    from types import SimpleNamespace

    from sotawhat.store.db import Store

    settings = SimpleNamespace(sotawhat_data_dir=tmp_path, sotawhat_config_dir=tmp_path, github_token="", hf_token="",
                               crossref_mailto="", gmail_address="", gmail_app_password="", gmail_query="",
                               instagram_per_account=3, instagram_max_usd_run=0.15)
    apify = SimpleNamespace(configured=True)
    with Store(tmp_path / "insight.db") as st:
        geral = _names(build_sources("geral", settings=settings, apify=apify))
        medico = _names(build_sources("medico", settings=settings, apify=apify, store=st))
        assert "instagram-ia" in geral and "instagram-saude" in medico and "manual-telegram" in medico
        off = _names(build_sources("medico", settings=settings, apify=SimpleNamespace(configured=False), store=st))
        assert "instagram-saude" not in off and "manual-telegram" in off          # links work without Apify
        assert not {"instagram-ia", "manual-telegram"} & set(_names(build_sources("geral")))


def test_newsletters_split_by_profile(tmp_path):
    from sotawhat.config import Settings

    settings = Settings(_env_file=None, sotawhat_data_dir=tmp_path, sotawhat_config_dir=tmp_path)
    seg = lambda *a: []                                                             # noqa: E731
    ia = next(s for s in build_sources("geral", settings=settings, segmenter=seg) if s.name == "newsletters-ia")
    saude = next(s for s in build_sources("medico", settings=settings, segmenter=seg) if s.name == "newsletters-saude")
    assert (ia.profile, saude.profile) == ("ia", "saude") and ia.segmenter is seg and saude.segmenter is seg
    assert ia.ai_filter is None and saude.ai_filter is not None and saude.ai_filter("Hcor adota IA")
    from sotawhat.sources.pages import read_article
    assert ia.article is read_article and saude.article is read_article        # excerpt feeds read the page
    assert str(ia.path) == str(tmp_path / "newsletters.yaml")
    assert str(saude.state_path) == str(tmp_path / "state" / "newsletters-saude.json")

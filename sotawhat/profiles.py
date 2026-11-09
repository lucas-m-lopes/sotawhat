# sotawhat/profiles.py
"""Profiles and their sources (SDD §5.3, §7). Keyword sources run once per profile keyword; channel sources
(P2) run once per day with a cap per source. Sources that keep state in `data/state/` (FDA, The Batch,
Gmail, newsletters, Instagram) are only built when `settings` is given; Gmail also needs the LLM segmenter,
and the newsletters split their digests with it (config/newsletters.yaml: ia -> geral, saude -> medico). P5: the
Instagram scan (Apify) splits by account category (ia -> geral, saude -> medico), and the links sent to the
Telegram bot (manual capture) enter the medical profile when the store is given."""
from sotawhat.sources.arxiv import ArxivSource
from sotawhat.sources.crossref import CrossrefJournalSource
from sotawhat.sources.fda import FDAAIDevicesSource
from sotawhat.sources.github import GitHubSource
from sotawhat.sources.gmail import GmailNewsletterSource
from sotawhat.sources.hf_hub import HFHubSource
from sotawhat.sources.hf_papers import HFPapersSource
from sotawhat.sources.inbox import InboxSource
from sotawhat.sources.instagram import InstagramSource
from sotawhat.sources.mcp_registry import MCPRegistrySource
from sotawhat.sources.newsletters import NewsletterFeedSource, mentions_ai_pt
from sotawhat.sources.medrxiv import MedRxivSource
from sotawhat.sources.pubmed import PubMedSource
from sotawhat.sources.rss import RSSSource
from sotawhat.sources.semantic_scholar import SemanticScholarSource
from sotawhat.sources.the_batch import TheBatchSource
from sotawhat.textmatch import contains_any

# Lab/blog feeds (general). URLs pinned here; unreachable feeds are skipped at runtime.
LAB_FEEDS = [
    ("google-research", "https://research.google/blog/rss/"),
    ("deepmind", "https://deepmind.google/blog/rss.xml"),
    ("bair", "https://bair.berkeley.edu/blog/feed.xml"),
    ("huggingface", "https://huggingface.co/blog/feed.xml"),
    ("ahead-of-ai", "https://magazine.sebastianraschka.com/feed"),
    ("simon-willison", "https://simonwillison.net/atom/everything/"),
    ("marktechpost", "https://www.marktechpost.com/feed/"),
]

# Medical journal feeds (verified to return entries via httpx + User-Agent).
MEDICAL_FEEDS = [
    ("jmir-ai", "https://ai.jmir.org/feed/atom"),
    ("jmir-medinform", "https://medinform.jmir.org/feed/atom"),
]

# Nature/npj RSS serve an anti-bot HTML page to non-browser clients (SDD §5.1), so these journals come
# from Crossref by ISSN (verified 2026-11-07); P2 adds JAMIA, Radiology: AI and npj Health Systems (2026-11-08).
MEDICAL_JOURNALS = [
    ("nature-machine-intelligence", "2522-5839"),
    ("npj-digital-medicine", "2398-6352"),
    ("nature-medicine", "1546-170X"),
    ("nejm-ai", "2836-9386"),
    ("jamia", "1527-974X"),
    ("radiology-ai", "2638-6100"),
    ("npj-health-systems", "3005-1959"),
]

# P2 channel feeds (verified 2026-11-08). AI-only ones skip the profile's AI-term filter.
HEALTH_AI_FEEDS = [
    ("jama-ai", "https://jamanetwork.com/rss/site_9/0_44024.xml"),
    ("stat-ai", "https://www.statnews.com/topic/artificial-intelligence/feed/"),
    ("monai", "https://github.com/Project-MONAI/MONAI/releases.atom"),
]
HEALTH_NEWS_FEEDS = [
    ("lancet-digital-health", "https://rss.sciencedirect.com/publication/science/25897500"),
    ("healthcaredive-it", "https://www.healthcaredive.com/feeds/topic/health-it/"),
]
GOOGLE_NEWS_FEEDS = [
    ("gnews-en", "https://news.google.com/rss/search?q=%28%22artificial+intelligence%22+OR+AI%29+%28hospital+OR+"
                 "clinical+OR+FDA%29+when%3A2d&hl=en-US&gl=US&ceid=US%3Aen"),
    ("gnews-pt", "https://news.google.com/rss/search?q=%22intelig%C3%AAncia+artificial%22+%28hospital+OR+Anvisa+OR+"
                 "SUS+OR+%22sa%C3%BAde+digital%22%29+-site%3Asapo.pt+when%3A2d&hl=pt-BR&gl=BR&ceid=BR%3Apt-419"),
]
AI_NEWS_FEEDS = [
    ("alphasignal", "https://alphasignal.ai/feed.xml"),
    ("openai", "https://openai.com/news/rss.xml"),
]
GITHUB_MEDICAL = [
    ("medical-imaging", "topic:medical-imaging"), ("healthcare-ai", "topic:healthcare-ai"),
    ("medical-ai", "topic:medical-ai"), ("fhir", "topic:fhir"), ("clinical-nlp", "topic:clinical-nlp"),
    ("digital-pathology", "topic:digital-pathology"), ("medical-llm", '"medical" "LLM" in:name,description'),
]
GITHUB_AI = [
    ("mcp-server", "topic:mcp-server"), ("agent-skills", "topic:agent-skills"), ("claude-skills", "topic:claude-skills"),
    ("ai-agents", "topic:ai-agents"), ("llm", "topic:llm"),
]
MCP_HEALTH_TERMS = ("health", "medical", "clinical", "fhir", "dicom", "pubmed", "radiology", "hl7")

# AND-ed into every medico PubMed query to force the AI/medicine intersection.
MEDICAL_AI_CLAUSE = (
    '"Artificial Intelligence"[Mesh] OR "machine learning"[tiab] '
    'OR "deep learning"[tiab] OR "neural network*"[tiab] '
    'OR "large language model*"[tiab] OR "foundation model*"[tiab]'
)

# A medico result is kept only if its title/abstract contains one of these
# (word-boundary match). "ML" is intentionally absent — it matches "mL".
AI_TERMS = [
    "artificial intelligence", "machine learning", "deep learning",
    "neural network", "large language model", "foundation model", "transformer",
    "computer vision", "natural language processing", "radiomics", "generative",
    "diffusion model", "reinforcement learning", "convolutional",
    "predictive model", "AI", "LLM", "NLP",
]

PROFILES = {
    "geral": {
        "keywords": ["large language model", "reinforcement learning",
                     "diffusion model", "agent"],
        "tags": ["ml-ai"],
    },
    "medico": {
        "keywords": ["clinical LLM", "medical imaging", "diagnosis",
                     "radiology", "electronic health record"],
        "tags": ["medical-ai"],
        "require_any": AI_TERMS,
    },
}


def health_ai_text(text) -> bool:
    """The health newsletters cover much more than AI: a story or post enters only when it mentions AI."""
    return contains_any(text, AI_TERMS) or mentions_ai_pt(text)


def _newsletters(settings, segmenter, profile):
    """Newsletters by RSS (config/newsletters.yaml): ia -> geral, saude -> medico (filtered by AI terms)."""
    return NewsletterFeedSource(f"newsletters-{profile}", settings.sotawhat_config_dir / "newsletters.yaml", profile,
                                settings.sotawhat_data_dir / "state" / f"newsletters-{profile}.json", segmenter=segmenter,
                                ai_filter=health_ai_text if profile == "saude" else None,
                                max_items=60 if profile == "ia" else 40)


def _instagram(settings, apify, describer, category):
    return InstagramSource(apify, settings.sotawhat_config_dir / "instagram_accounts.yaml",
                           settings.sotawhat_data_dir / "state" / "instagram.json", category, describer=describer,
                           per_account=settings.instagram_per_account, max_usd=settings.instagram_max_usd_run)


def build_sources(profile, crossref_mailto="", settings=None, segmenter=None, store=None, apify=None, describer=None):
    github_token = getattr(settings, "github_token", "") or ""
    hf_token = getattr(settings, "hf_token", "") or ""
    state = settings.sotawhat_data_dir / "state" if settings is not None else None
    crossref_mailto = crossref_mailto or getattr(settings, "crossref_mailto", "") or ""
    if profile == "geral":
        sources = [ArxivSource(("cs.LG", "cs.CL", "cs.AI")), SemanticScholarSource(), HFPapersSource(),
                   RSSSource("labs", LAB_FEEDS),
                   RSSSource("ai-news", AI_NEWS_FEEDS, keywordless=True, max_items=10, max_age_days=2, ai_specific=True)]
        if state is not None:
            sources.append(TheBatchSource(state / "the_batch.json"))
            if segmenter is not None:
                sources.append(GmailNewsletterSource(settings.gmail_address, settings.gmail_app_password,
                                                     settings.gmail_query, segmenter, state / "gmail.json"))
            sources.append(_newsletters(settings, segmenter, "ia"))
        sources += [GitHubSource("github-ai", GITHUB_AI, days=3, min_stars=20, max_items=15, token=github_token),
                    HFHubSource("hf-trending", [("trending-models", "models", {"sort": "trendingScore"})], per_query=10,
                                max_items=10, token=hf_token),
                    MCPRegistrySource("mcp-recent", recent_days=1, per_term=30, max_items=10)]
        if settings is not None and apify is not None and apify.configured:
            sources.append(_instagram(settings, apify, describer, "ia"))
        return sources
    if profile == "medico":
        sources = [PubMedSource(and_clause=MEDICAL_AI_CLAUSE),
                   ArxivSource(("q-bio.QM", "cs.LG", "cs.CV", "eess.IV")),
                   RSSSource("medical", MEDICAL_FEEDS),
                   CrossrefJournalSource(MEDICAL_JOURNALS, mailto=crossref_mailto),
                   RSSSource("health-ai-news", HEALTH_AI_FEEDS, keywordless=True, max_items=8, ai_specific=True),
                   RSSSource("health-news", HEALTH_NEWS_FEEDS, keywordless=True, max_items=10),
                   RSSSource("google-news", GOOGLE_NEWS_FEEDS, keywordless=True, max_items=10, max_age_days=2,
                             ai_specific=True),
                   MedRxivSource(days=2, max_items=40)]
        if state is not None:
            sources.append(FDAAIDevicesSource(state / "fda_ai_devices.json"))
            sources.append(_newsletters(settings, segmenter, "saude"))
        sources += [GitHubSource("github-med", GITHUB_MEDICAL, days=7, min_stars=5, max_items=15, token=github_token),
                    HFHubSource("hf-medical", [("medical-models", "models", {"filter": "medical", "sort": "trendingScore"}),
                                               ("medical-datasets", "datasets", {"filter": "medical", "sort": "trendingScore"})],
                                per_query=10, max_items=15, token=hf_token),
                    MCPRegistrySource("mcp-health", terms=MCP_HEALTH_TERMS, per_term=10, max_items=15)]
        if settings is not None and apify is not None and apify.configured:
            sources.append(_instagram(settings, apify, describer, "saude"))
        if store is not None:
            sources.append(InboxSource(store, apify=apify, describer=describer))
        return sources
    raise KeyError(f"Unknown profile: {profile}")

# sotawhat/profiles.py
from sotawhat.sources.arxiv import ArxivSource
from sotawhat.sources.semantic_scholar import SemanticScholarSource
from sotawhat.sources.hf_papers import HFPapersSource
from sotawhat.sources.pubmed import PubMedSource
from sotawhat.sources.rss import RSSSource

# Lab/blog feeds (general). URLs pinned here; unreachable feeds are skipped at runtime.
LAB_FEEDS = [
    ("google-research", "https://research.google/blog/rss/"),
    ("deepmind", "https://deepmind.google/blog/rss.xml"),
    ("bair", "https://bair.berkeley.edu/blog/feed.xml"),
    ("huggingface", "https://huggingface.co/blog/feed.xml"),
    ("the-gradient", "https://thegradient.pub/rss/"),
    ("ahead-of-ai", "https://magazine.sebastianraschka.com/feed"),
    ("simon-willison", "https://simonwillison.net/atom/everything/"),
    ("marktechpost", "https://www.marktechpost.com/feed/"),
]

# Medical journal feeds (verified to return entries via httpx + User-Agent).
MEDICAL_FEEDS = [
    ("nature-machine-intelligence", "https://www.nature.com/natmachintell.rss"),
    ("npj-digital-medicine", "https://www.nature.com/npjdigitalmed.rss"),
    ("jmir-ai", "https://ai.jmir.org/feed/atom"),
    ("jmir-medinform", "https://medinform.jmir.org/feed/atom"),
]

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

def build_sources(profile):
    if profile == "geral":
        return [ArxivSource(("cs.LG", "cs.CL", "cs.AI")),
                SemanticScholarSource(), HFPapersSource(),
                RSSSource("labs", LAB_FEEDS)]
    if profile == "medico":
        return [PubMedSource(and_clause=MEDICAL_AI_CLAUSE),
                ArxivSource(("q-bio.QM", "cs.LG", "cs.CV")),
                RSSSource("medical", MEDICAL_FEEDS)]
    raise KeyError(f"Unknown profile: {profile}")

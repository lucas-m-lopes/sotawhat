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

# Medical journal feeds.
MEDICAL_FEEDS = [
    ("nature-machine-intelligence", "https://www.nature.com/natmachintell.rss"),
    ("jmir-ai", "https://ai.jmir.org/feed/atom"),
    ("radiology-ai", "https://pubs.rsna.org/action/showFeed?type=etoc&feed=rss&jc=ai"),
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
    },
}

def build_sources(profile):
    if profile == "geral":
        return [ArxivSource(("cs.LG", "cs.CL", "cs.AI")),
                SemanticScholarSource(), HFPapersSource(),
                RSSSource("labs", LAB_FEEDS)]
    if profile == "medico":
        return [PubMedSource(),
                ArxivSource(("q-bio.QM", "cs.LG", "cs.CV")),
                RSSSource("medical", MEDICAL_FEEDS)]
    raise KeyError(f"Unknown profile: {profile}")

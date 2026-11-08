# sotawhat/sources/base.py
class Source:
    """Two kinds of sources:
    - keyword sources (arXiv, PubMed, Semantic Scholar, lab feeds): `search(keyword, limit)`, called once
      per profile keyword;
    - channel sources (P2: GitHub, Hugging Face, MCP registry, medRxiv, FDA, The Batch, Gmail, news feeds):
      `keywordless = True`, `fetch(limit)` called once per run with `max_items`; the triage decides relevance.
    `ai_specific = True` marks channels that only carry AI content, so the profile's AI-term filter is skipped."""
    name = "base"
    keywordless = False
    max_items = 20
    ai_specific = False

    def search(self, keyword, limit):
        raise NotImplementedError

    def fetch(self, limit):
        raise NotImplementedError

    def safe_search(self, keyword, limit, on_error=None):
        try:
            return self.search(keyword, limit)
        except Exception as exc:  # noqa: BLE001 - a failing source must not abort the run
            if on_error:
                on_error(f"[{self.name}] failed: {exc}")
            return []

    def safe_fetch(self, limit, on_error=None):
        try:
            return self.fetch(limit)
        except Exception as exc:  # noqa: BLE001 - a failing source must not abort the run
            if on_error:
                on_error(f"[{self.name}] failed: {exc}")
            return []

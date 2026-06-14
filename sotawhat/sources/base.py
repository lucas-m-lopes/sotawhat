class Source:
    name = "base"

    def search(self, keyword, limit):
        raise NotImplementedError

    def safe_search(self, keyword, limit, on_error=None):
        try:
            return self.search(keyword, limit)
        except Exception as exc:  # noqa: BLE001 - a failing source must not abort the run
            if on_error:
                on_error(f"[{self.name}] failed: {exc}")
            return []

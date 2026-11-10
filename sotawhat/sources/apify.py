# sotawhat/sources/apify.py
"""Apify REST client (P5, SDD §7.2): starts an actor, waits for it and reads its dataset.

- The token goes in the Authorization header, never in a URL (URLs end up in logs).
- Every run carries a charge cap (`maxTotalChargeUsd`) and, when given, an item cap (`maxItems`): the
  Instagram scraper is pay-per-event (US$ 0,0027 per result on the Free plan).
- A run that outlives `wait_seconds` is aborted, so a stuck scraper never keeps charging."""
import time

import httpx

API = "https://api.apify.com/v2"
TERMINAL = {"SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"}


class ApifyError(Exception):
    pass


class ApifyClient:
    def __init__(self, token, client=None, wait_seconds=600, clock=time.monotonic):
        self.token, self._client, self.wait_seconds, self._clock = token or "", client, wait_seconds, clock

    @property
    def configured(self) -> bool:
        return bool(self.token)

    def _open(self):
        return self._client or httpx.Client(base_url=API, timeout=90, headers={"User-Agent": "sotawhat/3.0"})

    def _call(self, client, method, path, **kwargs):
        try:
            r = client.request(method, path, headers={"Authorization": f"Bearer {self.token}"}, **kwargs)
        except httpx.HTTPError as exc:
            raise ApifyError(f"Apify: {type(exc).__name__}: {exc}") from None
        if r.status_code in (401, 403):
            raise ApifyError(f"Apify: token recusado ({r.status_code}); confira APIFY_TOKEN")
        if r.status_code == 402:
            raise ApifyError("Apify: sem crédito no plano neste mês (402)")
        if r.status_code >= 400:
            raise ApifyError(f"Apify {r.status_code}: {r.text[:200]}")
        return r.json()

    def run(self, actor, payload, max_usd=0.15, max_items=None, partial=False) -> list:
        """Runs `actor` (e.g. "apify~instagram-scraper") with `payload` and returns its dataset items. With `partial`, a
        run that is aborted or times out returns what it fetched (paid already) instead of raising."""
        if not self.configured:
            raise ApifyError("APIFY_TOKEN vazio")
        params = {"maxTotalChargeUsd": f"{max_usd:.2f}", "waitForFinish": 60}
        if max_items:
            params["maxItems"] = int(max_items)
        client = self._open()
        try:
            run = self._call(client, "POST", f"/acts/{actor}/runs", params=params, json=payload)["data"]
            deadline = self._clock() + self.wait_seconds
            while run["status"] not in TERMINAL:
                if self._clock() > deadline:
                    self._call(client, "POST", f"/actor-runs/{run['id']}/abort")
                    if partial:
                        return self._items(client, run)
                    raise ApifyError(f"Apify: o run {run['id']} passou de {self.wait_seconds} s e foi abortado")
                run = self._call(client, "GET", f"/actor-runs/{run['id']}", params={"waitForFinish": 60})["data"]
            if run["status"] != "SUCCEEDED" and not (partial and run["status"] in ("ABORTED", "TIMED-OUT")):
                raise ApifyError(f"Apify: o run {run['id']} terminou como {run['status']}")
            return self._items(client, run)
        finally:
            if self._client is None:
                client.close()

    def _items(self, client, run) -> list:
        items = self._call(client, "GET", f"/datasets/{run['defaultDatasetId']}/items",
                           params={"clean": "true", "format": "json"})
        return items if isinstance(items, list) else []

    def items(self, run_id) -> list:
        """The dataset items of an earlier run, e.g. one aborted after it had fetched (and charged) some results."""
        if not self.configured:
            raise ApifyError("APIFY_TOKEN vazio")
        client = self._open()
        try:
            return self._items(client, self._call(client, "GET", f"/actor-runs/{run_id}")["data"])
        finally:
            if self._client is None:
                client.close()

    def usage(self) -> dict:
        """-> {"used": US$ this cycle, "limit": US$ monthly cap, "cycle_end": ISO date} (for `doctor`)."""
        client = self._open()
        try:
            data = self._call(client, "GET", "/users/me/limits")["data"]
        finally:
            if self._client is None:
                client.close()
        return {"used": (data.get("current") or {}).get("monthlyUsageUsd", 0.0),
                "limit": (data.get("limits") or {}).get("maxMonthlyUsageUsd"),
                "cycle_end": ((data.get("monthlyUsageCycle") or {}).get("endAt") or "")[:10]}

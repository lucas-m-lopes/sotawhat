# tests/test_apify.py
"""Apify client (P5): auth header, charge cap, waiting, failures and the usage of the month."""
import httpx
import pytest

from sotawhat.sources.apify import API, ApifyClient, ApifyError


def _client(handler):
    return httpx.Client(base_url=API, transport=httpx.MockTransport(handler))


def test_run_waits_reads_the_dataset_and_never_puts_the_token_in_the_url():
    calls = []

    def handler(request):
        calls.append(request)
        assert request.headers["authorization"] == "Bearer apify_api_x" and "apify_api_x" not in str(request.url)
        if request.method == "POST" and request.url.path.endswith("/acts/apify~instagram-scraper/runs"):
            assert request.url.params["maxTotalChargeUsd"] == "0.15" and request.url.params["maxItems"] == "6"
            return httpx.Response(201, json={"data": {"id": "r1", "status": "RUNNING", "defaultDatasetId": "d1"}})
        if request.url.path.endswith("/actor-runs/r1"):
            return httpx.Response(200, json={"data": {"id": "r1", "status": "SUCCEEDED", "defaultDatasetId": "d1"}})
        if request.url.path.endswith("/datasets/d1/items"):
            assert request.url.params["clean"] == "true"
            return httpx.Response(200, json=[{"shortCode": "abc"}])
        return httpx.Response(404)

    items = ApifyClient("apify_api_x", client=_client(handler)).run("apify~instagram-scraper", {"x": 1}, max_items=6)
    assert items == [{"shortCode": "abc"}] and len(calls) == 3


def test_failed_and_stuck_runs_and_bad_tokens():
    def failed(request):
        if request.method == "POST":
            return httpx.Response(201, json={"data": {"id": "r2", "status": "FAILED", "defaultDatasetId": "d"}})
        return httpx.Response(404)

    with pytest.raises(ApifyError, match="FAILED"):
        ApifyClient("t", client=_client(failed)).run("a~b", {})

    aborted = []
    ticks = iter([0, 0, 700, 700])

    def stuck(request):
        if request.url.path.endswith("/abort"):
            aborted.append(True)
            return httpx.Response(200, json={"data": {"id": "r3", "status": "ABORTING"}})
        return httpx.Response(200, json={"data": {"id": "r3", "status": "RUNNING", "defaultDatasetId": "d"}})

    with pytest.raises(ApifyError, match="abortado"):
        ApifyClient("t", client=_client(stuck), wait_seconds=600, clock=lambda: next(ticks)).run("a~b", {})
    assert aborted == [True]
    with pytest.raises(ApifyError, match="token recusado"):
        ApifyClient("t", client=_client(lambda r: httpx.Response(401, json={}))).run("a~b", {})
    with pytest.raises(ApifyError, match="APIFY_TOKEN"):
        ApifyClient("").run("a~b", {})


def test_a_stuck_run_keeps_what_it_fetched_when_partial_and_an_old_run_can_be_read():
    ticks = iter([0, 0, 700, 700])

    def stuck(request):
        if request.url.path.endswith("/abort"):
            return httpx.Response(200, json={"data": {"id": "r4", "status": "ABORTING"}})
        if request.url.path.endswith("/datasets/d4/items"):
            return httpx.Response(200, json=[{"username": "a"}, {"username": "b"}])
        return httpx.Response(200, json={"data": {"id": "r4", "status": "RUNNING", "defaultDatasetId": "d4"}})

    client = ApifyClient("t", client=_client(stuck), wait_seconds=600, clock=lambda: next(ticks))
    assert client.run("a~b", {}, partial=True) == [{"username": "a"}, {"username": "b"}]

    def old(request):
        if request.url.path.endswith("/actor-runs/r5"):
            return httpx.Response(200, json={"data": {"id": "r5", "status": "ABORTED", "defaultDatasetId": "d5"}})
        if request.url.path.endswith("/datasets/d5/items"):
            return httpx.Response(200, json=[{"username": "c"}])
        return httpx.Response(404)

    assert ApifyClient("t", client=_client(old)).items("r5") == [{"username": "c"}]
    timed_out = lambda r: httpx.Response(201 if r.method == "POST" else 200, json=(  # noqa: E731
        {"data": {"id": "r6", "status": "TIMED-OUT", "defaultDatasetId": "d6"}} if "datasets" not in r.url.path else []))
    assert ApifyClient("t", client=_client(timed_out)).run("a~b", {}, partial=True) == []
    with pytest.raises(ApifyError, match="TIMED-OUT"):
        ApifyClient("t", client=_client(timed_out)).run("a~b", {})


def test_usage_of_the_month():
    def handler(request):
        return httpx.Response(200, json={"data": {"monthlyUsageCycle": {"endAt": "2026-12-07T23:59:59.999Z"},
                                                  "limits": {"maxMonthlyUsageUsd": 5},
                                                  "current": {"monthlyUsageUsd": 0.42}}})

    assert ApifyClient("t", client=_client(handler)).usage() == {"used": 0.42, "limit": 5, "cycle_end": "2026-12-07"}

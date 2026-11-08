# tests/test_inbox.py
"""Manual capture (P5, SDD §7.2 T2, §7.7): links sent to the bot become items."""
import httpx

from sotawhat.sources.inbox import InboxSource, page_summary
from sotawhat.store.db import Store
from tests.test_instagram import SIDECAR, FakeApify


def _inbox_store(tmp_path, *payloads):
    st = Store(tmp_path / "insight.db")
    for payload in payloads:
        st.add_inbox("telegram", payload)
    return st


def test_inbox_resolves_instagram_and_links_and_marks_rows(tmp_path):
    st = _inbox_store(tmp_path, {"text": "veja https://www.instagram.com/p/C1abcDEF/?igsh=1", "urls":
                                 ["https://www.instagram.com/p/C1abcDEF/?igsh=1"]},
                      {"text": "https://example.org/post e https://example.org/post",
                       "urls": ["https://example.org/post", "https://example.org/post"]})

    def handler(request):
        html = ('<html><head><title>Ignorado</title><meta property="og:title" content="Escriba ambiente &amp; PS">'
                '<meta name="description" content="Ensaio com 2 mil consultas."></head></html>')
        return httpx.Response(200, headers={"content-type": "text/html; charset=utf-8"}, content=html.encode())

    apify = FakeApify([SIDECAR])
    source = InboxSource(st, apify=apify, describer=lambda post: "slide com números",
                         client=httpx.Client(transport=httpx.MockTransport(handler)), check_host=lambda url: True)
    results = source.fetch(50)
    assert apify.calls[0][1]["directUrls"] == ["https://www.instagram.com/p/C1abcDEF/"]
    assert [r.source for r in results] == ["manual:telegram", "manual:telegram"]
    ig, link = results
    assert ig.extra["canonical_id"] == "ig:C1abcDEF" and ig.extra["manual"] and "slide com números" in ig.abstract
    assert link.title == "Escriba ambiente & PS" and link.abstract.startswith("Ensaio com 2 mil consultas.")
    assert st.conn.execute("SELECT COUNT(*) FROM inbox WHERE processed_at IS NULL").fetchone()[0] == 0
    assert source.fetch(50) == []
    st.close()


def test_inbox_falls_back_to_plain_links_and_refuses_private_hosts(tmp_path):
    st = _inbox_store(tmp_path, {"text": "", "urls": ["https://www.instagram.com/p/PRIVATE1/", "http://192.168.0.10/admin"]})

    class Down(FakeApify):
        def run(self, *args, **kwargs):
            raise RuntimeError("Apify fora do ar")

    hits = []
    source = InboxSource(st, apify=Down([]), client=httpx.Client(transport=httpx.MockTransport(
        lambda r: hits.append(r) or httpx.Response(200))), check_host=lambda url: "192.168" not in url)
    results = source.fetch(50)
    assert [r.title for r in results] == ["Link enviado: www.instagram.com", "Link enviado: 192.168.0.10"]
    assert all(r.extra["manual"] for r in results) and [str(h.url) for h in hits] == ["https://www.instagram.com/p/PRIVATE1/"]
    st.close()


def test_page_summary_reads_meta_in_any_order():
    html = '<meta content="Descrição B" name="description"><title> Título\n A </title>'
    assert page_summary(html) == ("Título A", "Descrição B")


def test_redirects_are_checked_hop_by_hop(tmp_path):
    st = _inbox_store(tmp_path, {"text": "", "urls": ["https://short.example/x"]})
    hits = []

    def handler(request):
        hits.append(str(request.url))
        return httpx.Response(302, headers={"location": "http://10.0.0.5/internal"})

    source = InboxSource(st, client=httpx.Client(transport=httpx.MockTransport(handler)),
                         check_host=lambda url: "10.0.0.5" not in url)
    assert [r.title for r in source.fetch(50)] == ["Link enviado: short.example"] and hits == ["https://short.example/x"]
    st.close()


def test_public_host_refuses_private_addresses():
    from sotawhat.sources.inbox import public_host

    assert not public_host("http://127.0.0.1:8765/api/stats") and not public_host("ftp://example.org/x")
    assert not public_host("http://192.168.0.1/") and not public_host("http://[::1]/")

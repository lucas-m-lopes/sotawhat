# tests/test_pages.py
"""Web pages read by the sources: the main content of an article (trafilatura) and the reader that never raises
and never leaves the public internet."""
import httpx

from sotawhat.sources.gmail import html_to_text
from sotawhat.sources.pages import main_content, read_article
from tests.test_newsletters import ARTICLE

PAGE = ('<html><head><title>Site</title></head><body><nav><a href="/">Home</a> <a href="/about">About us</a></nav>'
        f"<article>{ARTICLE}</article><footer><p>Privacy policy · Terms of use</p></footer></body></html>")


def test_main_content_keeps_the_article_and_its_links():
    text, links = html_to_text(main_content(PAGE, "https://site.org/a"))
    assert "Paragraph 0:" in text and "Paragraph 19:" in text and "JAMA study" in text
    assert "https://jamanetwork.com/x" in links.values()
    assert "About us" not in text and "Privacy policy" not in text
    assert main_content("") == "" and main_content("<html><body></body></html>") == ""


def test_read_article_never_raises_and_stays_on_public_hosts():
    hits = []

    def handler(request):
        hits.append(request.url.host)
        if request.url.host == "down.org":
            raise httpx.ConnectError("refused", request=request)
        if request.url.host == "blocked.org":
            return httpx.Response(403, headers={"content-type": "text/html"}, content=b"<html>Just a moment...</html>")
        if request.url.host == "short.link":
            return httpx.Response(302, headers={"location": "http://10.0.0.5/admin"})
        return httpx.Response(200, headers={"content-type": "text/html; charset=utf-8"}, content=PAGE.encode())

    client = httpx.Client(transport=httpx.MockTransport(handler))
    public = lambda url: "10.0.0.5" not in url                                      # noqa: E731
    assert "Paragraph 3:" in read_article("https://site.org/a", client=client, check_host=public)
    assert read_article("https://down.org/a", client=client, check_host=public) == ""
    assert read_article("https://blocked.org/a", client=client, check_host=public) == ""
    assert read_article("https://short.link/a", client=client, check_host=public) == ""   # every redirect hop checked
    assert read_article("http://127.0.0.1:8765/api/stats", client=client) == ""          # the real check: no request
    assert hits == ["site.org", "down.org", "blocked.org", "short.link"]

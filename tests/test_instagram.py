# tests/test_instagram.py
"""Instagram (P5, SDD §7.2): accounts file, post normalization and the daily scan with its watermark."""
from datetime import datetime, timezone

import pytest

from sotawhat.configfiles import ConfigError
from sotawhat.sources.instagram import InstagramSource, load_accounts, normalize, post_urls

NOW = datetime(2026, 11, 8, 12, 0, tzinfo=timezone.utc)
SIDECAR = {"shortCode": "C1abcDEF", "type": "Sidecar", "ownerUsername": "medai.br", "ownerFullName": "Med AI",
           "caption": "Novo paper: LLM triagem no PS\n#ai #health", "timestamp": "2026-11-08T09:00:00.000Z",
           "childPosts": [{"type": "Image", "displayUrl": "https://scontent.cdninstagram.com/a.jpg", "alt": "gráfico"},
                          {"type": "Image", "displayUrl": "https://scontent.cdninstagram.com/b.jpg"}],
           "displayUrl": "https://scontent.cdninstagram.com/a.jpg"}
REEL = {"shortCode": "R2reel", "type": "Video", "productType": "clips", "ownerUsername": "airesearch",
        "caption": "", "timestamp": "2026-11-07T22:00:00.000Z", "videoUrl": "https://scontent.cdninstagram.com/v.mp4",
        "displayUrl": "https://scontent.cdninstagram.com/c.jpg"}


class FakeApify:
    configured = True

    def __init__(self, items):
        self.items, self.calls = items, []

    def run(self, actor, payload, max_usd=0.15, max_items=None):
        self.calls.append((actor, payload, max_usd, max_items))
        return list(self.items)


def _accounts(tmp_path, text):
    path = tmp_path / "instagram_accounts.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_accounts_file_and_post_urls(tmp_path):
    path = _accounts(tmp_path, "accounts:\n- {username: medai.br, category: saude, enabled: true}\n"
                               "- {username: airesearch, category: ia, enabled: false}\n")
    assert [a["username"] for a in load_accounts(path)] == ["medai.br", "airesearch"]
    assert load_accounts(tmp_path / "missing.yaml") == []
    with pytest.raises(ConfigError):
        load_accounts(_accounts(tmp_path, "accounts:\n- {username: 'bad name', category: ia}\n"))
    with pytest.raises(ConfigError):
        load_accounts(_accounts(tmp_path, "accounts:\n- {username: ok, category: memes}\n"))
    text = ("olha https://www.instagram.com/p/C1abcDEF/?igsh=xyz e https://instagram.com/reel/R2reel/ "
            "e de novo https://www.instagram.com/medai.br/p/C1abcDEF/")
    assert post_urls(text) == ["https://www.instagram.com/p/C1abcDEF/", "https://www.instagram.com/reel/R2reel/"]


def test_normalize_posts():
    post = normalize(SIDECAR)
    assert (post["shortcode"], post["owner"], post["type"]) == ("C1abcDEF", "medai.br", "carousel")
    assert [m["url"] for m in post["media"]] == ["https://scontent.cdninstagram.com/a.jpg",
                                                 "https://scontent.cdninstagram.com/b.jpg"]
    reel = normalize(REEL)
    assert reel["type"] == "reel" and reel["url"] == "https://www.instagram.com/reel/R2reel/" and reel["video_url"]
    assert normalize({"caption": "sem shortcode"}) is None


def test_scan_uses_the_watermark_describes_and_skips_seen_posts(tmp_path):
    accounts = _accounts(tmp_path, "accounts:\n- {username: medai.br, category: saude, enabled: true}\n"
                                   "- {username: off, category: saude, enabled: false}\n"
                                   "- {username: airesearch, category: ia, enabled: true}\n")
    apify = FakeApify([SIDECAR, REEL])
    described = []
    source = InstagramSource(apify, accounts, tmp_path / "state" / "instagram.json", "saude",
                             describer=lambda post: described.append(post["shortcode"]) or "um gráfico de barras",
                             now=NOW)
    results = source.fetch(10)
    actor, payload, max_usd, max_items = apify.calls[0]
    assert actor == "apify~instagram-scraper" and payload["directUrls"] == ["https://www.instagram.com/medai.br/"]
    assert payload["onlyPostsNewerThan"] == "2026-11-07T12:00:00Z" and max_items == 3 and max_usd == 0.15
    assert [r.extra["canonical_id"] for r in results] == ["ig:C1abcDEF", "ig:R2reel"] and described == ["C1abcDEF", "R2reel"]
    first = results[0]
    assert first.title == "@medai.br: Novo paper: LLM triagem no PS" and "[conteúdo visual] um gráfico" in first.abstract
    assert first.extra["kind"] == "instagram_post" and first.source == "instagram" and not first.extra["manual"]
    later = InstagramSource(apify, accounts, tmp_path / "state" / "instagram.json", "saude",
                            now=datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc))
    assert later.fetch(10) == []                                         # both already seen
    assert apify.calls[1][1]["onlyPostsNewerThan"] == "2026-11-08T12:00:00Z"   # the watermark
    far = InstagramSource(apify, accounts, tmp_path / "state" / "instagram.json", "saude",
                          now=datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc))
    far.fetch(10)
    assert apify.calls[2][1]["onlyPostsNewerThan"] == "2026-11-17T12:00:00Z"   # never more than 3 days back
    assert InstagramSource(FakeApify([]), tmp_path / "none.yaml", tmp_path / "s.json", "ia").fetch(10) == []

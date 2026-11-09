# tests/test_newsletters.py
"""Newsletters by RSS (config/newsletters.yaml): posts, digests split by the LLM, the health AI filter, the
state that never reads an entry twice, `sotawhat newsletters add` and the doctor check."""
import calendar
import json
import time

import httpx
import pytest

from sotawhat.configfiles import ConfigError
from sotawhat.items import to_item
from sotawhat.llm.gateway import BudgetExceeded, LLMFailure
from sotawhat.llm.schemas import NewsletterStories
from sotawhat.profiles import health_ai_text
from sotawhat.sources.newsletters import (NewsletterFeedSource, add_newsletter, default_name, discover_feed,
                                          feed_candidates, load_newsletters, mentions_ai_pt)
from sotawhat.sources.rss import FeedError

NOW = calendar.timegm((2026, 11, 9, 12, 0, 0))


def _date(days_ago):
    return time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime(NOW - days_ago * 86400))


def rss(*entries, title="Feed"):
    items = "".join(
        f"<item><title>{t}</title><link>{link}</link><guid>{link}</guid><pubDate>{_date(age)}</pubDate>"
        f"<description><![CDATA[{body}]]></description></item>" for t, link, age, body in entries)
    return f'<?xml version="1.0"?><rss version="2.0"><channel><title>{title}</title>{items}</channel></rss>'.encode()


def write_yaml(path, rows):
    lines = ["# comentário do usuário", "newsletters:"]
    for row in rows:
        lines.append(f"  - name: {row['name']}")
        lines += [f"    {k}: {v}" for k, v in row.items() if k != "name"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def segmenter_returning(stories, seen):
    def segment(subject, sender, text):
        seen.append((subject, sender, text))
        return NewsletterStories.model_validate({"stories": stories}).stories
    return segment


ISSUE = ("<p>Welcome to Import AI.</p>" + "<p>Filler text about the week in AI research. </p>" * 12
         + '<p>A new <a href="https://arxiv.org/abs/2611.05555">paper on medical agents</a> came out.</p>'
         + '<p><a href="https://example.substack.com/subscribe">Subscribe</a></p>')


def test_load_newsletters_validates(tmp_path):
    assert load_newsletters(tmp_path / "none.yaml") == []
    good = write_yaml(tmp_path / "n.yaml", [{"name": "import-ai", "url": "https://importai.substack.com/feed",
                                            "profile": "ia", "kind": "digest"},
                                           {"name": "topol", "url": "https://erictopol.substack.com/feed",
                                            "profile": "saude", "enabled": "false"}])
    feeds = load_newsletters(good)
    assert [f["kind"] for f in feeds] == ["digest", "post"] and feeds[0]["enabled"] is True
    for bad in ({"name": "x", "url": "https://x.y/feed", "profile": "geral"},
                {"name": "X Y", "url": "https://x.y/feed", "profile": "ia"},
                {"name": "x", "url": "x.y/feed", "profile": "ia"},
                {"name": "x", "url": "https://x.y/feed", "profile": "ia", "kind": "essay"}):
        with pytest.raises(ConfigError):
            load_newsletters(write_yaml(tmp_path / "bad.yaml", [bad]))
    with pytest.raises(ConfigError):
        load_newsletters(write_yaml(tmp_path / "dup.yaml", [{"name": "x", "url": "https://a.b/feed", "profile": "ia"}] * 2))


def test_the_shipped_list_is_valid():
    feeds = load_newsletters("config/newsletters.yaml")
    assert {f["profile"] for f in feeds} == {"ia", "saude"} and sum(f["enabled"] for f in feeds) >= 20
    assert not next(f for f in feeds if f["name"] == "the-rundown")["enabled"]      # it comes by Gmail


def test_posts_newest_first_capped_per_feed_and_never_read_twice(tmp_path):
    path = write_yaml(tmp_path / "n.yaml", [{"name": "interconnects", "url": "https://i.ai/feed", "profile": "ia"},
                                            {"name": "disabled", "url": "https://off.ai/feed", "profile": "ia",
                                             "enabled": "false"},
                                            {"name": "topol", "url": "https://t.ai/feed", "profile": "saude"}])
    feed = rss(("Open models today", "https://i.ai/p/open-models", 1, "<p>How big is the <b>open</b> model economy?</p>"),
               ("RL scaling", "https://i.ai/p/rl?utm_source=rss", 2, "<p>RL notes</p>"),
               ("Older post", "https://i.ai/p/older", 3, "<p>Older</p>"),
               ("Too old", "https://i.ai/p/ancient", 10, "<p>Ancient</p>"))
    asked = []

    def fetch(url):
        asked.append(url)
        return feed

    src = NewsletterFeedSource("newsletters-ia", path, "ia", tmp_path / "state.json", fetch=fetch, per_feed=2, now=NOW)
    first = src.fetch(40)
    assert asked == ["https://i.ai/feed"] and src.feeds == [("interconnects", "https://i.ai/feed")]
    assert [r.title for r in first] == ["Open models today", "RL scaling"]
    assert first[0].abstract == "How big is the open model economy?" and first[0].source == "newsletter:interconnects"
    assert first[1].id == "https://i.ai/p/rl" and first[0].date == "2026-11-08"
    assert to_item(first[0]).kind == "newsletter_item"
    assert [r.title for r in src.fetch(40)] == ["Older post"]                       # the backlog drains next run
    assert src.fetch(40) == [] and len(json.loads((tmp_path / "state.json").read_text())["seen"]) == 3


def test_digest_is_split_into_stories_with_their_links(tmp_path):
    path = write_yaml(tmp_path / "n.yaml", [{"name": "import-ai", "url": "https://importai.substack.com/feed",
                                            "profile": "ia", "kind": "digest"}])
    feed = rss(("Import AI 480", "https://importai.substack.com/p/import-ai-480", 1, ISSUE))
    seen = []
    stories = [{"title": "Medical agents", "summary": "A paper on agents for hospitals.", "link": 1, "category": "paper"},
               {"title": "Jack's take", "summary": "Thoughts on compute.", "link": 0, "category": "opinion"},
               {"title": "Sponsor", "summary": "Buy GPUs.", "link": 0, "category": "sponsor"}]
    src = NewsletterFeedSource("newsletters-ia", path, "ia", tmp_path / "s.json", segmenter=segmenter_returning(stories, seen),
                               fetch=lambda url: feed, resolve=lambda url: url, now=NOW)
    results = src.fetch(40)
    subject, sender, text = seen[0]
    assert subject == "Import AI 480" and sender == "import-ai" and "[1] https://arxiv.org/abs/2611.05555" in text
    assert "subscribe" not in text.split("Links:")[1]                              # the footer link is never offered
    assert [r.title for r in results] == ["Medical agents", "Jack's take"]
    assert to_item(results[0]).id == "arxiv:2611.05555"
    assert results[1].url == "https://importai.substack.com/p/import-ai-480"
    assert to_item(results[1]).id == "newsletter:https://importai.substack.com/p/import-ai-480#2"
    without = NewsletterFeedSource("x", path, "ia", tmp_path / "s2.json", fetch=lambda url: feed, now=NOW).fetch(40)
    assert len(without) == 1 and without[0].title == "Import AI 480"              # no LLM: one item per issue


def test_health_posts_need_an_ai_term_in_english_or_portuguese(tmp_path):
    path = write_yaml(tmp_path / "n.yaml", [{"name": "futuro", "url": "https://f.br/feed", "profile": "saude"}])
    feed = rss(("Plano de saúde ia ser reajustado", "https://f.br/1", 1, "<p>O plano ia subir 12%.</p>"),
               ("Hcor adota IA na triagem", "https://f.br/2", 2, "<p>O hospital usa um modelo.</p>"),
               ("Epic launches an AI scribe", "https://f.br/3", 3, "<p>Ambient documentation.</p>"))
    src = NewsletterFeedSource("newsletters-saude", path, "saude", tmp_path / "s.json", ai_filter=health_ai_text,
                               fetch=lambda url: feed, per_feed=1, now=NOW)
    assert [r.title for r in src.fetch(40)] == ["Hcor adota IA na triagem"]      # the filter runs before the cap
    assert [r.title for r in src.fetch(40)] == ["Epic launches an AI scribe"]
    assert mentions_ai_pt("uso de inteligência artificial") and mentions_ai_pt("as IAs generativas")
    assert not mentions_ai_pt("ele ia ao hospital") and health_ai_text("a new LLM for radiology")


def test_llm_failure_reads_the_issue_again_and_budget_stops(tmp_path):
    path = write_yaml(tmp_path / "n.yaml", [{"name": "dair-ai", "url": "https://d.ai/feed", "profile": "ia",
                                            "kind": "digest"},
                                           {"name": "import-ai", "url": "https://i.ai/feed", "profile": "ia",
                                            "kind": "digest"}])
    feed = rss(("Top AI Papers", "https://d.ai/p/top", 1, ISSUE))

    def failing(*args):
        raise LLMFailure("invalid JSON twice")

    src = NewsletterFeedSource("n", path, "ia", tmp_path / "s.json", segmenter=failing, fetch=lambda url: feed, now=NOW)
    assert src.fetch(40) == [] and not (tmp_path / "s.json").exists()
    stories = [{"title": "Paper", "summary": "A paper.", "link": 1, "category": "paper"}]
    ok = NewsletterFeedSource("n", path, "ia", tmp_path / "s.json", segmenter=segmenter_returning(stories, []),
                              fetch=lambda url: feed, resolve=lambda url: url, now=NOW)
    assert len(ok.fetch(40)) == 2                                                  # one story from each feed

    calls = []

    def broke(*args):
        calls.append(args)
        raise BudgetExceeded("run budget reached")

    stop = NewsletterFeedSource("n", path, "ia", tmp_path / "s3.json", segmenter=broke, fetch=lambda url: feed, now=NOW)
    assert stop.fetch(40) == [] and stop.stopped == "run budget reached" and len(calls) == 1


def test_a_failing_feed_is_recorded_and_the_others_go_on(tmp_path):
    path = write_yaml(tmp_path / "n.yaml", [{"name": "down", "url": "https://down.ai/feed", "profile": "ia"},
                                            {"name": "up", "url": "https://up.ai/feed", "profile": "ia"}])

    def fetch(url):
        if "down" in url:
            raise FeedError("HTML instead of a feed")
        return rss(("Post", "https://up.ai/p/1", 1, "<p>x</p>"))

    src = NewsletterFeedSource("n", path, "ia", tmp_path / "s.json", fetch=fetch, now=NOW)
    assert [r.title for r in src.fetch(40)] == ["Post"]
    assert src.feed_errors == {"down": "FeedError: HTML instead of a feed"} and [n for n, _ in src.feeds] == ["down", "up"]


def test_feed_discovery():
    assert feed_candidates("importai")[0] == "https://importai.substack.com/feed"
    assert feed_candidates("https://www.fixhealth.ai/p/some-post")[:2] == ["https://www.fixhealth.ai/p/some-post/feed/",
                                                                         "https://www.fixhealth.ai/feed"]
    assert feed_candidates("https://www.statnews.com/topic/artificial-intelligence/")[0] == \
        "https://www.statnews.com/topic/artificial-intelligence/feed/"
    assert feed_candidates("https://site.org")[0] == "https://site.org/feed"
    assert feed_candidates("https://x.org/index.xml")[0] == "https://x.org/index.xml"
    feed = rss(("Post", "https://x.org/1", 1, "x"), title="X")

    def fetch(url):
        if url == "https://x.org/custom/feed.atom":
            return feed
        raise httpx.HTTPStatusError("404", request=httpx.Request("GET", url), response=httpx.Response(404))

    page = '<html><head><link rel="alternate" type="application/rss+xml" href="/custom/feed.atom"></head></html>'
    url, parsed = discover_feed("https://x.org/blog", fetch=fetch, page=lambda u: page)
    assert url == "https://x.org/custom/feed.atom" and parsed.feed.title == "X"
    with pytest.raises(ValueError):
        discover_feed("https://x.org/blog", fetch=fetch, page=lambda u: "<html></html>")
    assert default_name("https://importai.substack.com/feed") == "importai"
    assert default_name("https://www.fixhealth.ai/feed") == "fixhealth"
    assert default_name("https://blog.example.co.uk/rss") == "blog-example"


def test_add_newsletter_keeps_the_comments_and_refuses_repeats(tmp_path):
    path = write_yaml(tmp_path / "n.yaml", [{"name": "import-ai", "url": "https://importai.substack.com/feed",
                                            "profile": "ia", "kind": "digest"}])
    feed = rss(("Week 1", "https://palpate.substack.com/p/1", 5, "x"), title="Palpate: Health AI")

    def fetch(url):
        if url == "https://palpate.substack.com/feed":
            return feed
        raise FeedError("no")

    added = add_newsletter(path, "palpate", "saude", fetch=fetch, page=lambda u: "", today="2026-11-09")
    assert added["name"] == "palpate" and added["posts"] == 1 and added["newest"] == "2026-11-04"
    text = path.read_text(encoding="utf-8")
    assert text.startswith("# comentário do usuário") and "note: 'Palpate: Health AI (adicionada em 2026-11-09)'" in text
    feeds = load_newsletters(path)
    assert [f["name"] for f in feeds] == ["import-ai", "palpate"] and feeds[1]["profile"] == "saude"
    with pytest.raises(ValueError, match="já está na lista"):
        add_newsletter(path, "https://palpate.substack.com", "saude", fetch=fetch, page=lambda u: "")
    with pytest.raises(ValueError):
        add_newsletter(path, "palpate", "geral", fetch=fetch, page=lambda u: "")
    new = add_newsletter(tmp_path / "fresh.yaml", "palpate", "ia", kind="digest", fetch=fetch, page=lambda u: "")
    assert load_newsletters(tmp_path / "fresh.yaml")[0]["kind"] == "digest" and new["kind"] == "digest"


def test_doctor_names_failing_and_quiet_feeds(tmp_path):
    from types import SimpleNamespace

    from sotawhat.doctor import check_newsletters

    write_yaml(tmp_path / "newsletters.yaml",
               [{"name": "fresh", "url": "https://fresh.ai/feed", "profile": "ia"},
                {"name": "paused", "url": "https://paused.ai/feed", "profile": "saude"},
                {"name": "down", "url": "https://down.ai/feed", "profile": "saude"},
                {"name": "disabled", "url": "https://off.ai/feed", "profile": "ia", "enabled": "false"}])

    def fetch(url):
        if "down" in url:
            raise FeedError("challenge page")
        return rss(("Post", f"{url}/1", 1 if "fresh" in url else 120, "x"))

    settings = SimpleNamespace(sotawhat_config_dir=tmp_path)
    check = check_newsletters(settings, fetch=fetch, now=NOW)
    assert check.status == "warn" and "2 de 3 respondem (IA 1, saúde 2)" in check.detail
    assert "falhando: down (FeedError)" in check.detail and "sem post há 90+ dias: paused" in check.detail
    assert check_newsletters(SimpleNamespace(sotawhat_config_dir=tmp_path / "none")).status == "warn"

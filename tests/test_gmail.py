# tests/test_gmail.py
"""Gmail newsletters (SDD §7.1): read-only IMAP, X-GM-RAW search, segmentation by LLM, clean links."""
import json
from pathlib import Path

import pytest

from sotawhat.items import to_item
from sotawhat.llm.schemas import NewsletterStories
from sotawhat.sources.gmail import GmailNewsletterSource, covered, html_to_text, make_segmenter, skip_link

RAW = Path("tests/fixtures/newsletter.eml").read_bytes()


class FakeIMAP:
    def __init__(self, messages):
        self.messages, self.calls, self.readonly = messages, [], None

    def login(self, user, password):
        self.calls.append(("login", user))

    def list(self):
        return "OK", [b'(\\HasNoChildren) "/" "INBOX"', b'(\\All \\HasNoChildren) "/" "[Gmail]/Todos os e-mails"']

    def select(self, mailbox, readonly=False):
        self.calls.append(("select", mailbox, readonly))
        return "OK", [b"3"]

    def uid(self, command, *args):
        self.calls.append(("uid", command) + args)
        if command == "SEARCH":
            return "OK", [b" ".join(m[0] for m in self.messages)]
        uid = args[0]
        msgid, raw = next((m[1], m[2]) for m in self.messages if m[0] == uid)
        return "OK", [(b"1 (X-GM-MSGID " + msgid + b" UID " + uid + b" BODY[] {%d}" % len(raw), raw), b")"]

    def logout(self):
        self.calls.append(("logout",))


def segmenter_returning(stories, seen):
    def segment(subject, sender, text):
        seen.append((subject, sender, text))
        return NewsletterStories.model_validate({"stories": stories}).stories
    return segment


STORIES = [
    {"title": "MedGemma 2 is out", "summary": "Google released MedGemma 2, an open 27B model for radiology reports.",
     "link": 1, "category": "model"},
    {"title": "Agent evals", "summary": "A new benchmark for tool-using agents.", "link": 2, "category": "paper"},
    {"title": "CloudGPU", "summary": "Try CloudGPU today.", "link": 3, "category": "sponsor"},
]


def test_html_to_text_numbers_links_and_drops_scripts():
    text, links = html_to_text(RAW.decode().split("text/html; charset=\"utf-8\"")[1])
    assert "MedGemma 2 [1]" in text and "read the paper [2]" in text and "track()" not in text and "color:red" not in text
    assert links[1] == "https://click.aiweekly.example/track?id=1" and len(links) == 5
    assert skip_link("https://aiweekly.example/unsubscribe?u=1", "Unsubscribe") and skip_link("mailto:a@b.c", "")
    assert skip_link("https://x.example/p", "Manage preferences") and not skip_link(links[1], "MedGemma 2")


def test_fetch_reads_only_new_messages_and_cleans_links(tmp_path):
    imap, seen, resolved = FakeIMAP([(b"7", b"1111", RAW)]), [], []

    def resolve(url):
        resolved.append(url)
        return {"https://click.aiweekly.example/track?id=1": "https://blog.google/medgemma-2/?utm_source=aiweekly&ref=x",
                "https://link.mail.beehiiv.com/ss/c/xyz": "https://arxiv.org/abs/2611.01234"}.get(url, url)

    src = GmailNewsletterSource("eu@gmail.com", "abcd efgh ijkl mnop", "label:newsletters-ai newer_than:2d",
                                segmenter_returning(STORIES, seen), tmp_path / "gmail.json",
                                imap_factory=lambda: imap, resolve=resolve)
    results = src.fetch(40)
    assert ("select", '"[Gmail]/Todos os e-mails"', True) in imap.calls
    search = next(c for c in imap.calls if c[:2] == ("uid", "SEARCH"))
    assert search[2:] == ("X-GM-RAW", '"label:newsletters-ai newer_than:2d"')
    fetch = next(c for c in imap.calls if c[:2] == ("uid", "FETCH"))
    assert "BODY.PEEK[]" in fetch[3] and imap.calls[-1] == ("logout",)
    subject, sender, text = seen[0]
    assert subject.startswith("AI Weekly #42") and sender == "AI Weekly <news@aiweekly.example>" and "[2]" in text
    assert [r.title for r in results] == ["MedGemma 2 is out", "Agent evals"]           # the sponsor is dropped
    assert results[0].url == "https://blog.google/medgemma-2" and results[1].id == "https://arxiv.org/abs/2611.01234"
    assert results[0].source == "gmail:aiweekly.example" and results[0].date == "2026-11-07"
    assert to_item(results[1]).id == "arxiv:2611.01234" and to_item(results[0]).kind == "newsletter_item"
    assert not any("unsubscribe" in url or "preferences" in url for url in resolved)
    assert json.loads((tmp_path / "gmail.json").read_text())["seen"] == ["1111"]
    assert src.fetch(40) == [] and len(seen) == 1                                       # already read


def test_story_without_link_keeps_a_stable_id_and_unconfigured_source_is_silent(tmp_path):
    stories = [{"title": "Editorial note", "summary": "Thoughts on agents.", "link": 0, "category": "opinion"}]
    src = GmailNewsletterSource("eu@gmail.com", "pw", "q", segmenter_returning(stories, []), tmp_path / "g.json",
                                imap_factory=lambda: FakeIMAP([(b"8", b"2222", RAW)]), resolve=lambda u: u)
    result = src.fetch(10)[0]
    assert result.id == "gmail:2222#1" and result.url == ""
    assert GmailNewsletterSource("", "", "q", None, tmp_path / "x.json").fetch(10) == []


def test_make_segmenter_uses_the_segment_task():
    class Gateway:
        def __init__(self):
            self.calls = []

        def structured(self, task, messages, model, models=None):
            self.calls.append((task, messages))
            return NewsletterStories.model_validate({"stories": STORIES[:1]})

    gateway = Gateway()
    stories = make_segmenter(gateway)("Subject", "Sender <s@x.y>", "body [1]\n\nLinks:\n[1] https://x.y")
    task, messages = gateway.calls[0]
    assert task == "segment" and "Sender <s@x.y>" in messages[1]["content"] and stories[0].link == 1
    with pytest.raises(Exception):
        NewsletterStories.model_validate({"stories": [STORIES[0] | {"category": "spam"}]})


def test_senders_with_a_feed_of_their_own_are_skipped(tmp_path):
    """The Batch (sitemap) and AlphaSignal (RSS) already arrive by their own sources: a Gmail filter that also
    labels their e-mails must not double the stories, nor spend an LLM call."""
    batch = RAW.replace(b"From: AI Weekly <news@aiweekly.example>", b"From: The Batch <thebatch@mail.deeplearning.ai>")
    seen = []
    src = GmailNewsletterSource("eu@gmail.com", "pw", "q", segmenter_returning(STORIES, seen), tmp_path / "g.json",
                                imap_factory=lambda: FakeIMAP([(b"9", b"3333", batch), (b"7", b"1111", RAW)]),
                                resolve=lambda u: u)
    results = src.fetch(40)
    assert len(seen) == 1 and {r.source for r in results} == {"gmail:aiweekly.example"}
    assert sorted(json.loads((tmp_path / "g.json").read_text())["seen"]) == ["1111", "3333"]   # read, never again
    assert covered("AlphaSignal <news@alphasignal.ai>") and not covered("The Rundown <news@daily.therundown.ai>")

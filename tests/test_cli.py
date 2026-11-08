# tests/test_cli.py
from sotawhat.cli import parse_args

def test_parse_classic_keyword_and_number():
    ns = parse_args(["language", "model", "10"])
    assert ns.command == "search"
    assert ns.keyword == "language model"
    assert ns.num == 10

def test_parse_default_number():
    ns = parse_args(["transformer"])
    assert ns.keyword == "transformer"
    assert ns.num == 5

def test_parse_explicit_search():
    ns = parse_args(["search", "perplexity", "3"])
    assert ns.command == "search"
    assert ns.keyword == "perplexity"
    assert ns.num == 3

def test_parse_digest():
    ns = parse_args(["digest", "--profile", "medico", "--vault", "V"])
    assert ns.command == "digest"
    assert ns.profile == "medico"
    assert ns.vault == "V"

def test_parse_backfill_links():
    ns = parse_args(["backfill-links", "--vault", "V"])
    assert ns.command == "backfill-links"
    assert ns.vault == "V"
    assert ns.profile == "all"

def test_parse_backfill_links_with_profile():
    ns = parse_args(["backfill-links", "--vault", "V", "--profile", "medico"])
    assert ns.profile == "medico"

def test_parse_run_daily():
    ns = parse_args(["run", "daily", "--vault", "V", "--no-notify", "--limit", "5"])
    assert (ns.command, ns.kind, ns.vault, ns.no_notify, ns.limit) == ("run", "daily", "V", True, 5)
    ns = parse_args(["run", "daily"])
    assert ns.vault is None and ns.no_notify is False and ns.limit == 10

def test_parse_doctor():
    assert parse_args(["doctor"]).llm is False
    assert parse_args(["doctor", "--llm"]).llm is True

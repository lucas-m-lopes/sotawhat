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

def test_parse_run_no_llm_and_feedback():
    assert parse_args(["run", "daily", "--no-llm"]).no_llm is True
    assert parse_args(["run", "daily"]).no_llm is False
    assert parse_args(["feedback", "listen"]).action == "listen"
    assert parse_args(["feedback", "pull"]).command == "feedback"

def test_parse_eval_commands():
    ns = parse_args(["eval", "golden", "draft", "--vault", "V", "--n", "40"])
    assert (ns.eval_command, ns.action, ns.vault, ns.n, ns.dir) == ("golden", "draft", "V", 40, "tests/evals/triage")
    ns = parse_args(["eval", "models", "--models", "a/b,c/d", "--apply"])
    assert (ns.eval_command, ns.task, ns.models, ns.apply, ns.limit) == ("models", "triage", "a/b,c/d", True, 0)

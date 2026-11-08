# sotawhat/cli.py
import argparse
import sys

_SUBCOMMANDS = {"search", "run", "doctor", "feedback", "eval", "serve"}

def parse_args(argv):
    # Backward compat: `sotawhat <keyword...> [N]` with no subcommand -> search.
    if not argv:
        raise SystemExit("You must specify a keyword")
    if argv[0] not in _SUBCOMMANDS:
        argv = ["search"] + argv

    parser = argparse.ArgumentParser(prog="sotawhat")
    sub = parser.add_subparsers(dest="command", required=True)

    p_search = sub.add_parser("search")
    p_search.add_argument("words", nargs="+")

    p_run = sub.add_parser("run")
    p_run.add_argument("kind", choices=["daily"])
    p_run.add_argument("--limit", type=int, default=10)
    p_run.add_argument("--no-notify", action="store_true")
    p_run.add_argument("--no-llm", action="store_true", help="collect and run stage A only (no LLM calls)")

    p_doctor = sub.add_parser("doctor")
    p_doctor.add_argument("--llm", action="store_true", help="smoke-test each primary model (cents)")

    p_serve = sub.add_parser("serve", help="graph interface on http://127.0.0.1:8765")
    p_serve.add_argument("--port", type=int, default=None, help="default: SOTAWHAT_WEB_PORT (8765)")
    p_serve.add_argument("--no-browser", action="store_true", help="do not open the browser")

    p_feedback = sub.add_parser("feedback")
    p_feedback.add_argument("action", choices=["pull", "listen"])

    p_eval = sub.add_parser("eval")
    eval_sub = p_eval.add_subparsers(dest="eval_command", required=True)
    p_golden = eval_sub.add_parser("golden")
    p_golden.add_argument("action", choices=["draft", "import"])
    p_golden.add_argument("--n", type=int, default=60)
    p_golden.add_argument("--dir", default="tests/evals/triage")
    p_golden.add_argument("--name", default="golden_v1")
    p_golden.add_argument("--seed", type=int, default=13)
    p_golden.add_argument("--force", action="store_true", help="overwrite an existing draft")
    p_models = eval_sub.add_parser("models")
    p_models.add_argument("--task", default="triage", choices=["triage"])
    p_models.add_argument("--models", default=None, help="comma-separated OpenRouter ids (default: llm.yaml bakeoff)")
    p_models.add_argument("--golden", default="tests/evals/triage/golden_v1.jsonl")
    p_models.add_argument("--limit", type=int, default=0)
    p_models.add_argument("--concurrency", type=int, default=4)
    p_models.add_argument("--apply", action="store_true", help="put the winner first in config/llm.yaml")

    ns = parser.parse_args(argv)
    if ns.command == "search":
        words = ns.words
        num = 5
        if len(words) > 1:
            try:
                num = int(words[-1])
                words = words[:-1]
            except ValueError:
                pass
        ns.keyword = " ".join(words)
        ns.num = num
    return ns

def _run_search(ns):
    from sotawhat.sources.arxiv import ArxivSource
    from sotawhat.render import render_grouped
    warnings = []
    results = ArxivSource().safe_search(ns.keyword, ns.num, on_error=warnings.append)
    for w in warnings:
        print(w, file=sys.stderr)
    if not results:
        print(f"Sorry, we were unable to find anything for '{ns.keyword}'")
        return
    print(render_grouped(results, ns.keyword))

def main(argv=None):
    import truststore
    truststore.inject_into_ssl()   # trust the Windows store (local TLS inspection; never verify=False)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")   # cp1252 consoles/pipes must not crash on emoji
    ns = parse_args(argv if argv is not None else sys.argv[1:])
    if ns.command == "search":
        _run_search(ns)
    elif ns.command == "run":
        from sotawhat.pipeline.daily import main_daily
        raise SystemExit(main_daily(ns))
    elif ns.command == "doctor":
        from sotawhat.doctor import main_doctor
        raise SystemExit(main_doctor(ns))
    elif ns.command == "feedback":
        from sotawhat.pipeline.feedback import main_feedback
        raise SystemExit(main_feedback(ns))
    elif ns.command == "eval":
        from sotawhat.evals.commands import main_eval
        raise SystemExit(main_eval(ns))
    elif ns.command == "serve":
        from sotawhat.web.app import main_serve
        raise SystemExit(main_serve(ns))

if __name__ == "__main__":
    main()

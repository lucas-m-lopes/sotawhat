# sotawhat/cli.py
import argparse
import sys

_SUBCOMMANDS = {"search", "run", "ideate", "doctor", "feedback", "eval", "serve", "serve-mcp", "graph", "instagram",
                "newsletters", "backup", "calibrate", "repair", "lessons"}
_LESSON_ID_ACTIONS = ("resume", "rerender", "send", "pack")

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
    p_run.add_argument("kind", choices=["daily", "weekly"])
    p_run.add_argument("--limit", type=int, default=10)
    p_run.add_argument("--no-notify", action="store_true")
    p_run.add_argument("--no-llm", action="store_true", help="daily: collect and run stage A only (no LLM calls)")
    p_run.add_argument("--modo", choices=["economico", "completo"], default="economico", help="weekly: idea engine mode")

    p_ideate = sub.add_parser("ideate", help="idea engine on demand (report in data/weekly, ideas on Telegram)")
    p_ideate.add_argument("--tema", default=None, help='keep only technique × problem pairs about this theme, e.g. "UTI"')
    p_ideate.add_argument("--n", type=int, default=None, help="finalists wanted (N candidates, critique for N + 2)")
    p_ideate.add_argument("--modo", choices=["economico", "completo"], default="economico")
    p_ideate.add_argument("--no-notify", action="store_true", help="write the report only (no Telegram, no e-mail)")

    p_doctor = sub.add_parser("doctor")
    p_doctor.add_argument("--llm", action="store_true", help="smoke-test each primary model (cents)")

    p_serve = sub.add_parser("serve", help="graph interface on http://127.0.0.1:8765")
    p_serve.add_argument("--port", type=int, default=None, help="default: SOTAWHAT_WEB_PORT (8765)")
    p_serve.add_argument("--no-browser", action="store_true", help="do not open the browser")

    sub.add_parser("serve-mcp", help="MCP server sotawhat-graph over stdio (for Claude Code)")

    p_graph = sub.add_parser("graph", help="entity graph: Neo4j mirror, extraction backlog, export")
    p_graph.add_argument("graph_action", choices=["up", "extract", "sync", "status", "export"])
    p_graph.add_argument("--rebuild", action="store_true", help="sync: empty the Neo4j mirror and send everything")
    p_graph.add_argument("--limit", type=int, default=None, help="extract: at most N items")
    p_graph.add_argument("--out", default=None, help="export: folder (default data/exports)")

    p_instagram = sub.add_parser("instagram", help="Instagram accounts to scan (P5)")
    p_instagram.add_argument("instagram_action", choices=["import"])
    p_instagram.add_argument("file", help="following.json from the Accounts Center export")
    p_instagram.add_argument("--max", type=int, default=50, help="accounts enabled for the daily scan (default 50)")
    p_instagram.add_argument("--limit", type=int, default=None, help="classify at most N new accounts")
    p_instagram.add_argument("--yes", action="store_true", help="fetch the profiles on Apify (paid) and classify")

    p_news = sub.add_parser("newsletters", help="newsletters read by RSS (config/newsletters.yaml)")
    p_news.add_argument("newsletters_action", choices=["add"])
    p_news.add_argument("address", help="Substack name (importai), site or feed URL")
    p_news.add_argument("--profile", choices=["ia", "saude"], required=True,
                        help="ia: Fronteira de IA (perfil geral); saude: IA ∩ Saúde (perfil médico)")
    p_news.add_argument("--kind", choices=["post", "digest"], default="post",
                        help="post: each post is an item; digest: each issue is split into its stories by the LLM")
    p_news.add_argument("--name", default=None, help="short name (default: from the address)")

    p_lessons = sub.add_parser("lessons", help="aulas 3D narradas: setup, voices, make, resume, rerender, send, pack, list")
    p_lessons.add_argument("lessons_action", choices=["setup", "voices", "make", "resume", "rerender", "send", "pack", "list"])
    p_lessons.add_argument("id", nargs="?", type=int, help="the lesson number (resume, rerender, send, pack)")
    p_lessons.add_argument("--tema", help="topic of the lesson (make)")
    p_lessons.add_argument("--entidade", type=int, action="append", help="graph entity id; repeat for several")
    p_lessons.add_argument("--auto", action="store_true", help="the strongest weekly trend that has no lesson yet")
    p_lessons.add_argument("--voz", help="piper:faber|cadu|jeff or google:pt-BR-Chirp3-HD-<name>")
    p_lessons.add_argument("--modo", choices=["economico", "equilibrado"], default="economico",
                           help="equilibrado: Kimi K3.1 Pro writes the storyboard")
    p_lessons.add_argument("--sem-envio", dest="no_send", action="store_true", help="do not send it to Telegram")

    p_backup = sub.add_parser("backup", help="copy data/insight.db to data/backups (P6)")
    p_backup.add_argument("--keep", type=int, default=8, help="copies to keep (default 8)")
    p_backup.add_argument("--restore", default=None, help="restore this copy over data/insight.db")
    p_backup.add_argument("--yes", action="store_true", help="confirm the restore")

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
    eval_sub.add_parser("triage", help="precision of the triage by your votes (G2)")
    eval_sub.add_parser("ideas", help="the idea ledger: finalists and the share you want to explore (G4)")
    p_report = eval_sub.add_parser("report", help="the SDD goals G1-G4 in data/reports (P6)")
    p_report.add_argument("--send", action="store_true", help="also send the goals table to Telegram")
    p_extract = eval_sub.add_parser("extract", help="precision of the extraction on an annotated sample (G3)")
    p_extract.add_argument("action", choices=["draft", "import"])
    p_extract.add_argument("--n", type=int, default=40)
    p_extract.add_argument("--force", action="store_true", help="overwrite an existing draft")

    p_repair = sub.add_parser("repair", help="fix stored texts (P6)")
    p_repair.add_argument("repair_action", choices=["cjk"], help="cjk: triage texts with Chinese/Japanese/Korean characters")

    p_calibrate = sub.add_parser("calibrate", help="proposals for the triage cut-offs and the idea weights (P6)")
    p_calibrate.add_argument("--apply", action="store_true", help="write the proposal to config/")

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
    if ns.command == "lessons" and ns.lessons_action in _LESSON_ID_ACTIONS and ns.id is None:
        parser.error(f"lessons {ns.lessons_action} precisa do número da aula")
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

def _console_to_file():
    """Under pythonw.exe (the scheduled tasks run without a console window, so closing a window can no longer
    kill a run) there is no stdout/stderr: prints and tracebacks go to data/logs/console.log instead."""
    if sys.stdout is not None and sys.stderr is not None:
        return
    import os
    from pathlib import Path

    folder = Path(os.environ.get("SOTAWHAT_DATA_DIR") or "data") / "logs"
    folder.mkdir(parents=True, exist_ok=True)
    out = open(folder / "console.log", "a", encoding="utf-8", errors="replace", buffering=1)  # noqa: SIM115
    sys.stdout = sys.stdout or out
    sys.stderr = sys.stderr or out

def main(argv=None):
    import truststore
    truststore.inject_into_ssl()   # trust the Windows store (local TLS inspection; never verify=False)
    _console_to_file()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")   # cp1252 consoles/pipes must not crash on emoji
    ns = parse_args(argv if argv is not None else sys.argv[1:])
    if ns.command == "search":
        _run_search(ns)
    elif ns.command == "run" and ns.kind == "weekly":
        from sotawhat.pipeline.weekly import main_weekly
        raise SystemExit(main_weekly(ns))
    elif ns.command == "run":
        from sotawhat.pipeline.daily import main_daily
        raise SystemExit(main_daily(ns))
    elif ns.command == "ideate":
        from sotawhat.pipeline.weekly import main_ideate
        raise SystemExit(main_ideate(ns))
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
    elif ns.command == "serve-mcp":
        from sotawhat.mcp_server import main_mcp
        raise SystemExit(main_mcp(ns))
    elif ns.command == "graph":
        from sotawhat.graph.commands import main_graph
        raise SystemExit(main_graph(ns))
    elif ns.command == "repair":
        from sotawhat.pipeline.repair import main_repair
        raise SystemExit(main_repair(ns))
    elif ns.command == "calibrate":
        from sotawhat.evals.calibrate import main_calibrate
        raise SystemExit(main_calibrate(ns))
    elif ns.command == "backup":
        from sotawhat.store.backup import main_backup
        raise SystemExit(main_backup(ns))
    elif ns.command == "instagram":
        from sotawhat.pipeline.accounts import main_instagram
        raise SystemExit(main_instagram(ns))
    elif ns.command == "newsletters":
        from sotawhat.sources.newsletters import main_newsletters
        raise SystemExit(main_newsletters(ns))
    elif ns.command == "lessons":
        from sotawhat.lessons.pipeline import main_lessons
        raise SystemExit(main_lessons(ns))

if __name__ == "__main__":
    main()

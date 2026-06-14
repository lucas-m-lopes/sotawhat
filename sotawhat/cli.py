# sotawhat/cli.py
import argparse
import sys

_SUBCOMMANDS = {"search", "digest"}

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

    p_digest = sub.add_parser("digest")
    p_digest.add_argument("--profile", required=True)
    p_digest.add_argument("--vault", required=True)
    p_digest.add_argument("--limit", type=int, default=10)

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
    ns = parse_args(argv if argv is not None else sys.argv[1:])
    if ns.command == "search":
        _run_search(ns)
    elif ns.command == "digest":
        from sotawhat.digest import run_digest  # added in Phase 3
        run_digest(ns)

if __name__ == "__main__":
    main()

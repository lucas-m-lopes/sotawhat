# sotawhat/graph/commands.py
"""`sotawhat graph up|extract|sync|status|export` (SDD §6.12, P3)."""
import json
import sys
from pathlib import Path


def _mirror(settings):
    from sotawhat.graph.neo4j_sync import Neo4jMirror

    mirror = Neo4jMirror.from_settings(settings)
    if mirror is None:
        print("espelho Neo4j desligado: NEO4J_PASSWORD vazio no .env (a interface funciona sem ele)")
        return None
    if not mirror.ping():
        mirror.close()
        print(f"o Neo4j não responde em {settings.neo4j_uri}: rode `sotawhat graph up`", file=sys.stderr)
        return None
    return mirror


def main_graph(ns) -> int:
    from sotawhat.config import load_settings
    from sotawhat.graph import query
    from sotawhat.store.db import Store

    settings = load_settings()
    if ns.graph_action == "up":
        from sotawhat.graph.docker import graph_up

        ok, message = graph_up(settings, Path.cwd())
        print(message, file=sys.stdout if ok else sys.stderr)
        return 0 if ok else 1
    if ns.graph_action == "extract":
        from sotawhat.pipeline.daily import main_graph_extract

        return main_graph_extract(ns, settings)
    with Store(settings.db_path) as store:
        if ns.graph_action == "sync":
            mirror = _mirror(settings)
            if mirror is None:
                return 1 if settings.neo4j_password else 2
            try:
                stats = mirror.sync(store, rebuild=ns.rebuild)
            finally:
                mirror.close()
            print(f"Neo4j sincronizado: {stats.items} itens · {stats.entities} entidades · {stats.mentions} menções"
                  f" · {stats.relations} relações" + (f" · {stats.deleted} nós apagados antes" if stats.rebuilt else ""))
            return 0
        if ns.graph_action == "status":
            print(json.dumps(query.stats(store), ensure_ascii=False, indent=1))
            mirror = _mirror(settings)
            if mirror is not None:
                try:
                    print(f"Neo4j: {mirror.counts()}")
                finally:
                    mirror.close()
            return 0
        if ns.graph_action == "export":
            out = Path(ns.out) if ns.out else settings.sotawhat_data_dir / "exports"
            for path in query.export(store, out):
                print(path)
            return 0
    return 2

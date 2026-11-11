# sotawhat/mcp_server.py
"""`sotawhat serve-mcp`: the MCP server `sotawhat-graph` over stdio (SDD §6.11, US5), registered in
`.mcp.json` so Claude Code can ask the graph questions such as "what appeared about ambient scribes in
the last 30 days?". The tools read SQLite (one short connection per call) through graph/query.py and
ideation/ledger.py; `cypher` runs read-only Cypher on the Neo4j mirror. Nothing here writes (votes stay in
Telegram and in the interface), and nothing but the protocol goes to stdout."""
import re

from sotawhat.graph import intelligence as intel
from sotawhat.graph import query as q
from sotawhat.ideation import ledger
from sotawhat.store.db import Store

INSTRUCTIONS = (
    "Grafo pessoal de IA ∩ medicina e IA de fronteira do sotawhat. Entidades: técnicas, modelos, datasets, "
    "organizações, produtos, problemas e regulações extraídos dos itens que a triagem aprovou (seções 'IA ∩ "
    "Saúde', 'Fronteira de IA' e 'Radar'). Use search para achar nomes, entity e neighbors para explorar, "
    "recent_items para o que chegou num período e cypher para perguntas estruturais no espelho Neo4j "
    "(rótulos :Item e :Entity com :Technique, :Model, :Dataset, :Organization, :Product, :Problem, :Regulation; "
    "relações MENTIONS, USES, ADDRESSES, DEVELOPED_BY, EVALUATED_ON, COMPARED_WITH, BUILDS_ON, REGULATED_BY, "
    "IN_CATEGORY). Inteligência semanal: trends (o que subiu na semana e o mapa de comunidades), gaps (pares "
    "técnica × problema ainda sem ligação, a matéria-prima das ideias) e o ledger de ideias do motor de ideação "
    "(list_ideas e idea; status nova, curtida, testar, engavetada, construida, rejeitada ou descartada).")
_WRITE = re.compile(r"\b(CREATE|MERGE|DELETE|DETACH|SET|REMOVE|DROP|FOREACH|ALTER|RENAME|GRANT|DENY|REVOKE|"
                    r"LOAD\s+CSV|START\s+DATABASE|STOP\s+DATABASE)\b|\bCALL\s*\{|"
                    r"\bCALL\s+(dbms|db\.(create|drop|clear|index\.fulltext\.create)|apoc|gds|tx)\b", re.I)


def _entity_id(store, key):
    text = str(key or "").strip()
    if re.fullmatch(r"e?\d+", text):
        number = int(text.lstrip("e"))
        return number if store.get_entity(number) is not None else None
    hits = q.search(store, text, limit=10)["entities"]
    exact = [h for h in hits if h["name"].lower() == text.lower()]
    return (exact or hits)[0]["entity_id"] if (exact or hits) else None


def search_tool(db_path, query, limit=10) -> dict:
    with Store(db_path) as store:
        return q.search(store, query, limit=max(1, min(int(limit), 50)))


def entity_tool(db_path, name_or_id) -> dict:
    with Store(db_path) as store:
        entity_id = _entity_id(store, name_or_id)
        if entity_id is None:
            return {"error": f"entidade não encontrada: {name_or_id}; tente search"}
        return q.entity_detail(store, entity_id, items_limit=20)


def neighbors_tool(db_path, name_or_id, limit=20):
    with Store(db_path) as store:
        entity_id = _entity_id(store, name_or_id)
        if entity_id is None:
            return {"error": f"entidade não encontrada: {name_or_id}; tente search"}
        return q.neighbors(store, entity_id, limit=max(1, min(int(limit), 100)), types=q.ENTITY_TYPES)


def recent_items_tool(db_path, days=7, section="", topic="", limit=20) -> list:
    with Store(db_path) as store:
        entity_id = _entity_id(store, topic) if topic else None
        return q.recent_items(store, days=days or None, section=section or None, entity_id=entity_id,
                              text=None if entity_id is not None else (topic or None), limit=max(1, min(int(limit), 100)))


def graph_stats_tool(db_path) -> dict:
    with Store(db_path) as store:
        return q.stats(store)


def trends_tool(db_path) -> dict:
    with Store(db_path) as store:
        view = ledger.trends_view(store)
        return {"trends": view["trends"], "communities": view["communities"], "last_weekly_report": view["weekly"]}


def gaps_tool(db_path, limit=10) -> dict:
    with Store(db_path) as store:
        found = intel.gaps(store, limit=max(1, min(int(limit), 50)))
        return {name: [ledger.gap_pair(g) for g in pairs] for name, pairs in found.items()}


def list_ideas_tool(db_path, status="", finalists_only=True, limit=20) -> dict:
    if status and status not in ledger.STATUSES:
        return {"error": f"status inválido; use um de {', '.join(ledger.STATUSES)}"}
    with Store(db_path) as store:
        found = ledger.list_ideas(store, status=status or None, finalists_only=finalists_only,
                                  limit=max(1, min(int(limit), 100)))
        return {"ideas": [ledger.compact(c) for c in found["ideas"]], "counts": found["counts"]}


def idea_tool(db_path, idea_id) -> dict:
    with Store(db_path) as store:
        try:
            detail = ledger.idea_detail(store, int(str(idea_id).removeprefix("idea:")))
        except ValueError:
            detail = None
        return detail or {"error": f"ideia não encontrada: {idea_id}; tente list_ideas"}


def cypher_tool(db_path, query, limit=200, mirror_factory=None) -> dict:
    if _WRITE.search(query or ""):
        return {"error": "só consultas de leitura (MATCH ... RETURN); escrita e procedimentos administrativos são recusados"}
    mirror = mirror_factory() if mirror_factory else None
    if mirror is None:
        return {"error": "espelho Neo4j desligado: defina NEO4J_PASSWORD no .env e rode `sotawhat graph up`"}
    try:
        if not mirror.ping():
            return {"error": "o Neo4j não responde: rode `sotawhat graph up` e `sotawhat graph sync`"}
        rows, truncated = mirror.read(query, limit=max(1, min(int(limit), 1000)))
        return {"rows": rows, "truncated": truncated}
    except Exception as exc:  # noqa: BLE001 - Cypher errors go back to the caller as text
        return {"error": f"{type(exc).__name__}: {exc}"}
    finally:
        mirror.close()


def build_server(db_path, mirror_factory=None):
    from mcp.server import MCPServer

    server = MCPServer("sotawhat-graph", instructions=INSTRUCTIONS)

    @server.tool()
    def search(query: str, limit: int = 10) -> dict:
        """Busca entidades (nome ou alias) e itens aprovados (título ou resumo em pt-BR)."""
        return search_tool(db_path, query, limit)

    @server.tool()
    def entity(name_or_id: str) -> dict:
        """Uma entidade pelo nome, alias ou id (ex.: 'MedGemma 1.5', 'e12'): tipo, categoria, aliases, itens
        com resumo e seção, vizinhos, relações e números citados."""
        return entity_tool(db_path, name_or_id)

    @server.tool()
    def neighbors(name_or_id: str, limit: int = 20) -> list | dict:
        """Entidades que aparecem nos mesmos itens que esta, com o número de itens em comum (sem as categorias
        da triagem, que aparecem junto com quase tudo; elas vêm no campo neighbors de entity)."""
        return neighbors_tool(db_path, name_or_id, limit)

    @server.tool()
    def recent_items(days: int = 7, section: str = "", topic: str = "", limit: int = 20) -> list:
        """Itens aprovados dos últimos `days` dias (0 = todos), mais novos primeiro. section: main, frontier,
        radar ou o nome da seção; topic: uma entidade (nome) ou um texto livre."""
        return recent_items_tool(db_path, days, section, topic, limit)

    @server.tool()
    def graph_stats() -> dict:
        """Tamanho do grafo: itens, aprovados, extraídos, entidades por tipo, relações e sincronização."""
        return graph_stats_tool(db_path)

    @server.tool()
    def trends() -> dict:
        """O que subiu nos últimos 7 dias contra os 28 anteriores (z de Poisson; 'new' = apareceu agora) e as
        comunidades do grafo com o rótulo do último run semanal."""
        return trends_tool(db_path)

    @server.tool()
    def gaps(limit: int = 10) -> dict:
        """Lacunas do grafo (90 dias): técnicas recentes sem ligação com problemas frequentes, pontes entre
        comunidades e pares distantes (serendipidade). É a matéria-prima do motor de ideias."""
        return gaps_tool(db_path, limit)

    @server.tool()
    def list_ideas(status: str = "", finalists_only: bool = True, limit: int = 20) -> dict:
        """Ideias do ledger, do lote mais novo para o mais antigo. status: nova, curtida, testar, engavetada,
        construida, rejeitada ou descartada (vazio = todas); finalists_only=false inclui as não finalistas."""
        return list_ideas_tool(db_path, status, finalists_only, limit)

    @server.tool()
    def idea(idea_id: str) -> dict:
        """Uma ideia completa pelo id (ex.: '12' ou 'idea:12'): card, eixos da rubrica, novidade por faceta,
        vizinhos de prior art, críticas por papel, dossiê, fatos do grafo usados e histórico de votos."""
        return idea_tool(db_path, idea_id)

    @server.tool()
    def cypher(query: str, limit: int = 200) -> dict:
        """Cypher só leitura no espelho Neo4j (ex.: MATCH (m:Model)-[:DEVELOPED_BY]->(o:Organization)
        RETURN o.name, count(m) ORDER BY count(m) DESC LIMIT 10)."""
        return cypher_tool(db_path, query, limit, mirror_factory=mirror_factory)

    return server


def main_mcp(ns) -> int:
    from datetime import date

    from sotawhat.config import load_settings
    from sotawhat.graph.neo4j_sync import Neo4jMirror
    from sotawhat.pipeline.daily import setup_logging

    settings = load_settings()
    setup_logging(settings.sotawhat_data_dir, date.today().isoformat(), settings.sotawhat_log_level)
    build_server(settings.db_path, mirror_factory=lambda: Neo4jMirror.from_settings(settings)).run("stdio")
    return 0

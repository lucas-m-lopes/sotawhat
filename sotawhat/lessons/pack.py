# sotawhat/lessons/pack.py
"""The source pack of a lesson: the entities of the topic, the items the triage approved that mention them (with
the full text the collector keeps), and their graph neighbours as candidate prerequisites. The same pack goes to
the planner, to the fact gate and, as fontes.md, to the NotebookLM baseline."""
import json
from dataclasses import asdict, dataclass, field

from sotawhat.graph import query as q

LESSON_TYPES = ("technique", "problem", "model", "dataset")     # an organization or a product is not a process
SECTION_RANK = {"main": 0, "frontier": 1, "radar": 2}
ROLE_RANK = {"main": 0, "used": 1, "mentioned": 2, "tag": 3}


@dataclass
class Source:
    index: int
    item_id: str
    title: str
    url: str
    published: str
    summary_pt: str
    text: str


@dataclass
class Pack:
    topic: str
    entities: list = field(default_factory=list)     # [{"id", "name", "type"}]
    neighbors: list = field(default_factory=list)    # names of related entities
    sources: list = field(default_factory=list)      # [Source]

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=1)

    @classmethod
    def from_json(cls, text):
        data = json.loads(text)
        return cls(topic=data["topic"], entities=data["entities"], neighbors=data["neighbors"],
                   sources=[Source(**s) for s in data["sources"]])


def build_pack(store, topic, entity_ids=(), max_sources=8, chars=2500) -> Pack:
    """`entity_ids` empty: the entities whose name matches the topic (at most 3)."""
    ids = [int(e) for e in entity_ids] or [e["entity_id"] for e in q.search(store, topic, limit=3)["entities"]]
    pack, ranked, seen = Pack(topic=topic), [], set()
    neighbors = {}
    for eid in ids:
        detail = q.entity_detail(store, eid, items_limit=30)
        if detail is None:
            continue
        pack.entities.append({"id": eid, "name": detail["name"], "type": detail["type"]})
        for n in detail["neighbors"][:8]:
            if n["entity_id"] not in ids:
                neighbors[n["name"]] = neighbors.get(n["name"], 0) + n["shared"]
        for item in detail["items"]:
            if item["id"] not in seen:
                seen.add(item["id"])
                ranked.append(item)
    if not ranked:                                   # no entity: the approved items whose title or summary match
        ranked = q.search(store, topic, limit=max_sources)["items"]
    ranked.sort(key=lambda it: (ROLE_RANK.get(it.get("role"), 2), SECTION_RANK.get(it.get("decision"), 3),
                                -(len(it.get("summary_pt") or ""))))
    chosen = ranked[:max_sources]
    texts = {row["id"]: row["text"] or "" for row in store.get_items([it["id"] for it in chosen])}
    for n, it in enumerate(chosen):
        pack.sources.append(Source(index=n, item_id=it["id"], title=it["title"], url=it.get("url") or "",
                                   published=(it.get("published_at") or it.get("fetched_at") or "")[:10],
                                   summary_pt=it.get("summary_pt") or "", text=" ".join(texts.get(it["id"], "").split())[:chars]))
    pack.neighbors = [name for name, _ in sorted(neighbors.items(), key=lambda kv: -kv[1])[:10]]
    return pack


def pack_prompt(pack) -> str:
    lines = [f"Tema: {pack.topic}",
             "Entidades do grafo: " + (", ".join(f"{e['name']} ({e['type']})" for e in pack.entities) or "nenhuma"),
             "Vizinhos no grafo (candidatos a pré-requisito): " + (", ".join(pack.neighbors) or "nenhum"), "", "Fontes:"]
    for s in pack.sources:
        lines += [f"[{s.index}] {s.title} ({s.published}) {s.url}", f"resumo: {s.summary_pt}", f"texto: {s.text}", ""]
    if not pack.sources:
        lines.append("(nenhuma fonte aprovada; use só conhecimento canônico e marque source = -1)")
    return "\n".join(lines)


def pack_markdown(pack, plan=None) -> str:
    """fontes.md for the NotebookLM baseline: upload it and ask for a Video Overview (Explainer, pt-BR)."""
    out = [f"# {plan.title if plan else pack.topic}", ""]
    if plan:
        out += [f"Processo a explicar: {plan.process}", "", f"Objetivo: {plan.objective}", ""]
    out += ["Instrução para o Video Overview: explique em português do Brasil, para um médico que estuda IA, "
            "o processo acima passo a passo, usando só estas fontes e conhecimento canônico.", ""]
    for s in pack.sources:
        out += [f"## [{s.index}] {s.title}", f"{s.published} · {s.url}", "", s.text or s.summary_pt, ""]
    return "\n".join(out)


def pick_topic(store, min_sources=2):
    """The strongest trend of the latest weekly report that is a process-like entity, has sources and no lesson
    yet. -> (name, [entity_id]) or None."""
    report = store.latest_weekly_report("weekly") or store.latest_weekly_report()
    if not report:
        return None
    taught = store.taught_entities()
    for trend in sorted(report["payload"].get("trends") or [], key=lambda t: -(t.get("z") or 0)):
        eid = trend.get("entity_id")
        if eid is None or eid in taught or trend.get("type") not in LESSON_TYPES:
            continue
        detail = q.entity_detail(store, eid, items_limit=min_sources)
        if detail and len(detail["items"]) >= min_sources:
            return trend["name"], [eid]
    return None

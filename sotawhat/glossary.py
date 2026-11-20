# sotawhat/glossary.py
"""The glossary of the digests (SDD §17.2, 2026-11-20): the ML/AI terms of the day, one sentence each.

Each term is defined once, by the LLM, the first day a digest uses it; from then on it is found in the
texts with no LLM (`match`), so the cost falls as the glossary fills. A digest prints at most `limit` terms
of its own texts: the new ones first, then the ones it printed the fewest times, and never a term that was
already printed `repeats` times or that you marked "já sei" (those stay in the Glossário tab of the
interface, which lists them all). A term whose name is a technique of the graph points to it.

Medical terms, product names and model names stay out: the prompt asks for concepts only, and a term the
LLM returns without it being written in the texts is dropped."""
import json
import logging
import re

from sotawhat.graph.resolve import _singular, normalize
from sotawhat.llm.gateway import BudgetExceeded, LLMFailure
from sotawhat.llm.openrouter import InsufficientCredits
from sotawhat.llm.prompts import load as load_prompt
from sotawhat.llm.schemas import GlossaryBatch
from sotawhat.textmatch import fold

PROMPT_VERSION = "glossary_v1"
STATUSES = ("ativo", "conhecido")
SKIP = {"ai", "ia", "artificial intelligence", "inteligencia artificial"}
MAX_TERM, MAX_WORDS = 60, 45
_WORD = re.compile(r"[^\W_]+")
log = logging.getLogger("sotawhat.glossary")


def norm(term) -> str:
    """The identity of a term, the same key the graph gives a technique: "Embeddings" is "embedding"."""
    return normalize(" ".join(str(term or "").split()), "technique")


def _acronym(surface) -> bool:
    return len(surface) <= 6 and surface.isupper() and " " not in surface


def _tokens(text) -> list:
    return [(fold(w), fold(_singular(w))) for w in _WORD.findall(text or "")]


def occurs(surface, text, tokens=None) -> bool:
    """Whether a spelling of a term is written in the text. An acronym needs its capitals ("MAS" is not the
    Portuguese "mas"); anything else matches without case, accents, hyphens or the plural."""
    surface = " ".join(str(surface or "").split())
    if not surface:
        return False
    if _acronym(surface):
        return re.search(rf"(?<![\w-]){re.escape(surface)}s?(?![\w-])", text or "") is not None
    want = norm(surface).split()
    tokens = _tokens(text) if tokens is None else tokens
    return bool(want) and any(all(want[k] in tokens[i + k] for k in range(len(want)))
                              for i in range(len(tokens) - len(want) + 1))


def surfaces(row) -> list:
    return [s for s in [row["term"], row["expansion"], *json.loads(row["aliases_json"] or "[]")] if s]


def match(rows, texts) -> dict:
    """{term id: [item ids]} of the glossary terms written in the texts; `texts` is [(item id, text)]."""
    tokenized = [(item_id, text, _tokens(text)) for item_id, text in texts]
    found = {}
    for row in rows:
        spellings = surfaces(row)
        items = [item_id for item_id, text, tokens in tokenized if any(occurs(s, text, tokens) for s in spellings)]
        if items:
            found[row["id"]] = items
    return found


def system_prompt(limit) -> str:
    return load_prompt(PROMPT_VERSION).replace("{{LIMIT}}", str(limit))


def messages_for(texts, known, limit) -> list:
    have = ", ".join(sorted({row["term"] for row in known}, key=str.lower)) or "(nenhum ainda)"
    body = "\n\n".join(f"[{n}] {text}" for n, (_, text) in enumerate(texts, 1))
    return [{"role": "system", "content": system_prompt(limit)},
            {"role": "user", "content": f"Termos que o glossário já tem (não repita):\n{have}\n\nTextos de hoje:\n{body}"}]


def _entity(store, names):
    """The technique of the graph that one of these names leads to, if any."""
    for name in names:
        key = norm(name)
        row = store.entity_by_alias("technique", key) if key else None
        if row is not None:
            return row["id"]
    return None


def generate(store, gateway, texts, limit) -> dict:
    """Asks the LLM for the terms of the texts the glossary lacks and stores them. -> {term id: [item ids]}."""
    known = store.glossary_terms()
    by_norm = {}
    for row in known:
        for spelling in surfaces(row):
            by_norm.setdefault(norm(spelling), row["id"])
    res = gateway.structured_call("glossary", messages_for(texts, known, limit), GlossaryBatch)
    tokenized = [(item_id, text, _tokens(text)) for item_id, text in texts]
    created = {}
    for entry in res.output.termos[:limit]:
        term = " ".join(entry.termo.split()).strip(" .,:;\"'")
        definition = " ".join(entry.definicao.split())
        key = norm(term)
        if not key or key in SKIP or len(term) > MAX_TERM or not definition or len(definition.split()) > MAX_WORDS:
            continue
        variants = [" ".join(v.split()) for v in entry.variantes if v and v.strip()][:4]
        items = [item_id for item_id, text, tokens in tokenized
                 if any(occurs(s, text, tokens) for s in [term, *variants])]
        if not items:                       # the LLM named a term that the texts do not write
            log.info("glossary: '%s' is not in today's texts, skipped", term)
            continue
        existing = by_norm.get(key) or next((by_norm[norm(v)] for v in variants if norm(v) in by_norm), None)
        if existing is not None:            # another spelling of a term the glossary has
            store.add_glossary_aliases(existing, [term, *variants])
            created.setdefault(existing, [])
            created[existing] += [i for i in items if i not in created[existing]]
            continue
        expansion = " ".join(entry.sigla_de.split()) or None
        if not definition.endswith((".", "!", "?")):
            definition += "."
        term_id, new = store.add_glossary_term(
            term, key, definition, expansion=expansion, aliases=[v for v in variants if norm(v) != key],
            entity_id=_entity(store, [term, expansion, *variants]), model=res.model, prompt_version=PROMPT_VERSION)
        for spelling in [term, expansion, *variants]:
            if spelling:
                by_norm.setdefault(norm(spelling), term_id)
        created[term_id] = items
    return created


def build(store, gateway, digest, limit=8, repeats=3, new=10) -> list:
    """The glossary of one digest: [{"id", "term", "expansion", "definition", "new"}]. Never raises: with no
    LLM, or when its call fails, the digest still gets the terms the glossary already knows."""
    entries = list(digest.main) + list(digest.frontier)
    if not entries or limit <= 0:
        return []
    texts = [(e.item_id, f"{e.title}. {e.summary} {e.why}") for e in entries]
    try:
        found = match(store.glossary_terms(), texts)
        fresh = set()
        if gateway is not None and new > 0:
            try:
                created = generate(store, gateway, texts, new)
            except (LLMFailure, BudgetExceeded, InsufficientCredits) as exc:
                log.warning("glossary: %s", exc)
                created = {}
            fresh = set(created) - set(found)
            for term_id, items in created.items():
                found[term_id] = sorted(set(found.get(term_id, [])) | set(items))
        for term_id, items in found.items():
            store.link_glossary_items(term_id, items, digest.day)
        rows = {row["id"]: row for row in store.glossary_terms()}
        picked = [rows[i] for i in found if i in rows and rows[i]["status"] == "ativo"
                  and (rows[i]["shown_count"] < repeats or rows[i]["last_shown"] == digest.day)]
        picked.sort(key=lambda r: (r["id"] not in fresh, r["shown_count"], -len(found[r["id"]]), r["norm"]))
        return [{"id": r["id"], "term": r["term"], "expansion": r["expansion"], "definition": r["definition_pt"],
                 "new": r["id"] in fresh} for r in picked[:limit]]
    except Exception:  # noqa: BLE001 - the glossary is an extra: the digest goes out without it
        log.exception("glossary")
        return []


def mark_shown(store, digest) -> None:
    store.mark_glossary_shown([g["id"] for g in getattr(digest, "glossary", [])], digest.day)


def view(store, text="", status="") -> dict:
    """What the Glossário tab and the MCP show: every term, in alphabetical order, with where it appeared."""
    rows = store.glossary_terms()
    counts = {s: sum(1 for r in rows if r["status"] == s) for s in STATUSES}
    wanted = fold(text.strip()) if text else ""
    if status:
        rows = [r for r in rows if r["status"] == status]
    if wanted:
        rows = [r for r in rows if wanted in fold(" ".join(surfaces(r))) or wanted in fold(r["definition_pt"])]
    seen = {}
    for term_id, n, last in store.conn.execute("SELECT term_id, COUNT(*), MAX(day) FROM glossary_items GROUP BY term_id"):
        seen[term_id] = (n, last)
    latest = {}
    for row in store.conn.execute(
            "SELECT g.term_id, i.id, i.title, g.day FROM glossary_items g JOIN items i ON i.id = g.item_id"
            " ORDER BY g.day DESC, i.fetched_at DESC"):
        if len(latest.setdefault(row[0], [])) < 3:
            latest[row[0]].append({"id": row[1], "title": row[2], "day": row[3]})
    names = dict(store.conn.execute("SELECT id, name FROM entities WHERE id IN (SELECT entity_id FROM glossary"
                                    " WHERE entity_id IS NOT NULL)").fetchall())
    terms = [{"id": r["id"], "term": r["term"], "expansion": r["expansion"], "definition": r["definition_pt"],
              "aliases": json.loads(r["aliases_json"] or "[]"), "status": r["status"],
              "entity_id": r["entity_id"] if r["entity_id"] in names else None, "entity": names.get(r["entity_id"]),
              "created_at": r["created_at"], "shown_count": r["shown_count"], "last_shown": r["last_shown"],
              "items": seen.get(r["id"], (0, None))[0], "last_seen": seen.get(r["id"], (0, None))[1],
              "latest": latest.get(r["id"], [])} for r in rows]
    terms.sort(key=lambda t: fold(t["term"]))
    return {"terms": terms, "total": sum(counts.values()), "counts": counts}


# --- the digests already sent, and the command ---------------------------------------------
def digest_of_run(store, run_id):
    """What a daily run delivered in its two main sections, as much of a digest as `build` reads."""
    from types import SimpleNamespace

    rows = store.conn.execute(
        "SELECT d.section, d.day, i.id, i.title, t.summary_pt, t.why_it_matters_pt FROM deliveries d"
        " JOIN items i ON i.id = d.item_id JOIN triage t ON t.item_id = i.id"
        " WHERE d.run_id = ? AND d.section IN ('main', 'frontier') ORDER BY d.position", (run_id,)).fetchall()
    entries = {"main": [], "frontier": []}
    for r in rows:
        entries[r["section"]].append(SimpleNamespace(item_id=r["id"], title=r["title"], summary=r["summary_pt"] or "",
                                                     why=r["why_it_matters_pt"] or ""))
    return SimpleNamespace(day=rows[0]["day"] if rows else None, main=entries["main"], frontier=entries["frontier"])


def backfill(store, gateway, days=14, new=10, today=None) -> dict:
    """Defines the terms of the digests of the last `days` days, oldest first, so the Glossário tab starts
    filled. Nothing here counts as printed in a digest."""
    from datetime import date, timedelta

    since = ((today or date.today()) - timedelta(days=days)).isoformat()
    runs = [r[0] for r in store.conn.execute(
        "SELECT run_id FROM deliveries WHERE section IN ('main', 'frontier') AND day >= ? AND run_id IS NOT NULL"
        " GROUP BY run_id ORDER BY MIN(day), run_id", (since,))]
    before = len(store.glossary_terms())
    for run_id in runs:
        if gateway is not None:
            gateway.run_id = run_id
        build(store, gateway, digest_of_run(store, run_id), limit=10 ** 6, repeats=10 ** 6, new=new)
    return {"digests": len(runs), "new": len(store.glossary_terms()) - before, "total": len(store.glossary_terms())}


def main_glossary(ns) -> int:
    """`sotawhat glossary list|backfill [--dias N]`."""
    import sys

    from sotawhat.config import load_settings
    from sotawhat.configfiles import ConfigError, load_config
    from sotawhat.llm.gateway import LLMGateway
    from sotawhat.llm.openrouter import OpenRouterClient
    from sotawhat.store.db import Store

    settings = load_settings()
    with Store(settings.db_path) as store:
        if ns.glossary_action == "list":
            found = view(store)
            for t in found["terms"]:
                name = f"{t['term']} ({t['expansion']})" if t["expansion"] else t["term"]
                print(f"{name}: {t['definition']}" + (" [já sei]" if t["status"] == "conhecido" else ""))
            print(f"\n{found['total']} termos · {found['counts']['conhecido']} marcados como já sei")
            return 0
        try:
            config = load_config(settings.sotawhat_config_dir)
        except ConfigError as exc:
            print(f"[config] {exc}", file=sys.stderr)
            return 2
        if not settings.openrouter_api_key:
            print("sem OPENROUTER_API_KEY: o glossário só reconhece os termos que já tem", file=sys.stderr)
            return 2
        client = OpenRouterClient(settings.openrouter_api_key, base_url=settings.openrouter_base_url,
                                  app_title=settings.openrouter_app_title)
        gateway = LLMGateway(client, store=store, settings=settings, tasks=config.llm["tasks"])
        done = backfill(store, gateway, days=ns.dias, new=config.digest.glossary_new)
    print(f"glossário: {done['digests']} digests lidos · {done['new']} termos novos · {done['total']} no total")
    return 0

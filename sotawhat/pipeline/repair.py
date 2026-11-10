# sotawhat/pipeline/repair.py
"""`sotawhat repair cjk|names`: stored rows written by an older rule.

cjk (P6): before the P1 bake-off, MiniMax-M3.1-Flash triaged one run and slipped CJK tokens into the pt-BR
summaries ("orientar和质量 improvement"). The validator stops that since then, but those texts stayed in the store,
where the interface, the graph and the idea engine read them. The repair asks the current triage chain for
the item again and keeps only the texts: decision, scores and total stay as they were, so nothing is
delivered twice.

names (2026-11-10): until then the resolver cut the s of the last word of every technique and problem name, also
when it was no plural ("AI bias" → "AI bia", "CAMS" → "CAM", "Harness-S" → "Harness-") or no head ("mixture of
experts" → "mixture of expert"). The repair finds what that rule wrote from the raw names kept in the extractions
and moves names and keys to the current rule (graph/resolve.py), so new extractions meet the same entities."""
import json

import numpy as np

from sotawhat.graph.resolve import SINGULAR_TYPES, display_name, group, normalize, split_acronym
from sotawhat.items import from_row
from sotawhat.llm.gateway import BudgetExceeded, LLMFailure
from sotawhat.llm.openrouter import InsufficientCredits
from sotawhat.llm.schemas import _CJK, TriageOutput
from sotawhat.pipeline.triage import PROMPT_VERSION, messages_for

FIELDS = ("summary_pt", "why_it_matters_pt", "reason")


def cjk_rows(store) -> list:
    rows = store.conn.execute("SELECT t.*, i.title FROM triage t JOIN items i ON i.id = t.item_id").fetchall()
    return [r for r in rows if any(_CJK.search(r[f] or "") for f in FIELDS)]


def repair_cjk(store, gateway, rubric) -> dict:
    """-> {"found", "fixed", "failed", "stopped"}."""
    rows = cjk_rows(store)
    out = {"found": len(rows), "fixed": 0, "failed": 0, "stopped": None}
    for row in rows:
        item = from_row(store.conn.execute("SELECT * FROM items WHERE id = ?", (row["item_id"],)).fetchone())
        try:
            res = gateway.structured_call("triage", messages_for(item, rubric), TriageOutput)
        except (BudgetExceeded, InsufficientCredits) as exc:
            out["stopped"] = str(exc)
            break
        except LLMFailure:
            out["failed"] += 1
            continue
        why = res.output.why_it_matters_pt if row["why_it_matters_pt"] else ""
        with store._lock:
            store.conn.execute("UPDATE triage SET summary_pt = ?, why_it_matters_pt = ?, reason = ?, prompt_version = ? "
                               "WHERE item_id = ?", (res.output.summary_pt, why, res.output.reason_pt,
                                                    f"{PROMPT_VERSION}+repair", row["item_id"]))
            store.conn.commit()
        out["fixed"] += 1
    return out


# --- names -----------------------------------------------------------------------------------------------------
_NOT_PLURAL_V1 = {"diabetes", "herpes", "measles", "rabies", "scabies", "mumps", "series", "species", "news", "lens",
                  "aids", "lupus"}


def _singular_v1(word) -> str:
    lower = word.lower()
    if len(word) <= 3 or lower in _NOT_PLURAL_V1:
        return word
    if lower.endswith("ies"):
        return word[:-3] + "y"
    return word[:-1] if lower.endswith("s") and not lower.endswith(("ss", "us", "is", "ics")) else word


def names_v1(name, type_) -> tuple:
    """(display name, key) as the resolver wrote them until 2026-11-10, kept only to find those rows."""
    words, key = name.split(), normalize(name).split()
    if type_ in SINGULAR_TYPES:
        if words:
            words[-1] = _singular_v1(words[-1])
        if key:
            key[-1] = _singular_v1(key[-1])
    return " ".join(words), " ".join(key)


def name_fixes(store, aliases=None) -> tuple:
    """({(group, old key, new key): {old display name: new display name}}, {(group, key) that the current rule
    writes for some raw name}), from the raw technique and problem names in the extractions (with their acronyms)
    and in config/aliases.yaml."""
    raws = []
    for (payload,) in store.conn.execute("SELECT payload_json FROM extractions WHERE status = 'ok'"):
        for ent in json.loads(payload or "{}").get("entities", []):
            if ent.get("type") in SINGULAR_TYPES:
                base, acronym = split_acronym(ent.get("name") or "")
                raws += [(ent["type"], base)] + ([(ent["type"], acronym)] if acronym else [])
    for type_, table in (aliases or {}).items():
        if type_ in SINGULAR_TYPES:
            raws += [(type_, raw) for canonical, names in table.items() for raw in [canonical] + list(names)]
    fixes, current = {}, set()
    for type_, raw in raws:
        (old_name, old_key), new_name, new_key = names_v1(raw, type_), display_name(raw, type_), normalize(raw, type_)
        current.add((group(type_), new_key))
        if (old_name, old_key) != (new_name, new_key):
            fixes.setdefault((group(type_), old_key, new_key), {})[old_name] = new_name
    return fixes, current


def repair_names(store, embedder=None, dry_run=False, aliases=None) -> dict:
    """-> {"renamed": [{"id", "type", "name": (old, new), "norm": (old, new)}], "rekeyed": aliases moved,
    "clashes": [(old key, new key, owner id)], "items": items to send to the mirror again}. A new key that already
    belongs to another entity is reported and left alone: merging is the judge's call."""
    fixes, current = name_fixes(store, aliases)
    out, stale, conn = {"renamed": [], "rekeyed": 0, "clashes": [], "items": 0}, set(), store.conn
    for (grp, old_key, new_key), names in sorted(fixes.items()):
        hit = store.entity_by_alias(grp, old_key)
        if hit is None:                                  # a dropped name (generic, too long) or repaired already
            continue
        owner = store.entity_by_alias(grp, new_key)
        taken = conn.execute("SELECT id FROM entities WHERE type = ? AND norm = ? AND id != ?",
                             (hit["type"], new_key, hit["id"])).fetchone()
        if (owner is not None and owner["id"] != hit["id"]) or taken is not None:
            out["clashes"].append((old_key, new_key, owner["id"] if owner is not None else taken[0]))
            continue
        name, norm = names.get(hit["name"], hit["name"]), new_key if hit["norm"] == old_key else hit["norm"]
        if (name, norm) != (hit["name"], hit["norm"]):
            out["renamed"].append({"id": hit["id"], "type": hit["type"], "name": (hit["name"], name),
                                   "norm": (hit["norm"], norm)})
        out["rekeyed"] += old_key != new_key
        if dry_run:
            continue
        with store._lock:
            row = conn.execute("SELECT alias FROM entity_aliases WHERE grp = ? AND alias_norm = ?",
                               (grp, old_key)).fetchone()
            alias = names.get(row["alias"], row["alias"]) if row is not None else name
            if old_key == new_key:
                conn.execute("UPDATE entity_aliases SET alias = ? WHERE grp = ? AND alias_norm = ?", (alias, grp, old_key))
            else:
                conn.execute("INSERT OR IGNORE INTO entity_aliases(grp, alias_norm, entity_id, alias) VALUES(?,?,?,?)",
                             (grp, new_key, hit["id"], alias))
                if (grp, old_key) not in current:
                    stale.add((grp, old_key))
            conn.execute("UPDATE entities SET name = ?, norm = ? WHERE id = ?", (name, norm, hit["id"]))
            conn.commit()
    if dry_run:
        return out
    ids = sorted({r["id"] for r in out["renamed"]})     # the mirror keeps name and norm, not the aliases
    with store._lock:
        conn.executemany("DELETE FROM entity_aliases WHERE grp = ? AND alias_norm = ?", sorted(stale))
        if ids:
            cur = conn.execute("UPDATE items SET graph_synced_at = NULL WHERE id IN (SELECT DISTINCT item_id FROM"
                               f" entity_mentions WHERE entity_id IN ({','.join('?' * len(ids))}))", ids)
            out["items"] = cur.rowcount
        conn.commit()
    named = {r["id"]: (r["type"], r["name"][1]) for r in out["renamed"] if r["name"][0] != r["name"][1]}
    if embedder is not None and named:
        vectors = embedder.embed([f"{type_}: {name}" for type_, name in named.values()])
        store.save_entity_embeddings(embedder.name, [(eid, np.asarray(vec, dtype=np.float32))
                                                     for eid, vec in zip(named, vectors)])
    return out


def main_repair_names(settings, dry_run=False) -> int:
    from sotawhat.configfiles import ConfigError, load_aliases
    from sotawhat.store.db import Store
    from sotawhat.store.vectors import get_embedder

    path = settings.sotawhat_config_dir / "aliases.yaml"
    try:
        aliases = load_aliases(path) if path.exists() else {}
    except ConfigError as exc:
        print(f"[config] {exc}")
        return 2
    with Store(settings.db_path) as store:
        try:
            embedder = None if dry_run else get_embedder(settings)
        except Exception as exc:  # noqa: BLE001 - the names are fixed anyway; the vectors stay as they were
            print(f"[embeddings] {exc}: vetores mantidos")
            embedder = None
        result = repair_names(store, embedder=embedder, dry_run=dry_run, aliases=aliases)
    for r in result["renamed"]:
        (old, new), (old_key, new_key) = r["name"], r["norm"]
        print(f"  {r['id']}: {old} → {new}" if old != new else f"  {r['id']}: {old} (chave «{old_key}» → «{new_key}»)")
    for old_key, new_key, owner in result["clashes"]:
        print(f"  colisão: «{old_key}» → «{new_key}» já é da entidade {owner} (fica para o juiz)")
    print(f"{len(result['renamed'])} nomes corrigidos · {result['rekeyed']} chaves movidas · {len(result['clashes'])}"
          f" colisões" + (" (simulação: nada foi gravado)" if dry_run else f" · {result['items']} itens a reenviar"
                                                                            " ao Neo4j (`sotawhat graph sync`)"))
    return 0


def main_repair(ns) -> int:
    from datetime import date

    from sotawhat.config import load_settings
    from sotawhat.configfiles import ConfigError, load_config
    from sotawhat.llm.gateway import LLMGateway
    from sotawhat.llm.openrouter import OpenRouterClient
    from sotawhat.pipeline.daily import setup_logging
    from sotawhat.store.db import Store

    settings = load_settings()
    setup_logging(settings.sotawhat_data_dir, date.today().isoformat(), settings.sotawhat_log_level)
    if ns.repair_action == "names":
        return main_repair_names(settings, dry_run=getattr(ns, "dry_run", False))
    try:
        config = load_config(settings.sotawhat_config_dir)
    except ConfigError as exc:
        print(f"[config] {exc}")
        return 2
    with Store(settings.db_path) as store:
        found = cjk_rows(store)
        print(f"{len(found)} itens com caracteres CJK nos textos da triagem")
        if not found or not settings.openrouter_api_key:
            return 0 if not found else 2
        gateway = LLMGateway(OpenRouterClient(settings.openrouter_api_key, base_url=settings.openrouter_base_url,
                                              app_title=settings.openrouter_app_title),
                             store=store, settings=settings, tasks=config.llm["tasks"])
        result = repair_cjk(store, gateway, config.rubric)
    print(f"corrigidos {result['fixed']} · falharam {result['failed']}"
          + (f" · interrompido: {result['stopped']}" if result["stopped"] else ""))
    return 0 if not result["failed"] and not result["stopped"] else 1

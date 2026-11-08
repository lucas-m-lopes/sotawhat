# sotawhat/pipeline/repair.py
"""`sotawhat repair cjk` (P6): triage texts with Chinese, Japanese or Korean characters.

Before the P1 bake-off, MiniMax-M3.1-Flash triaged one run and slipped CJK tokens into the pt-BR summaries
("orientar和质量 improvement"). The validator stops that since then, but those texts stayed in the store,
where the interface, the graph and the idea engine read them. The repair asks the current triage chain for
the item again and keeps only the texts: decision, scores and total stay as they were, so nothing is
delivered twice."""
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

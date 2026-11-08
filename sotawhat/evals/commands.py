# sotawhat/evals/commands.py
"""`sotawhat eval golden draft|import` and `sotawhat eval models`."""
from datetime import date
from pathlib import Path


def main_golden(ns) -> int:
    from sotawhat.config import load_settings
    from sotawhat.evals.golden import from_store, import_labels, sample, write_draft
    from sotawhat.store.db import Store

    folder = Path(ns.dir)
    if ns.action == "import":
        report = import_labels(folder, ns.name)
        print(f"rotulados {report['labeled']} · sem rótulo {report['unlabeled']}")
        for bad in report["invalid"]:
            print(f"rótulo inválido (use incluir, radar ou excluir): {bad}")
        return 1 if report["invalid"] else 0
    if (folder / f"{ns.name}.md").exists() and not ns.force:
        print(f"{folder / (ns.name + '.md')} já existe (pode ter rótulos seus); use --force para sobrescrever")
        return 2
    settings = load_settings()
    with Store(settings.db_path) as store:
        candidates = from_store(store)
    entries = sample(candidates, ns.n, seed=ns.seed)
    md, _ = write_draft(entries, folder, ns.name)
    print(f"{len(entries)} itens em {md}: rotule e rode `sotawhat eval golden import`")
    return 0


def main_models(ns) -> int:
    import json
    from dataclasses import asdict

    from sotawhat.config import load_settings
    from sotawhat.configfiles import load_config
    from sotawhat.evals.bakeoff import (apply_winner, evaluate_model, metrics, model_costs, pick_winner, ranking,
                                        render_report)
    from sotawhat.evals.golden import load_golden
    from sotawhat.llm.gateway import BudgetExceeded, LLMGateway
    from sotawhat.llm.openrouter import InsufficientCredits, OpenRouterClient
    from sotawhat.llm.tasks import resolve
    from sotawhat.pipeline.triage import DEFAULT_COST_PER_ITEM
    from sotawhat.store.db import Store

    settings = load_settings()
    config = load_config(settings.sotawhat_config_dir)
    golden = load_golden(ns.golden)[:ns.limit or None]
    if not golden:
        print("golden set sem rótulos: rode `sotawhat eval golden draft`, rotule o .md e `sotawhat eval golden import`")
        return 2
    if not settings.openrouter_api_key:
        print("sem OPENROUTER_API_KEY no .env")
        return 2
    spec = resolve(ns.task, settings, config.llm["tasks"])
    candidates = ns.models.split(",") if ns.models else (config.llm["bakeoff"].get(ns.task) or list(spec.models))
    results, outcomes = {}, {}
    with Store(settings.db_path) as store:
        run_id = store.start_run("eval")
        client = OpenRouterClient(settings.openrouter_api_key, base_url=settings.openrouter_base_url,
                                  app_title=settings.openrouter_app_title)
        gateway = LLMGateway(client, store=store, settings=settings, run_id=run_id, tasks=config.llm["tasks"])
        estimate = (store.avg_llm_cost(ns.task) or DEFAULT_COST_PER_ITEM) * len(candidates) * len(golden)
        print(f"bake-off {ns.task}: {len(candidates)} modelos × {len(golden)} itens · estimativa ≈ US$ {estimate:.2f}")
        try:
            for model in candidates:
                outcomes[model] = evaluate_model(gateway, golden, config.rubric, model, ns.concurrency)
                results[model] = metrics(outcomes[model])
                r = results[model]
                print(f"  {model}: F1 {r['f1']:.2f} · acurácia {100 * r['accuracy']:.0f}% · "
                      f"JSON de 1ª {100 * r['valid_first_try']:.0f}% · falhas {r['failures']}")
        except (BudgetExceeded, InsufficientCredits) as exc:
            print(f"interrompido: {exc}")
        for model, cost in model_costs(store, run_id).items():
            if model in results:
                results[model]["cost_usd"] = cost
        store.finish_run(run_id, ok=bool(results), stats={"task": ns.task, "models": list(results),
                                                          "golden": len(golden)})
    winner = pick_winner(results)
    folder = settings.sotawhat_data_dir / "evals"
    folder.mkdir(parents=True, exist_ok=True)
    out = folder / f"{date.today().isoformat()}-{ns.task}-bakeoff.md"
    out.write_text(render_report(ns.task, date.today().isoformat(), results, outcomes, golden, winner), encoding="utf-8")
    rows = [{"model": m, **asdict(o)} for m, items in outcomes.items() for o in items]
    (folder / f"{date.today().isoformat()}-{ns.task}-outcomes.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")   # for calibration
    print(f"[relatório] {out}\nvencedor: {winner or 'nenhum'}")
    if ns.apply and winner:
        apply_winner(settings.sotawhat_config_dir / "llm.yaml", ns.task, ranking(results, winner),
                     spec.reasoning, spec.max_tokens)
        print(f"config/llm.yaml: {ns.task} agora começa por {winner}")
    return 0 if results else 1


def main_eval(ns) -> int:
    return main_golden(ns) if ns.eval_command == "golden" else main_models(ns)

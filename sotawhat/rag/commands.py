# sotawhat/rag/commands.py
"""`sotawhat ask "pergunta"` and `sotawhat rag index|status|up|eval` (SDD §6.15)."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def build(settings, store, rerank=True):
    """-> (retriever, slm) from the settings: the same pieces for the command, the interface and the MCP."""
    from sotawhat.rag.answer import from_settings
    from sotawhat.rag.retrieve import Retriever, get_reranker
    from sotawhat.store.vectors import get_embedder

    return Retriever(store, get_embedder(settings), get_reranker(settings) if rerank else None), from_settings(settings)


def render(answer, verbose=False) -> str:
    pack = answer.pack
    out = []
    if answer.text:
        out += [answer.text, ""]
    elif answer.error:
        out += [f"[sem resposta do SLM] {answer.error}", ""]
    out += [f"⚠️ {w}" for w in answer.warnings] + ([""] if answer.warnings else [])
    if pack.entities:
        out.append("Entidades: " + ", ".join(f"{e.name} ({e.type}, por {e.how})" for e in pack.entities))   # nome | sentido | fontes
    if pack.facts and (verbose or not answer.text):
        out += ["", "Fatos do grafo:"] + pack.facts
    if pack.sources:
        out += ["", "Fontes:"]
        for s in pack.sources:
            mark = "*" if s.n in answer.cited else " "
            where = " ".join(f"{name}#{rank}" for name, rank in s.channels.items())
            out.append(f"{mark}[{s.n}] {s.title[:110]} ({s.source}, {s.day[:10]}, {s.section})")
            if verbose:
                out.append(f"      {s.url}  ·  nota {s.score}"
                           + (f" · relevância {s.relevance}" if s.relevance is not None else "") + f" · {where}")
            elif not answer.text and s.summary:
                out.append(f"      {s.summary[:300]}")
    for note in pack.notes:
        out.append(f"({note})")
    t = pack.timings
    out.append(f"({answer.model or 'sem SLM'} · busca {t.get('total', 0):.1f} s"
               + (f" · resposta {answer.seconds:.1f} s" if answer.text and answer.model else "") + ")")
    return "\n".join(out)


def main_ask(ns) -> int:
    from sotawhat.config import load_settings
    from sotawhat.rag.answer import ask
    from sotawhat.store.db import Store

    settings = load_settings()
    question = " ".join(ns.question).strip()
    if not question:
        print('use: sotawhat ask "o que saiu sobre agentes clínicos esta semana?"', file=sys.stderr)
        return 2
    with Store(settings.db_path) as store:
        retriever, slm = build(settings, store, rerank=not ns.sem_rerank)
        answer = ask(retriever, None if ns.so_fontes else slm, question, days=ns.dias, k=ns.k or settings.rag_sources,
                     budget=settings.rag_context_chars)
    if ns.json:
        print(json.dumps(answer.as_dict(), ensure_ascii=False, indent=1))
    else:
        if ns.so_fontes:
            answer.error = None
        print(render(answer, verbose=ns.detalhes))
    return 0


def slm_up(settings, repo_dir, run=subprocess.run, sleep=time.sleep, ping=None, wait=120, step=3) -> tuple:
    """Starts the `ollama` service of compose.yaml, waits for it and pulls SLM_MODEL when it is missing.
    -> (ok, message). Like `graph up`, compose never reads the project `.env`."""
    from sotawhat.graph.docker import docker_ready
    from sotawhat.rag.answer import from_settings

    if not docker_ready(run):
        return False, "o Docker não responde: abra o Docker Desktop (ou aponte SLM_BASE_URL para outro servidor)"
    empty = Path(settings.sotawhat_data_dir) / "compose.env"
    empty.parent.mkdir(parents=True, exist_ok=True)
    empty.write_text("", encoding="utf-8")
    env = {**os.environ, "NEO4J_PASSWORD": settings.neo4j_password or "unused", "SLM_CONTEXT": str(settings.slm_context),
           "SLM_KEEP_ALIVE": settings.slm_keep_alive}
    try:
        up = run(["docker", "compose", "--env-file", str(empty), "up", "-d", "ollama"], cwd=repo_dir, env=env,
                 capture_output=True, text=True, timeout=1800)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"docker compose falhou: {exc}"
    if up.returncode != 0:
        return False, f"docker compose falhou: {(up.stderr or up.stdout or '').strip()[-400:]}"
    slm = from_settings(settings)
    ping = ping or slm.ping
    waited, (ok, detail) = 0, ping()
    while not ok and "não responde" in detail and waited < wait:
        sleep(step)
        waited += step
        ok, detail = ping()
    if not ok and "não está no servidor" in detail:
        pull = run(["docker", "exec", "sotawhat-ollama", "ollama", "pull", settings.slm_model], capture_output=True,
                   text=True, timeout=7200)
        if pull.returncode != 0:
            return False, f"não consegui baixar {settings.slm_model}: {(pull.stderr or pull.stdout or '').strip()[-300:]}"
        ok, detail = ping()
    return ok, (f"SLM no ar: {detail}" if ok else detail)


def main_rag(ns) -> int:
    from sotawhat.config import load_settings
    from sotawhat.rag import index
    from sotawhat.store.db import Store
    from sotawhat.store.vectors import get_embedder

    settings = load_settings()
    if ns.rag_action == "up":
        ok, message = slm_up(settings, Path.cwd())
        print(message, file=sys.stdout if ok else sys.stderr)
        return 0 if ok else 1
    if ns.rag_action == "eval":
        return main_eval(ns, settings)
    with Store(settings.db_path) as store:
        if ns.rag_action == "index":
            started = time.time()

            def progress(done):
                if done % 320 == 0:
                    print(f"  {done} passagens com vetor ({time.time() - started:.0f} s)", flush=True)

            stats = index.refresh(store, get_embedder(settings), rebuild=ns.rebuild, progress=progress)
            print(f"{index.render_line(stats)} · {time.time() - started:.0f} s")
            return 0 if not stats.pending else 1
        print(json.dumps(index.status(store), ensure_ascii=False, indent=1))
        from sotawhat.rag.answer import from_settings

        ok, detail = from_settings(settings).ping()
        print(f"SLM: {'ok' if ok else 'fora'} · {detail}")
    return 0


def main_eval(ns, settings) -> int:
    """`sotawhat rag eval [--gerar] [--n 40]`: the retrieval against questions written from your own items."""
    from datetime import date

    from sotawhat.rag import evaluate
    from sotawhat.store.db import Store

    path = settings.sotawhat_data_dir / evaluate.FOLDER / "questions.jsonl"
    with Store(settings.db_path) as store:
        retriever, slm = build(settings, store)
        questions = evaluate.load(path)
        if ns.gerar or not questions:
            ok, detail = slm.ping()
            if not ok:
                print(f"para gerar as perguntas é preciso o SLM: {detail} (rode `sotawhat rag up`)", file=sys.stderr)
                return 2
            questions = evaluate.draft(store, slm, n=ns.n)
            evaluate.save(questions, path)
            print(f"{len(questions)} perguntas em {path}")
        results = evaluate.run(retriever, questions[:ns.n], k=settings.rag_sources)
    report = evaluate.render(results, k=settings.rag_sources)
    out = settings.sotawhat_data_dir / evaluate.FOLDER / f"{date.today().isoformat()}-recuperacao.md"
    out.write_text(report + "\n", encoding="utf-8")
    print(report)
    print(f"\n[relatório] {out}")
    return 0

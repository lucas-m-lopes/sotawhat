# sotawhat/rag/evaluate.py
"""`sotawhat rag eval`: how often the retrieval finds the item a question is about (SDD §6.15).

The questions come from your own graph: for a sample of approved items the local SLM writes one question in
Portuguese whose answer is in the item, with other words than its title (`--gerar`, no paid call). Each
question is then asked to the whole retrieval and to each ranking alone, and the report says where the item
came: first (hit@1), among the first three or among the sources of an answer (hit@k), plus the mean
reciprocal rank. It is the measure to look at before changing a weight, the embedder or the reranker.
The questions are easier than real ones (they were written with the item in view), so read the numbers as a
ceiling and compare runs with each other, not with the outside world."""
import json
import random
from pathlib import Path

from sotawhat.store.db import APPROVED

FOLDER = Path("evals") / "rag"
SYSTEM = ("Você escreve perguntas de teste para um sistema de busca. Receberá o título e o resumo de um item sobre "
          "IA na medicina ou IA de fronteira. Escreva UMA pergunta em português do Brasil que um médico curioso faria "
          "e cuja resposta está neste item. Use outras palavras que não as do título, não copie frases do resumo, não "
          "cite o nome do artigo e não diga 'neste estudo'. Responda só com a pergunta, em uma linha.")
SETUPS = (("tudo", None, True), ("sem reranker", None, False), ("só sentido (denso)", {"dense"}, False),
          ("só palavras (BM25)", {"bm25"}, False), ("só grafo (PageRank)", {"graph"}, False),
          ("grafo + menções + relações", {"graph", "mention", "relation", "category"}, False),
          ("denso + BM25", {"dense", "bm25"}, False))


def draft(store, slm, n=40, seed=13) -> list:
    rows = store.conn.execute(
        "SELECT i.id, i.title, t.summary_pt FROM items i JOIN triage t ON t.item_id = i.id"
        f" WHERE t.decision IN ({','.join('?' * len(APPROVED))}) AND length(t.summary_pt) > 120 ORDER BY i.id",
        list(APPROVED)).fetchall()
    random.Random(seed).shuffle(rows)
    out = []
    for row in rows:
        if len(out) >= n:
            break
        reply = slm.chat([{"role": "system", "content": SYSTEM},
                          {"role": "user", "content": f"Título: {row['title']}\nResumo: {row['summary_pt']}"}],
                         max_tokens=120, temperature=0.7)
        question = reply.text.strip().splitlines()[0].strip(' "“”')
        if 20 <= len(question) <= 300 and question.endswith("?"):
            out.append({"question": question, "item_id": row["id"], "title": row["title"]})
    return out


def save(questions, path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(q, ensure_ascii=False) + "\n" for q in questions), encoding="utf-8")


def load(path) -> list:
    path = Path(path)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def measure(retriever, questions, k=8, channels=None, rerank=True) -> dict:
    reranker = retriever.reranker
    if not rerank:
        retriever.reranker = None
    ranks, seconds = [], 0.0
    try:
        for entry in questions:
            pack = retriever.retrieve(entry["question"], k=k, channels=channels)
            seconds += pack.timings.get("total", 0.0)
            found = [s.item_id for s in pack.sources]
            ranks.append(found.index(entry["item_id"]) + 1 if entry["item_id"] in found else None)
    finally:
        retriever.reranker = reranker
    n = len(ranks) or 1
    return {"n": len(ranks), "hit1": sum(r == 1 for r in ranks) / n, "hit3": sum(r is not None and r <= 3 for r in ranks) / n,
            "hitk": sum(r is not None for r in ranks) / n, "mrr": sum(1 / r for r in ranks if r) / n,
            "seconds": seconds / n, "ranks": ranks}


def run(retriever, questions, k=8) -> dict:
    return {name: measure(retriever, questions, k=k, channels=channels,
                          rerank=rerank and retriever.reranker is not None)
            for name, channels, rerank in SETUPS if rerank is False or retriever.reranker is not None}


def render(results, k=8) -> str:
    def pct(x):
        return f"{100 * x:.0f}%"

    n = next(iter(results.values()))["n"] if results else 0
    out = [f"Recuperação · {n} perguntas geradas dos seus itens · o item certo entre as {k} fontes", "",
           f"| Configuração | 1º lugar | top 3 | top {k} | MRR | s/pergunta |", "|---|---|---|---|---|---|"]
    for name, r in results.items():
        out.append(f"| {name} | {pct(r['hit1'])} | {pct(r['hit3'])} | {pct(r['hitk'])} | {r['mrr']:.2f} | "
                   f"{r['seconds']:.2f} |")
    return "\n".join(out)

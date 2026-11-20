# tests/test_rag.py
"""Questions to the graph (SDD §6.15): the passage index, the hybrid retrieval and the SLM answer with its checks."""
from datetime import datetime, timezone

import httpx
import pytest

from sotawhat.cli import parse_args
from sotawhat.config import Settings
from sotawhat.items import Item
from sotawhat.rag import index
from sotawhat.rag.answer import SLM, SLMError, ask, check, messages_for
from sotawhat.rag.commands import render, slm_up
from sotawhat.rag.retrieve import Pack, Retriever, Source, content_tokens, window_days
from sotawhat.store.db import Store
from sotawhat.store.vectors import HashEmbedder, passage_text, query_text

NOW = datetime(2026, 11, 20, 12, tzinfo=timezone.utc)
TEXT = ("Sepsis is a leading cause of death in intensive care units. We trained a gradient boosting model on vital "
        "signs to predict sepsis six hours before onset. " * 4)


def _item(n, title, text="short"):
    return Item(id=f"pmid:{n}", kind="paper", source="pubmed", source_id=str(n), title=title,
                url=f"https://example.org/{n}", text=text)


@pytest.fixture
def store(tmp_path):
    """Five approved items and one rejected. SepsisNet (item 1) addresses the problem "sepsis early detection";
    item 2 is about that problem without the model; item 3 is about MedGemma; item 4 is old; item 5 only shares
    Google with item 3."""
    with Store(tmp_path / "insight.db") as st:
        run = st.start_run("daily")
        st.upsert_items([_item(1, "SepsisNet prediz sepse na UTI", TEXT),
                         _item(2, "Alerta precoce de deterioração em enfermaria"),
                         _item(3, "MedGemma 1.5 lê tomografia"),
                         _item(4, "Estudo antigo de sepse"),
                         _item(5, "Google abre laboratório de agentes"),
                         _item(6, "Fase III de anticorpo")], run)
        summaries = {1: "SepsisNet usa gradient boosting para prever sepse 6 horas antes, com AUROC 0,91.",
                     2: "Sistema de alerta precoce reduz atraso no reconhecimento de deterioração clínica.",
                     3: "MedGemma 1.5 interpreta volumes de tomografia e supera a versão anterior.",
                     4: "Revisão antiga sobre escores de sepse em terapia intensiva.",
                     5: "Novo laboratório do Google estuda agentes que usam ferramentas."}
        for n, summary in summaries.items():
            st.record_triage(f"pmid:{n}", run, "main", total=4.0 - n / 10, summary_pt=summary,
                             why_it_matters_pt="Útil para a rede hospitalar.", tags={"domains": ["A05"] if n in (1, 2, 4) else []})
        st.record_triage("pmid:6", run, "reject", total=1.0, summary_pt="Sem IA.")
        st.conn.execute("UPDATE items SET fetched_at = '2026-11-19T10:00:00+00:00'")
        st.conn.execute("UPDATE items SET fetched_at = '2026-09-01T10:00:00+00:00' WHERE id = 'pmid:4'")
        st.conn.commit()
        ids = {"sepsisnet": st.add_entity("model", "SepsisNet", "sepsisnet", "C08"),
               "sepsis": st.add_entity("problem", "sepsis early detection", "sepsis early detection", "B03"),
               "gbm": st.add_entity("technique", "gradient boosting", "gradient boosting", "C09"),
               "medgemma": st.add_entity("model", "MedGemma 1.5", "medgemma 1 5", "C04"),
               "google": st.add_entity("organization", "Google", "google"),
               "icu": st.add_entity("domain", "terapia intensiva/deterioração", "terapia intensiva deterioracao", "A05")}
        st.add_alias("problem", "sepse", ids["sepsis"], "sepse")
        st.add_alias("artifact", "medgemma", ids["medgemma"], "MedGemma")
        seen = "2026-11-19T10:00:00+00:00"
        for item, entity, role in ((1, "sepsisnet", "main"), (1, "sepsis", "used"), (1, "gbm", "used"), (1, "icu", "tag"),
                                   (2, "sepsis", "mentioned"), (2, "icu", "tag"), (3, "medgemma", "main"),
                                   (3, "google", "mentioned"), (4, "sepsis", "main"), (4, "icu", "tag"), (5, "google", "main")):
            st.add_mention(f"pmid:{item}", ids[entity], role, seen)
        st.add_relation(ids["sepsisnet"], "addresses", ids["sepsis"], "pmid:1")
        st.add_relation(ids["sepsisnet"], "uses", ids["gbm"], "pmid:1")
        st.add_relation(ids["medgemma"], "developed_by", ids["google"], "pmid:3")
        st.record_extraction("pmid:1", run, "ok", payload={"claims": [{"text_pt": "AUROC de 0,91 seis horas antes.",
                                                                       "metric": "AUROC", "value": "0.91"}]})
        st.add_glossary_term("gradient boosting", "gradient boosting", "Soma de muitas árvores pequenas, cada uma "
                             "corrigindo o erro das anteriores.", entity_id=ids["gbm"])
        st.ids = ids
        yield st


class FakeReranker:
    """The source whose text has the favourite word wins."""
    def __init__(self, favourite=None, fail=False, low=0.1):
        self.favourite, self.fail, self.low, self.calls = favourite, fail, low, []

    def score(self, question, texts):
        self.calls.append((question, list(texts)))
        if self.fail:
            raise RuntimeError("no model here")
        return [0.9 if self.favourite and self.favourite in t else self.low for t in texts]


def _retriever(store, reranker=None, embedder=None):
    return Retriever(store, embedder or HashEmbedder(), reranker, now=lambda: NOW)


def test_chunks_cut_at_sentences_and_overlap():
    text = " ".join(f"Sentence number {n} has some words in it." for n in range(60))
    pieces = index.chunks(text, size=300, limit=5)
    assert len(pieces) == 5 and all(len(p) <= 400 for p in pieces) and all(p.endswith(".") for p in pieces)
    assert pieces[1].startswith(pieces[0].split(". ")[-1][:20])          # the last sentence opens the next chunk
    assert index.chunks("") == [] and index.chunks("One short sentence.") == ["One short sentence."]
    assert all(len(p) <= 300 for p in index.chunks("x" * 1000, size=300))  # no sentence end: cut anyway


def test_index_follows_the_store(store):
    stats = index.refresh(store, HashEmbedder())
    kinds = {k: v["passages"] for k, v in index.status(store)["kinds"].items()}
    assert kinds == {"card": 5, "text": 1, "entity": 6, "glossary": 1} and stats.added == 13 and stats.pending == 0
    assert stats.embedded == 13 and stats.lexical and index.status(store)["items_indexed"] == 5
    card = store.conn.execute("SELECT * FROM rag_passages WHERE kind = 'card' AND ref = 'pmid:1'").fetchone()
    assert "AUROC de 0,91" in card["body"] and "Entidades: SepsisNet" in card["body"] and "terapia intensiva" in card["body"]
    assert store.conn.execute("SELECT COUNT(*) FROM rag_fts").fetchone()[0] == 13
    again = index.refresh(store, HashEmbedder())
    assert (again.added, again.changed, again.removed, again.embedded) == (0, 0, 0, 0)       # nothing changed
    store.record_triage("pmid:2", 1, "main", summary_pt="Resumo reescrito sobre deterioração.", why_it_matters_pt="x")
    store.record_triage("pmid:5", 1, "reject")
    after = index.refresh(store, HashEmbedder())
    assert (after.added, after.changed, after.removed, after.embedded) == (0, 1, 1, 1)
    assert store.conn.execute("SELECT COUNT(*) FROM rag_fts WHERE rag_fts MATCH 'reescrito'").fetchone()[0] == 1
    assert store.conn.execute("SELECT COUNT(*) FROM rag_fts WHERE rag_fts MATCH 'laboratorio'").fetchone()[0] == 0
    no_vectors = index.refresh(store, None, rebuild=True)
    assert no_vectors.pending == no_vectors.passages == 12 and "sem vetor" in index.render_line(no_vectors)
    assert passage_text("google/embeddinggemma-300m", "", "x") == "title: none | text: x"
    assert query_text("google/embeddinggemma-300m", "q") == "task: search result | query: q" and query_text("hash-256", "q") == "q"


def test_the_question_gives_a_window_and_its_words():
    assert window_days("o que saiu esta semana sobre agentes?") == 7 and window_days("novidades de hoje") == 1
    assert window_days("nos últimos 30 dias") == 30 and window_days("últimas 2 semanas") == 14
    assert window_days("no último mês") == 31 and window_days("o que é RAG?") is None
    assert content_tokens("Quais modelos estão sendo usados para prever sepse na UTI?") == [
        "modelos", "sendo", "usados", "prever", "sepse", "uti"]


def test_linking_by_name_alias_and_category(store):
    index.refresh(store, HashEmbedder())
    r = _retriever(store)
    by_name = {e.name: e for e in r.link("O MedGemma 1.5 é melhor que o SepsisNet para sepse?")}
    assert set(by_name) == {"MedGemma 1.5", "SepsisNet", "sepsis early detection"}
    assert all(e.how == "nome" and e.weight == 1.0 for e in by_name.values())
    assert [e.name for e in r.link("o que há sobre terapia intensiva?")] == ["terapia intensiva/deterioração"]
    assert r.link("qual o melhor modelo?") == []                       # a generic word is not an entity


def test_retrieval_fuses_text_graph_and_mentions(store):
    index.refresh(store, HashEmbedder())
    pack = _retriever(store).retrieve("Quais modelos abordam sepse?")
    assert pack.sources[0].item_id == "pmid:1" and pack.days is None
    found = {s.item_id: s for s in pack.sources}
    assert "pmid:6" not in found                                          # rejected items are never a source
    assert {"mention", "graph"} <= set(found["pmid:1"].channels)
    assert "graph" in found["pmid:2"].channels                            # reached through the problem it mentions
    assert found["pmid:1"].excerpt.startswith("Sepsis is a leading cause") and found["pmid:1"].section == "IA ∩ Saúde"
    facts = "\n".join(pack.facts)
    assert "sepsis early detection (problema" in facts and "é abordado por: SepsisNet" in facts
    context = pack.context()
    assert context.startswith("## Fatos do grafo") and "[1] SepsisNet prediz sepse na UTI (pubmed, 19/11/2026" in context
    assert 'Trecho do original: "Sepsis is' in context
    assert pack.as_dict()["sources"][0]["title"] == "SepsisNet prediz sepse na UTI"

    recent = _retriever(store).retrieve("o que chegou sobre sepse esta semana?")
    assert recent.days == 7 and "pmid:4" not in {s.item_id for s in recent.sources} and "janela" in recent.notes[0]
    assert "pmid:4" in {s.item_id for s in _retriever(store).retrieve("o que há sobre sepse?").sources}
    assert "pmid:4" in {s.item_id for s in _retriever(store).retrieve("sepse esta semana", days=365).sources}

    by_category = _retriever(store).retrieve("resumo de terapia intensiva")
    assert {s.item_id for s in by_category.sources if "category" in s.channels} == {"pmid:1", "pmid:2", "pmid:4"}
    assert _retriever(store).retrieve("   ").sources == []


def test_facts_are_computed_from_the_graph(store):
    index.refresh(store, HashEmbedder())
    counted = _retriever(store).retrieve("Quantos itens falam de sepse este mês?")
    assert "• Contagem: 4 itens aprovados nos últimos 31 dias." in counted.facts
    assert "• Contagem: 2 itens aprovados citam sepsis early detection nos últimos 31 dias." in counted.facts
    top = "\n".join(_retriever(store).retrieve("quais os modelos mais citados?").facts)
    assert "Mais citados (modelo, em todo o grafo): " in top and "MedGemma 1.5 (1)" in top and "SepsisNet (1)" in top
    glossary = "\n".join(_retriever(store).retrieve("o que é gradient boosting?").facts)
    assert "• Glossário, gradient boosting: Soma de muitas árvores" in glossary and glossary.count("Glossário") == 1


def test_the_reranker_reorders_and_may_fail(store):
    index.refresh(store, HashEmbedder())
    reranker = FakeReranker(favourite="deterioração")
    pack = _retriever(store, reranker).retrieve("o que há sobre sepse?")
    assert pack.sources[0].item_id == "pmid:2" and pack.sources[0].relevance == 0.9 and not pack.weak
    assert reranker.calls[0][0] == "o que há sobre sepse?" and len(reranker.calls[0][1]) == len(pack.sources)
    broken = _retriever(store, FakeReranker(fail=True)).retrieve("o que há sobre sepse?")
    assert broken.sources[0].item_id == "pmid:1" and broken.sources[0].relevance is None
    assert any("reranker indisponível" in n for n in broken.notes)
    lost = _retriever(store, FakeReranker(low=0.001)).retrieve("receita de bolo de cenoura")
    assert lost.weak and "pouco ligadas" in lost.notes[-1]            # nothing in the graph is about it


def test_without_vectors_the_words_and_the_graph_still_answer(store):
    index.refresh(store, None)
    pack = _retriever(store).retrieve("Quais modelos abordam sepse?")
    assert pack.sources[0].item_id == "pmid:1" and "dense" not in pack.sources[0].channels
    assert any("sem vetores" in n for n in pack.notes)


def test_context_keeps_three_sources_and_drops_excerpts_first():
    sources = [Source(n=n, item_id=f"i{n}", title=f"Título {n}", url="", source="pubmed", day="2026-11-19T10:00:00+00:00",
                      section="IA ∩ Saúde", summary="Resumo. " * 20, why="Motivo.", excerpt="Original. " * 30)
               for n in range(1, 7)]
    pack = Pack(question="q", sources=sources, facts=["• fato"])
    small = pack.context(budget=300)
    assert small.count("\n[") + small.count("\n\n[") >= 3 and "[4] " not in small and "Trecho do original" not in small
    assert "[6] Título 6" in pack.context(budget=10 ** 6) and pack.context(budget=10 ** 6).count("Trecho do original") == 6


def _server(*replies, models=("qwen3.5:9b-q4_K_M",)):
    calls = []

    def post(url, json=None, headers=None, timeout=None):
        calls.append((url, json, headers))
        status, content = replies[min(len(calls) - 1, len(replies) - 1)]
        body = {"model": json["model"], "choices": [{"message": {"content": content}}],
                "usage": {"prompt_tokens": 900, "completion_tokens": 60}}
        return httpx.Response(status, json=body if status == 200 else {"error": content}, request=httpx.Request("POST", url))

    def get(url, headers=None, timeout=None):
        return httpx.Response(200, json={"data": [{"id": m} for m in models]}, request=httpx.Request("GET", url))

    return post, get, calls


def test_slm_client_talks_openai_and_turns_the_thinking_off():
    post, get, calls = _server((200, "<think>hmm</think>A resposta [1]."))
    slm = SLM("http://127.0.0.1:11434/v1/", "qwen3.5:9b-q4_K_M", api_key="k", post=post, get=get)
    reply = slm.chat([{"role": "user", "content": "oi"}])
    assert reply.text == "A resposta [1]." and (reply.tokens_in, reply.tokens_out) == (900, 60)
    url, payload, headers = calls[0]
    assert url == "http://127.0.0.1:11434/v1/chat/completions" and payload["reasoning_effort"] == "none"
    assert headers == {"Authorization": "Bearer k"} and payload["temperature"] == 0.2
    assert slm.ping() == (True, "qwen3.5:9b-q4_K_M em http://127.0.0.1:11434/v1")
    assert "não está no servidor" in SLM("http://x/v1", "outro", post=post, get=get).ping()[1]
    assert SLM("", "m").ping()[0] is False and not SLM("", "m").configured

    post, get, calls = _server((400, "unknown field"), (200, "Sem o campo [2]."))       # a server that refuses the field
    assert SLM("http://x/v1", "m", post=post, get=get).chat([]).text == "Sem o campo [2]."
    assert "reasoning_effort" in calls[0][1] and "reasoning_effort" not in calls[1][1]
    post, get, _ = _server((200, "<think>only thinking</think>"))
    with pytest.raises(SLMError, match="vazia"):
        SLM("http://x/v1", "m", post=post, get=get).chat([])
    post, get, _ = _server((500, "boom"))
    with pytest.raises(SLMError, match="500"):
        SLM("http://x/v1", "m", reasoning="", post=post, get=get).chat([])

    def down(url, **kwargs):
        raise httpx.ConnectError("refused")
    with pytest.raises(SLMError, match="rag up"):
        SLM("http://x/v1", "m", post=down).chat([])
    assert SLM("http://x/v1", "m", get=down).ping()[0] is False


def test_the_answer_is_checked_against_the_sources(store):
    index.refresh(store, HashEmbedder())
    retriever = _retriever(store)
    post, get, calls = _server((200, "O SepsisNet prevê sepse 6 horas antes, com AUROC 0,91 [1]."))
    slm = SLM("http://x/v1", "m", post=post, get=get)
    answer = ask(retriever, slm, "Quais modelos abordam sepse?")
    assert answer.text.startswith("O SepsisNet") and answer.cited == [1] and answer.warnings == [] and answer.model == "m"
    system, user = calls[0][1]["messages"]
    assert "somente o CONTEXTO" in system["content"] and user["content"].endswith("PERGUNTA: Quais modelos abordam sepse?")
    assert user["content"] == messages_for(answer.pack)[1]["content"]
    shown = render(answer)
    assert "*[1] SepsisNet prediz sepse na UTI" in shown and " [2] " in shown and "Entidades: " in shown
    assert answer.as_dict()["answer"] == answer.text and answer.as_dict()["sources"][0]["n"] == 1

    pack, context = answer.pack, answer.pack.context()
    assert check("Reduz mortalidade em 37% [1] e cita [9].", pack, context)["warnings"] == [
        "cita fonte que não existe: [9]", "números que não estão nas fontes: 37%"]
    assert check("Prevê sepse antes.", pack, context)["warnings"] == ["resposta sem citação: confira nas fontes"]
    assert check("Não encontrei isso no grafo.", pack, context) == {"cited": [], "warnings": [], "refused": True}
    assert check("AUROC de 0.91 [1].", pack, context)["warnings"] == []          # 0,91 and 0.91 are the same number

    no_model = ask(retriever, None, "Quais modelos abordam sepse?")
    assert no_model.text is None and "nenhum SLM" in no_model.error and "SepsisNet usa gradient boosting" in render(no_model)
    post, get, _ = _server((500, "boom"))
    broken = ask(retriever, SLM("http://x/v1", "m", post=post, get=get), "Quais modelos abordam sepse?")
    assert broken.text is None and "500" in broken.error and broken.pack.sources
    with Store(store.path.parent / "empty.db") as empty:
        assert ask(_retriever(empty), slm, "qualquer coisa").text == "Não encontrei isso no grafo."


def test_cli_and_settings():
    ns = parse_args(["ask", "o", "que", "saiu?", "--dias", "7", "--so-fontes"])
    assert (ns.command, ns.question, ns.dias, ns.so_fontes, ns.k) == ("ask", ["o", "que", "saiu?"], 7, True, None)
    assert parse_args(["rag", "index", "--rebuild"]).rebuild and parse_args(["rag", "up"]).rag_action == "up"
    s = Settings(_env_file=None)
    assert s.slm_base_url == "http://127.0.0.1:11434/v1" and s.slm_reasoning == "none" and s.rag_sources == 8
    assert s.rag_reranker == "BAAI/bge-reranker-v2-m3-int8"


def test_rag_up_starts_ollama_and_pulls_the_model(tmp_path):
    class Done:
        def __init__(self, code=0, err=""):
            self.returncode, self.stdout, self.stderr = code, "", err

    calls, answers = [], [(False, "http://x não responde (ConnectError)"), (False, "o modelo m não está no servidor (tem: nenhum)"),
                          (True, "m em http://x")]

    def run(cmd, **kwargs):
        calls.append((cmd, kwargs.get("env", {}).get("NEO4J_PASSWORD")))
        return Done()

    settings = Settings(_env_file=None, sotawhat_data_dir=tmp_path, slm_model="m")
    ok, message = slm_up(settings, tmp_path, run=run, sleep=lambda s: None, ping=lambda: answers.pop(0))
    assert ok and message == "SLM no ar: m em http://x"
    assert calls[1][0][:6] == ["docker", "compose", "--env-file", str(tmp_path / "compose.env"), "up", "-d"]
    assert calls[1][1] == "unused" and calls[2][0] == ["docker", "exec", "sotawhat-ollama", "ollama", "pull", "m"]
    failed = slm_up(settings, tmp_path, run=lambda cmd, **kw: Done(1, "no docker"))
    assert failed[0] is False and "Docker" in failed[1]


def test_rag_eval_asks_the_whole_retrieval_and_each_ranking(store, tmp_path):
    from sotawhat.rag import evaluate

    index.refresh(store, HashEmbedder())
    post, get, calls = _server((200, '"Que modelo antecipa sepse em seis horas na terapia intensiva?"'))
    questions = evaluate.draft(store, SLM("http://x/v1", "m", post=post, get=get), n=2, seed=1)
    assert len(questions) == 0 and len(calls) == 0             # summaries under 120 characters are not sampled
    store.record_triage("pmid:1", 1, "main", summary_pt="SepsisNet usa gradient boosting para prever sepse 6 horas antes, "
                        "com AUROC 0,91, em pacientes de terapia intensiva de três hospitais universitários.",
                        why_it_matters_pt="Útil para a rede hospitalar.")
    index.refresh(store, HashEmbedder())
    questions = evaluate.draft(store, SLM("http://x/v1", "m", post=post, get=get), n=2, seed=1)
    assert questions == [{"question": "Que modelo antecipa sepse em seis horas na terapia intensiva?", "item_id": "pmid:1",
                          "title": "SepsisNet prediz sepse na UTI"}]
    assert "Título: SepsisNet prediz sepse na UTI" in calls[0][1]["messages"][1]["content"]
    path = tmp_path / "evals" / "questions.jsonl"
    evaluate.save(questions, path)
    assert evaluate.load(path) == questions and evaluate.load(tmp_path / "missing.jsonl") == []
    retriever = _retriever(store, FakeReranker(favourite="SepsisNet"))
    results = evaluate.run(retriever, questions, k=3)
    assert set(results) == {name for name, _, _ in evaluate.SETUPS} and results["tudo"]["hit1"] == 1.0
    assert results["só palavras (BM25)"]["ranks"] == [1] and retriever.reranker is not None      # put back after each run
    without = evaluate.run(_retriever(store), questions, k=3)
    assert "tudo" not in without and "sem reranker" in without                                  # no reranker to compare
    report = evaluate.render(results, k=3)
    assert "| tudo | 100% | 100% | 100% | 1.00 |" in report and "1 perguntas" in report
    only = _retriever(store).retrieve("Quais modelos abordam sepse?", channels={"bm25"})
    assert all(set(s.channels) == {"bm25"} for s in only.sources)
    assert parse_args(["rag", "eval", "--gerar", "--n", "5"]).n == 5


def test_an_entity_shared_by_the_best_sources_is_linked(store):
    index.refresh(store, HashEmbedder())
    pack = _retriever(store).retrieve("alertas de deterioração clínica")           # no entity name in the question
    how = {e.name: e.how for e in pack.entities}
    assert how["sepsis early detection"] == "fontes" and how["terapia intensiva/deterioração"] == "nome"
    assert any(f.startswith("• sepsis early detection (problema") for f in pack.facts)
    assert not any("nenhuma entidade" in n for n in pack.notes)
    alone = _retriever(store).retrieve("o que o Google abriu?", k=1)                 # one source: nothing is "shared"
    assert [e.how for e in alone.entities] == ["nome"]


# --- the Jev engine (rag/jev.py): a typed-decision model judges the sources and picks the sentence that answers ---
class FakeSystemOne:
    """Answers each request by its passage: `yes` words make it relevant; the choice is the sentence with the word."""
    def __init__(self, yes=("SepsisNet",), fail=(), status=200, cost=0.00002, none=(), second=False):
        self.yes, self.fail, self.status, self.cost, self.calls = yes, fail, status, cost, []
        self.none, self.second = none, second        # none: sentences the choice refuses; second: it leans to s2

    def post(self, url, headers=None, json=None, timeout=None):
        self.calls.append((url, headers, json))
        passage = json["state"]["passage"]
        if self.status != 200 or any(word in passage for word in self.fail):
            return httpx.Response(self.status if self.status != 200 else 503, json={"error": {"message": "sem crédito"}},
                                  request=httpx.Request("POST", url))
        hit = next((word for word in self.yes if word in passage), None)
        answers = {"answers": {"type": "noul", "noul": 0.93 if hit else 0.04}}
        if "best" in json["questions"]:
            options = json["questions"]["best"]["criteria"]
            best = next((key for key, text in options.items() if hit and hit in text and key not in self.none), "none")
            spread = {k: float(k == best) for k in options}
            if best == "none" and hit and self.second:
                spread = {**spread, "none": 0.7, "s2": 0.3}
            answers["best"] = {"type": "choice", "choice": best, "probabilities": spread}
        return httpx.Response(200, json={"model": "typesafe/jev-1.13-20260917", "answers": answers, "provider": "TypeSafe",
                                         "usage": {"input_tokens": 400, "output_tokens": 20, "cost": self.cost}},
                              request=httpx.Request("POST", url))


def test_jev_asks_typed_questions_with_the_project_privacy(store):
    from sotawhat.rag import jev as J

    assert J.sentences("Primeira frase bem comprida aqui. Curta. Segunda frase também comprida, com 9,4 minutos.") == [
        "Primeira frase bem comprida aqui.", "Segunda frase também comprida, com 9,4 minutos."]
    api = FakeSystemOne()
    jev = J.Jev("key", store=store, post=api.post)
    judgments = jev.judge("O que prevê sepse?", [("SepsisNet prediz sepse", "O SepsisNet usa gradient boosting na UTI. "
                                                  "Ele antecipa a sepse em seis horas, com AUROC 0,91."),
                                                 ("Escriba ambiente", "Reduz a digitação no pronto-socorro.")])
    assert [round(j.probability, 2) for j in judgments] == [0.93, 0.04]
    assert judgments[0].quote == "O SepsisNet usa gradient boosting na UTI." and judgments[1].quote == ""
    first = next(call for call in api.calls if "SepsisNet" in call[2]["state"]["passage"])
    url, headers, body = first
    assert url == "https://openrouter.ai/api/v1/systemone" and headers == {"Authorization": "Bearer key"}
    assert body["model"] == "typesafe/jev-1.13" and body["provider"] == {"data_collection": "deny", "zdr": True}
    assert body["state"]["question"] == "O que prevê sepse?" and body["questions"]["answers"]["type"] == "noul"
    assert set(body["questions"]["best"]["criteria"]) == {"s1", "s2", "none"}
    single = next(call[2] for call in api.calls if "Escriba" in call[2]["state"]["passage"])
    assert "best" not in single["questions"]                        # one sentence: there is nothing to choose
    row = store.conn.execute("SELECT * FROM llm_calls WHERE task = 'rag_jev'").fetchone()
    assert (row["input_tokens"], row["status"], row["provider"]) == (800, "ok", "TypeSafe")
    assert abs(row["cost_usd"] - 0.00004) < 1e-9
    J.Jev("key", zdr=False, post=api.post).decide({"question": "q", "passage": "p"}, {"answers": J.ANSWERS})
    assert api.calls[-1][2]["provider"] == {"data_collection": "deny"}


def test_jev_failures_never_break_the_search(store):
    from sotawhat.rag import jev as J

    partial = J.Jev("key", store=store, post=FakeSystemOne(fail=("Escriba",)).post).judge(
        "q", [("SepsisNet", "O SepsisNet prevê sepse com antecedência de seis horas."), ("Escriba", "Reduz a digitação no PS.")])
    assert [round(j.probability, 2) for j in partial] == [0.93, 0.0]       # the passage whose request failed sinks
    with pytest.raises(J.JevError, match="402: sem crédito"):
        J.Jev("key", store=store, post=FakeSystemOne(status=402).post).judge("q", [("a", "texto qualquer aqui dentro")])
    assert store.conn.execute("SELECT status FROM llm_calls ORDER BY id DESC LIMIT 1").fetchone()[0] == "error"
    with pytest.raises(J.JevError, match="OPENROUTER_API_KEY"):
        J.Jev("", post=FakeSystemOne().post).judge("q", [("a", "b")])
    store.record_llm_call(task="triage", requested_model="m", cost_usd=30.0, status="ok")
    with pytest.raises(J.JevError, match="orçamento mensal"):
        J.Jev("key", store=store, budget_month=25.0, post=FakeSystemOne().post).judge("q", [("a", "b")])
    assert J.Jev("key", post=FakeSystemOne().post).judge("q", []) == []
    # the passage helps but no sentence answers the whole question: the most probable sentence, else the first one
    piece = [("SepsisNet", "O SepsisNet prevê sepse com antecedência. Foi validado em três hospitais universitários.")]
    leaning = J.Jev("key", post=FakeSystemOne(none=("s1", "s2"), second=True).post).judge("q", piece)[0]
    assert leaning.quote == "Foi validado em três hospitais universitários."
    plain = J.Jev("key", post=FakeSystemOne(none=("s1", "s2")).post).judge("q", piece)[0]
    assert plain.quote == "O SepsisNet prevê sepse com antecedência." and plain.probability == 0.93

    def down(url, **kwargs):
        raise httpx.ConnectError("refused")
    with pytest.raises(J.JevError, match="não respondeu"):
        J.Jev("key", post=down).decide("s", {"answers": J.ANSWERS})
    assert J.from_settings(Settings(_env_file=None)) is None
    made = J.from_settings(Settings(_env_file=None, openrouter_api_key="k", openrouter_zdr=False, rag_jev_model="typesafe/jev-9"))
    assert (made.model, made.zdr, made.data_collection, made.configured) == ("typesafe/jev-9", False, "deny", True)


def test_the_jev_engine_extracts_the_answer_instead_of_writing_it(store):
    from sotawhat.rag import jev as J
    from sotawhat.rag.answer import extract

    index.refresh(store, HashEmbedder())
    retriever = _retriever(store, FakeReranker(favourite="deterioração"))       # the cross-encoder is not asked
    api = FakeSystemOne(yes=("SepsisNet",))
    answer = ask(retriever, None, "Quais modelos abordam sepse?", engine="jev", jev=J.Jev("key", store=store, post=api.post))
    assert answer.engine == "jev" and answer.model == "typesafe/jev-1.13" and answer.error is None
    assert answer.text == ("• SepsisNet prediz sepse na UTI: SepsisNet usa gradient boosting para prever sepse 6 horas antes, "
                           "com AUROC 0,91. [1]")
    assert answer.cited == [1] and answer.pack.sources[0].item_id == "pmid:1" and answer.pack.sources[0].relevance == 0.93
    assert answer.pack.sources[1].quote == "" and retriever.reranker.calls == []
    assert len(api.calls) == len(answer.pack.sources) and answer.as_dict()["engine"] == "jev"
    assert "frases extraídas, nada foi redigido" in render(answer)

    nothing = ask(retriever, None, "Quais modelos abordam sepse?", engine="jev",
                  jev=J.Jev("key", post=FakeSystemOne(yes=()).post))
    assert nothing.text == "Não encontrei isso no grafo." and nothing.cited == []
    counted = ask(retriever, None, "Quantos itens falam de sepse?", engine="jev", jev=J.Jev("key", post=FakeSystemOne().post))
    assert counted.text.startswith("Contagem: 5 itens aprovados em todo o grafo.") and "[1]" in counted.text
    assert extract(Pack(question="q")) == (None, [])

    broken = ask(retriever, None, "Quais modelos abordam sepse?", engine="jev",
                 jev=J.Jev("key", post=FakeSystemOne(status=402).post))
    assert broken.text is None and broken.model is None and "a Jev não julgou as fontes" in broken.error and broken.pack.sources
    post, get, _ = _server((200, "O SepsisNet prevê sepse [1]."))             # no Jev configured: the local model answers
    local = ask(retriever, SLM("http://x/v1", "m", post=post, get=get), "Quais modelos abordam sepse?", engine="jev", jev=None)
    assert local.engine == "slm" and local.text.startswith("O SepsisNet")
    assert any("Jev indisponível" in n for n in local.pack.notes)
    assert parse_args(["ask", "pergunta", "--motor", "jev"]).motor == "jev" and parse_args(["ask", "pergunta"]).motor is None
    assert parse_args(["rag", "eval", "--jev"]).jev and Settings(_env_file=None).rag_engine == "slm"


def test_how_much_is_not_a_count(store):
    index.refresh(store, HashEmbedder())
    assert not any("Contagem" in f for f in _retriever(store).retrieve("Quanto tempo o SepsisNet antecipa a sepse?").facts)
    facts = "\n".join(_retriever(store).retrieve("Quantos modelos há no grafo?").facts)
    assert "• Contagem: 2 entidades do tipo modelo citadas em todo o grafo." in facts and "Mais citados" not in facts

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
    assert "sepsis early detection (problema" in facts and "é o alvo de «aborda» de: SepsisNet" in facts
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

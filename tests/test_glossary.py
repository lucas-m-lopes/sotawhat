# tests/test_glossary.py
"""The glossary of the digests (SDD §6.14): terms defined once by the LLM, found again with no LLM, a few a day."""
import pytest

from sotawhat import glossary
from sotawhat.configfiles import ConfigError, DigestStyle, load_config, load_digest_style
from sotawhat.items import Item
from sotawhat.llm.gateway import LLMFailure, StructuredResult, strict_schema
from sotawhat.llm.schemas import GlossaryBatch, GlossaryEntry
from sotawhat.llm.tasks import resolve
from sotawhat.pipeline.deliver import Digest, Entry, render_email, render_html, render_markdown, telegram_messages
from sotawhat.pipeline.triage import system_prompt
from sotawhat.store.db import Store


def _entry(n, summary, why="Serve para o hospital.", section="main"):
    return Entry(item_id=f"pmid:{n}", title=f"Estudo {n}", url=f"https://example.org/{n}", source="pubmed",
                 profile="medico", total=4.0, scores={"A": 4, "B": 4}, summary=summary, why=why, tags={}, sources=[],
                 section=section, position=n)


def _digest(*summaries, day="2026-11-20"):
    return Digest(day=day, stats_line="x", main=[_entry(n, s) for n, s in enumerate(summaries, 1)], radar=[],
                  extra=[], failing=[])


def _term(termo, definicao="Definição em uma frase", sigla_de="", variantes=(), itens=(1,)):
    return GlossaryEntry(termo=termo, sigla_de=sigla_de, definicao=definicao, variantes=list(variantes), itens=list(itens))


class FakeGateway:
    def __init__(self, *batches, fail=False):
        self.batches, self.fail, self.calls, self.run_id = list(batches), fail, [], None

    def structured_call(self, task, messages, output_model, models=None):
        self.calls.append((task, messages))
        if self.fail:
            raise LLMFailure("glossary: every model failed")
        batch = self.batches.pop(0) if self.batches else GlossaryBatch(termos=[])
        return StructuredResult(output=batch, model="deepseek/x", provider=None, cost_usd=0.0006, latency_ms=5,
                                attempts=1, first_try_valid=True)


@pytest.fixture
def store(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        run = st.start_run("daily")
        st.upsert_items([Item(id=f"pmid:{n}", kind="paper", source="pubmed", source_id=str(n), title=f"Estudo {n}",
                              url=f"https://example.org/{n}") for n in range(1, 5)], run)
        yield st


def test_a_term_is_found_whatever_its_case_hyphen_or_plural():
    text = "O pipeline usa fine tuning e Embeddings; o RAG ajuda, mas não basta. LLMs erram."
    assert glossary.occurs("fine-tuning", text) and glossary.occurs("embedding", text)
    assert glossary.occurs("RAG", text) and glossary.occurs("LLM", text)       # an acronym, also in the plural
    assert not glossary.occurs("MAS", text)                                    # "mas" is a Portuguese word
    assert not glossary.occurs("tuning curve", text) and not glossary.occurs("", text)
    assert glossary.norm("Embeddings") == "embedding" and glossary.norm(" Few-Shot ") == "few shot"


def test_new_terms_come_from_the_llm_once_and_are_matched_without_it_afterwards(store):
    technique = store.add_entity("technique", "retrieval-augmented generation", "retrieval augmented generation")
    store.add_alias("technique", "rag", technique, "RAG")
    first = _digest("O modelo usa RAG e few-shot para resumir prontuários.", "Um VAE gera exames sintéticos.")
    gateway = FakeGateway(GlossaryBatch(termos=[
        _term("RAG", "Técnica em que o modelo consulta documentos antes de responder", "retrieval-augmented generation"),
        _term("few-shot", "Ensinar a tarefa ao modelo com poucos exemplos no próprio pedido.", variantes=["few shot"]),
        _term("transformer", "Arquitetura que não está nos textos."),             # not written today: dropped
        _term("IA", "Inteligência artificial."),                                 # never a glossary term
        _term("VAE", "Rede que comprime os dados e os reconstrói.", "variational autoencoder", itens=[2])]))
    got = glossary.build(store, gateway, first)
    assert [(g["term"], g["new"]) for g in got] == [("few-shot", True), ("RAG", True), ("VAE", True)]
    assert got[1]["expansion"] == "retrieval-augmented generation" and got[1]["definition"].endswith("responder.")
    task, messages = gateway.calls[0]
    assert task == "glossary" and "(nenhum ainda)" in messages[1]["content"] and "[2] Estudo 2." in messages[1]["content"]
    rows = {r["term"]: r for r in store.glossary_terms()}
    assert set(rows) == {"RAG", "few-shot", "VAE"} and rows["RAG"]["entity_id"] == technique
    assert rows["RAG"]["model"] == "deepseek/x" and rows["RAG"]["prompt_version"] == "glossary_v1"
    assert store.conn.execute("SELECT item_id FROM glossary_items WHERE term_id = ?", (rows["VAE"]["id"],)).fetchall()[0][0] == "pmid:2"

    # the next day: known terms need no LLM; a new spelling of a known term becomes its alias, not a new term
    second = _digest("Avaliação de RAG com few shot em radiologia.", "Embeddings de laudos.", day="2026-11-21")
    quiet = FakeGateway(GlossaryBatch(termos=[_term("embedding", "Lista de números que representa um texto.",
                                                    variantes=["Embeddings"], itens=[2]),
                                              _term("Few Shot", "Outra definição.")]))
    got = glossary.build(store, quiet, second)
    assert [(g["term"], g["new"]) for g in got] == [("embedding", True), ("few-shot", False), ("RAG", False)]
    assert "few-shot, RAG, VAE" in quiet.calls[0][1][1]["content"]
    assert len(store.glossary_terms()) == 4
    assert [g["term"] for g in glossary.build(store, None, second)] == ["embedding", "few-shot", "RAG"]   # no LLM at all


def test_a_term_leaves_the_digests_after_its_repeats_or_when_marked_known(store):
    digest = _digest("O modelo usa RAG e LoRA.")
    gateway = FakeGateway(GlossaryBatch(termos=[_term("RAG"), _term("LoRA")]))
    digest.glossary = glossary.build(store, gateway, digest, repeats=2)
    glossary.mark_shown(store, digest)
    glossary.mark_shown(store, digest)                       # the run repeated on the same day: one exposure
    assert {r["term"]: r["shown_count"] for r in store.glossary_terms()} == {"RAG": 1, "LoRA": 1}
    again = _digest("RAG e LoRA de novo.", day="2026-11-21")
    again.glossary = glossary.build(store, None, again, repeats=2)
    assert len(again.glossary) == 2
    glossary.mark_shown(store, again)
    third = _digest("RAG e LoRA ainda.", day="2026-11-22")
    assert glossary.build(store, None, third, repeats=2) == []          # printed twice: only in the interface now
    assert len(glossary.build(store, None, again, repeats=2)) == 2      # the day it was printed still shows it
    lora = next(r for r in store.glossary_terms() if r["term"] == "LoRA")
    assert store.set_glossary_status(lora["id"], "conhecido") and not store.set_glossary_status(999, "conhecido")
    assert [g["term"] for g in glossary.build(store, None, third, repeats=9)] == ["RAG"]
    assert [g["term"] for g in glossary.build(store, None, third, repeats=9, limit=0)] == []


def test_the_digest_goes_out_when_the_llm_fails(store):
    digest = _digest("O modelo usa RAG.")
    assert glossary.build(store, FakeGateway(fail=True), digest) == []
    store.add_glossary_term("RAG", "rag", "Consulta documentos antes de responder.")
    assert [g["term"] for g in glossary.build(store, FakeGateway(fail=True), digest)] == ["RAG"]
    assert glossary.build(store, None, Digest(day="2026-11-20", stats_line="x", main=[], radar=[], extra=[], failing=[])) == []


def test_glossary_in_the_files_the_email_and_telegram():
    digest = _digest("O modelo usa RAG.")
    digest.glossary = [{"id": 1, "term": "RAG", "expansion": "retrieval-augmented generation",
                        "definition": "Consulta documentos <antes> de responder.", "new": True},
                       {"id": 2, "term": "few-shot", "expansion": None, "definition": "Poucos exemplos no pedido.", "new": False}]
    md = render_markdown(digest)
    assert "## 📖 Glossário do dia" in md and "- **RAG (retrieval-augmented generation)**: Consulta documentos <antes>" in md
    assert "<b>few-shot</b>: Poucos exemplos no pedido." in render_html(digest)
    _, text, html = render_email(digest)
    assert "Glossário do dia" in text and "RAG (retrieval-augmented generation)</b>: Consulta documentos &lt;antes&gt;" in html
    assert "aba Glossário" in html
    last = telegram_messages(digest)[-1]
    assert last["text"].startswith("📖 <b>Glossário do dia</b>\n• <b>RAG (retrieval-augmented generation)</b>: Consulta")
    assert last["rows"] == [] and last["silent"]
    digest.glossary = []
    assert "Glossário" not in render_markdown(digest) and "Glossário" not in telegram_messages(digest)[-1]["text"]


def test_view_lists_every_term_with_where_it_appeared(store):
    technique = store.add_entity("technique", "low-rank adaptation", "low rank adaptation")
    lora, _ = store.add_glossary_term("LoRA", "lora", "Ajuste fino barato, que treina poucas matrizes.",
                                      expansion="low-rank adaptation", aliases=["LoRAs"], entity_id=technique)
    rag, created = store.add_glossary_term("RAG", "rag", "Consulta documentos antes de responder.")
    assert created and store.add_glossary_term("Rag", "rag", "Outra.", aliases=["RAGs"]) == (rag, False)
    store.link_glossary_items(lora, ["pmid:1", "pmid:2"], "2026-11-20")
    store.set_glossary_status(rag, "conhecido")
    view = glossary.view(store)
    assert [t["term"] for t in view["terms"]] == ["LoRA", "RAG"] and view["counts"] == {"ativo": 1, "conhecido": 1}
    first = view["terms"][0]
    assert first["entity"] == "low-rank adaptation" and first["items"] == 2 and first["last_seen"] == "2026-11-20"
    assert {i["id"] for i in first["latest"]} == {"pmid:1", "pmid:2"} and first["aliases"] == ["LoRAs"]
    assert view["terms"][1]["aliases"] == ["RAGs"] and view["terms"][1]["definition"].startswith("Consulta")
    assert [t["term"] for t in glossary.view(store, text="documentos")["terms"]] == ["RAG"]
    assert [t["term"] for t in glossary.view(store, text="low-rank")["terms"]] == ["LoRA"]
    assert [t["term"] for t in glossary.view(store, status="conhecido")["terms"]] == ["RAG"]


def test_digest_style_config_and_the_prompts(tmp_path):
    assert DigestStyle().triage_prompt == "triage_v4" and DigestStyle(didactic=False).triage_prompt == "triage_v3"
    assert load_digest_style(tmp_path / "missing.yaml") == DigestStyle()
    path = tmp_path / "digest.yaml"
    path.write_text("didactic: false\nglossary_limit: 5\n", encoding="utf-8")
    assert load_digest_style(path) == DigestStyle(didactic=False, glossary_limit=5)
    assert load_config(tmp_path).digest.glossary_limit == 5
    for bad in ("didatico: true\n", "glossary_limit: muitos\n", "glossary: 1\n", "glossary_new: -1\n"):
        path.write_text(bad, encoding="utf-8")
        with pytest.raises(ConfigError):
            load_digest_style(path)
    assert load_config("config").digest == DigestStyle()                  # the file in the repository
    assert "up to 75 words" in system_prompt("triage_v4") and "up to 60 words" in system_prompt("triage_v3")
    assert "{{" not in system_prompt("triage_v4") and "{{" not in glossary.system_prompt(10)
    assert "At most 10 terms" in glossary.system_prompt(10)
    assert resolve("glossary").reasoning == "low"
    assert strict_schema(GlossaryBatch)["required"] == ["termos"]
    with pytest.raises(ValueError):
        _term("RAG", "检索增强生成")                                          # Portuguese only

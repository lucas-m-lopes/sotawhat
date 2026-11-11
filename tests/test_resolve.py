# tests/test_resolve.py
"""Entity resolution (SDD §6.8): normalization, aliases, digit guard, LLM judge, categories, patterns."""
import json

import numpy as np
import pytest

from sotawhat.configfiles import ConfigError, load_aliases
from sotawhat.graph.resolve import (Resolver, display_name, make_judge, normalize, split_acronym,
                                     strip_inner_acronyms)
from sotawhat.items import Item
from sotawhat.llm.schemas import Extraction, SameEntity
from sotawhat.store.db import Store


def _store(tmp_path, n_items=6):
    st = Store(tmp_path / "insight.db")
    run = st.start_run("daily")
    st.upsert_items([Item(id=f"pmid:{n}", kind="paper", source="pubmed", source_id=str(n), title=f"Paper {n}",
                          url=f"https://pubmed.ncbi.nlm.nih.gov/{n}/", text="English text only.", pmid=str(n))
                     for n in range(1, n_items + 1)], run)
    for n in range(1, n_items + 1):
        st.conn.execute("UPDATE items SET fetched_at = ? WHERE id = ?", (f"2026-11-08T10:{n:02d}:00+00:00", f"pmid:{n}"))
        st.record_triage(f"pmid:{n}", run, "main")
    st.conn.commit()
    return st


def _row(st, n, tags=None):
    row = dict(st.get_items([f"pmid:{n}"])[0])
    row["tags_json"] = json.dumps(tags or {})
    return row


def _x(*entities, relations=()):
    return Extraction.model_validate({
        "entities": [{"name": name, "type": type_, "category": category, "role": role}
                     for name, type_, category, role in entities],
        "relations": [{"source": s, "relation": r, "target": t} for s, r, t in relations],
        "claims": [], "maturity": "research", "data_modalities": []})


def _e(name, type_="technique", category="none", role="main"):
    return (name, type_, category, role)


class Judge:
    def __init__(self, same=()):
        self.same, self.calls = set(same), []

    def __call__(self, type_, name_a, context_a, name_b, context_b):
        self.calls.append((name_a, name_b))
        return (name_a, name_b) in self.same or (name_b, name_a) in self.same


def _ids(st, name):
    return [r["id"] for r in st.conn.execute("SELECT id FROM entities WHERE name = ?", (name,))]


def test_normalize_and_split_acronym():
    assert normalize("The Retrieval-Augmented Generation") == "retrieval augmented generation"
    assert normalize("Diffusion Models", "technique") == "diffusion model"
    assert normalize("pressure injuries", "problem") == "pressure injury"
    assert normalize("diabetes", "problem") == "diabetes" and normalize("Diagnostics", "technique") == "diagnostics"
    assert normalize("Ångström Labs", "organization") == "angstrom labs"
    assert normalize("Mayo Clinics", "organization") == "mayo clinics"          # only techniques and problems
    assert split_acronym("retrieval-augmented generation (RAG)") == ("retrieval-augmented generation", "RAG")
    assert split_acronym("LLMs (large language models)") == ("large language models", "LLMs")
    assert split_acronym("Food and Drug Administration (FDA)") == ("Food and Drug Administration", "FDA")
    assert split_acronym("MedGemma 1.5 (Google)") == ("MedGemma 1.5", None)       # not an acronym: dropped
    assert split_acronym("GPT-4o") == ("GPT-4o", None)


@pytest.mark.parametrize("plural, singular", [
    # words that only look plural, acronyms and words with symbols keep their s (all seen in real extractions)
    ("AI bias", "AI bias"), ("algorithmic biases", "algorithmic bias"), ("k-means", "k-means"),
    ("pancreas", "pancreas"), ("dental caries", "dental caries"), ("ARDS", "ARDS"), ("CAMS", "CAMS"),
    ("UPLC-MS/MS", "UPLC-MS/MS"), ("Harness-S", "Harness-S"), ("Alzheimer's", "Alzheimer's"),
    # the head noun is the word before the first preposition, else the last word
    ("mixture-of-experts", "mixture-of-experts"), ("Mixture of Transformers", "Mixture of Transformers"),
    ("attacks on LLMs", "attack on LLMs"), ("state-of-the-art models", "state-of-the-art model"),
    ("LLMs", "LLM"), ("AI-agents", "AI-agent"), ("filas de espera", "fila de espera"),
    # -es plurals lose the whole ending, -ies plurals become -y, a few Greek and Latin ones are listed
    ("Gaussian processes", "Gaussian process"), ("image patches", "image patch"), ("bounding boxes", "bounding box"),
    ("3D meshes", "3D mesh"), ("KV caches", "KV cache"), ("migraine headaches", "migraine headache"),
    ("respiratory viruses", "respiratory virus"), ("meta-analyses", "meta-analysis"), ("hypotheses", "hypothesis"),
    ("missed diagnoses", "missed diagnosis"), ("Diagnostic Criteria", "Diagnostic Criterion"),
    ("third-party cookies", "third-party cookie"), ("pressure injuries", "pressure injury"),
    ("rare diseases", "rare disease"), ("claim denials", "claim denial"),
])
def test_the_head_noun_goes_singular_and_nothing_else(plural, singular):
    assert display_name(plural, "problem") == singular
    assert display_name(singular, "problem") == singular                          # idempotent
    assert normalize(plural, "problem") == normalize(singular, "problem")        # both forms meet in one entity
    assert display_name(plural, "model") == plural                               # only techniques and problems


def test_seed_aliases_and_acronyms_lead_to_one_entity(tmp_path):
    st = _store(tmp_path)
    resolver = Resolver(st, aliases={"technique": {"large language model": ["LLM", "LLMs"]}})
    resolver.apply(_row(st, 1), _x(_e("LLMs")))
    resolver.apply(_row(st, 2), _x(_e("Large Language Models")))
    resolver.apply(_row(st, 3), _x(_e("retrieval-augmented generation (RAG)")))
    out = resolver.apply(_row(st, 4), _x(_e("RAG", role="used")))
    assert out.new_entities == 0 and out.mentions == 1
    llm, rag = _ids(st, "large language model"), _ids(st, "retrieval-augmented generation")
    assert len(llm) == 1 and st.get_entity(llm[0])["mention_count"] == 2
    assert len(rag) == 1 and st.get_entity(rag[0])["mention_count"] == 2
    st.close()


def test_model_and_product_share_a_group(tmp_path):
    st = _store(tmp_path)
    resolver = Resolver(st)
    resolver.apply(_row(st, 1), _x(_e("MedGemma 1.5", "model", "C04")))
    resolver.apply(_row(st, 2), _x(_e("MedGemma 1.5", "product")))
    rows = st.conn.execute("SELECT type, mention_count, category FROM entities WHERE type IN ('model', 'product')")
    assert [tuple(r) for r in rows] == [("model", 2, "C04")]
    st.close()


def test_different_numbers_never_reach_the_judge(tmp_path):
    st = _store(tmp_path)
    judge = Judge(same={("GPT-4.1", "GPT-4o"), ("MedGemma 2", "MedGemma 1.5")})
    resolver = Resolver(st, judge=judge)
    resolver.apply(_row(st, 1), _x(_e("GPT-4o", "model"), _e("MedGemma 1.5", "model")))
    resolver.apply(_row(st, 2), _x(_e("GPT-4.1", "model"), _e("MedGemma 2", "model")))
    assert judge.calls == [] and st.conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0] == 4
    st.close()


def test_the_judge_merges_or_keeps_apart_and_has_a_cap(tmp_path):
    st = _store(tmp_path)
    judge = Judge(same={("DeepMind", "Google DeepMind")})
    resolver = Resolver(st, judge=judge, max_judge_calls=2)
    resolver.apply(_row(st, 1), _x(_e("Google DeepMind", "organization"), _e("Mayo Clinic", "organization")))
    out = resolver.apply(_row(st, 2), _x(_e("DeepMind", "organization"), _e("Mayo Clinic Platform", "organization")))
    assert judge.calls == [("DeepMind", "Google DeepMind"), ("Mayo Clinic Platform", "Mayo Clinic")]
    assert (out.judge_calls, out.merges, out.new_entities) == (2, 1, 1)
    google = _ids(st, "Google DeepMind")[0]
    assert st.get_entity(google)["mention_count"] == 2 and _ids(st, "DeepMind") == []
    merge = st.conn.execute("SELECT entity_id, name, method, item_id FROM entity_merges").fetchone()
    assert tuple(merge) == (google, "DeepMind", "judge", "pmid:2")
    capped = resolver.apply(_row(st, 3), _x(_e("Mayo Clinic Hospital", "organization")))
    assert capped.judge_calls == 0 and capped.new_entities == 1 and len(judge.calls) == 2
    st.close()


def test_containment_alone_never_sends_techniques_or_problems_to_the_judge(tmp_path):
    st = _store(tmp_path)
    judge = Judge()
    resolver = Resolver(st, judge=judge)
    resolver.apply(_row(st, 1), _x(_e("large language model"), _e("sepsis", "problem")))
    resolver.apply(_row(st, 2), _x(_e("large language model agent"), _e("sepsis early detection", "problem")))
    assert judge.calls == []          # a narrower concept, not a synonym (2026-11-08 backfill: 40 calls, 0 merges)
    st.close()


def test_generic_long_and_foreign_names_are_dropped(tmp_path):
    st = _store(tmp_path)
    resolver = Resolver(st)
    out = resolver.apply(_row(st, 1), _x(_e("AI"), _e("model"), _e("patients", "problem"), _e("x" * 90),
                                         _e("通义千问", "model"), _e("federated learning")))
    assert (out.dropped, out.new_entities) == (5, 1)
    st.conn.execute("UPDATE items SET text = '通义千问 is a model family' WHERE id = 'pmid:2'")
    assert resolver.apply(_row(st, 2), _x(_e("通义千问", "model"))).new_entities == 1   # it is in the text
    st.close()


def test_relations_follow_the_allowed_patterns(tmp_path):
    st = _store(tmp_path)
    resolver = Resolver(st)
    out = resolver.apply(_row(st, 1), _x(
        _e("MedGemma 1.5", "model", "C04"), _e("Google", "organization"), _e("sepsis early detection", "problem"),
        _e("MIMIC-IV", "dataset"), _e("Dragon Copilot", "product"),
        relations=[("MedGemma 1.5", "developed_by", "Google"),               # ok
                   ("MedGemma 1.5", "developed_by", "sepsis early detection"),  # wrong target type
                   ("MedGemma 1.5", "addresses", "sepsis early detection"),     # ok
                   ("MedGemma 1.5", "compared_with", "Dragon Copilot"),         # ok: same group
                   ("MedGemma 1.5", "compared_with", "MIMIC-IV"),               # different kinds
                   ("MedGemma 1.5", "evaluated_on", "MedGemma 1.5"),            # self
                   ("Unknown thing", "uses", "MIMIC-IV")]))                     # not listed
    names = {r["id"]: r["name"] for r in st.conn.execute("SELECT id, name FROM entities")}
    kept = sorted((names[s], p, names[o]) for s, p, o in st.relations_of_item("pmid:1") if p != "in_category")
    assert kept == [("MedGemma 1.5", "addresses", "sepsis early detection"),
                    ("MedGemma 1.5", "compared_with", "Dragon Copilot"), ("MedGemma 1.5", "developed_by", "Google")]
    assert out.dropped == 4
    st.close()


def test_triage_categories_become_nodes_and_entities_link_to_them(tmp_path):
    st = _store(tmp_path)
    resolver = Resolver(st)
    row = _row(st, 1, tags={"domains": ["A03"], "techniques": ["C05"], "problem_types": ["B02", "Z99"]})
    resolver.apply(row, _x(_e("vision transformer", "technique", "C05"), _e("missed fractures", "problem", "B02")))
    cats = {(r["type"], r["category"]): r["name"] for r in
            st.conn.execute("SELECT * FROM entities WHERE type IN ('domain', 'technique_family', 'problem_type')")}
    assert cats == {("domain", "A03"): "radiologia/imagem", ("technique_family", "C05"): "visão computacional diagnóstica",
                    ("problem_type", "B02"): "erro/atraso diagnóstico"}
    roles = {r[0] for r in st.conn.execute("SELECT role FROM entity_mentions m JOIN entities e ON e.id = m.entity_id"
                                           " WHERE e.type = 'domain'")}
    assert roles == {"tag"}
    names = {r["id"]: r["name"] for r in st.conn.execute("SELECT id, name FROM entities")}
    links = sorted((names[s], names[o]) for s, p, o in st.relations_of_item("pmid:1") if p == "in_category")
    assert links == [("missed fracture", "erro/atraso diagnóstico"), ("vision transformer", "visão computacional diagnóstica")]
    assert resolver.link_categories("pmid:1", {"domains": ["A03"]}, row["fetched_at"]) == 0      # idempotent
    st.close()


def test_close_embeddings_send_synonyms_to_the_judge(tmp_path):
    class Embedder:
        name = "fake-2"

        def embed(self, texts):
            table = {"problem: heart attack": [1.0, 0.0], "problem: myocardial infarction": [0.99, 0.141],
                     "problem: stroke": [0.0, 1.0]}
            return np.array([table[t] for t in texts], dtype=np.float32)

    st = _store(tmp_path)
    judge = Judge(same={("myocardial infarction", "heart attack")})
    resolver = Resolver(st, embedder=Embedder(), judge=judge)
    resolver.apply(_row(st, 1), _x(_e("heart attack", "problem"), _e("stroke", "problem")))
    resolver.apply(_row(st, 2), _x(_e("myocardial infarction", "problem")))
    assert judge.calls == [("myocardial infarction", "heart attack")]
    assert st.get_entity(_ids(st, "heart attack")[0])["mention_count"] == 2
    assert len(st.load_entity_embeddings("fake-2", [r[0] for r in st.conn.execute("SELECT id FROM entities")])) == 2
    st.close()


def test_make_judge_calls_the_resolve_task_and_fails_safe():
    class Gateway:
        def __init__(self, error=None):
            self.error, self.calls = error, []

        def structured(self, task, messages, model, models=None):
            self.calls.append((task, messages[1]["content"]))
            if self.error:
                raise self.error
            return SameEntity(same=True, reason="short and long form")

    from sotawhat.llm.gateway import LLMFailure
    gateway = Gateway()
    assert make_judge(gateway)("organization", "DeepMind", "Paper 2", "Google DeepMind", "Paper 1") is True
    task, text = gateway.calls[0]
    assert task == "resolve" and "A: DeepMind" in text and "B: Google DeepMind" in text and "Paper 1" in text
    assert make_judge(Gateway(LLMFailure("down")))("organization", "a", "", "b", "") is False


def test_repository_aliases_map_common_names(tmp_path):
    st = _store(tmp_path)
    resolver = Resolver(st, aliases=load_aliases("config/aliases.yaml"))
    resolver.apply(_row(st, 1), _x(_e("Food and Drug Administration (FDA)", "organization"), _e("LLMs"),
                                   _e("HL7 FHIR", "regulation")))
    resolver.apply(_row(st, 2), _x(_e("U.S. Food and Drug Administration", "organization"),
                                   _e("Large Language Models"), _e("FHIR", "regulation")))
    rows = {r["name"]: r["mention_count"] for r in st.conn.execute("SELECT name, mention_count FROM entities")}
    assert rows == {"FDA": 2, "large language model": 2, "FHIR": 2}
    st.close()


def test_aliases_yaml_is_validated(tmp_path):
    good = tmp_path / "aliases.yaml"
    good.write_text("technique:\n  large language model: [LLM, LLMs]\n", encoding="utf-8")
    assert load_aliases(good) == {"technique": {"large language model": ["LLM", "LLMs"]}}
    assert load_aliases(tmp_path / "missing.yaml") == {}
    for bad in ("person:\n  Ana: [A]\n", "technique:\n  rag: retrieval\n", "technique: [a, b]\n"):
        good.write_text(bad, encoding="utf-8")
        with pytest.raises(ConfigError):
            load_aliases(good)


# --- 2026-11-11 graph repair: duplicates the resolver let in ------------------------------------
def test_an_acronym_inside_a_name_leaves_it():
    """The prompt asks for "name (ACRONYM)"; in a compound name the acronym lands in the middle."""
    assert strip_inner_acronyms("large language model (LLM) agent") == "large language model agent"
    assert strip_inner_acronyms("agentic large language model (LLM) pipeline") == "agentic large language model pipeline"
    assert strip_inner_acronyms("electronic health record (EHR)-based risk prediction") == \
        "electronic health record-based risk prediction"
    assert strip_inner_acronyms("vision-language-action (VLA) model") == "vision-language-action model"
    assert strip_inner_acronyms("ReAct-Plan-Exec-Reflect (RPR) workflow") == "ReAct-Plan-Exec-Reflect (RPR) workflow"
    assert strip_inner_acronyms("retrieval-augmented generation (RAG)") == "retrieval-augmented generation (RAG)"


def test_spacing_variants_and_inner_acronyms_meet_the_known_entity(tmp_path):
    st = _store(tmp_path)
    judge = Judge()                                     # would say no: these matches never ask it
    resolver = Resolver(st, judge=judge)
    resolver.apply(_row(st, 1), _x(_e("GPT-4", "model"), _e("nnU-Net", "model"), _e("large language model (LLM) agent")))
    out = resolver.apply(_row(st, 2), _x(_e("GPT4", "model"), _e("nnUnet", "model"), _e("large language model agent")))
    assert out.new_entities == 0 and judge.calls == []
    assert [len(_ids(st, n)) for n in ("GPT-4", "nnU-Net", "large language model agent")] == [1, 1, 1]
    assert _ids(st, "GPT4") == [] and st.get_entity(_ids(st, "GPT-4")[0])["mention_count"] == 2
    assert st.entity_by_alias("artifact", "gpt4")["name"] == "GPT-4"
    st.close()


def test_a_moved_alias_crosses_types_and_relations_follow_the_real_type(tmp_path):
    """After `repair entities` merges "regulation: MCP" into the technique, its alias keeps pointing there."""
    st = _store(tmp_path)
    resolver = Resolver(st)
    resolver.apply(_row(st, 1), _x(_e("Model Context Protocol (MCP)"), _e("HealthAPI", "product"),
                                   relations=[("HealthAPI", "uses", "Model Context Protocol")]))
    mcp = _ids(st, "Model Context Protocol")[0]
    st.add_alias("regulation", "model context protocol", mcp, "Model Context Protocol")
    out = resolver.apply(_row(st, 2), _x(_e("Model Context Protocol", "regulation"), _e("Codex", "product"),
                                         relations=[("Codex", "uses", "Model Context Protocol"),
                                                    ("Codex", "regulated_by", "Model Context Protocol")]))
    assert out.new_entities == 1 and _ids(st, "Model Context Protocol") == [mcp]     # Codex is the only new one
    assert st.get_entity(mcp)["mention_count"] == 2
    names = {r["id"]: r["name"] for r in st.conn.execute("SELECT id, name FROM entities")}
    kept = sorted((names[s], p, names[o]) for s, p, o in st.relations_of_item("pmid:2") if p != "in_category")
    assert kept == [("Codex", "uses", "Model Context Protocol")]            # regulated_by needs a regulation
    st.close()


def test_dropped_names_never_become_entities(tmp_path):
    st = _store(tmp_path)
    resolver = Resolver(st, ignore=[("organization", "level 3 delivery NICU")])
    out = resolver.apply(_row(st, 1), _x(_e("level 3 delivery NICU", "organization"), _e("Pieces", "product")))
    assert out.dropped == 1 and _ids(st, "level 3 delivery NICU") == [] and _ids(st, "Pieces")
    st.close()


def test_methods_compare_across_types_and_using_a_task_means_addressing_it(tmp_path):
    """Benchmarks compare architectures typed as technique with models; and an alias may turn the target of a
    "uses" into a problem (a task such as "radiology report generation")."""
    st = _store(tmp_path)
    Resolver(st).apply(_row(st, 1), _x(
        _e("nnU-Net"), _e("Swin-Unet", "model"), _e("RadRef"), _e("radiology report generation", "problem"),
        _e("MIMIC-CXR", "dataset"),
        relations=[("nnU-Net", "compared_with", "Swin-Unet"), ("RadRef", "uses", "radiology report generation"),
                   ("nnU-Net", "compared_with", "MIMIC-CXR")]))
    names = {r["id"]: r["name"] for r in st.conn.execute("SELECT id, name FROM entities")}
    kept = sorted((names[s], p, names[o]) for s, p, o in st.relations_of_item("pmid:1") if p != "in_category")
    assert kept == [("RadRef", "addresses", "radiology report generation"), ("nnU-Net", "compared_with", "Swin-Unet")]
    st.close()

# tests/test_repair.py
"""`sotawhat repair cjk` (P6): stored triage texts with CJK characters are rewritten, decisions kept."""
from sotawhat.configfiles import Rubric
from sotawhat.doctor import check_cjk
from sotawhat.items import Item
from sotawhat.llm.gateway import LLMFailure, StructuredResult
from sotawhat.pipeline.repair import cjk_rows, repair_cjk
from sotawhat.store.db import Store
from tests.test_triage import out


class Gateway:
    def __init__(self, fail_on=()):
        self.calls, self.fail_on = [], set(fail_on)

    def structured_call(self, task, messages, model_cls, models=None):
        self.calls.append(task)
        if len(self.calls) in self.fail_on:
            raise LLMFailure("triage: every model failed")
        return StructuredResult(output=out(summary_pt="Resumo limpo.", why_it_matters_pt="Importa.", reason_pt="Motivo."),
                                model="deepseek/x", provider=None, cost_usd=0.0004, latency_ms=1, attempts=1,
                                first_try_valid=True)


def test_repair_rewrites_only_the_texts(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        run = st.start_run("daily")
        st.upsert_items([Item(id=f"pmid:{n}", kind="paper", source="pubmed", source_id=str(n), title=f"T{n}", url="u",
                              text="texto") for n in range(3)], run)
        st.record_triage("pmid:0", run, "main", total=3.9, summary_pt="orientar和质量 improvement", why_it_matters_pt="ok")
        st.record_triage("pmid:1", run, "reject", total=1.0, summary_pt="limpo", reason="de随访")
        st.record_triage("pmid:2", run, "frontier", total=3.6, summary_pt="Resumo sem problema.")
        assert [r["item_id"] for r in cjk_rows(st)] == ["pmid:0", "pmid:1"] and check_cjk(st).status == "warn"
        result = repair_cjk(st, Gateway(), Rubric())
        assert result == {"found": 2, "fixed": 2, "failed": 0, "stopped": None} and check_cjk(st).status == "ok"
        main = st.conn.execute("SELECT * FROM triage WHERE item_id = 'pmid:0'").fetchone()
        assert (main["decision"], main["total"], main["summary_pt"], main["why_it_matters_pt"]) == \
            ("main", 3.9, "Resumo limpo.", "Importa.")
        rejected = st.conn.execute("SELECT * FROM triage WHERE item_id = 'pmid:1'").fetchone()
        assert rejected["decision"] == "reject" and rejected["why_it_matters_pt"] == "" and rejected["reason"] == "Motivo."
        assert rejected["prompt_version"].endswith("+repair")
        st.record_triage("pmid:2", run, "frontier", total=3.6, summary_pt="de随访")
        assert repair_cjk(st, Gateway(fail_on={1}), Rubric())["failed"] == 1

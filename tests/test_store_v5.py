# tests/test_store_v5.py
"""Schema 5: the lesson ledger and the quiz answers."""
import pytest

from sotawhat.store.db import Store


def test_lessons_ledger_answers_and_requiz(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        assert st.meta_get("schema_version") == "5"
        a = st.create_lesson("Atenção no Transformer", [105, 634])
        b = st.create_lesson("Da tomografia ao volume", [237])
        st.update_lesson(a, status="entregue", title="Atenção", delivered_at="2026-11-09T10:00:00+00:00",
                         plan={"title": "Atenção"}, report={"cost": 0.1})
        st.update_lesson(b, status="falhou", error="render")
        row = st.get_lesson(a)
        assert row["title"] == "Atenção" and row["plan_json"] == '{"title": "Atenção"}' and row["entities_json"] == "[105, 634]"
        assert [r["id"] for r in st.list_lessons()] == [b, a]
        assert st.taught_entities() == {105, 634}                         # the failed lesson frees its entities
        with pytest.raises(ValueError):
            st.update_lesson(a, colour="red")
        assert st.record_lesson_answer(a, 0, 0, 2, True) and st.record_lesson_answer(a, 0, 1, 0, False)
        assert not st.record_lesson_answer(a, 0, 0, 1, False)             # the first answer counts
        assert st.lesson_score(a, 0) == (1, 2) and st.lesson_score(a, 1) == (0, 0)
        assert [r["id"] for r in st.lessons_due_requiz("2026-11-11T10:00:00+00:00")] == [a]
        st.update_lesson(a, requiz_at="2026-11-11T10:00:00+00:00")
        assert st.lessons_due_requiz("2026-11-12T00:00:00+00:00") == []


def test_llm_cost_for_run(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        run = st.start_run("lesson")
        st.record_llm_call(run_id=run, task="lesson_plan", requested_model="m", status="ok", cost_usd=0.02)
        st.record_llm_call(run_id=run, task="lesson_code", requested_model="m", status="ok", cost_usd=0.03)
        st.record_llm_call(run_id=None, task="triage", requested_model="m", status="ok", cost_usd=0.5)
        assert st.llm_cost_for_run(run) == pytest.approx(0.05)

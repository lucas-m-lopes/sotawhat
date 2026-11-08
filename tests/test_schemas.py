# tests/test_schemas.py
import json
import re

import pytest
from pydantic import ValidationError

from sotawhat import taxonomy as tx
from sotawhat.llm.gateway import strict_schema
from sotawhat.llm.prompts import load
from sotawhat.llm.schemas import TriageOutput

VALID = dict(summary_pt="Resumo.", hard_exclusion="none", inclusion_rules=[1, 4], frontier_ai=4,
             medical_applicability=5, actionability=3, domains=["A03"], problem_types=["B02"], techniques=["C05"],
             evidence_stage="D4", stakeholders=["radiologia_patologia"], br_applicability="F1", cfm_risk="alto",
             substance=3, audience=["clinico"], vendor_only=False, reason_pt="Motivo.", why_it_matters_pt="Importa.")


def test_strict_schema_uses_only_enums_and_requires_everything():
    schema = strict_schema(TriageOutput)
    text = json.dumps(schema)
    assert schema["required"] == list(schema["properties"]) and schema["additionalProperties"] is False
    for keyword in ("minimum", "maximum", "maxLength", "$ref", "anyOf", '"default"'):
        assert keyword not in text                    # portable strict mode across providers
    assert schema["properties"]["frontier_ai"]["enum"] == [0, 1, 2, 3, 4, 5]
    assert schema["properties"]["domains"]["items"]["enum"] == list(tx.DOMAINS)


def test_output_validation_and_tags():
    out = TriageOutput(**VALID)
    assert out.tags()["domains"] == ["A03"] and out.tags()["hard_exclusion"] == "none"
    for field, bad in (("frontier_ai", 6), ("domains", ["A99"]), ("cfm_risk", "altíssimo"), ("inclusion_rules", [11])):
        with pytest.raises(ValidationError):
            TriageOutput(**dict(VALID, **{field: bad}))


def test_taxonomy_matches_the_sdd_and_prompt_placeholders():
    assert (len(tx.DOMAINS), len(tx.PROBLEMS), len(tx.TECHNIQUES), len(tx.EVIDENCE)) == (23, 15, 21, 7)
    assert tx.label("A14") == "ciclo de receita/glosas/autorização" and tx.label("Z9") == "Z9"
    template = load("triage_v1")
    assert set(re.findall(r"\{\{(\w+)\}\}", template)) == {"DOMAINS", "PROBLEMS", "TECHNIQUES", "EVIDENCE",
                                                          "STAKEHOLDERS", "BR", "CFM", "AUDIENCE"}

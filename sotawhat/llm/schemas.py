# sotawhat/llm/schemas.py
"""Structured outputs (SDD §6.6–§6.8: triage, extraction, resolution judge). Every constraint is an enum, which strict JSON schema supports
on every provider; free text is limited by the prompt, not by the schema. Validators that the JSON
schema cannot express (Portuguese text with no CJK slips) run locally: a failure makes the gateway ask
again, like invalid JSON, and then move to the next model."""
import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from sotawhat import taxonomy as tx

Score = Literal[0, 1, 2, 3, 4, 5]
_CJK = re.compile(r"[぀-ヿ㐀-䶿一-鿿가-힯豈-﫿]")
Exclusion = Literal["none", "clinical_without_ai", "generic_ai_no_bridge", "marketing_no_substance",
                    "identifiable_patient_data"]


def no_cjk(value):
    # MiniMax-M3.1-Flash slipped Chinese tokens into 13 of 60 summaries in the 2026-11-08 bake-off
    if _CJK.search(value):
        raise ValueError("contains Chinese, Japanese or Korean characters; write it in Brazilian Portuguese only")
    return value


class TriageOutput(BaseModel):
    summary_pt: str = Field(description="até 60 palavras, pt-BR, só fatos presentes no texto")
    hard_exclusion: Exclusion
    inclusion_rules: list[Literal[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]]
    frontier_ai: Score = Field(description="A: avanço de IA/ML")
    medical_applicability: Score = Field(description="B: aplicação médico-hospitalar direta ou plausível em 2 anos")
    actionability: Score = Field(description="C: dá para usar/testar agora")
    domains: list[Literal[tuple(tx.DOMAINS)]]
    problem_types: list[Literal[tuple(tx.PROBLEMS)]]
    techniques: list[Literal[tuple(tx.TECHNIQUES)]]
    evidence_stage: Literal[tuple(tx.EVIDENCE)]
    stakeholders: list[Literal[tuple(tx.STAKEHOLDERS)]]
    br_applicability: Literal[tuple(tx.BR_APPLICABILITY)]
    cfm_risk: Literal[tuple(tx.CFM_RISK)]
    substance: Literal[0, 1, 2, 3]
    audience: list[Literal[tuple(tx.AUDIENCE)]]
    vendor_only: bool
    reason_pt: str = Field(description="1 frase justificando as notas")
    why_it_matters_pt: str = Field(description="até 40 palavras para hospital/startup; vazio se excluído")

    @field_validator("summary_pt", "reason_pt", "why_it_matters_pt")
    @classmethod
    def _portuguese_only(cls, value):
        return no_cjk(value)

    def tags(self) -> dict:
        return {"domains": self.domains, "problem_types": self.problem_types, "techniques": self.techniques,
                "evidence_stage": self.evidence_stage, "stakeholders": self.stakeholders,
                "br_applicability": self.br_applicability, "cfm_risk": self.cfm_risk,
                "substance": self.substance, "audience": self.audience,
                "inclusion_rules": self.inclusion_rules, "hard_exclusion": self.hard_exclusion,
                "vendor_only": self.vendor_only}


# --- extraction (SDD §6.8, P3) --------------------------------------------------
EntityType = Literal["technique", "model", "dataset", "organization", "product", "problem", "regulation"]
RelationType = Literal["uses", "addresses", "developed_by", "evaluated_on", "compared_with", "builds_on",
                       "regulated_by"]


class ExtractedEntity(BaseModel):
    name: str = Field(description="canonical English name; proper names as written, with the version")
    type: EntityType
    category: Literal[("none",) + tuple(tx.TECHNIQUES) + tuple(tx.PROBLEMS)] = Field(
        description="technique family (technique, model) or problem type (problem); none otherwise")
    role: Literal["main", "used", "mentioned"]


class ExtractedRelation(BaseModel):
    source: str = Field(description="exact name of a listed entity")
    relation: RelationType
    target: str = Field(description="exact name of a listed entity")


class ExtractedClaim(BaseModel):
    text_pt: str = Field(description="one short sentence in Brazilian Portuguese; numbers only from the text")
    metric: str
    value: str

    @field_validator("text_pt")
    @classmethod
    def _portuguese_only(cls, value):
        return no_cjk(value)


class Extraction(BaseModel):
    entities: list[ExtractedEntity] = Field(description="at most 12")
    relations: list[ExtractedRelation] = Field(description="at most 10, only between the listed entities")
    claims: list[ExtractedClaim] = Field(description="at most 5")
    maturity: Literal["research", "prototype", "product", "deployed", "regulated", "unclear"]
    data_modalities: list[Literal["imaging", "ehr", "text", "audio", "signals", "genomics", "video", "other"]]


class SameEntity(BaseModel):
    """Entity-resolution judge (task `resolve`)."""
    same: bool
    reason: str = Field(description="one short sentence in English")

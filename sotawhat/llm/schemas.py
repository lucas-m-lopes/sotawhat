# sotawhat/llm/schemas.py
"""Structured outputs (SDD §6.6, §6.7). Every constraint is an enum, which strict JSON schema supports
on every provider; free text is limited by the prompt, not by the schema."""
from typing import Literal

from pydantic import BaseModel, Field

from sotawhat import taxonomy as tx

Score = Literal[0, 1, 2, 3, 4, 5]
Exclusion = Literal["none", "clinical_without_ai", "generic_ai_no_bridge", "marketing_no_substance",
                    "identifiable_patient_data"]


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

    def tags(self) -> dict:
        return {"domains": self.domains, "problem_types": self.problem_types, "techniques": self.techniques,
                "evidence_stage": self.evidence_stage, "stakeholders": self.stakeholders,
                "br_applicability": self.br_applicability, "cfm_risk": self.cfm_risk,
                "substance": self.substance, "audience": self.audience,
                "inclusion_rules": self.inclusion_rules, "hard_exclusion": self.hard_exclusion,
                "vendor_only": self.vendor_only}

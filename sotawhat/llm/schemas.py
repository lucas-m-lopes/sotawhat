# sotawhat/llm/schemas.py
"""Structured outputs (SDD §6.6–§6.8: triage, extraction, resolution judge). Every constraint is an enum,
which strict JSON schema supports on every provider; free text is limited by the prompt, not by the
schema. Validators that the JSON schema cannot express (Portuguese text with no CJK slips) run locally:
a failure makes the gateway ask again, like invalid JSON, and then move to the next model."""
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


class NewsletterStory(BaseModel):
    title: str = Field(description="short headline in the newsletter's language")
    summary: str = Field(description="one to three sentences in the newsletter's own words")
    link: int = Field(description="number n of the link [n] that points to the story's source; 0 when none")
    category: Literal["news", "paper", "model", "tool", "repo", "opinion", "event", "job", "sponsor", "other"]


class NewsletterStories(BaseModel):
    """Segmentation of one newsletter e-mail into stories (task `segment`, P2)."""
    stories: list[NewsletterStory] = Field(description="at most 15, in the order they appear")


# --- idea engine (SDD §8, P4) ---------------------------------------------------------
Form = Literal["produto_b2b", "plataforma", "dispositivo", "servico_corporativo", "b2b2c"]
Ten = Literal[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]


class _Portuguese(BaseModel):
    @field_validator("*")
    @classmethod
    def _no_cjk(cls, value):
        if isinstance(value, str):
            return no_cjk(value)
        if isinstance(value, list):
            return [no_cjk(v) if isinstance(v, str) else v for v in value]
        return value


class IdeaDraft(_Portuguese):
    titulo: str = Field(description="até 12 palavras, pt-BR")
    problema_jtbd: str = Field(description="a dor concreta, de quem, com que frequência")
    stakeholder_dono: str
    setor: Literal[tuple(tx.DOMAINS)]
    mecanismo: str = Field(description="como funciona, em 2–4 frases")
    tecnicas: list[str]
    capacidade_intermediaria: str
    dado_necessario: list[str]
    forma: Form
    integracao: Literal["FHIR", "PEP", "RNDS", "standalone", "outro"]
    modelo_negocio: str
    why_now: str
    riscos: list[str]
    hipotese_nula: str = Field(description="o que tornaria a ideia inútil ou errada")


class RoleCritique(_Portuguese):
    papel: Literal["clinico", "operacoes", "regulatorio", "dados", "ml", "paciente_etica"]
    veredito: Literal["seguir", "ajustar", "descartar"]
    kill_criteria: list[str]
    o_que_mudaria: str


class IdeaCritique(_Portuguese):
    criticas: list[RoleCritique] = Field(description="uma por papel, os seis papéis")
    nasss_complexos: Literal[0, 1, 2, 3, 4, 5, 6, 7]
    pre_mortem: str


class FacetJudgement(_Portuguese):
    faceta: Literal["problema", "tecnica", "dado", "integracao", "modelo_negocio", "geografia"]
    estado: Literal["igual", "parcial", "nao_encontrado"]
    confianca: Literal["baixa", "media", "alta"]
    vizinho: str = Field(description="título do vizinho mais próximo, ou vazio")


class NoveltyJudgement(_Portuguese):
    facetas: list[FacetJudgement] = Field(description="as seis facetas")


class IdeaScores(_Portuguese):
    valor: Ten
    viabilidade_tecnica: Ten
    viabilidade_negocio: Ten
    regulatorio: Ten = Field(description="10 = carga regulatória leve")
    tempo_piloto: Ten = Field(description="10 = piloto em 90 dias")
    fit: Ten
    adocao: Ten = Field(description="10 = adoção simples (poucos domínios NASSS complexos)")
    gates: list[Literal["sem_base_lgpd", "dado_inexistente", "samd_iv_sem_plano", "viola_cfm_anvisa",
                        "duplica_incumbente"]]
    confianca: Literal[5, 6, 7, 8, 9, 10] = Field(description="multiplicador ×0,1: força da evidência")
    justificativa: str


class Dossier(_Portuguese):
    lean_canvas: str
    piloto_90d: str
    plano_evidencia: str
    classe_samd: Literal["nao_samd", "I", "II", "III", "IV", "incerto"]
    base_legal_lgpd: str
    integracao_detalhe: str


class DraftRepeat(BaseModel):
    n: int = Field(description="número do rascunho novo")
    repete: str = Field(description='"" se é uma ideia nova; "N" se repete o rascunho N desta lista (N menor); '
                                    '"#ID" se repete a ideia anterior #ID do ledger')


class DedupJudgement(BaseModel):
    """Which drafts of one technique × problem pair are the same idea (P4, SDD §8.3 stage 3, dedup by facets)."""
    rascunhos: list[DraftRepeat] = Field(description="um por rascunho novo")


class MetaReview(_Portuguese):
    regras: list[str] = Field(description="até 10 regras curtas, imperativas, em pt-BR")


class CommunityLabel(_Portuguese):
    rotulo: str = Field(description="até 6 palavras, pt-BR")
    resumo: str = Field(description="2–3 frases: o que a comunidade reúne e o que mudou")


class SameEntity(BaseModel):
    """Entity-resolution judge (task `resolve`)."""
    same: bool
    reason: str = Field(description="one short sentence in English")

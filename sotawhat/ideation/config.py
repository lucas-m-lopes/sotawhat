# sotawhat/ideation/config.py
"""Ideation settings (SDD §8.3–§8.6), overridable in config/ideation.yaml. The economic mode is the
default and is leaner than the SDD estimate: the OpenRouter key of the project has a US$ 5 monthly limit,
and the daily runs already spend most of it."""
from dataclasses import dataclass, field, fields, replace
from pathlib import Path

from sotawhat.configfiles import ConfigError, read_yaml
from sotawhat.llm.tasks import DEEPSEEK_FLASH, GLM_FLASH, MIMO_PRO

LENSES = ("tech_push", "jtbd", "scamper", "triz", "analogia", "cenario_2029")
NEGATIVE = "negativa"
PERSONAS = ("residente de clínica médica", "enfermeira de UTI", "gestor de leitos", "engenheiro de dados do hospital",
            "fundador de healthtech que já falhou", "farmacêutica clínica", "coordenador do pronto-socorro",
            "analista de faturamento e glosas")
WEIGHTS = {"valor": 0.20, "viabilidade_tecnica": 0.15, "viabilidade_negocio": 0.15, "novidade": 0.15,
           "regulatorio": 0.10, "tempo_piloto": 0.10, "fit": 0.10, "adocao": 0.05}


@dataclass(frozen=True)
class IdeationConfig:
    candidates: int = 12
    lenses_per_candidate: int = 3
    negative_share: float = 0.25          # the contrarian lens covers at least this share of the batch (≥ 1)
    top_k: int = 10                       # critique, prior art and judges only for these
    judges: int = 2                       # judges of different families
    finalists: int = 6
    per_niche: int = 2                    # MAP-Elites style cap per (domain, technique family, form)
    min_contrarian: int = 1
    quotas: dict = field(default_factory=lambda: {"recent_technique": 0.4, "community_bridge": 0.3, "serendipity": 0.3})
    control_share: float = 0.1            # candidates with no graph context (SDD §8.1)
    context_triples: int = 30
    recent_pair_days: int = 28            # pairs behind ideas of the last 4 weeks lose their priority
    dedup_cosine: float = 0.95            # local embeddings: near-identical texts only (the judge does the rest)
    rejected_cosine: float = 0.95
    weights: dict = field(default_factory=lambda: dict(WEIGHTS))
    generators: tuple = (DEEPSEEK_FLASH, MIMO_PRO, GLM_FLASH)
    judge_models: tuple = (DEEPSEEK_FLASH, GLM_FLASH, MIMO_PRO)
    lenses: tuple = LENSES
    personas: tuple = PERSONAS


MODES = {"economico": {}, "completo": {"candidates": 40, "lenses_per_candidate": 5, "top_k": 30, "judges": 3,
                                       "finalists": 10}}


def load_ideation(path=None, mode="economico") -> IdeationConfig:
    if mode not in MODES:
        raise ConfigError(f"ideation: modo desconhecido {mode!r} (use {', '.join(MODES)})")
    data = read_yaml(path) if path is not None and Path(path).exists() else {}
    known = {f.name for f in fields(IdeationConfig)}
    unknown = sorted(set(data) - known - {"modes"})
    if unknown:
        raise ConfigError(f"ideation.yaml: chaves desconhecidas {unknown}")
    values = {k: tuple(v) if isinstance(v, list) else v for k, v in data.items() if k in known}
    values.update(MODES[mode])
    values.update((data.get("modes") or {}).get(mode) or {})
    config = replace(IdeationConfig(), **values)
    if abs(sum(config.weights.values()) - 1.0) > 1e-6 or set(config.weights) != set(WEIGHTS):
        raise ConfigError(f"ideation.yaml: weights precisa dos eixos {sorted(WEIGHTS)} somando 1")
    return config

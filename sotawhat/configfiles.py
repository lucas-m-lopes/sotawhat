# sotawhat/configfiles.py
"""Versioned, editable YAML in `config/` (SDD §6.2, §6.7): triage rubric, mute filters and per-task
LLM overrides. Every file and every key is optional; built-in defaults fill the gaps."""
from dataclasses import dataclass, field, fields, replace
from pathlib import Path
from urllib.parse import urlsplit

import yaml

from sotawhat.textmatch import contains_term

REASONING_LEVELS = {"none", "minimal", "low", "medium", "high", "xhigh", "max"}


class ConfigError(Exception):
    pass


def read_yaml(path) -> dict:
    path = Path(path)
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path.name}: YAML inválido ({exc})") from None
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigError(f"{path.name}: o topo do arquivo precisa ser um mapeamento")
    return data


@dataclass(frozen=True)
class Rubric:
    """SDD §6.7. total = wA·A + wB·B + wC·C + wD·D − penalties; main if total ≥ min_total and B ≥ min_b."""
    version: int = 1
    weights: dict = field(default_factory=lambda: {"A": 0.35, "B": 0.35, "C": 0.20, "D": 0.10})
    min_total: float = 3.2
    min_b: int = 2
    radar_min_a: int = 4
    radar_max_b: int = 1
    main_limit: int = 15
    radar_limit: int = 10
    vendor_only_penalty: float = 0.5
    weak_source_penalty: float = 0.5
    weak_sources: tuple = ()
    # max cosine similarity to the last `novelty_window_days` -> D: below the 1st threshold D=5 ... above the 5th D=0
    novelty_thresholds: tuple = (0.70, 0.76, 0.82, 0.88, 0.94)
    novelty_window_days: int = 30
    max_text_chars: int = 8000
    max_items_per_run: int = 300
    backlog_days: int = 3
    concurrency: int = 6
    classifier_min_ratings: int = 100
    classifier_top_n: int = 40


def load_rubric(path) -> Rubric:
    data = read_yaml(path)
    unknown = sorted(set(data) - {f.name for f in fields(Rubric)})
    if unknown:
        raise ConfigError(f"rubric.yaml: chaves desconhecidas {unknown}")
    values = {k: tuple(v) if isinstance(v, list) else v for k, v in data.items()}
    weights = dict(Rubric().weights)
    weights.update(values.pop("weights", None) or {})
    if set(weights) != {"A", "B", "C", "D"} or abs(sum(weights.values()) - 1.0) > 1e-6:
        raise ConfigError(f"rubric.yaml: weights precisa de A, B, C e D somando 1 (recebido {weights})")
    thresholds = values.get("novelty_thresholds", Rubric().novelty_thresholds)
    if len(thresholds) != 5 or list(thresholds) != sorted(thresholds):
        raise ConfigError("rubric.yaml: novelty_thresholds precisa de 5 limiares crescentes")
    return replace(Rubric(), weights=weights, **values)


@dataclass(frozen=True)
class Mutes:
    """config/mute.yaml: drop an item before the LLM; the reason is recorded in `triage`."""
    terms: tuple = ()          # whole word/phrase in title or text, case-insensitive
    title_terms: tuple = ()    # only in the title
    domains: tuple = ()        # URL host or any subdomain of it
    authors: tuple = ()        # exact name, case-insensitive
    sources: tuple = ()        # item source ("rss:marktechpost"); a trailing * matches a prefix ("rss:*")

    def match(self, item) -> str | None:
        title = item.title or ""
        for term in self.title_terms:
            if contains_term(title, term):
                return f"mute: '{term}' no título"
        body = f"{title} {item.text or ''}"
        for term in self.terms:
            if contains_term(body, term):
                return f"mute: termo '{term}'"
        host = urlsplit(item.url or "").netloc.lower()
        for domain in self.domains:
            domain = domain.lower().lstrip(".")
            if host == domain or host.endswith("." + domain):
                return f"mute: domínio {domain}"
        authors = {a.lower() for a in item.authors or []}
        for author in self.authors:
            if author.lower() in authors:
                return f"mute: autor {author}"
        for source in self.sources:
            if item.source == source or (source.endswith("*") and item.source.startswith(source[:-1])):
                return f"mute: fonte {source}"
        return None


def load_mutes(path) -> Mutes:
    data = read_yaml(path)
    unknown = sorted(set(data) - {f.name for f in fields(Mutes)})
    if unknown:
        raise ConfigError(f"mute.yaml: chaves desconhecidas {unknown}")
    not_lists = sorted(k for k, v in data.items() if v is not None and not isinstance(v, list))
    if not_lists:
        raise ConfigError(f"mute.yaml: {not_lists} precisam ser listas")
    return Mutes(**{k: tuple(str(x) for x in (v or [])) for k, v in data.items()})


def _check_models(where, models):
    if not isinstance(models, list) or not models or not all(isinstance(m, str) and "/" in m for m in models):
        raise ConfigError(f"llm.yaml: {where} precisa ser uma lista de ids do OpenRouter (autor/modelo)")


def load_llm_config(path) -> dict:
    """{'tasks': {task: {models?, reasoning?, max_tokens?}}, 'bakeoff': {task: [models]}}."""
    data = read_yaml(path)
    unknown = sorted(set(data) - {"tasks", "bakeoff"})
    if unknown:
        raise ConfigError(f"llm.yaml: chaves desconhecidas {unknown}")
    tasks = data.get("tasks") or {}
    for task, spec in tasks.items():
        if not isinstance(spec, dict) or set(spec) - {"models", "reasoning", "max_tokens"}:
            raise ConfigError(f"llm.yaml: tasks.{task} aceita só models, reasoning e max_tokens")
        if "models" in spec:
            _check_models(f"tasks.{task}.models", spec["models"])
        if spec.get("reasoning") is not None and spec["reasoning"] not in REASONING_LEVELS:
            raise ConfigError(f"llm.yaml: tasks.{task}.reasoning inválido: {spec['reasoning']}")
        if "max_tokens" in spec and (not isinstance(spec["max_tokens"], int) or spec["max_tokens"] <= 0):
            raise ConfigError(f"llm.yaml: tasks.{task}.max_tokens precisa ser inteiro positivo")
    bakeoff = data.get("bakeoff") or {}
    for task, models in bakeoff.items():
        _check_models(f"bakeoff.{task}", models)
    return {"tasks": tasks, "bakeoff": bakeoff}


@dataclass(frozen=True)
class AppConfig:
    rubric: Rubric
    mutes: Mutes
    llm: dict


def load_config(config_dir) -> AppConfig:
    config_dir = Path(config_dir)
    return AppConfig(rubric=load_rubric(config_dir / "rubric.yaml"),
                     mutes=load_mutes(config_dir / "mute.yaml"),
                     llm=load_llm_config(config_dir / "llm.yaml"))

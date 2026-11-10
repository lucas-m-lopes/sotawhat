"""config/tools_radar.yaml: the fronts of the radar (GitHub searches) and its limits."""
from dataclasses import dataclass, field
from pathlib import Path

from sotawhat.configfiles import ConfigError, read_yaml

LIMITS = {"active_min_stars": 50, "active_pushed_days": 14, "new_created_days": 45, "new_min_stars": 20,
          "per_query": 30, "search_pause_s": 2.2, "track_max": 400, "forget_days": 60, "hn_days": 7,
          "hn_min_points": 20, "judge_top": 30, "report_top": 10, "per_front": 4, "min_relevance": 3,
          "min_stars_week": 30, "min_downloads_week": 1000, "min_hn_points": 50, "test_after_days": 14}


@dataclass(frozen=True)
class Front:
    key: str
    label: str
    queries: tuple


@dataclass
class RadarConfig:
    fronts: dict                                   # key -> Front
    limits: dict = field(default_factory=lambda: dict(LIMITS))

    def label(self, key) -> str:
        front = self.fronts.get(key)
        return front.label if front is not None else "fora das frentes"


def load_radar(path) -> RadarConfig:
    path = Path(path)
    if not path.exists():
        raise ConfigError(f"{path.name} não existe (o radar de ferramentas precisa das frentes)")
    data = read_yaml(path)
    fronts = {}
    for key, spec in (data.get("fronts") or {}).items():
        spec = spec or {}
        queries = tuple(q.strip() for q in spec.get("queries") or [] if isinstance(q, str) and q.strip())
        if not queries:
            raise ConfigError(f"{path.name}: a frente {key!r} não tem buscas")
        fronts[key] = Front(key, spec.get("label") or key, queries)
    if not fronts:
        raise ConfigError(f"{path.name}: nenhuma frente")
    limits = data.get("limits") or {}
    unknown = sorted(set(limits) - set(LIMITS))
    if unknown:
        raise ConfigError(f"{path.name}: limites desconhecidos {unknown}")
    return RadarConfig(fronts, {**LIMITS, **limits})

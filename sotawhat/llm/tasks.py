# sotawhat/llm/tasks.py
"""Default task -> models matrix (SDD §6.6). Primary first, fallbacks from other model families."""
from dataclasses import dataclass, replace

DEEPSEEK_FLASH = "deepseek/deepseek-v4.1-flash-1017"
MIMO_FLASH = "xiaomi/mimo-v2.6-flash"
MIMO_PRO = "xiaomi/mimo-v2.6-pro"
GLM = "z-ai/glm-5.3"
GLM_FLASH = "z-ai/glm-5.3-flash"
MINIMAX_FLASH = "minimax/minimax-m3.1-flash"
KIMI_PRO = "moonshotai/kimi-k3.1-pro"     # lessons: escalation after 2 failed repairs (best open model on AA-3D)


@dataclass(frozen=True)
class TaskSpec:
    models: tuple
    reasoning: str | None = None   # None = model default; otherwise "low" or "high" (accepted by every
                                   # model below: GLM/MiniMax reject "none", DeepSeek V4.1 rejects "medium")
    max_tokens: int = 2000


DEFAULT_TASKS = {
    "triage": TaskSpec((DEEPSEEK_FLASH, MIMO_FLASH, GLM_FLASH), "low", 1500),
    # DeepSeek and GLM had the best strict-JSON rates in the 2026-11-08 bake-off (MiMo: 77% valid at first try)
    "segment": TaskSpec((DEEPSEEK_FLASH, GLM_FLASH), "low", 6000),
    "vision": TaskSpec((MIMO_FLASH, GLM_FLASH, MINIMAX_FLASH), "low", 1500),
    "extract": TaskSpec((DEEPSEEK_FLASH, MIMO_PRO, GLM), "high", 12000),
    "resolve": TaskSpec((DEEPSEEK_FLASH, GLM_FLASH), "low", 600),     # entity-resolution judge (P3)
    # idea engine (P4): the callers pass the model per call to rotate families; these are the defaults
    "ideate": TaskSpec((DEEPSEEK_FLASH, MIMO_PRO, GLM_FLASH), "high", 5000),
    "critique": TaskSpec((GLM_FLASH, DEEPSEEK_FLASH), "high", 5000),
    "judge": TaskSpec((DEEPSEEK_FLASH, GLM_FLASH, MIMO_PRO), "low", 2500),
    "synth": TaskSpec((DEEPSEEK_FLASH, MIMO_PRO), "high", 12000),
    "accounts": TaskSpec((DEEPSEEK_FLASH, GLM_FLASH), "low", 3000),   # Instagram accounts to scan (P5)
    # lessons (aulas 3D): the economic scenario of docs/research/reports/Aulas didáticas animadas em 3D.md;
    # three.js scenes pass (MIMO_PRO, DEEPSEEK_FLASH) per call, escalation passes (KIMI_PRO, MIMO_PRO)
    "lesson_plan": TaskSpec((DEEPSEEK_FLASH, MIMO_PRO, GLM_FLASH), "high", 24000),
    "lesson_facts": TaskSpec((DEEPSEEK_FLASH, GLM_FLASH), "low", 4000),
    "lesson_code": TaskSpec((DEEPSEEK_FLASH, MIMO_PRO), "high", 20000),
    "smoke": TaskSpec((DEEPSEEK_FLASH,), "low", 600),
}


def resolve(task, settings=None, overrides=None) -> TaskSpec:
    """Defaults < config/llm.yaml `tasks` (overrides) < SOTAWHAT_MODEL_<TASK> for the primary model."""
    spec = DEFAULT_TASKS[task]
    custom = (overrides or {}).get(task) or {}
    if custom:
        spec = replace(spec, models=tuple(custom.get("models") or spec.models),
                       reasoning=custom.get("reasoning", spec.reasoning),
                       max_tokens=custom.get("max_tokens", spec.max_tokens))
    override = settings.model_override(task) if settings is not None else ""
    if override:
        spec = replace(spec, models=(override,) + tuple(m for m in spec.models if m != override))
    return spec

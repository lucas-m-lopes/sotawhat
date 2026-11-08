# sotawhat/llm/tasks.py
"""Default task -> models matrix (SDD §6.6). Primary first, fallbacks from other model families."""
from dataclasses import dataclass, replace

DEEPSEEK_FLASH = "deepseek/deepseek-v4.1-flash-1017"
MIMO_FLASH = "xiaomi/mimo-v2.6-flash"
MIMO_PRO = "xiaomi/mimo-v2.6-pro"
GLM = "z-ai/glm-5.3"
GLM_FLASH = "z-ai/glm-5.3-flash"
MINIMAX_FLASH = "minimax/minimax-m3.1-flash"


@dataclass(frozen=True)
class TaskSpec:
    models: tuple
    reasoning: str | None = None   # None = model default; otherwise "low" or "high" (accepted by every
                                   # model below: GLM/MiniMax reject "none", DeepSeek V4.1 rejects "medium")
    max_tokens: int = 2000


DEFAULT_TASKS = {
    "triage": TaskSpec((DEEPSEEK_FLASH, MIMO_FLASH, GLM_FLASH), "low", 1500),
    "segment": TaskSpec((MIMO_FLASH, DEEPSEEK_FLASH), "low", 4000),
    "vision": TaskSpec((MIMO_FLASH, GLM_FLASH, MINIMAX_FLASH), "low", 1500),
    "extract": TaskSpec((DEEPSEEK_FLASH, MIMO_PRO, GLM), "high", 12000),
    "synth": TaskSpec((DEEPSEEK_FLASH, MIMO_PRO), "high", 12000),
    "smoke": TaskSpec((DEEPSEEK_FLASH,), "low", 600),
}


def resolve(task, settings=None) -> TaskSpec:
    spec = DEFAULT_TASKS[task]
    override = settings.model_override(task) if settings is not None else ""
    if override:
        spec = replace(spec, models=(override,) + tuple(m for m in spec.models if m != override))
    return spec

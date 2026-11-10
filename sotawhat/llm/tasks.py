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
    "radar": TaskSpec((DEEPSEEK_FLASH, GLM_FLASH), "low", 6000),      # tools radar judge, 10 repositories a call
    # idea engine (P4): the callers pass the model per call to rotate families; these are the defaults
    "ideate": TaskSpec((DEEPSEEK_FLASH, MIMO_PRO, GLM_FLASH), "high", 5000),
    "critique": TaskSpec((GLM_FLASH, DEEPSEEK_FLASH), "high", 5000),
    "judge": TaskSpec((DEEPSEEK_FLASH, GLM_FLASH, MIMO_PRO), "low", 2500),
    "synth": TaskSpec((DEEPSEEK_FLASH, MIMO_PRO), "high", 12000),
    "accounts": TaskSpec((DEEPSEEK_FLASH, GLM_FLASH), "low", 3000),   # Instagram accounts to scan (P5)
    # lessons (aulas 3D): the economic scenario of docs/research/reports/Aulas didáticas animadas em 3D.md;
    # sotawhat/lessons/coder.py passes the models per call (PRIMARY, ESCALATE, VISUAL_FIX); these are the defaults
    "lesson_plan": TaskSpec((DEEPSEEK_FLASH, MIMO_PRO, GLM_FLASH), "high", 24000),
    "lesson_facts": TaskSpec((DEEPSEEK_FLASH, GLM_FLASH), "low", 4000),
    "lesson_code": TaskSpec((DEEPSEEK_FLASH, MIMO_PRO), "high", 32000),           # Manim scenes and repairs
    # three.js scenes and visual fixes: MiMo-V2.6-Pro with high reasoning spent ~16k of 20k tokens thinking and cut
    # the code off (truncated JS, invalid JSON) in the pilot, so low reasoning and room for the code
    "lesson_code_3d": TaskSpec((MIMO_PRO, GLM_FLASH), "low", 24000),
    "lesson_fix": TaskSpec((MIMO_PRO, GLM_FLASH), "low", 24000),                  # sees the frames
    "lesson_critic": TaskSpec((MIMO_FLASH, GLM_FLASH), "low", 6000),             # G4: looks at the frames of a scene
    # HyperFrames lessons: the LLM no longer draws; it picks a scene template per scene and fills its data and the
    # action of each sentence (sotawhat/lessons/storyboard.py). Structure, not code: a cheap model with reasoning
    "lesson_storyboard": TaskSpec((DEEPSEEK_FLASH, MIMO_PRO), "high", 32000),
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

# sotawhat/lessons/coder.py
"""One scene, from storyboard to video.

1. The LLM writes the code (Manim or three.js); the code policy and the renderer judge it. The renderer's layout
   check covers arrows left behind, arrows before their target, overlaps and clutter.
2. Each error goes back for a repair. After two failures the scene escalates to another model family (Kimi K3.1
   Pro in the balanced scenario). On the last attempt layout problems only warn.
3. Visual review (G4): a vision model looks at the frame at the end of every sentence. A serious defect goes back,
   with the frames, to a model that sees images (MiMo-V2.6-Pro), at most twice. If a visual fix does not render,
   the last good version stays.
4. A scene that never renders becomes a deterministic slide (title and the scene's terms), so the lesson still comes
   out, and the report says so."""
import base64
import json
import shutil
import subprocess
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from sotawhat.lessons import render as rd
from sotawhat.llm.gateway import LLMFailure
from sotawhat.llm.prompts import load as load_prompt
from sotawhat.llm.schemas import _Portuguese
from sotawhat.llm.tasks import DEEPSEEK_FLASH, KIMI_PRO, MIMO_PRO

PRIMARY = {"manim": (DEEPSEEK_FLASH, MIMO_PRO), "three": (MIMO_PRO, DEEPSEEK_FLASH)}
# after two failures the scene goes to another family; Kimi K3.1 Pro only in the balanced scenario: in the pilot two
# Kimi repairs cost US$ 0.26 of a US$ 0.33 lesson
ESCALATE = {"economico": {"manim": (MIMO_PRO, DEEPSEEK_FLASH), "three": (DEEPSEEK_FLASH, MIMO_PRO)},
            "equilibrado": {"manim": (KIMI_PRO, MIMO_PRO), "three": (KIMI_PRO, MIMO_PRO)}}
VISUAL_FIX = (MIMO_PRO,)            # sees the frames
PROMPTS = {"manim": "lesson_manim_v2", "three": "lesson_three_v1"}
CRITIC_PROMPT = "lesson_critic_v1"
MAX_ATTEMPTS, MAX_VISUAL_FIXES = 4, 2


class SceneCode(BaseModel):
    code: str = Field(description="o arquivo completo da cena")


class VisualDefect(_Portuguese):
    frame: int = Field(description="número do quadro, 1 = primeira imagem")
    kind: Literal["seta_solta", "sobreposicao", "cortado", "ilegivel", "quebrado", "desencontro"]
    where: str = Field(description="onde está o defeito: posição e elemento")
    fix: str = Field(description="como corrigir, em uma frase curta")
    severity: Literal["grave", "leve"]


class VisualReview(_Portuguese):
    defects: list[VisualDefect]


def brief(plan, n, durations) -> str:
    scene = plan.scenes[n - 1]
    neighbours = [f"cena anterior: {plan.scenes[n - 2].title}" if n > 1 else "esta é a primeira cena",
                  f"próxima cena: {plan.scenes[n].title}" if n < len(plan.scenes) else "esta é a última cena"]
    lines = [f"Aula: {plan.title}", f"Processo explicado: {plan.process}", f"Cena {n} de {len(plan.scenes)}: "
             f"{scene.title} ({'; '.join(neighbours)})", f"Objetivo da cena: {scene.goal}"]
    if scene.mode == "three":
        lines.append(f"Por que 3D: {scene.why_3d}")
    lines.append("Termos na tela: " + ("; ".join(f"{t.term} = {t.gloss_pt}" for t in scene.labels) or "nenhum"))
    lines += ["", f"{len(scene.beats)} frases (beats), nesta ordem:"]
    for k, (beat, seconds) in enumerate(zip(scene.beats, durations), 1):
        lines.append(f"{k}. [{seconds:.1f} s] narração: {beat.narration}\n   visual: {beat.visual}")
    return "\n".join(lines) + "\n\n" + skeleton(scene, durations)


def skeleton(scene, durations) -> str:
    """The frame the code must fill: one beat per sentence (a wrong count was the most common failure)."""
    if scene.mode == "manim":
        body = "".join(f"        # frase {k}: {b.narration[:70]}\n        self.beat(...)\n"
                       for k, b in enumerate(scene.beats, 1))
        return (f"Esqueleto obrigatório (exatamente {len(scene.beats)} chamadas a self.beat, uma por frase):\n"
                "from lesson_kit import *\n\n\nclass Cena(LessonScene):\n    def construct(self):\n" + body)
    starts, acc = [], 0.0
    for d in durations:
        starts.append((acc, acc + d))
        acc += d
    body = "".join(f"      // frase {k} = beats[{k - 1}] ({a:.1f}–{b:.1f} s): {beat.narration[:60]}\n"
                   for k, (beat, (a, b)) in enumerate(zip(scene.beats, starts), 1))
    return ("Esqueleto obrigatório:\nexport default function build(kit) {\n  // crie os objetos aqui\n  return {\n"
            "    update(t) {\n" + body + "    },\n  };\n}")


def _ask(gateway, messages, models) -> str:
    return gateway.structured("lesson_code", messages, SceneCode, models=models).code


def slide_code(scene) -> str:
    """The fallback: the scene's title, its goal and its terms, one per sentence (no LLM)."""
    points = [f"{t.term} — {t.gloss_pt}" for t in scene.labels] or [scene.goal]
    return (
        "import textwrap\n\nfrom lesson_kit import *\n\n\nclass Cena(LessonScene):\n    def construct(self):\n"
        f"        self.add(title({scene.title[:60]!r}))\n"
        f"        goal = Paragraph(*textwrap.wrap({scene.goal!r}, 60), font_size=26, color=C_MUTED).move_to([0, 2.3, 0])\n"
        f"        points = {points!r}\n        shown = VGroup()\n"
        f"        for i in range({len(scene.beats)}):\n"
        "            if i == 0:\n                self.beat(FadeIn(goal))\n                continue\n"
        "            if i - 1 >= len(points):\n                self.beat()\n                continue\n"
        "            item = Paragraph(*textwrap.wrap(points[i - 1], 56), font_size=28, color=C_TEXT)\n"
        "            if len(shown) == 4:\n                old = shown[0]\n                shown.remove(old)\n"
        "                self.remove(old)\n"
        "            item.next_to(shown[-1] if len(shown) else goal, DOWN, buff=0.35).set_x(0)\n"
        "            shown.add(item)\n            self.beat(FadeIn(item, shift=UP * 0.2))\n")


def _render(tools, mode, lessons_root, scene_dir, kit_dir, cache_dir, code, lenient):
    problems = rd.python_problems(code) if mode == "manim" else rd.js_problems(code)
    if problems:
        raise rd.RenderError("política de código: " + "; ".join(problems))
    if mode == "manim":
        rd.render_manim(tools, scene_dir, kit_dir, cache_dir, lenient=lenient)
    else:
        rd.render_three(tools, lessons_root, scene_dir, lenient=lenient)


# --- visual review (G4) ---------------------------------------------------------------------------------------
def frames_of(tools, video, durations, out_dir) -> list:
    """The frame at the end of each sentence, 960×540 JPEG."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths, end = [], 0.0
    for k, seconds in enumerate(durations, 1):
        end += seconds
        path = out_dir / f"f{k:02d}.jpg"
        subprocess.run([tools.ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{max(0.0, end - 0.12):.2f}",
                        "-i", str(video), "-frames:v", "1", "-vf", "scale=960:540", "-q:v", "5", str(path)],
                       check=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        paths.append(path)
    return paths


def _image(path) -> dict:
    return {"type": "image_url",
            "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(Path(path).read_bytes()).decode("ascii")}}


def review(gateway, frames, scene) -> list:
    """Gate G4 -> [VisualDefect] for the frames at the end of each sentence."""
    lines = [f"{k}. narração: {b.narration}\n   visual pretendido: {b.visual}" for k, b in enumerate(scene.beats, 1)]
    content = [{"type": "text", "text": f"Cena: {scene.title}\nFrases, na ordem das imagens:\n" + "\n".join(lines)}]
    content += [_image(f) for f in frames]
    out = gateway.structured("lesson_critic", [{"role": "system", "content": load_prompt(CRITIC_PROMPT)},
                                               {"role": "user", "content": content}], VisualReview)
    return [d for d in out.defects if 1 <= d.frame <= len(frames)]


def _visual_round(gateway, tools, mode, lessons_root, scene_dir, kit_dir, cache_dir, scene, durations, messages, code,
                  report, log, n) -> str | None:
    """One review; when it finds serious defects, one fix shown the frames. -> the new code, or None to stop."""
    frames = frames_of(tools, scene_dir / "out.mp4", durations, scene_dir / "frames")
    try:
        defects = review(gateway, frames, scene)
    except LLMFailure as exc:
        report["visual"].append({"error": str(exc)[:200]})
        return None
    serious = [d for d in defects if d.severity == "grave"]
    report["visual"].append({"defects": [d.model_dump() for d in defects]})
    if not serious:
        return None
    log(f"  cena {n}: revisão visual achou {len(serious)} defeito(s) grave(s); corrigindo com as imagens")
    listing = "\n".join(f"- quadro {d.frame} ({d.kind}): {d.where} → {d.fix}" for d in serious)
    content = [{"type": "text", "text": "A revisão visual dos quadros (um por frase, na ordem) achou estes defeitos:\n"
                                        f"{listing}\n\nCorrija o código para eliminá-los sem piorar o resto e devolva o "
                                        "arquivo completo, seguindo o contrato."}]
    content += [_image(f) for f in frames]
    fix = messages + [{"role": "assistant", "content": json.dumps({"code": code}, ensure_ascii=False)},
                      {"role": "user", "content": content}]
    try:
        return gateway.structured("lesson_code", fix, SceneCode, models=VISUAL_FIX).code
    except LLMFailure as exc:
        report["visual"].append({"error": str(exc)[:200]})
        return None


def build_scene(gateway, tools, lessons_root, scene_dir, kit_dir, cache_dir, plan, n, durations, log=print,
                cost_mode="economico", critic=True) -> dict:
    """-> {"mode", "ok", "attempts", "errors", "models", "fallback", "warnings", "visual", "visual_fixes"};
    the video is scene_dir/out.mp4."""
    scene = plan.scenes[n - 1]
    scene_dir = Path(scene_dir)
    scene_dir.mkdir(parents=True, exist_ok=True)
    rd.write_beats(scene_dir, [b.narration for b in scene.beats], durations)
    mode = scene.mode
    code_path = scene_dir / ("scene.py" if mode == "manim" else "scene.js")
    if mode == "three":
        rd.write_three_page(scene_dir, f"{plan.title} · {scene.title}")
    messages = [{"role": "system", "content": load_prompt(PROMPTS[mode])},
                {"role": "user", "content": brief(plan, n, durations)}]
    report = {"mode": mode, "ok": False, "attempts": 0, "errors": [], "models": [], "fallback": False, "warnings": [],
              "visual": [], "visual_fixes": 0}
    if code_path.exists():
        code = code_path.read_text(encoding="utf-8")
        report["models"].append("cache")
    else:
        code = _ask(gateway, messages, PRIMARY[mode])
        report["models"].append(PRIMARY[mode][0])
    for attempt in range(1, MAX_ATTEMPTS + 1):
        report["attempts"] = attempt
        code_path.write_text(code, encoding="utf-8")
        try:
            _render(tools, mode, lessons_root, scene_dir, kit_dir, cache_dir, code, lenient=attempt == MAX_ATTEMPTS)
            report["ok"] = True
            log(f"  cena {n} ({mode}) ok na tentativa {attempt}")
            break
        except rd.RenderError as exc:
            report["errors"].append(str(exc)[:600])
            log(f"  cena {n} ({mode}) falhou na tentativa {attempt}: {str(exc).splitlines()[-1][:160] if str(exc) else '?'}")
            if attempt == MAX_ATTEMPTS:
                break
            models = PRIMARY[mode] if attempt < 2 else ESCALATE[cost_mode][mode]
            report["models"].append(models[0])
            fix = messages + [{"role": "assistant", "content": json.dumps({"code": code}, ensure_ascii=False)},
                              {"role": "user", "content": f"O render falhou:\n{exc}\n\nCorrija a causa e devolva o "
                                                          "arquivo completo, seguindo o contrato."}]
            code = _ask(gateway, fix, models)
    if not report["ok"]:
        (scene_dir / "scene.py").write_text(slide_code(scene), encoding="utf-8")
        rd.render_manim(tools, scene_dir, kit_dir, cache_dir, lenient=True)
        report.update(fallback=True, warnings=_warnings(scene_dir))
        log(f"  cena {n}: virou slide (sem código que renderizasse)")
        return report
    report["warnings"] = _warnings(scene_dir)
    if critic:
        for _ in range(MAX_VISUAL_FIXES):
            new = _visual_round(gateway, tools, mode, lessons_root, scene_dir, kit_dir, cache_dir, scene, durations,
                                messages, code, report, log, n)
            if new is None:
                break
            shutil.copyfile(scene_dir / "out.mp4", scene_dir / "out_ok.mp4")
            code_path.write_text(new, encoding="utf-8")
            try:
                _render(tools, mode, lessons_root, scene_dir, kit_dir, cache_dir, new, lenient=False)
            except rd.RenderError as exc:       # the fix broke the scene: the last good version stays
                report["errors"].append(f"correção visual: {str(exc)[:400]}")
                code_path.write_text(code, encoding="utf-8")
                shutil.copyfile(scene_dir / "out_ok.mp4", scene_dir / "out.mp4")
                break
            code = new
            report["visual_fixes"] += 1
            report["warnings"] = _warnings(scene_dir)
        else:
            frames_of(tools, scene_dir / "out.mp4", durations, scene_dir / "frames")   # frames of the final version
        (scene_dir / "out_ok.mp4").unlink(missing_ok=True)
    return report


def _warnings(scene_dir) -> list:
    path = Path(scene_dir) / "warnings.txt"
    return [l for l in path.read_text(encoding="utf-8").splitlines() if l] if path.exists() else []

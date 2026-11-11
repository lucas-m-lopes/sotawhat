# sotawhat/lessons/three3d.py
"""The mechanism3d scenes (2026-11-11): the three.js the LLM writes for one scene, inside the HyperFrames kit.

The lesson 7 asked for it: its acquisition scene became boxes, where lessons 2 and 5 had shown the gantry, the
tube, the beam and the detector turning around the patient. The storyboard gives the parts and when they act; the
LLM writes only geometry and motion (`build(kit)` → `{update(t), view}`, prompt lesson_three_v2); the kit
(`mountFree` in motion_kit/scene3d.js) owns the camera, the labels, the timing and the look.

Per scene, after the narration (the times are real):
1. the code policy (no imports, DOM, network, timers, Date or Math.random);
2. the headless probe (probe3d.py, in the lessons tools): JavaScript errors and the kit's checks at the end of
   every sentence (a storyboard part not registered, a part off the frame or too small); an error goes back for a
   repair, at most twice (MiMo-V2.6-Pro, then GLM-5.3-Flash);
3. the visual critic on the probe frames, and one fix that sees the frames with serious defects; a fix that breaks
   the probe is dropped and the previous code stays.
A scene that never passes is drawn as the graph of its parts (`compose` without its module), so the lesson still
comes out. The accepted module is data/lessons/<id>/3d/sNN.js, with sNN.json holding the key of its brief: a
resume with the same brief pays nothing."""
import hashlib
import json
import subprocess
from pathlib import Path

from sotawhat.lessons import hyperframes as hfm
from sotawhat.lessons import render as rd
from sotawhat.lessons.coder import SceneCode, review
from sotawhat.llm.gateway import LLMFailure
from sotawhat.llm.prompts import load as load_prompt
from sotawhat.llm.tasks import GLM_FLASH, MIMO_PRO

PROMPT = "lesson_three_v2"
KIT_VERSION = "free3d-1"                 # bump when the contract of mountFree changes: the cached modules are redone
WRITE = (MIMO_PRO, GLM_FLASH)
REPAIR = (GLM_FLASH, MIMO_PRO)
VISUAL_FIX = (MIMO_PRO, GLM_FLASH)       # both see images
MAX_REPAIRS, MAX_FIX_FRAMES = 2, 4
PROBE_TIMEOUT = 420
PROBE = Path(__file__).parent / "probe3d.py"


class ProbeError(Exception):
    pass


def brief(plan, n, bscene, data) -> str:
    """What the LLM gets for scene n: the lesson, the scene, its parts (ids, labels, colours, when they appear) and
    every sentence with its local time, its intended visual and the storyboard actions in it."""
    scene = plan.scenes[n - 1]
    lines = [f"Aula: {plan.title}", f"Processo explicado: {plan.process}",
             f"Exemplo da aula: {getattr(plan, 'example', '') or '-'}",
             f"Cena {n} de {len(plan.scenes)}: {scene.title}", f"Objetivo da cena: {scene.goal}",
             f"Duração da cena: {data['dur']:.1f} s", "",
             "Peças do storyboard (registre cada uma com kit.part(id, objeto); as cores vêm de color(id)):"]
    actions = data["actions"]
    for node in bscene.nodes:
        show = next((a["t"] for a in actions if a["do"] == "show" and (not a["ids"] or node.id in a["ids"])), None)
        when = f"aparece em {show:.1f} s" if show is not None else "presente desde o início"
        lines.append(f'- "{node.id}": rótulo "{node.label}"' + (f' ({node.gloss})' if node.gloss else "")
                     + f", papel {node.role}, {when}")
    lines += ["", "Frases (tempo local da cena):"]
    for k, ((a, b), beat) in enumerate(zip(data["beats"], scene.beats)):
        lines.append(f"{k}. [{a:.1f}–{b:.1f} s] narração: {beat.narration}")
        lines.append(f"   visual pretendido: {beat.visual}")
        acts = [x for x in actions if a - 0.5 <= x["t"] < b + 0.3 and x["do"] != "unfocus"]
        if acts:
            lines.append("   ações do storyboard: " + "; ".join(
                f"{x['do']} {','.join(x['ids']) or ''}{' “' + x['text'] + '”' if x['text'] else ''} em {x['t']:.1f} s"
                for x in acts))
    return "\n".join(lines) + "\n\n" + skeleton(bscene, data)


def skeleton(bscene, data) -> str:
    parts = "".join(f'  // part("{n.id}", …);\n' for n in bscene.nodes)
    beats = "".join(f"      // frase {k} = beats[{k}] ({a:.1f}–{b:.1f} s)\n" for k, (a, b) in enumerate(data["beats"]))
    return ("Esqueleto obrigatório:\nexport default function build(kit) {\n"
            "  const { THREE, palette, part, add, material, glow, sprite, rod, stretch, color, beats, dur, progress, "
            "shownAt, ease, lerp, clamp, random } = kit;\n" + parts
            + "  return {\n    view: { azimuth: 30, elevation: 16 },\n    update(t) {\n" + beats + "    },\n  };\n}")


def key_of(text) -> str:
    return hashlib.sha256(f"{KIT_VERSION}\n{load_prompt(PROMPT)}\n{text}".encode("utf-8")).hexdigest()[:20]


def probe_times(data) -> list:
    """The end of every sentence (what the critic compares with the sentence)."""
    return [round(max(0.1, b - 0.12), 2) for _, b in data["beats"]]


def probe_page(work, cid, data, captions, module) -> str:
    """The probe page of one scene, served from the lesson folder (it uses the kit copied into hf/assets)."""
    page = work / "3d" / f"probe-{cid}.html"
    head = "".join(f'<link rel="stylesheet" href="../hf/assets/kit/{c}">' for c in ("kit.css", "player.css"))
    scripts = "".join(f'<script src="../hf/assets/{s}"></script>' for s in ("lib/gsap.min.js", "kit/kit.js", "kit/player.js"))
    body = (f'<script type="module">\nimport {{ mountFree, orbit }} from "../hf/assets/kit/scene3d.js";\n'
            f'import build from "./{module}";\nconst data = {hfm._js(data)};\n'
            f'PLAYER.start({{ probe: true, orbit, scenes: [{{ id: "{cid}", num: data.num, title: data.title, '
            f'dur: data.dur, captions: {hfm._js(captions)}, mount: () => mountFree("{cid}", data, 0, build) }}] }});\n'
            "</script>")
    page.write_text(f'<!doctype html>\n<html lang="pt-BR">\n<head>\n<meta charset="utf-8">\n{head}\n{scripts}\n</head>\n'
                    f"<body>\n{body}\n</body>\n</html>\n", encoding="utf-8")
    return page.relative_to(work).as_posix()


def run_probe(tools, work, page, times, out_dir) -> dict:
    """-> {"errors", "issues": [[k, text]], "frames"} from the probe of one page."""
    try:
        done = tools.run([tools.python, PROBE, work, page, out_dir, "--at", ",".join(f"{t:.2f}" for t in times)],
                         cwd=tools.root, timeout=PROBE_TIMEOUT)
    except subprocess.TimeoutExpired:
        raise ProbeError(f"a sonda passou de {PROBE_TIMEOUT // 60} min: simplifique a cena") from None
    line = next((l for l in reversed(done.stdout.splitlines()) if l.startswith("{")), None)
    if line is None:
        raise ProbeError((done.stderr or done.stdout)[-1500:] or f"a sonda terminou com código {done.returncode}")
    return json.loads(line)


def problems_of(code, result) -> list:
    """What makes the code fail: the policy, JavaScript errors and the kit's checks (with the sentence)."""
    found = list(result.get("errors") or [])
    found += [f"fim da frase {k - 1}: {text}" for k, text in result.get("issues") or []]
    return found


def _ask(gateway, messages, models) -> str:
    return gateway.structured("lesson_code_3d", messages, SceneCode, models=models).code


def build_scene(gateway, tools, work, plan, n, bscene, data, captions, log=print) -> dict:
    """-> {"ok", "cached", "attempts", "errors", "visual", "visual_fixes", "models"}; the module is work/3d/sNN.js."""
    cid = f"s{n:02d}"
    folder = work / "3d"
    folder.mkdir(parents=True, exist_ok=True)
    text = brief(plan, n, bscene, data)
    key = key_of(text)
    final, meta_path = folder / f"{cid}.js", folder / f"{cid}.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    report = {"ok": False, "cached": False, "attempts": 0, "errors": [], "visual": [], "visual_fixes": 0, "models": []}
    if meta.get("key") == key and (final.exists() or not meta.get("ok")):     # a failure is not paid twice
        report.update(meta.get("report") or {}, cached=True)
        report["ok"] = bool(meta.get("ok"))
        return report
    times = probe_times(data)
    messages = [{"role": "system", "content": load_prompt(PROMPT)}, {"role": "user", "content": text}]

    def attempt(code, tag):
        """-> (problems, frames) for a candidate module."""
        policy = rd.js_problems(code)
        if policy:
            return ["política de código: " + "; ".join(policy)], []
        cand = folder / f"{cid}.{tag}.js"
        cand.write_text(code, encoding="utf-8")
        page = probe_page(work, cid, data, captions, cand.name)
        result = run_probe(tools, work, page, times, folder / f"frames-{cid}-{tag}")
        return problems_of(code, result), result.get("frames") or []

    good, frames = None, []
    try:
        code = _ask(gateway, messages, WRITE)
        report["models"].append(WRITE[0])
        for k in range(MAX_REPAIRS + 1):
            report["attempts"] = k + 1
            problems, frames = attempt(code, f"a{k + 1}")
            if not problems:
                good = code
                log(f"  cena {n} (3D livre) passou na sonda na tentativa {k + 1}")
                break
            report["errors"].append("; ".join(problems)[:700])
            log(f"  cena {n} (3D livre) tentativa {k + 1}: {problems[0][:160]}")
            if k == MAX_REPAIRS:
                break
            models = WRITE if k == 0 else REPAIR
            report["models"].append(models[0])
            fix = messages + [{"role": "assistant", "content": json.dumps({"code": code}, ensure_ascii=False)},
                              {"role": "user", "content": "A sonda da cena achou estes problemas:\n- "
                                                          + "\n- ".join(problems[:12])
                                                          + "\n\nCorrija a causa e devolva o módulo completo, "
                                                            "seguindo o contrato."}]
            code = _ask(gateway, fix, models)
        if good is not None and frames:
            good, frames = _visual(gateway, report, messages, good, frames, plan.scenes[n - 1], attempt, log, n)
    except (LLMFailure, ProbeError) as exc:
        report["errors"].append(f"{type(exc).__name__}: {str(exc)[:400]}")
        log(f"  cena {n} (3D livre): {str(exc)[:200]}")
    report["ok"] = good is not None
    if good is not None:
        final.write_text(good, encoding="utf-8")
    else:
        final.unlink(missing_ok=True)
        log(f"  cena {n}: o 3D livre não passou; a cena vira o diagrama das mesmas peças")
    meta_path.write_text(json.dumps({"key": key, "ok": report["ok"], "report": report}, ensure_ascii=False, indent=1),
                         encoding="utf-8")
    for f in folder.glob(f"{cid}.*.js"):
        f.unlink(missing_ok=True)
    return report


def _visual(gateway, report, messages, code, frames, scene, attempt, log, n):
    """The critic on the probe frames; serious defects get one fix that sees those frames. -> (code, frames)."""
    from sotawhat.lessons.coder import _image

    try:
        defects = review(gateway, frames, scene)
    except LLMFailure as exc:
        report["visual"].append({"error": str(exc)[:200]})
        return code, frames
    report["visual"].append({"defects": [d.model_dump() for d in defects]})
    serious = [d for d in defects if d.severity == "grave"]
    if not serious:
        return code, frames
    log(f"  cena {n} (3D livre): o crítico achou {len(serious)} defeito(s) grave(s); corrigindo com as imagens")
    shown = sorted({d.frame for d in serious})[:MAX_FIX_FRAMES]
    listing = "\n".join(f"- quadro {d.frame} ({d.kind}): {d.where} → {d.fix}" for d in serious)
    content = [{"type": "text", "text": "A revisão visual dos quadros (um no fim de cada frase, na ordem) achou estes "
                                        f"defeitos:\n{listing}\n\nOs rótulos, a câmera e as legendas são do kit: "
                                        "corrija a geometria e o movimento para eliminá-los sem piorar o resto e "
                                        "devolva o módulo completo, seguindo o contrato. As imagens são os quadros "
                                        f"{', '.join(map(str, shown))}."}]
    content += [_image(frames[k - 1]) for k in shown]
    fix = messages + [{"role": "assistant", "content": json.dumps({"code": code}, ensure_ascii=False)},
                      {"role": "user", "content": content}]
    try:
        new = gateway.structured("lesson_fix", fix, SceneCode, models=VISUAL_FIX).code
        report["models"].append(VISUAL_FIX[0])
        problems, new_frames = attempt(new, "v1")
    except (LLMFailure, ProbeError) as exc:
        report["visual"].append({"error": str(exc)[:200]})
        return code, frames
    if problems:                       # the fix broke the scene: the checked version stays
        report["errors"].append("correção visual: " + "; ".join(problems)[:400])
        return code, frames
    report["visual_fixes"] += 1
    return new, new_frames


def code_step(gateway, tools, hf, work, plan, board, nar, log=print) -> dict:
    """The mechanism3d scenes of a lesson. -> {"codes": {n: path}, "scenes": {n: report}, "fallback": [n]}."""
    targets = [n for n, s in enumerate(board.scenes, 1) if s.template == "mechanism3d"]
    out = {"codes": {}, "scenes": {}, "fallback": []}
    if not targets:
        return out
    hfm.copy_assets(hf, work / "hf", nar["wav"])          # the probe pages use the kit of the project
    for n, ((start, dur), scene, nscene, bscene) in enumerate(zip(hfm.slots(nar), plan.scenes, nar["scenes"],
                                                                 board.scenes), 1):
        if n not in targets:
            continue
        data = hfm.scene_data(n, scene, bscene, nscene, start, dur)
        report = build_scene(gateway, tools, work, plan, n, bscene, data, hfm.scene_captions(nscene, start), log=log)
        out["scenes"][n] = report
        if report["ok"]:
            out["codes"][n] = work / "3d" / f"s{n:02d}.js"
        else:
            out["fallback"].append(n)
    return out

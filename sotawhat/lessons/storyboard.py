# sotawhat/lessons/storyboard.py
"""The storyboard of a HyperFrames lesson: the LLM no longer draws. For each scene of the plan it fills the scene
template of the kit (sotawhat/lessons/motion_kit) that the plan chose — the parts of a diagram, the bars, the
curves of a chart, the events of a timeline, the cells of a comparison, the organ of a 3D volume — and, for each
narration sentence, the actions that happen while it is spoken (show, focus, draw a link, turn scores into
weights, cut the volume…) with the word that triggers them.

Layout, arrows, motion, type and colour belong to the templates, so a link always leaves the border of its
source and reaches the border of its target, and it fades together with them. `validate` checks the references
and the limits and repairs what it can (a ROC curve is even drawn from its AUC, so the number said, the area
painted and the curve agree); what it cannot repair goes back to the LLM once."""
import math
import re
import unicodedata
from statistics import NormalDist
from typing import Literal

from pydantic import Field

from sotawhat.llm.prompts import load as load_prompt
from sotawhat.llm.schemas import _Portuguese

PROMPT = "lesson_storyboard_v2"
TEMPLATES = ("graph", "bars", "chart", "timeline", "compare", "vectors3d", "patches", "volume3d")
TEMPLATES_3D = ("vectors3d", "volume3d")
ROLES = ("token", "embedding", "query", "key", "value", "score", "weight", "output", "neutral", "alert", "info")
MAX_VISIBLE, MAX_COLS, MAX_ROWS = 7, 6, 5
LABEL_MAX, GLOSS_MAX, NOTE_MAX = 24, 34, 44
ROC_X = (0.0, 0.01, 0.025, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)
_STAGE = re.compile(r"^\s*(limpa|limpe|limpamos)\s+a\s+tela\s*[.,;:!]?\s*", re.I)

Role = Literal["token", "embedding", "query", "key", "value", "score", "weight", "output", "neutral", "alert", "info"]


class Node(_Portuguese):
    id: str = Field(description="id curto e único na cena: q, k1, emb, soma")
    label: str = Field(description="texto na tela, até 24 caracteres (termo em inglês pode ficar em inglês)")
    kind: Literal["box", "token", "vector", "matrix", "stack", "stat"]
    role: Role
    col: int = Field(description="coluna 0–5, da esquerda para a direita")
    row: int = Field(description="linha 0–4 dentro da coluna, de cima para baixo")
    panel: int = Field(description="1, ou 2 para o segundo diagrama de uma cena que troca de quadro")
    gloss: str = Field(description="texto pequeno sob o rótulo, até 34 caracteres, ou vazio")
    values: list[float] = Field(description="vector: 3 a 5 números; stat: [] (o número vai no label); outros: []")


class Edge(_Portuguese):
    id: str
    source: str = Field(description="id do nó de origem")
    target: str = Field(description="id do nó de destino")
    label: str = Field(description="rótulo curto sobre a ligação (até 12 caracteres) ou vazio")
    role: Role


class Bar(_Portuguese):
    id: str
    label: str = Field(description="o item, até 16 caracteres")
    value: float = Field(description="o score bruto do item")
    role: Role


class Vector3D(_Portuguese):
    id: str
    label: str = Field(description="até 20 caracteres, ex.: query · nódulo")
    role: Role
    x: float
    y: float
    z: float


class Patches(_Portuguese):
    image: Literal["ultrassom", "patologia", "raio-x", "tomografia", "nenhuma"]
    rows: int = Field(description="2 a 6; 0 quando a cena não usa patches")
    cols: int = Field(description="2 a 6; 0 quando a cena não usa patches")
    focus_row: int
    focus_col: int


class Axes(_Portuguese):
    x_label: str = Field(description="o que o eixo x mede, até 30 caracteres; vazio fora do chart")
    y_label: str = Field(description="o que o eixo y mede, até 30 caracteres; vazio fora do chart")
    x_min: float
    x_max: float
    y_min: float
    y_max: float


class Series(_Portuguese):
    id: str
    label: str = Field(description="o nome da curva, até 22 caracteres")
    role: Role
    points: list[list[float]] = Field(description="pontos [x, y] em ordem de x, de 2 a 30; [] numa ROC dada pela auc")
    auc: float = Field(description="curva ROC: a AUC entre 0,5 e 1, e o kit desenha a curva com essa área; outras: 0")


class Event(_Portuguese):
    id: str
    when: str = Field(description="o ano ou a fase, até 10 caracteres: 1972, 2017, fase 2")
    label: str = Field(description="o marco, até 26 caracteres")
    gloss: str = Field(description="um detalhe curto, até 34 caracteres, ou vazio")
    role: Role


class Column(_Portuguese):
    id: str
    title: str = Field(description="a alternativa comparada, até 22 caracteres")
    role: Role


class Row(_Portuguese):
    id: str
    label: str = Field(description="o atributo comparado, até 22 caracteres")
    cells: list[str] = Field(description="um texto curto por coluna, na ordem das colunas, até 24 caracteres cada")


class Volume(_Portuguese):
    organ: Literal["pulmão", "fígado", "cérebro", "rim", "coração", "corpo", "nenhum"]
    finding: Literal["nódulo", "massa", "nenhum"]
    modality: Literal["tomografia", "ressonância", "nenhuma"]
    slices: int = Field(description="quantas fatias o volume mostra, 8 a 24; 0 quando a cena não usa volume")


class FormulaPart(_Portuguese):
    id: str
    tex: str = Field(description="um pedaço da fórmula em LaTeX (KaTeX), ex.: q \\cdot k")


class Action(_Portuguese):
    do: Literal["show", "hide", "focus", "unfocus", "dim", "pulse", "label", "flow", "panel", "note", "formula",
                "scale", "softmax", "total", "score", "project", "tokenize", "attend", "conv",
                "area", "mark", "pick", "stack", "slice", "segment"]
    ids: list[str] = Field(description="ids dos elementos que a ação toca (nós, ligações, barras, vetores, curvas, "
                                       "marcos, linhas, colunas, partes da fórmula); vazio quando não se aplica")
    text: str = Field(description="label: o novo texto; note, area e mark: a anotação (até 44 caracteres); "
                                  "outros: vazio")
    value: float = Field(description="scale: o divisor (ex.: 8 para raiz de 64); mark: o x do ponto; slice: a "
                                     "altura do corte de 0 a 1 (0 = pelo achado); outros: 0")
    cue: str = Field(description="uma palavra da frase; a ação começa quando ela é dita (vazio = início da frase)")


class Step(_Portuguese):
    beat: int = Field(description="índice da frase na cena, começando em 0")
    actions: list[Action]


class SceneBoard(_Portuguese):
    scene: int = Field(description="número da cena no plano, começando em 1")
    template: Literal[TEMPLATES]
    nodes: list[Node]
    edges: list[Edge]
    bars: list[Bar]
    vectors: list[Vector3D]
    patches: Patches
    # the defaults only let the first storyboards (lesson 6) load; the strict schema the LLM gets requires them all
    axes: Axes = Field(default_factory=lambda: Axes(x_label="", y_label="", x_min=0, x_max=0, y_min=0, y_max=0))
    series: list[Series] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)
    columns: list[Column] = Field(default_factory=list)
    rows: list[Row] = Field(default_factory=list)
    volume: Volume = Field(default_factory=lambda: Volume(organ="nenhum", finding="nenhum", modality="nenhuma",
                                                          slices=0))
    formula: list[FormulaPart]
    steps: list[Step]


class Storyboard(_Portuguese):
    scenes: list[SceneBoard]


def clean_narration(text) -> str:
    """Drops stage directions that leaked into the narration ("Limpa a tela." was read aloud in lesson 4)."""
    out = _STAGE.sub("", text).strip()
    return out[:1].upper() + out[1:] if out else out


def _fold(word) -> str:
    word = unicodedata.normalize("NFKD", word.lower())
    return "".join(c for c in word if c.isalnum())


def cue_in(cue, sentence) -> bool:
    if not cue.strip():
        return True
    words = {_fold(w) for w in sentence.split()}
    return all(_fold(w) in words for w in cue.split() if _fold(w))


def board_prompt(plan, sentences) -> str:
    """The plan as the storyboard LLM sees it: the example, the scenes with their template, the sentence of each beat
    and the visual it intended."""
    lines = [f"Aula: {plan.title}", f"Objetivo: {plan.objective}"]
    if getattr(plan, "example", ""):
        lines.append(f"Exemplo que atravessa a aula (use estes números): {plan.example}")
    lines.append("")
    for n, scene in enumerate(plan.scenes, 1):
        template = getattr(scene, "template", None)
        if template:
            lines.append(f"## Cena {n}: {scene.title} (modelo de cena do plano: {template})")
        else:
            lines.append(f"## Cena {n}: {scene.title} (modo sugerido no plano: {scene.mode}"
                         f"{'; ' + scene.why_3d if scene.why_3d else ''})")
        lines.append(f"Meta: {scene.goal}")
        for k, (beat, sentence) in enumerate(zip(scene.beats, sentences[n - 1])):
            lines.append(f"- frase {k}: {sentence}")
            lines.append(f"  visual pretendido: {beat.visual}")
        lines.append("")
    return "\n".join(lines)


def _ids(scene) -> dict:
    return {"node": {x.id for x in scene.nodes}, "edge": {x.id for x in scene.edges}, "bar": {x.id for x in scene.bars},
            "vector": {x.id for x in scene.vectors}, "formula": {x.id for x in scene.formula},
            "series": {x.id for x in scene.series}, "event": {x.id for x in scene.events},
            "column": {x.id for x in scene.columns}, "row": {x.id for x in scene.rows}}


def roc_points(auc) -> list:
    """Equal-variance binormal ROC with exactly this area: y = Φ(a + Φ⁻¹(x)), a = √2 · Φ⁻¹(AUC)."""
    nd = NormalDist()
    a = math.sqrt(2) * nd.inv_cdf(min(max(auc, 0.5001), 0.9995))
    out = []
    for x in ROC_X:
        y = 0.0 if x <= 0 else 1.0 if x >= 1 else nd.cdf(a + nd.inv_cdf(x))
        out.append([x, round(y, 4)])
    return out


def trapezoid(points) -> float:
    return sum((x1 - x0) * (y0 + y1) / 2 for (x0, y0), (x1, y1) in zip(points, points[1:]))


def _fix_chart(scene, where, problems) -> None:
    ax = scene.axes
    ax.x_label, ax.y_label = ax.x_label.strip()[:30], ax.y_label.strip()[:30]
    scene.series = scene.series[:4]
    for s in scene.series:
        s.label = s.label.strip()[:22]
        if 0.5 < s.auc < 1:                               # a ROC curve: the kit draws the area the narration says
            s.points = roc_points(s.auc)
        else:
            s.auc = 0.0
            pts = [p[:2] for p in s.points if len(p) >= 2 and all(math.isfinite(v) for v in p[:2])]
            s.points = sorted({p[0]: p for p in pts}.values(), key=lambda p: p[0])[:30]
    pts = [p for s in scene.series for p in s.points]
    if not scene.series or any(len(s.points) < 2 for s in scene.series):
        problems.append(f"{where}: template chart precisa de 1 a 4 curvas com 2 a 30 pontos [x, y] (ou auc na ROC)")
    if pts and (ax.x_min >= ax.x_max or ax.y_min >= ax.y_max):
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        ax.x_min, ax.x_max = min(xs), (max(xs) if max(xs) > min(xs) else min(xs) + 1)
        low = min(0.0, min(ys))
        ax.y_min, ax.y_max = low, (max(ys) if max(ys) > low else low + 1)
    for s in scene.series:                               # the curves stay inside the axes
        s.points = [[min(max(x, ax.x_min), ax.x_max), min(max(y, ax.y_min), ax.y_max)] for x, y in s.points]


def _fix_compare(scene, where, problems) -> None:
    scene.columns = scene.columns[:3]
    scene.rows = scene.rows[:5]
    for c in scene.columns:
        c.title = c.title.strip()[:22]
    for r in scene.rows:
        r.label = r.label.strip()[:22]
        r.cells = [c.strip()[:24] for c in r.cells[:len(scene.columns)]]
        r.cells += [""] * (len(scene.columns) - len(r.cells))
    if not (2 <= len(scene.columns) <= 3 and 2 <= len(scene.rows) <= 5):
        problems.append(f"{where}: template compare precisa de 2 ou 3 colunas e de 2 a 5 linhas")


def validate(board, sentences, planned=None) -> list:
    """Problems that only the LLM can fix -> [str]. Repairs in place what has an obvious fix (lengths, cues that
    are not in the sentence, a link shown before its ends, missing steps, curves out of their axes). `planned`: the
    template of each scene in the plan, which the storyboard must use."""
    problems = []
    if len(board.scenes) != len(sentences):
        problems.append(f"o storyboard tem {len(board.scenes)} cenas; o plano tem {len(sentences)}")
    for n, (scene, said) in enumerate(zip(board.scenes, sentences), 1):
        scene.scene = n
        where = f"cena {n}"
        if planned and n <= len(planned) and planned[n - 1] and scene.template != planned[n - 1]:
            problems.append(f"{where}: use o modelo de cena do plano, {planned[n - 1]} (veio {scene.template})")
        groups = (scene.nodes, scene.edges, scene.bars, scene.vectors, scene.formula, scene.series, scene.events,
                  scene.columns, scene.rows)
        all_ids = [x.id for group in groups for x in group]
        if len(all_ids) != len(set(all_ids)):
            problems.append(f"{where}: ids repetidos")
        ids = _ids(scene)
        known = set(all_ids)
        for node in scene.nodes:
            node.label = node.label.strip()[:LABEL_MAX]
            node.gloss = node.gloss.strip()[:GLOSS_MAX]
            node.col = min(max(node.col, 0), MAX_COLS - 1)
            node.row = min(max(node.row, 0), MAX_ROWS - 1)
            node.panel = 2 if node.panel == 2 else 1
            node.values = node.values[:5] if node.kind == "vector" else []
        for edge in scene.edges:
            if edge.source not in ids["node"] or edge.target not in ids["node"]:
                problems.append(f"{where}: a ligação {edge.id} liga ids que não são nós ({edge.source} → {edge.target})")
            edge.label = edge.label.strip()[:12]
        if scene.template == "graph" and not scene.nodes:
            problems.append(f"{where}: template graph sem nós")
        if scene.template == "bars" and not 2 <= len(scene.bars) <= 6:
            problems.append(f"{where}: template bars precisa de 2 a 6 barras")
        if scene.template == "vectors3d" and not 2 <= len(scene.vectors) <= 6:
            problems.append(f"{where}: template vectors3d precisa de 2 a 6 vetores")
        if scene.template == "patches":
            p = scene.patches
            if p.image == "nenhuma" or p.rows < 1 or p.cols < 1:
                problems.append(f"{where}: template patches precisa de imagem e de 3 a 6 linhas e colunas")
            p.rows, p.cols = min(max(p.rows, 3), 6), min(max(p.cols, 3), 6)     # a 2 × 2 grid does not read as patches
            p.focus_row = min(max(p.focus_row, 0), p.rows - 1)
            p.focus_col = min(max(p.focus_col, 0), p.cols - 1)
        if scene.template == "chart":
            _fix_chart(scene, where, problems)
        if scene.template == "timeline":
            scene.events = scene.events[:7]
            for e in scene.events:
                e.when, e.label, e.gloss = e.when.strip()[:10], e.label.strip()[:26], e.gloss.strip()[:34]
            if len(scene.events) < 2:
                problems.append(f"{where}: template timeline precisa de 2 a 7 marcos")
        if scene.template == "compare":
            _fix_compare(scene, where, problems)
        if scene.template == "volume3d":
            v = scene.volume
            v.slices = min(max(v.slices or 16, 8), 24)
            v.organ = "corpo" if v.organ == "nenhum" else v.organ
            v.modality = "tomografia" if v.modality == "nenhuma" else v.modality
        # one step per sentence, in order; an empty sentence holds the picture
        by_beat = {}
        for step in scene.steps:
            if 0 <= step.beat < len(said):
                by_beat.setdefault(step.beat, []).extend(step.actions)
        missing = [k for k in range(len(said)) if not by_beat.get(k)]
        if len(missing) > max(1, len(said) // 3):
            problems.append(f"{where}: as frases {missing} não têm nenhuma ação")
        scene.steps = [Step(beat=k, actions=by_beat.get(k, [])) for k in range(len(said))]
        shown = set()
        for step in scene.steps:
            for act in step.actions:
                unknown = [i for i in act.ids if i not in known]
                if unknown:
                    problems.append(f"{where}, frase {step.beat}: ids desconhecidos em {act.do}: {unknown}")
                    act.ids = [i for i in act.ids if i in known]
                if not cue_in(act.cue, said[step.beat]):
                    act.cue = ""
                act.text = act.text.strip()[:NOTE_MAX]
                if act.do == "slice":
                    act.value = min(max(act.value, 0.0), 1.0)
                if act.do == "show":
                    for edge in scene.edges:          # a link never appears before both of its ends
                        if edge.id in act.ids:
                            for end in (edge.source, edge.target):
                                if end not in shown and end not in act.ids:
                                    act.ids.append(end)
                    shown.update(act.ids)
            visible = [x for x in shown if x in ids["node"]]
            if scene.template == "graph" and len(visible) > MAX_VISIBLE + 2:
                problems.append(f"{where}, frase {step.beat}: {len(visible)} nós visíveis; o máximo é {MAX_VISIBLE} "
                                "(esconda os antigos ou use o painel 2)")
    for scene in board.scenes:
        if scene.template == "vectors3d":
            untangle(scene)
    sync_scores(board)
    return problems


def dot(a, b) -> float:
    return a.x * b.x + a.y * b.y + a.z * b.z


def untangle(scene, min_deg=8.0, tilt_deg=14.0) -> None:
    """A key drawn exactly along the query hides it in 3D. Tilt it away from the query by adding a component
    perpendicular to it: the angle opens, the dot product (the score the lesson shows) stays the same."""
    query = next((v for v in scene.vectors if v.role == "query"), None)
    if query is None:
        return
    q = (query.x, query.y, query.z)
    qn = math.sqrt(sum(c * c for c in q))
    if qn == 0:
        return
    qh = tuple(c / qn for c in q)
    up = (0.0, 1.0, 0.0) if abs(qh[1]) < 0.9 else (1.0, 0.0, 0.0)
    perp = (qh[1] * up[2] - qh[2] * up[1], qh[2] * up[0] - qh[0] * up[2], qh[0] * up[1] - qh[1] * up[0])
    pn = math.sqrt(sum(c * c for c in perp))
    perp = tuple(c / pn for c in perp)
    sign = 1.0
    for v in scene.vectors:
        if v is query:
            continue
        vec = (v.x, v.y, v.z)
        vn = math.sqrt(sum(c * c for c in vec))
        along = sum(a * b for a, b in zip(vec, qh))
        if vn == 0 or along / vn < math.cos(math.radians(min_deg)):
            continue
        add = math.tan(math.radians(tilt_deg)) * along * sign
        v.x, v.y, v.z = (round(a + b * add, 3) for a, b in zip(vec, perp))
        sign = -sign


def sync_scores(board) -> None:
    """The bars of a scene that follows a vectors3d scene take the dot products shown there (same items): one data
    set drives the lesson, whatever numbers the LLM wrote."""
    scores = {}
    for scene in board.scenes:
        if scene.template == "vectors3d":
            query = next((v for v in scene.vectors if v.role == "query"), None)
            if query:
                scores = {_fold(v.label): round(dot(query, v), 1) for v in scene.vectors if v is not query}
        elif scene.template == "bars" and scores:
            for bar in scene.bars:
                name = _fold(bar.label)
                hit = [s for label, s in scores.items() if name and name in label]
                if len(hit) == 1:
                    bar.value = hit[0]


def planned_templates(plan) -> list | None:
    templates = [getattr(s, "template", None) for s in plan.scenes]
    return templates if any(templates) else None


def make_storyboard(gateway, plan, sentences, models=None) -> tuple:
    """-> (storyboard, remaining problems). One repair round."""
    planned = planned_templates(plan)
    messages = [{"role": "system", "content": load_prompt(PROMPT)},
                {"role": "user", "content": board_prompt(plan, sentences)}]
    board = gateway.structured("lesson_storyboard", messages, Storyboard, models=models)
    problems = validate(board, sentences, planned)
    if problems:
        messages += [{"role": "assistant", "content": board.model_dump_json()},
                     {"role": "user", "content": "Corrija estes problemas e devolva o storyboard inteiro:\n- "
                                                 + "\n- ".join(problems)}]
        board = gateway.structured("lesson_storyboard", messages, Storyboard, models=models)
        problems = validate(board, sentences, planned)
    return board, problems

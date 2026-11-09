# lesson_kit.py — base of every Manim scene of a sotawhat lesson (copied to data/lessons/_kit; do not edit per lesson).
"""A scene reads its narration sentences ("beats") from the JSON in LESSON_SCENE: [{"text", "duration"}].
`self.beat(*animations)` plays what one sentence describes and holds the frame until the sentence ends, so the
picture is always in sync with the voice. The subtitles are drawn here, in the band below y = -2.7.

Layout by construction: `connect(a, b)` is an arrow that follows its two ends and disappears with them, `flow()`
lays out a chain with its arrows, `at()` places things in named zones and `self.clear_stage()` empties the stage
when the scene changes subject. After each beat the picture is checked; a problem raises LayoutError, which goes
back to the LLM that wrote the scene:
- anything outside the frame or in the subtitle band;
- text over text, a text crossing the border of a shape, shapes partially covering each other;
- an arrow left behind when the object at one end left, an arrow that arrives before its target, a loose arrow
  that touches nothing, an arrow that crosses another object;
- LaTeX typed into a Text; more than 16 things on the stage.
Formulas use matplotlib's mathtext (no LaTeX installed)."""
import hashlib
import json
import math
import os
import re
import textwrap
from pathlib import Path

from manim import *  # noqa: F401,F403 - the scenes use the whole manim namespace through this module
from manim import (DOWN, LEFT, RIGHT, UP, Annulus, Arrow, ArrowTip, BackgroundRectangle, Brace, Circle,
                   CurvedArrow, CurvedDoubleArrow, DecimalNumber, DoubleArrow, Ellipse, FadeOut, Line, MarkupText,
                   NumberLine, Paragraph, Polygon, Rectangle, RegularPolygon, RoundedRectangle, Scene, Sector, Square,
                   SurroundingRectangle, SVGMobject, Text, TipableVMobject, VGroup, config)

config.background_color = "#0f141a"
FONT = "Segoe UI"
for _cls in (Text, Paragraph):
    _cls.set_default(font=FONT)

C_TEXT, C_MUTED = "#f2f2f2", "#9aa4b2"
C_BLUE, C_ORANGE, C_GREEN, C_PURPLE = "#4ea1ff", "#ffb74d", "#7bd389", "#b39ddb"
C_RED, C_YELLOW, C_GRAY, C_TEAL = "#ef6f6c", "#ffd54f", "#8a94a6", "#4dd0c4"
SAFE_LEFT, SAFE_RIGHT, SAFE_TOP, SAFE_BOTTOM = -6.75, 6.75, 3.8, -2.7
SUB_Y, SUB_WIDTH = -3.38, 62
MAX_ON_STAGE = 16
ZONES = {"center": (0, 0.4), "left": (-4.3, 0.4), "right": (4.3, 0.4), "top": (0, 2.3), "bottom": (0, -1.6),
         "top-left": (-4.3, 2.3), "top-right": (4.3, 2.3), "bottom-left": (-4.3, -1.6), "bottom-right": (4.3, -1.6)}
_STAGE = {"scene": None, "incoming": set(), "ids": set(), "stamp": None}
_LATEX = re.compile(r"\\[A-Za-z]+|[\^_]\{")


class LayoutError(Exception):
    pass


# --- formulas and the mobjects that would need LaTeX ----------------------------------------------------------
def Formula(tex, color=C_TEXT, font_size=40):
    """A formula in matplotlib mathtext (\\frac, \\sqrt, ^, _, \\mathrm, Greek letters) as a vector mobject."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cache = Path(os.environ.get("LESSON_CACHE", ".")) / "formulas"
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / (hashlib.sha1(tex.encode("utf-8")).hexdigest()[:16] + ".svg")
    if not path.exists():
        matplotlib.rcParams["svg.fonttype"] = "path"
        matplotlib.rcParams["mathtext.fontset"] = "cm"
        fig = plt.figure(figsize=(0.01, 0.01))
        fig.text(0, 0, f"${tex}$", fontsize=40, color="white")
        fig.savefig(path, format="svg", transparent=True, bbox_inches="tight", pad_inches=0.02)
        plt.close(fig)
    mob = SVGMobject(str(path), stroke_width=0).set_color(color)
    tall = 1.0 + 0.9 * min(tex.count("\\frac"), 2)
    mob.set(height=0.62 * font_size / 40 * tall)
    mob.lesson_text = "fórmula"
    return mob


def MathTex(*parts, color=C_TEXT, font_size=40, **_):
    return Formula(" ".join(parts), color=color, font_size=font_size)


Tex = MathTex


def _number_text(value, **kwargs):
    return Text(str(value), font_size=kwargs.pop("font_size", 28), color=C_TEXT)


DecimalNumber.set_default(mob_class=Text)
NumberLine.set_default(label_constructor=Text)


class Matrix(VGroup):
    """A matrix of text entries between drawn brackets (manim's Matrix needs LaTeX for its brackets)."""

    def __init__(self, values, h_buff=1.0, v_buff=0.7, font_size=28, color=C_TEXT, **_):
        super().__init__()
        self._rows = [[_number_text(v, font_size=font_size) for v in row] for row in values]
        for r, row in enumerate(self._rows):
            for c, entry in enumerate(row):
                entry.set_color(color).move_to([c * h_buff, -r * v_buff, 0])
        self.entries = VGroup(*[e for row in self._rows for e in row]).center()
        height, tick = self.entries.height + 0.35, 0.14
        left = VGroup(Line([0, height / 2, 0], [0, -height / 2, 0]), Line([0, height / 2, 0], [tick, height / 2, 0]),
                      Line([0, -height / 2, 0], [tick, -height / 2, 0]))
        right = left.copy().flip(UP)
        left.next_to(self.entries, LEFT, buff=0.2)
        right.next_to(self.entries, RIGHT, buff=0.2)
        self.brackets = VGroup(left, right)
        self.add(left, self.entries, right)

    def get_entries(self):
        return self.entries

    def get_rows(self):
        return VGroup(*[VGroup(*row) for row in self._rows])

    def get_columns(self):
        return VGroup(*[VGroup(*[row[c] for row in self._rows if c < len(row)])
                        for c in range(max(len(r) for r in self._rows))])

    def get_brackets(self):
        return self.brackets


def Title(*parts, **_):
    return title(" ".join(str(p) for p in parts))


def BulletedList(*items, font_size=28, **_):
    return VGroup(*[Text(f"• {item}", font_size=font_size, color=C_TEXT) for item in items]).arrange(
        DOWN, aligned_edge=LEFT, buff=0.25)


def BraceText(mob, text, brace_direction=DOWN, **_):
    brace = Brace(mob, brace_direction)
    return VGroup(brace, Text(text, font_size=24, color=C_TEXT).next_to(brace, brace_direction, buff=0.15))


BraceLabel = BraceText


# --- building blocks ---------------------------------------------------------------------------------------------
def title(text, color=C_TEXT):
    """The scene title at the top; it stays when the stage is cleared."""
    mob = Text(text, font_size=40, color=color).to_edge(UP, buff=0.45)
    mob.lesson_keep = True
    return mob


def label(text, size=28, color=C_TEXT):
    return Text(text, font_size=size, color=color)


def box(text, color=C_BLUE, size=26, width=None, height=None):
    """A rounded box with centered text: VGroup(rectangle, text). The box always fits its text."""
    words = Text(text, font_size=size, color=C_TEXT)
    rect = RoundedRectangle(corner_radius=0.14, width=max(width or 0, words.width + 0.5),
                            height=max(height or 0, words.height + 0.4), stroke_color=color, stroke_width=3,
                            fill_color=color, fill_opacity=0.18)
    return VGroup(rect, words.move_to(rect))


def tokens(words, color=C_BLUE, size=26):
    return VGroup(*[box(w, color=color, size=size) for w in words]).arrange(RIGHT, buff=0.18)


def at(mob, zone):
    """Puts a mobject in a named zone of the stage: center, left, right, top, bottom, top-left, top-right,
    bottom-left, bottom-right."""
    x, y = ZONES[zone]
    return mob.move_to([x, y, 0])


def allow_overlap(*mobs):
    """For overlaps that are the point (a Venn diagram, a heat map over a contour): the check skips them."""
    for mob in mobs:
        for m in mob.get_family():
            m.lesson_overlap_ok = True
    return mobs[0] if len(mobs) == 1 else VGroup(*mobs)


def _family_ids():
    scene = _STAGE["scene"]
    stamp = (scene.renderer.time, len(scene.mobjects))
    if _STAGE["stamp"] != stamp:
        _STAGE["ids"] = {id(m) for top in scene.mobjects for m in top.get_family()}
        _STAGE["stamp"] = stamp
    return _STAGE["ids"]


def _on_stage(mob) -> bool:
    """On the stage and visible, or coming in during the current beat."""
    if _STAGE["scene"] is None or id(mob) in _STAGE["incoming"]:
        return True
    if id(mob) not in _family_ids():
        return False
    return any(_shown(m) for m in mob.get_family())


def connect(a, b, color=C_MUTED, width=4, path_arc=0.0):
    """An arrow from the border of `a` to the border of `b` that follows them when they move and disappears when
    either of them leaves the stage. Create it with GrowArrow(...) in the beat where both ends are on screen."""
    def build():
        return Arrow(a, b, buff=0.12, stroke_width=width, color=color, path_arc=path_arc,
                     max_tip_length_to_length_ratio=0.18)

    link = build()
    link.lesson_link = (a, b)

    def follow(m):
        m.become(build())
        if not (_on_stage(a) and _on_stage(b)):
            m.set_opacity(0)

    link.add_updater(follow)
    return link


def arrow(a, b, color=C_MUTED, width=4):
    """Same as connect(a, b)."""
    return connect(a, b, color=color, width=width)


def flow(*items, direction=RIGHT, buff=1.0, color=C_MUTED):
    """A chain laid out in `direction` with a connect() arrow between neighbours -> (group, arrows)."""
    group = VGroup(*items).arrange(direction, buff=buff)
    return group, VGroup(*[connect(a, b, color=color) for a, b in zip(items, items[1:])])


class Grid(VGroup):
    """rows × cols cells (squares with an optional value); `grid.cell(r, c)`."""

    def __init__(self, rows, cols, values=None, cell=0.55, color=C_GRAY, size=20):
        super().__init__()
        self.rows, self.cols = rows, cols
        for r in range(rows):
            for c in range(cols):
                square = Square(side_length=cell, stroke_color=color, stroke_width=2, fill_color=color, fill_opacity=0.08)
                square.move_to([c * cell, -r * cell, 0])
                group = VGroup(square)
                if values is not None:
                    group.add(Text(str(values[r][c]), font_size=size, color=C_TEXT).move_to(square))
                self.add(group)
        self.center()

    def cell(self, r, c):
        return self[r * self.cols + c]

    def heat(self, weights, color=C_BLUE):
        """Animations that fill each cell with an opacity proportional to its weight (0–1)."""
        return [self.cell(r, c)[0].animate.set_fill(color, opacity=0.1 + 0.85 * float(weights[r][c]))
                for r in range(self.rows) for c in range(self.cols)]


# --- the layout check ------------------------------------------------------------------------------------------
ARROWS = (Arrow, DoubleArrow, CurvedArrow, CurvedDoubleArrow)
SHAPES = (Rectangle, Circle, Ellipse, Polygon, RegularPolygon, Annulus, Sector)
NOT_SHAPES = (BackgroundRectangle, SurroundingRectangle, ArrowTip)


def _shown(m) -> bool:
    return m.has_points() and (m.get_fill_opacity() > 0.05 or m.get_stroke_opacity() > 0.05)


def _text_like(m) -> bool:
    return isinstance(m, (Text, Paragraph, MarkupText)) or bool(getattr(m, "lesson_text", None))


def _box(m):
    return m.get_left()[0], m.get_right()[0], m.get_bottom()[1], m.get_top()[1]


def _area(b) -> float:
    return max(0.0, b[1] - b[0]) * max(0.0, b[3] - b[2])


def _inter(a, b) -> float:
    w, h = min(a[1], b[1]) - max(a[0], b[0]), min(a[3], b[3]) - max(a[2], b[2])
    return w * h if w > 0 and h > 0 else 0.0


def _dist(p, b) -> float:
    return math.hypot(max(b[0] - p[0], 0.0, p[0] - b[1]), max(b[2] - p[1], 0.0, p[1] - b[3]))


def _inside(p, b, shrink=0.12) -> bool:
    w, h = (b[1] - b[0]) * shrink / 2, (b[3] - b[2]) * shrink / 2
    return b[0] + w < p[0] < b[1] - w and b[2] + h < p[1] < b[3] - h


def _name(m) -> str:
    if isinstance(m, Paragraph):
        return "o parágrafo"
    text = getattr(m, "text", "") if isinstance(m, (Text, MarkupText)) else ""
    if text:
        return f"o texto {text[:28]!r}"
    if getattr(m, "lesson_text", None):
        return "a fórmula"
    kind = {"RoundedRectangle": "a caixa", "Rectangle": "o retângulo", "Square": "o quadrado", "Circle": "o círculo",
            "Dot": "o ponto", "Ellipse": "a elipse"}.get(type(m).__name__, f"o {type(m).__name__}")
    return f"{kind} em ({m.get_x():.1f}, {m.get_y():.1f})"


def _arrow_name(m) -> str:
    s, e = m.get_start(), m.get_end()
    return f"a seta de ({s[0]:.1f}, {s[1]:.1f}) a ({e[0]:.1f}, {e[1]:.1f})"


class LessonScene(Scene):
    def setup(self):
        spec = json.loads(Path(os.environ["LESSON_SCENE"]).read_text(encoding="utf-8"))
        self.beats, self._i = spec["beats"], 0
        self.lenient = os.environ.get("LESSON_LENIENT") == "1"
        self.warnings = []
        self._sub = VGroup()
        self.add(self._sub)
        self._arrows = {}               # id(arrow) -> [id of what its start touched, id of what its tip touched]
        _STAGE.update(scene=self, incoming=set(), stamp=None)

    # --- subtitles ------------------------------------------------------------------------
    @staticmethod
    def _chunks(text):
        lines = textwrap.wrap(text, SUB_WIDTH)
        return [lines[i:i + 2] for i in range(0, len(lines), 2)] or [[""]]

    def _subtitle(self, text, duration):
        chunks = self._chunks(text)
        weights = [sum(len(x) for x in c) for c in chunks]
        bounds, acc = [], 0
        for w in weights:
            acc += w
            bounds.append(duration * acc / max(1, sum(weights)))
        start, state = self.renderer.time, {"shown": -1}

        def show(group, dt=0):
            k = next((n for n, b in enumerate(bounds) if self.renderer.time - start < b), len(chunks) - 1)
            if k != state["shown"]:
                state["shown"] = k
                words = Paragraph(*chunks[k], font_size=26, alignment="center", line_spacing=0.6, color=C_TEXT)
                words.move_to([0, SUB_Y, 0])
                group.become(VGroup(BackgroundRectangle(words, fill_opacity=0.6, buff=0.12, color="#000000"), words))

        self._sub.clear_updaters()
        show(self._sub)
        self._sub.add_updater(show)

    # --- beats ----------------------------------------------------------------------------
    def beat(self, *animations, run_time=None):
        """Plays the animations of the next narration sentence and holds the frame until the sentence ends."""
        if self._i >= len(self.beats):
            raise LayoutError(f"beat() foi chamado {self._i + 1} vezes, mas a cena tem {len(self.beats)} frases")
        total = float(self.beats[self._i]["duration"])
        self._subtitle(self.beats[self._i]["text"], total)
        rest = total
        animations = [a for a in animations if a is not None]
        if animations:
            moving = [m for a in animations if getattr(a, "mobject", None) is not None for m in a.mobject.get_family()]
            _STAGE["incoming"] = {id(m) for m in moving}
            for m in moving:            # connect() arrows made before their ends were placed: follow them now
                if m.updaters:
                    m.update(0)
            played = min(run_time or min(1.8, total * 0.6), total)
            self.play(*animations, run_time=played)
            _STAGE["incoming"] = set()
            rest = total - played
        if rest > 0.02:
            self.wait(rest)
        self._check(self._i)
        self._i += 1

    def clear_stage(self, *keep):
        """FadeOut animations for everything on the stage except the title and `keep`: pass them to beat()."""
        kept = {id(k) for k in keep}
        return [FadeOut(m) for m in self.mobjects
                if m is not self._sub and not getattr(m, "lesson_keep", False) and id(m) not in kept]

    # --- the check ------------------------------------------------------------------------
    def _problem(self, message):
        if self.lenient:
            self.warnings.append(message)
            print(f"AVISO de layout: {message}")
        else:
            raise LayoutError(message)

    def _units(self):
        """-> texts, shapes, arrows, others (visible units) and {id(unit): id(its top-level mobject)}."""
        texts, shapes, arrows, others, seen, owner = [], [], [], [], set(), {}
        for top in self.mobjects:
            if top is self._sub:
                continue
            for m in top.get_family():
                if id(m) in seen:
                    continue
                owner[id(m)] = id(top)
                if _text_like(m) or isinstance(m, ARROWS) or isinstance(m, NOT_SHAPES) or \
                        (isinstance(m, TipableVMobject) and m.has_tip()):
                    seen.update(id(d) for d in m.get_family())
                    if isinstance(m, NOT_SHAPES):
                        continue
                    if any(_shown(d) for d in m.get_family()):
                        (texts if _text_like(m) else arrows).append(m)
                    continue
                if not _shown(m):
                    continue
                (shapes if isinstance(m, SHAPES) else others).append(m)
        return texts, shapes, arrows, others, owner

    def _check(self, i):
        n = i + 1
        texts, shapes, arrows, others, owner = self._units()
        on_stage = [m for m in self.mobjects if m is not self._sub and not getattr(m, "lesson_keep", False)
                    and any(_shown(d) for d in m.get_family())]
        if len(on_stage) > MAX_ON_STAGE:
            self._problem(f"frase {n}: {len(on_stage)} elementos na tela (máximo {MAX_ON_STAGE}); limpe com "
                          f"self.beat(*self.clear_stage(), ...) ao mudar de assunto")
        for m in texts + shapes + arrows + others:
            left, right, bottom, top = _box(m)
            name = _arrow_name(m) if m in arrows else _name(m)
            if left < SAFE_LEFT - 0.05 or right > SAFE_RIGHT + 0.05 or top > SAFE_TOP + 0.05:
                self._problem(f"frase {n}: {name} sai do quadro (x de {left:.1f} a {right:.1f}, topo {top:.1f}); "
                              "a área útil é x ∈ [-6.75, 6.75], y ≤ 3.8")
            elif bottom < SAFE_BOTTOM - 0.05:
                self._problem(f"frase {n}: {name} invade a faixa das legendas (base em y = {bottom:.1f}; "
                              "mantenha y ≥ -2.7)")
        for t in texts:
            content = getattr(t, "text", "") if isinstance(t, (Text, MarkupText)) else ""
            if content and _LATEX.search(content):
                self._problem(f"frase {n}: {_name(t)} tem LaTeX dentro de Text; use Formula(r\"...\") ou um "
                              "símbolo Unicode (Σ, √, ≈)")
        boxes = {id(m): _box(m) for m in texts + shapes + others}
        for a in range(len(texts)):
            for b in range(a + 1, len(texts)):
                ba, bb = boxes[id(texts[a])], boxes[id(texts[b])]
                if _inter(ba, bb) > 0.3 * max(1e-6, min(_area(ba), _area(bb))):
                    self._problem(f"frase {n}: {_name(texts[a])} e {_name(texts[b])} se sobrepõem; use "
                                  "arrange/next_to ou tire um deles com FadeOut")
        # overlaps between different objects (a drawing made of overlapping shapes, a stack of slices, is one object)
        solid = [s for s in shapes if _area(boxes[id(s)]) > 0.04 and not getattr(s, "lesson_overlap_ok", False)]
        for t in texts:
            if getattr(t, "lesson_overlap_ok", False):
                continue
            bt = boxes[id(t)]
            for s in solid:
                if owner.get(id(s)) == owner.get(id(t)):
                    continue
                share = _inter(bt, boxes[id(s)]) / max(1e-6, _area(bt))
                if 0.12 < share < 0.85:
                    self._problem(f"frase {n}: {_name(t)} cruza a borda de {_name(s)}; ponha o texto dentro "
                                  "(box(...) ajusta a caixa ao texto) ou ao lado, com next_to")
        for a in range(len(solid)):
            for b in range(a + 1, len(solid)):
                if owner.get(id(solid[a])) == owner.get(id(solid[b])):
                    continue
                ba, bb = boxes[id(solid[a])], boxes[id(solid[b])]
                share = _inter(ba, bb) / max(1e-6, min(_area(ba), _area(bb)))
                if 0.12 < share < 0.85:
                    self._problem(f"frase {n}: {_name(solid[a])} e {_name(solid[b])} se cobrem em parte; afaste "
                                  "com arrange/next_to (ou allow_overlap se a sobreposição for o conteúdo)")
        # arrows: what each end touched when the arrow came in is remembered; an end whose object left (and that now
        # touches nothing) or a target that only arrives in a later sentence is a problem; connect() needs no check
        anchors = texts + shapes + others
        present = {id(m) for m in anchors}

        def nearest(p):
            ranked = sorted(anchors, key=lambda m: _dist(p, boxes[id(m)]))
            return ranked[0] if ranked and _dist(p, boxes[id(ranked[0])]) <= 0.45 else None

        for arr in arrows:
            ends = (arr.get_start(), arr.get_end())
            linked = getattr(arr, "lesson_link", None)
            near = [nearest(p) for p in ends]
            if not linked:
                record = self._arrows.get(id(arr))
                if record is None:
                    self._arrows[id(arr)] = [id(m) if m is not None else None for m in near]
                    origin = any(other is not arr and min(math.dist(ends[0][:2], other.get_start()[:2]),
                                                          math.dist(ends[0][:2], other.get_end()[:2])) < 0.3
                                 for other in arrows)             # hand-drawn axes share their origin
                    if near[0] is None and near[1] is None and not origin:
                        self._problem(f"frase {n}: {_arrow_name(arr)} está solta, nenhuma ponta toca um objeto; "
                                      "ligue objetos com connect(a, b)")
                else:
                    for k in (0, 1):
                        if record[k] is not None and record[k] not in present and near[k] is None:
                            self._problem(f"frase {n}: {_arrow_name(arr)} ficou na tela, mas o objeto da "
                                          f"{'origem' if k == 0 else 'ponta'} saiu; tire a seta junto (FadeOut) ou "
                                          "use connect(a, b), que some com as pontas")
                        elif record[k] is None and near[k] is not None and k == 1:
                            self._problem(f"frase {n}: {_arrow_name(arr)} apareceu antes do alvo; crie a seta na "
                                          "mesma frase em que o objeto da ponta entra")
                        if near[k] is not None:
                            record[k] = id(near[k])
            skip = {id(m) for m in near if m is not None}
            if linked:
                skip |= {id(d) for end in linked for d in end.get_family()}
            for target in texts + solid:
                if id(target) in skip:
                    continue
                bt = boxes[id(target)]
                if all(_inside(p, bt, shrink=0.0) for p in ends):        # a container around the arrow
                    continue
                if any(_inside(arr.point_from_proportion(k / 10), bt) for k in range(2, 9)):
                    self._problem(f"frase {n}: {_arrow_name(arr)} atravessa {_name(target)}; desvie o caminho, "
                                  "mude a posição dos objetos ou tire a seta")
                    break

    def tear_down(self):
        _STAGE.update(scene=None, incoming=set(), stamp=None)
        if self._i != len(self.beats):
            raise LayoutError(f"a cena tem {len(self.beats)} frases e beat() foi chamado {self._i} vezes; "
                              f"chame self.beat(...) exatamente uma vez por frase")

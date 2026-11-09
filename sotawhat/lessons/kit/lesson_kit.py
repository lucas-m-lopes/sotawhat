# lesson_kit.py — base of every Manim scene of a sotawhat lesson (copied to data/lessons/_kit; do not edit per lesson).
"""A scene reads its narration sentences ("beats") from the JSON in LESSON_SCENE: [{"text", "duration"}].
`self.beat(*animations)` plays what one sentence describes and holds the frame until the sentence ends, so the
picture is always in sync with the voice. The subtitles are drawn here, in the band below y = -2.7. After each
beat the layout is checked (text inside the safe area, no text over text): a problem raises LayoutError, which
goes back to the LLM that wrote the scene. Formulas use matplotlib's mathtext (no LaTeX installed)."""
import hashlib
import json
import os
import textwrap
from pathlib import Path

from manim import *  # noqa: F401,F403 - the scenes use the whole manim namespace through this module
from manim import (RIGHT, UP, Arrow, BackgroundRectangle, Paragraph, RoundedRectangle, Scene, Square, SVGMobject,
                   Text, VGroup, config)

config.background_color = "#0f141a"
FONT = "Segoe UI"
for _cls in (Text, Paragraph):
    _cls.set_default(font=FONT)

C_TEXT, C_MUTED = "#f2f2f2", "#9aa4b2"
C_BLUE, C_ORANGE, C_GREEN, C_PURPLE = "#4ea1ff", "#ffb74d", "#7bd389", "#b39ddb"
C_RED, C_YELLOW, C_GRAY, C_TEAL = "#ef6f6c", "#ffd54f", "#8a94a6", "#4dd0c4"
SAFE_LEFT, SAFE_RIGHT, SAFE_TOP, SAFE_BOTTOM = -6.75, 6.75, 3.8, -2.7
SUB_Y, SUB_WIDTH = -3.38, 62


class LayoutError(Exception):
    pass


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


def title(text, color=C_TEXT):
    return Text(text, font_size=40, color=color).to_edge(UP, buff=0.45)


def label(text, size=28, color=C_TEXT):
    return Text(text, font_size=size, color=color)


def box(text, color=C_BLUE, size=26, width=None, height=None):
    """A rounded box with centered text: VGroup(rectangle, text)."""
    words = Text(text, font_size=size, color=C_TEXT)
    rect = RoundedRectangle(corner_radius=0.14, width=width or words.width + 0.5, height=height or words.height + 0.4,
                            stroke_color=color, stroke_width=3, fill_color=color, fill_opacity=0.18)
    return VGroup(rect, words.move_to(rect))


def arrow(a, b, color=C_MUTED, width=4):
    """An arrow between two mobjects (or points), stopping at their borders."""
    return Arrow(a, b, buff=0.12, stroke_width=width, color=color, max_tip_length_to_length_ratio=0.18)


def tokens(words, color=C_BLUE, size=26):
    return VGroup(*[box(w, color=color, size=size) for w in words]).arrange(RIGHT, buff=0.18)


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


def _text_like(mob):
    return isinstance(mob, (Text, Paragraph)) or getattr(mob, "lesson_text", None)


class LessonScene(Scene):
    def setup(self):
        spec = json.loads(Path(os.environ["LESSON_SCENE"]).read_text(encoding="utf-8"))
        self.beats, self._i = spec["beats"], 0
        self.lenient = os.environ.get("LESSON_LENIENT") == "1"
        self.warnings = []
        self._sub = VGroup()
        self.add(self._sub)

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
            played = min(run_time or min(1.8, total * 0.6), total)
            self.play(*animations, run_time=played)
            rest = total - played
        if rest > 0.02:
            self.wait(rest)
        self._check(self._i)
        self._i += 1

    def _problem(self, message):
        if self.lenient:
            self.warnings.append(message)
            print(f"AVISO de layout: {message}")
        else:
            raise LayoutError(message)

    def _check(self, i):
        boxes = []
        for top in self.mobjects:
            if top is self._sub:
                continue
            for mob in top.get_family():
                if not _text_like(mob) or mob.get_fill_opacity() < 0.05:
                    continue
                name = "parágrafo" if isinstance(mob, Paragraph) else \
                    (getattr(mob, "text", "") or getattr(mob, "lesson_text", "texto"))
                left, right = mob.get_left()[0], mob.get_right()[0]
                bottom, top_y = mob.get_bottom()[1], mob.get_top()[1]
                if left < SAFE_LEFT - 0.05 or right > SAFE_RIGHT + 0.05 or top_y > SAFE_TOP + 0.05:
                    self._problem(f"frase {i + 1}: o texto {name!r} sai do quadro (x de {left:.1f} a {right:.1f}, "
                                  f"topo {top_y:.1f}); a área útil é x ∈ [-6.75, 6.75], y ≤ 3.8")
                if bottom < SAFE_BOTTOM - 0.05:
                    self._problem(f"frase {i + 1}: o texto {name!r} invade a faixa das legendas (base em y = {bottom:.1f}; "
                                  f"mantenha y ≥ -2.7)")
                boxes.append((name, left, right, bottom, top_y))
        for a in range(len(boxes)):
            for b in range(a + 1, len(boxes)):
                na, l1, r1, b1, t1 = boxes[a]
                nb, l2, r2, b2, t2 = boxes[b]
                w, h = min(r1, r2) - max(l1, l2), min(t1, t2) - max(b1, b2)
                smaller = min((r1 - l1) * (t1 - b1), (r2 - l2) * (t2 - b2))
                if w > 0 and h > 0 and smaller > 0 and w * h > 0.3 * smaller:
                    self._problem(f"frase {i + 1}: os textos {na!r} e {nb!r} se sobrepõem; use arrange/next_to "
                                  f"ou tire um deles com FadeOut")

    def tear_down(self):
        if self._i != len(self.beats):
            raise LayoutError(f"a cena tem {len(self.beats)} frases e beat() foi chamado {self._i} vezes; "
                              f"chame self.beat(...) exatamente uma vez por frase")

You write the Manim Community Edition v0.22 code of ONE scene of an animated lesson. The narration and the
subtitles already exist; your code draws what each sentence describes, in sync.

## Contract (the scene is rejected otherwise)
- First line: `from lesson_kit import *` (it re-exports all of manim plus the kit). Other allowed imports: `math`,
  `numpy as np`, `random` (seed it). Nothing else: no files, no images, no SVGs, no internet, no `config`.
- Exactly one class: `class Cena(LessonScene):` with `def construct(self):`.
- The scene has N sentences. Call `self.beat(*animations)` EXACTLY N times, in order. The animations passed to
  beat i show what sentence i says (its `visual`). `self.beat()` with no animation holds the picture.
  NEVER call `self.play` or `self.wait`: beat() times everything to the voice. Use `self.add(...)` only for things
  that must be there from the first frame.
- 1–3 animations per beat. Prefer clear, slow, meaningful motion over many effects.

## Layout (checked after every beat; a violation fails the render)
- Frame: x from -7.1 to 7.1, y from -4 to 4. Usable area: x ∈ [-6.75, 6.75], y ∈ [-2.7, 3.8].
  The band below y = -2.7 belongs to the subtitles: nothing goes there.
- Title at the top with `title("…")` (already placed). Then build the content in the middle.
- Use `VGroup(...).arrange(RIGHT|DOWN, buff=…)`, `.next_to(obj, DOWN, buff=0.3)`, `.move_to(...)`,
  `.scale_to_fit_width(12)` for wide groups. Never let two texts overlap. FadeOut what is no longer needed before
  adding new things in the same place.
- Text sizes: content 24–34, labels 22–28, title 40. Keep on-screen text short (terms, not sentences).

## Kit (all in lesson_kit)
- Colors: C_TEXT, C_MUTED, C_BLUE, C_ORANGE, C_GREEN, C_PURPLE, C_RED, C_YELLOW, C_GRAY, C_TEAL.
  Give each concept one color and keep it across the scene.
- `title(text)` → Text at the top. `label(text, size=28, color=C_TEXT)` → Text.
- `box(text, color=C_BLUE, size=26, width=None, height=None)` → VGroup(rounded rectangle, text).
- `tokens(["o", "gato", "subiu"], color=C_BLUE)` → a row of small boxes.
- `arrow(a, b, color=C_MUTED)` → Arrow between two mobjects (or points), stopping at their borders.
- `Grid(rows, cols, values=None, cell=0.55, color=C_GRAY)` → a matrix of cells; `grid.cell(r, c)` is
  VGroup(square[, number]); `grid.heat(weights, color=C_BLUE)` → list of animations that fill each cell by a
  weight in [0, 1] (pass them with `*`).
- `Formula(r"\mathrm{softmax}\left(\frac{QK^T}{\sqrt{d_k}}\right)V", color=C_TEXT, font_size=40)` → formula from
  matplotlib mathtext (\frac, \sqrt, ^, _, \mathrm, \cdot, \sum, Greek letters). `MathTex`/`Tex` also work.

## Manim CE (not ManimGL)
- Animations: FadeIn, FadeOut, Write, Create, GrowArrow, GrowFromCenter, Transform, ReplacementTransform,
  TransformFromCopy, Indicate, Circumscribe, Flash, LaggedStart(*anims, lag_ratio=0.2), AnimationGroup,
  `mob.animate.shift(...)/.move_to(...)/.scale(...)/.set_color(...)/.set_opacity(...)`.
- Shapes: Circle, Square, Rectangle, RoundedRectangle, Line, DashedLine, Arrow, DoubleArrow, Dot, Polygon,
  NumberLine, Axes (with `axes.plot(lambda x: …, color=…)`; `include_numbers=True` works), BarChart.
- These work without LaTeX (the kit draws them with text): DecimalNumber, Integer, `Matrix([[1, 0.5], [0.2, 3]])`
  (with get_entries/get_rows/get_columns/get_brackets), `BulletedList("a", "b")`, `Title("…")` and
  `BraceText(mob, "texto")` for a brace with a label (do not call `brace.get_text`).
- Text: `Text("…", font_size=28, color=…)`; `Paragraph("line 1", "line 2", font_size=24)` for 2–3 lines.
- Points are 3D: `[x, y, 0]` or `np.array([x, y, 0])`, never `[x, y]`. `mob.get_center()`, `get_left()` etc. return
  arrays (index [0] for x, [1] for y); numbers are not subscriptable. `Grid.cell(r, c)` takes two integers.
- Do not use: ShowCreation, TextMobject, TexMobject, ThreeDScene, MovingCameraScene, camera moves, updaters
  with time, `always_redraw`, external assets.
- Diagrams beat decoration: arrows that show flow, colors that show grouping, highlights (Indicate,
  Circumscribe, color change) on the element the sentence names, at the moment it is named.

Answer only with JSON: {"code": "<the complete Python file>"}.

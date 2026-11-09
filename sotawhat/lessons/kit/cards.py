# cards.py — the opening and closing cards of a lesson, made without the LLM (LESSON_CARD: kind, title, lines, seconds).
import json
import os
import textwrap
from pathlib import Path

from lesson_kit import C_MUTED, C_TEXT, DOWN, ORIGIN, UP, FadeIn, Paragraph, Scene, Text, VGroup


class Card(Scene):
    def construct(self):
        spec = json.loads(Path(os.environ["LESSON_CARD"]).read_text(encoding="utf-8"))
        seconds = float(spec.get("seconds", 3.5))
        brand = Text("sotawhat · aula", font_size=24, color=C_MUTED).to_edge(UP, buff=0.6)
        head = Paragraph(*textwrap.wrap(spec["title"], 34), font_size=50, alignment="center", color=C_TEXT)
        lines = [Text(line, font_size=26, color=C_MUTED) for text in spec.get("lines", []) for line in textwrap.wrap(text, 70)]
        body = VGroup(head, *([VGroup(*lines).arrange(DOWN, buff=0.22)] if lines else [])).arrange(DOWN, buff=0.6)
        body.move_to(ORIGIN)
        self.add(brand)
        self.play(FadeIn(body, shift=UP * 0.2), run_time=0.8)
        self.wait(max(0.1, seconds - 0.8))

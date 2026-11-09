# sotawhat/lessons/__init__.py
"""Aulas 3D (F0/F1, docs/superpowers/plans/2026-11-09-aulas-3d-f0-f1.md): a topic of the graph becomes a 3–6 min
lesson narrated in Brazilian Portuguese, animated by code that an LLM writes and the PC renders.

pack -> plan (G2 lint, G1 facts) -> narration per sentence (beat) -> code per scene (Manim for the abstract,
three.js for the spatial) -> render with repair -> assembled MP4 (subtitles drawn by the renderers) -> Telegram
(video, quiz, review) and the local page /aulas. The renderers run in data/tools/lessons (`sotawhat lessons
setup`), never inside this process."""

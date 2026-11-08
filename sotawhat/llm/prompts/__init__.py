# sotawhat/llm/prompts/__init__.py
"""Versioned prompts (SDD §6.6). The version string is stored with every result that used it."""
from importlib.resources import files


def load(name: str) -> str:
    return files(__package__).joinpath(f"{name}.md").read_text(encoding="utf-8")

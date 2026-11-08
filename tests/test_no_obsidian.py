# tests/test_no_obsidian.py
"""The user asked for no Obsidian at all (SDD §9, D12): nothing reads or writes a vault."""
import importlib.util

import pytest

from sotawhat.cli import parse_args


@pytest.mark.parametrize("module", ["sotawhat.obsidian", "sotawhat.backfill", "sotawhat.digest"])
def test_obsidian_modules_are_gone(module):
    assert importlib.util.find_spec(module) is None


@pytest.mark.parametrize("argv", [
    ["digest", "--profile", "medico", "--vault", "V"],
    ["backfill-links", "--vault", "V"],
    ["run", "daily", "--vault", "V"],
    ["eval", "golden", "draft", "--vault", "V"],
])
def test_vault_commands_and_options_are_rejected(argv):
    with pytest.raises(SystemExit):
        parse_args(argv)


@pytest.mark.parametrize("argv", [["run", "--help"], ["eval", "golden", "--help"]])
def test_help_never_mentions_a_vault(argv, capsys):
    with pytest.raises(SystemExit):
        parse_args(argv)
    text = capsys.readouterr().out.lower()
    assert "vault" not in text and "obsidian" not in text

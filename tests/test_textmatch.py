# tests/test_textmatch.py
from sotawhat.textmatch import contains_any, contains_term, fold

def test_contains_term_word_boundary():
    assert contains_term("we built an agent system", "agent")
    assert not contains_term("we used a reagent here", "agent")

def test_contains_term_is_case_insensitive():
    # The matcher is case-insensitive, so short ambiguous acronyms like "ML"
    # would match "mL" (milliliters). The medico design avoids this by excluding
    # "ML" from AI_TERMS (see profiles.py), NOT by the matcher distinguishing case.
    assert contains_term("we injected 5 mL of saline", "ML")

def test_contains_term_multiword_phrase():
    assert contains_term("a machine learning model", "machine learning")
    assert not contains_term("a statistical model", "machine learning")

def test_contains_any():
    assert contains_any("deep learning in radiology", ["machine learning", "deep learning"])
    assert not contains_any("a clinical trial of aspirin", ["machine learning", "deep learning"])


def test_fold_drops_case_and_accents_only():
    assert fold("Diagnóstico") == "diagnostico" and fold("SAÚDE") == "saude" and fold("Fréchet") == "frechet"
    assert fold("GPT-5") == "gpt-5" and fold("ß") == "ss" and fold("IA ∩ Saúde") == "ia ∩ saude"
    assert fold("β-amiloide") == "β-amiloide" and fold(None) is None

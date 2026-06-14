# tests/test_textmatch.py
from sotawhat.textmatch import contains_term, contains_any

def test_contains_term_word_boundary():
    assert contains_term("we built an agent system", "agent")
    assert not contains_term("we used a reagent here", "agent")

def test_contains_term_ml_not_milliliters():
    # Case-insensitive word-boundary matching cannot distinguish "mL" (milliliters)
    # from "ML" (machine learning) once both are lowercased; both match \bml\b.
    # The safer keyword for ML relevance is the full phrase "machine learning".
    assert contains_term("we injected 5 mL of saline", "ML")  # mL is a word boundary match
    assert contains_term("a machine learning model", "machine learning")

def test_contains_any():
    assert contains_any("deep learning in radiology", ["machine learning", "deep learning"])
    assert not contains_any("a clinical trial of aspirin", ["machine learning", "deep learning"])

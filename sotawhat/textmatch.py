# sotawhat/textmatch.py
import re

def contains_term(text, term):
    return re.search(r"\b" + re.escape(term.lower()) + r"\b", text.lower()) is not None

def contains_any(text, terms):
    return any(contains_term(text, t) for t in terms)

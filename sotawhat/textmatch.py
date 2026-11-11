# sotawhat/textmatch.py
import re
import unicodedata


_COMBINING = re.compile("[\u0300-\u036f\u1ab0-\u1aff\u1dc0-\u1dff\u20d0-\u20ff\ufe20-\ufe2f]")   # combining marks


def fold(text):
    """Text without case or accents, for searches typed in a hurry ("diagnostico" finds "diagnóstico").
    SQLite's lower() only folds ASCII, so the store registers this as the SQL function fold(); a search runs
    it on every title and summary, hence the ASCII shortcut and the regex instead of a loop per character."""
    if text is None:
        return None
    text = str(text)
    if text.isascii():
        return text.lower()
    return _COMBINING.sub("", unicodedata.normalize("NFKD", text)).casefold()


def contains_term(text, term):
    return re.search(r"\b" + re.escape(term.lower()) + r"\b", text.lower()) is not None

def contains_any(text, terms):
    return any(contains_term(text, t) for t in terms)

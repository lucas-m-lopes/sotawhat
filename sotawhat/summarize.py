import re

_TOKEN_RE = re.compile(r"\w+(?:\.\w+)?|[^\w\s]")

def tokenize(text):
    """Lightweight word tokenizer replacing nltk.word_tokenize for our needs."""
    return _TOKEN_RE.findall(text)

def is_float(token):
    return re.match(r"^\d+?\.\d+?$", token) is not None

def is_citation_year(tokens, i):
    if len(tokens[i]) != 4:
        return False
    if re.match(r"[12][0-9]{3}", tokens[i]) is None:
        return False
    if i == 0 or i == len(tokens) - 1:
        return False
    if (tokens[i - 1] == "," or tokens[i - 1] == "(") and tokens[i + 1] == ")":
        return True
    return False

def is_list_numer(tokens, i, value):
    if value < 1 or value > 4:
        return False
    if i == len(tokens) - 1:
        return False
    if (i == 0 or tokens[i - 1] in {"(", ".", ":"}) and tokens[i + 1] == ")":
        return True
    return False

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

def has_number(sent):
    tokens = tokenize(sent)
    for i, token in enumerate(tokens):
        if token.endswith("\\"):
            token = token[:-2]
        if token.endswith("x"):
            token = token[:-1]
        if token.startswith("x"):
            token = token[1:]
        if token.startswith("$") and token.endswith("$"):
            token = token[1:-1]
        if is_float(token):
            return True
        try:
            value = int(token)
        except ValueError:
            continue
        if not is_citation_year(tokens, i) and not is_list_numer(tokens, i, value):
            return True
    return False

def contains_sota(sent):
    return ("state-of-the-art" in sent or "state of the art" in sent
            or "SOTA" in sent)

def extract_line(abstract, keyword, limit):
    lines = []
    numbered_lines = []
    kw_mentioned = False
    abstract = abstract.replace("et. al", "et al.")
    sentences = abstract.split(". ")
    kw_sentences = []
    for sent in sentences:
        if keyword in sent.lower():
            kw_mentioned = True
            if has_number(sent):
                numbered_lines.append(sent)
            elif contains_sota(sent):
                numbered_lines.append(sent)
            else:
                kw_sentences.append(sent)
                lines.append(sent)
            continue
        if kw_mentioned and has_number(sent):
            if not numbered_lines and kw_sentences:
                numbered_lines.append(kw_sentences[-1])
            numbered_lines.append(sent)
        if kw_mentioned and contains_sota(sent):
            lines.append(sent)
    if numbered_lines:
        return ". ".join(numbered_lines), True
    return ". ".join(lines[-2:]), False

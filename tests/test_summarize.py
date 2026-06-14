from sotawhat.summarize import tokenize, is_float, is_citation_year, is_list_numer

def test_tokenize_splits_words_and_punct():
    assert tokenize("BLEU of 2.3 (Vaswani, 2017).") == \
        ["BLEU", "of", "2.3", "(", "Vaswani", ",", "2017", ")", "."]

def test_is_float():
    assert is_float("2.3") is True
    assert is_float("23") is False

def test_is_citation_year():
    toks = ["(", "Vaswani", ",", "2017", ")"]
    assert is_citation_year(toks, 3) is True
    assert is_citation_year(["in", "2017", "we"], 1) is False

def test_is_list_numer():
    toks = ["(", "2", ")", "we"]
    assert is_list_numer(toks, 1, 2) is True
    assert is_list_numer(["x", "9", ")"], 1, 9) is False

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

from sotawhat.summarize import has_number, contains_sota, extract_line

def test_has_number_ignores_citation_years():
    assert has_number("Proposed by Vaswani (2017)") is False
    assert has_number("We improve BLEU by 2.3 points") is True

def test_contains_sota():
    assert contains_sota("achieves state-of-the-art results") is True
    assert contains_sota("a normal sentence") is False

def test_extract_line_prefers_numeric_sentences():
    abstract = ("We study transformers. Our transformer improves BLEU by 2.3. "
                "It is nice.")
    text, has_num = extract_line(abstract, "transformer", 280)
    assert has_num is True
    assert "2.3" in text

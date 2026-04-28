import pytest
from text_processor.core import TextProcessor

def test_count_words():
    tp = TextProcessor("Hello world from Python")
    assert tp.count_words() == 4
    
    tp_empty = TextProcessor("")
    assert tp_empty.count_words() == 0

def test_transform_case():
    tp = TextProcessor("Hello World")
    assert tp.transform_case("upper") == "HELLO WORLD"
    assert tp.transform_case("lower") == "hello world"
    
    with pytest.raises(ValueError):
        tp.transform_case("invalid")

def test_find_keyword():
    tp = TextProcessor("The quick brown fox jumps over the lazy dog. The dog is happy.")
    # Case sensitive search
    assert tp.find_keyword("the") == [35] 
    # Multiple occurrences
    assert tp.find_keyword("dog") == [40, 53]
    # Not found
    assert tp.find_keyword("cat") == []

def test_find_keyword_overlap():
    tp = TextProcessor("aaaaa")
    # Should find 'aa' at 0, 2 (non-overlapping by logic in core.py)
    # Current core.py implementation: start += len(keyword)
    assert tp.find_keyword("aa") == [0, 2]
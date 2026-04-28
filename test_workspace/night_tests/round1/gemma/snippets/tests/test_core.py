import pytest
from src.analyzer.core import analyze_text, AnalysisResult

def test_analyze_text_basic():
    text = "Hello world hello Python"
    result = analyze_text(text, top_n=2)
    
    assert result.word_count == 4
    assert result.char_count == 25
    assert result.top_words == [("hello", 2), ("world", 1)]

def test_analyze_text_empty():
    result = analyze_text("")
    assert result.word_count == 0
    assert result.char_count == 0
    assert result.top_words == []

def test_analyze_text_case_insensitivity():
    text = "Apple apple APPLE Banana"
    result = analyze_text(text, top_n=1)
    assert result.top_words[0] == ("apple", 3)

def test_analyze_text_top_n_limit():
    text = "one two three four five"
    result = analyze_text(text, top_n=2)
    assert len(result.top_words) == 2

def test_analyze_text_type():
    result = analyze_text("test")
    assert isinstance(result, AnalysisResult)
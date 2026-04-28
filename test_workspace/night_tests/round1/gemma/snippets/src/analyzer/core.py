from collections import Counter
from typing import NamedTuple

class AnalysisResult(NamedTuple):
    word_count: int
    char_count: int
    top_words: list[tuple[str, int]]

def analyze_text(text: str, top_n: int = 5) -> AnalysisResult:
    """
    Analyzes the provided text to count words, characters, 
    and find the most frequent words.
    """
    if not text:
        return AnalysisResult(0, 0, [])

    # Character count (including whitespace)
    char_count = len(text)

    # Word count and frequency
    # Simple split by whitespace; in a real app, we'd use regex or nltk
    words = text.lower().split()
    word_count = len(words)
    
    counts = Counter(words)
    top_words = counts.most_common(top_n)

    return AnalysisResult(
        word_count=word_count,
        char_count=char_count,
        top_words=top_words
    )
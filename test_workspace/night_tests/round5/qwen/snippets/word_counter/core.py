from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TextStats:
    lines: int
    words: int
    chars: int


def count_text(text: str) -> TextStats:
    """计算文本的行数、单词数和字符数。"""
    lines = len(text.splitlines()) if text else 0
    words = len(text.split())
    chars = len(text)
    return TextStats(lines=lines, words=words, chars=chars)
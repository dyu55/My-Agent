from pathlib import Path
from dataclasses import dataclass

@dataclass(frozen=True)
class TextStats:
    lines: int
    words: int
    characters: int

def analyze_file(file_path: Path) -> TextStats:
    """分析文本文件的行数、单词数和字符数。"""
    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    content: str = file_path.read_text(encoding="utf-8")
    lines: int = len(content.splitlines())
    words: int = len(content.split())
    characters: int = len(content)
    
    return TextStats(lines=lines, words=words, characters=characters)
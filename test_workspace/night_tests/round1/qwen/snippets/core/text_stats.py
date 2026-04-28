from __future__ import annotations

import pathlib
from dataclasses import dataclass


@dataclass(frozen=True)
class TextStats:
    lines: int
    words: int
    characters: int
    byte_size: int


def count_text(file_path: pathlib.Path) -> TextStats:
    """计算指定文本文件的统计信息。"""
    content = file_path.read_text(encoding="utf-8")
    return TextStats(
        lines=len(content.splitlines()),
        words=len(content.split()),
        characters=len(content),
        byte_size=len(content.encode("utf-8")),
    )
from __future__ import annotations
import argparse
import sys
from pathlib import Path

from .core import count_text


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        description="统计文件或标准输入中的行数、单词数和字符数。"
    )
    parser.add_argument(
        "file",
        nargs="?",
        default=None,
        type=Path,
        help="要分析的文件路径。若省略则从标准输入读取。",
    )
    return parser.parse_args(args)


def main(args: list[str] | None = None) -> None:
    """CLI 程序入口。"""
    parsed = parse_args(args)

    if parsed.file:
        if not parsed.file.exists():
            print(f"错误: 文件 '{parsed.file}' 不存在。", file=sys.stderr)
            sys.exit(1)
        if not parsed.file.is_file():
            print(f"错误: '{parsed.file}' 不是常规文件。", file=sys.stderr)
            sys.exit(1)

        try:
            content = parsed.file.read_text(encoding="utf-8")
        except PermissionError:
            print(f"错误: 拒绝访问文件 '{parsed.file}'。", file=sys.stderr)
            sys.exit(1)
        except UnicodeDecodeError:
            print(f"错误: 文件 '{parsed.file}' 包含无效的 UTF-8 编码。", file=sys.stderr)
            sys.exit(1)
    else:
        content = sys.stdin.read()

    stats = count_text(content)
    print(f"{stats.lines}\t{stats.words}\t{stats.chars}")
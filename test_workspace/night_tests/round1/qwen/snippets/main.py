from __future__ import annotations

import argparse
import pathlib
import sys
from core.text_stats import count_text


def main() -> None:
    parser = argparse.ArgumentParser(
        description="计算文本文件的行数、单词数、字符数和字节大小。",
    )
    parser.add_argument(
        "file",
        type=pathlib.Path,
        help="目标文本文件路径",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="显示详细统计信息",
    )
    args = parser.parse_args()

    if not args.file.exists():
        parser.error(f"文件不存在: {args.file}")
    if not args.file.is_file():
        parser.error(f"路径不是文件: {args.file}")

    try:
        stats = count_text(args.file)
    except UnicodeDecodeError as e:
        print(f"错误: 无法解码文件，请确保是UTF-8编码。详情: {e}", file=sys.stderr)
        sys.exit(1)

    if args.verbose:
        print(f"文件: {args.file.name}")
        print(f"行数:   {stats.lines}")
        print(f"单词数: {stats.words}")
        print(f"字符数: {stats.characters}")
        print(f"字节大小: {stats.byte_size}")
    else:
        print(f"行数: {stats.lines}, 单词数: {stats.words}, 字符数: {stats.characters}")


if __name__ == "__main__":
    main()
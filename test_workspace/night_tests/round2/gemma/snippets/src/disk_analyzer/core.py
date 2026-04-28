import os
from pathlib import Path
from typing import Generator, Tuple

class DiskAnalyzer:
    """Handles the logic for calculating directory and file sizes."""

    @staticmethod
    def format_size(size_bytes: int) -> str:
        """Convert bytes to human-readable string (e.g., MB, GB)."""
        if size_bytes == 0:
            return "0B"
        
        units = ("B", "KB", "MB", "GB", "TB", "PB")
        i = 0
        while size_bytes >= 1024 and i < len(units) - 1:
            size_bytes /= 1024
            i += 1
        
        return f"{size_bytes:.2f} {units[i]}"

    def get_size(self, path: Path) -> int:
        """Recursively calculate the size of a file or directory."""
        if path.is_file():
            return path.stat().st_size
        
        total_size = 0
        try:
            for entry in path.rglob('*'):
                if entry.is_file():
                    total_size += entry.stat().st_size
        except PermissionError:
            # Skip directories where we don't have access
            pass
        return total_size

    def list_top_items(self, path: Path, limit: int = 10) -> Generator[Tuple[Path, int], None, None]:
        """List the largest immediate children of the given path."""
        items_with_size = []
        
        try:
            for item in path.iterdir():
                items_with_size.append((item, self.get_size(item)))
        except PermissionError:
            return

        # Sort by size descending
        sorted_items = sorted(items_with_size, key=lambda x: x[1], reverse=True)
        
        for item in sorted_items[:limit]:
            yield item
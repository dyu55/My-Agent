from typing import Final

class TextProcessor:
    """Core logic for text manipulation."""
    
    def __init__(self, text: str) -> None:
        self.text: Final[str] = text

    def count_words(self) -> int:
        """Count words in the text."""
        return len(self.text.split())

    def transform_case(self, mode: str) -> str:
        """Change text case based on mode: 'upper' or 'lower'."""
        if mode == "upper":
            return self.text.upper()
        elif mode == "lower":
            return self.text.lower()
        else:
            raise ValueError(f"Unsupported mode: {mode}. Use 'upper' or 'lower'.")

    def find_keyword(self, keyword: str) -> list[int]:
        """Find all starting indices of a keyword in the text."""
        indices = []
        start = 0
        while True:
            start = self.text.find(keyword, start)
            if start == -1:
                break
            indices.append(start)
            start += len(keyword)
        return indices
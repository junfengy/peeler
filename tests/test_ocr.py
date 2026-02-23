"""Tests for OCR letter recognition from tile photos."""

from __future__ import annotations

import base64
from collections import Counter
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"

# Ground truth for each test image
# tiles_12_AAMVIMERLNFV.jpg: 12 Bananagrams tiles photographed at various orientations
TILES_12_PATH = FIXTURES / "tiles_12_AAMVIMERLNFV.jpg"
TILES_12_EXPECTED = list("AAEFILMNMRVV")  # sorted ground truth


class TestParseLetters:
    """Unit tests for _parse_letters — no model needed."""

    def test_comma_separated(self) -> None:
        from web.app import _parse_letters
        assert _parse_letters("A, B, C, A, E") == ["A", "B", "C", "A", "E"]

    def test_space_separated(self) -> None:
        from web.app import _parse_letters
        assert _parse_letters("A B C A E") == ["A", "B", "C", "A", "E"]

    def test_mixed_case(self) -> None:
        from web.app import _parse_letters
        assert _parse_letters("a, b, c") == ["A", "B", "C"]

    def test_filters_non_letters(self) -> None:
        from web.app import _parse_letters
        result = _parse_letters("A, 1, B, ?, C, 23")
        assert result == ["A", "B", "C"]

    def test_multichar_tokens_filtered(self) -> None:
        from web.app import _parse_letters
        # Multi-char tokens like "AB" should be filtered out
        result = _parse_letters("A, AB, B, CD, C")
        assert result == ["A", "B", "C"]

    def test_empty_string(self) -> None:
        from web.app import _parse_letters
        assert _parse_letters("") == []

    def test_newlines(self) -> None:
        from web.app import _parse_letters
        assert _parse_letters("A\nB\nC") == ["A", "B", "C"]


@pytest.mark.skipif(not TILES_12_PATH.exists(), reason="fixture image not found")
class TestOllamaOCR:
    """Integration tests for Ollama OCR — requires a running Ollama server."""

    @staticmethod
    def _ollama_available() -> bool:
        from urllib.request import urlopen
        from urllib.error import URLError
        try:
            urlopen("http://localhost:11434/api/tags", timeout=3)
            return True
        except (URLError, OSError):
            return False

    @pytest.fixture(autouse=True)
    def skip_if_no_ollama(self) -> None:
        if not self._ollama_available():
            pytest.skip("Ollama server not running")

    @pytest.fixture
    def image_b64(self) -> str:
        return base64.b64encode(TILES_12_PATH.read_bytes()).decode()

    def test_ollama_returns_letters(self, image_b64: str) -> None:
        from web.app import _ollama_ocr
        result = _ollama_ocr(image_b64)
        assert result is not None, "Ollama returned no letters"
        letters, model = result
        assert len(letters) > 0
        assert all(ch.isalpha() and len(ch) == 1 for ch in letters)
        print(f"Ollama ({model}) recognized: {letters}")

    def test_ollama_count_accuracy(self, image_b64: str) -> None:
        """Ollama should recognize at least 10 of 12 tiles."""
        from web.app import _ollama_ocr
        result = _ollama_ocr(image_b64)
        assert result is not None
        letters, model = result
        assert len(letters) >= 10, (
            f"Ollama ({model}) only recognized {len(letters)}/12 tiles: {letters}"
        )

    def test_ollama_letter_accuracy(self, image_b64: str) -> None:
        """At least 80% of recognized letters should be correct."""
        from web.app import _ollama_ocr
        result = _ollama_ocr(image_b64)
        assert result is not None
        letters, model = result

        expected = Counter(TILES_12_EXPECTED)
        recognized = Counter(sorted(letters))
        # Count correct: min of expected and recognized for each letter
        correct = sum((expected & recognized).values())
        accuracy = correct / len(TILES_12_EXPECTED)
        assert accuracy >= 0.8, (
            f"Ollama ({model}) accuracy {accuracy:.0%} < 80%: "
            f"got {sorted(letters)}, expected {TILES_12_EXPECTED}"
        )

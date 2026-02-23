"""Trie-based dictionary for word lookup and word finding from letter sets."""

from __future__ import annotations

import os
from collections import Counter
from pathlib import Path


class TrieNode:
    __slots__ = ("children", "is_word")

    def __init__(self) -> None:
        self.children: dict[str, TrieNode] = {}
        self.is_word: bool = False


class Dictionary:
    """Trie-backed word dictionary with efficient letter-constrained word finding."""

    def __init__(self) -> None:
        self.root = TrieNode()
        self._word_count = 0

    def load(self, path: str | Path) -> None:
        """Load words from a file (one word per line)."""
        with open(path) as f:
            for line in f:
                word = line.strip().upper()
                if len(word) >= 2:
                    self._insert(word)

    def _insert(self, word: str) -> None:
        node = self.root
        for ch in word:
            if ch not in node.children:
                node.children[ch] = TrieNode()
            node = node.children[ch]
        if not node.is_word:
            node.is_word = True
            self._word_count += 1

    def is_valid_word(self, word: str) -> bool:
        node = self.root
        for ch in word.upper():
            if ch not in node.children:
                return False
            node = node.children[ch]
        return node.is_word

    def has_prefix(self, prefix: str) -> bool:
        node = self.root
        for ch in prefix.upper():
            if ch not in node.children:
                return False
            node = node.children[ch]
        return True

    def find_words_from_letters(self, letters: Counter[str],
                                min_length: int = 2,
                                max_length: int | None = None) -> list[str]:
        """Find all words that can be formed using the available letters.

        Traverses the trie, consuming letters from the counter.
        Prunes immediately when a prefix is impossible.
        """
        results: list[str] = []
        max_len = max_length or sum(letters.values())

        def _search(node: TrieNode, remaining: Counter[str], path: list[str], depth: int) -> None:
            if node.is_word and depth >= min_length:
                results.append("".join(path))
            if depth >= max_len:
                return
            for ch, child in node.children.items():
                if remaining[ch] > 0:
                    remaining[ch] -= 1
                    path.append(ch)
                    _search(child, remaining, path, depth + 1)
                    path.pop()
                    remaining[ch] += 1

        _search(self.root, Counter(letters), [], 0)
        return results

    @property
    def word_count(self) -> int:
        return self._word_count


def load_default_dictionary() -> Dictionary:
    """Load the SOWPODS dictionary from the data/ directory."""
    data_dir = Path(__file__).resolve().parent.parent / "data"
    path = data_dir / "sowpods.txt"
    if not path.exists():
        raise FileNotFoundError(
            f"Dictionary not found at {path}. "
            "Download SOWPODS word list and place it at data/sowpods.txt"
        )
    d = Dictionary()
    d.load(path)
    return d

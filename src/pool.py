"""Tile pool manager — tracks undrawn tiles and handles draws."""

from __future__ import annotations

import random
from collections import Counter

from src.constants import TILE_DISTRIBUTION


class TilePool:
    """Manages the pool of undrawn Bananagrams tiles."""

    def __init__(self, initial_hand: list[str], seed: int | None = None) -> None:
        """Subtract initial hand from TILE_DISTRIBUTION, shuffle remainder."""
        hand_counts = Counter(initial_hand)
        tiles: list[str] = []
        for letter, total in TILE_DISTRIBUTION.items():
            available = max(0, total - hand_counts.get(letter, 0))
            tiles.extend([letter] * available)

        rng = random.Random(seed)
        rng.shuffle(tiles)
        self._tiles = tiles

    def draw(self) -> str | None:
        """Pop one tile from the pool. Returns None if empty."""
        if not self._tiles:
            return None
        return self._tiles.pop()

    def remaining(self) -> int:
        """Number of tiles left in the pool."""
        return len(self._tiles)

    def is_empty(self) -> bool:
        return len(self._tiles) == 0

    def swap(self, letter: str) -> list[str] | None:
        """Put *letter* back into the pool, shuffle, draw 3.

        Returns the 3 drawn tiles, or None if fewer than 3 tiles
        are available after returning the letter.
        """
        self._tiles.append(letter)
        random.shuffle(self._tiles)
        if len(self._tiles) < 3:
            # Undo — take the letter back out
            self._tiles.remove(letter)
            return None
        return [self._tiles.pop() for _ in range(3)]

"""Sparse 2D crossword grid for placing and validating words."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.dictionary import Dictionary


class Direction(Enum):
    ACROSS = (0, 1)  # row stays same, col increases
    DOWN = (1, 0)    # row increases, col stays same


@dataclass
class PlacedWord:
    """Record of a word placement on the grid."""
    word: str
    row: int
    col: int
    direction: Direction
    cells_added: list[tuple[int, int]] = field(default_factory=list)


class Grid:
    """Sparse 2D grid that supports word placement, validation, and undo."""

    def __init__(self) -> None:
        self.cells: dict[tuple[int, int], str] = {}
        self.placed_words: list[PlacedWord] = []

    def is_empty(self) -> bool:
        return len(self.cells) == 0

    def get(self, row: int, col: int) -> str | None:
        return self.cells.get((row, col))

    def _word_positions(self, word: str, row: int, col: int,
                        direction: Direction) -> list[tuple[int, int]]:
        dr, dc = direction.value
        return [(row + i * dr, col + i * dc) for i in range(len(word))]

    def _get_run(self, row: int, col: int, direction: Direction) -> str:
        """Get the full contiguous run of letters through (row, col) in the given direction."""
        dr, dc = direction.value
        # Find start of run
        r, c = row - dr, col - dc
        while (r, c) in self.cells:
            r -= dr
            c -= dc
        r += dr
        c += dc
        # Read run
        letters = []
        while (r, c) in self.cells:
            letters.append(self.cells[(r, c)])
            r += dr
            c += dc
        return "".join(letters)

    def place_word(self, word: str, row: int, col: int,
                   direction: Direction, dictionary: Dictionary) -> PlacedWord | None:
        """Try to place a word. Returns PlacedWord on success, None on failure.

        Validates:
        - Each cell is empty or has matching letter
        - At least one intersection with existing letters (unless grid is empty)
        - Cells before/after the word are empty
        - All perpendicular runs created are valid words
        """
        positions = self._word_positions(word, row, col, direction)
        dr, dc = direction.value
        perp_dir = Direction.DOWN if direction == Direction.ACROSS else Direction.ACROSS
        perp_dr, perp_dc = perp_dir.value
        was_empty = self.is_empty()

        # Check cell before and after word are empty
        before = (row - dr, col - dc)
        after = (row + len(word) * dr, col + len(word) * dc)
        if before in self.cells or after in self.cells:
            return None

        cells_added: list[tuple[int, int]] = []
        intersections = 0

        for i, (r, c) in enumerate(positions):
            existing = self.cells.get((r, c))
            if existing is not None:
                if existing != word[i]:
                    # Conflict — undo
                    for pos in cells_added:
                        del self.cells[pos]
                    return None
                intersections += 1
            else:
                cells_added.append((r, c))
                self.cells[(r, c)] = word[i]

        # Must intersect existing letters (unless first word)
        if not was_empty and intersections == 0:
            for pos in cells_added:
                del self.cells[pos]
            return None

        # Validate perpendicular runs for newly placed cells
        for r, c in cells_added:
            # Check if there are neighbors in the perpendicular direction
            has_perp_neighbor = ((r + perp_dr, c + perp_dc) in self.cells or
                                 (r - perp_dr, c - perp_dc) in self.cells)
            if has_perp_neighbor:
                run = self._get_run(r, c, perp_dir)
                if len(run) > 1 and not dictionary.is_valid_word(run):
                    # Invalid perpendicular word — undo
                    for pos in cells_added:
                        del self.cells[pos]
                    return None

        placed = PlacedWord(word, row, col, direction, cells_added)
        self.placed_words.append(placed)
        return placed

    def remove_word(self, placed: PlacedWord) -> None:
        """Undo a word placement (for backtracking)."""
        for pos in placed.cells_added:
            del self.cells[pos]
        # Remove by identity (not equality) to avoid removing the wrong
        # duplicate when multiple identical placements exist during search.
        for i in range(len(self.placed_words) - 1, -1, -1):
            if self.placed_words[i] is placed:
                del self.placed_words[i]
                break

    def get_valid_placements(self, word: str,
                             dictionary: Dictionary) -> list[tuple[int, int, Direction]]:
        """Find all positions where a word can legally be placed on the grid."""
        placements: list[tuple[int, int, Direction]] = []

        if self.is_empty():
            # First word: place at origin horizontally
            return [(0, 0, Direction.ACROSS)]

        # Try to intersect with each existing cell
        for (er, ec), letter in list(self.cells.items()):
            for i, ch in enumerate(word):
                if ch != letter:
                    continue
                # Try placing so word[i] lands on (er, ec)
                for direction in Direction:
                    dr, dc = direction.value
                    start_r = er - i * dr
                    start_c = ec - i * dc
                    # Quick pre-check: would this overlap an existing word in the same direction?
                    placed = self.place_word(word, start_r, start_c, direction, dictionary)
                    if placed is not None:
                        placements.append((start_r, start_c, direction))
                        self.remove_word(placed)

        return placements

    def bounds(self) -> tuple[int, int, int, int]:
        """Returns (min_row, max_row, min_col, max_col)."""
        if not self.cells:
            return (0, 0, 0, 0)
        rows = [r for r, c in self.cells]
        cols = [c for r, c in self.cells]
        return (min(rows), max(rows), min(cols), max(cols))

    def letter_count(self) -> int:
        """Total letters placed on the grid."""
        return len(self.cells)

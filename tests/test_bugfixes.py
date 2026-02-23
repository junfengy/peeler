"""Tests for bugs fixed during web app development."""

from __future__ import annotations

from collections import Counter

import pytest

from src.dictionary import Dictionary
from src.grid import Direction, Grid, PlacedWord
from src.solver import _snapshot_grid, solve


@pytest.fixture
def small_dict() -> Dictionary:
    """Minimal dictionary for grid tests."""
    d = Dictionary()
    for w in [
        "QAT", "CAT", "AT", "TA", "AN", "NA", "AH", "HA",
        "IT", "TI", "IN", "ON", "NO", "OR", "TO",
        "ZAX", "AX", "OX", "EX",
        "HATH", "HAW", "THRAW",
    ]:
        d._insert(w)
    return d


class TestRemoveWordByIdentity:
    """Bug: remove_word used list.remove() which matches by equality.
    When two identical PlacedWord objects existed (same word, position,
    direction), removing one could delete the wrong entry."""

    def test_remove_correct_instance(self, small_dict: Dictionary) -> None:
        grid = Grid()
        pw1 = grid.place_word("CAT", 0, 0, Direction.ACROSS, small_dict)
        assert pw1 is not None

        # Place a second word
        pw2 = grid.place_word("AT", 0, 1, Direction.DOWN, small_dict)
        if pw2 is not None:
            # Remove pw2 — should only remove pw2, not pw1
            grid.remove_word(pw2)
            assert len(grid.placed_words) == 1
            assert grid.placed_words[0] is pw1

    def test_remove_last_added_when_duplicate_values(self, small_dict: Dictionary) -> None:
        """If two PlacedWord objects have equal fields, remove_word should
        remove the exact object passed (by identity), not the first match."""
        grid = Grid()
        pw1 = grid.place_word("CAT", 0, 0, Direction.ACROSS, small_dict)
        assert pw1 is not None

        # Manually create a duplicate-valued PlacedWord and append it
        pw_dup = PlacedWord("CAT", 0, 0, Direction.ACROSS, [])
        grid.placed_words.append(pw_dup)
        assert len(grid.placed_words) == 2

        # Remove the duplicate — should remove pw_dup, not pw1
        grid.remove_word(pw_dup)
        assert len(grid.placed_words) == 1
        assert grid.placed_words[0] is pw1


class TestSnapshotGridDedup:
    """Bug: _snapshot_grid did a shallow copy of placed_words, which could
    contain duplicate entries accumulated during backtracking. Now it
    deduplicates by (word, row, col, direction)."""

    def test_snapshot_removes_duplicates(self, small_dict: Dictionary) -> None:
        grid = Grid()
        pw = grid.place_word("CAT", 0, 0, Direction.ACROSS, small_dict)
        assert pw is not None

        # Manually inject duplicates (simulates the backtracking bug)
        grid.placed_words.append(
            PlacedWord("CAT", 0, 0, Direction.ACROSS, [])
        )
        grid.placed_words.append(
            PlacedWord("CAT", 0, 0, Direction.ACROSS, [])
        )
        assert len(grid.placed_words) == 3

        snap = _snapshot_grid(grid)
        assert len(snap.placed_words) == 1
        assert snap.placed_words[0].word == "CAT"

    def test_snapshot_preserves_distinct_words(self, small_dict: Dictionary) -> None:
        grid = Grid()
        grid.place_word("CAT", 0, 0, Direction.ACROSS, small_dict)
        grid.place_word("AT", 0, 1, Direction.DOWN, small_dict)
        assert len(grid.placed_words) == 2

        snap = _snapshot_grid(grid)
        assert len(snap.placed_words) == 2

    def test_snapshot_cells_independent(self, small_dict: Dictionary) -> None:
        grid = Grid()
        grid.place_word("CAT", 0, 0, Direction.ACROSS, small_dict)
        snap = _snapshot_grid(grid)

        # Modifying original shouldn't affect snapshot
        grid.cells[(5, 5)] = "Z"
        assert (5, 5) not in snap.cells


class TestUnplacedLetters:
    """Bug: grid_to_json didn't report unplaced letters. Now it computes
    hand - grid and returns them in the 'unplaced' field."""

    def test_all_placed_returns_empty(self, small_dict: Dictionary) -> None:
        from web.app import grid_to_json
        grid = Grid()
        grid.place_word("CAT", 0, 0, Direction.ACROSS, small_dict)
        result = grid_to_json(grid, all_letters=["C", "A", "T"])
        assert result["unplaced"] == []

    def test_partially_placed(self, small_dict: Dictionary) -> None:
        from web.app import grid_to_json
        grid = Grid()
        grid.place_word("CAT", 0, 0, Direction.ACROSS, small_dict)
        result = grid_to_json(grid, all_letters=["C", "A", "T", "Q", "Q"])
        assert sorted(result["unplaced"]) == ["Q", "Q"]

    def test_no_letters_placed(self) -> None:
        from web.app import grid_to_json
        grid = Grid()
        result = grid_to_json(grid, all_letters=["X", "Y", "Z"])
        assert sorted(result["unplaced"]) == ["X", "Y", "Z"]

    def test_none_all_letters(self) -> None:
        from web.app import grid_to_json
        grid = Grid()
        result = grid_to_json(grid, all_letters=None)
        assert result["unplaced"] == []


class TestGetValidPlacementsNoLeak:
    """Verify that get_valid_placements doesn't leak entries into
    placed_words (it temporarily places/removes during search)."""

    def test_placed_words_stable_after_search(self, small_dict: Dictionary) -> None:
        grid = Grid()
        grid.place_word("CAT", 0, 0, Direction.ACROSS, small_dict)
        before = len(grid.placed_words)

        grid.get_valid_placements("AT", small_dict)

        assert len(grid.placed_words) == before

    def test_repeated_searches_no_growth(self, small_dict: Dictionary) -> None:
        grid = Grid()
        grid.place_word("CAT", 0, 0, Direction.ACROSS, small_dict)

        for _ in range(10):
            grid.get_valid_placements("AT", small_dict)
            grid.get_valid_placements("TA", small_dict)

        assert len(grid.placed_words) == 1


class TestSolverPlacedWordsClean:
    """Bug: solver returned grids with hundreds of duplicate placed_words.
    Now _snapshot_grid deduplicates and solve returns a snapshot."""

    def test_solve_no_duplicate_words(self, small_dict: Dictionary) -> None:
        letters = list("CATAH")
        grid = solve(letters, small_dict, timeout=5)
        if grid is None:
            pytest.skip("Solver didn't find a solution")

        # Check no duplicates in placed_words
        seen = set()
        for pw in grid.placed_words:
            key = (pw.word, pw.row, pw.col, pw.direction)
            assert key not in seen, f"Duplicate placed_word: {pw.word} at ({pw.row},{pw.col})"
            seen.add(key)

    def test_placed_words_count_reasonable(self) -> None:
        """With the full dictionary, placed_words should not exceed the
        number of cells (worst case: all 2-letter words)."""
        from src.dictionary import load_default_dictionary
        d = load_default_dictionary()
        letters = list("WHATHATTHRAWQQ")
        grid = solve(letters, d, timeout=15)
        if grid is None:
            pytest.skip("Solver didn't find a solution")

        # placed_words should be much less than cell count
        assert len(grid.placed_words) <= len(grid.cells)

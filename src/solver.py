"""Backtracking crossword grid solver for Bananagrams."""

from __future__ import annotations

import time
from collections import Counter

from src.constants import LETTER_DIFFICULTY
from src.dictionary import Dictionary
from src.grid import Direction, Grid, PlacedWord


def _word_difficulty(word: str) -> int:
    return sum(LETTER_DIFFICULTY.get(ch, 0) for ch in word)


def _sort_candidates(words: list[str]) -> list[str]:
    return sorted(words, key=lambda w: (-_word_difficulty(w), -len(w), w))


def solve(letters: list[str], dictionary: Dictionary,
          timeout: float = 60.0) -> Grid | None:
    """Arrange all letters into a valid crossword grid."""
    letter_counts = Counter(letters)
    total_letters = len(letters)

    all_words = dictionary.find_words_from_letters(letter_counts, min_length=2)
    all_words = _sort_candidates(all_words)

    if not all_words:
        print("No valid words can be formed from these letters.")
        return None

    print(f"Found {len(all_words)} candidate words from {total_letters} letters")

    grid = Grid()
    best_grid: Grid | None = None
    best_placed = 0
    start_time = time.time()
    iterations = 0

    def _remaining_letters() -> Counter[str]:
        on_grid = Counter[str]()
        for ch in grid.cells.values():
            on_grid[ch] += 1
        remaining = Counter(letter_counts)
        remaining.subtract(on_grid)
        return remaining

    def _backtrack(depth: int = 0) -> bool:
        nonlocal best_grid, best_placed, iterations

        iterations += 1
        if depth > 200:
            return False
        if iterations % 500 == 0 and time.time() - start_time > timeout:
            return False

        placed_count = grid.letter_count()

        if placed_count > best_placed:
            best_placed = placed_count
            best_grid = _snapshot_grid(grid)

        if placed_count == total_letters:
            return True

        remaining = +_remaining_letters()  # only positive counts
        if not remaining:
            return False

        remaining_total = sum(remaining.values())

        # Find words using only remaining (unplaced) letters.
        candidates = dictionary.find_words_from_letters(remaining, min_length=2)

        # When few letters remain, also find words that combine remaining letters
        # with grid letters via intersections (e.g., remaining="H", grid has "E",
        # so "HE" becomes a candidate placed through the E).
        if remaining_total <= 4 and grid.cells:
            grid_unique = set(grid.cells.values())
            for grid_ch in grid_unique:
                augmented = Counter(remaining)
                augmented[grid_ch] += 1
                extra = dictionary.find_words_from_letters(augmented, min_length=2)
                for w in extra:
                    if w not in candidates:
                        # Only add if it actually uses a remaining letter
                        wc = Counter(w)
                        uses_remaining = any(
                            min(wc[c], remaining[c]) > 0 for c in remaining
                        )
                        if uses_remaining:
                            candidates.append(w)

        candidates = _sort_candidates(candidates)

        for word in candidates:
            placements = grid.get_valid_placements(word, dictionary)
            for row, col, direction in placements:
                placed = grid.place_word(word, row, col, direction, dictionary)
                if placed is not None:
                    # Sanity check: grid must not exceed letter budget
                    r = _remaining_letters()
                    if any(v < 0 for v in r.values()):
                        grid.remove_word(placed)
                        continue
                    if _backtrack(depth + 1):
                        return True
                    grid.remove_word(placed)

            if iterations % 1000 == 0 and time.time() - start_time > timeout:
                return False

        return False

    for first_word in all_words[:30]:
        word_counter = Counter(first_word)
        if not all(word_counter[ch] <= letter_counts[ch] for ch in word_counter):
            continue

        placed = grid.place_word(first_word, 0, 0, Direction.ACROSS, dictionary)
        if placed is not None:
            if _backtrack():
                return _snapshot_grid(grid)  # deduplicates placed_words
            grid.remove_word(placed)

        if time.time() - start_time > timeout:
            break

    if best_grid is not None:
        elapsed = time.time() - start_time
        if elapsed >= timeout:
            print(f"\nTimeout after {timeout:.0f}s. Best partial: {best_placed}/{total_letters} letters placed.")
        else:
            print(f"\nNo complete solution found. Best: {best_placed}/{total_letters} letters placed.")
        return best_grid

    return None


def _snapshot_grid(grid: Grid) -> Grid:
    new = Grid()
    new.cells = dict(grid.cells)
    # Deduplicate placed_words — backtracking can leave duplicate entries
    seen: set[tuple[str, int, int, str]] = set()
    deduped: list[PlacedWord] = []
    for pw in grid.placed_words:
        key = (pw.word, pw.row, pw.col, pw.direction.name)
        if key not in seen:
            seen.add(key)
            deduped.append(pw)
    new.placed_words = deduped
    return new


# ---------------------------------------------------------------------------
# Incremental solve — used during peel loop
# ---------------------------------------------------------------------------

def incremental_solve(
    grid: Grid,
    new_letter: str,
    all_letters: list[str],
    dictionary: Dictionary,
    timeout: float = 30.0,
) -> tuple[Grid, str]:
    """Try to incorporate *new_letter* into *grid* using a 3-strategy cascade.

    Returns ``(updated_grid, strategy_name)``.
    strategy_name is one of: "quick_attach", "partial_restructure",
    "full_resolve", or "failed".
    """
    start = time.time()

    # Budget split: A=20%, B=30%, C=remaining
    budget_a = timeout * 0.20
    budget_b = timeout * 0.30

    # --- Strategy A: quick attach ---
    result = _quick_attach(grid, new_letter, all_letters, dictionary, budget_a)
    if result is not None:
        return result, "quick_attach"

    # --- Strategy B: partial restructure ---
    elapsed = time.time() - start
    remaining_b = max(0.0, budget_a + budget_b - elapsed)
    result = _partial_restructure(grid, new_letter, all_letters, dictionary, remaining_b)
    if result is not None:
        return result, "partial_restructure"

    # --- Strategy C: full re-solve ---
    # Only attempt if we have enough budget and enough unplaced letters
    # to justify the cost.  For 1-2 unplaced letters, quick_attach and
    # partial_restructure are sufficient; a full re-solve would just grind.
    elapsed = time.time() - start
    remaining_c = max(0.0, timeout - elapsed)
    unplaced_count = len(all_letters) - grid.letter_count()
    if remaining_c >= 3.0 and unplaced_count >= 3:
        result = _full_resolve(all_letters, dictionary, remaining_c)
        if result is not None:
            return result, "full_resolve"

    return grid, "failed"


def _quick_attach(
    grid: Grid,
    new_letter: str,
    all_letters: list[str],
    dictionary: Dictionary,
    timeout: float,
) -> Grid | None:
    """Find a short word (2-3 letters) containing *new_letter* that can be
    placed on the grid using exactly 1 new cell (the new letter's cell)."""
    start = time.time()
    letter_counts = Counter(all_letters)
    # We need words of length 2-3 that contain new_letter and can be formed
    # from the full letter set.
    candidates = dictionary.find_words_from_letters(
        letter_counts, min_length=2, max_length=3,
    )
    candidates = [w for w in candidates if new_letter in w]

    for word in candidates:
        if time.time() - start > timeout:
            break
        placements = grid.get_valid_placements(word, dictionary)
        for row, col, direction in placements:
            placed = grid.place_word(word, row, col, direction, dictionary)
            if placed is None:
                continue
            # Accept only if exactly 1 new cell was added (the new letter).
            if len(placed.cells_added) == 1:
                return grid
            grid.remove_word(placed)

    return None


def _partial_restructure(
    grid: Grid,
    new_letter: str,
    all_letters: list[str],
    dictionary: Dictionary,
    timeout: float,
) -> Grid | None:
    """Remove the last 1-3 placed words, freeing their letters, then try to
    re-solve with freed letters + new_letter on the existing grid."""
    start = time.time()

    if not grid.placed_words:
        return None

    # Try removing last 1, then 2, then 3 words
    for n_remove in range(1, min(4, len(grid.placed_words) + 1)):
        if time.time() - start > timeout:
            break

        snapshot = _snapshot_grid(grid)
        removed_words = list(grid.placed_words[-n_remove:])

        # Remove in reverse order
        freed_letters: list[str] = []
        for pw in reversed(removed_words):
            for r, c in pw.cells_added:
                freed_letters.append(grid.cells[(r, c)])
            grid.remove_word(pw)

        freed_letters.append(new_letter)
        freed_counts = Counter(freed_letters)

        # Try to place words using freed letters
        freed_words = dictionary.find_words_from_letters(freed_counts, min_length=2)
        freed_words = _sort_candidates(freed_words)

        placed_all = _mini_backtrack(
            grid, freed_letters, freed_words, dictionary,
            start, timeout,
        )
        if placed_all:
            return grid

        # Restore grid from snapshot
        grid.cells = snapshot.cells
        grid.placed_words = snapshot.placed_words

    return None


def _mini_backtrack(
    grid: Grid,
    letters_to_place: list[str],
    candidates: list[str],
    dictionary: Dictionary,
    start_time: float,
    timeout: float,
) -> bool:
    """Small backtracking search to place *letters_to_place* onto *grid*.

    Tracks remaining letters by counting cells_added (new cells consumed
    from our budget) across all placements in the current stack.
    """
    budget = Counter(letters_to_place)

    def _used() -> Counter[str]:
        """Letters from our budget currently on the grid."""
        used = Counter[str]()
        for pw in grid.placed_words:
            for r, c in pw.cells_added:
                ch = grid.cells.get((r, c))
                if ch:
                    used[ch] += 1
        return used

    def _remaining() -> Counter[str]:
        # We only care about letters_to_place that aren't yet on the grid
        # via cells we added.  But cells_added from *prior* words (before
        # this mini-backtrack) shouldn't count.  We snapshot the placed
        # words at entry and only count cells_added from words added *after*.
        return budget  # recalculated each call below

    initial_words = set(id(pw) for pw in grid.placed_words)

    def _get_remaining() -> Counter[str]:
        rem = Counter(budget)
        for pw in grid.placed_words:
            if id(pw) in initial_words:
                continue
            for r, c in pw.cells_added:
                ch = grid.cells.get((r, c))
                if ch and rem[ch] > 0:
                    rem[ch] -= 1
        return +rem  # only positive counts

    def _bt() -> bool:
        if time.time() - start_time > timeout:
            return False
        rem = _get_remaining()
        if not rem:
            return True

        usable = dictionary.find_words_from_letters(rem, min_length=2)
        usable = _sort_candidates(usable)

        for word in usable:
            placements = grid.get_valid_placements(word, dictionary)
            for row, col, direction in placements:
                placed = grid.place_word(word, row, col, direction, dictionary)
                if placed is None:
                    continue
                # Verify we haven't exceeded our budget
                new_rem = _get_remaining()
                if any(v < 0 for v in new_rem.values()):
                    grid.remove_word(placed)
                    continue
                if _bt():
                    return True
                grid.remove_word(placed)
        return False

    return _bt()


def _full_resolve(
    all_letters: list[str],
    dictionary: Dictionary,
    timeout: float,
) -> Grid | None:
    """Full re-solve from scratch."""
    return solve(all_letters, dictionary, timeout=timeout)

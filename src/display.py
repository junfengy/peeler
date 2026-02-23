"""Terminal rendering of the crossword grid."""

from __future__ import annotations

from src.grid import Grid


def render_grid(grid: Grid) -> str:
    """Render the grid as a string for terminal display."""
    if not grid.cells:
        return "(empty grid)"

    min_row, max_row, min_col, max_col = grid.bounds()

    lines: list[str] = []

    # Column headers
    col_nums = range(min_col, max_col + 1)
    header = "    " + "".join(f"{c:3d}" for c in col_nums)
    lines.append(header)
    lines.append("    " + "---" * (max_col - min_col + 1))

    for row in range(min_row, max_row + 1):
        parts: list[str] = [f"{row:3d}|"]
        for col in range(min_col, max_col + 1):
            letter = grid.get(row, col)
            if letter is not None:
                parts.append(f"  {letter}")
            else:
                parts.append("  .")
        lines.append("".join(parts))

    return "\n".join(lines)


def print_grid(grid: Grid) -> None:
    """Print the grid to the terminal."""
    print("\n" + render_grid(grid))


def print_word_list(grid: Grid) -> None:
    """Print the list of placed words."""
    if not grid.placed_words:
        print("No words placed.")
        return

    print(f"\nPlaced {len(grid.placed_words)} words ({grid.letter_count()} letters):")
    for pw in grid.placed_words:
        dir_str = "ACROSS" if pw.direction.name == "ACROSS" else "DOWN"
        print(f"  {pw.word:<15s} at ({pw.row},{pw.col}) {dir_str}")


def print_solution(grid: Grid, total_letters: int) -> None:
    """Print the complete solution with grid and word list."""
    print_grid(grid)
    print_word_list(grid)
    placed = grid.letter_count()
    if placed < total_letters:
        print(f"\n  ** Partial solution: {placed}/{total_letters} letters placed **")
    else:
        print(f"\n  All {total_letters} letters placed!")

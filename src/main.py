"""CLI entry point for the Bananagrams solver."""

from __future__ import annotations

import argparse
import re
import sys

from src.dictionary import Dictionary, load_default_dictionary
from src.display import print_grid, print_solution
from src.grid import Grid
from src.pool import TilePool
from src.solver import incremental_solve, solve
from src.swap import print_swap_analysis


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bananagrams Solver — arrange tiles into a crossword grid",
    )
    parser.add_argument(
        "--letters", "-l",
        type=str,
        help='Letters to solve, e.g. "AACEJNORT" or "A,A,C,E,J,N,O,R,T"',
    )
    parser.add_argument(
        "--no-camera",
        action="store_true",
        help="Skip camera capture; enter letters interactively",
    )
    parser.add_argument(
        "--timeout", "-t",
        type=float,
        default=60.0,
        help="Solver timeout in seconds (default: 60)",
    )
    parser.add_argument(
        "--no-swap",
        action="store_true",
        help="Skip swap analysis",
    )
    parser.add_argument(
        "--peel",
        action="store_true",
        help="Enable interactive peel mode",
    )
    return parser.parse_args()


def get_letters_from_input() -> list[str]:
    """Prompt the user to type their letters."""
    raw = input("Enter your letters (e.g. AACEJNORT or A,A,C,E): ").strip().upper()
    parts = re.split(r"[,\s]+", raw)
    letters = [ch for ch in parts if re.match(r"^[A-Z]$", ch)]
    # Also handle a single string like "AACEJNORT"
    if len(letters) == 0 and len(raw) > 0:
        letters = [ch for ch in raw if ch.isalpha()]
    if not letters:
        print("No valid letters entered.")
        sys.exit(1)
    return letters


def get_letters_from_camera() -> list[str]:
    """Capture image and use OCR to recognize tiles."""
    from src.camera import capture_image
    from src.ocr import confirm_letters, recognize_letters

    image_path = capture_image()
    letters = recognize_letters(image_path)
    letters = confirm_letters(letters)
    return letters


def peel_loop(
    grid: Grid,
    letters: list[str],
    dictionary: Dictionary,
    pool: TilePool,
    timeout: float,
) -> None:
    """Interactive peel loop: draw new tiles and incrementally solve."""
    all_letters = list(letters)

    while True:
        # Show current state
        print_grid(grid)
        print(f"\nPool: {pool.remaining()} tiles remaining")
        print(f"Hand: {len(all_letters)} letters")

        # Swap analysis for current hand
        print_swap_analysis(all_letters, dictionary)

        # Prompt
        print("\n[P]eel / [M]anual / [S]wap / [Q]uit")
        try:
            choice = input("> ").strip().upper()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting peel mode.")
            break

        if choice == "Q":
            print("Exiting peel mode.")
            break

        if choice == "S":
            try:
                raw = input("Letter to swap: ").strip().upper()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting peel mode.")
                break
            if len(raw) != 1 or not raw.isalpha() or raw not in all_letters:
                print(f"Invalid — you don't have '{raw}' in your hand.")
                continue
            drawn = pool.swap(raw)
            if drawn is None:
                print("Not enough tiles in pool to swap (need 3).")
                continue
            all_letters.remove(raw)
            all_letters.extend(drawn)
            print(f"\nSwapped {raw} → drew {', '.join(drawn)}")
            # Full re-solve with updated hand
            print(f"Re-solving with {len(all_letters)} letters...")
            new_grid = solve(all_letters, dictionary, timeout=timeout)
            if new_grid is not None:
                grid = new_grid
            else:
                print("Could not solve after swap.")
            continue

        new_letter: str | None = None

        if choice == "P":
            new_letter = pool.draw()
            if new_letter is None:
                print("Pool is empty! No more tiles to draw.")
                continue
            print(f"\nDrew: {new_letter}")

        elif choice == "M":
            try:
                raw = input("Enter letter: ").strip().upper()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting peel mode.")
                break
            if len(raw) == 1 and raw.isalpha():
                new_letter = raw
            else:
                print("Invalid input. Enter a single letter A-Z.")
                continue

        else:
            print("Invalid choice.")
            continue

        # Incorporate new letter
        all_letters.append(new_letter)
        print(f"\nIncorporating {new_letter} into grid ({len(all_letters)} total letters)...")

        grid, strategy = incremental_solve(
            grid, new_letter, all_letters, dictionary, timeout=timeout,
        )

        if strategy == "failed":
            print(f"Could not place {new_letter}. Letter remains unplaced.")
        else:
            print(f"Solved using strategy: {strategy}")

    # Final state
    print("\n=== Final Grid ===")
    print_solution(grid, len(all_letters))


def main() -> None:
    args = parse_args()

    # 1. Get letters
    if args.letters:
        # Parse from command line
        raw = args.letters.upper()
        parts = re.split(r"[,\s]+", raw)
        letters = [ch for ch in parts if re.match(r"^[A-Z]$", ch)]
        if not letters:
            letters = [ch for ch in raw if ch.isalpha()]
    elif args.no_camera:
        letters = get_letters_from_input()
    else:
        letters = get_letters_from_camera()

    print(f"\nSolving with {len(letters)} letters: {' '.join(sorted(letters))}")

    # 2. Load dictionary
    print("Loading dictionary...")
    dictionary = load_default_dictionary()
    print(f"Loaded {dictionary.word_count} words.")

    # 3. Solve
    print(f"\nSolving (timeout: {args.timeout:.0f}s)...")
    grid = solve(letters, dictionary, timeout=args.timeout)

    if grid is None:
        print("\nNo solution found.")
        sys.exit(1)

    # 4. Display
    print_solution(grid, len(letters))

    # 5. Swap analysis (skip if entering peel mode — it shows analysis each round)
    if not args.no_swap and not args.peel:
        print_swap_analysis(letters, dictionary)

    # 6. Peel mode
    if args.peel:
        pool = TilePool(letters)
        peel_loop(grid, letters, dictionary, pool, timeout=args.timeout)


if __name__ == "__main__":
    main()

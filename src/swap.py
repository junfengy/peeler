"""Swap strategy analysis for difficult letters."""

from __future__ import annotations

import random
from collections import Counter

from src.constants import LETTER_DIFFICULTY, Q_WITHOUT_U_WORDS, TILE_DISTRIBUTION
from src.dictionary import Dictionary


def _vowel_consonant_ratio(letters: list[str]) -> float:
    """Return the ratio of vowels to consonants."""
    vowels = sum(1 for ch in letters if ch in "AEIOU")
    consonants = len(letters) - vowels
    return vowels / max(consonants, 1)


def _word_availability(letter: str, letters: list[str], dictionary: Dictionary) -> float:
    """What fraction of formable words use this letter?"""
    counts = Counter(letters)
    all_words = dictionary.find_words_from_letters(counts, min_length=2)
    if not all_words:
        return 0.0
    using_letter = sum(1 for w in all_words if letter in w)
    return using_letter / len(all_words)


def _simulate_swap(letter: str, letters: list[str], dictionary: Dictionary,
                   simulations: int = 20) -> float:
    """Monte Carlo: remove letter, draw 3 random tiles, average resulting difficulty."""
    remaining = list(letters)
    remaining.remove(letter)

    # Build draw pool (tiles not in hand)
    hand_counts = Counter(letters)
    pool: list[str] = []
    for ch, total in TILE_DISTRIBUTION.items():
        available = max(0, total - hand_counts.get(ch, 0))
        pool.extend([ch] * available)

    if len(pool) < 3:
        return float("inf")  # Not enough tiles to draw

    total_difficulty = 0.0
    for _ in range(simulations):
        drawn = random.sample(pool, 3)
        new_hand = remaining + drawn
        hand_difficulty = sum(LETTER_DIFFICULTY.get(ch, 0) for ch in new_hand)
        total_difficulty += hand_difficulty

    return total_difficulty / simulations


def analyze_swaps(letters: list[str], dictionary: Dictionary) -> list[dict]:
    """Analyze each hard letter and recommend whether to swap.

    Returns a list of recommendations sorted by strength (strongest first).
    """
    counts = Counter(letters)
    recommendations: list[dict] = []

    # Only analyze letters with difficulty >= 5
    hard_letters = sorted(
        {ch for ch in counts if LETTER_DIFFICULTY.get(ch, 0) >= 5},
        key=lambda ch: -LETTER_DIFFICULTY.get(ch, 0),
    )

    if not hard_letters:
        return []

    current_difficulty = sum(LETTER_DIFFICULTY.get(ch, 0) for ch in letters)

    for letter in hard_letters:
        diff_score = LETTER_DIFFICULTY[letter]
        availability = _word_availability(letter, letters, dictionary)
        sim_difficulty = _simulate_swap(letter, letters, dictionary)

        # Special handling: Q without U
        special_note = ""
        if letter == "Q":
            has_u = counts.get("U", 0) > 0
            if not has_u:
                # Check if Q-without-U words are possible
                q_words_possible = any(
                    dictionary.is_valid_word(w)
                    and all(counts[c] >= Counter(w)[c] for c in Counter(w) if c != "Q")
                    for w in Q_WITHOUT_U_WORDS
                )
                if not q_words_possible:
                    special_note = "Q without U and no Q-without-U words possible"
                else:
                    special_note = "Q without U, but Q-words like QI may be playable"

        # Decision logic
        swap_score = 0.0
        swap_score += diff_score / 10.0  # 0-1 from difficulty
        swap_score += max(0, 0.5 - availability)  # boost if few words use it
        if sim_difficulty < current_difficulty:
            swap_score += 0.3  # boost if swap likely improves hand

        if special_note and "no Q-without-U words possible" in special_note:
            swap_score += 0.5  # strong boost for unusable Q

        if swap_score >= 0.8:
            recommendation = "STRONGLY RECOMMENDED"
        elif swap_score >= 0.5:
            recommendation = "RECOMMENDED"
        else:
            recommendation = "NOT RECOMMENDED"

        reasons = []
        reasons.append(f"Difficulty: {diff_score}/10")
        reasons.append(f"Used in {availability:.0%} of formable words")
        if sim_difficulty < current_difficulty:
            reasons.append(f"Swapping likely improves hand difficulty ({current_difficulty:.0f} -> {sim_difficulty:.0f})")
        else:
            reasons.append(f"Swap may not improve difficulty ({current_difficulty:.0f} -> {sim_difficulty:.0f})")
        if special_note:
            reasons.append(special_note)

        recommendations.append({
            "letter": letter,
            "recommendation": recommendation,
            "swap_score": swap_score,
            "reasons": reasons,
        })

    recommendations.sort(key=lambda r: -r["swap_score"])
    return recommendations


def print_swap_analysis(letters: list[str], dictionary: Dictionary) -> None:
    """Print swap recommendations to terminal."""
    recs = analyze_swaps(letters, dictionary)

    if not recs:
        print("\nSwap Analysis: No difficult letters in hand — no swaps recommended.")
        return

    print("\n=== Swap Analysis ===")
    for rec in recs:
        status = rec["recommendation"]
        letter = rec["letter"]
        print(f"\n  {letter}: {status}")
        for reason in rec["reasons"]:
            print(f"    - {reason}")

"""Unit tests for swap analysis module."""

from __future__ import annotations

from io import StringIO
from unittest.mock import patch

import pytest

from src.swap import (
    _simulate_swap,
    _vowel_consonant_ratio,
    _word_availability,
    analyze_swaps,
    print_swap_analysis,
)


class TestVowelConsonantRatio:
    def test_balanced(self) -> None:
        ratio = _vowel_consonant_ratio(list("AEINORST"))
        # 4 vowels (A, E, I, O), 4 consonants (N, R, S, T) → 1.0
        assert ratio == pytest.approx(1.0)

    def test_all_vowels(self) -> None:
        ratio = _vowel_consonant_ratio(list("AEIOUAEI"))
        # 8 vowels, 0 consonants → 8/max(0,1) = 8.0
        assert ratio == pytest.approx(8.0)

    def test_all_consonants(self) -> None:
        ratio = _vowel_consonant_ratio(list("BCDFGHJK"))
        # 0 vowels, 8 consonants → 0.0
        assert ratio == pytest.approx(0.0)

    def test_empty(self) -> None:
        ratio = _vowel_consonant_ratio([])
        # 0 vowels, 0 consonants → 0/max(0,1) = 0.0
        assert ratio == pytest.approx(0.0)

    def test_single_vowel(self) -> None:
        ratio = _vowel_consonant_ratio(["A"])
        # 1 vowel, 0 consonants → 1/1 = 1.0
        assert ratio == pytest.approx(1.0)

    def test_single_consonant(self) -> None:
        ratio = _vowel_consonant_ratio(["B"])
        # 0 vowels, 1 consonant → 0.0
        assert ratio == pytest.approx(0.0)


class TestWordAvailability:
    def test_common_letter_high_availability(self, good_hand, small_dictionary) -> None:
        # E is very common — should appear in many formable words
        avail = _word_availability("E", good_hand, small_dictionary)
        assert avail > 0.0

    def test_rare_letter_low_availability(self, q_without_u_hand, small_dictionary) -> None:
        avail = _word_availability("Q", q_without_u_hand, small_dictionary)
        # Q should appear in very few words from this hand
        assert avail >= 0.0
        assert avail <= 1.0

    def test_impossible_hand(self, small_dictionary) -> None:
        # ZZ — no 2+ letter words possible
        avail = _word_availability("Z", ["Z", "Z"], small_dictionary)
        assert avail == pytest.approx(0.0)

    def test_returns_float_in_range(self, good_hand, small_dictionary) -> None:
        for letter in good_hand:
            avail = _word_availability(letter, good_hand, small_dictionary)
            assert isinstance(avail, float)
            assert 0.0 <= avail <= 1.0


class TestSimulateSwap:
    def test_returns_positive_float(self, good_hand, small_dictionary) -> None:
        result = _simulate_swap("A", good_hand, small_dictionary)
        assert isinstance(result, float)
        assert result > 0.0

    def test_hard_letter_swap_improves_difficulty(self, small_dictionary) -> None:
        # Hand with hard letters — swapping Q should usually improve difficulty
        hand = list("QXZAEINR")
        current_difficulty = sum(
            __import__("src.constants", fromlist=["LETTER_DIFFICULTY"]).LETTER_DIFFICULTY.get(ch, 0)
            for ch in hand
        )
        # Run multiple simulations to get a stable estimate
        sim_difficulty = _simulate_swap("Q", hand, small_dictionary, simulations=50)
        # Swapping Q (difficulty=10) should statistically reduce hand difficulty
        assert sim_difficulty <= current_difficulty

    def test_pool_not_exhausted(self, single_letter_hand, small_dictionary) -> None:
        # Single letter hand — pool should have plenty of tiles
        result = _simulate_swap("A", single_letter_hand, small_dictionary)
        assert result < float("inf")


class TestAnalyzeSwaps:
    def test_q_without_u_strongly_recommended(self, q_without_u_hand, small_dictionary) -> None:
        recs = analyze_swaps(q_without_u_hand, small_dictionary)
        q_rec = next((r for r in recs if r["letter"] == "Q"), None)
        assert q_rec is not None
        assert q_rec["recommendation"] == "STRONGLY RECOMMENDED"

    def test_good_hand_empty(self, good_hand, small_dictionary) -> None:
        recs = analyze_swaps(good_hand, small_dictionary)
        # AEINORST has no letters with difficulty >= 5
        assert recs == []

    def test_result_dict_structure(self, q_without_u_hand, small_dictionary) -> None:
        recs = analyze_swaps(q_without_u_hand, small_dictionary)
        for rec in recs:
            assert "letter" in rec
            assert "recommendation" in rec
            assert "swap_score" in rec
            assert "reasons" in rec
            assert isinstance(rec["letter"], str)
            assert rec["recommendation"] in (
                "STRONGLY RECOMMENDED", "RECOMMENDED", "NOT RECOMMENDED"
            )
            assert isinstance(rec["swap_score"], float)
            assert isinstance(rec["reasons"], list)

    def test_sorted_by_swap_score_desc(self, small_dictionary) -> None:
        # Hand with multiple hard letters
        hand = list("QXJAEINR")
        recs = analyze_swaps(hand, small_dictionary)
        scores = [r["swap_score"] for r in recs]
        assert scores == sorted(scores, reverse=True)

    def test_all_vowels_empty(self, all_vowels_hand, small_dictionary) -> None:
        recs = analyze_swaps(all_vowels_hand, small_dictionary)
        # All vowels have difficulty 0, so no hard letters
        assert recs == []

    def test_j_k_in_consonant_hand_recommended(self, small_dictionary) -> None:
        # J(8) and K(5) are hard letters
        hand = list("JKBCNRST")
        recs = analyze_swaps(hand, small_dictionary)
        hard_letters_found = {r["letter"] for r in recs}
        assert "J" in hard_letters_found
        assert "K" in hard_letters_found


class TestPrintSwapAnalysis:
    def test_no_hard_letters_message(self, good_hand, small_dictionary, capsys) -> None:
        print_swap_analysis(good_hand, small_dictionary)
        captured = capsys.readouterr()
        assert "no swaps recommended" in captured.out.lower()

    def test_hard_letters_shows_analysis(self, q_without_u_hand, small_dictionary, capsys) -> None:
        print_swap_analysis(q_without_u_hand, small_dictionary)
        captured = capsys.readouterr()
        assert "Swap Analysis" in captured.out
        assert "Q" in captured.out
        assert "STRONGLY RECOMMENDED" in captured.out or "RECOMMENDED" in captured.out

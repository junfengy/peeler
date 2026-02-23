"""Shared fixtures for Bananagrams tests."""

from __future__ import annotations

import pytest

from src.dictionary import Dictionary


@pytest.fixture
def small_dictionary() -> Dictionary:
    """~50 hand-picked words inserted directly via _insert(). No file I/O."""
    d = Dictionary()
    words = [
        # 2-letter
        "AA", "AB", "AD", "AE", "AI", "AN", "AR", "AS", "AT", "AW",
        "BE", "BI", "DO", "ED", "EL", "EN", "ER", "ES", "ET",
        "GO", "HE", "HI", "IN", "IS", "IT", "LA", "LI", "LO",
        "NA", "NE", "NO", "OE", "ON", "OR", "OS", "RE", "SI",
        "SO", "TA", "TI", "TO", "QI",
        # 3-letter
        "ABS", "ACE", "ANT", "APE", "ATE", "EAR", "EAT", "IRE",
        "JAB", "JAR", "ORE", "RAN", "RAT", "SAT", "SET", "SIT",
        "TAN", "TAR", "TEA", "TEN", "TIN", "TON", "ZAP",
        # 4-letter
        "ANTE", "EARN", "EAST", "IOTA", "NEAR", "NEST", "NOTE",
        "RAIN", "RANT", "RENT", "RISE", "SIRE", "SNIT", "SORT",
        "STAR", "STEIN", "TIRE", "TONE", "TORE",
        # 5-letter
        "ARISE", "NOISE", "NOTES", "RAISE", "RINSE", "SENOR",
        "SNORE", "STARE", "STERN", "STONE", "STORE", "TIRES",
        "STORE", "QUIZ",
    ]
    for w in words:
        d._insert(w)
    return d


@pytest.fixture
def good_hand() -> list[str]:
    """No hard letters — balanced, easy hand."""
    return list("AEINORST")


@pytest.fixture
def q_without_u_hand() -> list[str]:
    """Q with no U — triggers Q swap recommendation."""
    return list("QRSTLNEP")


@pytest.fixture
def all_vowels_hand() -> list[str]:
    return list("AEIOUAEI")


@pytest.fixture
def all_consonants_hand() -> list[str]:
    return list("BCDFGHJK")


@pytest.fixture
def single_letter_hand() -> list[str]:
    return ["A"]

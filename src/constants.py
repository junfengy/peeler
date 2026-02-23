"""Bananagrams game constants: tile distribution and letter difficulty scores."""

# Official Bananagrams tile distribution (144 tiles total)
TILE_DISTRIBUTION: dict[str, int] = {
    "A": 13, "B": 3, "C": 3, "D": 6, "E": 18, "F": 3,
    "G": 4, "H": 3, "I": 12, "J": 2, "K": 2, "L": 5,
    "M": 3, "N": 8, "O": 11, "P": 3, "Q": 2, "R": 9,
    "S": 6, "T": 9, "U": 6, "V": 3, "W": 3, "X": 2,
    "Y": 3, "Z": 2,
}

# Letter difficulty scores (higher = harder to use)
# Based on Scrabble point values and Bananagrams playability
LETTER_DIFFICULTY: dict[str, int] = {
    "A": 0, "B": 3, "C": 3, "D": 2, "E": 0, "F": 4,
    "G": 2, "H": 3, "I": 0, "J": 8, "K": 5, "L": 1,
    "M": 3, "N": 1, "O": 0, "P": 3, "Q": 10, "R": 1,
    "S": 1, "T": 1, "U": 0, "V": 5, "W": 4, "X": 9,
    "Y": 3, "Z": 9,
}

# Letters that are valid in Scrabble words without U after Q
Q_WITHOUT_U_WORDS = {"QI", "QOPH", "QADI", "QAID", "QANAT", "QAT", "QINTAR",
                     "QINDAR", "QOPH", "QWERTY", "TRANQ", "SHEQEL", "QOPHS",
                     "QADIS", "QAIDS", "QANATS", "QATS", "QINTARS", "QINDARS"}

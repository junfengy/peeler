# Peeler

A Bananagrams solver that arranges letter tiles into a valid crossword grid. Includes a web UI with camera-based tile recognition and a full game loop (solve, peel, swap).

## Features

- **Backtracking solver** — arranges letters into a connected crossword grid using the SOWPODS dictionary (267k words)
- **Camera OCR** — photograph your tiles and recognize letters via Ollama vision models (llama3.2-vision) or Claude API
- **Incremental solve** — 3-strategy cascade (quick attach, partial restructure, full re-solve) for adding new letters without starting over
- **Swap analysis** — scores each unplaced letter and recommends which to swap back to the pool
- **Web UI** — single-page Flask app with grid display, peel/swap actions, and unplaced letter tracking
- **CLI** — terminal-based solver with camera capture and interactive peel loop

## Quick Start

### Web App

```bash
pip install -r requirements.txt
python3 web/app.py
```

Open https://localhost:8080. Type letters and click Solve, or use the camera to photograph tiles.

### CLI

```bash
python3 -m src.main --letters WHATHATTHRAW
```

Or launch with camera capture:

```bash
python3 -m src.main
```

## Project Structure

```
peeler/
├── data/
│   └── sowpods.txt          # SOWPODS dictionary (267k words)
├── src/
│   ├── constants.py         # Tile distribution, letter difficulty scores
│   ├── dictionary.py        # Trie-based dictionary with prefix/word lookup
│   ├── grid.py              # Grid state, word placement, cross-word validation
│   ├── solver.py            # Backtracking solver, incremental solve, snapshots
│   ├── ocr.py               # Claude Vision API for tile recognition
│   ├── pool.py              # Tile pool (draw, swap)
│   ├── swap.py              # Swap analysis and recommendations
│   ├── camera.py            # OpenCV camera capture
│   ├── display.py           # Terminal grid display
│   └── main.py              # CLI entry point
├── web/
│   ├── app.py               # Flask backend (all routes, game state)
│   └── templates/
│       └── index.html       # Single-page frontend (inline CSS/JS)
├── tests/
│   ├── test_bugfixes.py     # Regression tests for fixed bugs
│   ├── test_ocr.py          # OCR unit + integration tests
│   └── test_swap.py         # Swap analysis tests
├── pyproject.toml
└── requirements.txt
```

## How the Solver Works

1. **Find candidate words** from the available letters using the dictionary
2. **Sort by difficulty** — prioritize hard letters (Q, X, Z, J) to place them early
3. **Backtrack** — try placing each word on the grid, recurse, undo if stuck
4. **Unplaceable detection** — letters that can't appear in any candidate word are excluded upfront
5. **Snapshot deduplication** — grid snapshots deduplicate placed words accumulated during backtracking

### Incremental Solve (Peel/Swap)

When a new letter arrives, three strategies are tried in order:

| Strategy | Budget | Description |
|----------|--------|-------------|
| Quick attach | 20% | Find a 2-3 letter word that adds exactly 1 new cell |
| Partial restructure | 30% | Remove last 1-3 words, re-solve with freed letters |
| Full re-solve | remaining | Solve from scratch with all letters |

## Web App Routes

| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Serve the UI |
| `/ocr` | POST | Camera image → letter recognition |
| `/solve` | POST | Letters → initial grid solve |
| `/peel` | POST | Draw a random tile from the pool |
| `/manual` | POST | Add specific letters to the hand |
| `/swap` | POST | Return a letter, draw 3 from pool |
| `/analyze` | POST | Swap score recommendations |

## OCR

Tile recognition tries models in order:

1. **llama3.2-vision** (Ollama, local, 11B) — best accuracy
2. **minicpm-v** (Ollama, local, 5.5B) — fallback
3. **moondream** (Ollama, local, 1.7B) — fallback
4. **Claude API** (cloud) — final fallback, requires `ANTHROPIC_API_KEY`

## Tests

```bash
python3 -m pytest tests/ -v
```

## Requirements

- Python 3.10+
- Flask 3.0+
- For OCR: [Ollama](https://ollama.com) with a vision model, or an Anthropic API key
- For CLI camera: OpenCV (`opencv-python`)

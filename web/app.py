"""Bananagrams web application — Flask backend."""
from __future__ import annotations

import base64
import re
import sys
import tempfile
import uuid
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError
import json as _json

# Ensure project root is on sys.path so `src.*` imports work
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from flask import Flask, jsonify, render_template, request

from src.dictionary import load_default_dictionary
from src.grid import Grid, Direction
from src.ocr import recognize_letters
from src.pool import TilePool
from src.solver import solve, incremental_solve
from src.swap import analyze_swaps

sys.setrecursionlimit(10000)

app = Flask(__name__)

# Load dictionary once at startup
DICTIONARY = load_default_dictionary()

# Ollama vision models to try, in order of preference
OLLAMA_MODELS = ["minicpm-v", "moondream"]
OLLAMA_URL = "http://localhost:11434"

TILE_PROMPT = (
    "This image shows Bananagrams letter tiles. "
    "Identify each individual letter tile visible in the image. "
    "Return ONLY a comma-separated list of uppercase letters, "
    "one entry per tile. For example: A, B, C, A, E\n"
    "Include duplicates — list every tile you see."
)


def _parse_letters(text: str) -> list[str]:
    """Extract single uppercase letters from a model response."""
    raw = re.split(r"[,\s]+", text.strip())
    return [p.strip().upper() for p in raw if re.match(r"^[A-Za-z]$", p.strip())]


def _ollama_ocr(image_b64: str) -> list[str] | None:
    """Try OCR via Ollama vision models. Returns letters or None."""
    for model in OLLAMA_MODELS:
        try:
            payload = _json.dumps({
                "model": model,
                "prompt": TILE_PROMPT,
                "images": [image_b64],
                "stream": False,
            }).encode()
            req = Request(
                f"{OLLAMA_URL}/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urlopen(req, timeout=60) as resp:
                body = _json.loads(resp.read())
            text = body.get("response", "")
            letters = _parse_letters(text)
            if letters:
                print(f"Ollama OCR ({model}): {letters}")
                return letters
            print(f"Ollama OCR ({model}): no letters parsed from: {text!r}")
        except (URLError, OSError, KeyError, ValueError) as e:
            print(f"Ollama OCR ({model}) failed: {e}")
            continue
    return None

# Game state keyed by session UUID
GAMES: dict[str, dict] = {}


def grid_to_json(grid: Grid, all_letters: list[str] | None = None) -> dict:
    """Serialize a Grid to the JSON format expected by the frontend."""
    min_r, max_r, min_c, max_c = grid.bounds()
    cells = [
        {"row": r, "col": c, "letter": letter}
        for (r, c), letter in sorted(grid.cells.items())
    ]
    words = [
        {
            "word": pw.word,
            "row": pw.row,
            "col": pw.col,
            "direction": pw.direction.name,
        }
        for pw in grid.placed_words
    ]
    count = grid.letter_count()
    total = len(all_letters) if all_letters else count

    # Calculate unplaced letters
    unplaced: list[str] = []
    if all_letters:
        from collections import Counter
        hand = Counter(all_letters)
        on_grid = Counter(grid.cells.values())
        remaining = hand - on_grid
        unplaced = sorted(remaining.elements())

    return {
        "cells": cells,
        "bounds": {
            "min_row": min_r,
            "max_row": max_r,
            "min_col": min_c,
            "max_col": max_c,
        },
        "words": words,
        "letter_count": count,
        "total_letters": total,
        "unplaced": unplaced,
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/ocr", methods=["POST"])
def ocr():
    data = request.get_json()
    image_data = data.get("image", "")
    # Strip data URL prefix if present
    if "," in image_data:
        image_data = image_data.split(",", 1)[1]

    # Try Ollama first (free, local)
    letters = _ollama_ocr(image_data)
    if letters:
        return jsonify({"letters": letters, "source": "ollama"})

    # Fall back to Claude API
    raw = base64.b64decode(image_data)
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        f.write(raw)
        tmp_path = f.name
    try:
        letters = recognize_letters(tmp_path)
    except Exception as e:
        return jsonify({"error": f"OCR failed: {e}"}), 500
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    return jsonify({"letters": letters, "source": "claude"})


@app.route("/solve", methods=["POST"])
def solve_route():
    data = request.get_json()
    letters = [ch.upper() for ch in data.get("letters", []) if ch.isalpha()]
    timeout = float(data.get("timeout", 60))
    if not letters:
        return jsonify({"error": "No letters provided"}), 400

    try:
        grid = solve(letters, DICTIONARY, timeout=timeout)
    except RecursionError:
        return jsonify({"error": "Too many letters — solver hit recursion limit"}), 200
    except Exception as e:
        return jsonify({"error": f"Solve error: {e}"}), 500
    if grid is None:
        return jsonify({"error": "No solution found"}), 200

    session_id = str(uuid.uuid4())
    pool = TilePool(letters)
    GAMES[session_id] = {"grid": grid, "letters": list(letters), "pool": pool}
    result = grid_to_json(grid, all_letters=letters)
    result["session_id"] = session_id
    result["pool_remaining"] = pool.remaining()
    return jsonify(result)


@app.route("/peel", methods=["POST"])
def peel():
    data = request.get_json()
    session_id = data.get("session_id", "")
    game = GAMES.get(session_id)
    if game is None:
        return jsonify({"error": "Session not found"}), 404

    pool: TilePool = game["pool"]
    if pool.is_empty():
        return jsonify({"error": "Pool is empty — you win!", "win": True}), 200

    new_letter = pool.draw()
    if new_letter is None:
        return jsonify({"error": "Pool is empty — you win!", "win": True}), 200

    game["letters"].append(new_letter)
    grid, strategy = incremental_solve(
        game["grid"], new_letter, game["letters"], DICTIONARY
    )
    game["grid"] = grid
    result = grid_to_json(grid, all_letters=game["letters"])
    result["session_id"] = session_id
    result["new_letter"] = new_letter
    result["strategy"] = strategy
    result["pool_remaining"] = pool.remaining()
    return jsonify(result)


@app.route("/manual", methods=["POST"])
def manual():
    data = request.get_json()
    session_id = data.get("session_id", "")
    game = GAMES.get(session_id)
    if game is None:
        return jsonify({"error": "Session not found"}), 404

    # Accept "letters" (list or string) or single "letter"
    raw = data.get("letters") or data.get("letter", "")
    if isinstance(raw, list):
        letters = [ch.upper() for ch in raw if ch.isalpha()]
    else:
        letters = [ch.upper() for ch in str(raw) if ch.isalpha()]
    if not letters:
        return jsonify({"error": "No valid letters provided"}), 400

    strategy = ""
    for letter in letters:
        game["letters"].append(letter)
        game["grid"], strategy = incremental_solve(
            game["grid"], letter, game["letters"], DICTIONARY
        )

    result = grid_to_json(game["grid"], all_letters=game["letters"])
    result["session_id"] = session_id
    result["strategy"] = strategy
    result["added"] = letters
    result["pool_remaining"] = game["pool"].remaining()
    return jsonify(result)


@app.route("/swap", methods=["POST"])
def swap():
    data = request.get_json()
    session_id = data.get("session_id", "")
    letter = data.get("letter", "").upper()
    game = GAMES.get(session_id)
    if game is None:
        return jsonify({"error": "Session not found"}), 404
    if not letter or not letter.isalpha() or len(letter) != 1:
        return jsonify({"error": "Invalid letter"}), 400
    if letter not in game["letters"]:
        return jsonify({"error": f"Letter '{letter}' not in your hand"}), 400

    pool: TilePool = game["pool"]
    drawn = pool.swap(letter)
    if drawn is None:
        return jsonify({"error": "Not enough tiles in pool to swap"}), 400

    game["letters"].remove(letter)
    game["letters"].extend(drawn)

    grid = solve(game["letters"], DICTIONARY, timeout=60)
    if grid is None:
        return jsonify({"error": "No solution found after swap"}), 200

    game["grid"] = grid
    result = grid_to_json(grid, all_letters=game["letters"])
    result["session_id"] = session_id
    result["drawn_tiles"] = drawn
    result["pool_remaining"] = pool.remaining()
    return jsonify(result)


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    session_id = data.get("session_id", "")
    game = GAMES.get(session_id)
    if game is None:
        return jsonify({"error": "Session not found"}), 404

    # Only analyze unplaced letters — those are the problem tiles
    from collections import Counter
    hand = Counter(game["letters"])
    on_grid = Counter(game["grid"].cells.values())
    remaining = hand - on_grid
    unplaced = sorted(remaining.elements())

    if not unplaced:
        return jsonify({"recommendations": []})

    recommendations = analyze_swaps(unplaced, DICTIONARY)
    return jsonify({"recommendations": recommendations})


if __name__ == "__main__":
    print(f"Dictionary loaded: {DICTIONARY.word_count} words")
    app.run(debug=True, host="0.0.0.0", port=8080, ssl_context="adhoc")

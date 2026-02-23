"""Claude Vision API for recognizing letter tiles from a photo."""

from __future__ import annotations

import base64
import re
from pathlib import Path

import anthropic


def recognize_letters(image_path: str) -> list[str]:
    """Send an image to Claude Vision and extract letter tiles.

    Returns a list of uppercase single letters.
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    # Read and base64-encode the image
    image_data = base64.standard_b64encode(path.read_bytes()).decode("utf-8")

    # Determine media type
    suffix = path.suffix.lower()
    media_types = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
    media_type = media_types.get(suffix, "image/jpeg")

    client = anthropic.Anthropic()

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            "This image shows Bananagrams letter tiles. "
                            "Identify each individual letter tile visible in the image. "
                            "Return ONLY a comma-separated list of uppercase letters, "
                            "one entry per tile. For example: A, B, C, A, E\n"
                            "Include duplicates — list every tile you see."
                        ),
                    },
                ],
            }
        ],
    )

    # Parse the response
    text = message.content[0].text.strip()
    # Extract letters: split on commas/spaces, keep only single uppercase letters
    raw_parts = re.split(r"[,\s]+", text)
    letters = [p.strip().upper() for p in raw_parts if re.match(r"^[A-Z]$", p.strip().upper())]

    if not letters:
        raise ValueError(f"Could not parse letters from Claude response: {text}")

    return letters


def confirm_letters(letters: list[str]) -> list[str]:
    """Show recognized letters and let user confirm or correct them."""
    print(f"\nRecognized {len(letters)} tiles: {' '.join(letters)}")
    response = input("Correct? (Enter to accept, or type corrected letters): ").strip()

    if not response:
        return letters

    # Parse user correction
    corrected = re.split(r"[,\s]+", response.upper())
    corrected = [ch for ch in corrected if re.match(r"^[A-Z]$", ch)]

    if not corrected:
        print("Could not parse correction, using original.")
        return letters

    print(f"Using {len(corrected)} tiles: {' '.join(corrected)}")
    return corrected

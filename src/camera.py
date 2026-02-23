"""OpenCV camera capture for photographing Bananagrams tiles."""

from __future__ import annotations

import tempfile
from pathlib import Path


def capture_image() -> str:
    """Open camera, show live preview. Press SPACE to capture, Q to quit.

    Returns the path to the captured image file.
    """
    import cv2

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Could not open camera. Check that a camera is connected.")

    print("Camera opened. Press SPACE to capture, Q to quit.")

    captured_path: str | None = None

    while True:
        ret, frame = cap.read()
        if not ret:
            raise RuntimeError("Failed to read from camera.")

        cv2.imshow("Bananagrams - SPACE to capture, Q to quit", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord(" "):
            # Save capture to temp file
            tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
            cv2.imwrite(tmp.name, frame)
            captured_path = tmp.name
            print(f"Image captured: {captured_path}")
            break
        elif key == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()

    if captured_path is None:
        raise RuntimeError("No image captured — user quit.")

    return captured_path

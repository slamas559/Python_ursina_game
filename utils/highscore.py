"""
utils/highscore.py — Thin wrapper around the highscore.txt file.
"""

from constants import HIGHSCORE_FILE


def load_highscore() -> int:
    """Return the stored high score, or 0 if the file is missing/corrupt."""
    try:
        with open(HIGHSCORE_FILE, 'r') as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return 0


def save_highscore(score: int) -> None:
    """Write *score* to disk only if it beats the current record."""
    current = load_highscore()
    if score > current:
        with open(HIGHSCORE_FILE, 'w') as f:
            f.write(str(score))

"""Small shared helpers: thresholds, classification, formatting."""
from __future__ import annotations

import html
from dataclasses import dataclass
from datetime import datetime, timezone

CATEGORIES = ("Low Similarity", "Moderate Similarity", "High Similarity", "Very High Similarity")

CATEGORY_COLORS = {
    "Low Similarity": "#10B981",
    "Moderate Similarity": "#F59E0B",
    "High Similarity": "#F97316",
    "Very High Similarity": "#EF4444",
}


@dataclass(frozen=True)
class Thresholds:
    """Lower bounds of the Moderate, High and Very High categories.

    Ranges are half-open: [0, moderate), [moderate, high), [high, very_high),
    [very_high, 100]. This guarantees there are no gaps and no overlaps, even
    for scores with decimals (e.g. 24.6 is Low, 25.0 is Moderate).
    """

    moderate: float = 25.0
    high: float = 50.0
    very_high: float = 75.0

    def validate(self) -> list[str]:
        if not (0 < self.moderate < self.high < self.very_high <= 100):
            return ["Thresholds must satisfy 0 < moderate < high < very high <= 100."]
        return []

    def ranges(self) -> list[tuple[str, float, float]]:
        bounds = [0.0, self.moderate, self.high, self.very_high, 100.0]
        return [(CATEGORIES[i], bounds[i], bounds[i + 1]) for i in range(4)]


def classify_score(score: float | None, thresholds: Thresholds) -> str | None:
    """Map a 0-100 score to a category label (None stays None)."""
    if score is None:
        return None
    if score >= thresholds.very_high:
        return CATEGORIES[3]
    if score >= thresholds.high:
        return CATEGORIES[2]
    if score >= thresholds.moderate:
        return CATEGORIES[1]
    return CATEGORIES[0]


def is_high_or_above(label: str | None) -> bool:
    return label in (CATEGORIES[2], CATEGORIES[3])


def badge_html(label: str | None) -> str:
    """HTML badge for a classification label (escaped)."""
    if label is None:
        return '<span class="cs-badge" style="--c:#9CA3AF">Not scored</span>'
    color = CATEGORY_COLORS.get(label, "#9CA3AF")
    return f'<span class="cs-badge" style="--c:{color}">{html.escape(label)}</span>'


def format_size(num_bytes: int) -> str:
    if num_bytes < 1024:
        return f"{num_bytes} B"
    if num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    return f"{num_bytes / (1024 * 1024):.2f} MB"


def fmt_score(score: float | None) -> str:
    return "n/a" if score is None else f"{score:.1f}%"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

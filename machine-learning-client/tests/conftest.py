"""Shared fixtures for gaze_math tests."""

from __future__ import annotations

from types import SimpleNamespace
from typing import List


def make_landmark_list() -> List[SimpleNamespace]:
    """Build a 478-long fake landmark list (MediaPipe face mesh size)."""
    pts: List[SimpleNamespace] = [SimpleNamespace(x=0.5, y=0.5) for _ in range(478)]

    def set_idx(idx: int, x: float, y: float) -> None:
        pts[idx] = SimpleNamespace(x=x, y=y)

    set_idx(33, 0.35, 0.52)
    set_idx(263, 0.65, 0.52)
    set_idx(133, 0.44, 0.52)
    set_idx(362, 0.56, 0.52)
    set_idx(159, 0.40, 0.45)
    set_idx(145, 0.40, 0.58)
    set_idx(386, 0.60, 0.45)
    set_idx(374, 0.60, 0.58)
    for i in [468, 469, 470, 471, 472]:
        set_idx(i, 0.42, 0.50)
    for i in [473, 474, 475, 476, 477]:
        set_idx(i, 0.58, 0.50)

    return pts

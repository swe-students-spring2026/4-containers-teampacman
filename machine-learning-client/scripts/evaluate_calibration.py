#!/usr/bin/env python3
"""Offline evaluation of SimpleCalibrator using synthetic feature samples."""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from gaze_math import (  # noqa: E402 pylint: disable=wrong-import-position
    CALIBRATION_MIN_SAMPLES_PER_TARGET,
    CALIBRATION_ORDER,
    FeaturePoint,
    ScreenPoint,
    SimpleCalibrator,
    mean_screen_point_error,
)


def _synthetic_calibration() -> SimpleCalibrator:
    cal = SimpleCalibrator()
    for key in CALIBRATION_ORDER:
        target = cal.targets[key]
        for i in range(CALIBRATION_MIN_SAMPLES_PER_TARGET):
            noise = 0.02 * (i % 3 - 1)
            cal.add_sample(
                key,
                FeaturePoint(
                    float(target.x * 0.6 + noise * 0.05),
                    float(target.y * 0.6 + noise * 0.05),
                ),
            )
    return cal


def main() -> None:
    """Print mean calibration error on synthetic probe points."""
    cal = _synthetic_calibration()
    probes = [
        (FeaturePoint(0.30, 0.28), cal.targets["top_left"]),
        (FeaturePoint(0.70, 0.30), cal.targets["top_right"]),
        (FeaturePoint(0.50, 0.52), cal.targets["center"]),
    ]
    preds: list[ScreenPoint] = []
    truths: list[ScreenPoint] = []
    for feat, truth in probes:
        est = cal.estimate_screen_point(feat)
        if est is None:
            print("estimate returned None (calibration data missing?)")
            sys.exit(1)
        preds.append(est)
        truths.append(truth)
    mae = mean_screen_point_error(preds, truths)
    print(
        "Synthetic calibration probe — mean L2 error (normalized screen units):",
        f"{mae:.4f}",
    )


if __name__ == "__main__":
    main()

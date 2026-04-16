"""Unit tests for gaze_math."""

from __future__ import annotations

from collections import deque
from types import SimpleNamespace

import numpy as np
import pytest

from gaze_math import (
    CALIBRATION_MIN_SAMPLES_PER_TARGET,
    CALIBRATION_ORDER,
    FeaturePoint,
    ScreenPoint,
    SimpleCalibrator,
    clamp01,
    extract_feature_point,
    mean_screen_point_error,
    screen_point_l2_error,
    smooth_gaze_deque,
)
from tests.conftest import make_landmark_list


def test_clamp01_bounds() -> None:
    assert clamp01(-1.0) == 0.0
    assert clamp01(2.0) == 1.0
    assert clamp01(0.35) == 0.35


def test_smooth_gaze_deque_averages() -> None:
    buf: deque[tuple[float, float]] = deque(maxlen=4)
    x, y = smooth_gaze_deque(buf, ScreenPoint(0.0, 1.0))
    assert x == 0.0 and y == 1.0
    x2, y2 = smooth_gaze_deque(buf, ScreenPoint(1.0, 0.0))
    assert abs(x2 - 0.5) < 1e-6 and abs(y2 - 0.5) < 1e-6


def test_screen_metrics() -> None:
    a = ScreenPoint(0.0, 0.0)
    b = ScreenPoint(0.3, 0.4)
    assert abs(screen_point_l2_error(a, b) - 0.5) < 1e-9
    m = mean_screen_point_error(
        [ScreenPoint(0.0, 0.0), ScreenPoint(1.0, 1.0)],
        [ScreenPoint(0.0, 0.0), ScreenPoint(0.0, 0.0)],
    )
    assert abs(m - np.hypot(1.0, 1.0) / 2.0) < 1e-9


def test_mean_screen_point_error_length_mismatch() -> None:
    with pytest.raises(ValueError):
        mean_screen_point_error([ScreenPoint(0, 0)], [])


def test_extract_feature_point_returns_feature() -> None:
    landmarks = make_landmark_list()
    fp = extract_feature_point(landmarks)
    assert fp is not None
    assert isinstance(fp.x_ratio, float)
    assert isinstance(fp.y_ratio, float)


def test_extract_feature_point_none_when_degenerate() -> None:
    landmarks = [SimpleNamespace(x=0.5, y=0.5) for _ in range(478)]
    assert extract_feature_point(landmarks) is None


def test_simple_calibrator_has_enough_data() -> None:
    cal = SimpleCalibrator()
    assert not cal.has_enough_data()
    for key in CALIBRATION_ORDER:
        for _ in range(CALIBRATION_MIN_SAMPLES_PER_TARGET):
            cal.add_sample(
                key, FeaturePoint(0.1 * (hash(key) % 7), 0.1 * (hash(key) % 5))
            )
    assert cal.has_enough_data()


def test_simple_calibrator_estimate_weighted() -> None:
    cal = SimpleCalibrator()
    for key in CALIBRATION_ORDER:
        t = cal.targets[key]
        for _ in range(CALIBRATION_MIN_SAMPLES_PER_TARGET):
            jitter = 0.01 * (hash(key) % 3)
            cal.add_sample(
                key,
                FeaturePoint(
                    float(t.x * 0.5 + jitter * 0.01),
                    float(t.y * 0.5 + jitter * 0.01),
                ),
            )
    est = cal.estimate_screen_point(FeaturePoint(0.25, 0.25))
    assert est is not None
    assert 0.0 <= est.x <= 1.0 and 0.0 <= est.y <= 1.0


def test_simple_calibrator_estimate_empty() -> None:
    cal = SimpleCalibrator()
    assert cal.estimate_screen_point(FeaturePoint(0.0, 0.0)) is None


def test_calibration_order_length() -> None:
    assert len(CALIBRATION_ORDER) == len(SimpleCalibrator().targets)

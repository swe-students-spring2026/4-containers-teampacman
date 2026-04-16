"""Gaze feature extraction and simple 5-point screen calibration."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Deque, Dict, List, Optional, Tuple
import numpy as np

# Minimum samples per calibration target (aligned with web UI and tracker).
CALIBRATION_MIN_SAMPLES_PER_TARGET = 8

CALIBRATION_ORDER: Tuple[str, ...] = (
    "center",
    "top_left",
    "top_right",
    "bottom_left",
    "bottom_right",
)

LEFT_IRIS = [468, 469, 470, 471, 472]
RIGHT_IRIS = [473, 474, 475, 476, 477]
LEFT_EYE_OUTER = 33
LEFT_EYE_INNER = 133
RIGHT_EYE_INNER = 362
RIGHT_EYE_OUTER = 263
LEFT_EYE_TOP = 159
LEFT_EYE_BOTTOM = 145
RIGHT_EYE_TOP = 386
RIGHT_EYE_BOTTOM = 374


@dataclass
class FeaturePoint:
    """Normalized iris-to-eye-corner ratios used as the gaze feature vector."""

    x_ratio: float
    y_ratio: float


@dataclass
class ScreenPoint:
    """Normalized screen coordinates in [0, 1] x [0, 1] space."""

    x: float
    y: float


def clamp01(value: float) -> float:
    """Clamp a float to the closed unit interval [0, 1]."""
    return max(0.0, min(1.0, value))


def smooth_gaze_deque(
    buffer: Deque[Tuple[float, float]], point: ScreenPoint
) -> Tuple[float, float]:
    """Append one screen estimate and return the mean-smoothed (x, y) in [0, 1]."""
    buffer.append((point.x, point.y))
    avg_x = clamp01(float(np.mean([p[0] for p in buffer])))
    avg_y = clamp01(float(np.mean([p[1] for p in buffer])))
    return avg_x, avg_y


def screen_point_l2_error(a: ScreenPoint, b: ScreenPoint) -> float:
    """Euclidean distance between two normalized screen points."""
    return float(np.hypot(a.x - b.x, a.y - b.y))


def mean_screen_point_error(
    predictions: List[ScreenPoint], targets: List[ScreenPoint]
) -> float:
    """Mean L2 error across paired screen points; lists must match in length."""
    if len(predictions) != len(targets) or not predictions:
        raise ValueError("predictions and targets must be non-empty and same length")
    errors = [
        screen_point_l2_error(p, t) for p, t in zip(predictions, targets, strict=True)
    ]
    return float(np.mean(errors))


def _landmark_xy(landmarks, idx: int) -> np.ndarray:
    """Return the (x, y) position of a single landmark as a float32 array."""
    point = landmarks[idx]
    return np.array([point.x, point.y], dtype=np.float32)


def _mean_landmark_xy(landmarks, indices: List[int]) -> np.ndarray:
    """Return the centroid of a group of landmarks as a float32 array."""
    points = np.array([_landmark_xy(landmarks, i) for i in indices], dtype=np.float32)
    return np.mean(points, axis=0)


def _eye_dimensions(landmarks):
    """Return average eye width and height from landmarks."""
    left_outer = _landmark_xy(landmarks, LEFT_EYE_OUTER)
    left_inner = _landmark_xy(landmarks, LEFT_EYE_INNER)
    right_inner = _landmark_xy(landmarks, RIGHT_EYE_INNER)
    right_outer = _landmark_xy(landmarks, RIGHT_EYE_OUTER)
    left_top = _landmark_xy(landmarks, LEFT_EYE_TOP)
    left_bottom = _landmark_xy(landmarks, LEFT_EYE_BOTTOM)
    right_top = _landmark_xy(landmarks, RIGHT_EYE_TOP)
    right_bottom = _landmark_xy(landmarks, RIGHT_EYE_BOTTOM)

    width = (
        np.linalg.norm(left_inner - left_outer)
        + np.linalg.norm(right_outer - right_inner)
    ) / 2.0
    height = (
        np.linalg.norm(left_bottom - left_top)
        + np.linalg.norm(right_bottom - right_top)
    ) / 2.0
    return left_outer, right_outer, width, height


def extract_feature_point(landmarks) -> Optional[FeaturePoint]:
    """Compute a normalized iris-position feature from face landmarks."""
    left_iris = _mean_landmark_xy(landmarks, LEFT_IRIS)
    right_iris = _mean_landmark_xy(landmarks, RIGHT_IRIS)
    left_outer, right_outer, eye_width, eye_height = _eye_dimensions(landmarks)

    if eye_width < 1e-6 or eye_height < 1e-6:
        return None

    iris_center = (left_iris + right_iris) / 2.0
    eye_center = (left_outer + right_outer) / 2.0

    x_ratio = float((iris_center[0] - eye_center[0]) / eye_width)
    y_ratio = float((iris_center[1] - eye_center[1]) / eye_height)

    return FeaturePoint(x_ratio=x_ratio, y_ratio=y_ratio)


class SimpleCalibrator:
    """Calibrates for targets."""

    def __init__(self) -> None:
        """Initialize buckets for the five targets"""
        self.samples: Dict[str, List[FeaturePoint]] = {
            "center": [],
            "top_left": [],
            "top_right": [],
            "bottom_left": [],
            "bottom_right": [],
        }
        self.targets: Dict[str, ScreenPoint] = {
            "center": ScreenPoint(0.50, 0.50),
            "top_left": ScreenPoint(0.08, 0.10),
            "top_right": ScreenPoint(0.92, 0.10),
            "bottom_left": ScreenPoint(0.08, 0.90),
            "bottom_right": ScreenPoint(0.92, 0.90),
        }

    def add_sample(self, key: str, point: FeaturePoint) -> None:
        """Record one gaze feature sample for the named calibration target."""
        self.samples[key].append(point)

    def has_enough_data(
        self, min_per_target: int = CALIBRATION_MIN_SAMPLES_PER_TARGET
    ) -> bool:
        """Return True when every target has at least min_per_target samples."""
        return all(len(v) >= min_per_target for v in self.samples.values())

    def estimate_screen_point(self, feature: FeaturePoint) -> Optional[ScreenPoint]:
        """Estimate screen gaze by inverse-distance weighting over calibration targets."""
        weighted_sum = np.zeros(2, dtype=np.float32)
        total_weight = 0.0

        for key, points in self.samples.items():
            if not points:
                continue
            arr = np.array([[p.x_ratio, p.y_ratio] for p in points], dtype=np.float32)
            centroid = np.mean(arr, axis=0)
            distance = np.linalg.norm(
                np.array([feature.x_ratio, feature.y_ratio]) - centroid
            )
            weight = 1.0 / (max(distance, 1e-4) ** 2)
            target = self.targets[key]
            weighted_sum += weight * np.array([target.x, target.y], dtype=np.float32)
            total_weight += weight

        if total_weight <= 0:
            return None

        result = weighted_sum / total_weight
        result = np.clip(result, 0.0, 1.0)
        return ScreenPoint(x=float(result[0]), y=float(result[1]))

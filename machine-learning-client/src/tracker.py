"""Webcam gaze tracker using MediaPipe Tasks Face Landmarker."""

from __future__ import annotations

import argparse
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
import time
from typing import Deque, Optional, Tuple
from urllib.request import urlopen

import cv2
import mediapipe as mp
import numpy as np
import requests
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.core.base_options import BaseOptions

from gaze_math import FeaturePoint, SimpleCalibrator, extract_feature_point

CALIBRATION_ORDER = ["center", "top_left", "top_right", "bottom_left", "bottom_right"]
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/1/face_landmarker.task"
)


@dataclass
class TrackerState:
    """Mutable runtime state for the gaze tracking loop."""

    calibrator: SimpleCalibrator = field(default_factory=SimpleCalibrator)
    calibration_step: int = 0
    smoothing: Deque[Tuple[float, float]] = field(
        default_factory=lambda: deque(maxlen=5)
    )
    last_send: float = 0.0


def draw_calibration_marker(frame, step_name: str) -> None:
    """Overlay a yellow calibration dot and instruction text onto frame."""
    h, w = frame.shape[:2]
    targets = {
        "center": (int(w * 0.50), int(h * 0.50)),
        "top_left": (int(w * 0.08), int(h * 0.10)),
        "top_right": (int(w * 0.92), int(h * 0.10)),
        "bottom_left": (int(w * 0.08), int(h * 0.90)),
        "bottom_right": (int(w * 0.92), int(h * 0.90)),
    }
    x, y = targets[step_name]
    cv2.circle(frame, (x, y), 18, (0, 255, 255), -1)
    cv2.putText(
        frame,
        f"Look at the yellow dot: {step_name}. Press SPACE to sample.",
        (18, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )


def clamp01(value: float) -> float:
    """Clamp a float value to the range [0, 1]."""
    return max(0.0, min(1.0, value))


def post_gaze(endpoint: str, point: Tuple[float, float]) -> None:
    """POST a normalized gaze point to the web-app API endpoint."""
    try:
        requests.post(
            endpoint,
            json={"x": point[0], "y": point[1], "ts": time.time()},
            timeout=0.15,
        )
    except requests.RequestException:
        pass


def ensure_face_landmarker_model(path: Path) -> Path:
    """Download face_landmarker.task model if not already present locally."""
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(MODEL_URL, timeout=20) as response:
        path.write_bytes(response.read())
    return path


def create_face_landmarker(model_path: Path):
    """Build and return a MediaPipe Tasks FaceLandmarker for still images."""
    options = vision.FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(model_path)),
        running_mode=vision.RunningMode.IMAGE,
        num_faces=1,
    )
    return vision.FaceLandmarker.create_from_options(options)


def _draw_calibration_ui(frame, calibration_step: int) -> None:
    """Draw calibration dot and quit hint onto the frame."""
    step_name = CALIBRATION_ORDER[calibration_step]
    draw_calibration_marker(frame, step_name)
    cv2.putText(
        frame,
        "Press Q to quit",
        (18, frame.shape[0] - 20),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (220, 220, 220),
        1,
        cv2.LINE_AA,
    )


def _smooth_gaze(smoothing: Deque, estimated) -> Tuple[float, float]:
    """Append estimate to smoothing buffer and return clamped average."""
    smoothing.append((estimated.x, estimated.y))
    avg_x = clamp01(float(np.mean([p[0] for p in smoothing])))
    avg_y = clamp01(float(np.mean([p[1] for p in smoothing])))
    return avg_x, avg_y


def _send_gaze(
    feature: FeaturePoint,
    calibrator: SimpleCalibrator,
    smoothing: Deque,
    last_send: float,
    args,
) -> Tuple[float, float, float]:
    """Estimate, smooth, and POST gaze; return (avg_x, avg_y, last_send)."""
    estimated = calibrator.estimate_screen_point(feature)
    if estimated is None:
        return 0.0, 0.0, last_send
    avg_x, avg_y = _smooth_gaze(smoothing, estimated)
    now = time.time()
    if now - last_send >= args.send_interval:
        post_gaze(args.api_url, (avg_x, avg_y))
        last_send = now
    return avg_x, avg_y, last_send


def _update_calibration(
    calibration_step: int,
    feature: Optional[FeaturePoint],
    key: int,
    calibrator: SimpleCalibrator,
) -> int:
    """Record a calibration sample on SPACE and advance step when enough collected."""
    if key == 32 and feature is not None:
        target = CALIBRATION_ORDER[calibration_step]
        calibrator.add_sample(target, feature)
        if len(calibrator.samples[target]) >= 8:
            return calibration_step + 1
    return calibration_step


def _build_args():
    """Parse and return command-line arguments."""
    default_model = str(
        Path(__file__).resolve().parents[1] / "models" / "face_landmarker.task"
    )
    parser = argparse.ArgumentParser(description="EyeWrite ML client")
    args_config = [
        ("--camera", int, 0),
        ("--send-interval", float, 0.07),
        ("--smooth-window", int, 5),
    ]
    for flag, arg_type, default in args_config:
        parser.add_argument(flag, type=arg_type, default=default)
    parser.add_argument("--api-url", default="http://127.0.0.1:5000/api/gaze")
    parser.add_argument("--model-path", default=default_model)
    return parser.parse_args()


def _run_loop(cap, face_landmarker, state: TrackerState, args) -> None:
    """Main capture-and-process loop."""
    while True:
        ok, frame = cap.read()
        if not ok:
            break

        frame = cv2.flip(frame, 1)
        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB),
        )
        result = face_landmarker.detect(mp_image)

        feature: Optional[FeaturePoint] = None
        if result.face_landmarks:
            feature = extract_feature_point(result.face_landmarks[0])

        if state.calibration_step < len(CALIBRATION_ORDER):
            _draw_calibration_ui(frame, state.calibration_step)
        else:
            cv2.putText(
                frame,
                "Calibration complete. Sending gaze data...",
                (18, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (70, 255, 70),
                2,
                cv2.LINE_AA,
            )
            if feature is not None:
                avg_x, avg_y, state.last_send = _send_gaze(
                    feature, state.calibrator, state.smoothing, state.last_send, args
                )
                h, w = frame.shape[:2]
                cv2.circle(frame, (int(avg_x * w), int(avg_y * h)), 10, (0, 220, 0), -1)

        cv2.imshow("EyeWrite Tracker", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        if state.calibration_step < len(CALIBRATION_ORDER):
            state.calibration_step = _update_calibration(
                state.calibration_step, feature, key, state.calibrator
            )


def main() -> None:
    """Entry point: run the webcam gaze tracking and calibration loop."""
    args = _build_args()

    if not hasattr(mp, "tasks"):
        raise RuntimeError("Installed mediapipe does not expose the Tasks API.")

    try:
        model_path = ensure_face_landmarker_model(Path(args.model_path))
    except Exception as exc:
        raise RuntimeError("Unable to prepare face_landmarker.task model.") from exc

    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        raise RuntimeError("Cannot open webcam")

    state = TrackerState(smoothing=deque(maxlen=max(1, args.smooth_window)))

    with create_face_landmarker(model_path) as face_landmarker:
        _run_loop(cap, face_landmarker, state, args)

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()

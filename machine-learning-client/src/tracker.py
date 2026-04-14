"""Webcam gaze tracker using MediaPipe Tasks Face Landmarker."""

from __future__ import annotations

import argparse
from collections import deque
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


def main() -> None:
    """Entry point: run the webcam gaze tracking and calibration loop."""
    parser = argparse.ArgumentParser(description="EyeWrite ML client")
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--api-url", default="http://127.0.0.1:5000/api/gaze")
    parser.add_argument("--send-interval", type=float, default=0.07)
    parser.add_argument("--smooth-window", type=int, default=5)
    parser.add_argument(
        "--model-path",
        default=str(Path(__file__).resolve().parents[1] / "models" / "face_landmarker.task"),
    )
    args = parser.parse_args()

    if not hasattr(mp, "tasks"):
        raise RuntimeError(
            "Installed mediapipe package does not expose the Tasks API. "
            "Run: python -m pipenv install"
        )

    try:
        model_path = ensure_face_landmarker_model(Path(args.model_path))
    except Exception as exc:
        raise RuntimeError(
            "Unable to prepare face_landmarker.task model. "
            "Check internet access or pass --model-path to a local model file."
        ) from exc

    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        raise RuntimeError("Cannot open webcam")

    calibrator = SimpleCalibrator()
    calibration_step = 0
    smoothing: Deque[Tuple[float, float]] = deque(maxlen=max(1, args.smooth_window))
    last_send = 0.0

    with create_face_landmarker(model_path) as face_landmarker:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = face_landmarker.detect(mp_image)

            feature: Optional[FeaturePoint] = None
            if result.face_landmarks:
                landmarks = result.face_landmarks[0]
                feature = extract_feature_point(landmarks)

            if calibration_step < len(CALIBRATION_ORDER):
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
                    estimated = calibrator.estimate_screen_point(feature)
                    if estimated is not None:
                        smoothing.append((estimated.x, estimated.y))
                        avg_x = float(np.mean([p[0] for p in smoothing]))
                        avg_y = float(np.mean([p[1] for p in smoothing]))
                        avg_x, avg_y = clamp01(avg_x), clamp01(avg_y)

                        now = time.time()
                        if now - last_send >= args.send_interval:
                            post_gaze(args.api_url, (avg_x, avg_y))
                            last_send = now

                        h, w = frame.shape[:2]
                        px, py = int(avg_x * w), int(avg_y * h)
                        cv2.circle(frame, (px, py), 10, (0, 220, 0), -1)

            cv2.imshow("EyeWrite Tracker", frame)
            key = cv2.waitKey(1) & 0xFF

            if key == ord("q"):
                break

            if key == 32 and calibration_step < len(CALIBRATION_ORDER):
                if feature is not None:
                    target = CALIBRATION_ORDER[calibration_step]
                    calibrator.add_sample(target, feature)
                    if len(calibrator.samples[target]) >= 8:
                        calibration_step += 1

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()

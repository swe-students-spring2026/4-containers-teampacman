"""Webcam gaze tracker using MediaPipe Tasks Face Landmarker."""

from __future__ import annotations

import base64
import os
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Deque, Optional, Tuple
from urllib.request import urlopen

import cv2
import mediapipe as mp
import numpy as np
from flask import Flask, request, jsonify
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.core.base_options import BaseOptions
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from gaze_math import (
    ScreenPoint,
    SimpleCalibrator,
    extract_feature_point,
    smooth_gaze_deque,
)

MODEL_PATH = Path(__file__).resolve().parents[1] / "models" / "face_landmarker.task"


MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/1/face_landmarker.task"
)

app = Flask(__name__)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017/")
gaze_collection: Optional[Any] = None
try:
    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client["eyewrite_db"]
    gaze_collection = db["gaze_data"]
except PyMongoError as e:
    print(f"error connecting to the database: {e}")


@dataclass
class TrackerState:
    """Mutable runtime state for the gaze tracking loop."""

    calibrator: SimpleCalibrator = field(default_factory=SimpleCalibrator)
    calibration_step: int = 0
    smoothing: Deque[Tuple[float, float]] = field(
        default_factory=lambda: deque(maxlen=5)
    )
    last_send: float = 0.0


state = TrackerState()
face_landmarker = None


def ensure_face_landmarker_model(path: Path) -> Path:
    """Download face_landmarker.task model if not already present locally."""
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(MODEL_URL, timeout=20) as response:
        path.write_bytes(response.read())
    return path


def create_face_landmarker(path: Path):
    """Build and return a MediaPipe Tasks FaceLandmarker for still images."""
    options = vision.FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(path)),
        running_mode=vision.RunningMode.IMAGE,
        num_faces=1,
    )
    return vision.FaceLandmarker.create_from_options(options)


def decode_image(img_string: str) -> Optional[np.ndarray]:
    """Decodes base64 image into an OpenCV BGR image (or None if bytes are invalid)."""
    img_data = base64.b64decode(img_string)
    nparr = np.frombuffer(img_data, np.uint8)
    return cv2.imdecode(nparr, cv2.IMREAD_COLOR)


def _smooth_gaze(smoothing: Deque, estimated: ScreenPoint) -> Tuple[float, float]:
    """Append estimate to smoothing buffer and return clamped average."""
    return smooth_gaze_deque(smoothing, estimated)


@app.route("/process", methods=["POST"])
def process():  # pylint: disable=too-many-return-statements
    """Process a single frame and return the estimated gaze point."""
    data = request.json
    if not data or "image" not in data:
        return jsonify({"error": "no image"}), 400

    try:
        frame = decode_image(data["image"])
        if frame is None:
            return jsonify({"error": "invalid image"}), 400
        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB),
        )
        result = face_landmarker.detect(mp_image)

        if not result.face_landmarks:
            return jsonify({"error": "no face landmarks"}), 400

        feature = extract_feature_point(result.face_landmarks[0])

        if not feature:
            return jsonify({"error": "no feature"}), 400

        estimated = state.calibrator.estimate_screen_point(feature)

        if estimated:
            avg_x, avg_y = _smooth_gaze(state.smoothing, estimated)

            if gaze_collection is not None:
                try:
                    gaze_collection.insert_one(
                        {"x": avg_x, "y": avg_y, "timestamp": time.time()}
                    )
                except PyMongoError as db_err:
                    print(f"error connecting to the database: {db_err}")

            return jsonify({"x": avg_x, "y": avg_y}), 200

        return jsonify({"x": 0.5, "y": 0.5, "status": "waiting_for_calibration"})

    except (ValueError, TypeError) as err:
        return jsonify({"error": str(err)}), 500


@app.route("/calibrate", methods=["POST"])
def calibrate():
    """Endpoint to add a new calibration sample for a specific target"""
    data = request.json
    if not data or "image" not in data or "target" not in data:
        return jsonify({"error": "invalid data"}), 400
    try:
        frame = decode_image(data["image"])
        if frame is None:
            return jsonify({"error": "invalid image"}), 400
        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB),
        )
        result = face_landmarker.detect(mp_image)

        if not result.face_landmarks:
            return jsonify({"error": "no face detected for calibration"}), 400

        feature = extract_feature_point(result.face_landmarks[0])

        if not feature:
            return jsonify({"error": "no feature"}), 400

        state.calibrator.add_sample(data["target"], feature)

        state.smoothing.clear()

        sample_count = len(state.calibrator.samples[data["target"]])
        return jsonify(
            {
                "status": "success",
                "target": data["target"],
                "sample_count": sample_count,
            }
        )

    except (ValueError, TypeError) as err:
        return jsonify({"error": str(err)}), 500


if __name__ == "__main__":
    model_path = ensure_face_landmarker_model(MODEL_PATH)
    face_landmarker = create_face_landmarker(model_path)

    print("Ml client starting")
    app.run(host="0.0.0.0", port=5002)

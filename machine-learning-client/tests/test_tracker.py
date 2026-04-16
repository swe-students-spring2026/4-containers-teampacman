"""Tests for tracker Flask app and helpers."""

from __future__ import annotations

import base64
from collections import deque
from pathlib import Path
from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import tracker
from gaze_math import (
    CALIBRATION_MIN_SAMPLES_PER_TARGET,
    CALIBRATION_ORDER,
    FeaturePoint,
    ScreenPoint,
)


def _cv2_encode_jpeg(arr: np.ndarray) -> tuple[bool, bytes]:
    ok, buf = cv2.imencode(".jpg", arr)
    return bool(ok), buf.tobytes()


def test_smooth_gaze_delegates() -> None:
    buf: deque[tuple[float, float]] = deque(maxlen=3)
    x, y = tracker._smooth_gaze(buf, ScreenPoint(0.4, 0.6))
    assert abs(x - 0.4) < 1e-9 and abs(y - 0.6) < 1e-9


def test_ensure_face_landmarker_uses_existing(tmp_path: Path) -> None:
    path = tmp_path / "face_landmarker.task"
    path.write_bytes(b"ok")
    assert tracker.ensure_face_landmarker_model(path) == path


def test_ensure_face_landmarker_downloads(tmp_path: Path) -> None:
    path = tmp_path / "models" / "face_landmarker.task"

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

        def read(self):
            return b"model-bytes"

    with patch("tracker.urlopen", return_value=_Resp()):
        out = tracker.ensure_face_landmarker_model(path)
    assert out == path
    assert path.read_bytes() == b"model-bytes"


def test_decode_image_roundtrip() -> None:
    arr = np.zeros((4, 4, 3), dtype=np.uint8)
    arr[1, 1] = [10, 20, 30]
    ok, buf = _cv2_encode_jpeg(arr)
    assert ok
    b64 = base64.b64encode(buf).decode("ascii")
    out = tracker.decode_image(b64)
    assert out is not None
    assert out.shape[2] == 3


def test_process_requires_image() -> None:
    tracker.app.config["TESTING"] = True
    client = tracker.app.test_client()
    resp = client.post("/process", json={})
    assert resp.status_code == 400


def test_process_invalid_image_returns_400(monkeypatch) -> None:
    tracker.app.config["TESTING"] = True
    monkeypatch.setattr(tracker, "decode_image", lambda _s: None)
    client = tracker.app.test_client()
    resp = client.post("/process", json={"image": "abc"})
    assert resp.status_code == 400


def test_calibrate_requires_fields() -> None:
    tracker.app.config["TESTING"] = True
    client = tracker.app.test_client()
    assert client.post("/calibrate", json={}).status_code == 400


def test_process_returns_waiting_when_not_calibrated(monkeypatch) -> None:
    tracker.app.config["TESTING"] = True
    monkeypatch.setattr(tracker, "state", tracker.TrackerState())
    arr = np.zeros((8, 8, 3), dtype=np.uint8)
    ok, buf = _cv2_encode_jpeg(arr)
    assert ok
    b64 = base64.b64encode(buf).decode("ascii")

    mock_lm = MagicMock()
    lm_result = MagicMock()
    lm_result.face_landmarks = [object()]
    mock_lm.detect.return_value = lm_result
    monkeypatch.setattr(tracker, "face_landmarker", mock_lm)
    monkeypatch.setattr(
        tracker,
        "extract_feature_point",
        lambda _lm: FeaturePoint(0.1, 0.1),
    )
    monkeypatch.setattr(
        tracker,
        "decode_image",
        lambda _s: np.zeros((8, 8, 3), dtype=np.uint8),
    )

    client = tracker.app.test_client()
    resp = client.post("/process", json={"image": b64})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("status") == "waiting_for_calibration"


def test_process_returns_xy_when_calibrated(monkeypatch) -> None:
    tracker.app.config["TESTING"] = True
    st = tracker.TrackerState()
    for key in CALIBRATION_ORDER:
        for _ in range(CALIBRATION_MIN_SAMPLES_PER_TARGET):
            st.calibrator.add_sample(key, FeaturePoint(0.2, 0.2))
    monkeypatch.setattr(tracker, "state", st)
    monkeypatch.setattr(tracker, "gaze_collection", None)

    mock_lm = MagicMock()
    lm_result = MagicMock()
    lm_result.face_landmarks = [object()]
    mock_lm.detect.return_value = lm_result
    monkeypatch.setattr(tracker, "face_landmarker", mock_lm)
    monkeypatch.setattr(
        tracker,
        "extract_feature_point",
        lambda _lm: FeaturePoint(0.2, 0.2),
    )
    monkeypatch.setattr(
        tracker,
        "decode_image",
        lambda _s: np.zeros((8, 8, 3), dtype=np.uint8),
    )

    client = tracker.app.test_client()
    resp = client.post("/process", json={"image": "e30="})
    assert resp.status_code == 200
    data = resp.get_json()
    assert "x" in data and "y" in data


def test_calibrate_success(monkeypatch) -> None:
    tracker.app.config["TESTING"] = True
    monkeypatch.setattr(tracker, "state", tracker.TrackerState())

    mock_lm = MagicMock()
    lm_result = MagicMock()
    lm_result.face_landmarks = [object()]
    mock_lm.detect.return_value = lm_result
    monkeypatch.setattr(tracker, "face_landmarker", mock_lm)
    monkeypatch.setattr(
        tracker,
        "extract_feature_point",
        lambda _lm: FeaturePoint(0.1, 0.2),
    )
    monkeypatch.setattr(
        tracker,
        "decode_image",
        lambda _s: np.zeros((8, 8, 3), dtype=np.uint8),
    )

    client = tracker.app.test_client()
    resp = client.post(
        "/calibrate",
        json={"image": "e30=", "target": "center"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "success"

"""Unit tests for web-app Flask routes."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import requests
from pymongo.errors import PyMongoError

import app as app_module


def test_index_returns_ok(client):
    """Home page renders."""
    response = client.get("/")
    assert response.status_code == 200


def test_process_frame_missing_image_returns_400(client):
    """POST without image yields 400."""
    response = client.post("/api/process_frame", json={})
    assert response.status_code == 400
    assert response.get_json()["error"] == "No frame"


@patch("app.requests.post")
def test_process_frame_ml_success_updates_gaze(mock_post, client):
    """Successful ML response returns coordinates and updates gaze cache."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"x": 0.2, "y": 0.8}
    mock_post.return_value = mock_resp

    response = client.post("/api/process_frame", json={"image": "dGVzdA=="})
    assert response.status_code == 200
    data = response.get_json()
    assert data["x"] == 0.2
    assert data["y"] == 0.8

    snap = app_module.get_gaze_snapshot_for_tests()
    assert snap["x"] == 0.2
    assert snap["y"] == 0.8


@patch("app.requests.post")
def test_process_frame_ml_error_status_passthrough(mock_post, client):
    """Non-200 ML response body and status are forwarded."""
    mock_resp = MagicMock()
    mock_resp.status_code = 503
    mock_resp.json.return_value = {"error": "busy"}
    mock_post.return_value = mock_resp

    response = client.post("/api/process_frame", json={"image": "dGVzdA=="})
    assert response.status_code == 503
    assert response.get_json() == {"error": "busy"}


@patch("app.requests.post")
def test_process_frame_request_exception_returns_500(mock_post, client):
    """Connection failure to ML service yields 500."""
    mock_post.side_effect = requests.exceptions.ConnectionError("refused")

    response = client.post("/api/process_frame", json={"image": "dGVzdA=="})
    assert response.status_code == 500
    assert response.get_json()["error"] == "Frame processing failed"


def test_calibrate_empty_payload_returns_400(client):
    """Calibration without JSON body returns 400."""
    response = client.post("/api/calibrate", json={})
    assert response.status_code == 400
    assert response.get_json()["error"] == "No payload"


@patch("app.requests.post")
def test_calibrate_success(mock_post, client):
    """Calibration proxies ML response."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"ok": True}
    mock_post.return_value = mock_resp

    response = client.post("/api/calibrate", json={"image": "x", "target": 1})
    assert response.status_code == 200
    assert response.get_json() == {"ok": True}
    mock_post.assert_called_once()
    assert "/calibrate" in mock_post.call_args[0][0]


@patch("app.requests.post")
def test_calibrate_request_exception_returns_500(mock_post, client):
    """ML unavailable during calibration returns 500."""
    mock_post.side_effect = requests.exceptions.Timeout("slow")

    response = client.post("/api/calibrate", json={"image": "x", "target": 0})
    assert response.status_code == 500
    assert response.get_json()["error"] == "ML Service unavailable"


def test_dashboard_renders_ok(client):
    """Dashboard page loads when no DB connection exists."""
    with patch("app.gaze_collection", None):
        response = client.get("/dashboard")
    assert response.status_code == 200
    assert b"Gaze Data Dashboard" in response.data


def test_dashboard_renders_with_gaze_data(client):
    """Dashboard renders data rows when MongoDB returns gaze points."""
    fake_points = [
        {"x": 0.1, "y": 0.2, "timestamp": 1700000000.0},
        {"x": 0.5, "y": 0.5, "timestamp": 1700000060.0},
    ]
    mock_collection = MagicMock()
    mock_collection.find.return_value.sort.return_value.limit.return_value = fake_points

    with patch("app.gaze_collection", mock_collection):
        response = client.get("/dashboard")

    assert response.status_code == 200
    assert b"0.1" in response.data
    assert b"0.5" in response.data


def test_dashboard_handles_db_error(client):
    """Dashboard returns 200 with empty table when MongoDB raises an error."""

    mock_collection = MagicMock()
    mock_collection.find.side_effect = PyMongoError("connection refused")

    with patch("app.gaze_collection", mock_collection):
        response = client.get("/dashboard")

    assert response.status_code == 200
    assert b"No data recorded yet" in response.data

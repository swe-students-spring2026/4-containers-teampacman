"""The Flask Web Application that displays the keyboard for our app"""

from __future__ import annotations
import os
import threading
import time
from flask import Flask, jsonify, render_template, request
import requests

app = Flask(__name__)

ML_CLIENT_URL = os.getenv("ML_CLIENT_URL", "http://ml-client:5002/process")

_gaze_lock = threading.Lock()
_latest_gaze = {"x": 0.5, "y": 0.5, "ts": 0.0}


@app.route("/")
def index():
    """Displays the page"""
    return render_template("index.html")


@app.route("/api/process_frame", methods=["POST"])
def process_frame():
    """
    Receives a base64 image frame, sends it to the ML-Client and updates
    the latest gaze position.
    """
    payload = request.get_json(silent=True) or {}
    frame = payload.get("image")

    if not frame:
        return jsonify({"error": "No frame"}), 400
    try:
        ml_response = requests.post(ML_CLIENT_URL, json={"image": frame}, timeout=1.5)

        if ml_response.status_code == 200:
            data = ml_response.json()
            x = float(data.get("x", 0.5))
            y = float(data.get("y", 0.5))
            ts = time.time()

            with _gaze_lock:
                _latest_gaze["x"] = x
                _latest_gaze["y"] = y
                _latest_gaze["ts"] = ts

            return jsonify({"x": x, "y": y})

        return jsonify(ml_response.json()), ml_response.status_code
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to the ml-client: {e}")

    return jsonify({"error": "Frame processing failed"}), 500


@app.route("/api/calibrate", methods=["POST"])
def calibrate_frame():
    """
    Sends the calibration request (img and target label) to the ML-Client
    """
    payload = request.get_json(silent=True) or {}
    if not payload:
        return jsonify({"error": "No payload"}), 400
    try:
        calib_url = ML_CLIENT_URL.replace("/process", "/calibrate")
        ml_response = requests.post(calib_url, json=payload, timeout=2)
        return jsonify(ml_response.json()), ml_response.status_code

    except requests.exceptions.RequestException as e:

        print(f"Error connecting to ml client calibration: {e}")
        return jsonify({"error": "ML Service unavailable"}), 500


if __name__ == "__main__":
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host=host, port=port, debug=debug)

"""The Flask Web Application that displays the keyboard for our app"""

from __future__ import annotations
import os
import threading
import time
from typing import Dict
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

_gaze_lock = threading.Lock()
_latest_gaze: Dict[str, float] = {"x": 0.5, "y": 0.5, "ts": 0.0}


@app.route("/")
def index():
    """Displays the page"""
    return render_template("index.html")


@app.route("/api/gaze", methods=["POST"])
def update_gaze():
    """Retrieves new coordinates and stores them"""
    payload = request.get_json(silent=True) or {}
    x = float(payload.get("x", 0.5))
    y = float(payload.get("y", 0.5))
    ts = float(payload.get("ts", time.time()))

    with _gaze_lock:
        _latest_gaze["x"] = max(0.0, min(1.0, x))
        _latest_gaze["y"] = max(0.0, min(1.0, y))
        _latest_gaze["ts"] = ts

    return jsonify({"ok": True})


@app.route("/api/gaze", methods=["GET"])
def get_gaze():
    """Sends the latest coordinates to the frontend"""
    with _gaze_lock:
        return jsonify(dict(_latest_gaze))


@app.route("/api/health")
def health():
    """Check for the endpoint's status"""
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    host = os.getenv("FLASK_HOST", "127.0.0.1")
    port = int(os.getenv("FLASK_PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host=host, port=port, debug=debug)

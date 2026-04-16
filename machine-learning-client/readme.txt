Machine learning client (Flask API on port 5002): gaze from frames + calibration.

Accuracy / calibration:
- src/gaze_math.py — features, 5-point calibration, inverse-square weights, smoothing helpers, L2 metrics.
- scripts/evaluate_calibration.py — offline synthetic mean L2 error (no camera).

Tests:
  cd machine-learning-client && pipenv sync --dev && pipenv run pytest

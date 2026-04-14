![Lint-free](https://github.com/nyu-software-engineering/containerized-app-exercise/actions/workflows/lint.yml/badge.svg)

# EyeWrite MVP (Containerized App Exercise)

This repository now contains an EyeWrite MVP split into two services:

- `machine-learning-client/`: webcam + eye tracking + calibration + gaze sending
- `web-app/`: Flask UI + large keyboard + dwell typing + message + speech

## Current Structure

- `machine-learning-client/src/tracker.py`: OpenCV + MediaPipe tracking loop
- `machine-learning-client/src/gaze_math.py`: gaze feature extraction and simple calibration mapping
- `web-app/app.py`: Flask API and page server
- `web-app/templates/index.html`: typing UI
- `web-app/static/js/app.js`: gaze cursor + dwell logic + text entry + speech
- `web-app/static/css/styles.css`: responsive interface styling

## Quick Start

Start the web app first:

```bash
cd web-app
pipenv install
pipenv run python app.py
```

Then start the ML client in another terminal:

```bash
cd machine-learning-client
pipenv install
pipenv run python src/tracker.py --api-url http://127.0.0.1:5000/api/gaze
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000).

## MVP Coverage

- Webcam feed
- Eye landmark + iris tracking
- Simple calibration
- Large keyboard with dwell typing
- Typed text box
- Space / Backspace / Clear
- Speak button
- Quick phrases (nice-to-have starter)

## Next Iterations

- MongoDB persistence for messages, calibration profiles, and phrase sets
- Blink-to-select confirmation
- Word prediction/autocomplete
- Full-screen mode and theme toggles
- More robust calibration and adaptive drift correction

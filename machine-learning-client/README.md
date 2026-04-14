## EyeWrite ML Client

This service reads webcam frames, detects eye/iris landmarks with MediaPipe, runs a simple 5-point calibration, estimates screen gaze coordinates, and sends them to the Flask web app.

## Team Members
Angelina Wu [https://github.com/TangelinaWu]
Team Member 2
Team Member 3
Team Member 4
Team Member 5



## Features in MVP

- Webcam feed and live face/iris processing
- Eye landmark-based gaze feature extraction
- Simple 5-point calibration (`center`, corners)
- Smoothed gaze estimate output
- HTTP push to web app `/api/gaze`

## Run

1. Install dependencies:

```bash
pipenv install
```

2. Start tracker:

```bash
pipenv run python src/tracker.py --api-url http://127.0.0.1:5000/api/gaze
```

3. Calibration flow:
- Look at highlighted dot
- Press `SPACE` repeatedly until it advances
- Repeat for all 5 points
- Press `Q` to quit

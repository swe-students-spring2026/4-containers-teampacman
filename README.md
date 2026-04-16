[![Lint-free](https://github.com/swe-students-spring2026/4-containers-teampacman/actions/workflows/lint.yml/badge.svg)](https://github.com/swe-students-spring2026/4-containers-teampacman/actions/workflows/lint.yml)
[![Machine learning client tests](https://github.com/swe-students-spring2026/4-containers-teampacman/actions/workflows/machine-learning-client.yml/badge.svg)](https://github.com/swe-students-spring2026/4-containers-teampacman/actions/workflows/machine-learning-client.yml)

# EyeWrite MVP (Containerized App Exercise)

This repository contains an EyeWrite MVP split into two services plus MongoDB (via Docker):

- `machine-learning-client/`: MediaPipe gaze tracking, calibration math (`gaze_math`), REST `/process` and `/calibrate`, optional writes to MongoDB
- `web-app/`: Flask UI, webcam, five-point calibration, gaze cursor, dwell typing, quick phrases

All three parts are wired in `docker-compose.yml` (MongoDB, `web-app` on host port **5001**, `ml-client` on **5002**).

##  Structure

- `machine-learning-client/src/tracker.py`: Flask service for frame processing and Mongo inserts
- `machine-learning-client/src/gaze_math.py`: landmarks → screen mapping, smoothing, calibration helpers
- `web-app/app.py`: Flask routes (`/`, `/api/process_frame`, `/api/calibrate`, etc.)
- `web-app/templates/index.html`: typing UI
- `web-app/static/js/app.js`: camera, calibration, gaze loop, dwell, phrases
- `web-app/static/css/styles.css`: layout and keyboard styling
- `docker-compose.yml`: MongoDB + web-app + ml-client

## Team

- [Angelina Wu](https://github.com/TangelinaWu)
- [Adam Shin](https://github.com/aus2005)
- [Han Xiao](https://github.com/vick12333)
- Alejandro
- Wonden

##  How to run

### Docker Compose (recommended)

```bash
docker-compose up --build
```

Open the UI at [http://127.0.0.1:5001](http://127.0.0.1:5001). MongoDB is exposed on the host at `127.0.0.1:27017`. No seed data is required for a basic run.

### Local (no Docker)

MongoDB must be running if you want the ML client to persist gaze samples.

Start the **web app** first (listens on **5000** by default):

```bash
cd web-app
pipenv install
export ML_CLIENT_URL=http://127.0.0.1:5002/process
export FLASK_HOST=127.0.0.1
pipenv run python app.py
```

Then start the **machine learning client** in another terminal (listens on **5002**):

```bash
cd machine-learning-client
pipenv install
export MONGO_URI=mongodb://127.0.0.1:27017/
pipenv run python src/tracker.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000).

**Environment variables (reference)**

| Variable     | Used by              | Typical value (Compose)        |
|-------------|----------------------|---------------------------------|
| `ML_CLIENT_URL` | web-app          | `http://ml-client:5002/process` |
| `MONGO_URI`     | machine-learning-client | `mongodb://mongodb:27017/` |
| `FLASK_HOST`    | web-app          | `0.0.0.0` in containers       |

## MVP Coverage

- Webcam feed and frame streaming to the ML service
- Eye / iris landmarks and gaze estimation
- Five-point calibration and gaze-to-screen mapping
- Large on-screen keyboard with dwell typing (~0.9s)
- Text entry, space / backspace / clear, quick phrases
- Optional persistence of gaze metadata in MongoDB (`eyewrite_db.gaze_data`)

**ML client tests**

```bash
cd machine-learning-client
pipenv sync --dev && pipenv run pytest
```

Synthetic calibration check (no camera): `pipenv run python scripts/evaluate_calibration.py`

Standup reports (full reports are posted to the team channel; below matches that layout):

# Standup Report - 15 April 2026

## Adam Shin @aus2005
- **did**: Web app and API integration; README and run instructions.
- **doing**: Polish Flask UI and env defaults for local vs Docker.
- **blockers**: None.

## Angelina Wu @TangelinaWu
- **did**: EyeWrite scope, reviews, ML + web coordination. 
- **doing**: Refine ML client and web app behavior.
- **blockers**: None.

## Han Xiao @vick12333
- **did**: ML accuracy experiments, `gaze_math` and tracker work Add web-app pytest.
- **doing**: Continue calibration / smoothing improvements.
- **blockers**: None.

## Alejandro
- **did**: Docker Compose, MongoDB wiring, container builds.
- **doing**: Container hardening and docs alignment.
- **blockers**: Waiting on any remaining lint or CI fixes from teammates.

## Wonden
- **did**: Web app UI work.
- **doing**: Refine typing and dwell UX.
- **blockers**: None.

# Standup Report - 15 April 2026 Evening Meeting

## Adam Shin @aus2005
- **did**: Polished UI and env.
- **doing**: Handle Linting Errors and github reversion issues.
- **blockers**: None.

## Angelina Wu @TangelinaWu
- **did**: Refined web app behavior.
- **doing**: Refine task boards.
- **blockers**: None.

## Han Xiao @vick12333
- **did**: Continued calibration / smoothing
- **doing**: Still working on calibration / smoothing improvements.
- **blockers**: None.

## Alejandro
- **did**: Worked more on the Container
- **doing**: Docs Alignment
- **blockers**: None.

## Wonden
- **did**: Refined Typing
- **doing**: Continue to work on UX. 
- **blockers**: None.

# Standup Report - 16 April 2026

## Adam Shin @aus2005
- **did**: Handled Linting Errors and github.
- **doing**: Updating ReadMe.
- **blockers**: None.

## Angelina Wu @TangelinaWu
- **did**: Finalized Task Boards.
- **doing**: Review Code.
- **blockers**: None.

## Han Xiao @vick12333
- **did**: Finished Calibration and smoothing improvements
- **doing**: Final code review.
- **blockers**: None.

## Alejandro
- **did**: Finished container and Docs Alignment.
- **doing**: Working through app to find bugs. 
- **blockers**: None.

## Wonden
- **did**: Refined UX.
- **doing**: Final checkover of project.
- **blockers**: None.

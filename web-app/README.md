# EyeWrite Web App

Flask web app for EyeWrite MVP.

## Features in MVP

- Receives normalized gaze coordinates from ML client
- Big on-screen option buttons for gaze comunication
- Dwell typing (~900ms)
- Typed message box
- Small Camera Preview
- Calibration and Re-Calibration button

## How to run:
To run the full application (including the database and ML Client), follow the instructions in the Root Directory [README](../README.md).

#### If you only want to run this Flask service:

1. Move into the service folder:

```bash
cd web-app
```

2. Install dependencies:

```bash
pipenv install
```

3. Start Flask app:

```bash
export ML_CLIENT_URL="[http://127.0.0.1:5002/process](http://127.0.0.1:5002/process)"
pipenv run python app.py
```

4. Open browser:

- http://127.0.0.1:5000

_(Note: The UI will load, but gaze tracking will throw 500 errors unless the ML Client is also running)._

#### If you wnat to run through the standalone Docker build:
```bash
docker build -t eyewrite-webapp .
docker run -p 5000:5000 -e ML_CLIENT_URL="[http://host.docker.internal:5002/process](http://host.docker.internal:5002/process)" eyewrite-webapp
```




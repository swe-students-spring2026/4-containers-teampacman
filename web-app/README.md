# EyeWrite Web App

Flask web app for EyeWrite MVP.

## Features in MVP

- Receives normalized gaze coordinates from ML client
- Big on-screen keyboard for gaze typing
- Dwell typing (~900ms)
- Typed message box
- `Space` and `Backspace`
- `Speak` button (browser speech synthesis)
- Quick phrase buttons

## Run

1. Install dependencies:

```bash
pipenv install
```

2. Start Flask app:

```bash
pipenv run python app.py
```

3. Open browser:

- http://127.0.0.1:5000

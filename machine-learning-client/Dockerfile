FROM python:3.11-slim

# System dependencies needed for OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./

RUN pip3 install -r requirements.txt

ADD . .

CMD ["python", "src/tracker.py", "--api-url", "http://web-app:5000/api/gaze"]
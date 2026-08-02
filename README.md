# Street Light SOS

Street Light SOS is an intelligent emergency detection system designed for modern smart cities. By mounting computer vision technology directly onto street lights, the system monitors public roads and sidewalks in real time. When an emergency happens, it automatically alerts response teams so help can arrive as quickly as possible.

## Why This Matters

Emergency response time is critical when accidents or medical crises happen on public streets. Often, valuable minutes are lost while waiting for someone nearby to call emergency services. Street Light SOS solves this problem by using automated edge AI cameras that detect incidents the moment they occur and trigger immediate alerts.

## Key Capabilities

The system uses dual computer vision models (YOLOv8 object detection and pose estimation) to identify six primary emergency categories:

1. Road Accidents: Detects sudden drops in vehicle speed paired with overlapping bounding boxes indicating a crash.
2. Unconscious or Fallen Persons: Uses pose keypoints to measure body orientation. If a person stays horizontal on the ground for several seconds, the system flags a medical emergency.
3. Physical Fights: Monitors spatial proximity between people alongside rapid kinetic movement to detect physical violence.
4. Fire and Smoke: Identifies expanding fire or smoke signatures in public areas.
5. Forced Dragging or Abduction: Detects fast, suspicious dragging movements between individuals near vehicles.
6. Traffic Stagnation: Identifies long term gridlock where vehicles remain stationary for extended periods.

## System Architecture

The project consists of three main parts:

1. Detection Engine (main.py and detector.py): Connects to live CCTV feeds, webcams, or video files. It runs frame by frame inference using YOLO models and OpenCV to identify emergency events.
2. Automated Alert Dispatcher (alert.py): When a high confidence detection occurs, it dispatches notifications through Twilio SMS, voice calls, and local REST API endpoints.
3. Web Dashboard and Live Demo (dashboard.py and docs folder): Provides a live dashboard for monitoring node status, camera health, frame rates, and recent incident logs.

## Quick Start Guide

### Prerequisites

Make sure you have Python 3.8 or higher installed on your computer.

### Step 1: Clone the Repository

```bash
git clone https://github.com/Kanah-png/street-light-sos.git
cd street-light-sos
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Run the Main Application

To start the system using your default computer webcam:

```bash
python main.py --source 0
```

To run the system using a specific video file:

```bash
python main.py --source input_video.mp4
```

To run in headless mode on server hardware like an NVIDIA Jetson:

```bash
python main.py --no-display
```

Once running, open your web browser and go to `http://localhost:8000` to view the live dashboard.

## Web Browser Version

We have also created a web version inside the `docs` folder. When you open the website, it requests permission to use your camera and displays a live preview with simulated emergency detection overlays right inside your browser.

To host the web version on GitHub Pages:

1. Go to your repository settings on GitHub.
2. Navigate to the Pages section.
3. Select the `main` branch and choose the `/docs` folder.
4. Click Save.

## Configuration

You can customize detection sensitivity, alert phone numbers, and camera settings inside `config.py`.

Key settings include:
- USER_PHONE_NUMBER: Set your target mobile number for receiving Twilio SMS alerts.
- DETECTION_CONF_THRESHOLD: Adjust minimum confidence required for emergency detection.
- PROCESS_EVERY_N_FRAMES: Set frame skipping rate to optimize performance on low power devices.

## Tech Stack

- Python 3
- OpenCV
- Ultralytics YOLOv8
- FastAPI and Uvicorn
- Twilio API
- HTML5, CSS3, and JavaScript

## License

This project is open source and available under the MIT License.
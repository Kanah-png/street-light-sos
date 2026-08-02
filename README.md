# 🚦 Smart Emergency Street Light SOS System

An AI-powered street light camera system that watches a live feed and automatically detects emergencies, sending real-time SMS alerts.

## 🔍 What It Detects
| Emergency | Detection Method |
|---|---|
| 🚗 Road Accident | Speed drop + vehicle overlap |
| 🚦 Traffic Jam | 8+ vehicles stalled for 15s |
| 🤕 Unconscious Person | Horizontal body pose via YOLOv8-Pose |
| 👊 Physical Fight | Close proximity + rapid keypoint motion |
| 🔥 Fire / Smoke | Custom YOLO class detection |
| 🚨 Kidnapping | Rapid dragging motion near vehicle |

## 📁 Project Structure
```
street-light-sos/
├── config.py          # All settings & thresholds
├── detector.py        # AI detection engine (YOLOv8)
├── alert.py           # SMS, REST API, local logging
├── main.py            # Entry point — run this!
├── dashboard.py       # Web dashboard (FastAPI)
├── requirements.txt   # Dependencies
├── alerts/            # Auto-created: snapshots & logs
└── sample_data/       # Auto-created: test videos
```

## ⚡ Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure your settings
Edit `config.py`:
- Set your **Twilio credentials** (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
- Set your **phone number** (USER_PHONE_NUMBER)
- Set your **camera source** (DEFAULT_CAMERA_SOURCE)

### 3. Run the system
```bash
python main.py
```

### 4. Open the dashboard
Visit: **http://localhost:8000**

## 🎛 Command Line Options
```bash
python main.py --source 0          # Webcam (default)
python main.py --source video.mp4  # Test with a video file
python main.py --no-display        # Headless server mode
python main.py --no-dashboard      # Skip web dashboard
```

## 📱 SMS Alerts (Twilio Setup)
1. Sign up at [twilio.com](https://www.twilio.com) (free trial available)
2. Get your Account SID and Auth Token from the Twilio Console
3. Get a Twilio phone number
4. Set them in `config.py` or as environment variables:
   ```bash
   set TWILIO_ACCOUNT_SID=ACxxxxx
   set TWILIO_AUTH_TOKEN=your_token
   set TWILIO_FROM_NUMBER=+1xxxxxxxxxx
   ```

## 🧠 AI Models
The system auto-downloads YOLOv8 models on first run:
- `yolov8n.pt` — Object detection (vehicles, persons)
- `yolov8n-pose.pt` — Human pose estimation

For better accuracy, switch to `yolov8s.pt` or `yolov8m.pt` in `config.py`.

## 📊 Alert Log
All alerts are saved to `alerts/alerts.log` as JSON.
Snapshot images are saved to `alerts/` as JPEGs.

"""
Smart Emergency Street Light System - Global Configuration
Edge-optimized configuration settings for perception pipeline, detection rules,
alert thresholds, hardware settings, and communication channels.
"""

import os
from pathlib import Path

# Base Directory Structure
BASE_DIR = Path(__file__).resolve().parent
ALERTS_DIR = BASE_DIR / "alerts"
ALERTS_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE_DIR = BASE_DIR / "sample_data"
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

# Hardware & Inference Engine Configuration
DEVICE = "0"  # "0" for CUDA (NVIDIA Jetson/GPU), "cpu" for Raspberry Pi CPU, or "mps" for Apple Silicon
USE_TENSORRT = False  # Set True when TensorRT FP16/INT8 engine is available
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
TARGET_FPS = 30
PROCESS_EVERY_N_FRAMES = 2  # Frame skipping for edge optimization (process every 2nd frame)

# Camera / Stream Source
# Options: 0 (webcam), "rtsp://user:pass@ip:port/h264", or path to video file
DEFAULT_CAMERA_SOURCE = 0

# Model Paths & Confidence
YOLO_MODEL_PATH = "yolov8n.pt"        # Primary Object & Vehicle/Person model
POSE_MODEL_PATH = "yolov8n-pose.pt"   # Human Pose estimation model for fallen/lying persons
DETECTION_CONF_THRESHOLD = 0.50
ALERT_CONF_THRESHOLD = 0.70           # High confidence minimum to trigger official emergency alert

# Emergency Category Thresholds & Rules
DETECTION_RULES = {
    "ROAD_ACCIDENT": {
        "enabled": True,
        "speed_drop_threshold": 20.0,       # Sudden velocity drop (pixels/frame)
        "bounding_box_overlap": 0.25,       # Overlap ratio between colliding vehicles (IoU >= 0.25)
        "single_vehicle_decel": 30.0,       # Extreme deceleration threshold for single-vehicle barrier/pole impact
        "rollover_aspect_min": 0.40,        # Bounding box aspect ratio (W/H) minimum anomaly for overturned vehicles
        "rollover_aspect_max": 2.70,        # Bounding box aspect ratio anomaly threshold
        "trajectory_angle_shift": 60.0,     # Sharp direction shift angle (degrees) indicating spin-out/collision
        "pedestrian_collision_dist": 50.0,  # Proximity limit (pixels) for vehicle-pedestrian impact
        "min_confidence": 0.70,
        "cooldown_seconds": 30
    },
    "TRAFFIC_JAM": {
        "enabled": True,
        "min_vehicle_count": 8,        # Vehicles present in ROI
        "max_avg_speed": 1.5,          # Stagnant motion threshold (pixels/frame)
        "duration_seconds": 15,        # Must persist for 15 seconds
        "min_confidence": 0.80,
        "cooldown_seconds": 60
    },
    "UNCONSCIOUS_PERSON": {
        "enabled": True,
        "max_torso_angle": 30.0,       # Body angle relative to horizontal ground (degrees)
        "aspect_ratio_min": 1.8,       # Width / Height ratio of bounding box (horizontal orientation)
        "persist_frames": 10,          # Must remain horizontal across consecutive frames
        "min_confidence": 0.75,
        "cooldown_seconds": 45
    },
    "PHYSICAL_FIGHT": {
        "enabled": True,
        "proximity_distance": 80.0,    # Max distance between individuals (pixels)
        "keypoint_motion_std": 18.0,   # High kinetic energy fluctuation threshold
        "persist_frames": 8,
        "min_confidence": 0.70,
        "cooldown_seconds": 30
    },
    "FIRE_SMOKE": {
        "enabled": True,
        "fire_classes": [1, 2],         # Custom YOLO trained class IDs for fire/smoke
        "min_area_pixels": 400,
        "min_confidence": 0.65,
        "cooldown_seconds": 30
    },
    "KIDNAPPING_FORCED_MOVEMENT": {
        "enabled": True,
        "rapid_drag_speed": 35.0,      # Unusually fast forced dragging motion vector
        "person_vehicle_proximity": 60.0,
        "persist_frames": 5,
        "min_confidence": 0.75,
        "cooldown_seconds": 45
    }
}

# Prototype Mode Configuration
PROTOTYPE_MODE = True
USER_PHONE_NUMBER = os.getenv("USER_PHONE_NUMBER", "+919983974149")  # Change to your personal phone number

# Alert Dispatch & Communication Settings
ALERT_CHANNELS = {
    "REST_API": {
        "enabled": True,
        "endpoint_url": "https://api.emergency-services.local/v1/incidents",
        "timeout": 5.0
    },
    "SMS_TWILIO": {
        "enabled": True,              # Set True for Prototype Personal SMS / Call
        "account_sid": os.getenv("TWILIO_ACCOUNT_SID", "YOUR_TWILIO_ACCOUNT_SID"),
        "auth_token": os.getenv("TWILIO_AUTH_TOKEN", "YOUR_TWILIO_AUTH_TOKEN"),
        "from_number": os.getenv("TWILIO_FROM_NUMBER", "+18005550199"),  # Twilio Phone Number
        "to_number": USER_PHONE_NUMBER
    },
    "MQTT": {
        "enabled": False,
        "broker_host": "localhost",
        "broker_port": 1883,
        "topic": "streetlights/emergency/alerts"
    },
    "SAVE_LOCAL_SNAPSHOT": True,
    "SAVE_LOCAL_LOG": True
}

# FastAPI Web Dashboard Settings
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 8000

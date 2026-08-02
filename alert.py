"""
Smart Emergency Street Light System - Alert Module
Dispatches emergency alerts via SMS (Twilio), REST API, and local logs/snapshots.
"""

import json
import time
import datetime
import threading
import cv2
import requests
import config


def _timestamp():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def send_sms(alert: dict):
    """Send an SMS alert to the configured phone number via Twilio."""
    ch = config.ALERT_CHANNELS["SMS_TWILIO"]
    if not ch["enabled"]:
        return

    sid = ch["account_sid"]
    token = ch["auth_token"]

    if "YOUR_TWILIO" in sid or "YOUR_TWILIO" in token:
        print(f"[Alert] ⚠ Twilio not configured — skipping SMS for {alert['type']}")
        return

    try:
        from twilio.rest import Client
        client = Client(sid, token)
        body = (
            f"🚨 STREET LIGHT SOS ALERT\n"
            f"Type: {alert['type']}\n"
            f"Confidence: {alert['confidence'] * 100:.0f}%\n"
            f"Details: {alert['description']}\n"
            f"Time: {datetime.datetime.now().strftime('%d-%b-%Y %H:%M:%S')}"
        )
        message = client.messages.create(
            body=body,
            from_=ch["from_number"],
            to=ch["to_number"]
        )
        print(f"[Alert] ✅ SMS sent (SID: {message.sid}) for {alert['type']}")
    except Exception as e:
        print(f"[Alert] ❌ SMS failed: {e}")


def send_rest_api(alert: dict):
    """POST alert data to the configured REST API endpoint."""
    ch = config.ALERT_CHANNELS["REST_API"]
    if not ch["enabled"]:
        return

    payload = {
        "event_type": alert["type"],
        "confidence": alert["confidence"],
        "description": alert["description"],
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "location": "Street Camera Node-01"
    }
    try:
        resp = requests.post(
            ch["endpoint_url"],
            json=payload,
            timeout=ch["timeout"]
        )
        print(f"[Alert] REST API response: {resp.status_code} for {alert['type']}")
    except requests.exceptions.ConnectionError:
        print(f"[Alert] ⚠ REST API unreachable — skipping (offline/prototype mode)")
    except Exception as e:
        print(f"[Alert] ❌ REST API error: {e}")


def save_snapshot(frame, alert: dict):
    """Save a JPEG snapshot of the frame when an emergency is detected."""
    if not config.ALERT_CHANNELS.get("SAVE_LOCAL_SNAPSHOT", True):
        return None
    filename = config.ALERTS_DIR / f"{alert['type']}_{_timestamp()}.jpg"
    cv2.imwrite(str(filename), frame)
    print(f"[Alert] 📸 Snapshot saved: {filename.name}")
    return str(filename)


def save_log(alert: dict, snapshot_path: str = None):
    """Append alert entry to the local JSONL log file."""
    if not config.ALERT_CHANNELS.get("SAVE_LOCAL_LOG", True):
        return
    log_file = config.ALERTS_DIR / "alerts.log"
    entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "type": alert["type"],
        "confidence": alert["confidence"],
        "description": alert["description"],
        "snapshot": snapshot_path
    }
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"[Alert] 📝 Logged: {alert['type']}")


def dispatch(alert: dict, frame=None):
    """
    Main dispatch function — called when an emergency is detected.
    Runs all alert channels in a background thread so detection doesn't block.
    """
    print(f"\n[Alert] 🚨 EMERGENCY: {alert['type']} (conf={alert['confidence']})")
    print(f"        {alert['description']}\n")

    def _run():
        snapshot_path = save_snapshot(frame, alert) if frame is not None else None
        save_log(alert, snapshot_path)
        send_sms(alert)
        send_rest_api(alert)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()


def load_recent_alerts(max_entries=50):
    """Read the most recent alerts from the log file for the dashboard."""
    log_file = config.ALERTS_DIR / "alerts.log"
    if not log_file.exists():
        return []
    entries = []
    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            try:
                entries.append(json.loads(line.strip()))
            except json.JSONDecodeError:
                continue
    return entries[-max_entries:]

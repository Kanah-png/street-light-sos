"""
Smart Emergency Street Light System - Main Entry Point
Run this file to start the full detection pipeline.

Usage:
    python main.py
    python main.py --source 0          # Use webcam
    python main.py --source video.mp4  # Use a video file
    python main.py --no-display        # Headless mode (no OpenCV window)
"""

import sys
import time
import argparse
import threading
import datetime
import cv2
import config
import detector as det_module
import alert as alert_module
import dashboard


def parse_args():
    parser = argparse.ArgumentParser(description="Smart Emergency Street Light SOS System")
    parser.add_argument("--source", default=config.DEFAULT_CAMERA_SOURCE,
                        help="Camera index (0), RTSP URL, or video file path")
    parser.add_argument("--no-display", action="store_true",
                        help="Run headless without OpenCV window (for servers/Jetson)")
    parser.add_argument("--no-dashboard", action="store_true",
                        help="Disable the FastAPI web dashboard")
    return parser.parse_args()


def main():
    args = parse_args()

    # --- Start web dashboard in background ---
    if not args.no_dashboard:
        print(f"[Main] 🌐 Starting dashboard at http://localhost:{config.SERVER_PORT}")
        dash_thread = threading.Thread(target=dashboard.start_server, daemon=True)
        dash_thread.start()
        dashboard.system_state["started_at"] = datetime.datetime.now()

    # --- Load AI models ---
    detector = det_module.EmergencyDetector()
    dashboard.system_state["model_loaded"] = True

    # --- Open camera / video source ---
    source = args.source
    try:
        source = int(source)  # Try as webcam index
    except (ValueError, TypeError):
        pass   # Keep as string (RTSP / file path)

    print(f"[Main] 📷 Opening camera source: {source}")
    cap = cv2.VideoCapture(source)

    if not cap.isOpened():
        print(f"[Main] ❌ Cannot open camera source '{source}'. Check your config.")
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, config.TARGET_FPS)

    dashboard.system_state["camera_ok"] = True
    print(f"[Main] ✅ Camera opened. Running detection... Press Q to quit.\n")

    frame_idx = 0
    fps_timer = time.time()
    fps_counter = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[Main] ⚠ Frame read failed — end of stream or camera disconnected.")
                break

            frame_idx += 1
            fps_counter += 1

            # Update FPS every second
            if time.time() - fps_timer >= 1.0:
                dashboard.system_state["fps"] = fps_counter / (time.time() - fps_timer)
                fps_counter = 0
                fps_timer = time.time()

            # Frame skipping — only process every N frames
            if frame_idx % config.PROCESS_EVERY_N_FRAMES != 0:
                if not args.no_display:
                    cv2.imshow("Street Light SOS", frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
                continue

            # --- Run detection ---
            annotated_frame, alerts = detector.process_frame(frame)

            # --- Dispatch alerts ---
            for a in alerts:
                dashboard.system_state["total_alerts"] += 1
                alert_module.dispatch(a, frame=annotated_frame)

            # --- Show live window ---
            if not args.no_display:
                # Draw FPS on screen
                fps_text = f"FPS: {dashboard.system_state['fps']:.1f}"
                cv2.putText(annotated_frame, fps_text,
                            (config.FRAME_WIDTH - 130, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)

                cv2.imshow("Street Light SOS - Press Q to quit", annotated_frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    print("[Main] Q pressed - shutting down.")
                    break

    except KeyboardInterrupt:
        print("\n[Main] Interrupted by user.")

    finally:
        cap.release()
        cv2.destroyAllWindows()
        dashboard.system_state["camera_ok"] = False
        dashboard.system_state["running"] = False
        print("[Main] 🛑 System stopped.")


if __name__ == "__main__":
    main()

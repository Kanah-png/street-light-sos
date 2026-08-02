"""
Smart Emergency Street Light System - Detector Module
Handles all AI inference: YOLOv8 object detection, pose estimation,
vehicle tracking, and emergency event classification.
"""

import time
import math
import numpy as np
import cv2
from collections import defaultdict, deque
from ultralytics import YOLO
import config


class CentroidTracker:
    """Simple centroid-based tracker to assign IDs and track speeds & trajectories."""

    def __init__(self, max_disappeared=30):
        self.next_id = 0
        self.objects = {}         # id -> centroid
        self.disappeared = {}     # id -> frames missing
        self.history = defaultdict(lambda: deque(maxlen=10))      # id -> speed history
        self.pos_history = defaultdict(lambda: deque(maxlen=10))  # id -> position (cx, cy) history
        self.max_disappeared = max_disappeared

    def register(self, centroid):
        self.objects[self.next_id] = centroid
        self.disappeared[self.next_id] = 0
        self.pos_history[self.next_id].append(centroid)
        self.next_id += 1

    def deregister(self, obj_id):
        del self.objects[obj_id]
        del self.disappeared[obj_id]
        if obj_id in self.history:
            del self.history[obj_id]
        if obj_id in self.pos_history:
            del self.pos_history[obj_id]

    def update(self, detections):
        """
        detections: list of (cx, cy) centroids
        Returns: dict of id -> centroid
        """
        if len(detections) == 0:
            for obj_id in list(self.disappeared.keys()):
                self.disappeared[obj_id] += 1
                if self.disappeared[obj_id] > self.max_disappeared:
                    self.deregister(obj_id)
            return self.objects

        if len(self.objects) == 0:
            for centroid in detections:
                self.register(centroid)
        else:
            obj_ids = list(self.objects.keys())
            obj_centroids = list(self.objects.values())

            # Compute distances
            D = np.zeros((len(obj_centroids), len(detections)))
            for i, oc in enumerate(obj_centroids):
                for j, dc in enumerate(detections):
                    D[i, j] = math.dist(oc, dc)

            rows = D.min(axis=1).argsort()
            cols = D.argmin(axis=1)[rows]

            used_rows, used_cols = set(), set()
            for (row, col) in zip(rows, cols):
                if row in used_rows or col in used_cols:
                    continue
                obj_id = obj_ids[row]
                prev = self.objects[obj_id]
                curr = detections[col]
                speed = math.dist(prev, curr)
                self.history[obj_id].append(speed)
                self.pos_history[obj_id].append(curr)
                self.objects[obj_id] = curr
                self.disappeared[obj_id] = 0
                used_rows.add(row)
                used_cols.add(col)

            unused_rows = set(range(len(obj_centroids))) - used_rows
            unused_cols = set(range(len(detections))) - used_cols

            for row in unused_rows:
                obj_id = obj_ids[row]
                self.disappeared[obj_id] += 1
                if self.disappeared[obj_id] > self.max_disappeared:
                    self.deregister(obj_id)

            for col in unused_cols:
                self.register(detections[col])

        return self.objects

    def get_speed(self, obj_id):
        h = self.history.get(obj_id, [])
        return float(np.mean(h)) if h else 0.0


class EmergencyDetector:
    """
    Main AI detection engine.
    Loads YOLO models and detects all 6 emergency categories.
    """

    # COCO class indices
    VEHICLE_CLASSES = {2, 3, 5, 7}   # car, motorbike, bus, truck
    PERSON_CLASS = 0

    def __init__(self):
        print("[Detector] Loading YOLOv8 object detection model...")
        self.yolo = YOLO(config.YOLO_MODEL_PATH)

        print("[Detector] Loading YOLOv8 pose estimation model...")
        self.pose = YOLO(config.POSE_MODEL_PATH)

        self.vehicle_tracker = CentroidTracker()
        self.person_tracker = CentroidTracker()

        # Frame counters for persistence-based rules
        self._unconscious_counts = defaultdict(int)   # person_id -> consecutive horizontal frames
        self._fight_counts = 0
        self._kidnap_counts = 0
        self._jam_start_time = None

        # Cooldown timestamps per emergency type
        self._cooldowns = {}

        print("[Detector] Models loaded. Ready.\n")

    def _is_on_cooldown(self, event_type):
        last = self._cooldowns.get(event_type, 0)
        cd = config.DETECTION_RULES.get(event_type, {}).get("cooldown_seconds", 30)
        return (time.time() - last) < cd

    def _trigger(self, event_type):
        self._cooldowns[event_type] = time.time()

    def _iou(self, box1, box2):
        """Compute Intersection over Union of two boxes [x1,y1,x2,y2]."""
        xi1 = max(box1[0], box2[0])
        yi1 = max(box1[1], box2[1])
        xi2 = min(box1[2], box2[2])
        yi2 = min(box1[3], box2[3])
        inter = max(0, xi2 - xi1) * max(0, yi2 - yi1)
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area1 + area2 - inter
        return inter / union if union > 0 else 0

    def process_frame(self, frame):
        """
        Run full detection pipeline on a single frame.
        Returns: (annotated_frame, list_of_alert_dicts)
        """
        alerts = []
        rules = config.DETECTION_RULES

        # --- Run YOLO object detection ---
        det_results = self.yolo(
            frame,
            conf=config.DETECTION_CONF_THRESHOLD,
            verbose=False
        )[0]

        # --- Run pose estimation ---
        pose_results = self.pose(
            frame,
            conf=config.DETECTION_CONF_THRESHOLD,
            verbose=False
        )[0]

        # Parse object detections
        vehicle_boxes = []
        vehicle_centroids = []
        person_boxes = []
        person_centroids = []

        annotated = frame.copy()

        if det_results.boxes is not None:
            for box in det_results.boxes:
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

                if cls in self.VEHICLE_CLASSES:
                    vehicle_boxes.append((x1, y1, x2, y2, conf))
                    vehicle_centroids.append((cx, cy))
                    cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 200, 255), 2)

                elif cls == self.PERSON_CLASS:
                    person_boxes.append((x1, y1, x2, y2, conf))
                    person_centroids.append((cx, cy))
                    cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 100), 2)

        # Update trackers
        self.vehicle_tracker.update(vehicle_centroids)
        self.person_tracker.update(person_centroids)

        # -------------------------------------------------------
        # 1. ROAD ACCIDENT
        # -------------------------------------------------------
        r = rules["ROAD_ACCIDENT"]
        if r["enabled"] and not self._is_on_cooldown("ROAD_ACCIDENT"):
            accident_detected = False
            acc_reason = ""
            acc_conf = 0.0

            # (A) Multi-Vehicle Collision (IoU + Speed drop)
            if len(vehicle_boxes) >= 2:
                for i in range(len(vehicle_boxes)):
                    for j in range(i + 1, len(vehicle_boxes)):
                        iou = self._iou(vehicle_boxes[i][:4], vehicle_boxes[j][:4])
                        conf_avg = (vehicle_boxes[i][4] + vehicle_boxes[j][4]) / 2

                        v1_speed_hist = list(self.vehicle_tracker.history.get(i, []))
                        v2_speed_hist = list(self.vehicle_tracker.history.get(j, []))
                        max_drop = 0.0
                        if len(v1_speed_hist) >= 2:
                            max_drop = max(max_drop, max(v1_speed_hist[:-1]) - v1_speed_hist[-1])
                        if len(v2_speed_hist) >= 2:
                            max_drop = max(max_drop, max(v2_speed_hist[:-1]) - v2_speed_hist[-1])

                        if (iou >= r["bounding_box_overlap"] or max_drop >= r["speed_drop_threshold"]) and conf_avg >= r["min_confidence"]:
                            accident_detected = True
                            acc_reason = f"Vehicle collision — IoU={iou:.2f}, speed drop={max_drop:.1f}px/f"
                            acc_conf = conf_avg
                            break
                    if accident_detected:
                        break

            # (B) Single-Vehicle High Deceleration Impact (Collision with barrier/pole)
            if not accident_detected:
                for v_id, v_speed_hist in self.vehicle_tracker.history.items():
                    if len(v_speed_hist) >= 3:
                        speeds = list(v_speed_hist)
                        drop = max(speeds[:-1]) - speeds[-1]
                        if drop >= r["single_vehicle_decel"]:
                            accident_detected = True
                            acc_reason = f"Single-vehicle impact — sudden deceleration drop {drop:.1f}px/f"
                            acc_conf = r["min_confidence"] + 0.10
                            break

            # (C) Vehicle Rollover / Overturned Aspect Ratio Anomaly
            if not accident_detected and vehicle_boxes:
                for vb in vehicle_boxes:
                    vw = vb[2] - vb[0]
                    vh = vb[3] - vb[1]
                    if vh > 0:
                        ar = vw / vh
                        if (ar < r["rollover_aspect_min"] or ar > r["rollover_aspect_max"]) and vb[4] >= r["min_confidence"]:
                            accident_detected = True
                            acc_reason = f"Vehicle rollover detected — aspect ratio anomaly (w/h={ar:.2f})"
                            acc_conf = vb[4]
                            break

            # (D) Angular Trajectory Spin-out
            if not accident_detected:
                for v_id, pos_hist in self.vehicle_tracker.pos_history.items():
                    if len(pos_hist) >= 4:
                        p = list(pos_hist)
                        v1 = (p[-2][0] - p[-4][0], p[-2][1] - p[-4][1])
                        v2 = (p[-1][0] - p[-2][0], p[-1][1] - p[-2][1])
                        mag1 = math.hypot(v1[0], v1[1])
                        mag2 = math.hypot(v2[0], v2[1])
                        if mag1 > 5.0 and mag2 > 2.0:
                            dot = (v1[0] * v2[0] + v1[1] * v2[1]) / (mag1 * mag2)
                            dot = max(-1.0, min(1.0, dot))
                            angle_deg = math.degrees(math.acos(dot))
                            if angle_deg >= r["trajectory_angle_shift"]:
                                accident_detected = True
                                acc_reason = f"Vehicle spin-out detected — trajectory deflection ({angle_deg:.1f}°)"
                                acc_conf = r["min_confidence"] + 0.08
                                break

            # (E) Vehicle-Pedestrian Impact Zone
            if not accident_detected and vehicle_boxes and person_boxes:
                for vb in vehicle_boxes:
                    vcx, vcy = (vb[0] + vb[2]) / 2, (vb[1] + vb[3]) / 2
                    for pb in person_boxes:
                        pcx, pcy = (pb[0] + pb[2]) / 2, (pb[1] + pb[3]) / 2
                        dist = math.dist((vcx, vcy), (pcx, pcy))
                        if dist <= r["pedestrian_collision_dist"]:
                            accident_detected = True
                            acc_reason = f"Pedestrian-vehicle impact — proximity {dist:.1f}px"
                            acc_conf = max(vb[4], pb[4])
                            break
                    if accident_detected:
                        break

            if accident_detected:
                self._trigger("ROAD_ACCIDENT")
                alerts.append({
                    "type": "ROAD_ACCIDENT",
                    "confidence": round(min(0.99, float(acc_conf)), 2),
                    "description": acc_reason
                })
                cv2.putText(annotated, "⚠ ACCIDENT", (20, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)

        # -------------------------------------------------------
        # 2. TRAFFIC JAM
        # -------------------------------------------------------
        r = rules["TRAFFIC_JAM"]
        if r["enabled"] and not self._is_on_cooldown("TRAFFIC_JAM"):
            if len(vehicle_boxes) >= r["min_vehicle_count"]:
                avg_speeds = [self.vehicle_tracker.get_speed(vid)
                              for vid in list(self.vehicle_tracker.objects.keys())]
                avg_speed = float(np.mean(avg_speeds)) if avg_speeds else 999
                if avg_speed <= r["max_avg_speed"]:
                    if self._jam_start_time is None:
                        self._jam_start_time = time.time()
                    elif time.time() - self._jam_start_time >= r["duration_seconds"]:
                        self._trigger("TRAFFIC_JAM")
                        self._jam_start_time = None
                        alerts.append({
                            "type": "TRAFFIC_JAM",
                            "confidence": round(r["min_confidence"], 2),
                            "description": f"{len(vehicle_boxes)} vehicles stalled, avg speed={avg_speed:.2f}px/f"
                        })
                        cv2.putText(annotated, "⚠ TRAFFIC JAM", (20, 100),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 165, 255), 3)
                else:
                    self._jam_start_time = None
            else:
                self._jam_start_time = None

        # -------------------------------------------------------
        # 3. UNCONSCIOUS PERSON (via pose)
        # -------------------------------------------------------
        r = rules["UNCONSCIOUS_PERSON"]
        if r["enabled"] and not self._is_on_cooldown("UNCONSCIOUS_PERSON"):
            if pose_results.boxes is not None and pose_results.keypoints is not None:
                for idx, (box, kpts) in enumerate(
                        zip(pose_results.boxes, pose_results.keypoints)):
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    w = x2 - x1
                    h = y2 - y1
                    if h == 0:
                        continue
                    aspect = w / h
                    conf = float(box.conf[0])

                    if aspect >= r["aspect_ratio_min"] and conf >= r["min_confidence"]:
                        self._unconscious_counts[idx] += 1
                        if self._unconscious_counts[idx] >= r["persist_frames"]:
                            self._trigger("UNCONSCIOUS_PERSON")
                            self._unconscious_counts[idx] = 0
                            alerts.append({
                                "type": "UNCONSCIOUS_PERSON",
                                "confidence": round(conf, 2),
                                "description": f"Person lying horizontal (aspect={aspect:.2f}) for {r['persist_frames']}+ frames"
                            })
                            cv2.putText(annotated, "⚠ UNCONSCIOUS", (20, 140),
                                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 200), 3)
                    else:
                        self._unconscious_counts[idx] = max(0, self._unconscious_counts[idx] - 1)

        # -------------------------------------------------------
        # 4. PHYSICAL FIGHT
        # -------------------------------------------------------
        r = rules["PHYSICAL_FIGHT"]
        if r["enabled"] and not self._is_on_cooldown("PHYSICAL_FIGHT") and len(person_boxes) >= 2:
            fight_detected = False
            for i in range(len(person_boxes)):
                for j in range(i + 1, len(person_boxes)):
                    cx_i = (person_boxes[i][0] + person_boxes[i][2]) / 2
                    cy_i = (person_boxes[i][1] + person_boxes[i][3]) / 2
                    cx_j = (person_boxes[j][0] + person_boxes[j][2]) / 2
                    cy_j = (person_boxes[j][1] + person_boxes[j][3]) / 2
                    dist = math.dist((cx_i, cy_i), (cx_j, cy_j))
                    if dist <= r["proximity_distance"]:
                        # Check keypoint motion variance
                        speeds_i = list(self.person_tracker.history.get(i, []))
                        speeds_j = list(self.person_tracker.history.get(j, []))
                        all_speeds = speeds_i + speeds_j
                        if all_speeds and np.std(all_speeds) >= r["keypoint_motion_std"]:
                            fight_detected = True

            if fight_detected:
                self._fight_counts += 1
                if self._fight_counts >= r["persist_frames"]:
                    self._trigger("PHYSICAL_FIGHT")
                    self._fight_counts = 0
                    conf_avg = float(np.mean([b[4] for b in person_boxes]))
                    alerts.append({
                        "type": "PHYSICAL_FIGHT",
                        "confidence": round(max(conf_avg, r["min_confidence"]), 2),
                        "description": f"Fight detected between {len(person_boxes)} people in close proximity"
                    })
                    cv2.putText(annotated, "⚠ FIGHT", (20, 180),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 200), 3)
            else:
                self._fight_counts = max(0, self._fight_counts - 1)

        # -------------------------------------------------------
        # 5. FIRE / SMOKE  (uses custom trained YOLO classes)
        # -------------------------------------------------------
        r = rules["FIRE_SMOKE"]
        if r["enabled"] and not self._is_on_cooldown("FIRE_SMOKE"):
            if det_results.boxes is not None:
                for box in det_results.boxes:
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])
                    if cls in r["fire_classes"] and conf >= r["min_confidence"]:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        area = (x2 - x1) * (y2 - y1)
                        if area >= r["min_area_pixels"]:
                            self._trigger("FIRE_SMOKE")
                            alerts.append({
                                "type": "FIRE_SMOKE",
                                "confidence": round(conf, 2),
                                "description": f"Fire/smoke detected (class={cls}, area={area}px²)"
                            })
                            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 0, 255), 3)
                            cv2.putText(annotated, "⚠ FIRE/SMOKE", (20, 220),
                                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)

        # -------------------------------------------------------
        # 6. KIDNAPPING / FORCED MOVEMENT
        # -------------------------------------------------------
        r = rules["KIDNAPPING_FORCED_MOVEMENT"]
        if r["enabled"] and not self._is_on_cooldown("KIDNAPPING_FORCED_MOVEMENT"):
            if person_boxes and vehicle_boxes:
                for pb in person_boxes:
                    pcx = (pb[0] + pb[2]) / 2
                    pcy = (pb[1] + pb[3]) / 2
                    for vb in vehicle_boxes:
                        vcx = (vb[0] + vb[2]) / 2
                        vcy = (vb[1] + vb[3]) / 2
                        prox = math.dist((pcx, pcy), (vcx, vcy))
                        if prox <= r["person_vehicle_proximity"]:
                            # Check person speed
                            p_speed = float(np.mean(list(
                                self.person_tracker.history.get(0, [0])
                            )))
                            if p_speed >= r["rapid_drag_speed"]:
                                self._kidnap_counts += 1
                                if self._kidnap_counts >= r["persist_frames"]:
                                    self._trigger("KIDNAPPING_FORCED_MOVEMENT")
                                    self._kidnap_counts = 0
                                    alerts.append({
                                        "type": "KIDNAPPING_FORCED_MOVEMENT",
                                        "confidence": round(pb[4], 2),
                                        "description": f"Forced movement near vehicle detected (speed={p_speed:.1f}px/f)"
                                    })
                                    cv2.putText(annotated, "⚠ KIDNAP ALERT", (20, 260),
                                                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)
                            else:
                                self._kidnap_counts = max(0, self._kidnap_counts - 1)

        # Draw FPS overlay
        cv2.putText(annotated, "Smart Street Light SOS", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        return annotated, alerts

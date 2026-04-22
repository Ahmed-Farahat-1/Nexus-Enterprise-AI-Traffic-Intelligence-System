import cv2
import numpy as np
from ultralytics import YOLO
from collections import defaultdict

# ==========================================
# ⚙️ CONFIGURATION & CONSTANTS
# ==========================================
K = 10000  # Configurable constant for distance approximation
VEHICLE_CLASSES = [2, 3, 5, 7]  # COCO classes: car, motorcycle, bus, truck
HISTORY_LENGTH = 10  # Number of frames to keep in history for smoothing

# Colors (BGR format for OpenCV)
COLOR_NORMAL = (0, 255, 0)      # Green
COLOR_WRONG_WAY = (0, 0, 255)   # Red
COLOR_SUDDEN_STOP = (0, 165, 255)# Orange
COLOR_TEXT = (255, 255, 255)    # White

# ==========================================
# 🧠 CORE LOGIC FUNCTIONS
# ==========================================

def get_lane(x_center, frame_width):
    """Divides the road into LEFT and RIGHT lanes based on the image midpoint."""
    return "LEFT" if x_center < (frame_width / 2) else "RIGHT"

def compute_speed(current_h, past_h, frame_diff, fps):
    """
    Computes approximate speed using the inverse proportion of bounding box height.
    Formula: distance ≈ K / bbox_height
    Speed = |d2 - d1| / time_elapsed * 3.6
    """
    if past_h == 0 or current_h == 0 or frame_diff == 0:
        return 0.0
    
    d1 = K / past_h
    d2 = K / current_h
    time_elapsed = frame_diff / fps
    
    # Calculate speed in km/h
    speed = (abs(d2 - d1) / time_elapsed) * 3.6
    return round(speed, 1)

def detect_direction(centers_y):
    """Determines direction based on the vertical movement of center points."""
    if len(centers_y) < 5:
        return "UNKNOWN"
    
    # Compare current Y with Y from 5 frames ago to reduce noise
    dy = centers_y[-1] - centers_y[-5]
    
    # Y increases downwards in images
    if dy > 5:
        return "DOWN"
    elif dy < -5:
        return "UP"
    return "UNKNOWN"

def check_wrong_way(lane, direction):
    """Flags wrong-way driving based on lane rules."""
    if direction == "UNKNOWN":
        return False
    # Rule: Left lane must go DOWN, Right lane must go UP
    if lane == "LEFT" and direction == "UP":
        return True
    if lane == "RIGHT" and direction == "DOWN":
        return True
    return False

def check_sudden_stop(current_speed, speed_history):
    """Detects if a vehicle suddenly dropped speed from >20 km/h to <3 km/h."""
    if not speed_history:
        return False
    max_recent_speed = max(speed_history)
    return max_recent_speed > 20.0 and current_speed < 3.0

def get_traffic_density(vehicle_count, avg_speed):
    """Classifies overall traffic conditions."""
    if vehicle_count > 15 and avg_speed < 10:
        return "TRAFFIC JAM"
    elif vehicle_count > 10:
        return "HIGH"
    elif vehicle_count > 5:
        return "MEDIUM"
    else:
        return "LOW"

# ==========================================
# 🚀 MAIN PIPELINE
# ==========================================

def process_video(input_path, output_path="output_traffic.mp4"):
    # Initialize YOLOv8 model
    print("Loading YOLOv8 model...")
    model = YOLO("yolov8n.pt")  # Use 'yolov8s.pt' for better accuracy if hardware permits
    
    # Open video capture
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        print(f"Error: Could not open video {input_path}")
        return

    # Video properties
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0  # Fallback to 30 if cannot read FPS
    
    # Setup Video Writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    # Tracking History Dictionary
    # Stores lists of historical data for each unique vehicle ID
    track_history = defaultdict(lambda: {
        "centers_y": [],
        "heights": [],
        "speeds": [],
        "last_seen_frame": 0
    })

    frame_count = 0

    print("Processing video frames...")
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break
            
        frame_count += 1
        
        # Draw lane divider
        cv2.line(frame, (width // 2, 0), (width // 2, height), (255, 255, 255), 2)
        cv2.putText(frame, "DOWN", (width // 4, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(frame, "UP", (3 * width // 4, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        # Run YOLOv8 tracking (uses ByteTrack by default)
        results = model.track(frame, persist=True, classes=VEHICLE_CLASSES, verbose=False, conf=0.3)

        current_vehicle_count = 0
        current_frame_speeds = []

        if results[0].boxes is not None and results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            ids = results[0].boxes.id.cpu().numpy().astype(int)
            current_vehicle_count = len(ids)

            for box, track_id in zip(boxes, ids):
                x1, y1, x2, y2 = map(int, box)
                x_center = (x1 + x2) / 2
                y_center = (y1 + y2) / 2
                bbox_height = y2 - y1

                # Update History
                history = track_history[track_id]
                history["centers_y"].append(y_center)
                history["heights"].append(bbox_height)
                
                # Keep history lists bounded
                if len(history["centers_y"]) > HISTORY_LENGTH:
                    history["centers_y"].pop(0)
                    history["heights"].pop(0)

                # ==========================
                # METRICS CALCULATION
                # ==========================
                
                # 1. Lane
                lane = get_lane(x_center, width)
                
                # 2. Direction
                direction = detect_direction(history["centers_y"])
                
                # 3. Speed (Compute comparing current height to height 5 frames ago)
                current_speed = 0.0
                if len(history["heights"]) >= 5:
                    past_h = history["heights"][-5]
                    current_speed = compute_speed(bbox_height, past_h, frame_diff=5, fps=fps)
                
                history["speeds"].append(current_speed)
                if len(history["speeds"]) > HISTORY_LENGTH:
                    history["speeds"].pop(0)
                    
                current_frame_speeds.append(current_speed)

                # 4. Behavior Analysis
                is_wrong_way = check_wrong_way(lane, direction)
                is_sudden_stop = check_sudden_stop(current_speed, history["speeds"][:-1])
                
                behavior = "NORMAL"
                color = COLOR_NORMAL
                
                if is_wrong_way:
                    behavior = "WRONG WAY"
                    color = COLOR_WRONG_WAY
                elif is_sudden_stop:
                    behavior = "SUDDEN STOP"
                    color = COLOR_SUDDEN_STOP
                elif current_speed < 3.0:
                    behavior = "STOPPED"
                elif current_speed < 10.0:
                    behavior = "SLOW"

                # ==========================
                # VISUALIZATION
                # ==========================
                
                # Draw Bounding Box
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                
                # Info Text
                label_1 = f"ID: {track_id} | {lane}"
                label_2 = f"{current_speed} km/h | {behavior}"
                
                # Background for text
                cv2.rectangle(frame, (x1, y1 - 40), (x2, y1), color, -1)
                cv2.putText(frame, label_1, (x1 + 2, y1 - 22), cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLOR_TEXT, 2)
                cv2.putText(frame, label_2, (x1 + 2, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLOR_TEXT, 2)

        # ==========================
        # GLOBAL TRAFFIC METRICS
        # ==========================
        avg_speed = sum(current_frame_speeds) / len(current_frame_speeds) if current_frame_speeds else 0
        density_status = get_traffic_density(current_vehicle_count, avg_speed)

        # Global Overlay Panel
        cv2.rectangle(frame, (10, 10), (350, 130), (0, 0, 0), -1)
        cv2.putText(frame, f"Density: {density_status}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        cv2.putText(frame, f"Vehicle Count: {current_vehicle_count}", (20, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLOR_TEXT, 2)
        cv2.putText(frame, f"Avg Speed: {round(avg_speed, 1)} km/h", (20, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLOR_TEXT, 2)

        # Write and optionally display frame
        out.write(frame)
        
        # Uncomment below to view processing in real-time (press 'q' to quit)
        # cv2.imshow("Traffic Intelligence System", frame)
        # if cv2.waitKey(1) & 0xFF == ord('q'):
        #     break

    # Cleanup
    cap.release()
    out.release()
    cv2.destroyAllWindows()
    print(f"Processing complete! Saved to {output_path}")

if __name__ == "__main__":
    # Ensure you provide a valid path to a traffic video
    # Example: process_video("test_traffic.mp4")
    process_video(r"C:\Users\asamy\Downloads\AI_Traffic_Video_Generation_Request.mp4")
    print("Script initialized. Call process_video('your_video.mp4') to run.")
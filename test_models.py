"""Diagnostic v2: Re-test all slave models after easyocr install."""
import cv2
import numpy as np
from ultralytics import YOLO
from utils.constants import VEHICLE_CLASSES, YOLO_CONFIDENCE

video = r"C:\Users\asamy\Downloads\Realistic_Traffic_Surveillance_Video_Generation.mp4"
cap = cv2.VideoCapture(video)
model = YOLO("yolov8n.pt")

cap.set(cv2.CAP_PROP_POS_FRAMES, 60)
ret, frame = cap.read()
results = model.track(frame, persist=True, classes=VEHICLE_CLASSES, verbose=False, conf=YOLO_CONFIDENCE)
boxes = results[0].boxes.xyxy.cpu().numpy()
areas = [(b[2]-b[0])*(b[3]-b[1]) for b in boxes]
best = np.argmax(areas)
x1, y1, x2, y2 = map(int, boxes[best])
crop = frame[y1:y2, x1:x2].copy()
cap.release()
print(f"Crop shape: {crop.shape}, area: {areas[best]:.0f}px^2")

# === TEST 1: BLIP ===
print("\n=== TEST 1: BLIP Vehicle Description ===")
try:
    from core.vehicle_descriptor import describe_vehicle
    desc = describe_vehicle(crop)
    print(f'  Result: "{desc}"')
except Exception as e:
    print(f"  FAILED: {e}")

# === TEST 2: Plate Reader (heuristic + EasyOCR) ===
print("\n=== TEST 2: Plate Reader ===")
try:
    from core.plate_reader import read_plate, _heuristic_plate_crop, _run_ocr
    from core.model_registry import ModelRegistry

    # Test heuristic crop
    plate_crop = _heuristic_plate_crop(crop)
    if plate_crop is not None:
        print(f"  Heuristic plate crop shape: {plate_crop.shape}")
    else:
        print("  Heuristic crop returned None")

    # Test EasyOCR directly
    reg = ModelRegistry()
    reader = reg.get_ocr_reader()
    if reader is None:
        print("  EasyOCR: FAILED TO LOAD")
    else:
        print("  EasyOCR: LOADED OK")
        if plate_crop is not None:
            ocr_results = reader.readtext(plate_crop, detail=0, paragraph=True,
                                          allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789- ")
            print(f"  Raw OCR results: {ocr_results}")

    # Test full pipeline
    plate = read_plate(crop)
    print(f'  Full pipeline result: "{plate}"')
except Exception as e:
    import traceback
    print(f"  FAILED: {e}")
    traceback.print_exc()

# === TEST 3: CLIP DMS ===
print("\n=== TEST 3: Driver Monitor (CLIP) ===")
try:
    from core.driver_monitor import analyze_driver
    status = analyze_driver(crop)
    print(f'  Result: "{status}"')
except Exception as e:
    print(f"  FAILED: {e}")

# === TEST 4: Check dispatch timing ===
print("\n=== TEST 4: Dispatch timing check ===")
from core.traffic_analyzer import TrafficAnalyzer
analyzer = TrafficAnalyzer()
tid = 1
# Simulate 20 frames with same bbox area
for i in range(20):
    area = 85000
    should = analyzer.should_dispatch_plate(tid, area, i)
    if should:
        print(f"  Plate dispatch triggered at frame {i}")
        break
else:
    # Now simulate area decreasing
    for i in range(20, 50):
        area = 80000  # Smaller than peak
        should = analyzer.should_dispatch_plate(tid, area, i)
        if should:
            print(f"  Plate dispatch triggered at frame {i} (after peak at frame 19)")
            break
    else:
        print("  Plate dispatch NOT triggered in 50 frames!")

print("\n=== ALL TESTS COMPLETE ===")

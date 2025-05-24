from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import cv2
import numpy as np
import pandas as pd
from ultralytics import YOLO

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

yolo_model = YOLO('models/yolo11n-pose.pt')
WINDOW_SIZE = 60

selected_keypoints = {
    "left_shoulder": 5,
    "right_shoulder": 6,
    "left_elbow": 7,
    "right_elbow": 8,
    "left_hip": 11,
    "right_hip": 12,
    "left_knee": 13,
    "right_knee": 14
}

def create_empty_data_structure():
    return {
        f"{key}_confidences": [] for key in selected_keypoints
    }

@app.route('/process_videos', methods=['POST'])
def process_videos():
    if 'videos' not in request.files:
        return jsonify({"error": "Missing 'videos' in request"}), 400

    files = request.files.getlist('videos')
    video_paths = []

    for f in files:
        filename = f.filename
        path = os.path.join(UPLOAD_FOLDER, filename)
        f.save(path)
        video_paths.append(path)

    dataset = []
    for video_index, video_path in enumerate(video_paths):
        video_id = video_index + 1
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            continue

        frame_index = 0
        window_data = {0: create_empty_data_structure()}

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            current_window = frame_index // WINDOW_SIZE
            if current_window not in window_data:
                window_data[current_window] = create_empty_data_structure()

            height, width, _ = frame.shape
            results = yolo_model(frame)

            if len(results[0].keypoints) == 0:
                frame_index += 1
                continue

            keypoints = results[0].keypoints.data[0].cpu().numpy()
            keypoints[:, 0] *= width
            keypoints[:, 1] *= height

            data_entry = {
                "video_id": video_id,
                "frame": frame_index,
                "window_id": current_window
            }

            for name, idx in selected_keypoints.items():
                if idx >= len(keypoints):
                    continue
                x, y, conf = keypoints[idx]
                x_norm, y_norm = x / width, y / height
                data_entry[f"{name}_x"] = x_norm
                data_entry[f"{name}_y"] = y_norm
                data_entry[f"{name}_conf"] = float(conf)
                window_data[current_window][f"{name}_confidences"].append(float(conf))

            dataset.append(data_entry)
            frame_index += 1

        cap.release()

    df = pd.DataFrame(dataset)
    df.to_csv("movenet_motion_dataset_with_window_scores.csv", index=False, encoding="utf-8-sig")

    return jsonify({
        "message": "Processing completed",
        "frames_processed": len(dataset),
        "csv_file": "movenet_motion_dataset_with_window_scores.csv"
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)

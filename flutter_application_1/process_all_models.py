
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import threading
import time
import cv2
import numpy as np
import pandas as pd
import tensorflow as tf
from ultralytics import YOLO
import mediapipe as mp

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def process_movenet(video_path):
    interpreter = tf.lite.Interpreter(model_path="models/thunder3.tflite")
    interpreter.allocate_tensors()

    selected_keypoints = [5, 6, 7, 8, 11, 12, 13, 14]
    MIN_X, MAX_X = -1, 1
    MIN_Y, MAX_Y = -1, 1
    WINDOW_SIZE = 60
    dataset = []

    cap = cv2.VideoCapture(video_path)
    frame_index = 0
    video_id = 1
    current_window_index = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        input_tensor = cv2.resize(frame, (256, 256))
        input_tensor = np.expand_dims(input_tensor.astype(np.float32), axis=0)
        interpreter.set_tensor(interpreter.get_input_details()[0]['index'], input_tensor)
        interpreter.invoke()
        keypoints_with_scores = interpreter.get_tensor(interpreter.get_output_details()[0]['index'])
        keypoints = keypoints_with_scores[0, 0, :, :2]
        scores = keypoints_with_scores[0, 0, :, 2]

        height, width, _ = frame.shape
        keypoints *= [width, height]
        current_time = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0

        data_entry = {
            "video_id": video_id,
            "frame": frame_index,
            "window_index": current_window_index
        }

        for i in selected_keypoints:
            point = keypoints[i]
            score = scores[i]
            norm_x = (point[0] - MIN_X) / (MAX_X - MIN_X)
            norm_y = (point[1] - MIN_Y) / (MAX_Y - MIN_Y)
            data_entry[f"keypoint_{i}_x"] = norm_x
            data_entry[f"keypoint_{i}_y"] = norm_y
            data_entry[f"keypoint_{i}_confidence"] = score

        dataset.append(data_entry)
        frame_index += 1

    cap.release()
    df = pd.DataFrame(dataset)
    df.to_csv("movenet_motion_dataset_with_window_scores.csv", index=False)
    print("✔ MoveNet: done.")

def process_yolo(video_path):
    model = YOLO('models/yolo11n-pose.pt')
    WINDOW_SIZE = 60
    dataset = []

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

    cap = cv2.VideoCapture(video_path)
    frame_index = 0
    video_id = 1

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        height, width, _ = frame.shape
        results = model(frame)

        if len(results[0].keypoints) == 0:
            frame_index += 1
            continue

        keypoints = results[0].keypoints.data[0].cpu().numpy()
        keypoints[:, 0] *= width
        keypoints[:, 1] *= height

        data_entry = {
            "video_id": video_id,
            "frame": frame_index,
            "window_id": frame_index // WINDOW_SIZE
        }

        for name, idx in selected_keypoints.items():
            if idx >= len(keypoints):
                continue
            x, y, conf = keypoints[idx]
            data_entry[f"{name}_x"] = x / width
            data_entry[f"{name}_y"] = y / height
            data_entry[f"{name}_conf"] = float(conf)

        dataset.append(data_entry)
        frame_index += 1

    cap.release()
    df = pd.DataFrame(dataset)
    df.to_csv("yolo_motion_dataset_with_window_scores.csv", index=False, encoding="utf-8-sig")
    print("✔ YOLO: done.")

def process_mediapipe(video_path):
    pose = mp.solutions.pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)

    selected_keypoints = [11, 12, 13, 14, 23, 24, 25, 26]
    MIN_X, MAX_X = -1, 1
    MIN_Y, MAX_Y = -1, 1
    dataset = []

    cap = cv2.VideoCapture(video_path)
    frame_index = 0
    chunk_index = 0
    video_id = 1
    FRAMES_PER_CHUNK = 60

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        if frame_index > 0 and frame_index % FRAMES_PER_CHUNK == 0:
            chunk_index += 1

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(frame_rgb)

        if results.pose_landmarks:
            height, width, _ = frame.shape
            keypoints = results.pose_landmarks.landmark
            current_keypoints = [[kp.x * width, kp.y * height] for kp in keypoints]
            current_scores = [kp.visibility for kp in keypoints]

            data_entry = {
                "video_id": video_id,
                "frame": frame_index,
                "chunk_index": chunk_index
            }

            for i in selected_keypoints:
                point = current_keypoints[i]
                score = current_scores[i]
                norm_x = (point[0] - MIN_X) / (MAX_X - MIN_X)
                norm_y = (point[1] - MIN_Y) / (MAX_Y - MIN_Y)
                data_entry[f"keypoint_{i}_x"] = norm_x
                data_entry[f"keypoint_{i}_y"] = norm_y
                data_entry[f"keypoint_{i}_confidence"] = score

            dataset.append(data_entry)

        frame_index += 1

    cap.release()
    df = pd.DataFrame(dataset)
    df.to_csv("mediapipe_motion_dataset_with_windows_scores.csv", index=False)
    print("✔ MediaPipe: done.")

@app.route('/upload', methods=['POST'])
def upload_and_process():
    if 'file' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400

    video = request.files['file']
    if video.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    video_path = os.path.join(UPLOAD_FOLDER, video.filename)
    video.save(video_path)

    process_movenet(video_path)
    process_yolo(video_path)
    process_mediapipe(video_path)

    return jsonify({
        'message': 'Video processed by all models',
        'csv_outputs': [
            "movenet_motion_dataset_with_window_scores.csv",
            "yolo_motion_dataset_with_window_scores.csv",
            "mediapipe_motion_dataset_with_windows_scores.csv"
        ]
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050)

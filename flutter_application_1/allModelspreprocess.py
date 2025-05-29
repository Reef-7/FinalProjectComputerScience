from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import cv2
import numpy as np
import pandas as pd
import tensorflow as tf
import mediapipe as mp
from ultralytics import YOLO

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

WINDOW_SIZE = 60

# ---------- MoveNet ----------
def process_movenet(video_path):
    interpreter = tf.lite.Interpreter(model_path="models/thunder3.tflite")
    interpreter.allocate_tensors()
    selected_keypoints = [5, 6, 7, 8, 11, 12, 13, 14]
    MIN_X, MAX_X = -1, 1
    MIN_Y, MAX_Y = -1, 1
    dataset = []
    video_id = 1
    cap = cv2.VideoCapture(video_path)
    frame_index = 0
    current_window_index = 0

    def normalize(value, min_val, max_val):
        return (value - min_val) / (max_val - min_val)

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
        keypoints = keypoints * np.array([width, height])

        data_entry = {
            "video_id": video_id,
            "frame": frame_index,
            "window_index": frame_index // WINDOW_SIZE
        }

        for i in selected_keypoints:
            x, y = keypoints[i]
            data_entry[f"keypoint_{i}_x"] = normalize(x, MIN_X, MAX_X)
            data_entry[f"keypoint_{i}_y"] = normalize(y, MIN_Y, MAX_Y)
            data_entry[f"keypoint_{i}_confidence"] = scores[i]

        dataset.append(data_entry)
        frame_index += 1

    cap.release()
    df = pd.DataFrame(dataset)
    output_csv = "movenet_motion_dataset_with_window_scores.csv"
    df.to_csv(output_csv, index=False)
    return output_csv

# ---------- YOLO ----------
def process_yolo(video_path):
    model = YOLO('models/yolo11n-pose.pt')
    selected_keypoints = {
        "left_shoulder": 5, "right_shoulder": 6, "left_elbow": 7, "right_elbow": 8,
        "left_hip": 11, "right_hip": 12, "left_knee": 13, "right_knee": 14
    }
    dataset = []
    video_id = 1
    cap = cv2.VideoCapture(video_path)
    frame_index = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        results = model(frame)
        if not results or len(results[0].keypoints) == 0:
            frame_index += 1
            continue

        keypoints = results[0].keypoints.data[0].cpu().numpy()
        height, width, _ = frame.shape
        keypoints[:, 0] *= width
        keypoints[:, 1] *= height

        data_entry = {
            "video_id": video_id,
            "frame": frame_index,
            "window_index": frame_index // WINDOW_SIZE
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
    output_csv = "yolo_motion_dataset_with_window_scores.csv"
    df.to_csv(output_csv, index=False, encoding="utf-8-sig")
    return output_csv

# ---------- MediaPipe ----------
def process_mediapipe(video_path):
    mp_pose = mp.solutions.pose
    pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
    selected_keypoints = [11, 12, 13, 14, 23, 24, 25, 26]
    MIN_X, MAX_X = -1, 1
    MIN_Y, MAX_Y = -1, 1
    dataset = []
    video_id = 1
    cap = cv2.VideoCapture(video_path)
    frame_index = 0

    def normalize(value, min_val, max_val):
        return (value - min_val) / (max_val - min_val)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(frame_rgb)

        if results.pose_landmarks:
            keypoints = results.pose_landmarks.landmark
            height, width, _ = frame.shape
            data_entry = {
                "video_id": video_id,
                "frame": frame_index,
                "window_index": frame_index // WINDOW_SIZE
            }

            for i in selected_keypoints:
                kp = keypoints[i]
                x = normalize(kp.x * width, MIN_X, MAX_X)
                y = normalize(kp.y * height, MIN_Y, MAX_Y)
                data_entry[f"keypoint_{i}_x"] = x
                data_entry[f"keypoint_{i}_y"] = y
                data_entry[f"keypoint_{i}_confidence"] = kp.visibility

            dataset.append(data_entry)
        frame_index += 1

    cap.release()
    df = pd.DataFrame(dataset)
    output_csv = "mediapipe_motion_dataset_with_window_scores.csv"
    df.to_csv(output_csv, index=False)
    return output_csv

# ---------- API Routes ----------
@app.route('/upload/<method>', methods=['POST'])
def upload_video(method):
    if 'file' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400

    video = request.files['file']
    if video.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    video_path = os.path.join(UPLOAD_FOLDER, video.filename)
    video.save(video_path)

    if method == "movenet":
        csv_path = process_movenet(video_path)
    elif method == "yolo":
        csv_path = process_yolo(video_path)
    elif method == "mediapipe":
        csv_path = process_mediapipe(video_path)
    else:
        return jsonify({'error': f'Invalid method: {method}'}), 400

    return jsonify({
        'message': f'Video processed using {method}',
        'csv_file': csv_path
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)


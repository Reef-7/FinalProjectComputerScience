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

    def normalize_data(value, min_val, max_val):
        return (value - min_val) / (max_val - min_val)

    selected_keypoints = [5, 6, 7, 8, 11, 12, 13, 14]
    MIN_X, MAX_X = -1, 1
    MIN_Y, MAX_Y = -1, 1
    WINDOW_SIZE = 60
    dataset = []

    video_id = 1  # כי זה וידאו אחד
    cap = cv2.VideoCapture(video_path)
    prev_keypoints = None
    prev_velocity = None
    prev_time = None
    frame_index = 0
    time_windows_data = {}
    current_window_index = 0

    time_windows_data[current_window_index] = {
        "start_frame": 0,
        "end_frame": WINDOW_SIZE - 1,
        "video_id": video_id,
        "left_shoulder_confidences": [],
        "right_shoulder_confidences": [],
        "left_elbow_confidences": [],
        "right_elbow_confidences": [],
        "left_hip_confidences": [],
        "right_hip_confidences": [],
        "left_knee_confidences": [],
        "right_knee_confidences": []
    }

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        if frame_index >= (current_window_index + 1) * WINDOW_SIZE:
            current_window_index += 1
            time_windows_data[current_window_index] = {
                "start_frame": current_window_index * WINDOW_SIZE,
                "end_frame": (current_window_index + 1) * WINDOW_SIZE - 1,
                "video_id": video_id,
                "left_shoulder_confidences": [],
                "right_shoulder_confidences": [],
                "left_elbow_confidences": [],
                "right_elbow_confidences": [],
                "left_hip_confidences": [],
                "right_hip_confidences": [],
                "left_knee_confidences": [],
                "right_knee_confidences": []
            }

        input_tensor = cv2.resize(frame, (256, 256))
        input_tensor = np.expand_dims(input_tensor.astype(np.float32), axis=0)

        interpreter.set_tensor(interpreter.get_input_details()[0]['index'], input_tensor)
        interpreter.invoke()
        keypoints_with_scores = interpreter.get_tensor(interpreter.get_output_details()[0]['index'])

        keypoints = keypoints_with_scores[0, 0, :, :2]
        scores = keypoints_with_scores[0, 0, :, 2]

        height, width, _ = frame.shape
        keypoints = keypoints * np.array([width, height])
        current_time = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0


        if prev_keypoints is not None and prev_time is not None:
            time_diff = current_time - prev_time

        data_entry = {
            "video_id": video_id,
            "frame": frame_index,
            "window_index": current_window_index
        }

        for i in selected_keypoints:
            point = keypoints[i]
            score = scores[i]
            norm_x = normalize_data(point[0], MIN_X, MAX_X)
            norm_y = normalize_data(point[1], MIN_Y, MAX_Y)
            data_entry[f"keypoint_{i}_x"] = norm_x
            data_entry[f"keypoint_{i}_y"] = norm_y
            data_entry[f"keypoint_{i}_confidence"] = score

            if i == 5:
                time_windows_data[current_window_index]["left_shoulder_confidences"].append(score)
            elif i == 6:
                time_windows_data[current_window_index]["right_shoulder_confidences"].append(score)
            elif i == 11:
                time_windows_data[current_window_index]["left_hip_confidences"].append(score)
            elif i == 12:
                time_windows_data[current_window_index]["right_hip_confidences"].append(score)

        dataset.append(data_entry)
        prev_keypoints = keypoints.copy()
        prev_time = current_time
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

    def normalize_data(value, min_val, max_val):
        return (value - min_val) / (max_val - min_val)

    def initialize_chunk_data():
        return {
            "left_shoulder_confidences": [],
            "right_shoulder_confidences": [],
            "left_elbow_confidences": [],
            "right_elbow_confidences": [],
            "left_hip_confidences": [],
            "right_hip_confidences": [],
            "left_knee_confidences": [],
            "right_knee_confidences": []
        }

    dataset = []
    selected_keypoints = [11, 12, 13, 14, 23, 24, 25, 26]
    MIN_X = -1
    MAX_X = 1
    MIN_Y = -1
    MAX_Y = 1
    FRAMES_PER_CHUNK = 60

    video_id = 1
    cap = cv2.VideoCapture(video_path)
    prev_keypoints = None
    prev_time = None
    frame_index = 0
    chunk_index = 0
    current_chunk_data = initialize_chunk_data()

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        if frame_index > 0 and frame_index % FRAMES_PER_CHUNK == 0:
            chunk_start = frame_index - FRAMES_PER_CHUNK
            chunk_end = frame_index - 1
            current_chunk_data = initialize_chunk_data()
            chunk_index += 1

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(frame_rgb)

        if results.pose_landmarks:
            height, width, _ = frame.shape
            keypoints = results.pose_landmarks.landmark

            current_keypoints = []
            current_scores = []
            for idx in range(len(keypoints)):
                kp = keypoints[idx]
                current_keypoints.append([kp.x * width, kp.y * height])
                current_scores.append(kp.visibility)

            current_keypoints = np.array(current_keypoints)
            current_scores = np.array(current_scores)
            current_time = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0

            data_entry = {
                "video_id": video_id,
                "frame": frame_index,
                "chunk_index": chunk_index
            }

            for i in selected_keypoints:
                point = current_keypoints[i]
                score = current_scores[i]
                norm_x = normalize_data(point[0], MIN_X, MAX_X)
                norm_y = normalize_data(point[1], MIN_Y, MAX_Y)
                data_entry[f"keypoint_{i}_x"] = norm_x
                data_entry[f"keypoint_{i}_y"] = norm_y
                data_entry[f"keypoint_{i}_confidence"] = score

                if i == 11:
                    current_chunk_data["left_shoulder_confidences"].append(score)
                elif i == 12:
                    current_chunk_data["right_shoulder_confidences"].append(score)
                elif i == 23:
                    current_chunk_data["left_hip_confidences"].append(score)
                elif i == 24:
                    current_chunk_data["right_hip_confidences"].append(score)

            dataset.append(data_entry)
            prev_keypoints = current_keypoints.copy()
            prev_time = current_time

        frame_index += 1

    if frame_index % FRAMES_PER_CHUNK != 0 and any(len(val) > 0 for val in current_chunk_data.values()):
        chunk_start = chunk_index * FRAMES_PER_CHUNK
        chunk_end = frame_index - 1

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


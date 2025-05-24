

from flask import Flask, request, jsonify
import os
import cv2
import numpy as np
import tensorflow as tf
import pandas as pd
from flask_cors import CORS
from sklearn.preprocessing import MinMaxScaler
import pickle
import joblib
from sklearn.preprocessing import LabelEncoder

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def process_video(video_path):
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
    df.to_csv("movenet_motion_dataset_with_window_scores.csv", index=False)
    print("File: movenet_motion_dataset_with_window_scores.csv was saved")



@app.route('/upload', methods=['POST'])
def upload_video():
    if 'file' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400

    video = request.files['file']
    if video.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    video_path = os.path.join(UPLOAD_FOLDER, video.filename)
    video.save(video_path)

    process_video(video_path)
    return jsonify({'message': 'Video processed successfully', 'filename': video.filename}), 200
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
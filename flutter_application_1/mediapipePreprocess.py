import cv2
import numpy as np
import pandas as pd
import os
import mediapipe as mp
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

mp_pose = mp.solutions.pose
pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)

def process_video(video_path):
    import cv2
    import numpy as np
    import pandas as pd
    import os
    import mediapipe as mp

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
    df.to_csv("mediapipe_motion_dataset_with_windows_scores.csv", index=False)
    print(f"File: mediapipe_motion_dataset_with_windows_scores.csv was saved")
    return "mediapipe_motion_dataset_with_windows_scores.csv"


@app.route('/upload', methods=['POST'])
def upload_video():
    if 'file' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400

    video = request.files['file']
    if video.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    video_path = os.path.join(UPLOAD_FOLDER, video.filename)
    video.save(video_path)

    # עיבוד עם מודל המדיה־פייפ שלך
    output_csv = process_video(video_path)

    return jsonify({
        'message': 'Video processed successfully',
        'filename': video.filename,
        'csv_file': os.path.basename(output_csv)
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5004)
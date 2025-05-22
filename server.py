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

tflite_model_path = "thunder3.tflite"
interpreter = tf.lite.Interpreter(model_path=tflite_model_path)
interpreter.allocate_tensors()

# פונקציה לחישוב זווית בין שלוש נקודות
def calculate_angle(p1, p2, p3):
    v1 = np.array(p1) - np.array(p2)
    v2 = np.array(p3) - np.array(p2)
    angle = np.arccos(
        np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-6)
    )
    return np.degrees(angle)

def process_video(video_path):
    cap = cv2.VideoCapture(video_path)
    dataset = []
    frame_index = 0
    prev_keypoints, prev_velocity, prev_time = None, None, None

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        input_tensor = cv2.resize(frame, (256, 256))
        input_tensor = np.expand_dims(input_tensor.astype(np.float32), axis=0)
        
        interpreter.set_tensor(interpreter.get_input_details()[0]['index'], input_tensor)
        interpreter.invoke()
        keypoints_with_scores = interpreter.get_tensor(interpreter.get_output_details()[0]['index'])

        keypoints = keypoints_with_scores[0, 0, :, :2] * np.array([frame.shape[1], frame.shape[0]])
        scores = keypoints_with_scores[0, 0, :, 2]
        current_time = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0

        velocity, acceleration = None, None
        if prev_keypoints is not None and prev_time is not None:
            time_diff = current_time - prev_time
            if time_diff > 0:
                velocity = (keypoints - prev_keypoints) / time_diff
                if prev_velocity is not None:
                    acceleration = (velocity - prev_velocity) / time_diff

        angles = {
            13: ("left_knee_angle", calculate_angle(keypoints[11], keypoints[13], keypoints[15])),
            14: ("right_knee_angle", calculate_angle(keypoints[12], keypoints[14], keypoints[16])),
            7: ("left_elbow_angle", calculate_angle(keypoints[5], keypoints[7], keypoints[9])),
            8: ("right_elbow_angle", calculate_angle(keypoints[6], keypoints[8], keypoints[10]))
        }

        for i, (point, score) in enumerate(zip(keypoints, scores)):
            data_entry = {
                "video_id": video_path,
                "frame": frame_index,
                "keypoint_id": i,
                "x": point[0],
                "y": point[1],
                "confidence": score,
                "velocity_x": velocity[i][0] if velocity is not None else None,
                "velocity_y": velocity[i][1] if velocity is not None else None,
                "acceleration_x": acceleration[i][0] if acceleration is not None else None,
                "acceleration_y": acceleration[i][1] if acceleration is not None else None
            }
            if i in angles:
                angle_name, angle_value = angles[i]
                data_entry[angle_name] = angle_value
            dataset.append(data_entry)

        prev_keypoints, prev_velocity, prev_time = keypoints.copy(), velocity.copy() if velocity is not None else None, current_time
        frame_index += 1
    
    cap.release()
    df = pd.DataFrame(dataset)
    df.to_csv("motion_dataset.csv", index=False)
    return "motion_dataset.csv"

def process_motion_data():
    df = pd.read_csv("motion_dataset.csv")
    df.fillna(df.select_dtypes(include=[np.number]).mean(), inplace=True)
    stats_df = df.groupby("video_id").agg({
        'velocity_x': ['mean', 'std', 'min', 'max'],
        'velocity_y': ['mean', 'std', 'min', 'max'],
        'acceleration_x': ['mean', 'std', 'min', 'max'],
        'acceleration_y': ['mean', 'std', 'min', 'max'],
        'left_elbow_angle': ['mean', 'std', 'min', 'max'],
        'right_elbow_angle': ['mean', 'std', 'min', 'max'],
        'left_knee_angle': ['mean', 'std', 'min', 'max'],
        'right_knee_angle': ['mean', 'std', 'min', 'max']
    })
    stats_df.columns = ['_'.join(col).strip() for col in stats_df.columns.values]
    stats_df.reset_index(inplace=True)
    stats_df.to_csv("videos_motion_dataset.csv", index=False)
    return "videos_motion_dataset.csv"

def load_models():
    models = {
        "elbow_dt": joblib.load(open("elbow_model_dt.pkl", "rb")),
        "elbow_rf": joblib.load(open("elbow_model_rf.pkl", "rb")),
        "elbow_svc": joblib.load(open("elbow_model_svc.pkl", "rb")),
        "knee_dt": joblib.load(open("knee_model_dt.pkl", "rb")),
        "knee_rf": joblib.load(open("knee_model_rf.pkl", "rb")),
        "knee_svc": joblib.load(open("knee_model_svc.pkl", "rb")),
        "movement_dt": joblib.load(open("movement_score_model_dt.pkl", "rb")),
        "movement_rf": joblib.load(open("movement_score_model_rf.pkl", "rb")),
        "movement_svr": joblib.load(open("movement_score_model_svr.pkl", "rb"))
    }
    # הדפסת סוגי המודלים כדי לוודא שהם נטענים כראוי
    for name, model in models.items():
        print(f"Model {name}: {type(model)}")
    return models


def load_models_and_predict():
    models = load_models()
    df = pd.read_csv("videos_motion_dataset.csv")


    elbow_encoder = joblib.load('elbow_encoder.pkl')
    knee_encoder = joblib.load('knee_encoder.pkl')

    feature_cols = [
        'velocity_x_mean', 'velocity_x_std', 'velocity_x_min', 'velocity_x_max',
        'velocity_y_mean', 'velocity_y_std', 'velocity_y_min', 'velocity_y_max',
        'acceleration_x_mean', 'acceleration_x_std', 'acceleration_x_min', 'acceleration_x_max',
        'acceleration_y_mean', 'acceleration_y_std', 'acceleration_y_min', 'acceleration_y_max',
        'left_elbow_angle_mean', 'left_elbow_angle_std', 'left_elbow_angle_min', 'left_elbow_angle_max',
        'right_elbow_angle_mean', 'right_elbow_angle_std', 'right_elbow_angle_min', 'right_elbow_angle_max',
        'left_knee_angle_mean', 'left_knee_angle_std', 'left_knee_angle_min', 'left_knee_angle_max',
        'right_knee_angle_mean', 'right_knee_angle_std', 'right_knee_angle_min', 'right_knee_angle_max'
    ]

    # הדפסת חלק מהנתונים כדי לוודא שהפורמט תקין
    X = df[feature_cols]
    print("Data for prediction (first few rows):")
    print(X.head())

    try:
        # תחזיות של המודלים
        print("Making predictions with elbow_dt...")
        df["elbow_dt_pred"] = models["elbow_dt"].predict(X)
        print("elbow_dt prediction complete.")
        
        print("Making predictions with elbow_rf...")
        df["elbow_rf_pred"] = models["elbow_rf"].predict(X)
        print("elbow_rf prediction complete.")
        
        print("Making predictions with elbow_svc...")
        df["elbow_svc_pred"] = models["elbow_svc"].predict(X)
        print("elbow_svc prediction complete.")
        
        print("Making predictions with knee_dt...")
        df["knee_dt_pred"] = models["knee_dt"].predict(X)
        print("knee_dt prediction complete.")
        
        print("Making predictions with knee_rf...")
        df["knee_rf_pred"] = models["knee_rf"].predict(X)
        print("knee_rf prediction complete.")
        
        print("Making predictions with knee_svc...")
        df["knee_svc_pred"] = models["knee_svc"].predict(X)
        print("knee_svc prediction complete.")
        
        print("Making predictions with movement_dt...")
        df["movement_dt_pred"] = models["movement_dt"].predict(X)
        print("movement_dt prediction complete.")
        
        print("Making predictions with movement_rf...")
        df["movement_rf_pred"] = models["movement_rf"].predict(X)
        print("movement_rf prediction complete.")
        
        print("Making predictions with movement_svr...")
        df["movement_svr_pred"] = models["movement_svr"].predict(X)
        print("movement_svr prediction complete.")



        # שימוש ב-inverse_transform להחזיר את הערכים לטקסט
        df["elbow_dt_pred_text"] = elbow_encoder.inverse_transform(df["elbow_dt_pred"])
        df["elbow_rf_pred_text"] = elbow_encoder.inverse_transform(df["elbow_rf_pred"])
        df["elbow_svc_pred_text"] = elbow_encoder.inverse_transform(df["elbow_svc_pred"])
        df["knee_dt_pred_text"] = knee_encoder.inverse_transform(df["knee_dt_pred"])
        df["knee_rf_pred_text"] = knee_encoder.inverse_transform(df["knee_rf_pred"])
        df["knee_svc_pred_text"] = knee_encoder.inverse_transform(df["knee_svc_pred"])
        
    except AttributeError as e:
        print(f"Error during prediction: {e}")
        return "Error during prediction", 500

    df.to_csv("predictions.csv", index=False)
    print("Predictions saved to predictions.csv")
    return "predictions.csv"



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
    process_motion_data()
    result_file = load_models_and_predict()  # שימוש בפונקציה החדשה

    return jsonify({'message': 'Video processed and predicted successfully', 'processed_file': result_file}), 200

@app.route('/results', methods=['GET'])
def show_results():
    try:
        print("Attempting to read predictions.csv...")  # הוספת הדפסה לצורך ניפוי
        df = pd.read_csv("predictions.csv")
        results = df.to_dict(orient='records')
        print("Results loaded successfully!")  # אם הכל עובד
        return jsonify(results)
    except Exception as e:
        print(f"Error: {e}")  # הדפסת שגיאה במקרה של בעיה
        return jsonify({'error': str(e)}), 500
    
if __name__ == '__main__':
    app.run(debug=True)

from tensorflow.keras.models import load_model
import numpy as np
from scipy.stats import mode
import pandas as pd

from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/predict')
def predict():

    rmse_values = {
        'yolo': 0.7082,
        'movenet': 1.7612,
        'mediapipe': 0.9285
    }
    inv = {k: 1/v for k, v in rmse_values.items()}
    total = sum(inv.values())
    weights_motion = [inv['yolo']/total, inv['movenet']/total, inv['mediapipe']/total]


    model_yolo = load_model('models/best_yolo_infant_movement_model.keras')
    model_movenet = load_model('models/best_movenet_infant_movement_model.keras')
    model_mediapipe = load_model('models/best_mediapipe_infant_movement_model.keras')

    def predict_all_models(X_tests):
        preds = {}
        for name, model in {
            'yolo': model_yolo,
            'movenet': model_movenet,
            'mediapipe': model_mediapipe
        }.items():
            print(f"Running prediction for {name}")
            X_test = X_tests[name]  
            movement, knee_probs, elbow_probs = model.predict(X_test, verbose=0)
            preds[name] = {
                'movement': movement.squeeze(),
                'knee': np.argmax(knee_probs, axis=1),
                'elbow': np.argmax(elbow_probs, axis=1)
         }
        return preds

# Ensemble function
    def ensemble_predictions(preds, weights=None, vote_type='majority', class_weights=None):
        model_names = list(preds.keys())
        n_models = len(model_names)

    # Default: equal weights for regression models
        if weights is None:
            weights = np.ones(n_models) / n_models

    # Regression result: weighted average
        movement_preds = np.array([preds[m]['movement'] for m in model_names])
        movement_ensemble = np.average(movement_preds, axis=0, weights=weights)

    # Classification: majority or weighted voting
        knee_preds = np.array([preds[m]['knee'] for m in model_names])
        elbow_preds = np.array([preds[m]['elbow'] for m in model_names])

        if vote_type == 'majority':
            knee_ensemble = mode(knee_preds, axis=0).mode[0]
            elbow_ensemble = mode(elbow_preds, axis=0).mode[0]

        elif vote_type == 'weighted':
        # class_weights must be provided as dict with weights
            if class_weights is None:
                raise ValueError("class_weights required for weighted voting")

            w_knee = np.array([class_weights[m]['knee'] for m in model_names])
            w_elbow = np.array([class_weights[m]['elbow'] for m in model_names])

        # Weighted vote -> weighted sum > 0.5 -> 1
            knee_weighted = np.average(knee_preds, axis=0, weights=w_knee)
            elbow_weighted = np.average(elbow_preds, axis=0, weights=w_elbow)

            knee_ensemble = (knee_weighted > 0.5).astype(int)
            elbow_ensemble = (elbow_weighted > 0.5).astype(int)

        else:
            raise ValueError("vote_type must be either 'majority' or 'weighted'")

        return movement_ensemble, knee_ensemble, elbow_ensemble

    def run_ensemble_evaluation(X_test, y_true_movement, y_true_knee, y_true_elbow):
        preds = predict_all_models(X_test)
        movement_pred, knee_pred, elbow_pred = ensemble_predictions(preds, weights=weights_motion, vote_type='majority')
    
    df_yolo = pd.read_csv('test_yolo_dataset.csv')
    df_movenet = pd.read_csv('test_movenet_dataset.csv')
    df_mediapipe = pd.read_csv('test_mediapipe_dataset.csv')


    keys = ['video_id', 'frame', 'window_id']


    df_common = df_yolo[keys].merge(df_movenet[keys], on=keys).merge(df_mediapipe[keys], on=keys)

    print(f"df_yolo rows: {len(df_yolo)}")
    print(f"df_movenet rows: {len(df_movenet)}")
    print(f"df_mediapipe rows: {len(df_mediapipe)}")
    print(f"df_common rows after merge: {len(df_common)}")


    df_yolo_filtered = pd.merge(df_yolo, df_common, on=keys)
    df_movenet_filtered = pd.merge(df_movenet, df_common, on=keys)
    df_mediapipe_filtered = pd.merge(df_mediapipe, df_common, on=keys)


    feature_columns = [
     'left_shoulder_x', 'left_shoulder_y', 'left_shoulder_confidence',
     'right_shoulder_x', 'right_shoulder_y', 'right_shoulder_confidence',
     'left_elbow_x', 'left_elbow_y', 'left_elbow_confidence',
     'right_elbow_x', 'right_elbow_y', 'right_elbow_confidence',
     'left_hip_x', 'left_hip_y', 'left_hip_confidence',
     'right_hip_x', 'right_hip_y', 'right_hip_confidence',
     'left_knee_x', 'left_knee_y', 'left_knee_confidence',
     'right_knee_x', 'right_knee_y', 'right_knee_confidence'
    ]


    X_test_yolo = df_yolo_filtered[feature_columns].values
    X_test_movenet = df_movenet_filtered[feature_columns].values
    X_test_mediapipe = df_mediapipe_filtered[feature_columns].values


    TIMESTEPS = 30
    STEP = 30  # קפיצה של חלון שלם, בלי חפיפה
    def create_sequences_sampled(X, timesteps, step=STEP):
        sequences = []
        for i in range(0, len(X) - timesteps + 1, step):
            sequences.append(X[i:i+timesteps])
        return np.array(sequences)

    X_test_yolo_seq = create_sequences_sampled(X_test_yolo, TIMESTEPS, STEP)
    X_test_movenet_seq = create_sequences_sampled(X_test_movenet, TIMESTEPS, STEP)
    X_test_mediapipe_seq = create_sequences_sampled(X_test_mediapipe, TIMESTEPS, STEP)

    X_tests = {
        'yolo': X_test_yolo_seq,
        'movenet': X_test_movenet_seq,
        'mediapipe': X_test_mediapipe_seq
    }


    predictions = predict_all_models(X_tests)
    movement_pred, knee_pred, elbow_pred = ensemble_predictions(predictions, weights=weights_motion, vote_type='majority')


    df_common_seq = df_common.iloc[(TIMESTEPS - 1)::STEP].reset_index(drop=True)
    duplicates = df_common_seq[df_common_seq.duplicated(subset=['video_id', 'window_id'], keep=False)]
    df_common_seq = df_common_seq.drop_duplicates(subset=['video_id', 'window_id'], keep='first').reset_index(drop=True)


    df_preds = pd.DataFrame({
     'movement_prediction': movement_pred,
     'knee_prediction': knee_pred,
     'elbow_prediction': elbow_pred
    })

    df_output = pd.concat([df_common_seq, df_preds], axis=1)

    df_output = df_output.dropna(subset=['video_id', 'window_id', 'frame'])
    df_output = df_output.drop(columns=['frame'])

    df_output.to_csv('ensemble_predictions_with_ids.csv', index=False)

    print("predictions were saved to ensemble_predictions.csv")
    return jsonify(df_output.to_dict(orient='records'))


if __name__ == '__main__':
    app.run(debug=True)
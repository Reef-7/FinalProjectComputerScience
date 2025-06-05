import pandas as pd
import numpy as np

file_paths = ['mediapipe_motion_dataset_with_window_scores.csv', 
              'movenet_motion_dataset_with_window_scores.csv',
              'yolo_motion_dataset_with_window_scores.csv']


dfs = [pd.read_csv(path) for path in file_paths]


keypoint_map = {
    "left_shoulder": [("keypoint_5", "movenet"), ("keypoint_11", "mediapipe"), ("keypoint_5", "yolo")],
    "right_shoulder": [("keypoint_6", "movenet"), ("keypoint_12", "mediapipe"), ("keypoint_6", "yolo")],
    "left_elbow": [("keypoint_7", "movenet"), ("keypoint_13", "mediapipe"), ("keypoint_7", "yolo")],
    "right_elbow": [("keypoint_8", "movenet"), ("keypoint_14", "mediapipe"), ("keypoint_8", "yolo")],
    "left_hip": [("keypoint_11", "movenet"), ("keypoint_23", "mediapipe"), ("keypoint_11", "yolo")],
    "right_hip": [("keypoint_12", "movenet"), ("keypoint_24", "mediapipe"), ("keypoint_12", "yolo")],
    "left_knee": [("keypoint_13", "movenet"), ("keypoint_25", "mediapipe"), ("keypoint_13", "yolo")],
    "right_knee": [("keypoint_14", "movenet"), ("keypoint_26", "mediapipe"), ("keypoint_14", "yolo")]
}



def standardize_column_names(df, model_name):
    rename_dict = {}

    for joint_name, keypoints in keypoint_map.items():
        for keypoint_id, model in keypoints:
            if model == model_name:
                for suffix in ["x", "y", "confidence", "velocity_x", "velocity_y", "acceleration_x", "acceleration_y"]:
                    old_col = f"{keypoint_id}_{suffix}"
                    new_col = f"{joint_name}_{suffix}"
                    if old_col in df.columns:
                        rename_dict[old_col] = new_col

    angle_columns = {
        "left_elbow_angle": "angle_left_elbow",
        "right_elbow_angle": "angle_right_elbow",
        "left_knee_angle": "angle_left_knee",
        "right_knee_angle": "angle_right_knee"
    }
    for old_col, new_col in angle_columns.items():
        if old_col in df.columns:
            rename_dict[old_col] = new_col

    if "window_id" not in df.columns:
        if "window_index" in df.columns:
            rename_dict["window_index"] = "window_id"
        elif "chunk_index" in df.columns:
            rename_dict["chunk_index"] = "window_id"

    return df.rename(columns=rename_dict)

df_yolo = pd.read_csv("yolo_motion_dataset_with_window_scores.csv")
df_movenet = standardize_column_names(df_yolo, "yolo")

df_movenet = pd.read_csv("movenet_motion_dataset_with_window_scores.csv")
df_movenet = standardize_column_names(df_movenet, "movenet")


df_mediapipe = pd.read_csv("mediapipe_motion_dataset_with_window_scores.csv")
df_mediapipe = standardize_column_names(df_mediapipe, "mediapipe")

dfs = [df_yolo, df_movenet, df_mediapipe]

common_columns = set(dfs[0].columns)
for df in dfs[1:]:
    common_columns &= set(df.columns)

print("Common columns of all files:")
print(sorted(common_columns))

num_common_columns = len(common_columns)
total_columns = len(set(dfs[0].columns))

non_common_columns = {}
for i, df in enumerate(dfs):
    unique_columns = set(df.columns) - common_columns
    non_common_columns[f"File {i+1}"] = sorted(unique_columns)

print(f"\nNumber of common columns: {num_common_columns}/{total_columns} from the first file")

for file_key, unique_cols in non_common_columns.items():
    print(f"\nNon-common columns in {file_key}:")
    print(unique_cols)

column_map = {
    'left_shoulder_conf': 'left_shoulder_confidence',
    'right_shoulder_conf': 'right_shoulder_confidence',
    'left_elbow_conf': 'left_elbow_confidence',
    'right_elbow_conf': 'right_elbow_confidence',
    'left_knee_conf': 'left_knee_confidence',
    'right_knee_conf': 'right_knee_confidence',
    'left_hip_conf': 'left_hip_confidence',
    'right_hip_conf': 'right_hip_confidence',
}


dfs_standardized = []
for df in dfs:
    df = df.rename(columns=column_map)
    dfs_standardized.append(df)

common_columns_after = set(dfs_standardized[0].columns)
for df in dfs_standardized[1:]:
    common_columns_after &= set(df.columns)

print("Common columns after standardization:")
print(sorted(common_columns_after))

required_columns = {"window_id", "video_id"}
common_columns_after = set(dfs_standardized[0].columns)
for df in dfs_standardized[1:]:
    common_columns_after &= set(df.columns)

# נוודא שהעמודות הדרושות בפנים
common_columns_after |= required_columns  # מוסיף בכוח אם חסרות

# כעת ממשיכים כרגיל:
dfs_filtered = []
for df in dfs_standardized:
    existing_columns = [col for col in common_columns_after if col in df.columns]
    df_filtered = df[existing_columns]
    dfs_filtered.append(df_filtered)

output_file_paths = ['df_yolo_filtered.csv', 'df_movenet_filtered.csv', 'df_mediapipe_filtered.csv']
for df_filtered, output_path in zip(dfs_filtered, output_file_paths):
    print(f"Saving to {output_path}, columns: {df_filtered.columns.tolist()}")
    df_filtered.to_csv(output_path, index=False)
required_columns = {"window_id", "video_id"}
common_columns_after = set(dfs_standardized[0].columns)
for df in dfs_standardized[1:]:
    common_columns_after &= set(df.columns)

# נוודא שהעמודות הדרושות בפנים
common_columns_after |= required_columns  # מוסיף בכוח אם חסרות



# כעת ממשיכים כרגיל:
dfs_filtered = []
for df in dfs_standardized:
    if 'window_id' not in df.columns:
         # יוצרים עמודת window_id שבה כל 60 שורות מקבלות את אותו מספר
        df['window_id'] = (df.index // 60)

    df_filtered = df[list(common_columns_after)]
    dfs_filtered.append(df_filtered)

output_file_paths = ['df_yolo_filtered.csv', 'df_movenet_filtered.csv', 'df_mediapipe_filtered.csv']
for df_filtered, output_path in zip(dfs_filtered, output_file_paths):
    print(f"Saving to {output_path}, columns: {df_filtered.columns.tolist()}")
    df_filtered.to_csv(output_path, index=False)


def normalize_to_0_10_using_z(df, column_name):
    # חישוב ממוצע וסטיית תקן
    mean = df[column_name].mean()  # ממוצע הציונים
    std_dev = df[column_name].std()  # סטיית תקן
    
    # חישוב ה-Z-Score עבור כל הציונים
    z_scores = (df[column_name] - mean) / std_dev
    
    # חיתוך ערכים קיצוניים אם יש (למנוע השפעה לא נכונה של חריגים)
    z_scores_clipped = z_scores.clip(-2, 2)  # חיתוך ל-Z Score בטווח -2 עד 2
    
    # ממפים את ה-Z-Score לטווח 0-10 כך שהממוצע יהיה 5
    normalized_scores = (z_scores_clipped + 2) * 2.5  # מביא את הציונים לטווח 0-10
    return normalized_scores



# שמירה של התוצאות
output_file_paths = ['df_yolo_filtered.csv', 'df_movenet_filtered.csv', 'df_mediapipe_filtered.csv']
for df, output_path in zip(dfs, output_file_paths):
    df.to_csv(output_path, index=False)

file_paths = ['df_yolo_filtered.csv',
              'df_movenet_filtered.csv',
              'df_mediapipe_filtered.csv']


dfs = [pd.read_csv(path) for path in file_paths]
                                
common_columns = set(dfs[0].columns)  

for df in dfs[1:]:
    common_columns &= set(df.columns)  

print("common columns of all files:")
print(common_columns)

for df, path in zip(dfs, output_file_paths):
    df.to_csv(path, index=False)

file_paths = ['df_yolo_filtered.csv', 
              'df_movenet_filtered.csv',
              'df_mediapipe_filtered.csv']


dfs = [pd.read_csv(path) for path in file_paths]

columns_to_drop = df.columns[df.columns.str.contains('acceleration')]
for df in dfs:
    cols_in_df = [col for col in columns_to_drop if col in df.columns]
    df = df.drop(columns=cols_in_df)

df1, df2 = dfs[-2], dfs[-1]
columns_df1 = set(df1.columns)
columns_df2 = set(df2.columns)
common_columns = columns_df1 & columns_df2
all_columns = columns_df1 | columns_df2
non_shared_columns = all_columns - common_columns

df1, df2 = dfs[0], dfs[1]

columns_df1 = set(df1.columns)
columns_df2 = set(df2.columns)

common_columns = columns_df1 & columns_df2

only_in_df1 = columns_df1 - columns_df2

only_in_df2 = columns_df2 - columns_df1

df1.columns = df1.columns.str.replace('conf', 'confidence')


columns_df1 = set(df1.columns)
columns_df2 = set(df2.columns)

common_columns = columns_df1 & columns_df2

only_in_df1 = columns_df1 - columns_df2

only_in_df2 = columns_df2 - columns_df1

df1, df2,df3 = dfs[0], dfs[1],dfs[2]

df1 = df1.drop(columns={'right_shoulder_score', 'left_shoulder_score', 'right_hip_score', 'left_hip_score'} , errors='ignore')
df2 = df2.drop(columns={'left_elbow_acceleration_x', 'left_knee_acceleration_x', 'left_shoulder_acceleration_y', 'right_knee_acceleration_y', 'right_elbow_acceleration_y', 'right_elbow_acceleration_x', 'right_hip_acceleration_y', 'left_hip_acceleration_x', 'right_hip_acceleration_x', 'right_shoulder_acceleration_y', 'left_hip_acceleration_y', 'right_shoulder_acceleration_x', 'left_shoulder_acceleration_x', 'left_knee_acceleration_y', 'left_elbow_acceleration_y', 'right_knee_acceleration_x'}, errors='ignore')
df3 = df3.drop(columns={'left_elbow_acceleration_x', 'left_knee_acceleration_x', 'left_shoulder_acceleration_y', 'right_knee_acceleration_y', 'right_elbow_acceleration_y', 'right_elbow_acceleration_x', 'right_hip_acceleration_y', 'left_hip_acceleration_x', 'right_hip_acceleration_x', 'right_shoulder_acceleration_y', 'left_hip_acceleration_y', 'right_shoulder_acceleration_x', 'left_shoulder_acceleration_x', 'left_knee_acceleration_y', 'left_elbow_acceleration_y', 'right_knee_acceleration_x'}, errors='ignore')



unique_df1 = set(df1.columns) - set(df2.columns) - set(df3.columns)

unique_df2 = set(df2.columns) - set(df1.columns) - set(df3.columns)

unique_df3 = set(df3.columns) - set(df1.columns) - set(df2.columns)

df1 = df1.fillna(method='bfill')
df2 = df2.fillna(method='bfill')
df3 = df3.fillna(method='bfill')

df1.to_csv('test_yolo_dataset.csv', index=False)
df2.to_csv('test_movenet_dataset.csv', index=False)
df3.to_csv('test_mediapipe_dataset.csv', index=False)



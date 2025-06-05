import subprocess
import threading
import socket
from flask import Flask, request, jsonify
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


import time

'''
def wait_for_server(host, port, timeout=30):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.create_connection((host, port), timeout=2):
                print(f"Server on {host}:{port} is up.")
                return
        except OSError:
            time.sleep(1)
    raise TimeoutError(f"Server on {host}:{port} did not start within {timeout} seconds.")
'''

def wait_for_video(upload_folder, video_extensions=None):
    if video_extensions is None:
        video_extensions = ['.mp4', '.mov', '.avi', '.mkv'] 

    print("Waiting for a video file to appear in 'uploads' folder...")
    while True:
        files = os.listdir(upload_folder)
        video_files = [f for f in files if os.path.splitext(f)[1].lower() in video_extensions]
        if video_files:
            print(f"Found video file(s): {video_files}")
            break
        time.sleep(2)  #wait 2 seconds before checking again
'''
def wait_for_server(host, port, timeout=30):
    start = time.time()
    while True:
        try:
            with socket.create_connection((host, port), timeout=2):
                print(f"Server at {host}:{port} is ready.")
                return
        except OSError:
            if time.time() - start > timeout:
                raise TimeoutError(f"Server at {host}:{port} did not start within {timeout} seconds.")
            time.sleep(1)
'''


def wait_for_server(host, port, retry_interval=1):
    print(f"Waiting for server at {host}:{port} to become available...")
    while True:
        try:
            with socket.create_connection((host, port), timeout=2):
                print(f"✅ Server is up at {host}:{port}")
                return
        except (OSError, ConnectionRefusedError):
            print(f"⏳ Still waiting for server at {host}:{port}...")
            time.sleep(retry_interval)



def wait_for_file(directory, filename, timeout=60):
    """Wait until a specific file appears in a directory (or current directory)."""
    full_path = os.path.join(directory, filename) if directory else filename
    print(f"Waiting for file {filename} in {directory or 'current directory'}...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        if os.path.exists(full_path):
            print(f"Found file: {filename}")
            return
        time.sleep(1)
   

def run_script(script_name):
    
    print(f"Starting script: {script_name}")
    # Start the script as a subprocess without waiting (non-blocking)
    process = subprocess.Popen(["python", script_name])
    # Optionally, you can wait here if you want to block until this script finishes
    # process.wait()
    print(f"Script {script_name} is running with PID {process.pid}")

def run_main():
    '''
    # List of scripts to run in parallel (assumed independent)
    scripts_stage_1 = [
        "movenetPreprocess.py",
        "mediapipePreprocess.py",
        "yoloPreprocess.py"
    ]


    threads = []
    for script in scripts_stage_1:
        # Create and start a thread to run each script
        t = threading.Thread(target=run_script, args=(script,))
        t.start()
        threads.append(t)
    


    # Wait for all threads to start the subprocesses (not for the subprocesses themselves to finish)
    for t in threads:
        t.join()

    wait_for_server("127.0.0.1", 5002)
    wait_for_server("127.0.0.1", 5004)
    '''

    '''
    scripts_stage_1 = {
        "movenetPreprocess.py": 5000,
        "yoloPreprocess.py": 5002,
        "mediapipePreprocess.py": 5004
    }

    
    
    for script, port in scripts_stage_1.items():
        print(f"Running {script}...")
        subprocess.Popen(["python", script])
        wait_for_server("127.0.0.1", port)
        print(f"{script} is ready on port {port}.")
    '''

    
    '''
    scripts_stage_1 = [
        ("movenetPreprocess.py", 5000, "movenet_motion_dataset_with_window_scores.csv"),
        ("yoloPreprocess.py", 5002, "yolo_motion_dataset_with_window_scores.csv"),
        ("mediapipePreprocess.py", 5004, "mediapipe_motion_dataset_with_window_scores.csv")
    ]
    
    

    for script, port, output_file in scripts_stage_1:
        print(f"Running {script}...")

        
        process = subprocess.Popen(["python", script])

        
        wait_for_server("127.0.0.1", port)

        
        wait_for_file(".", output_file)

        
        process.terminate()
        try:
            process.wait(timeout=5)
            print(f"{script} terminated cleanly.")
        except subprocess.TimeoutExpired:
            process.kill()
            print(f"{script} forcefully killed.")



    print("Step 1 complete: All initial scripts have been started.")

    '''


    script = "allModelspreprocess.py"
    port = 5000

    print(f"Running {script}...")
    process = subprocess.Popen(["python", script])

    wait_for_server("127.0.0.1", port)

    expected_outputs = [
        "movenet_motion_dataset_with_window_scores.csv",
        "yolo_motion_dataset_with_window_scores.csv",
        "mediapipe_motion_dataset_with_window_scores.csv"
    ]

    for output_file in expected_outputs:
        wait_for_file(".", output_file)

    process.terminate()
    try:
        process.wait(timeout=5)
        print(f"{script} terminated cleanly.")
    except subprocess.TimeoutExpired:
        process.kill()
        print(f"{script} forcefully killed.")

    print("Step 1 complete: allModelspreprocess.py finished processing all models.")



    
    # Run further processing script - this will wait until it finishes
    print("Running additionalPreprocess.py...")
    subprocess.run(["python", "additionalPreprocess.py"])
    print("additionalPreprocess.py completed.")
    
    # Run the Flask server script (blocking call - will run until interrupted)
    print("Running ensambleModelRun.py (Flask server)...")
    process = subprocess.Popen(["python", "ensambleModelRun.py"])
    print(f"Flask server started with PID {process.pid}")

if __name__ == "__main__":
    run_main()  
    print("All preprocessing done. Starting server.")
    app.run(debug=False)  
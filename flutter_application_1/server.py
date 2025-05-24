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

def run_script(script_name):
    wait_for_video(UPLOAD_FOLDER)
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

    scripts_stage_1 = {
        "movenetPreprocess.py": 5000,
        "yoloPreprocess.py": 5002,
        "mediapipePreprocess.py": 5004
    }

    wait_for_video(UPLOAD_FOLDER)
    
    for script, port in scripts_stage_1.items():
        print(f"Running {script}...")
        subprocess.Popen(["python", script])
        wait_for_server("127.0.0.1", port)
        print(f"{script} is ready on port {port}.")

    print("Step 1 complete: All initial scripts have been started.")

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
    app.run(debug=True)  

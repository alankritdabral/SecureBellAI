# Refactored splitter.py

import cv2
import os
import subprocess
import math
import multiprocessing
import numpy as np
from tqdm import tqdm
# Import ONLY the functions that exist in the provided face_identification.py
# find_matches is crucial for the centralized recognition step
from face_identification import load_database, find_matches 
from functools import partial
from insightface.app import FaceAnalysis

# --- Constants (Defined in __main__ and passed to runn) ---
# For this refactor, constants are defined below and passed to runn or used globally.
# This structure assumes the constants are defined later in __main__
# -----------------------------------------------------------

def get_video_duration_and_fps(video_path):
    """Retrieves video duration and FPS."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video file: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    print(fps)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Duration is frame_count / fps. Use max(1, fps) to avoid division by zero if fps is 0
    duration = frame_count / max(1, fps)
    cap.release()
    return duration, fps

def split_video_ffmpeg(input_path, output_dir, segment_duration):
    """Split video using FFmpeg for speed (no re-encoding)."""
    os.makedirs(output_dir, exist_ok=True)
    
    duration, _ = get_video_duration_and_fps(input_path)
    # Ensure there is at least one segment
    num_segments = max(1, math.ceil(duration / segment_duration)) 
    segment_paths = []

    print(f"\n--- Splitting Configuration ---")
    print(f"Video Duration: {duration:.2f}s | Segment Duration: {segment_duration:.2f}s")
    print(f"Expected Segments: {num_segments}")
    print(f"--------------------------------\n")

    for i in range(num_segments):
        start_time = i * segment_duration
        # Output file name is used to determine segment number in face_identification.py
        output_file = os.path.join(output_dir, f"{i+1}.mp4")

        # Use -c copy for fast, lossless splitting (no re-encoding)
        command = [
            'ffmpeg',
            '-i', input_path,
            '-ss', str(start_time),
            '-t', str(segment_duration),
            '-c', 'copy',
            '-avoid_negative_ts', 'make_zero',
            '-y',
            output_file
        ]

        try:
            # Setting stdout and stderr to PIPE prevents FFmpeg spamming the console
            subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            segment_paths.append(output_file)
        except subprocess.CalledProcessError as e:
            # Decode stderr to get a useful error message from FFmpeg
            error_message = e.stderr.decode('utf-8', errors='ignore').strip()
            print(f"❌ FFmpeg split error (segment {i+1}): {error_message}")
            break
        except FileNotFoundError:
            print("❌ ERROR: FFmpeg not installed or not in PATH.")
            return []

    return segment_paths

def detect_faces_in_segment(segment_path, segment_index, fps, resize_factor):
    """
    Worker function for the multiprocessing pool.
    Initializes FaceAnalysis locally, processes each frame for face detection, 
    and returns a list of detected face observations.
    """
    print(f"[INFO] Worker started processing segment {segment_index}: {os.path.basename(segment_path)}")
    
    # Initialize FaceAnalysis inside the worker process (crucial for multiprocessing)
    app = FaceAnalysis(providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
    app.prepare(ctx_id=0, det_size=(640, 640))

    cap = cv2.VideoCapture(segment_path)
    if not cap.isOpened():
        print(f"[ERROR] Could not open segment: {segment_path}")
        return []

    # Get frame index offset to calculate the correct global_frame_number
    # Segment index is 1-based, start_frame_index will be 0, N, 2N, ...
    # Assumes consistent FPS across segments
    frames_per_segment = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Calculate the first global frame number of this segment
    # NOTE: This is an approximation/simplification. A better way would be 
    # to pass the true start_frame_number from the splitting logic.
    global_frame_offset = (segment_index - 1) * frames_per_segment
    
    detected_face_observations = []
    local_frame_count = 0
    scale = 1.0 / resize_factor # Scale factor for bounding boxes

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
            
        local_frame_count += 1
        global_frame_number = global_frame_offset + local_frame_count

        # Resize the frame down for faster processing
        small = cv2.resize(frame, (0, 0), fx=resize_factor, fy=resize_factor)
        faces = app.get(small)

        for face in faces:
            # Scale bounding box back to original frame size and convert to integer coordinates
            bbox = (face.bbox * scale).astype(int)
            
            # Store the essential data for later centralized recognition
            # The embedding must be stored as a list/bytes/string for safe multiprocessing transfer
            # We convert to list here.
            detected_face_observations.append({
                'global_frame_number': global_frame_number,
                'embedding': face.embedding.tolist(), # Convert numpy array to list
                'bbox': bbox.tolist()
                # We do NOT save the image here, only the data
            })
            
    cap.release()
    return detected_face_observations 

def runn(video_src, output_dir, db_dir, tolerance, resize_factor):
    """
    Main execution function to split a video, run face detection in parallel, 
    and then centralize face recognition.
    """
    if not os.path.exists(video_src):
        print(f"ERROR: Video not found: {video_src}")
        return

    # 1️⃣ Setup (Duration, Cores, Splitting)
    duration, fps = get_video_duration_and_fps(video_src)
    num_cores = multiprocessing.cpu_count()
    
    # Ensure segment duration is reasonable: minimum 1.0s, and aim for ~1 segment per core
    segment_duration = max(1.0, duration / num_cores) 

    print(f"[INFO] {num_cores} cores detected.")
    print(f"[INFO] Splitting into ~{num_cores} segments of ~{segment_duration:.2f}s each.")

    segment_files = split_video_ffmpeg(video_src, output_dir, segment_duration)
    if not segment_files:
        print("Video splitting failed. Exiting.")
        return

    print(f"\n✅ Created {len(segment_files)} video segments.")
    print("⚙️ Starting parallel face detection...")

    # 2️⃣ Parallel Face Detection and Aggregation
    # Prepare arguments for the partial function: fps and resize_factor
    # segment_path and segment_index will be passed by the pool
    partial_process = partial(detect_faces_in_segment, 
                              fps=fps, 
                              resize_factor=resize_factor)

    all_faces_data = []
    # Create an iterable of (segment_path, segment_index) pairs
    segment_tasks = [(path, i + 1) for i, path in enumerate(segment_files)]

    with multiprocessing.Pool(processes=num_cores) as pool:
        # pool.starmap is used because the worker function now expects two arguments: path and index
        segment_results = list(tqdm(pool.starmap(partial_process, segment_tasks),
                                    total=len(segment_tasks),
                                    desc="Detecting Faces in Segments"))

    # Aggregate all detected faces data into a single list
    for segment_face_list in segment_results:
        all_faces_data.extend(segment_face_list)
        
    total_faces_detected = len(all_faces_data)
    print(f"\n✅ Parallel detection complete. Total face observations detected: {total_faces_detected}")

    # 3️⃣ Face Recognition (Centralized)
    if total_faces_detected == 0:
        print("No faces detected, skipping recognition.")
        return

    # A single app instance is sufficient for database loading
    app_main = FaceAnalysis(providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
    app_main.prepare(ctx_id=0, det_size=(640, 640))

    try:
        # Pass the database directory and the main app instance
        db_embeddings, db_names = load_database(db_dir, app_main)
    except Exception as e:
        print(f"❌ Error loading database: {e}")
        return

    if db_embeddings.size == 0:
        print("[WARN] Database is empty. Skipping recognition.")
        return
        
    print("\n⚙️ Starting centralized face recognition...")
    
    recognized_faces = []
    for face_obs in tqdm(all_faces_data, desc="Centralized Face Recognition"):
        
        # Convert the embedding list back to a numpy array for processing
        query_embedding = np.array(face_obs['embedding'], dtype=np.float32)
        
        # Call the existing find_matches function
        name, sim = find_matches(db_embeddings, db_names, query_embedding, tolerance)
        
        # Store the final result
        recognized_faces.append({
            'global_frame_number': face_obs['global_frame_number'],
            'name': name,
            'similarity': sim, # Store as float
            'bbox': face_obs['bbox']
        })

    print(f"✅ Recognition complete. Identified {len(recognized_faces)} face observations.")
    
    # Display results summary
    print("\n--- Recognition Summary (First 5 Observations) ---")
    # Use slicing to safely get the first 5 elements
    for result in recognized_faces[:5]:
        # Format the similarity to 2 decimal places for display
        print(f"Frame {result['global_frame_number']}: {result['name']} (Sim: {result['similarity']:.2f})")
    print("--------------------------------------------------")

if __name__ == "__main__":
    # --- Configuration Constants ---
    DEFAULT_DB_DIR = "/home/aloo/Desktop/SecureBellAI/backend/visitors/verified/ALankrit"
    VIDEO_SRC = "/home/aloo/Desktop/SecureBellAI/suits.mp4"
    DEFAULT_TOLERANCE = 0.6
    RESIZE_FACTOR = 0.25
    OUTPUT_DIR = "video_segments"
    # -------------------------------

    runn(
        video_src=VIDEO_SRC,
        output_dir=OUTPUT_DIR,
        db_dir=DEFAULT_DB_DIR, # Using DEFAULT_DB_DIR for the database source
        tolerance=DEFAULT_TOLERANCE,
        resize_factor=RESIZE_FACTOR
    )
import os
import time
import json
import uuid
import math
import subprocess

import cv2
import numpy as np
from flask import (
    Flask, redirect, render_template, request, jsonify, url_for, 
    Response, stream_with_context, send_from_directory, abort, 
    Blueprint
)
from flask_cors import CORS
from werkzeug.utils import secure_filename # Recommended for security
import base64
import traceback # Added for better error logging

# --- Custom Imports (Assuming these modules exist) ---
from backend.db_helper import log_with_timestamp, insert_signup, search_login_credentials, get_all_details
from insightface.app import FaceAnalysis
# IMPORTANT: Added 'recognize_from_image' to imports
from face_identification import load_database, process_and_recognize_frame, DEFAULT_DB_DIR, DEFAULT_TOLERANCE 


app = Flask(__name__)
CORS(app)

# ---------- CONFIGURATION ----------
# Base directory for the application
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 1. UPLOAD Folder Config
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 2. PROCESSED Frame Output Config
OUTPUT_FRAME_DIR = os.path.join(BASE_DIR, 'processed_frames')
os.makedirs(OUTPUT_FRAME_DIR, exist_ok=True)
app.config['OUTPUT_FRAME_DIR'] = OUTPUT_FRAME_DIR

# 3. Processing Config
FRAME_SKIP = 30 # Process every 30th frame (to speed up demo)


# -------------------- GLOBAL STATE AND INITIALIZATION --------------------

# Global variables to store the initialized face analysis app and database
GLOBAL_APP = None
GLOBAL_DB_EMBEDDINGS = None
GLOBAL_DB_NAMES = None

# Global counter for unique naming of live stream frames
LIVE_FRAME_COUNTER = 0


def initialize_processing_env():
    """Initializes the InsightFace app and loads the face database."""
    global GLOBAL_APP, GLOBAL_DB_EMBEDDINGS, GLOBAL_DB_NAMES
    
    if GLOBAL_APP is None or GLOBAL_DB_EMBEDDINGS is None:
        print("[INIT] Initializing FaceAnalysis and loading database...")
        try:
            # Use CPU provider for broader compatibility in a server environment
            GLOBAL_APP = FaceAnalysis(providers=['CPUExecutionProvider'])
            # Prepare the model (det_size should match detection resolution)
            GLOBAL_APP.prepare(ctx_id=0, det_size=(640, 640))
        except Exception as e:
            print(f"[FATAL] InsightFace initialization failed: {e}")
            GLOBAL_APP = None
            return # Exit if model setup failed
        
        # Load the database
        GLOBAL_DB_EMBEDDINGS, GLOBAL_DB_NAMES = load_database(DEFAULT_DB_DIR, GLOBAL_APP)
        
        if GLOBAL_DB_EMBEDDINGS is None or GLOBAL_DB_EMBEDDINGS.size == 0:
            print("[WARN] No known faces loaded. All detections will be 'Unknown'.")
        
        print("[INIT] Initialization complete.")

# Call initialization once when the app starts
initialize_processing_env()

# -------------------- UTILITY FUNCTIONS --------------------

def get_video_duration_and_fps(video_path):
    """Calculates video duration and FPS using OpenCV."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video file: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    duration = frame_count / fps if fps > 0 else 0
    cap.release()
    return duration, fps


def split_video_ffmpeg(input_path, output_dir, segment_duration):
    """
    Split video using FFmpeg (copy codec for speed, no re-encoding).
    
    NOTE: This function is present in the provided code but appears unused 
    in the final `/analyze-video-stream` route, which uses a standard 
    OpenCV approach.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        duration, _ = get_video_duration_and_fps(input_path)
    except FileNotFoundError as e:
        print(f"❌ Error getting video info for splitting: {e}")
        return []

    # Ensure there is at least one segment
    num_segments = max(1, math.ceil(duration / segment_duration)) 
    segment_paths = []

    print(f"\n--- Splitting Configuration ---")
    print(f"Video Duration: {duration:.2f}s | Segment Duration: {segment_duration:.2f}s")
    print(f"Expected Segments: {num_segments}")
    print(f"--------------------------------\n")

    for i in range(num_segments):
        start_time = i * segment_duration
        output_file = os.path.join(output_dir, f"{i+1}.mp4")

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
            # Use PIPE to suppress FFmpeg output spamming the console
            subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            segment_paths.append(output_file)
        except subprocess.CalledProcessError as e:
            print(f"❌ FFmpeg split error (segment {i+1}): {e.stderr.decode('utf-8')}")
            break
        except FileNotFoundError:
            print("❌ ERROR: FFmpeg not installed or not in PATH.")
            return []

    return segment_paths


# -------------------- AUTHENTICATION ROUTES --------------------

@app.route("/", methods=["GET", "POST"])
def auth():
    """Handles the main sign-in/authentication page."""
    if request.method == "POST":
        # NOTE: This POST block is vestigial, login happens via API call.
        return redirect(url_for("home"))
    
    # NOTE: Requires 'index.html' template
    return render_template("index.html", page_title="Sign in to your account")


@app.route('/api/login', methods=['POST'])
def login():
    """Handles user sign-in requests via API."""
    try:
        data = request.get_json()   
        if not data:    
            return jsonify({'message': 'No input data provided'}), 400

        email = data.get('email')
        password = data.get('password')

        get_all_details() # Database interaction placeholder
        if search_login_credentials(email, password):
            return jsonify({'success': True}), 200

        return jsonify({'message': 'Invalid email or password. Please try again.'}), 401

    except Exception as e:
        print(f"Error during login: {e}")
        return jsonify({'message': 'An internal server error occurred'}), 500


@app.route('/api/signup', methods=['POST'])
def signup():
    """Handles user sign-up requests via API."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'message': 'No input data provided'}), 400
            
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')

        print(f"Sign Up attempt: username={username}, email={email}")

        if insert_signup(username, email, password):
            response_data = {'success': True}
        else:
            response_data = {'message': 'Error creating account. Please try again.'}
        return jsonify(response_data)

    except Exception as e:
        log_with_timestamp(f"Error in signup route: {e}")
        print(f"Error in signup route: {e}")
        return jsonify({'message': 'An error occurred during signup.'}), 500


@app.route('/api/forgot-password', methods=['POST'])
def forgot_password():
    """Handles forgot password requests (STUB)."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'message': 'No input data provided'}), 400
            
        email = data.get('email')
        print(f"Forgot Password request for: email={email}")

        # 🔹 STUB: Placeholder for actual password reset logic
        return jsonify({'message': f'If an account with {email} exists, a password reset link has been sent.'}), 200

    except Exception as e:
        print(f"Error during forgot password: {e}")
        return jsonify({'message': 'An internal server error occurred'}), 500


@app.route("/home")
def home():
    """Renders the dashboard page."""
    # NOTE: Requires 'home.html' template
    return render_template("home.html", page_title="Dashboard")


# -------------------- VIDEO UPLOAD & ANALYSIS ROUTES --------------------

@app.route('/upload-video', methods=['POST'])
def upload_video():
    """Handles video file upload and assigns a unique filename."""
    if 'video_file' not in request.files:
        return jsonify({
            "status": "error", 
            "message": "No file part in the request (Expected 'video_file')."
        }), 400

    file = request.files['video_file']

    if file.filename == '':
        return jsonify({
            "status": "error", 
            "message": "No selected file."
        }), 400

    if file:
        original_filename = secure_filename(file.filename)
        _, file_extension = os.path.splitext(original_filename)
        # Generate a unique filename using UUID and the original extension
        unique_filename = str(uuid.uuid4()) + file_extension
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        try:
            file.save(file_path)
        except Exception as e:
            print(f"File saving error: {e}")
            return jsonify({
                "status": "error", 
                "message": "Server failed to save the file."
            }), 500
        
        return jsonify({
            "status": "success",
            "message": f"File '{unique_filename}' uploaded successfully.",
            "filename": unique_filename # <--- Return the unique name
        }), 200

    return jsonify({
        "status": "error", 
        "message": "An unknown error occurred during upload."
    }), 500


@app.route('/processed-frames/<filename>')
def processed_frames(filename):
    """Serves the saved annotated frame images from the output directory."""
    try:
        return send_from_directory(app.config['OUTPUT_FRAME_DIR'], filename)
    except FileNotFoundError:
        abort(404)

@app.route('/analyze-video-stream', methods=['GET'])
def analyze_video_stream():
    """
    Server-Sent Events (SSE) endpoint for real-time video analysis streaming.
    """
    filename = request.args.get('filename')
    
    if not filename:
        return Response("data: {\"status\": \"error\", \"message\": \"Missing filename parameter\"}\n\n", mimetype='text/event-stream')

    uploaded_filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(uploaded_filepath):
        return Response(f"data: {{\"status\": \"error\", \"message\": \"Uploaded file {filename} not found on server.\"}}\n\n", mimetype='text/event-stream')

    # Ensure processing environment is ready
    if GLOBAL_APP is None or GLOBAL_DB_EMBEDDINGS is None:
        initialize_processing_env()
        
    if GLOBAL_APP is None:
        return Response("data: {\"status\": \"error\", \"message\": \"Model initialization failed.\"}\n\n", mimetype='text/event-stream')

    def event_stream(video_filepath, app_instance, db_embed, db_names):
        """
        The core generator function that processes the video frame-by-frame 
        and yields SSE messages.
        """
        cap = None
        frame_count = 0
        
        try:
            # 1. Video Initialization
            cap = cv2.VideoCapture(video_filepath)
            if not cap.isOpened():
                raise Exception("Failed to open video file with OpenCV.")
                
            fps = cap.get(cv2.CAP_PROP_FPS)

            # 2. Main Processing Loop
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_count += 1
                
                # Apply frame skipping for performance/demo
                if frame_count % FRAME_SKIP != 0:
                    continue
                
                start_time = time.time()

                # 3. Process and Recognize (The core logic)
                # NOTE: This function handles face detection, recognition, 
                # annotation, and saving the annotated frame image.
                recognition_data = process_and_recognize_frame(
                    frame, 
                    app_instance, 
                    db_embed, 
                    db_names, 
                    DEFAULT_TOLERANCE, 
                    frame_count,
                    app.config['OUTPUT_FRAME_DIR'],
                    fps
                )

                if recognition_data['faces']==None:
                    continue

                # 4. Create the JSON payload for the frontend
                payload = {
                    "status": "image_available", 
                    "frame_num": frame_count,
                    # Image filename is returned for the frontend to fetch the annotated image
                    "image_filename": recognition_data['image_filename'], 
                    "face_data": recognition_data['faces']
                }
                
                # 5. Yield the message in SSE format: data: JSON_STRING\n\n
                yield f"data: {json.dumps(payload)}\n\n"
                
                # Optional: Throttle stream to prevent overwhelming the client/server
                processing_time = time.time() - start_time
                wait_time = max(0, 0.05 - processing_time) # Target minimum 20 updates per second
                time.sleep(wait_time)


            # Send completion message
            completion_payload = {
                "status": "complete",
                "message": f"Successfully processed {frame_count} frames (skipping every {FRAME_SKIP})."
            }
            yield f"data: {json.dumps(completion_payload)}\n\n"

        except Exception as e:
            error_payload = {
                "status": "error",
                "message": f"Internal processing error: {str(e)}"
            }
            yield f"data: {json.dumps(error_payload)}\n\n"
        finally:
            if cap:
                cap.release()
            print(f"Analysis stream for {filename} finished. Total frames processed: {frame_count}")


    # Return the generator as a response with the correct MIME type for SSE
    return Response(
        stream_with_context(event_stream(uploaded_filepath, GLOBAL_APP, GLOBAL_DB_EMBEDDINGS, GLOBAL_DB_NAMES)),
        mimetype='text/event-stream'
    )


@app.route('/analyze-live-frame', methods=['POST'])
def analyze_live_frame():
    """
    Receives a single Base64-encoded frame from the client's webcam, 
    processes it using face recognition, and returns the processed image filename.
    """
    global LIVE_FRAME_COUNTER
    
    # Ensure processing environment is ready
    if GLOBAL_APP is None:
        initialize_processing_env()
        if GLOBAL_APP is None:
             return jsonify({"status": "error", "message": "Model initialization failed."}), 500

    try:
        data = request.get_json()
        base64_data = data.get('image_data')

        if not base64_data:
            return jsonify({"status": "error", "message": "No image_data provided"}), 400

        # 1. Decode Base64 string to binary image data
        image_binary = base64.b64decode(base64_data)
        
        # 2. Convert binary data to OpenCV image array (BGR format)
        nparr = np.frombuffer(image_binary, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            return jsonify({"status": "error", "message": "Failed to decode image from base64"}), 400

        # Increment frame counter for the live session. This creates unique IDs 
        # for sequential saving in the same directory as video frames.
        LIVE_FRAME_COUNTER += 1
        
        # 3. Process and Recognize (The core logic)
        # NOTE: We rely on process_and_recognize_frame to handle saving the file 
        # with a unique name based on the LIVE_FRAME_COUNTER.
        recognition_data = process_and_recognize_frame(
            frame, 
            GLOBAL_APP, 
            GLOBAL_DB_EMBEDDINGS, 
            GLOBAL_DB_NAMES, 
            DEFAULT_TOLERANCE, 
            LIVE_FRAME_COUNTER, 
            app.config['OUTPUT_FRAME_DIR']
        )
        
        # Check if the process returned valid data and the filename
        if recognition_data and 'image_filename' in recognition_data:
            return jsonify({
                "status": "success",
                "message": "Live frame processed successfully.",
                "image_filename": recognition_data['image_filename']
            }), 200
        else:
            # Handle cases where the frame was processed but failed to return expected data
            return jsonify({
                "status": "error", 
                "message": "Frame processed, but internal function failed to return expected output."
            }), 500

    except Exception as e:
        print(f"Error processing live frame: {e}")
        return jsonify({"status": "error", "message": f"An error occurred during live processing: {e}"}), 500


# -------------------- MISCELLANEOUS & BLUEPRINT ROUTES --------------------

@app.route("/visitors")
def visitors():
    """Render the visitors page (Stub)."""
    visitors_data = [
        {"name": "John Doe", "image": "https://i.pravatar.cc/300?u=john", "verified": True, "date": "2025-09-04", "time": "11:15"},
        {"name": "Jane Smith", "image": "https://i.pravatar.cc/300?u=jane", "verified": False, "date": "2025-09-04", "time": "12:00"},
    ]
    # NOTE: Requires 'visitors.html' template
    return render_template("visitors.html", visitors=visitors_data, page_title="Visitors")


# Define a Blueprint for API routes
bp = Blueprint('api', __name__) 

@bp.route("/api/face-id-login", methods=["POST"])
def face_id_login():
    """
    Face ID login endpoint. Receives a base64 encoded image and attempts 
    to recognize a known user.
    """
    try:
        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({'success': False, 'message': 'No image data received'}), 400

        image_data_url = data['image']
        if ',' not in image_data_url:
            return jsonify({'success': False, 'message': 'Invalid image format'}), 400

        # Decode base64 image data
        _, encoded = image_data_url.split(',', 1)
        image_bytes = base64.b64decode(encoded)
        np_array = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
        if frame is None:
            return jsonify({'success': False, 'message': 'Failed to decode image data'}), 500

        # NOTE: Removed the inefficient cv2.imwrite call

        known_encodings = GLOBAL_DB_EMBEDDINGS
        known_names = GLOBAL_DB_NAMES
        
        if known_encodings is None or known_encodings.size == 0:
            return jsonify({'success': False, 'message': 'No valid face encodings found in database'}), 500

# -- PROPER RECOGNITION CALL FOR FACE ID LOGIN ---
        # NOTE: Using GLOBAL_APP for the InsightFace model
        result = process_and_recognize_frame(
            frame=frame,
            app=GLOBAL_APP, # <-- CORRECT: Use the global InsightFace app instance
            db_embeddings=known_encodings,
            db_names=known_names,
            threshold=DEFAULT_TOLERANCE, # Use the configured tolerance
            global_frame_number=1,
            output_dir=app.config['OUTPUT_FRAME_DIR']) # Use a valid output directory
        # ------------------------------------------------

        recognized_identities= result["faces"]
        if recognized_identities:
            print(f"[SUCCESS] Face recognized: {recognized_identities}")
            # Authenticate the first identity found, and include all matches
            return jsonify({'success': True, 'identity': recognized_identities[0], 'all_matches': recognized_identities}), 200
        elif recognized_identities== None:
            print("[WARN] Face ID failed: No Face found.")
            return jsonify({'failure': True, 'message': 'Face ID failed. No Face found.'}), 401
        else:
            print("[WARN] Face ID failed: No match found.")
            return jsonify({'failure': True, 'message': 'Face ID failed. No match found or face is unknown.'}), 401

    except Exception as e:
        import traceback
        print(f"[ERROR] Face ID login failed: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Internal server error'}), 500
    
app.register_blueprint(bp)


# -------------------- MAIN EXECUTION --------------------

if __name__ == '__main__':
    print(f"Flask app running. Frame skip set to {FRAME_SKIP}.")
    # Host on 0.0.0.0 and port 80 for common deployment/access
    app.run(host="0.0.0.0", port=80, debug=True)

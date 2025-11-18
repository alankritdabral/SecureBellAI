import os
import cv2
import numpy as np
from insightface.app import FaceAnalysis

# --- Configuration for Streaming ---
# The database directory is now relative to the app execution
DEFAULT_DB_DIR = "/home/aloo/Desktop/SecureBellAI/backend/visitors/verified/ALankrit" 
DEFAULT_TOLERANCE = 0.4  # Similarity threshold for recognition (0.0 to 1.0)
ALLOWED_EXTENSIONS = (".png", ".jpg", ".jpeg")
RESIZE_FACTOR = 0.25 # Scale down for faster processing (25% size)

# -------------------- Utility Functions --------------------
def get_video_duration_and_fps(video_path):
    """Calculates video duration and FPS using OpenCV."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video file: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    cap.release()
    return frame_count, fps

def load_database(database_dir, app):
    """Loads known face images, extracts embeddings, and returns them."""
    known_embeddings, known_names = [], []
    print(f"[INFO] Loading database from: {database_dir}")
    
    # Ensure the directory exists before attempting to list files
    if not os.path.exists(database_dir):
        print(f"[WARN] Database directory '{database_dir}' not found. Recognition will not work.")
        return np.array([]), []

    for filename in os.listdir(database_dir):
        if not filename.lower().endswith(ALLOWED_EXTENSIONS):
            continue
        filepath = os.path.join(database_dir, filename)
        name = os.path.splitext(filename)[0]
        img = cv2.imread(filepath)
        if img is None:
            print(f"[WARN] Could not read {filename}")
            continue
            
        # Detect faces and get embeddings
        # InsightFace needs BGR input (which cv2.imread provides)
        faces = app.get(img) 
        
        if not faces:
            print(f"[WARN] No face found in {filename} in database.")
            continue
            
        # Assuming one face per database image for simplicity
        known_embeddings.append(faces[0].embedding)
        known_names.append(name)
        
    if not known_embeddings:
        print("[WARN] No valid embeddings found in database.")
        return np.array([]), []

    print(f"[INFO] Loaded {len(known_names)} known faces.")
    # Stack embeddings vertically for efficient numpy operations
    return np.vstack(known_embeddings), known_names

def find_matches(db_embeddings, db_names, query_embedding, threshold):
    """Finds the best match in the database for a query embedding using cosine similarity."""
    if db_embeddings.size == 0 or query_embedding.size == 0:
        return "Unknown", 0.0
    
    # Cosine similarity calculation (dot product of normalized vectors)
    # The embeddings from InsightFace are usually L2 normalized, but we re-normalize for robustness
    db_norm = db_embeddings / np.linalg.norm(db_embeddings, axis=1, keepdims=True)
    query_norm = query_embedding / np.linalg.norm(query_embedding)
    sims = np.dot(db_norm, query_norm)
    best_idx = np.argmax(sims)
    best_sim = sims[best_idx]
    
    # Return match if similarity is above threshold
    return (db_names[best_idx], float(best_sim)) if best_sim >= threshold else ("Unknown", float(best_sim))

def process_and_recognize_frame(frame, app, db_embeddings, db_names, threshold, global_frame_number, output_dir,fps=30):
    """
    Processes a single frame for face detection, extracts embeddings, performs recognition,
    draws bounding boxes, saves the annotated frame, and returns the result data.
    """
    # name = [] # Initialize to [] to satisfy your 'if (name == [])' check later
    # Prepare the output filename
    # NOTE: The format needs to ensure correct sorting in the frontend. 
    # frame_00001.jpg, frame_00010.jpg is correct.


    # 1. Face Detection and Feature Extraction
    # Resize the frame down for faster processing, which InsightFace detects on
    small = cv2.resize(frame, (0, 0), fx=RESIZE_FACTOR, fy=RESIZE_FACTOR)
    faces = app.get(small)
    duration= global_frame_number/fps
    image_filename = f"{duration:.2f} sec.jpg" 

    if faces != []:
        scale = 1.0 / RESIZE_FACTOR # Calculate scale factor to map back to original size

        recognition_results = []

        # Create a copy of the frame to draw on
        annotated_frame = frame.copy()

        for face in faces:
            # Scale bounding box back to original frame size and convert to integer coordinates
            bbox = (face.bbox * scale).astype(int)
            x1, y1, x2, y2 = bbox
            embedding = face.embedding

            # 2. Recognition
            # NOTE: The embedding needs to be a 1D array for find_matches
            name, sim = find_matches(db_embeddings, db_names, embedding, threshold)

            # image_filename = f"{name}{i}.jpg" 
            # filepath = os.path.join(output_dir, image_filename)

            # 4. Store result data
            recognition_results.append({
                'name': name,
                'similarity': f"{sim:.2f}",
                'bbox': bbox.tolist() # Convert numpy array to list for JSON serialization
            })

            # 5. Save the annotated frame
            if (name == "Unknown" ):
                filepath = os.path.join(output_dir, image_filename)
                cv2.imwrite(filepath, annotated_frame)
            else:
                image_filename = f"{duration:.2f} sec Identified {name}.jpg" 
                filepath = os.path.join(output_dir, image_filename)
                cv2.imwrite(filepath, annotated_frame)


            return {
                "image_filename": image_filename,
                "faces": recognition_results
            }
    
    # Return all recognition data and the filename of the saved frame
    return {
        "image_filename": image_filename,
        "faces": None
    }

if __name__ == "__main__":
    import argparse
    import json
    import time

    parser = argparse.ArgumentParser(description="Run real-time face recognition using InsightFace.")
    parser.add_argument("--source", type=str, default="0",
                        help="Video source. Use integer for camera index (default=0) or path to video file.")
    parser.add_argument("--db_dir", type=str, default=DEFAULT_DB_DIR,
                        help=f"Directory with known face images (default={DEFAULT_DB_DIR}).")
    parser.add_argument("--output_dir", type=str, default="output_frames",
                        help="Directory where annotated frames will be saved.")
    parser.add_argument("--threshold", type=float, default=DEFAULT_TOLERANCE,
                        help=f"Similarity threshold for recognition (default={DEFAULT_TOLERANCE}).")
    parser.add_argument("--display", action="store_true",
                        help="Show annotated frames in a window (useful for debugging).")
    parser.add_argument("--device", type=str, default="cpu",
                        help="Device for InsightFace: 'cpu' or 'gpu' (if supported).")
    parser.add_argument("--max-frames", type=int, default=0,
                        help="If >0, stop after processing this many frames.")
    args = parser.parse_args()

    # Normalize source (camera index if integer-like)
    try:
        source = int(args.source)
    except Exception:
        source = args.source

    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)

    # Initialize InsightFace FaceAnalysis
    print(f"[INFO] Initializing InsightFace on device='{args.device}' ...")
    if args.device.lower() == "cpu":
        ctx_id = -1
    else:
        # GPU device id 0 by default; change if needed
        ctx_id = 0

    app = FaceAnalysis()  # default constructor; can pass name or allowed_modules if desired
    try:
        # det_size chooses detection input size. Adjust depending on speed/accuracy needs.
        app.prepare(ctx_id=ctx_id, det_size=(640, 640))
    except Exception as e:
        print(f"[WARN] app.prepare failed with: {e}. Trying prepare with default params.")
        app.prepare(ctx_id=ctx_id)

    # Load known faces database
    db_embeddings, db_names = load_database(args.db_dir, app)

    # Open video source
    print(f"[INFO] Opening video source: {source}")
    cap = cv2.VideoCapture("/home/aloo/Desktop/SecureBellAI/suits.mp4")
    if not cap.isOpened():
        raise RuntimeError(f"Unable to open video source: {source}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    global_frame_number = 1
    processed_frames = 0
    start_time = time.time()

    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                print("[INFO] End of video stream or failed to read frame.")
                break
            if global_frame_number % fps == 0:
                result = process_and_recognize_frame(
                    frame=frame,
                    app=app,
                    db_embeddings=db_embeddings,
                    db_names=db_names,
                    threshold=args.threshold,
                    global_frame_number=global_frame_number,
                    output_dir=args.output_dir,
                    fps=fps
                    )
                # Print a short summary to stdout
                print(f"[FRAME {global_frame_number}] {json.dumps(result, ensure_ascii=False)}")

                # Optionally display the saved annotated image
                if args.display:
                    filepath = os.path.join(args.output_dir, result["image_filename"])
                    img = cv2.imread(filepath)
                    if img is not None:
                        cv2.imshow("Annotated", img)
                        # Wait 1 ms; press 'q' to quit early
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            print("[INFO] Quit requested by user.")
                            break

            global_frame_number += 1
            processed_frames += 1

            if args.max_frames > 0 and processed_frames >= args.max_frames:
                print(f"[INFO] Reached max frames: {args.max_frames}")
                break

    except KeyboardInterrupt:
        print("[INFO] Interrupted by user.")
    finally:
        cap.release()
        if args.display:
            cv2.destroyAllWindows()
        elapsed = time.time() - start_time
        fps = processed_frames / elapsed if elapsed > 0 else 0.0
        print(f"[INFO] Done. Processed {processed_frames} frames in {elapsed:.2f}s ({fps:.2f} FPS).")

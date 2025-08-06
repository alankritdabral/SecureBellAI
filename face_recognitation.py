import os
import cv2
import face_recognition

def load_database(database_dir):
    known_encodings, known_names = [], []
    for filename in os.listdir(database_dir):
        if not filename.lower().endswith((".png", ".jpg", ".jpeg")):
            continue
        filepath = os.path.join(database_dir, filename)
        name, _ = os.path.splitext(filename)
        image = face_recognition.load_image_file(filepath)
        face_locations = face_recognition.face_locations(image)
        if not face_locations:
            print(f"[WARNING] No face in '{filename}'. Skipping.")
            continue
        face_encoding = face_recognition.face_encodings(image, face_locations)[0]
        known_encodings.append(face_encoding)
        known_names.append(name)
    return known_encodings, known_names

def recognize_faces(image, known_encodings, known_names, tolerance=0.6):
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    face_locations = face_recognition.face_locations(rgb_image)
    face_encodings = face_recognition.face_encodings(rgb_image, face_locations)
    results = []
    for face_encoding in face_encodings:
        distances = face_recognition.face_distance(known_encodings, face_encoding)
        match_name = known_names[distances.argmin()] if distances.min() <= tolerance else "Unknown"
        results.append(match_name)
    return results

def recognize_from_image(query_image_path, known_encodings, known_names):
    image = cv2.imread(query_image_path)
    if image is None:
        raise FileNotFoundError(f"Unable to load image '{query_image_path}'.")
    results = recognize_faces(image, known_encodings, known_names)
    return results

def recognize_from_camera(known_encodings, known_names, tolerance=0.6):
    video_capture = cv2.VideoCapture(0)
    if not video_capture.isOpened():
        raise RuntimeError("Unable to access the webcam.")
    print("[INFO] Press 'q' to quit.")
    while True:
        ret, frame = video_capture.read()
        if not ret:
            break
        results = recognize_faces(frame, known_encodings, known_names, tolerance)
        for name in results:
            print(f"Detected: {name}")
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    video_capture.release()
    cv2.destroyAllWindows()

def main(database_dir="visitors/old", query_image_path="visitors/new/query.jpg", use_camera=False):
    if not os.path.isdir(database_dir):
        raise FileNotFoundError(f"Database folder '{database_dir}' not found.")
    known_encodings, known_names = load_database(database_dir)
    if not known_encodings:
        raise ValueError("No valid face encodings found in the database.")
    if use_camera:
        recognize_from_camera(known_encodings, known_names)
    elif query_image_path:
        results = recognize_from_image(query_image_path, known_encodings, known_names)
        for name in results:
            print(f"Detected: {name}")
    else:
        raise ValueError("Either a query image path or camera mode must be specified.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        # Use default arguments if no command-line arguments are provided
        main()
    else:
        database_dir = sys.argv[1]
        query_image_path = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else None
        use_camera = "--camera" in sys.argv
        main(database_dir, query_image_path, use_camera)

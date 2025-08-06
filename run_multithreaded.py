import cv2
import time
import os
from object_detection import detectObject
from head_pose_estimation import get_head_pose
from eye_gaze_detection import initialize_face_mesh, process_frame as process_eye_frame
from face_recognitation import load_database, recognize_from_image  # Import face recognition functions
from datetime import datetime

class FaceRecognitionSystem:
    def __init__(self, database_dir="visitors/old"):
        self.face_mesh = initialize_face_mesh()
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.known_encodings, self.known_names = load_database(database_dir)
        self.cooldown_until = 0
        self.faces = []
        self.running = True

    def detect_faces(self, frame):
        """Perform face detection on a downscaled version of the frame."""
        small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)  # Reduce resolution
        gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
        return faces

    def log_with_timestamp(self, message):
        """Helper function to log messages with a timestamp."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open('report.txt', 'a') as file:
            file.write(f"[{timestamp}] {message}\n")

    def process_frame(self, frame):
        """Process a single frame for object detection, eye tracking, head pose estimation, and face recognition."""
        current_time = time.time()
        if current_time < self.cooldown_until:
            # Skip processing during cooldown
            return [], None

        detected_objects = detectObject(frame)
        person_count = len(detected_objects)
        head_pose = None  # Initialize to handle cases where it's not set


        if person_count == 1 and len(self.faces) > 0:
            frame, eye_pos = process_eye_frame(self.face_mesh, frame)
            head_pose = get_head_pose(frame, self.face_mesh)

            self.log_with_timestamp(f"Head pose: {head_pose}")

            if eye_pos and head_pose == "Center,Center":
                # Capture and save the image
                timestamp = time.strftime("%Y%m%d-%H%M%S")  # Generate a timestamp for the filename
                os.makedirs("recent", exist_ok=True)  # Ensure the directory exists
                filename = f"recent/captured_image_{timestamp}.jpg"
                cv2.imwrite(filename, frame)
                print(f"Image captured and saved as {filename}")

                # Perform face recognition on the captured image
                results = recognize_from_image(filename, self.known_encodings, self.known_names)
                print(f"Face recognition results: {results}")

                self.log_with_timestamp(f"Image captured: {filename}")
                self.log_with_timestamp(f"Face recognition results: {results}")

                self.cooldown_until = current_time + 30  # Set cooldown for 30 seconds

        return detected_objects, head_pose

    def run(self, video_source=0, display=False):
        cap = cv2.VideoCapture(video_source)
        if not cap.isOpened():
            self.log_with_timestamp("Error: Could not open video source.")
            print("Error: Could not open video source.")
            return

        frame_count = 0  # Counter to skip frames for face detection
        while self.running:
            ret, frame = cap.read()
            if not ret:
                self.log_with_timestamp("Error: Failed to read frame from video source.")
                break

            # Perform face detection every 5 frames
            if frame_count % 30 == 0:
                self.faces = self.detect_faces(frame)
                self.log_with_timestamp(f"Detected faces: {self.faces}")

            detected_objects, head_pose = self.process_frame(frame)

            if display:
                cv2.imshow("Processing", frame)

            # Exit condition (optional, if running in a loop)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                self.log_with_timestamp("User requested to quit the application.")
                break

            frame_count += 1

        cap.release()
        cv2.destroyAllWindows()
        self.log_with_timestamp("Video processing stopped.")


if __name__ == '__main__':
    system = FaceRecognitionSystem(database_dir="visitors/old")
    print("Running face recognition on video source...")
    system.run(video_source=0, display=True)
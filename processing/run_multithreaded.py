import cv2
import time
import os
from object_detection import detectObject
from head_pose_estimation import get_head_pose
from eye_gaze_detection import initialize_face_mesh, process_frame as process_eye_frame
from a3 import load_database, recognize_from_image
from backend.query import getdetails, detected_unknown, detected_known

class FaceRecognitionSystem:
    def __init__(self, database_dir="backend/visitors/verified"):
        self.face_mesh = initialize_face_mesh()
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.known_encodings, self.known_names = load_database(database_dir)
        self.cooldown_until = 0
        self.faces = []
        self.running = True

    def detect_faces(self, frame):
        """Perform face detection on a downscaled version of the frame."""
        small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
        gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
        return faces

    def process_frame(self, frame):
        """Process frame for detection and recognition."""
        current_time = time.time()
        if current_time < self.cooldown_until:
            return [], None

        detected_objects = detectObject(frame)
        person_count = len(detected_objects)
        head_pose = None

        if person_count == 1 and len(self.faces) > 0:
            frame, eye_pos = process_eye_frame(self.face_mesh, frame)
            head_pose = get_head_pose(frame, self.face_mesh)
            print(f"Head pose: {head_pose}")

            if eye_pos and head_pose == "Center,Center":
                timestamp = time.strftime("%Y%m%d-%H%M%S")
                os.makedirs("backend/recent_visitors", exist_ok=True)
                filename = f"backend/recent_visitors/captured_image_{timestamp}.jpg"
                cv2.imwrite(filename, frame)
                print(f"Image saved: {filename}")

                # Recognize visitor
                visitor_ids = recognize_from_image(filename, self.known_encodings, self.known_names)
                visitor_id = visitor_ids[0] if visitor_ids else "unknown"

                if visitor_id.lower() != "unknown":
                    results = getdetails(visitor_id)
                    print(f"Recognized visitor: {results}")
                    detected_known(visitor_id, filename)
                else:
                    filename = f"backend/visitors/verified/captured_image_{timestamp}.jpg"
                    cv2.imwrite(filename, frame)
                    print(f"Image saved: {filename}")
                    final_path = detected_unknown(filename)
                    print(f"Unknown visitor logged with image: {final_path}")

                self.cooldown_until = current_time + 30

        return detected_objects, head_pose

    def run(self, video_source=0, display=False):
        cap = cv2.VideoCapture(video_source)
        if not cap.isOpened():
            print("Error: Could not open video source.")
            return

        frame_count = 0
        while self.running:
            ret, frame = cap.read()
            if not ret:
                print("Error: Failed to read frame.")
                break

            if frame_count % 30 == 0:
                self.faces = self.detect_faces(frame)
                print(f"Detected faces: {self.faces}")

            detected_objects, head_pose = self.process_frame(frame)

            if display:
                cv2.imshow("Processing", frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("User requested quit.")
                break

            frame_count += 1

        cap.release()
        cv2.destroyAllWindows()
        print("Video stopped.")


if __name__ == '__main__':
    system = FaceRecognitionSystem(database_dir="backend/visitors/verified")
    print("Starting face recognition...")
    system.run(video_source=0, display=True)

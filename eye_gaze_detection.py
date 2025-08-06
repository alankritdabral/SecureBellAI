import cv2
import mediapipe as mp
import numpy as np

def initialize_face_mesh():
    """Initialize MediaPipe Face Mesh with iris refinement enabled."""
    mp_face_mesh = mp.solutions.face_mesh
    return mp_face_mesh.FaceMesh(
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )

def process_frame(face_mesh, frame):
    """Process a single frame to detect face landmarks and compute gaze direction."""
    h, w, _ = frame.shape
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb_frame)

    eye_pos = "Unknown,Unknown"  # Default value if no landmarks are detected

    if results.multi_face_landmarks:
        for face_landmarks in results.multi_face_landmarks:
            # --- IRIS DETECTION ---
            right_iris_idx = [469, 470, 471, 472]
            left_iris_idx = [474, 475, 476, 477]

            right_iris = np.array([[face_landmarks.landmark[i].x, face_landmarks.landmark[i].y] for i in right_iris_idx])
            left_iris = np.array([[face_landmarks.landmark[i].x, face_landmarks.landmark[i].y] for i in left_iris_idx])
            right_center = np.mean(right_iris, axis=0)
            left_center = np.mean(left_iris, axis=0)

            right_center_pix = (int(right_center[0] * w), int(right_center[1] * h))
            left_center_pix = (int(left_center[0] * w), int(left_center[1] * h))

            # --- GAZE ESTIMATION ---
            right_eye_outer = face_landmarks.landmark[33]
            right_eye_inner = face_landmarks.landmark[133]
            left_eye_outer = face_landmarks.landmark[362]
            left_eye_inner = face_landmarks.landmark[263]

            r_outer = np.array([right_eye_outer.x * w, right_eye_outer.y * h])
            r_inner = np.array([right_eye_inner.x * w, right_eye_inner.y * h])
            l_outer = np.array([left_eye_outer.x * w, left_eye_outer.y * h])
            l_inner = np.array([left_eye_inner.x * w, left_eye_inner.y * h])

            right_h_ratio = (right_center_pix[0] - r_outer[0]) / ((r_inner[0] - r_outer[0]) + 1e-6)
            left_h_ratio = (l_inner[0] - left_center_pix[0]) / ((l_inner[0] - l_outer[0]) + 1e-6)

            left_gaze = "Right" if left_h_ratio < 0.35 else "Left" if left_h_ratio > 0.65 else "Center"
            right_gaze = "Right" if right_h_ratio < 0.35 else "Left" if right_h_ratio > 0.65 else "Center"

            eye_pos = f"{left_gaze},{right_gaze}"

            # Annotate the frame
            # cv2.circle(frame, right_center_pix, 5, (0, 255, 0), -1)
            # cv2.circle(frame, left_center_pix, 5, (0, 255, 0), -1)
            # cv2.putText(frame, eye_pos, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)

    return frame, eye_pos

def main():
    """Main function to run the eye gaze detection."""
    face_mesh = initialize_face_mesh()
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to capture frame.")
            break

        frame = cv2.flip(frame, 1)
        frame , pos= process_frame(face_mesh, frame)
        print(pos)
        cv2.imshow("Eye Gaze Detection", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

# if __name__ == "__main__":
#     main()

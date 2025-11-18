import cv2
import mediapipe as mp
import numpy as np

# Initialize MediaPipe Face Mesh
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

def get_head_pose(frame, face_mesh):
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb_frame)
    
    if not results.multi_face_landmarks:
        return None
        
    face_landmarks = results.multi_face_landmarks[0]
    
    # Get specific landmarks for pose estimation
    image_points = np.array([
        [face_landmarks.landmark[i].x * frame.shape[1], face_landmarks.landmark[i].y * frame.shape[0]]
        for i in [1, 152, 226, 446, 57, 287]
    ], dtype="double")
    
    model_points = np.array([
        (0.0, 0.0, 0.0),             # Nose tip
        (0.0, -330.0, -65.0),        # Chin
        (-225.0, 170.0, -135.0),     # Left eye
        (225.0, 170.0, -135.0),      # Right eye
        (-150.0, -150.0, -125.0),    # Left mouth
        (150.0, -150.0, -125.0)      # Right mouth
    ])
    
    # Camera internals
    focal_length = frame.shape[1]
    center = (frame.shape[1] / 2, frame.shape[0] / 2)
    camera_matrix = np.array([
        [focal_length, 0, center[0]],
        [0, focal_length, center[1]],
        [0, 0, 1]
    ], dtype="double")
    
    dist_coeffs = np.zeros((4, 1))
    success, rotation_vector, translation_vector = cv2.solvePnP(
        model_points, image_points, camera_matrix, dist_coeffs, flags=cv2.SOLVEPNP_ITERATIVE
    )
    
    if not success:
        return None
        
    rmat, _ = cv2.Rodrigues(rotation_vector)
    proj_matrix = np.hstack((rmat, translation_vector))
    euler_angles = cv2.decomposeProjectionMatrix(proj_matrix)[6]
    pitch, yaw, roll = [float(angle) for angle in euler_angles]
    
    pitch_threshold_up = 15
    pitch_threshold_down = -15
    yaw_threshold_left = -15
    yaw_threshold_right = 15
    
    vertical = "Center" if (-180 < pitch < -170) or (180 > pitch > 170) else "Down" if pitch < pitch_threshold_down else "Up"
    horizontal = "Left" if yaw < yaw_threshold_left else "Right" if yaw > yaw_threshold_right else "Center"
    
    direction = f"{vertical},{horizontal}".strip()
    return direction

def main():
    cap = cv2.VideoCapture(0)
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        result = get_head_pose(frame, face_mesh)  # Pass face_mesh as a parameter
        if result:
            direction = result
            print(f"{direction}")
        
        cv2.imshow("Camera", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    face_mesh.close()

if __name__ == "__main__":
    main()

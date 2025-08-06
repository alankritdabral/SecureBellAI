from run_multithreaded import FaceRecognitionSystem
import cv2

def main():
    system = FaceRecognitionSystem(database_dir="visitors/old")
    print("Running face recognition on video source...")
    system.run(video_source=0, display=True)

    print("Processing a single frame...")
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    if ret:
        detected_objects, head_pose = system.process_single_frame(frame)
        print(f"Detected objects: {detected_objects}, Head pose: {head_pose}")
    cap.release()

if __name__ == '__main__':
    main()

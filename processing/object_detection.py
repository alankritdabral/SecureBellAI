import cv2
from ultralytics import YOLO

# Load the YOLOv8n model
model = YOLO("yolov8n.pt")  # Make sure yolov8n.pt is in the current directory or provide full path

def detectObject(frame):
    """Detect objects in the given frame using YOLOv8."""
    labels_this_frame = []
    results = model(frame, verbose=False)[0]

    # Iterate over each detected object (each box)
    for box in results.boxes:
        # Extract class id and label
        cls_id = int(box.cls[0])
        label = model.names[cls_id]

        if float(box.conf[0]) > 0.5:
            labels_this_frame.append(label)  # Append only the label (object name)

    return labels_this_frame

def main():
    """Main function to capture video and detect objects."""
    cap = cv2.VideoCapture(0)  # Use webcam; replace 0 with a video file path if needed
    
    if not cap.isOpened():
        print("Error: Could not open video source.")
        return
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Detect objects
        detected_objects = detectObject(frame)
        print(f"{''.join(detected_objects)}")  # Print only object names
        
        # Display frame
        cv2.imshow("YOLOv8 Object Detection", frame)
        
        # Exit on pressing 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()

import multiprocessing
import subprocess

def run_server():
    """Run the Flask server."""
    subprocess.run(["python", "/home/aloo/Desktop/New Folder/server.py"])

def run_face_recognition():
    """Run the FaceRecognitionSystem."""
    subprocess.run(["python", "/home/aloo/Desktop/New Folder/run_multithreaded.py"])

if __name__ == "__main__":
    # Create processes for server and face recognition
    server_process = multiprocessing.Process(target=run_server)
    face_recognition_process = multiprocessing.Process(target=run_face_recognition)

    # Start both processes
    server_process.start()
    face_recognition_process.start()

    # Wait for both processes to complete
    server_process.join()
    face_recognition_process.join()

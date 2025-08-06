from flask import Flask, render_template, Response, request, jsonify, redirect, url_for
from flask_cors import CORS
from backend.db_helper import *
import cv2
import numpy as np
from run_multithreaded import FaceRecognitionSystem
from datetime import datetime
import os
from flask import send_from_directory


app = Flask(__name__)
CORS(app)

# Define a global variable to store the email
global_email = None


def log_with_timestamp(message):
    """Helper function to log messages with a timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open('report.txt', 'a') as file:
        file.write(f"[{timestamp}] {message}\n")


# Receiving the sign_up data credentials 
@app.route('/signup_data', methods=['POST'])
def signup_data():
    try:
        data = request.get_json()
        print("Received signup data:", data)  # Debugging log

        name = data.get('name')
        gender = data.get('gender')
        dob = data.get('dob')
        mobile = data.get('mobile')
        email = data.get('email')
        password = data.get('password')

        # Debugging: Log extracted data
        print(f"Extracted data - Name: {name}, Gender: {gender}, DOB: {dob}, Mobile: {mobile}, Email: {email}, Password: {password}")

        if insert_signup(name, gender, dob, mobile, email, password) == 1:
            log_with_timestamp(f"Signup successful for {email}.")
            response_data = {'message': 'Data inserted successfully!'}
        else:
            log_with_timestamp(f"Signup failed for {email}.")
            response_data = {'message': 'Error in inserting the data!'}
        return jsonify(response_data)

    except Exception as e:
        log_with_timestamp(f"Error in signup_data route: {e}")
        print(f"Error in signup_data route: {e}")
        return jsonify({'message': 'An error occurred during signup.'}), 500

# Receiving the login_data credentials
@app.route('/login_data', methods=['POST'])
def login_data():
    global global_email
    try:
        data = request.get_json()
        print(data)
        
        # Save the email to the global variable
        global_email = data['email']
        
        response_data = search_login_credentials(global_email, data['password'])
        if response_data:
            log_with_timestamp(f"Login successful for {global_email}.")
            return jsonify(response_data)
        else:
            log_with_timestamp(f"Login failed for {global_email}.")
            return jsonify({'message': 'Data not found!'})
    except Exception as e:
        log_with_timestamp(f"Error in login_data route: {e}")
        print(f"Error in login_data route: {e}")
        return jsonify({'message': 'An error occurred during login.'}), 500

# Router to render the index HTML template
@app.route('/')
def index_page():
    return render_template('index.html')

@app.route('/welcome')
def welcome_page():
    return render_template('welcome.html')

@app.route('/visitors')
def visitors_page():
    return render_template('visitors.html')

@app.route('/logs', methods=['GET'])
def view_logs():
    """Route to display the logs from report.txt."""
    try:
        with open('report.txt', 'r') as file:
            logs = file.readlines()
        return render_template('logs.html', logs=logs)
    except Exception as e:
        log_with_timestamp(f"Error reading logs: {e}")
        return jsonify({'message': 'Error reading logs.'}), 500


@app.route('/stop', methods=['POST'])
def stop_server():
    """Route to stop the Flask server."""
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    return jsonify({'message': 'Server shutting down...'})


@app.route('/data', methods=['GET'])
def data_page():
    """Route to display images from visitors/old."""
    try:
        image_folder = os.path.join('visitors', 'old')
        images = os.listdir(image_folder)
        return render_template('data.html', images=images, folder=image_folder)
    except Exception as e:
        log_with_timestamp(f"Error in data_page route: {e}")
        return jsonify({'message': 'Error fetching images.'}), 500

@app.route('/temp_data', methods=['GET'])
def temp_data_page():
    """Route to display images from recent/."""
    try:
        image_folder = os.path.join('recent')
        images = os.listdir(image_folder)
        return render_template('temp_data.html', images=images, folder=image_folder)
    except Exception as e:
        log_with_timestamp(f"Error in temp_data_page route: {e}")
        return jsonify({'message': 'Error fetching images.'}), 500

@app.route('/images/<path:folder>/<filename>')
def serve_image(folder, filename):
    """Serve images from the specified folder."""
    return send_from_directory(folder, filename)

# Main function
if __name__ == "__main__":
    print("Starting the Python Flask Server.....")
    app.run(port=5000, debug=True)

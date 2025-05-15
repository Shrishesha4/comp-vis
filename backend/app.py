import os
import cv2
import numpy as np
import time
import uuid
from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image
import io
import tempfile
from helmet_detector import HelmetDetectionModel

# Initialize Flask app
app = Flask(__name__)
# Configure CORS to allow requests from your frontend
CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}})

# Load helmet detection model
model = HelmetDetectionModel()

# Add a route for the root URL
@app.route('/', methods=['GET'])
def index():
    return jsonify({
        'status': 'ok',
        'message': 'Helmet Detection API is running',
        'endpoints': {
            '/process': 'POST - Process an image for helmet detection',
            '/process-video': 'POST - Process a video for helmet detection'
        }
    })

@app.route('/process', methods=['POST'])
def process_image():
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
    
    # Get image file from request
    file = request.files['image']
    
    # Read image data once and store it
    file_data = file.read()
    if not file_data:
        return jsonify({'error': 'Empty image data'}), 400
        
    # Read image using PIL
    img = Image.open(io.BytesIO(file_data))
    
    # Convert PIL image to OpenCV format
    open_cv_image = np.array(img)
    # Convert RGB to BGR (OpenCV format)
    if open_cv_image.shape[2] == 3:
        open_cv_image = open_cv_image[:, :, ::-1].copy()
    
    # Preprocess the image to improve detection
    # 1. Resize if too large
    max_dim = 1024
    h, w = open_cv_image.shape[:2]
    if max(h, w) > max_dim:
        scale = max_dim / max(h, w)
        open_cv_image = cv2.resize(open_cv_image, None, fx=scale, fy=scale)
    
    # 2. Apply contrast enhancement
    lab = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    enhanced_lab = cv2.merge((cl, a, b))
    enhanced_image = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
    
    # Process image with model
    detections = model.detect(enhanced_image)
    
    return jsonify({
        'detections': detections,
        'count': len(detections)
    })

@app.route('/process-video', methods=['POST'])
def process_video():
    if 'video' not in request.files:
        return jsonify({'error': 'No video provided'}), 400
    
    # Get video file from request
    file = request.files['video']
    
    # Create a temporary file to save the uploaded video
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_file:
        file.save(temp_file.name)
        video_path = temp_file.name
    
    try:
        # Open the video file
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            return jsonify({'error': 'Could not open video file'}), 400
        
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Process only a subset of frames to improve performance
        # For example, process 1 frame per second
        frame_interval = max(1, int(fps))
        
        all_detections = []
        frame_number = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Process only every nth frame
            if frame_number % frame_interval == 0:
                # Preprocess the frame
                # 1. Resize if too large
                max_dim = 1024
                h, w = frame.shape[:2]
                if max(h, w) > max_dim:
                    scale = max_dim / max(h, w)
                    frame = cv2.resize(frame, None, fx=scale, fy=scale)
                
                # 2. Apply contrast enhancement
                lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
                l, a, b = cv2.split(lab)
                clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
                cl = clahe.apply(l)
                enhanced_lab = cv2.merge((cl, a, b))
                enhanced_frame = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
                
                # Process frame with model
                detections = model.detect(enhanced_frame)
                
                # Add frame number to detections
                for detection in detections:
                    detection['frame'] = frame_number
                
                all_detections.extend(detections)
            
            frame_number += 1
        
        cap.release()
        
        # Calculate statistics
        total_people = len(all_detections)
        people_with_helmets = sum(1 for d in all_detections if d['has_helmet'])
        people_without_helmets = total_people - people_with_helmets
        
        # Clean up the temporary file
        os.unlink(video_path)
        
        return jsonify({
            'detections': all_detections,
            'total_frames': frame_count,
            'processed_frames': frame_number // frame_interval,
            'statistics': {
                'total_people': total_people,
                'people_with_helmets': people_with_helmets,
                'people_without_helmets': people_without_helmets,
                'helmet_percentage': (people_with_helmets / total_people * 100) if total_people > 0 else 0
            }
        })
    
    except Exception as e:
        # Clean up the temporary file in case of error
        if os.path.exists(video_path):
            os.unlink(video_path)
        return jsonify({'error': str(e)}), 500

# Add a route for collecting training data
@app.route('/collect', methods=['POST'])
def collect_training_data():
    if 'image' not in request.files or 'label' not in request.form:
        return jsonify({'error': 'Image and label required'}), 400
    
    file = request.files['image']
    label = request.form['label']
    
    # Create directories if they don't exist
    os.makedirs('training_data/helmet', exist_ok=True)
    os.makedirs('training_data/no_helmet', exist_ok=True)
    
    # Save the image to the appropriate directory
    save_dir = f'training_data/{label}'
    filename = f"{int(time.time())}_{uuid.uuid4().hex[:8]}.jpg"
    file_path = os.path.join(save_dir, filename)
    
    # Save the image
    img = Image.open(io.BytesIO(file.read()))
    img.save(file_path)
    
    return jsonify({
        'status': 'success',
        'message': f'Image saved as {label}',
        'file': filename
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8844)
import os
import cv2
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image
import io
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
            '/process': 'POST - Process an image for helmet detection'
        }
    })

@app.route('/process', methods=['POST'])
def process_image():
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
    
    # Get image file from request
    file = request.files['image']
    
    # Read image using PIL
    img = Image.open(io.BytesIO(file.read()))
    
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
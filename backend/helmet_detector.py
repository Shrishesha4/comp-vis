import os
import torch
import torch.nn as nn
import torchvision.transforms as transforms
import torchvision.models as models
import cv2
import numpy as np
from PIL import Image

class HelmetDetectionModel:
    def __init__(self, model_path=None):
        # Load person detector
        self.person_detector = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)
        self.person_detector.classes = [0]  # Only detect people (class 0 in COCO dataset)
        
        # Load or create helmet classifier
        if model_path and os.path.exists(model_path):
            # Load custom trained model if provided
            self.helmet_classifier = torch.load(model_path)
        else:
            # Use a pre-trained model and fine-tune for helmet detection
            self.helmet_classifier = models.resnet50(pretrained=True)
            num_ftrs = self.helmet_classifier.fc.in_features
            self.helmet_classifier.fc = nn.Linear(num_ftrs, 2)  # 2 classes: helmet/no helmet
            
            # Set to evaluation mode
            self.helmet_classifier.eval()
        
        # Define image transformations for the helmet classifier
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        
        # Initialize motorcycle detector (using the same YOLOv5 model)
        self.motorcycle_detector = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)
        self.motorcycle_detector.classes = [3]  # Class 3 is motorcycle in COCO dataset
    
    def detect(self, image):
        # Detect people in the image
        results = self.person_detector(image)
        
        # Detect motorcycles in the image
        motorcycle_results = self.motorcycle_detector(image)
        
        # Extract motorcycle bounding boxes
        motorcycle_boxes = []
        for pred in motorcycle_results.xyxy[0]:
            x1, y1, x2, y2, conf, cls = pred.tolist()
            if int(cls) == 3 and conf > 0.5:  # If it's a motorcycle with confidence > 50%
                motorcycle_boxes.append([x1, y1, x2, y2])
        
        detections = []
        
        # Process each detected person
        for pred in results.xyxy[0]:  # Process first image in batch
            x1, y1, x2, y2, conf, cls = pred.tolist()
            
            if int(cls) == 0 and conf > 0.5:  # If it's a person with confidence > 50%
                # Extract the person region
                person_roi = image[int(y1):int(y2), int(x1):int(x2)]
                
                # Check if the person is on a motorcycle
                is_on_motorcycle = self.check_motorcycle_overlap([x1, y1, x2, y2], motorcycle_boxes)
                
                # Extract the head region (top 1/3 of the person bounding box)
                head_y2 = int(y1 + (y2-y1) * 0.3)
                head_roi = image[int(y1):head_y2, int(x1):int(x2)]
                
                # Detect if the person is wearing a helmet
                has_helmet = self.detect_helmet(head_roi)
                
                # Only include people on motorcycles if there are motorcycles detected
                # Otherwise include all people
                if len(motorcycle_boxes) == 0 or is_on_motorcycle:
                    detections.append({
                        'bbox': [int(x1), int(y1), int(x2-x1), int(y2-y1)],  # [x, y, width, height]
                        'confidence': float(conf),
                        'class': int(cls),
                        'has_helmet': has_helmet,
                        'on_motorcycle': is_on_motorcycle
                    })
        
        return detections
    
    def check_motorcycle_overlap(self, person_box, motorcycle_boxes):
        """Check if a person overlaps with any motorcycle"""
        if not motorcycle_boxes:
            return False
            
        px1, py1, px2, py2 = person_box
        
        for mx1, my1, mx2, my2 in motorcycle_boxes:
            # Calculate intersection area
            x_left = max(px1, mx1)
            y_top = max(py1, my1)
            x_right = min(px2, mx2)
            y_bottom = min(py2, my2)
            
            if x_right < x_left or y_bottom < y_top:
                continue  # No overlap
                
            intersection_area = (x_right - x_left) * (y_bottom - y_top)
            person_area = (px2 - px1) * (py2 - py1)
            
            # If the intersection is significant (>20% of person area)
            if intersection_area > 0.2 * person_area:
                return True
                
        return False
    
    def detect_helmet(self, head_image):
        # Check if head region is valid
        if head_image.size == 0:
            return False
        
        try:
            # Convert OpenCV image (BGR) to PIL Image (RGB)
            head_pil = Image.fromarray(cv2.cvtColor(head_image, cv2.COLOR_BGR2RGB))
            
            # Apply transformations
            head_tensor = self.transform(head_pil).unsqueeze(0)  # Add batch dimension
            
            # Make prediction
            with torch.no_grad():
                outputs = self.helmet_classifier(head_tensor)
                _, predicted = torch.max(outputs, 1)
                
            # Return True if helmet detected (class 1), False otherwise
            return bool(predicted.item() == 1)
        except Exception as e:
            print(f"Error in helmet detection: {e}")
            return False

# Usage example:
# model = HelmetDetectionModel()
# detections = model.detect(image)
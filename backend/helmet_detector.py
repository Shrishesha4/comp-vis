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
    
    def detect(self, image):
        # Detect people in the image
        results = self.person_detector(image)
        
        detections = []
        
        # Process each detected person
        for pred in results.xyxy[0]:  # Process first image in batch
            x1, y1, x2, y2, conf, cls = pred.tolist()
            
            if int(cls) == 0 and conf > 0.5:  # If it's a person with confidence > 50%
                # Extract the person region
                person_roi = image[int(y1):int(y2), int(x1):int(x2)]
                
                # Check if the person is on a motorcycle (optional enhancement)
                # is_on_motorcycle = self.check_motorcycle(person_roi)
                
                # Extract the head region (top 1/3 of the person bounding box)
                head_y2 = int(y1 + (y2-y1) * 0.3)
                head_roi = image[int(y1):head_y2, int(x1):int(x2)]
                
                # Detect if the person is wearing a helmet
                has_helmet = self.detect_helmet(head_roi)
                
                detections.append({
                    'bbox': [int(x1), int(y1), int(x2-x1), int(y2-y1)],  # [x, y, width, height]
                    'confidence': float(conf),
                    'class': int(cls),
                    'has_helmet': has_helmet
                })
        
        return detections
    
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
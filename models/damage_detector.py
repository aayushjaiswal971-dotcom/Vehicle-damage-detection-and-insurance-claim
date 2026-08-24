from ultralytics import YOLO
import cv2
import numpy as np

class DamageDetector:
    def __init__(self, model_path):
        self.model_path = model_path
        self.model = None
        self.part_names = ['bumper', 'door', 'hood', 'fender', 'windshield', 'damage']
    
    def load_model(self):
        """Load YOLOv8 model"""
        try:
            self.model = YOLO(self.model_path)
            print(f"YOLOv8 model loaded from {self.model_path}")
        except Exception as e:
            print(f"Error loading YOLOv8 model: {e}")
            print("Using pretrained YOLOv8n as fallback")
            self.model = YOLO('yolov8n.pt')
    
    def detect(self, image):
        """
        Detect damaged regions and vehicle parts
        Returns: detections with bounding boxes, classes, and confidence
        """
        if self.model is None:
            self.load_model()
        
        results = self.model(image, conf=0.25)
        
        detections = []
        for result in results:
            boxes = result.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = float(box.conf[0])
                cls = int(box.cls[0])
                
                detection = {
                    'bbox': [int(x1), int(y1), int(x2), int(y2)],
                    'confidence': conf,
                    'class_id': cls,
                    'class_name': self.get_class_name(cls),
                    'area': (x2 - x1) * (y2 - y1)
                }
                detections.append(detection)
        
        return detections
    
    def get_class_name(self, class_id):
        """Map class ID to part name"""
        if class_id < len(self.part_names):
            return self.part_names[class_id]
        return f"class_{class_id}"
    
    def draw_detections(self, image, detections):
        """Draw bounding boxes on image"""
        img_copy = image.copy()
        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            label = f"{det['class_name']}: {det['confidence']:.2f}"
            
            cv2.rectangle(img_copy, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(img_copy, label, (x1, y1 - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        return img_copy

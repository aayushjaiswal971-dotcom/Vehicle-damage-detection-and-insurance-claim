import numpy as np
import cv2

class FeatureExtractor:
    def __init__(self):
        pass
    
    def extract_features(self, image, detections, masks):
        """
        Extract features for severity and cost estimation
        Returns: feature vector
        """
        features = {}
        
        # Basic detection features
        if detections:
            total_bbox_area = sum([d['area'] for d in detections])
            max_bbox_area = max([d['area'] for d in detections])
            num_detections = len(detections)
            avg_confidence = np.mean([d['confidence'] for d in detections])
        else:
            total_bbox_area = 0
            max_bbox_area = 0
            num_detections = 0
            avg_confidence = 0
        
        features['total_bbox_area'] = total_bbox_area
        features['max_bbox_area'] = max_bbox_area
        features['num_detections'] = num_detections
        features['avg_confidence'] = avg_confidence
        
        # Mask-based features
        if masks:
            total_mask_area = sum([m['area'] for m in masks])
            max_mask_area = max([m['area'] for m in masks])
            num_masks = len(masks)
            
            # Calculate shape irregularity (perimeter^2 / area)
            irregularities = []
            for mask_info in masks:
                mask = mask_info['mask']
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if contours:
                    perimeter = cv2.arcLength(contours[0], True)
                    area = mask_info['area']
                    if area > 0:
                        irregularity = (perimeter ** 2) / (4 * np.pi * area)
                        irregularities.append(irregularity)
            
            avg_irregularity = np.mean(irregularities) if irregularities else 0
        else:
            total_mask_area = 0
            max_mask_area = 0
            num_masks = 0
            avg_irregularity = 0
        
        features['total_mask_area'] = total_mask_area
        features['max_mask_area'] = max_mask_area
        features['num_masks'] = num_masks
        features['avg_irregularity'] = avg_irregularity
        
        # Damage ratio
        image_area = image.shape[0] * image.shape[1]
        features['damage_ratio'] = total_mask_area / image_area if image_area > 0 else 0
        
        # Texture features (using grayscale)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        features['mean_intensity'] = np.mean(gray)
        features['std_intensity'] = np.std(gray)
        
        # Edge density
        edges = cv2.Canny(gray, 50, 150)
        features['edge_density'] = np.sum(edges > 0) / image_area if image_area > 0 else 0
        
        return features
    
    def features_to_vector(self, features):
        """Convert feature dict to numpy array"""
        feature_order = [
            'total_bbox_area', 'max_bbox_area', 'num_detections', 'avg_confidence',
            'total_mask_area', 'max_mask_area', 'num_masks', 'avg_irregularity',
            'damage_ratio', 'mean_intensity', 'std_intensity', 'edge_density'
        ]
        return np.array([features.get(k, 0) for k in feature_order])

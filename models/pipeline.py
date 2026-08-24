import os
import cv2
from models.preprocessing import ImagePreprocessor
from models.damage_detector import DamageDetector
from models.segmentation import MaskRCNNSegmenter
from models.feature_extractor import FeatureExtractor
from models.severity_estimator import SeverityEstimator
from models.cost_estimator import CostEstimator

class DamageAssessmentPipeline:
    def __init__(self, config):
        self.config = config
        
        # Initialize components
        self.preprocessor = ImagePreprocessor()
        self.detector = DamageDetector(config.YOLOV8_MODEL_PATH)
        self.segmenter = MaskRCNNSegmenter(config.MASKRCNN_MODEL_PATH)
        self.feature_extractor = FeatureExtractor()
        self.severity_estimator = SeverityEstimator(config.SEVERITY_MODEL_PATH)
        self.cost_estimator = CostEstimator(config.COST_MODEL_PATH, config.COST_RANGES)
    
    def load_models(self):
        """Load all models at startup"""
        print("Loading models...")
        self.detector.load_model()
        self.segmenter.load_model()
        self.severity_estimator.load_model()
        self.cost_estimator.load_model()
        print("All models loaded successfully")
    
    def process_image(self, image_path, output_dir=None):
        """
        Complete damage assessment pipeline
        Returns: assessment results
        """
        try:
            # Step 1: Preprocessing
            preprocessed_img, resized_img = self.preprocessor.preprocess(image_path)
            
            # Step 2: Damage detection with YOLOv8
            detections = self.detector.detect(preprocessed_img)
            
            if not detections:
                return {
                    'success': False,
                    'message': 'No damage detected in the image',
                    'damaged_part': 'None',
                    'severity': 'None',
                    'damage_ratio': 0.0,
                    'estimated_cost': 0
                }
            
            # Step 3: Segmentation with Mask R-CNN
            masks = self.segmenter.segment(preprocessed_img, detections)
            
            # Step 4: Feature extraction
            features = self.feature_extractor.extract_features(
                preprocessed_img, detections, masks
            )
            feature_vector = self.feature_extractor.features_to_vector(features)
            
            # Step 5: Severity estimation
            severity = self.severity_estimator.predict(feature_vector)
            
            # Step 6: Identify damaged part
            damaged_part = self._identify_damaged_part(detections)
            
            # Step 7: Cost estimation
            estimated_cost = self.cost_estimator.predict(
                feature_vector, severity, damaged_part
            )
            
            # Calculate damage ratio
            damage_ratio = features['damage_ratio']
            
            # Save visualizations if output directory provided
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                
                # Save detection visualization
                det_img = self.detector.draw_detections(preprocessed_img, detections)
                det_path = os.path.join(output_dir, 'detections.jpg')
                cv2.imwrite(det_path, det_img)
                
                # Save segmentation visualization
                if masks:
                    seg_img = self.segmenter.visualize_masks(preprocessed_img, masks)
                    seg_path = os.path.join(output_dir, 'segmentation.jpg')
                    cv2.imwrite(seg_path, seg_img)
            
            return {
                'success': True,
                'damaged_part': damaged_part,
                'severity': severity,
                'damage_ratio': round(damage_ratio, 4),
                'estimated_cost': int(estimated_cost),
                'num_detections': len(detections),
                'features': features
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error processing image: {str(e)}',
                'damaged_part': 'Error',
                'severity': 'Error',
                'damage_ratio': 0.0,
                'estimated_cost': 0
            }
    
    def _identify_damaged_part(self, detections):
        """Identify the primary damaged vehicle part"""
        if not detections:
            return 'unknown'
        
        # Find detection with highest confidence
        best_detection = max(detections, key=lambda x: x['confidence'])
        return best_detection['class_name']

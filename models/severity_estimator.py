import lightgbm as lgb
import numpy as np
import os

class SeverityEstimator:
    def __init__(self, model_path=None):
        self.model_path = model_path
        self.model = None
        self.severity_classes = ['Minor', 'Moderate', 'Severe']
    
    def load_model(self):
        """Load LightGBM severity classification model"""
        if self.model_path and os.path.exists(self.model_path):
            try:
                self.model = lgb.Booster(model_file=self.model_path)
                print(f"Severity model loaded from {self.model_path}")
            except Exception as e:
                print(f"Error loading severity model: {e}")
                self.model = None
        else:
            print("Severity model not found, using rule-based estimation")
            self.model = None
    
    def predict(self, features):
        """
        Predict severity level from features
        Returns: severity class (Minor, Moderate, Severe)
        """
        if self.model is not None:
            try:
                feature_vector = features.reshape(1, -1)
                prediction = self.model.predict(feature_vector)
                severity_idx = int(np.argmax(prediction))
                return self.severity_classes[severity_idx]
            except Exception as e:
                print(f"Error in model prediction: {e}")
                return self._rule_based_severity(features)
        else:
            return self._rule_based_severity(features)
    
    def _rule_based_severity(self, features):
        """
        Rule-based severity estimation using damage ratio
        """
        # Extract damage ratio (index 8 in feature vector)
        if isinstance(features, dict):
            damage_ratio = features.get('damage_ratio', 0)
        else:
            damage_ratio = features[8] if len(features) > 8 else 0
        
        if damage_ratio < 0.05:
            return 'Minor'
        elif damage_ratio < 0.15:
            return 'Moderate'
        else:
            return 'Severe'
    
    def get_severity_score(self, severity):
        """Convert severity to numeric score"""
        severity_map = {'Minor': 1, 'Moderate': 2, 'Severe': 3}
        return severity_map.get(severity, 1)

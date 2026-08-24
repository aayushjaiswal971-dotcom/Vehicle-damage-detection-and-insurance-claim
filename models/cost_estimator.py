import xgboost as xgb
import numpy as np
import os

class CostEstimator:
    def __init__(self, model_path=None, cost_ranges=None):
        self.model_path = model_path
        self.model = None
        self.cost_ranges = cost_ranges or {
            'Minor': (5000, 15000),
            'Moderate': (15000, 50000),
            'Severe': (50000, 100000)
        }
    
    def load_model(self):
        """Load XGBoost cost regression model"""
        if self.model_path and os.path.exists(self.model_path):
            try:
                self.model = xgb.Booster()
                self.model.load_model(self.model_path)
                print(f"Cost model loaded from {self.model_path}")
            except Exception as e:
                print(f"Error loading cost model: {e}")
                self.model = None
        else:
            print("Cost model not found, using rule-based estimation")
            self.model = None
    
    def predict(self, features, severity, damaged_part='unknown'):
        """
        Predict repair cost from features and severity
        Returns: estimated cost in INR
        """
        if self.model is not None:
            try:
                feature_vector = features.reshape(1, -1)
                dmatrix = xgb.DMatrix(feature_vector)
                cost = float(self.model.predict(dmatrix)[0])
                return max(cost, 1000)  # Minimum cost
            except Exception as e:
                print(f"Error in cost prediction: {e}")
                return self._rule_based_cost(severity, damaged_part, features)
        else:
            return self._rule_based_cost(severity, damaged_part, features)
    
    def _rule_based_cost(self, severity, damaged_part, features):
        """
        Rule-based cost estimation
        """
        # Base cost from severity
        min_cost, max_cost = self.cost_ranges[severity]
        
        # Extract damage ratio
        if isinstance(features, dict):
            damage_ratio = features.get('damage_ratio', 0)
            num_detections = features.get('num_detections', 1)
        else:
            damage_ratio = features[8] if len(features) > 8 else 0
            num_detections = features[2] if len(features) > 2 else 1
        
        # Calculate base cost within range
        range_span = max_cost - min_cost
        base_cost = min_cost + (damage_ratio / 0.2) * range_span
        base_cost = min(max(base_cost, min_cost), max_cost)
        
        # Part-specific multipliers
        part_multipliers = {
            'windshield': 1.3,
            'hood': 1.2,
            'door': 1.1,
            'bumper': 1.0,
            'fender': 1.05,
            'unknown': 1.0
        }
        
        multiplier = part_multipliers.get(damaged_part.lower(), 1.0)
        
        # Multiple damage multiplier
        if num_detections > 1:
            multiplier *= (1 + 0.1 * (num_detections - 1))
        
        estimated_cost = base_cost * multiplier
        
        # Round to nearest 1000
        estimated_cost = round(estimated_cost / 1000) * 1000
        
        return estimated_cost

import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DATABASE_PATH = 'database/vehicle_damage.db'
    UPLOAD_FOLDER = 'static/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
    
    # Model paths
    YOLOV8_MODEL_PATH = 'models/yolov8_damage.pt'
    MASKRCNN_MODEL_PATH = 'models/maskrcnn_damage.pth'
    SEVERITY_MODEL_PATH = 'models/severity_lgb.txt'
    COST_MODEL_PATH = 'models/cost_xgb.json'
    
    # Cost ranges (in INR)
    COST_RANGES = {
        'Minor': (5000, 15000),
        'Moderate': (15000, 50000),
        'Severe': (50000, 100000)
    }
    
    # Damage severity thresholds
    SEVERITY_THRESHOLDS = {
        'Minor': 0.05,      # < 5% damage
        'Moderate': 0.15,   # 5-15% damage
        'Severe': 0.15      # > 15% damage
    }

import os
import sys
import numpy as np
from PIL import Image

def test_imports():
    """Test if all required packages can be imported"""
    print("Testing imports...")
    
    packages = {
        'flask': 'Flask',
        'cv2': 'OpenCV',
        'torch': 'PyTorch',
        'ultralytics': 'YOLOv8',
        'lightgbm': 'LightGBM',
        'xgboost': 'XGBoost',
        'numpy': 'NumPy',
        'pandas': 'Pandas',
        'sklearn': 'scikit-learn'
    }
    
    failed = []
    for package, name in packages.items():
        try:
            __import__(package)
            print(f"  ✓ {name}")
        except ImportError as e:
            print(f"  ✗ {name}: {e}")
            failed.append(name)
    
    return len(failed) == 0

def test_directories():
    """Test if required directories exist"""
    print("\nTesting directories...")
    
    directories = [
        'database',
        'models',
        'static/uploads',
        'static/css',
        'templates'
    ]
    
    failed = []
    for directory in directories:
        if os.path.exists(directory):
            print(f"  ✓ {directory}")
        else:
            print(f"  ✗ {directory} (missing)")
            failed.append(directory)
    
    return len(failed) == 0

def test_files():
    """Test if required files exist"""
    print("\nTesting files...")
    
    files = {
        'app.py': 'Flask application',
        'config.py': 'Configuration',
        'database/db_manager.py': 'Database manager',
        'models/pipeline.py': 'Processing pipeline',
        'templates/login.html': 'Login template',
        'templates/dashboard.html': 'Dashboard template',
        'static/css/style.css': 'Stylesheet'
    }
    
    failed = []
    for file, description in files.items():
        if os.path.exists(file):
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ {description} (missing)")
            failed.append(file)
    
    return len(failed) == 0

def test_database():
    """Test database functionality"""
    print("\nTesting database...")
    
    try:
        from database.db_manager import DatabaseManager
        
        # Create test database
        test_db = 'database/test.db'
        if os.path.exists(test_db):
            os.remove(test_db)
        db = DatabaseManager(test_db)
        
        # Test registration
        success, user_id = db.register_user('test_user', 'test@example.com', 'password123')
        if success:
            print("  ✓ User registration")
        else:
            print("  ✗ User registration failed")
            return False
        
        # Test login
        success, user = db.login_user('test@example.com', 'password123')
        if success:
            print("  ✓ User login")
        else:
            print("  ✗ User login failed")
            return False
        
        # Test duplicate prevention
        success, msg = db.register_user('test_user2', 'test@example.com', 'password456')
        if not success:
            print("  ✓ Duplicate email prevention")
        else:
            print("  ✗ Duplicate email prevention failed")
            return False
        
        # Test prediction save
        pred_id = db.save_prediction(
            user_id, 'test.jpg', 'bumper', 'Minor', 0.05, 10000
        )
        if pred_id:
            print("  ✓ Prediction save")
        else:
            print("  ✗ Prediction save failed")
            return False
        
        # Test history retrieval
        history = db.get_user_history(user_id)
        if len(history) == 1:
            print("  ✓ History retrieval")
        else:
            print("  ✗ History retrieval failed")
            return False
        
        # Cleanup
        if os.path.exists(test_db):
            os.remove(test_db)
        
        return True
        
    except Exception as e:
        print(f"  ✗ Database test failed: {e}")
        return False

def test_models():
    """Test model components"""
    print("\nTesting model components...")
    
    try:
        from models.preprocessing import ImagePreprocessor
        from models.feature_extractor import FeatureExtractor
        from models.severity_estimator import SeverityEstimator
        from models.cost_estimator import CostEstimator
        
        # Test preprocessor
        preprocessor = ImagePreprocessor()
        print("  ✓ Image preprocessor")
        
        # Test feature extractor
        extractor = FeatureExtractor()
        test_features = {
            'total_bbox_area': 1000,
            'max_bbox_area': 500,
            'num_detections': 1,
            'avg_confidence': 0.9,
            'total_mask_area': 800,
            'max_mask_area': 400,
            'num_masks': 1,
            'avg_irregularity': 1.5,
            'damage_ratio': 0.05,
            'mean_intensity': 120,
            'std_intensity': 30,
            'edge_density': 0.1
        }
        feature_vector = extractor.features_to_vector(test_features)
        if len(feature_vector) == 12:
            print("  ✓ Feature extractor")
        else:
            print("  ✗ Feature extractor failed")
            return False
        
        # Test severity estimator
        severity_est = SeverityEstimator()
        severity = severity_est.predict(feature_vector)
        if severity in ['Minor', 'Moderate', 'Severe']:
            print("  ✓ Severity estimator")
        else:
            print("  ✗ Severity estimator failed")
            return False
        
        # Test cost estimator
        cost_est = CostEstimator()
        cost = cost_est.predict(feature_vector, severity, 'bumper')
        if cost > 0:
            print("  ✓ Cost estimator")
        else:
            print("  ✗ Cost estimator failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"  ✗ Model test failed: {e}")
        return False

def test_config():
    """Test configuration"""
    print("\nTesting configuration...")
    
    try:
        from config import Config
        
        # Check required attributes
        required = [
            'SECRET_KEY',
            'DATABASE_PATH',
            'UPLOAD_FOLDER',
            'YOLOV8_MODEL_PATH',
            'COST_RANGES',
            'SEVERITY_THRESHOLDS'
        ]
        
        for attr in required:
            if hasattr(Config, attr):
                print(f"  ✓ {attr}")
            else:
                print(f"  ✗ {attr} (missing)")
                return False
        
        return True
        
    except Exception as e:
        print(f"  ✗ Config test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("="*60)
    print("Vehicle Damage Detection System - System Test")
    print("="*60)
    print()
    
    results = {
        'Imports': test_imports(),
        'Directories': test_directories(),
        'Files': test_files(),
        'Configuration': test_config(),
        'Database': test_database(),
        'Models': test_models()
    }
    
    print("\n" + "="*60)
    print("Test Results Summary")
    print("="*60)
    
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name:20s}: {status}")
    
    print("="*60)
    
    if all(results.values()):
        print("\n✓ All tests passed! System is ready to use.")
        print("\nNext steps:")
        print("1. Train models: python train_models.py")
        print("2. Run application: python app.py")
        return 0
    else:
        print("\n✗ Some tests failed. Please resolve the issues above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())

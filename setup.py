import os
import sys

def create_directories():
    """Create necessary directories"""
    directories = [
        'database',
        'models',
        'static/uploads',
        'static/css',
        'templates',
        'runs/detect'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✓ Created directory: {directory}")

def check_dataset():
    """Check if dataset exists"""
    dataset_path = 'Car Damage Detection.v1i.yolov8'
    data_yaml = os.path.join(dataset_path, 'data.yaml')
    
    if os.path.exists(data_yaml):
        print(f"✓ Dataset found at: {dataset_path}")
        return True
    else:
        print(f"✗ Dataset not found at: {dataset_path}")
        print("  Please ensure the YOLOv8 dataset is in the project directory")
        return False

def check_dependencies():
    """Check if required packages are installed"""
    required_packages = [
        'flask',
        'opencv-python',
        'torch',
        'ultralytics',
        'lightgbm',
        'xgboost',
        'numpy',
        'pandas'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✓ {package} installed")
        except ImportError:
            print(f"✗ {package} not installed")
            missing_packages.append(package)
    
    if missing_packages:
        print("\nMissing packages detected!")
        print("Install them using: pip install -r requirements.txt")
        return False
    
    return True

def main():
    """Setup script"""
    print("="*60)
    print("Vehicle Damage Detection System - Setup")
    print("="*60)
    print()
    
    print("Step 1: Creating directories...")
    create_directories()
    print()
    
    print("Step 2: Checking dependencies...")
    deps_ok = check_dependencies()
    print()
    
    print("Step 3: Checking dataset...")
    dataset_ok = check_dataset()
    print()
    
    print("="*60)
    if deps_ok and dataset_ok:
        print("✓ Setup completed successfully!")
        print()
        print("Next steps:")
        print("1. Train YOLOv8 model: python train_yolov8.py")
        print("2. Train ML models: python train_models.py")
        print("3. Run application: python app.py")
    else:
        print("✗ Setup incomplete. Please resolve the issues above.")
        sys.exit(1)
    print("="*60)

if __name__ == '__main__':
    main()

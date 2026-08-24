from ultralytics import YOLO
import os
import shutil

def train_yolov8():
    """
    Train YOLOv8 model for vehicle damage detection
    """
    print("Starting YOLOv8 training...")
    
    # Load pretrained YOLOv8 model
    model = YOLO('yolov8n.pt')
    
    # Path to dataset configuration
    data_yaml = 'Car Damage Detection.v1i.yolov8/data.yaml'
    
    if not os.path.exists(data_yaml):
        print(f"Error: Dataset configuration not found at {data_yaml}")
        print("Please ensure the dataset is in the correct location")
        return
    
    # Train the model
    results = model.train(
        data=data_yaml,
        epochs=50,
        imgsz=640,
        batch=16,
        name='vehicle_damage_yolov8',
        patience=10,
        save=True,
        device='cpu',  # Change to 'cuda' if GPU available
        workers=4,
        project='runs/detect',
        exist_ok=True
    )
    
    # Validate the model
    metrics = model.val()
    
    print("\nTraining completed!")
    print(f"Model saved to: runs/detect/vehicle_damage_yolov8/weights/best.pt")
    print(f"mAP50: {metrics.box.map50:.4f}")
    print(f"mAP50-95: {metrics.box.map:.4f}")
    
    # Copy best model to models directory
    os.makedirs('models', exist_ok=True)
    shutil.copy(
        'runs/detect/vehicle_damage_yolov8/weights/best.pt',
        'models/yolov8_damage.pt'
    )
    print("\nModel copied to models/yolov8_damage.pt")

if __name__ == '__main__':
    train_yolov8()

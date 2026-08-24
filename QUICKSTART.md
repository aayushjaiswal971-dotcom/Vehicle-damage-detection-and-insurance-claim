# Quick Start Guide

Get the Vehicle Damage Detection System up and running in minutes!

## Prerequisites

- Python 3.8 or higher
- pip package manager
- 4GB+ RAM
- (Optional) NVIDIA GPU with CUDA for faster training

## Installation Steps

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install all required packages including Flask, PyTorch, OpenCV, YOLOv8, LightGBM, and XGBoost.

### 2. Run Setup Script

```bash
python setup.py
```

This script will:
- Create necessary directories
- Check if all dependencies are installed
- Verify dataset location
- Confirm system is ready

### 3. Train Models

#### Option A: Quick Training (Recommended for testing)

Train severity and cost models with synthetic data (takes ~2 minutes):

```bash
python train_models.py
```

#### Option B: Full Training (Recommended for production)

Train YOLOv8 detection model on your dataset (takes 30-60 minutes on CPU):

```bash
python train_yolov8.py
```

Then train severity and cost models:

```bash
python train_models.py
```

### 4. Start the Application

```bash
python app.py
```

You should see:
```
Initializing application...
Loading models...
YOLOv8 model loaded from models/yolov8_damage.pt
Mask R-CNN loaded
Severity model loaded from models/severity_lgb.txt
Cost model loaded from models/cost_xgb.json
All models loaded successfully
Application ready!
 * Running on http://0.0.0.0:5000
```

### 5. Access the Web Interface

Open your browser and navigate to:
```
http://localhost:5000
```

## First Time Usage

### Register an Account

1. Click "Register" on the homepage
2. Fill in the form:
   - Username: Your name
   - Email: your.email@example.com
   - Password: At least 6 characters
3. Click "Register"

### Login

1. Enter your registered email and password
2. Click "Login"
3. You'll be redirected to the dashboard

### Analyze Vehicle Damage

1. Click "Choose an image" button
2. Select a vehicle image from your computer
3. Preview the image
4. Click "Analyze Damage"
5. Wait for processing (5-10 seconds)
6. View results:
   - Damaged Part
   - Severity Level
   - Damage Ratio
   - Estimated Cost

### View History

Scroll down on the dashboard to see all your previous assessments in a table format.

## Testing the System

### Sample Test Flow

1. **Register Test User**
   - Username: test_user
   - Email: test@example.com
   - Password: test123

2. **Upload Test Image**
   - Use any vehicle image with visible damage
   - Supported formats: JPG, JPEG, PNG
   - Max size: 16MB

3. **Verify Results**
   - Check if damaged part is identified
   - Verify severity classification
   - Confirm cost estimation is reasonable

## Troubleshooting

### "No module named 'flask'"
```bash
pip install -r requirements.txt
```

### "Dataset not found"
Ensure the dataset folder is in the project root:
```
Car Damage Detection.v1i.yolov8/
├── data.yaml
├── train/
├── valid/
└── test/
```

### "Model not found" warnings
The system will use fallback methods if models aren't trained yet. For full functionality:
```bash
python train_models.py
```

### Port 5000 already in use
Change the port in `app.py`:
```python
app.run(debug=True, host='0.0.0.0', port=5001)
```

### Slow processing
- First inference is slower (model loading)
- Subsequent inferences are faster
- Use GPU for better performance

## Quick Commands Reference

```bash
# Setup
python setup.py

# Train models
python train_models.py          # Quick (2 min)
python train_yolov8.py         # Full (30-60 min)

# Run application
python app.py

# Access application
# Open browser: http://localhost:5000
```

## System Requirements

### Minimum
- CPU: Dual-core 2.0 GHz
- RAM: 4GB
- Storage: 5GB free space
- OS: Windows, Linux, or macOS

### Recommended
- CPU: Quad-core 2.5 GHz+
- RAM: 8GB+
- GPU: NVIDIA with 4GB+ VRAM
- Storage: 10GB+ free space

## Next Steps

After getting the system running:

1. **Customize Cost Ranges**: Edit `config.py` to adjust cost estimates for your region
2. **Train on Real Data**: Replace synthetic data with actual damage assessment records
3. **Add More Parts**: Extend the detection classes in YOLOv8 training
4. **Improve UI**: Customize templates and CSS for your branding
5. **Deploy**: Use production WSGI server (Gunicorn, uWSGI) for deployment

## Support

If you encounter issues:

1. Check the main README.md for detailed documentation
2. Verify all dependencies are installed correctly
3. Ensure Python version is 3.8 or higher
4. Check console output for error messages
5. Review the troubleshooting section above

## Success Indicators

You'll know the system is working correctly when:

- ✓ All dependencies install without errors
- ✓ Setup script completes successfully
- ✓ Models train and save to `models/` directory
- ✓ Application starts without errors
- ✓ You can register and login
- ✓ Image upload and analysis works
- ✓ Results are displayed correctly
- ✓ History is saved and displayed

Enjoy using the Vehicle Damage Detection System! 🚗

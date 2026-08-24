# Complete Installation and Usage Instructions

## Step-by-Step Guide for Windows

### Step 1: Verify Python Installation

Open Command Prompt (cmd) and run:
```bash
python --version
```

You should see Python 3.8 or higher. If not, download and install Python from [python.org](https://www.python.org/downloads/).

### Step 2: Navigate to Project Directory

```bash
cd path\to\vehicle-damage-detection
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

This will take 5-10 minutes depending on your internet connection.

### Step 4: Run Setup Script

```bash
python setup.py
```

This verifies that all components are properly installed.

### Step 5: Train Models

#### Option A: Quick Training (Recommended for First Run)

Train severity and cost models with synthetic data (takes ~2 minutes):

```bash
python train_models.py
```

You should see output like:
```
Generating synthetic training data...
Dataset shape: (2000, 14)
Training severity classification model...
Severity model accuracy: 0.9xxx
Training cost regression model...
Cost model RMSE: ₹xxxx.xx
Training completed successfully!
```

#### Option B: Full Training (Optional - for production use)

Train YOLOv8 on the vehicle damage dataset (takes 30-60 minutes):

```bash
python train_yolov8.py
```

### Step 6: Run System Tests (Optional but Recommended)

```bash
python test_system.py
```

All tests should pass with ✓ marks.

### Step 7: Start the Application

#### Method 1: Using Python directly
```bash
python app.py
```

#### Method 2: Using the batch file (Windows)
```bash
run.bat
```

You should see:
```
Initializing application...
Loading models...
YOLOv8 model loaded...
Mask R-CNN loaded...
Severity model loaded...
Cost model loaded...
All models loaded successfully
Application ready!
 * Running on http://0.0.0.0:5000
```

### Step 8: Access the Application

1. Open your web browser
2. Navigate to: `http://localhost:5000`
3. You should see the login page

### Step 9: Create Your First Account

1. Click "Register" link
2. Fill in the registration form:
   - Username: your_name
   - Email: your.email@example.com
   - Password: at least 6 characters
3. Click "Register" button
4. You'll be redirected to login page

### Step 10: Login

1. Enter your registered email and password
2. Click "Login" button
3. You'll be redirected to the dashboard

### Step 11: Analyze Vehicle Damage

1. Click "Choose an image..." button
2. Select a vehicle image from your computer
   - Supported formats: JPG, JPEG, PNG
   - Maximum size: 16MB
3. Preview the image
4. Click "Analyze Damage" button
5. Wait 5-10 seconds for processing
6. View the results:
   - Damaged Part (e.g., bumper, door, hood)
   - Severity Level (Minor, Moderate, Severe)
   - Damage Ratio (percentage)
   - Estimated Cost (in ₹)

### Step 12: View History

Scroll down on the dashboard to see all your previous damage assessments in a table.

## Common Issues and Solutions

### Issue 1: "pip is not recognized"

**Solution**: Add Python to your PATH or use:
```bash
python -m pip install -r requirements.txt
```

### Issue 2: "No module named 'flask'"

**Solution**: Install dependencies:
```bash
pip install -r requirements.txt
```

### Issue 3: "Port 5000 is already in use"

**Solution**: Either:
- Stop the application using port 5000
- Or change the port in `app.py` (last line):
```python
app.run(debug=True, host='0.0.0.0', port=5001)
```

### Issue 4: "Dataset not found"

**Solution**: Ensure the dataset folder exists:
```
Car Damage Detection.v1i.yolov8/
├── data.yaml
├── train/
├── valid/
└── test/
```

### Issue 5: Models not loading

**Solution**: Train the models first:
```bash
python train_models.py
```

The system will use fallback methods if models aren't trained, but for best results, train them.

### Issue 6: Slow processing

**Causes and Solutions**:
- First inference is slower (models loading) - Normal behavior
- Large images - System automatically resizes
- CPU processing - Consider using GPU for faster inference

### Issue 7: "Cannot read image"

**Solution**: Ensure:
- Image file is not corrupted
- File format is JPG, JPEG, or PNG
- File size is under 16MB

## Testing the System

### Test with Sample Images

1. Find vehicle images with visible damage
2. Upload through the dashboard
3. Verify results are reasonable

### Expected Results

For a typical damaged vehicle:
- **Damaged Part**: Should identify the correct part (bumper, door, etc.)
- **Severity**: 
  - Minor: Small scratches, minor dents
  - Moderate: Visible damage, multiple areas
  - Severe: Major damage, structural issues
- **Damage Ratio**: 0.01 to 0.30 (1% to 30%)
- **Cost**: ₹5,000 to ₹100,000 depending on severity

## Understanding the Results

### Damaged Part
The vehicle component that has sustained damage:
- **Bumper**: Front or rear bumper
- **Door**: Side doors
- **Hood**: Engine cover
- **Fender**: Wheel well panels
- **Windshield**: Front or rear glass

### Severity Levels
- **Minor**: < 5% damage, cosmetic issues, ₹5,000-₹15,000
- **Moderate**: 5-15% damage, functional impact, ₹15,000-₹50,000
- **Severe**: > 15% damage, structural issues, ₹50,000+

### Damage Ratio
Percentage of the image area affected by damage. Higher ratio indicates more extensive damage.

### Estimated Cost
Repair cost in Indian Rupees (₹) based on:
- Severity level
- Damaged part type
- Damage extent
- Number of damaged areas

## Advanced Usage

### Training on Custom Data

To train on your own labeled data:

1. Prepare dataset in YOLOv8 format
2. Update `data.yaml` with correct paths
3. Run training:
```bash
python train_yolov8.py
```

### Customizing Cost Ranges

Edit `config.py`:
```python
COST_RANGES = {
    'Minor': (5000, 15000),      # Adjust these values
    'Moderate': (15000, 50000),
    'Severe': (50000, 100000)
}
```

### Adjusting Severity Thresholds

Edit `config.py`:
```python
SEVERITY_THRESHOLDS = {
    'Minor': 0.05,      # < 5% damage
    'Moderate': 0.15,   # 5-15% damage
    'Severe': 0.15      # > 15% damage
}
```

## Stopping the Application

Press `Ctrl+C` in the terminal/command prompt where the application is running.

## Restarting the Application

Simply run again:
```bash
python app.py
```

Your data (users and history) is preserved in the database.

## Backup Your Data

The database is stored in:
```
database/vehicle_damage.db
```

Copy this file to backup your data.

## Getting Help

1. Check this instructions file
2. Read README.md for detailed documentation
3. Read QUICKSTART.md for quick reference
4. Run system tests: `python test_system.py`
5. Check console output for error messages

## Next Steps

After successfully running the system:

1. **Experiment**: Try different vehicle images
2. **Customize**: Adjust cost ranges and thresholds
3. **Train**: Use real data for better accuracy
4. **Deploy**: Follow DEPLOYMENT.md for production setup
5. **Extend**: Add new features based on your needs

## System Requirements Reminder

### Minimum
- Windows 10 or later
- Python 3.8+
- 4GB RAM
- 5GB free disk space
- Internet connection (for initial setup)

### Recommended
- Windows 10/11
- Python 3.9+
- 8GB+ RAM
- 10GB+ free disk space
- GPU with CUDA support (optional, for faster processing)

## Quick Command Reference

```bash
# Setup
python setup.py

# Train models
python train_models.py          # Quick (2 min)
python train_yolov8.py         # Full (30-60 min)

# Test system
python test_system.py

# Run application
python app.py
# or
run.bat

# Access application
# Browser: http://localhost:5000
```

## Success Checklist

- [ ] Python 3.8+ installed
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Setup script completed successfully
- [ ] Models trained (`python train_models.py`)
- [ ] System tests passed (`python test_system.py`)
- [ ] Application starts without errors
- [ ] Can access http://localhost:5000
- [ ] Can register new account
- [ ] Can login successfully
- [ ] Can upload and analyze images
- [ ] Results are displayed correctly
- [ ] History is saved and displayed

If all items are checked, your system is working perfectly! 🎉

## Support

For additional help:
- Review the error messages in the console
- Check the troubleshooting section above
- Ensure all prerequisites are met
- Verify file permissions
- Try restarting the application

Enjoy using the Vehicle Damage Detection System!

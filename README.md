# Vehicle Damage Detection and Cost Estimation System

A complete full-stack web application for automated vehicle damage assessment using deep learning. The system detects damaged vehicle parts, estimates severity levels, and predicts repair costs.

## Features

### User Authentication
- User registration with email validation
- Secure password hashing (SHA-256)
- Login/logout functionality
- Session management
- Duplicate email prevention

### Damage Assessment Pipeline
1. **Image Preprocessing** (OpenCV)
   - Resizing to 640x640
   - Bilateral filtering for noise reduction
   - CLAHE contrast enhancement

2. **Damage Detection** (YOLOv8)
   - Detects damaged regions
   - Identifies vehicle parts (bumper, door, hood, fender, windshield)
   - Bounding box localization

3. **Segmentation** (Mask R-CNN)
   - Pixel-level damage segmentation
   - Precise damage area calculation
   - Mask refinement

4. **Feature Extraction**
   - Bounding box area metrics
   - Damage ratio calculation
   - Shape irregularity analysis
   - Texture features (intensity, edges)

5. **Severity Classification** (LightGBM)
   - Minor: < 5% damage (₹5,000 - ₹15,000)
   - Moderate: 5-15% damage (₹15,000 - ₹50,000)
   - Severe: > 15% damage (₹50,000+)

6. **Cost Estimation** (XGBoost)
   - Regression-based cost prediction
   - Part-specific multipliers
   - Multiple damage adjustments

### Dashboard Features
- Image upload interface
- Real-time damage analysis
- Assessment history tracking
- Detailed results display
- Responsive design

## Project Structure

```
.
├── app.py                          # Flask application
├── config.py                       # Configuration settings
├── requirements.txt                # Python dependencies
├── train_yolov8.py                # YOLOv8 training script
├── train_models.py                # Severity & cost model training
├── database/
│   └── db_manager.py              # Database operations
├── models/
│   ├── preprocessing.py           # Image preprocessing
│   ├── damage_detector.py         # YOLOv8 detection
│   ├── segmentation.py            # Mask R-CNN segmentation
│   ├── feature_extractor.py       # Feature extraction
│   ├── severity_estimator.py      # Severity classification
│   ├── cost_estimator.py          # Cost estimation
│   └── pipeline.py                # Complete pipeline
├── templates/
│   ├── base.html                  # Base template
│   ├── login.html                 # Login page
│   ├── register.html              # Registration page
│   └── dashboard.html             # Dashboard page
├── static/
│   └── css/
│       └── style.css              # Styling
└── Car Damage Detection.v1i.yolov8/  # YOLOv8 dataset
    ├── data.yaml
    ├── train/
    ├── valid/
    └── test/
```

## Installation

### Prerequisites
- Python 3.8+
- pip package manager
- (Optional) CUDA-enabled GPU for faster training

### Setup Steps

1. **Clone or navigate to the project directory**

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Verify dataset structure**
Ensure the YOLOv8 dataset is in the correct location:
```
Car Damage Detection.v1i.yolov8/
├── data.yaml
├── train/
│   ├── images/
│   └── labels/
├── valid/
│   ├── images/
│   └── labels/
└── test/
    ├── images/
    └── labels/
```

## Training Models

### 1. Train YOLOv8 Detection Model

```bash
python train_yolov8.py
```

This will:
- Load pretrained YOLOv8n weights
- Train on the vehicle damage dataset
- Save best model to `models/yolov8_damage.pt`
- Training takes ~30-60 minutes on CPU, ~10-15 minutes on GPU

**Training Parameters:**
- Epochs: 50
- Image size: 640x640
- Batch size: 16
- Early stopping: 10 epochs

### 2. Train Severity & Cost Models

```bash
python train_models.py
```

This will:
- Generate synthetic training data (2000 samples)
- Train LightGBM severity classifier
- Train XGBoost cost regressor
- Save models to `models/` directory

**Output:**
- `models/severity_lgb.txt` - Severity classification model
- `models/cost_xgb.json` - Cost regression model

**Note:** For production use, replace synthetic data with real labeled data from your damage assessment records.

## Running the Application

### Start the Flask Server

```bash
python app.py
```

The application will:
1. Initialize the database
2. Load all trained models
3. Start the web server on `http://localhost:5000`

### Access the Application

1. Open browser and navigate to `http://localhost:5000`
2. Register a new account
3. Login with your credentials
4. Upload vehicle images for damage assessment

## Usage Guide

### Registration
1. Click "Register" on the homepage
2. Enter username, email, and password
3. Submit to create account

### Login
1. Enter registered email and password
2. Click "Login" to access dashboard

### Damage Assessment
1. Click "Choose an image" to select a vehicle photo
2. Preview the selected image
3. Click "Analyze Damage" to start assessment
4. View results:
   - Damaged part (bumper, door, hood, etc.)
   - Severity level (Minor, Moderate, Severe)
   - Damage ratio (percentage)
   - Estimated repair cost (₹)

### View History
- All assessments are saved to your account
- View past assessments in the history table
- Track damage trends over time

## Database Schema

### Users Table
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Prediction History Table
```sql
CREATE TABLE prediction_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    image_path TEXT NOT NULL,
    damaged_part TEXT,
    severity_level TEXT,
    damage_ratio REAL,
    estimated_cost REAL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);
```

## API Endpoints

### Authentication
- `GET /` - Home page (redirects to login/dashboard)
- `GET /register` - Registration page
- `POST /register` - Create new account
- `GET /login` - Login page
- `POST /login` - Authenticate user
- `GET /logout` - Logout user

### Dashboard
- `GET /dashboard` - Main dashboard
- `POST /upload` - Upload and analyze image
- `GET /history` - Get user's assessment history (JSON)

## Model Performance

### YOLOv8 Detection
- Trained on vehicle damage dataset
- Detects 6 classes: bumper, door, hood, fender, windshield, damage
- Real-time inference (~50ms per image on GPU)

### Severity Classification
- 3-class classification (Minor, Moderate, Severe)
- Rule-based fallback using damage ratio thresholds
- Accuracy depends on training data quality

### Cost Estimation
- Regression model predicting repair costs
- Cost ranges:
  - Minor: ₹5,000 - ₹15,000
  - Moderate: ₹15,000 - ₹50,000
  - Severe: ₹50,000 - ₹100,000
- Adjusts for part type and multiple damages

## Configuration

Edit `config.py` to customize:

```python
# File upload settings
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# Cost ranges (INR)
COST_RANGES = {
    'Minor': (5000, 15000),
    'Moderate': (15000, 50000),
    'Severe': (50000, 100000)
}

# Severity thresholds
SEVERITY_THRESHOLDS = {
    'Minor': 0.05,      # < 5% damage
    'Moderate': 0.15,   # 5-15% damage
    'Severe': 0.15      # > 15% damage
}
```

## Error Handling

The system includes comprehensive error handling:
- Invalid file types rejected
- Missing models use fallback methods
- Database errors caught and reported
- Network errors handled gracefully
- User-friendly error messages

## Security Features

- Password hashing (SHA-256)
- Session-based authentication
- SQL injection prevention (parameterized queries)
- File upload validation
- CSRF protection (Flask built-in)

## Performance Optimization

- Models loaded once at startup
- Efficient image preprocessing
- Batch processing support
- Database connection pooling
- Static file caching

## Troubleshooting

### Models not loading
- Ensure models are trained and saved in `models/` directory
- Check file paths in `config.py`
- System will use fallback methods if models missing

### Database errors
- Check write permissions for `database/` directory
- Verify SQLite is installed
- Database auto-creates on first run

### Upload errors
- Verify `static/uploads/` directory exists
- Check file size limits
- Ensure allowed file extensions

### Training issues
- Verify dataset structure matches YOLOv8 format
- Check `data.yaml` paths are correct
- Ensure sufficient disk space
- For GPU training, verify CUDA installation

## Future Enhancements

- [ ] Real-time video damage detection
- [ ] Multi-angle damage assessment
- [ ] Insurance claim integration
- [ ] Mobile app development
- [ ] Advanced damage classification (scratch, dent, crack)
- [ ] Part replacement recommendations
- [ ] Repair shop locator
- [ ] PDF report generation

## Technologies Used

- **Backend:** Flask, Python 3.8+
- **Database:** SQLite3
- **Deep Learning:** PyTorch, YOLOv8, Mask R-CNN
- **ML Models:** LightGBM, XGBoost
- **Image Processing:** OpenCV, PIL
- **Frontend:** HTML5, CSS3, JavaScript
- **Data Science:** NumPy, Pandas, scikit-learn

## License

This project is for educational and demonstration purposes.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Verify all dependencies are installed
3. Ensure models are properly trained
4. Check console logs for detailed error messages

## Acknowledgments

- YOLOv8 by Ultralytics
- Mask R-CNN by Facebook AI Research
- Dataset from Roboflow
- Flask web framework
- PyTorch deep learning library

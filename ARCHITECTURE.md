# System Architecture

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   Register   │  │    Login     │  │     Dashboard        │  │
│  │     Page     │  │     Page     │  │  (Upload & Results)  │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FLASK WEB SERVER                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Authentication Routes  │  Dashboard Routes  │  API       │  │
│  │  /register  /login      │  /dashboard        │  /upload   │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                ┌─────────────┴─────────────┐
                ▼                           ▼
┌───────────────────────────┐   ┌──────────────────────────────┐
│   DATABASE MANAGER        │   │   DAMAGE ASSESSMENT PIPELINE │
│                           │   │                              │
│  ┌─────────────────────┐  │   │  ┌────────────────────────┐ │
│  │  User Management    │  │   │  │  1. Preprocessing      │ │
│  │  - Register         │  │   │  │     (OpenCV)           │ │
│  │  - Login            │  │   │  │                        │ │
│  │  - Authentication   │  │   │  │  2. Detection          │ │
│  └─────────────────────┘  │   │  │     (YOLOv8)           │ │
│                           │   │  │                        │ │
│  ┌─────────────────────┐  │   │  │  3. Segmentation       │ │
│  │  History Management │  │   │  │     (Mask R-CNN)       │ │
│  │  - Save predictions │  │   │  │                        │ │
│  │  - Retrieve history │  │   │  │  4. Feature Extract    │ │
│  └─────────────────────┘  │   │  │                        │ │
│                           │   │  │  5. Severity Classify  │ │
│  ┌─────────────────────┐  │   │  │     (LightGBM)         │ │
│  │   SQLite Database   │  │   │  │                        │ │
│  │  - users            │  │   │  │  6. Cost Estimation    │ │
│  │  - prediction_hist  │  │   │  │     (XGBoost)          │ │
│  └─────────────────────┘  │   │  └────────────────────────┘ │
└───────────────────────────┘   └──────────────────────────────┘
```

## Detailed Processing Pipeline

```
┌──────────────────────────────────────────────────────────────────┐
│                    IMAGE UPLOAD & PROCESSING                     │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  Upload Image    │
                    │  (JPG/PNG)       │
                    └──────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 1: PREPROCESSING (OpenCV)                                │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ • Resize to 640x640                                         │ │
│ │ • Bilateral Filter (noise reduction)                        │ │
│ │ • CLAHE (contrast enhancement)                              │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 2: DAMAGE DETECTION (YOLOv8)                             │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Input: Preprocessed Image                                   │ │
│ │ Output: Bounding boxes, classes, confidence scores          │ │
│ │ Classes: bumper, door, hood, fender, windshield, damage     │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 3: SEGMENTATION (Mask R-CNN)                             │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Input: Image + Detection boxes                              │ │
│ │ Output: Pixel-level masks for each damage region            │ │
│ │ Calculates: Precise damage area                             │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 4: FEATURE EXTRACTION                                     │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Extracts 12 features:                                       │ │
│ │ 1. total_bbox_area      7. num_masks                        │ │
│ │ 2. max_bbox_area        8. avg_irregularity                 │ │
│ │ 3. num_detections       9. damage_ratio                     │ │
│ │ 4. avg_confidence      10. mean_intensity                   │ │
│ │ 5. total_mask_area     11. std_intensity                    │ │
│ │ 6. max_mask_area       12. edge_density                     │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 5: SEVERITY CLASSIFICATION (LightGBM)                    │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Input: 12-dimensional feature vector                        │ │
│ │ Output: Severity class (Minor/Moderate/Severe)              │ │
│ │                                                             │ │
│ │ Thresholds:                                                 │ │
│ │ • Minor:    damage_ratio < 5%   → ₹5K-15K                  │ │
│ │ • Moderate: damage_ratio 5-15%  → ₹15K-50K                 │ │
│ │ • Severe:   damage_ratio > 15%  → ₹50K+                    │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 6: COST ESTIMATION (XGBoost)                             │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Input: Feature vector + Severity + Damaged part             │ │
│ │ Output: Estimated repair cost (₹)                           │ │
│ │                                                             │ │
│ │ Adjustments:                                                │ │
│ │ • Part multipliers (windshield: 1.3x, hood: 1.2x, etc.)    │ │
│ │ • Multiple damage multiplier                                │ │
│ │ • Damage ratio scaling                                      │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  Final Results   │
                    │  - Damaged Part  │
                    │  - Severity      │
                    │  - Damage Ratio  │
                    │  - Estimated Cost│
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  Save to DB      │
                    │  Display to User │
                    └──────────────────┘
```

## Database Schema

```
┌─────────────────────────────────────────────────────────────────┐
│                         DATABASE SCHEMA                         │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────────────┐
│          users               │
├──────────────────────────────┤
│ id (PK)         INTEGER      │
│ username        TEXT         │
│ email           TEXT UNIQUE  │
│ password_hash   TEXT         │
│ created_at      TIMESTAMP    │
└──────────────────────────────┘
                │
                │ 1:N
                │
                ▼
┌──────────────────────────────┐
│    prediction_history        │
├──────────────────────────────┤
│ id (PK)         INTEGER      │
│ user_id (FK)    INTEGER      │
│ image_path      TEXT         │
│ damaged_part    TEXT         │
│ severity_level  TEXT         │
│ damage_ratio    REAL         │
│ estimated_cost  REAL         │
│ timestamp       TIMESTAMP    │
└──────────────────────────────┘
```

## Component Interaction Flow

```
┌──────────────┐
│   Browser    │
└──────┬───────┘
       │ HTTP Request
       ▼
┌──────────────┐
│    Flask     │
│   Routes     │
└──────┬───────┘
       │
       ├─────────────────┐
       │                 │
       ▼                 ▼
┌──────────────┐  ┌──────────────┐
│   Database   │  │   Pipeline   │
│   Manager    │  │   Processor  │
└──────┬───────┘  └──────┬───────┘
       │                 │
       │                 ├──────────────┐
       │                 │              │
       │                 ▼              ▼
       │          ┌──────────┐   ┌──────────┐
       │          │ YOLOv8   │   │ Mask-RCNN│
       │          └──────────┘   └──────────┘
       │                 │              │
       │                 ▼              ▼
       │          ┌──────────┐   ┌──────────┐
       │          │ LightGBM │   │ XGBoost  │
       │          └──────────┘   └──────────┘
       │                 │
       │                 ▼
       │          ┌──────────────┐
       │          │   Results    │
       │          └──────┬───────┘
       │                 │
       ▼                 ▼
┌──────────────────────────────┐
│      Save & Return           │
└──────────────────────────────┘
       │
       ▼
┌──────────────┐
│   Browser    │
│  (Display)   │
└──────────────┘
```

## File Organization

```
vehicle-damage-detection/
│
├── Core Application
│   ├── app.py              # Flask application & routes
│   ├── config.py           # Configuration settings
│   └── wsgi.py            # WSGI entry point (for production)
│
├── Database Layer
│   └── database/
│       └── db_manager.py   # Database operations
│
├── Model Layer
│   └── models/
│       ├── preprocessing.py      # Image preprocessing
│       ├── damage_detector.py    # YOLOv8 detection
│       ├── segmentation.py       # Mask R-CNN segmentation
│       ├── feature_extractor.py  # Feature extraction
│       ├── severity_estimator.py # Severity classification
│       ├── cost_estimator.py     # Cost estimation
│       └── pipeline.py           # Complete pipeline
│
├── View Layer
│   ├── templates/
│   │   ├── base.html       # Base template
│   │   ├── login.html      # Login page
│   │   ├── register.html   # Registration page
│   │   └── dashboard.html  # Dashboard page
│   │
│   └── static/
│       ├── css/
│       │   └── style.css   # Styling
│       └── uploads/        # Uploaded images
│
├── Training Scripts
│   ├── train_yolov8.py    # YOLOv8 training
│   └── train_models.py    # ML models training
│
├── Utilities
│   ├── setup.py           # Setup script
│   └── test_system.py     # System tests
│
└── Documentation
    ├── README.md          # Main documentation
    ├── QUICKSTART.md      # Quick start guide
    ├── INSTRUCTIONS.md    # Detailed instructions
    ├── DEPLOYMENT.md      # Deployment guide
    ├── ARCHITECTURE.md    # This file
    └── PROJECT_SUMMARY.md # Project summary
```

## Technology Stack Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                      PRESENTATION LAYER                         │
│  HTML5 │ CSS3 │ JavaScript │ Responsive Design                  │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                      APPLICATION LAYER                          │
│  Flask 3.0 │ Werkzeug │ Jinja2 Templates                        │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                      BUSINESS LOGIC LAYER                       │
│  Authentication │ Image Processing │ Pipeline Management        │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                      MODEL LAYER                                │
│  YOLOv8 │ Mask R-CNN │ LightGBM │ XGBoost                       │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                      DATA PROCESSING LAYER                      │
│  OpenCV │ PyTorch │ NumPy │ Pandas │ scikit-learn               │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                      DATA LAYER                                 │
│  SQLite3 │ File System                                          │
└─────────────────────────────────────────────────────────────────┘
```

## Request-Response Flow

```
User Action: Upload Image
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ 1. Browser sends POST request to /upload with image file     │
└──────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ 2. Flask receives request, validates session                 │
└──────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ 3. Validate file type and size                               │
└──────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ 4. Save file to uploads directory                            │
└──────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ 5. Pass to damage assessment pipeline                        │
│    • Preprocess image                                        │
│    • Detect damage (YOLOv8)                                  │
│    • Segment regions (Mask R-CNN)                            │
│    • Extract features                                        │
│    • Classify severity (LightGBM)                            │
│    • Estimate cost (XGBoost)                                 │
└──────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ 6. Save results to database                                  │
│    • user_id, image_path, damaged_part                       │
│    • severity, damage_ratio, cost, timestamp                 │
└──────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ 7. Return JSON response to browser                           │
│    {                                                         │
│      "success": true,                                        │
│      "damaged_part": "bumper",                               │
│      "severity": "Moderate",                                 │
│      "damage_ratio": 0.0823,                                 │
│      "estimated_cost": 25000                                 │
│    }                                                         │
└──────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ 8. JavaScript updates UI with results                        │
└──────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ 9. Page refreshes to show updated history                    │
└──────────────────────────────────────────────────────────────┘
```

## Security Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      SECURITY LAYERS                            │
└─────────────────────────────────────────────────────────────────┘

Layer 1: Input Validation
├── File type validation (JPG, PNG only)
├── File size limits (16MB max)
├── Email format validation
└── Password length requirements

Layer 2: Authentication
├── Password hashing (SHA-256)
├── Session management
├── Login required decorators
└── Duplicate email prevention

Layer 3: Data Protection
├── SQL injection prevention (parameterized queries)
├── Secure filename handling
├── Session cookie security
└── CSRF protection (Flask built-in)

Layer 4: Application Security
├── Error handling without information leakage
├── Secure file upload handling
├── Path traversal prevention
└── Input sanitization
```

## Scalability Considerations

```
Current Architecture (Single Server)
┌──────────────────────────────────────┐
│  Flask App + Models + Database       │
│  (All on one server)                 │
└──────────────────────────────────────┘

Scalable Architecture (Future)
┌──────────────────────────────────────┐
│         Load Balancer                │
└──────────────────────────────────────┘
                │
    ┌───────────┼───────────┐
    ▼           ▼           ▼
┌────────┐  ┌────────┐  ┌────────┐
│ App 1  │  │ App 2  │  │ App 3  │
└────────┘  └────────┘  └────────┘
    │           │           │
    └───────────┼───────────┘
                ▼
    ┌───────────────────────┐
    │   Shared Database     │
    │   (PostgreSQL)        │
    └───────────────────────┘
                │
    ┌───────────────────────┐
    │   Shared Storage      │
    │   (S3/NFS)            │
    └───────────────────────┘
```

This architecture document provides a comprehensive visual understanding of how all components work together in the Vehicle Damage Detection System.

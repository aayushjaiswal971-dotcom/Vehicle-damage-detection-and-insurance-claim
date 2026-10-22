from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from config import Config
from database.db_manager import DatabaseManager
from models.pipeline import DamageAssessmentPipeline

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY

# Initialize database
db = DatabaseManager(Config.DATABASE_PATH)

# Initialize damage assessment pipeline
pipeline = DamageAssessmentPipeline(Config)

# Create necessary directories
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
os.makedirs('models', exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not username or not email or not password:
            return render_template('register.html', error='All fields are required')
        
        success, result = db.register_user(username, email, password)
        
        if success:
            return redirect(url_for('login', message='Registration successful! Please login.'))
        else:
            return render_template('register.html', error=result)
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            return render_template('login.html', error='Email and password are required')
        
        success, result = db.login_user(email, password)
        
        if success:
            session['user_id'] = result['id']
            session['username'] = result['username']
            session['email'] = result['email']
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error=result)
    
    message = request.args.get('message')
    return render_template('login.html', message=message)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    history = db.get_user_history(session['user_id'])
    return render_template('dashboard.html', username=session['username'], history=history)

@app.route('/upload', methods=['POST'])
def upload():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    if 'image' not in request.files:
        return jsonify({'success': False, 'message': 'No image file provided'}), 400
    
    file = request.files['image']
    
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'message': 'Invalid file type. Only PNG, JPG, JPEG allowed'}), 400
    
    try:
        # Save uploaded file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{session['user_id']}_{timestamp}_{filename}"
        filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        # Process image through pipeline
        output_dir = os.path.join(Config.UPLOAD_FOLDER, f"results_{timestamp}")
        result = pipeline.process_image(filepath, output_dir)
        
        if result['success']:
            # Save to database
            db.save_prediction(
                session['user_id'],
                filepath,
                result['damaged_part'],
                result['severity'],
                result['damage_ratio'],
                result['estimated_cost']
            )
            
            return jsonify({
                'success': True,
                'damaged_part': result['damaged_part'],
                'severity': result['severity'],
                'damage_ratio': result['damage_ratio'],
                'estimated_cost': result['estimated_cost'],
                'image_path': filepath
            })
        else:
            return jsonify({
                'success': False,
                'message': result.get('message', 'Processing failed')
            }), 400
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/history')
def history():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    history = db.get_user_history(session['user_id'])
    return jsonify({'success': True, 'history': history})

if __name__ == '__main__':
    # Load models at startup
    print("Initializing application...")
    pipeline.load_models()
    print("Application ready!")
    
    app.run(debug=True, use_reloader=False, host='0.0.0.0', port=5000)

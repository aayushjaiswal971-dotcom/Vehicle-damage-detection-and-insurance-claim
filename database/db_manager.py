import sqlite3
import hashlib
from datetime import datetime
import os

class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.init_database()
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def init_database(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Prediction history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS prediction_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                image_path TEXT NOT NULL,
                damaged_part TEXT,
                severity_level TEXT,
                damage_ratio REAL,
                estimated_cost REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()
    
    def register_user(self, username, email, password):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            password_hash = self.hash_password(password)
            
            cursor.execute(
                'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
                (username, email, password_hash)
            )
            conn.commit()
            user_id = cursor.lastrowid
            conn.close()
            return True, user_id
        except sqlite3.IntegrityError:
            return False, "Email already registered"
    
    def login_user(self, email, password):
        conn = self.get_connection()
        cursor = conn.cursor()
        password_hash = self.hash_password(password)
        
        cursor.execute(
            'SELECT id, username FROM users WHERE email = ? AND password_hash = ?',
            (email, password_hash)
        )
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return True, {'id': user[0], 'username': user[1], 'email': email}
        return False, "Invalid email or password"
    
    def save_prediction(self, user_id, image_path, damaged_part, severity, damage_ratio, cost):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO prediction_history 
            (user_id, image_path, damaged_part, severity_level, damage_ratio, estimated_cost)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, image_path, damaged_part, severity, damage_ratio, cost))
        
        conn.commit()
        prediction_id = cursor.lastrowid
        conn.close()
        return prediction_id
    
    def get_user_history(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, image_path, damaged_part, severity_level, 
                   damage_ratio, estimated_cost, timestamp
            FROM prediction_history
            WHERE user_id = ?
            ORDER BY timestamp DESC
        ''', (user_id,))
        
        history = cursor.fetchall()
        conn.close()
        
        return [
            {
                'id': row[0],
                'image_path': row[1],
                'damaged_part': row[2],
                'severity_level': row[3],
                'damage_ratio': row[4],
                'estimated_cost': row[5],
                'timestamp': row[6]
            }
            for row in history
        ]

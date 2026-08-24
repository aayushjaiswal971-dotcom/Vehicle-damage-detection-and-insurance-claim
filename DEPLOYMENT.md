# Deployment Guide

This guide covers deploying the Vehicle Damage Detection System to production.

## Production Checklist

Before deploying to production:

- [ ] Train models on real labeled data
- [ ] Change SECRET_KEY in config.py
- [ ] Set up production database (PostgreSQL/MySQL)
- [ ] Configure HTTPS/SSL
- [ ] Set up proper logging
- [ ] Implement rate limiting
- [ ] Add input validation
- [ ] Set up monitoring
- [ ] Configure backups
- [ ] Test thoroughly

## Environment Setup

### 1. Production Configuration

Create a production config file `config_prod.py`:

```python
import os

class ProductionConfig:
    SECRET_KEY = os.environ.get('SECRET_KEY')  # Set via environment variable
    DATABASE_PATH = os.environ.get('DATABASE_URL', 'postgresql://user:pass@localhost/vehicle_damage')
    UPLOAD_FOLDER = '/var/www/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    
    # Security
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Logging
    LOG_LEVEL = 'INFO'
    LOG_FILE = '/var/log/vehicle_damage/app.log'
```

### 2. Use Production WSGI Server

Install Gunicorn:
```bash
pip install gunicorn
```

Create `wsgi.py`:
```python
from app import app

if __name__ == "__main__":
    app.run()
```

Run with Gunicorn:
```bash
gunicorn --workers 4 --bind 0.0.0.0:8000 wsgi:app
```

## Deployment Options

### Option 1: Traditional Server (Ubuntu/Debian)

#### Install System Dependencies

```bash
sudo apt-get update
sudo apt-get install python3-pip python3-venv nginx supervisor
```

#### Setup Application

```bash
# Create application directory
sudo mkdir -p /var/www/vehicle-damage
cd /var/www/vehicle-damage

# Clone/copy application files
# ...

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install gunicorn
```

#### Configure Nginx

Create `/etc/nginx/sites-available/vehicle-damage`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /static {
        alias /var/www/vehicle-damage/static;
    }

    client_max_body_size 16M;
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/vehicle-damage /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### Configure Supervisor

Create `/etc/supervisor/conf.d/vehicle-damage.conf`:

```ini
[program:vehicle-damage]
directory=/var/www/vehicle-damage
command=/var/www/vehicle-damage/venv/bin/gunicorn --workers 4 --bind 127.0.0.1:8000 wsgi:app
user=www-data
autostart=true
autorestart=true
stderr_logfile=/var/log/vehicle-damage/err.log
stdout_logfile=/var/log/vehicle-damage/out.log
```

Start application:
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start vehicle-damage
```

### Option 2: Docker Deployment

Create `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn

# Copy application
COPY . .

# Create directories
RUN mkdir -p database models static/uploads

# Expose port
EXPOSE 8000

# Run application
CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:8000", "wsgi:app"]
```

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./database:/app/database
      - ./models:/app/models
      - ./static/uploads:/app/static/uploads
    environment:
      - SECRET_KEY=your-secret-key-here
      - FLASK_ENV=production
    restart: unless-stopped
```

Build and run:
```bash
docker-compose up -d
```

### Option 3: Cloud Platforms

#### AWS Elastic Beanstalk

1. Install EB CLI:
```bash
pip install awsebcli
```

2. Initialize:
```bash
eb init -p python-3.9 vehicle-damage
```

3. Create environment:
```bash
eb create vehicle-damage-env
```

4. Deploy:
```bash
eb deploy
```

#### Google Cloud Platform

1. Create `app.yaml`:
```yaml
runtime: python39
entrypoint: gunicorn -b :$PORT wsgi:app

instance_class: F2

automatic_scaling:
  min_instances: 1
  max_instances: 10
```

2. Deploy:
```bash
gcloud app deploy
```

#### Heroku

1. Create `Procfile`:
```
web: gunicorn wsgi:app
```

2. Deploy:
```bash
heroku create vehicle-damage-app
git push heroku main
```

## Database Migration

For production, migrate from SQLite to PostgreSQL:

### Install PostgreSQL adapter
```bash
pip install psycopg2-binary
```

### Update database manager
Modify `database/db_manager.py` to support PostgreSQL:

```python
import psycopg2
from psycopg2.extras import RealDictCursor

class DatabaseManager:
    def __init__(self, db_url):
        self.db_url = db_url
        self.init_database()
    
    def get_connection(self):
        return psycopg2.connect(self.db_url)
    
    # Update methods to use psycopg2...
```

## Security Hardening

### 1. Environment Variables

Create `.env` file (never commit to git):
```
SECRET_KEY=your-very-secret-key-here
DATABASE_URL=postgresql://user:pass@localhost/dbname
FLASK_ENV=production
```

Load in application:
```python
from dotenv import load_dotenv
load_dotenv()
```

### 2. Rate Limiting

Install Flask-Limiter:
```bash
pip install Flask-Limiter
```

Add to `app.py`:
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@app.route('/upload', methods=['POST'])
@limiter.limit("10 per minute")
def upload():
    # ...
```

### 3. HTTPS/SSL

Use Let's Encrypt with Certbot:
```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### 4. Input Validation

Add comprehensive validation:
```python
from werkzeug.utils import secure_filename
import magic

def validate_image(file):
    # Check file size
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    
    if size > 16 * 1024 * 1024:
        return False, "File too large"
    
    # Check MIME type
    mime = magic.from_buffer(file.read(1024), mime=True)
    file.seek(0)
    
    if mime not in ['image/jpeg', 'image/png']:
        return False, "Invalid file type"
    
    return True, "Valid"
```

## Monitoring and Logging

### Setup Logging

```python
import logging
from logging.handlers import RotatingFileHandler

if not app.debug:
    file_handler = RotatingFileHandler(
        'logs/vehicle_damage.log',
        maxBytes=10240000,
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Vehicle Damage Detection startup')
```

### Application Monitoring

Use services like:
- Sentry for error tracking
- New Relic for performance monitoring
- Datadog for infrastructure monitoring

## Backup Strategy

### Database Backups

Automated PostgreSQL backup:
```bash
#!/bin/bash
# backup.sh
BACKUP_DIR="/backups/database"
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump vehicle_damage > "$BACKUP_DIR/backup_$DATE.sql"
find $BACKUP_DIR -mtime +7 -delete  # Keep 7 days
```

Add to crontab:
```bash
0 2 * * * /path/to/backup.sh
```

### Model Backups

Backup trained models regularly:
```bash
tar -czf models_backup_$(date +%Y%m%d).tar.gz models/
```

## Performance Optimization

### 1. Model Optimization

- Use TorchScript for faster inference
- Quantize models for reduced size
- Use ONNX runtime for cross-platform optimization

### 2. Caching

Install Redis:
```bash
pip install redis flask-caching
```

Add caching:
```python
from flask_caching import Cache

cache = Cache(app, config={'CACHE_TYPE': 'redis'})

@cache.memoize(timeout=300)
def process_image(image_path):
    # ...
```

### 3. CDN for Static Files

Use CloudFlare, AWS CloudFront, or similar for static assets.

## Scaling Considerations

### Horizontal Scaling

- Use load balancer (Nginx, HAProxy)
- Deploy multiple application instances
- Share session storage (Redis)
- Use shared file storage (S3, NFS)

### Vertical Scaling

- Increase server resources
- Optimize model inference
- Use GPU instances for processing

## Maintenance

### Regular Tasks

- Monitor disk space
- Review logs for errors
- Update dependencies
- Retrain models with new data
- Test backup restoration
- Security updates

### Health Checks

Add health check endpoint:
```python
@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'models_loaded': pipeline.model is not None,
        'database': check_database_connection()
    })
```

## Troubleshooting Production Issues

### High Memory Usage
- Reduce batch size
- Implement model unloading
- Use model quantization

### Slow Response Times
- Enable caching
- Optimize database queries
- Use CDN for static files
- Scale horizontally

### Database Connection Issues
- Implement connection pooling
- Add retry logic
- Monitor connection limits

## Support and Maintenance

For production support:
1. Set up monitoring alerts
2. Create runbook for common issues
3. Document deployment process
4. Train operations team
5. Establish on-call rotation

## Conclusion

This deployment guide covers the essentials for production deployment. Adjust based on your specific requirements, scale, and infrastructure.

@echo off
echo ============================================================
echo  ClaimSense AI — Django Setup (Windows)
echo ============================================================

REM 1. Create virtual environment
python -m venv venv
call venv\Scripts\activate.bat

REM 2. Install all dependencies
pip install -r requirements.txt

REM 3. Copy .env.example to .env if it doesn't exist
if not exist .env (
    copy .env.example .env
    echo.
    echo [!] Created .env from .env.example
    echo     Please open .env and fill in your real credentials before continuing.
    echo     Required: SECRET_KEY, DB_*, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET,
    echo               AWS_*, GEMINI_API_KEY
    pause
)

REM 4. Apply Django migrations
python manage.py migrate

REM 5. Create a superuser (optional)
echo.
set /p CREATE_SU="Create a Django superuser? (y/n): "
if /i "%CREATE_SU%"=="y" python manage.py createsuperuser

REM 6. Run the development server
echo.
echo Starting Django development server at http://127.0.0.1:8000/
python manage.py runserver

pause

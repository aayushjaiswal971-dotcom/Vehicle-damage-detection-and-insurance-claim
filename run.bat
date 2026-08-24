@echo off
echo ========================================
echo Vehicle Damage Detection System
echo ========================================
echo.

echo Checking Python installation...
python --version
if errorlevel 1 (
    echo Python is not installed or not in PATH
    pause
    exit /b 1
)
echo.

echo Starting application...
echo.
echo The application will be available at:
echo http://localhost:5000
echo.
echo Press Ctrl+C to stop the server
echo.

python app.py

pause

@echo on
echo Starting Django...

REM Activate the virtual environment
call "C:\Users\pyspiders(jntu)\OneDrive\Desktop\hr_project\env\Scripts\activate.bat"

REM Navigate to Django project folder
cd /d "C:\Users\pyspiders(jntu)\OneDrive\Desktop\hr_project\hrfsdi"

REM Start Django development server
python manage.py runserver 0.0.0.0:8000

echo Django exited with code %ERRORLEVEL%
pause

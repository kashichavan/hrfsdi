@echo off
setlocal enabledelayedexpansion

:: ==============================================
:: Configuration Section
:: ==============================================
set SERVICE_NAME=DjangoServer
set "PROJECT_DIR=C:\hr_project\hrfsdi"
set "BAT_FILE=%PROJECT_DIR%\start_django.bat"
set "NSSM_DIR=C:\nssm"
set LOG_DATE=%date:~-4%-%date:~3,2%-%date:~0,2%_%time:~0,2%-%time:~3,2%

:: ==============================================
:: Pre-Checks with Detailed Logging
:: ==============================================
echo [%LOG_DATE%] Starting installation >> "%PROJECT_DIR%\install.log"

echo Checking NSSM installation...
if not exist "%NSSM_DIR%\nssm.exe" (
    echo [ERROR] nssm.exe missing in %NSSM_DIR% >> "%PROJECT_DIR%\install.log"
    echo Error: nssm.exe not found at %NSSM_DIR%
    echo Download from https://nssm.cc/download and copy to this location
    pause
    exit /b 1
)

echo Verifying project structure...
if not exist "%PROJECT_DIR%\manage.py" (
    echo [ERROR] Django project not found at %PROJECT_DIR% >> "%PROJECT_DIR%\install.log"
    echo Error: Django project files missing in %PROJECT_DIR%
    echo Verify these files exist:
    echo - manage.py
    echo - start_django.bat
    pause
    exit /b 1
)

:: ==============================================
:: Service Installation (Revised Method)
:: ==============================================
echo Cleaning up previous installation...
"%NSSM_DIR%\nssm.exe" stop %SERVICE_NAME% >> "%PROJECT_DIR%\install.log" 2>&1
"%NSSM_DIR%\nssm.exe" remove %SERVICE_NAME% confirm >> "%PROJECT_DIR%\install.log" 2>&1

echo Creating service with DEBUG parameters...
"%NSSM_DIR%\nssm.exe" install %SERVICE_NAME% ^
"%BAT_FILE%" ^
>> "%PROJECT_DIR%\install.log" 2>&1

if errorlevel 1 (
    echo [ERROR] Service installation failed >> "%PROJECT_DIR%\install.log"
    echo Failed to install service. Check install.log
    pause
    exit /b 1
)

:: ==============================================
:: Critical Service Configuration
:: ==============================================
echo Configuring service...
"%NSSM_DIR%\nssm.exe" set %SERVICE_NAME% AppDirectory "%PROJECT_DIR%"
"%NSSM_DIR%\nssm.exe" set %SERVICE_NAME% DisplayName "Django Production Server"
"%NSSM_DIR%\nssm.exe" set %SERVICE_NAME% AppStdout "%PROJECT_DIR%\service.log"
"%NSSM_DIR%\nssm.exe" set %SERVICE_NAME% AppStderr "%PROJECT_DIR%\service.log"
"%NSSM_DIR%\nssm.exe" set %SERVICE_NAME% AppStopMethodSkip 6000
"%NSSM_DIR%\nssm.exe" set %SERVICE_NAME% Start SERVICE_AUTO_START

:: ==============================================
:: Service Account Configuration
:: ==============================================
echo Setting service credentials...
"%NSSM_DIR%\nssm.exe" set %SERVICE_NAME% ObjectName ".\YourWindowsUsername" "YourPassword"

:: ==============================================
:: Final Activation Sequence
:: ==============================================
echo Starting service...
"%NSSM_DIR%\nssm.exe" start %SERVICE_NAME%

timeout /t 10 >nul

echo Service Status:
"%NSSM_DIR%\nssm.exe" status %SERVICE_NAME%

echo Debugging Information:
echo 1. Full installation log: %PROJECT_DIR%\install.log
echo 2. Service output: %PROJECT_DIR%\service.log
echo 3. Event Viewer: Windows Logs -> Application

:: ==============================================
:: Post-Installation Test
:: ==============================================
echo Testing Django server...
curl -I http://localhost:8000 >> "%PROJECT_DIR%\install.log" 2>&1
if errorlevel 1 (
    echo [WARNING] Django server not responding on port 8000 >> "%PROJECT_DIR%\install.log"
    echo Warning: Server not responding. Check service.log
)

pause
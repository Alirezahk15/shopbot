@echo off
echo ============================================
echo   Shop Bot + Web Panel - Windows Installer
echo ============================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

REM Check Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found. Please install Node.js 18+ from https://nodejs.org
    pause
    exit /b 1
)

echo [1/4] Installing Python bot dependencies...
pip install -r requirements.txt
if errorlevel 1 ( echo [ERROR] Failed to install bot dependencies & pause & exit /b 1 )

echo.
echo [2/4] Installing Python API dependencies...
pip install -r api\requirements.txt
if errorlevel 1 ( echo [ERROR] Failed to install API dependencies & pause & exit /b 1 )

echo.
echo [3/4] Installing Node.js panel dependencies...
cd panel
npm install
if errorlevel 1 ( echo [ERROR] Failed to install panel dependencies & cd .. & pause & exit /b 1 )

echo.
echo [4/4] Building React panel for production...
npm run build
if errorlevel 1 ( echo [ERROR] Failed to build panel & cd .. & pause & exit /b 1 )
cd ..

echo.
echo ============================================
echo   Installation Complete!
echo ============================================
echo.
echo Next steps:
echo   1. Edit .env and set your credentials
echo   2. Run start.bat to launch everything
echo.
pause

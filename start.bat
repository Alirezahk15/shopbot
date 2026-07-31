@echo off
echo ============================================
echo   Starting Shop Bot + Web Panel
echo ============================================
echo.

REM Start Telegram Bot in a new window
start "Telegram Bot" cmd /k "python main.py"

REM Wait a moment
timeout /t 2 /nobreak >nul

REM Start FastAPI backend in a new window
start "Web API (port 8000)" cmd /k "uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload"

REM Wait a moment
timeout /t 2 /nobreak >nul

REM Start React dev server in a new window (for development)
REM Comment this out in production (use the built panel served by FastAPI instead)
start "Web Panel Dev (port 3000)" cmd /k "cd panel && npm run dev"

echo.
echo All services started!
echo.
echo   Telegram Bot:  Running in background
echo   Web API:       http://localhost:8000
echo   Web Panel:     http://localhost:3000
echo   API Docs:      http://localhost:8000/docs
echo.
echo Press any key to close this window (services will keep running)
pause >nul

@echo off
setlocal

echo ============================================
echo   FantaMazor - Avvio
echo ============================================
echo.

start "FantaMazor - Backend" cmd /k "cd /d %~dp0backend && call .venv\Scripts\activate && uvicorn app.main:app --reload --port 8000"

timeout /t 3 /nobreak >nul

start "FantaMazor - Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo Backend e frontend avviati in due finestre separate.
echo Tra pochi secondi apri il browser su:  http://localhost:3000
echo.
echo Per chiudere FantaMazor, chiudi semplicemente quelle due finestre nere.
echo.

timeout /t 6 /nobreak >nul
start "" "http://localhost:3000"

pause

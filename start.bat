@echo off
echo Starting AMY Chatbot...

echo Starting Docker services (postgres + redis)...
docker-compose up postgres redis -d

echo Starting backend...
start "AMY Backend" cmd /k "cd /d "%~dp0backend" && venv\Scripts\activate && uvicorn app.main:app --reload --port 8000"

echo Starting frontend...
start "AMY Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo.
echo Services started:
echo   Backend  -^> http://localhost:8000
echo   API Docs -^> http://localhost:8000/docs
echo   Frontend -^> http://localhost:5173
echo.
pause

@echo off
echo ===============================
echo   Morphlink Runner
echo ===============================
echo Choose mode:
echo 1. Monolith (single service)
echo 2. Microservices (links + redirector + analytics + autopilot)
set /p choice="Enter choice (1/2): "

if "%choice%"=="1" (
    echo Starting Monolith...
    start cmd /k "uvicorn app.main:app --reload --port 8000"
    goto end
)

if "%choice%"=="2" (
    echo Starting Microservices...
    start cmd /k "uvicorn links_service:app --reload --port 8001"
    start cmd /k "uvicorn redirector_service:app --reload --port 8002"
    start cmd /k "uvicorn analytics_service:app --reload --port 8003"
    start cmd /k "python -m app.autopilot.controller"
    goto end
)

:end
echo Done. Windows opened for services.

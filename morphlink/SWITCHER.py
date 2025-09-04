import os
import uvicorn
import httpx
import subprocess
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from app.common import switch, metrics
from app.common.logging_config import setup_logging, get_logger
from app.main import app as monolith_app
from app.autopilot.controller import check_and_switch
from starlette.testclient import TestClient
import threading
import asyncio
import time

setup_logging()
logger = get_logger("dispatcher")

app = FastAPI(title="Dispatcher Service")

# Keep track of running microservice processes
MICROSERVICE_PROCESSES = {}

# Map module to service file
SERVICE_FILES = {
    "links": "links_service.py",
    "redirector": "redirector_service.py",
    "analytics": "analytics_service.py"
}

# Middleware to record RPM
@app.middleware("http")
async def record_requests_middleware(request: Request, call_next):
    path = request.url.path
    if path.startswith("/links"):
        metrics.record_request("links")
    elif path.startswith("/r"):
        metrics.record_request("redirector")
    elif path.startswith("/analytics"):
        metrics.record_request("analytics")
    return await call_next(request)


def start_microservice(module: str):
    """Start the microservice process if not already running"""
    if module in MICROSERVICE_PROCESSES and MICROSERVICE_PROCESSES[module].poll() is None:
        # Already running
        return

    service_file = SERVICE_FILES[module]
    logger.info(f"Starting microservice for {module} using {service_file}")
    # Start in new console window
    process = subprocess.Popen(
        ["python", service_file],
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )
    MICROSERVICE_PROCESSES[module] = process
    # Give service a few seconds to start
    time.sleep(2)


async def forward_request(request: Request, service_url: str):
    async with httpx.AsyncClient() as client:
        url = f"{service_url}{request.url.path}"
        try:
            if request.method == "GET":
                r = await client.get(url, params=request.query_params, timeout=5)
            elif request.method == "POST":
                r = await client.post(url, json=await request.json(), timeout=5)
            elif request.method == "PUT":
                r = await client.put(url, json=await request.json(), timeout=5)
            elif request.method == "DELETE":
                r = await client.delete(url, params=request.query_params, timeout=5)
            else:
                return JSONResponse({"error": "Method not supported"}, status_code=405)
        except Exception as e:
            logger.warning(f"Microservice {service_url} unreachable: {e}")
            return JSONResponse({"error": "Microservice unreachable"}, status_code=503)

    # Handle redirects
    if r.status_code in (301, 302):
        location = r.headers.get("location", "/")
        return RedirectResponse(url=location, status_code=r.status_code)

    return JSONResponse(r.json(), status_code=r.status_code)


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def main_router(request: Request, path: str):
    module = None
    if path.startswith("links"):
        module = "links"
    elif path.startswith("r"):
        module = "redirector"
    elif path.startswith("analytics"):
        module = "analytics"

    if not module:
        return JSONResponse({"error": "Invalid path"}, status_code=404)

    # Check and switch mode
    check_and_switch(module)
    mode = switch.ACTIVE_MODULES[module]
    logger.info(f"Dispatcher routing: {module} mode={mode}")

    if mode == "monolith":
        client = TestClient(monolith_app)
        if request.method == "GET":
            r = client.get(request.url.path, params=request.query_params)
        elif request.method == "POST":
            r = client.post(request.url.path, json=await request.json())
        elif request.method == "PUT":
            r = client.put(request.url.path, json=await request.json())
        elif request.method == "DELETE":
            r = client.delete(request.url.path, params=request.query_params)
        # Preserve redirect responses
        if r.status_code in (301, 302):
            return RedirectResponse(url=r.headers["location"], status_code=r.status_code)
        return JSONResponse(r.json(), status_code=r.status_code)
    else:
        # Start microservice if not running
        start_microservice(module)
        service_url = switch.URLS[module]
        return await forward_request(request, service_url)


if __name__ == "__main__":
    # Background autopilot loop
    def run_autopilot_loop():
        while True:
            for module_name in switch.ACTIVE_MODULES.keys():
                check_and_switch(module_name)
            time.sleep(10)

    t = threading.Thread(target=run_autopilot_loop, daemon=True)
    t.start()

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

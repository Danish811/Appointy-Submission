import time, requests
from app.common import switch, metrics
from app.common.logging_config import get_logger

logger = get_logger("autopilot")

THRESHOLDS = {"redirector": 50, "analytics": 50, "links": 50}

def check_and_switch(module: str):
    rpm = metrics.get_rpm(module)
    mode = switch.ACTIVE_MODULES[module]
    threshold = THRESHOLDS[module]

    logger.info(f"[Autopilot] {module}: {rpm} rpm (mode={mode})")

    if rpm > threshold and mode == "monolith":
        url = switch.URLS[module]
        try:
            r = requests.get(f"{url}/health", timeout=2)
            if r.status_code == 200:
                switch.ACTIVE_MODULES[module] = "microservice"
                logger.info(f"[Autopilot] Scaled {module} → microservice (rpm={rpm})")
        except Exception as e:
            logger.warning(f"[Autopilot] {module} microservice not reachable: {e}")
    elif rpm < threshold * 0.5 and mode == "microservice":
        switch.ACTIVE_MODULES[module] = "monolith"
        logger.info(f"[Autopilot] Scaled {module} → monolith (rpm={rpm})")

def run_autopilot():
    logger.info("[Autopilot] Started monitoring loop")
    while True:
        for module in switch.ACTIVE_MODULES.keys():
            check_and_switch(module)
        time.sleep(10)

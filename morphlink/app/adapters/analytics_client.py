import httpx
from app.analytics import service
from app.common import config, switch
from app.common.worker import submit_task
from app.common.logging_config import get_logger

logger = get_logger("analytics.client")

def record_click(code: str):
    mode = switch.ACTIVE_MODULES.get("analytics", "monolith")
    logger.info(f"record_click({code}) mode={mode}")

    if mode == "monolith":
        submit_task(service.record_click, code)
    else:
        try:
            httpx.post(f"{switch.URLS['analytics']}/events", json={"short_code": code}, timeout=1.0)
            logger.debug(f"Click sent to analytics service for {code}")
        except Exception as e:
            logger.warning(f"Analytics service not reachable: {e}")

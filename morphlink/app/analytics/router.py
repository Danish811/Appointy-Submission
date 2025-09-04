from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.common.db import get_db
from app.common import models, utils
from app.common.metrics import record_request
from app.common.logging_config import get_logger
from app.analytics import service

logger = get_logger("analytics.router")
router = APIRouter()

@router.get("/health")
def health_check():
    return {"status": "ok"}

# Get analytics for all links owned by a user
@router.get("/")
def get_user_stats(user: str = Query(...), db: Session = Depends(get_db)):
    record_request("analytics")
    owner_id = utils.get_user(user)
    return service.get_user_stats(owner_id, db)

# Get analytics for a specific link
@router.get("/{code}")
def get_link_stats(code: str, user: str, db: Session = Depends(get_db)):
    record_request("analytics")
    owner_id = utils.get_user(user)
    result = service.get_link_stats(owner_id, code, db)
    if not result:
        raise HTTPException(404, "Link not found or not yours")
    return result

@router.get("/metrics")
def metrics():
    from app.common.metrics import get_rpm
    return {"analytics_rpm": get_rpm("analytics")}

# (Optional) Microservice mode internal API
@router.post("/events")
def record_event(short_code: str):
    record_request("analytics")
    service.record_click(short_code)
    return {"status": "ok"}

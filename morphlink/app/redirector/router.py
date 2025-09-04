from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.common.db import get_db
from app.common import models
from app.adapters.analytics_client import record_click
from app.common.metrics import record_request
from app.common.logging_config import get_logger
from dotenv import load_dotenv
import redis
import os
logger = get_logger("redirector")
load_dotenv()
redis_pass = os.environ.get("REDIS_PASS")
r = redis.Redis(
    host='redis-18026.c17.us-east-1-4.ec2.redns.redis-cloud.com',
    port=18026,
    decode_responses=True,
    username="default",
    password=redis_pass,
)

router = APIRouter()

@router.get("/health")
def health_check():
    return {"status": "ok"}

@router.get("/{code}")
def redirect(code: str, db: Session = Depends(get_db)):
    record_request("redirector")
    long_url = r.get(code)

    if long_url:
        logger.info(f"Cache hit: {code} -> {long_url}")
    else:
        link = db.query(models.Link).filter_by(short_code=code).first()
        if not link:
            logger.warning(f"Redirect failed: {code} not found")
            raise HTTPException(status_code=404, detail="Link not found")

        long_url = link.long_url
        r.set(code, long_url, ex=3600) 
        logger.info(f"Cache miss: storing {code} -> {long_url} in Redis")

    # Always call via adapter (thread or HTTP depending on MODE)
    logger.info(f"Redirecting {code} -> {link.long_url}")

    return RedirectResponse(url=link.long_url)

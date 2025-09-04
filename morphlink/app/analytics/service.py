from app.common.db import SessionLocal
from app.common import models
from datetime import datetime
from sqlalchemy import func
from app.common.logging_config import get_logger

logger = get_logger("analytics.service")

def record_click(code: str):
    logger.info(f"Recording click for {code}")
    db = SessionLocal()
    try:
        db.add(models.Analytics(short_code=code, timestamp=datetime.utcnow()))
        db.commit()
    finally:
        db.close()
    logger.info(f"Click recorded for {code}")

def get_user_stats(owner_id: int, db):
    results = (
        db.query(models.Link.short_code,
                 models.Link.long_url,
                 func.count(models.Analytics.id).label("clicks"))
        .join(models.Analytics, models.Link.short_code == models.Analytics.short_code, isouter=True)
        .filter(models.Link.owner_id == owner_id)
        .group_by(models.Link.short_code, models.Link.long_url)
        .all()
    )
    return [
        {"short_code": r[0], "long_url": r[1], "clicks": r[2]}
        for r in results
    ]

def get_link_stats(owner_id: int, code: str, db):
    link = db.query(models.Link).filter_by(short_code=code, owner_id=owner_id).first()
    if not link:
        return None
    clicks = db.query(func.count(models.Analytics.id)).filter_by(short_code=code).scalar()
    return {"short_code": code, "long_url": link.long_url, "clicks": clicks}

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.common.db import get_db
from app.common import models, utils
from app.common.metrics import record_request
from app.common.logging_config import get_logger

logger = get_logger("links")
router = APIRouter()

@router.get("/health")
def health_check():
    return {"status": "ok"}

@router.post("/")
def create_link(url: str, user: str, db: Session = Depends(get_db)):
    owner_id = utils.get_user(user)
    code = utils.generate_code()
    while db.query(models.Link).filter_by(short_code=code).first():
        code = utils.generate_code()
    link = models.Link(short_code=code, long_url=url, owner_id=owner_id)
    db.add(link)
    db.commit()
    db.refresh(link)
    return {"short_code": link.short_code, "long_url": link.long_url, "owner_id": link.owner_id}

@router.get("/")
def list_links(user: str, db: Session = Depends(get_db)):
    owner_id = utils.get_user(user)
    return db.query(models.Link).filter_by(owner_id=owner_id).all()

@router.get("/{code}")
def get_link(code: str, user: str, db: Session = Depends(get_db)):
    owner_id = utils.get_user(user)
    link = db.query(models.Link).filter_by(short_code=code, owner_id=owner_id).first()
    if not link:
        raise HTTPException(404, "Link not found")
    return {"short_code": link.short_code, "long_url": link.long_url, "created_at": link.created_at}

@router.put("/{code}")
def update_link(code: str, url: str, user: str, db: Session = Depends(get_db)):
    owner_id = utils.get_user(user)
    link = db.query(models.Link).filter_by(short_code=code, owner_id=owner_id).first()
    if not link:
        raise HTTPException(404, "Link not found")
    link.long_url = url
    db.commit()
    return {"short_code": link.short_code, "long_url": link.long_url}

@router.delete("/{code}")
def delete_link(code: str, user: str, db: Session = Depends(get_db)):
    owner_id = utils.get_user(user)
    link = db.query(models.Link).filter_by(short_code=code, owner_id=owner_id).first()
    if not link:
        raise HTTPException(404, "Link not found")
    db.delete(link)
    db.commit()
    return {"deleted": True}

@router.get("/metrics")
def metrics():
    from app.common.metrics import get_rpm
    return {"links_rpm": get_rpm("links")}

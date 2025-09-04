from fastapi import FastAPI
from app.common.db import Base, engine
from app.links.router import router as links_router
from app.redirector.router import router as redirector_router
from app.analytics.router import router as analytics_router
from app.common.logging_config import setup_logging

setup_logging()
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Morphlink Monolith")

app.include_router(links_router, prefix="/links", tags=["links"])
app.include_router(redirector_router, prefix="/r", tags=["redirector"])
app.include_router(analytics_router, prefix="/analytics", tags=["analytics"])

from fastapi import FastAPI
from app.common.db import Base, engine
from app.analytics.router import router as analytics_router
from app.common.logging_config import setup_logging

setup_logging()
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Analytics Service")
app.include_router(analytics_router, prefix="/analytics", tags=["analytics"])

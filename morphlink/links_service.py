from fastapi import FastAPI
from app.common.db import Base, engine
from app.links.router import router as links_router
from app.common.logging_config import setup_logging

setup_logging()
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Links Service")
app.include_router(links_router, prefix="/links", tags=["links"])

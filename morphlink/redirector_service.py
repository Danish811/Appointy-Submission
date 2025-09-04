from fastapi import FastAPI, APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import redis
import os
from app.common.db import get_db
from app.common import models
from app.adapters.analytics_client import record_click
from app.common.metrics import record_request
from app.common.logging_config import setup_logging, get_logger
from app.redirector.router import router as redirector_router

# Setup logging
setup_logging()
logger = get_logger("redirector")

app = FastAPI(title="Redirector Service")

app.include_router(router, prefix="/r", tags=["redirector"])


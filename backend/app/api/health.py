from fastapi import APIRouter
from datetime import datetime, timezone
from app.core.config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("/health")
async def health_check():
    """Basic health check — confirms API is running"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": settings.app_env,
        "version": "1.0.0",
    }


@router.get("/")
async def root():
    return {
        "name": "Zero Trust Security Dashboard API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }

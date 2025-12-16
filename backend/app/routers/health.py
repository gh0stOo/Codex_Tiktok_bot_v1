from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text
from ..db import SessionLocal
from ..config import get_settings
import redis

router = APIRouter()
settings = get_settings()


@router.get("/")
def health():
    return {"status": "ok"}


@router.get("/healthz")
def healthz():
    """Basic health check - always returns ok if service is running"""
    return {"status": "ok"}


@router.get("/readyz")
def readyz():
    """Readiness check - verifies DB and Redis connections"""
    errors = []
    
    # Check database connection
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
    except Exception as e:
        errors.append(f"Database connection failed: {str(e)}")
    
    # Check Redis connection
    try:
        r = redis.from_url(settings.redis_url)
        r.ping()
    except Exception as e:
        errors.append(f"Redis connection failed: {str(e)}")
    
    if errors:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not ready", "errors": errors}
        )
    
    return {"status": "ready"}

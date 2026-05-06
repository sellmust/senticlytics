"""
Health Check Routes
System health monitoring endpoints
"""

from datetime import datetime
from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from backend.database import AsyncSessionLocal, test_connection
from backend.rag_pipeline import get_rag_pipeline
from backend.gemini_service import get_gemini_service
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("")
async def health():
    """
    Health check endpoint
    Returns system status
    """
    try:
        # Test database
        db_ok = await test_connection()
        
        # Test RAG
        rag = get_rag_pipeline()
        rag_ok = rag.health_check()
        
        # Test Gemini (if available)
        try:
            gemini = await get_gemini_service()
            gemini_ok = await gemini.health_check()
        except:
            gemini_ok = False
        
        status = "healthy" if all([db_ok, rag_ok]) else "degraded"
        
        return {
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "database": "ok" if db_ok else "down",
                "rag_pipeline": "ok" if rag_ok else "down",
                "gemini_api": "ok" if gemini_ok else "down"
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }, 503

@router.get("/ready")
async def ready():
    """
    Readiness check
    Returns if service is ready to accept requests
    """
    try:
        db_ok = await test_connection()
        
        if not db_ok:
            raise HTTPException(status_code=503, detail="Database not ready")
        
        return {
            "ready": True,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@router.get("/live")
async def live():
    """
    Liveness check
    Returns if service is running
    """
    return {
        "alive": True,
        "timestamp": datetime.utcnow().isoformat()
    }
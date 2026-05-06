"""
Customer Feedback Intelligence Platform - FastAPI Backend
Main application entry point
"""

import os
import logging
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from backend.routes import feedback, health

load_dotenv()

logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def startup_event():
    logger.info("Starting Customer Feedback Intelligence Platform...")

    from backend.database import init_db
    await init_db()
    logger.info("✓ Database initialized")

    try:
        from backend.rag_pipeline import RAGPipeline
        global rag_pipeline
        rag_pipeline = RAGPipeline()
        logger.info("✓ RAG Pipeline initialized")
    except Exception as e:
        logger.warning(f"⚠ RAG Pipeline initialization failed: {str(e)}")

    logger.info("✓ All services started successfully")

async def shutdown_event():
    logger.info("Shutting down services...")
    logger.info("✓ Shutdown complete")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await startup_event()
    yield
    await shutdown_event()

app = FastAPI(
    title="Customer Feedback Intelligence API",
    description="AI-powered feedback analysis with RAG + Gemini sentiment classification",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

origins = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.debug(f"{request.method} {request.url.path}")
    response = await call_next(request)
    return response

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(feedback.router, prefix="/api/v1/feedback", tags=["Feedback"])


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Customer Feedback Intelligence API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "operational"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=os.getenv('FASTAPI_HOST', '0.0.0.0'),
        port=int(os.getenv('FASTAPI_PORT', 8000)),
        workers=int(os.getenv('FASTAPI_WORKERS', 2)),
        reload=os.getenv('FASTAPI_ENV') == 'development',
        log_level=os.getenv('LOG_LEVEL', 'info').lower()
    )
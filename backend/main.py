import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import logging

from routes.query import router as query_router
from routes.auth import router as auth_router
from routes.feedback import router as feedback_router

load_dotenv()

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Legal AI Backend",
    description="RAG-based Legal AI System using Ollama phi3",
    version="1.0.0"
)

# CORS configuration
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
allow_credentials = os.getenv("ALLOW_CREDENTIALS", "true").lower() == "true"
allow_methods = os.getenv("ALLOW_METHODS", "GET,POST,PUT,DELETE,OPTIONS").split(",")
allow_headers = os.getenv("ALLOW_HEADERS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=allow_credentials,
    allow_methods=allow_methods,
    allow_headers=allow_headers,
)

# Routers
app.include_router(auth_router, prefix="/api")
app.include_router(query_router, prefix="/api")
app.include_router(feedback_router, prefix="/api")


@app.on_event("startup")
async def startup_check():
    """Validate config on startup"""
    try:
        from models.llm_config import config
        config.validate_config()
        logger.info("Startup check complete")
    except Exception as e:
        logger.error(f"Startup check warning: {e}")


@app.get("/")
def root():
    return {
        "message": "Legal AI backend running",
        "version": "1.0.0",
        "status": "active"
    }


@app.get("/health")
def health_check():
    """Health check with Ollama status"""
    try:
        from models.llm_provider import get_llm_provider

        provider = get_llm_provider()
        is_ready = provider.check_connection()

        return {
            "status": "healthy" if is_ready else "warning",
            "ollama_ready": is_ready,
            "message": "System ready" if is_ready else "Ollama initializing... please wait"
        }
    except Exception as e:
        logger.warning(f"Health check warning: {e}")
        return {
            "status": "warning",
            "ollama_ready": False,
            "message": f"Initializing LLM provider: {str(e)[:100]}"
        }
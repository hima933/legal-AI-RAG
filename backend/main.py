import os
from fastapi import FastAPI, Request
from routes.query import router as query_router
from routes.auth import router as auth_router
from routes.feedback import router as feedback_router
from routes.evaluation import router as evaluation_router
from fastapi.middleware.cors import CORSMiddleware
from routes.upload import router as upload_router
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Legal AI Backend",
    description="RAG-based Legal AI System",
    version="1.0.0"
)

# Parse CORS origins from environment
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

# Include routers
app.include_router(auth_router, prefix="/api")
app.include_router(query_router, prefix="/api")
app.include_router(upload_router, prefix="/api")
app.include_router(feedback_router, prefix="/api")
app.include_router(evaluation_router, prefix="/api")

@app.on_event("startup")
async def startup_check():
    """Perform startup checks and auto-recovery"""
    try:
        # Validate LLM config and fallbacks
        from models.llm_config import config
        config.validate_config()

        from vectorstore.faiss_store import get_index_info
        # This will trigger the internal consistency check and auto-recover if needed
        info = get_index_info()
        if not info.get("consistent", False):
            logger.warning("Startup: Index inconsistency detected. Triggering recovery...")
            # Recovery is handled by the store on load/access, but we log it here
            logger.info(f"Index state: {info}")
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
    """Health check endpoint with Ollama status"""
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


@app.get("/api/models/ollama")
def get_ollama_models():
    """Get list of available Ollama models"""
    try:
        from models.llm_provider import get_available_ollama_models, get_selected_model
        
        available_models = get_available_ollama_models()
        selected = get_selected_model()
        
        return {
            "status": "success",
            "models": available_models,
            "current_selection": selected,
            "count": len(available_models)
        }
    except Exception as e:
        logger.error(f"Error fetching models: {e}")
        return {
            "status": "error",
            "error": str(e),
            "models": []
        }


@app.post("/api/models/select")
async def select_model(request: Request):
    """Set the selected Ollama model"""
    try:
        data = await request.json()
        model_name = data.get("model")
        if not model_name:
            return {"status": "error", "error": "Model name required"}
        
        from models.llm_provider import set_selected_model
        result = set_selected_model(model_name)
        return result
    except Exception as e:
        logger.error(f"Error setting model: {e}")
        return {"status": "error", "error": str(e)}


@app.get("/api/models/recommendations")
def get_model_recommendations():
    """Get model recommendations based on hardware"""
    try:
        from models.llm_provider import get_model_recommendations
        recommendations = get_model_recommendations()
        return {
            "status": "success",
            "recommendations": recommendations
        }
    except Exception as e:
        logger.error(f"Error fetching recommendations: {e}")
        return {"status": "error", "error": str(e)}


# ============================================
# INDEX RECOVERY & MAINTENANCE ENDPOINTS
# ============================================

@app.get("/api/index/status")
def get_index_status():
    """Get current index status and consistency info"""
    try:
        from vectorstore.faiss_store import get_index_info
        info = get_index_info()
        return {
            "status": "success",
            "index": info
        }
    except Exception as e:
        logger.error(f"Error getting index status: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


@app.post("/api/index/recover")
def recover_index():
    """Recover index from backup if needed"""
    try:
        from vectorstore.faiss_store import get_index_info
        info = get_index_info()
        
        if not info.get("consistent", False):
            logger.warning("Index inconsistency detected, attempting recovery...")
            # The recovery happens automatically on load if backup exists
            return {
                "status": "warning",
                "message": "Index inconsistency detected. Reloading from backup if available.",
                "index": info
            }
        
        return {
            "status": "success",
            "message": "Index is healthy and consistent",
            "index": info
        }
    except Exception as e:
        logger.error(f"Error attempting recovery: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


@app.post("/api/system/reset")
def reset_system():
    """DANGER: Reset the entire system (use only if necessary)"""
    try:
        from vectorstore.faiss_store import reset_index
        logger.warning("⚠️ SYSTEM RESET INITIATED - All indexed documents will be cleared")
        reset_index()
        return {
            "status": "success",
            "message": "System reset complete. All indexed documents cleared."
        }
    except Exception as e:
        logger.error(f"Error during system reset: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

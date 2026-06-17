"""
Configuration management for Legal AI Backend
Centralized configuration from environment variables
"""

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration"""
    
    # MongoDB
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "legal_ai")
    
    # Server
    BACKEND_HOST = os.getenv("BACKEND_HOST", "0.0.0.0")
    BACKEND_PORT = int(os.getenv("BACKEND_PORT", 8000))
    BACKEND_RELOAD = os.getenv("BACKEND_RELOAD", "true").lower() == "true"
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    
    # CORS
    ALLOWED_ORIGINS = os.getenv(
        "ALLOWED_ORIGINS", 
        "http://localhost:3000"
    ).split(",")
    ALLOW_CREDENTIALS = os.getenv("ALLOW_CREDENTIALS", "true").lower() == "true"
    ALLOW_METHODS = os.getenv("ALLOW_METHODS", "GET,POST,PUT,DELETE,OPTIONS").split(",")
    ALLOW_HEADERS = os.getenv("ALLOW_HEADERS", "Content-Type,Authorization").split(",")
    
    # API
    API_VERSION = os.getenv("API_VERSION", "v1")
    API_PREFIX = os.getenv("API_PREFIX", "/api")
    
    # Security
    DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"


class DevelopmentConfig(Config):
    """Development configuration"""
    ENVIRONMENT = "development"
    DEBUG_MODE = True
    BACKEND_RELOAD = True


class ProductionConfig(Config):
    """Production configuration"""
    ENVIRONMENT = "production"
    DEBUG_MODE = False
    BACKEND_RELOAD = False
    ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "https://yourdomain.com").split(",")


def get_config():
    """Get appropriate configuration based on environment"""
    env = os.getenv("ENVIRONMENT", "development")
    if env == "production":
        return ProductionConfig()
    return DevelopmentConfig()


# Current config instance
config = get_config()

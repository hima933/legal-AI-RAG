"""
LLM Configuration for Legal AI
Uses Ollama phi3 model 
"""

import os
from dotenv import load_dotenv

load_dotenv()


class LLMConfig:
    """Ollama configuration"""
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "phi3")

    GENERATION_CONFIG = {
        "temperature": 0.3,
        "max_tokens": 256,
    }

    LEGAL_SYSTEM_PROMPT = """You are an expert legal assistant specializing in Indian Laws.
Provide accurate legal information based on provided documents.
Never hallucinate. If unsure, say so clearly."""


class EmbeddingConfig:
    """Embedding model configuration"""
    MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    DIMENSION = 384


class FileHandlingConfig:
    """File upload configuration"""
    SUPPORTED_EXTENSIONS = ["pdf", "docx", "txt"]
    MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", 50))
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 500))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 50))
    MIN_CHUNK_LENGTH = int(os.getenv("MIN_CHUNK_LENGTH", 100))


class SafetyConfig:
    """Safety configuration"""
    LEGAL_DISCLAIMER = (
        "This AI provides educational information only. "
        "Consult a qualified lawyer for actual legal matters."
    )
    HARMFUL_QUERY_KEYWORDS = [
        "how to commit",
        "how to evade",
        "how to hide",
        "how to destroy evidence",
    ]
    MIN_CONFIDENCE = 0.5
    MAX_QUERY_LENGTH = 1000


class AppConfig:
    """Main application configuration"""
    llm = LLMConfig
    embedding = EmbeddingConfig
    file_handling = FileHandlingConfig
    safety = SafetyConfig

    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def validate_config(cls):
        """Basic config validation"""
        print(f"Using Ollama model: {cls.llm.OLLAMA_MODEL}")
        print(f"Ollama host: {cls.llm.OLLAMA_HOST}")
        return True


config = AppConfig()
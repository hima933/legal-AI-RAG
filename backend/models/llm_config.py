"""
Advanced LLM Configuration with Legal-Specialized Models
Optimized for low-resource devices with high accuracy
"""

import os
from enum import Enum
from dotenv import load_dotenv

load_dotenv()


class LLMProvider(Enum):
    """Supported LLM providers"""
    OLLAMA = "ollama"  # Local, free, best for low resources
    GROK = "grok"  # Cloud API, fast, free tier available
    OPENAI = "openai"  # Premium, most accurate
    HUGGINGFACE = "huggingface"  # Open source


class LLMConfig:
    """
    LLM Configuration for Legal AI
    - OLLAMA: Recommended for offline, low-resource devices
    - GROK: Recommended for cloud with free tier
    """
    
    # Provider selection (set in .env)
    PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()
    
    # Fallback configuration
    ENABLE_FALLBACK = os.getenv("ENABLE_FALLBACK", "true").lower() == "true"
    FALLBACK_PROVIDERS = [p.strip() for p in os.getenv("FALLBACK_PROVIDERS", "grok,openai").split(",") if p.strip()]
    
    # Model configurations
    MODELS = {
        "ollama": {
            "host": os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            # Legal-specialized models (lightweight & accurate)
            "model": os.getenv("OLLAMA_MODEL", ""),  # or "neural-chat", "orca-mini"
            "context_window": 4096,
            "is_local": True,
        },
        "grok": {
            "api_key": os.getenv("GROK_API_KEY", ""),
            "model": os.getenv("GROK_MODEL", "mixtral-8x7b-32768"),  # Powerful & free
            "context_window": 32768,
            "is_local": False,
        },
        "openai": {
            "api_key": os.getenv("OPENAI_API_KEY", ""),
            "model": os.getenv("OPENAI_MODEL", "gpt-4"),
            "context_window": 8192,
            "is_local": False,
        },
        "huggingface": {
            "api_token": os.getenv("HUGGINGFACE_API_TOKEN", ""),
            "model": os.getenv("HUGGINGFACE_MODEL", "mistralai/Mistral-7B-Instruct-v0.1"),
            "context_window": 4096,
            "is_local": False,
        }
    }
    
    # Embedding model (lightweight for low resources)
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    EMBEDDING_DIM = 384  # Dimension of embeddings
    
    # Generation parameters (optimized for legal accuracy)
    GENERATION_CONFIG = {
        "temperature": 0.3,  # Lower = more factual (important for legal)
        "top_p": 0.85,
        "top_k": 30,
        "max_tokens":  256,  # Increased for better legal answers
        "repetition_penalty": 1.5,  # Higher = less repetition
    }
    
    # Legal-specific system prompt
    LEGAL_SYSTEM_PROMPT = """You are an expert legal assistant specializing in Indian Laws and Constitutional law. 
Your role is to provide accurate, precise legal information and guidance.

CRITICAL INSTRUCTIONS:
1. ALWAYS base answers on provided legal documents and accurate legal knowledge
2. NEVER hallucinate or make up legal information
3. If you don't know something with certainty, say "I don't have enough information to answer this accurately"
4. Include relevant legal sections, acts, and case law references when applicable
5. Maintain objectivity and professional language
6. Add disclaimers when legal advice might be misinterpreted
7. If the question involves potential illegal activity, warn the user clearly

RESPONSE FORMAT:
- Start with a clear, direct answer
- Support with relevant legal sections/acts
- Provide citations from uploaded documents if available
- Include important exceptions or nuances
- End with a disclaimer if the answer involves legal advice"""

    # Confidence thresholds
    CONFIDENCE_THRESHOLDS = {
        "high": 0.8,      # Safe to use
        "medium": 0.6,    # Needs verification
        "low": 0.4,       # Requires caution
        "unsafe": 0.0     # Do not use without review
    }
    
    # Safety keywords (for detecting potentially harmful responses)
    SAFETY_KEYWORDS = {
        "escalation": ["don't worry", "just ignore", "bypass", "exploit", "loophole"],
        "illegal": ["illegal", "crime", "criminal", "felony", "misdemeanor"],
        "medical": ["cure", "treat disease", "medical advice"],
    }


class EmbeddingConfig:
    """Configuration for embedding models"""
    
    # Models optimized for legal domain
    AVAILABLE_MODELS = {
        "all-MiniLM-L6-v2": {
            "size": 80,  # MB
            "dimensions": 384,
            "speed": "fast",
            "accuracy": "good",
            "resource_efficient": True,
        },
        "all-mpnet-base-v2": {
            "size": 420,  # MB
            "dimensions": 768,
            "speed": "medium",
            "accuracy": "better",
            "resource_efficient": False,
        },
        "legal-bert-base-uncased": {
            "size": 420,  # MB
            "dimensions": 768,
            "speed": "medium",
            "accuracy": "excellent",  # Specialized for legal
            "resource_efficient": False,
        },
    }
    
    # Selected model
    MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    DIMENSION = AVAILABLE_MODELS[MODEL]["dimensions"]


class OptimizationConfig:
    """Configuration for optimizing resources"""
    
    # Model quantization (for resource-constrained devices)
    USE_QUANTIZATION = os.getenv("USE_QUANTIZATION", "true").lower() == "true"
    QUANTIZATION_BITS = int(os.getenv("QUANTIZATION_BITS", 8))  # 4-bit or 8-bit
    
    # Batch settings
    MAX_BATCH_SIZE = int(os.getenv("MAX_BATCH_SIZE", 4))  # Smaller for low RAM
    CHUNK_METHOD = os.getenv("CHUNK_METHOD", "semantic")  # semantic, overlap, fixed
    
    # Cache settings
    ENABLE_CACHE = os.getenv("ENABLE_CACHE", "true").lower() == "true"
    CACHE_SIZE_MB = int(os.getenv("CACHE_SIZE_MB", 512))
    
    # Device settings
    DEVICE = os.getenv("DEVICE", "cpu")  # "cpu", "cuda", "mps"
    USE_GPU = DEVICE in ["cuda", "mps"]
    GPU_MEMORY_FRACTION = float(os.getenv("GPU_MEMORY_FRACTION", 0.5))


class FileHandlingConfig:
    """Configuration for multi-format file handling"""

    # Map actual file extensions → processing type
    EXTENSION_MAP = {
        "pdf": "pdf",
        "docx": "docx",
        "doc": "doc",
        "txt": "txt",
        "rtf": "rtf",
        "jpg": "image",
        "jpeg": "image",
        "png": "image",
        "bmp": "image",
        "tiff": "image",
    }

    # Processing configuration
    SUPPORTED_FORMATS = {
        "pdf": {
            "library": "pypdf",
            "enabled": True,
        },
        "docx": {
            "library": "python-docx",
            "enabled": True,
        },
        "doc": {
            "library": "python-docx2docm",
            "enabled": True,
        },
        "txt": {
            "library": "builtin",
            "enabled": True,
        },
        "rtf": {
            "library": "striprtf",
            "enabled": True,
        },
        "image": {
            "library": "pytesseract",
            "enabled": True,
        },
    }

    # File upload limits
    MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", 50))
    MAX_FILES_PER_UPLOAD = int(os.getenv("MAX_FILES_PER_UPLOAD", 5))

    # Chunk settings
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 500))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 50))
    MIN_CHUNK_LENGTH = int(os.getenv("MIN_CHUNK_LENGTH", 100))

    @classmethod
    def is_supported(cls, extension: str) -> bool:
        """Check if file extension is supported"""
        extension = extension.lower().replace(".", "")
        mapped_type = cls.EXTENSION_MAP.get(extension)
        return (
            mapped_type in cls.SUPPORTED_FORMATS
            and cls.SUPPORTED_FORMATS[mapped_type]["enabled"]
        )

    @classmethod
    def get_processing_type(cls, extension: str) -> str:
        """Get processing type from file extension"""
        extension = extension.lower().replace(".", "")
        return cls.EXTENSION_MAP.get(extension)
    
    # File upload limits
    MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", 50))
    MAX_FILES_PER_UPLOAD = int(os.getenv("MAX_FILES_PER_UPLOAD", 5))
    
    # Chunk settings
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 500))  # words
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 50))  # words
    MIN_CHUNK_LENGTH = int(os.getenv("MIN_CHUNK_LENGTH", 100))  # words


class SafetyConfig:
    """Safety and compliance configuration"""
    
    # Legal disclaimers
    ENABLE_DISCLAIMERS = os.getenv("ENABLE_DISCLAIMERS", "true").lower() == "true"
    
    LEGAL_DISCLAIMER = """⚠️ IMPORTANT LEGAL DISCLAIMER:
This AI assistant provides educational information only and is NOT a substitute for professional legal advice.
- Always consult with a qualified lawyer for actual legal matters
- Do not rely on this information for critical legal decisions
- Laws vary by jurisdiction and are subject to interpretation
- This tool may contain errors or outdated information
- Do not use this information to defend yourself in court without legal counsel"""

    # Confidence thresholds
    MIN_CONFIDENCE_FOR_ANSWER = float(os.getenv("MIN_CONFIDENCE_FOR_ANSWER", 0.5))
    
    # Harmful query detection
    HARMFUL_QUERY_KEYWORDS = [
        "how to commit", "how to evade", "how to avoid prosecution",
        "how to hide", "how to destroy evidence"
    ]
    
    # Query validation
    VALIDATE_QUERY = os.getenv("VALIDATE_QUERY", "true").lower() == "true"
    MAX_QUERY_LENGTH = int(os.getenv("MAX_QUERY_LENGTH", 1000))


class AppConfig:
    """Main application configuration"""
    
    # Load all configurations
    llm = LLMConfig
    embedding = EmbeddingConfig
    optimization = OptimizationConfig
    file_handling = FileHandlingConfig
    safety = SafetyConfig
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "logs/legal_ai.log")
    
    @classmethod
    def get_current_provider(cls):
        """Get current LLM provider info"""
        provider = cls.llm.PROVIDER
        return cls.llm.MODELS.get(provider, {})
    
    @classmethod
    def validate_config(cls):
        """Validate configuration"""
        provider = cls.llm.PROVIDER
        
        if provider not in cls.llm.MODELS:
            raise ValueError(f"Unknown LLM provider: {provider}")
        
        if provider == "grok" and not cls.llm.MODELS["grok"]["api_key"]:
            print("⚠️  Warning: GROK_API_KEY not set. Get free API key from https://console.grok.com")
        
        if provider == "openai" and not cls.llm.MODELS["openai"]["api_key"]:
            print("⚠️  Warning: OPENAI_API_KEY not set")
        
        # Validate fallback providers
        if cls.llm.ENABLE_FALLBACK:
            valid_fallbacks = []
            for p in cls.llm.FALLBACK_PROVIDERS:
                is_valid = True
                if p == "grok":
                    if not cls.llm.MODELS["grok"]["api_key"]:
                        print(f"⚠️  Warning: Fallback provider GROK configured but API key missing. Skipping.")
                        is_valid = False
                    else:
                        try:
                            import grok
                        except ImportError:
                            print(f"⚠️  Warning: Fallback provider GROK configured but 'grok' library missing. Install with: pip install grok. Skipping.")
                            is_valid = False
                
                if p == "openai" and not cls.llm.MODELS["openai"]["api_key"]:
                    print(f"⚠️  Warning: Fallback provider OPENAI configured but API key missing. Skipping.")
                    is_valid = False
                
                if is_valid:
                    valid_fallbacks.append(p)
            
            # Update fallbacks to only include valid ones
            cls.llm.FALLBACK_PROVIDERS = valid_fallbacks
        
        return True


# Instantiate config
config = AppConfig()

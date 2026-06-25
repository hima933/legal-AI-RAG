"""
Models package - LLM, embeddings, and document processing
"""

from .llm_config import config, LLMConfig, EmbeddingConfig
from .llm_provider import (
    get_llm_provider, 
    generate_legal_answer, 
    LLMFactory,
    LLMCache
)
from .document_processor import (
    DocumentManager,
    DocumentFactory,
    TextChunker,
    PDFProcessor,
    DOCXProcessor,
    TXTProcessor,
    ImageProcessor,
)

__all__ = [
    "config",
    "LLMConfig",
    "EmbeddingConfig",
    "OptimizationConfig",
    "get_llm_provider",
    "generate_legal_answer",
    "LLMFactory",
    "LLMCache",
    "DocumentManager",
    "DocumentFactory",
    "TextChunker",
    "PDFProcessor",
    "DOCXProcessor",
    "TXTProcessor",
    "ImageProcessor",
]

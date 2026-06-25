"""
Embedding model for Legal AI
Uses sentence-transformers all-MiniLM-L6-v2 (lightweight, fast, 384 dimensions)
"""

import logging
from typing import List
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

# Load model once at startup
logger.info(f"Loading embedding model: {MODEL_NAME}")
model = SentenceTransformer(MODEL_NAME)
logger.info("Embedding model loaded successfully")


def generate_embedding(text: str) -> List[float]:
    """Generate a 384-dimension embedding for the given text"""
    if not text or not text.strip():
        raise ValueError("Text cannot be empty")

    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()
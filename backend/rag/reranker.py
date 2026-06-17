import logging
import os
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

_reranker = None
_load_attempted = False

ENABLE_RERANKER = os.getenv("ENABLE_CROSS_ENCODER_RERANKER", "true").lower() == "true"
RERANKER_MODEL = os.getenv("CROSS_ENCODER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")


def _load_reranker():
    global _reranker, _load_attempted
    if _load_attempted:
        return _reranker

    _load_attempted = True
    if not ENABLE_RERANKER:
        logger.info("Cross-encoder reranker disabled by config")
        return None

    try:
        from sentence_transformers import CrossEncoder

        _reranker = CrossEncoder(RERANKER_MODEL)
        logger.info(f"Loaded cross-encoder reranker: {RERANKER_MODEL}")
        return _reranker
    except Exception as exc:
        logger.warning(f"Cross-encoder reranker unavailable: {exc}")
        _reranker = None
        return None


def rerank_chunks(query: str, chunks: List[Dict[str, Any]], top_k: int = 6) -> List[Dict[str, Any]]:
    if not chunks:
        return []

    reranker = _load_reranker()
    if not reranker:
        return chunks[:top_k]

    try:
        pairs = [(query, str(chunk.get("text", ""))) for chunk in chunks]
        scores = reranker.predict(pairs)
        rescored = []
        for chunk, score in zip(chunks, scores):
            payload = dict(chunk)
            payload["_rerank_score"] = float(score)
            rescored.append(payload)

        rescored.sort(key=lambda item: item.get("_rerank_score", 0.0), reverse=True)
        return rescored[:top_k]
    except Exception as exc:
        logger.warning(f"Reranking failed, using original ranking: {exc}")
        return chunks[:top_k]

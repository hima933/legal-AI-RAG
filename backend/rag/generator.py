"""
RAG generator with strict grounded answering constraints.
"""

import logging
import re
from typing import List

from models.llm_provider import generate_legal_answer as llm_generate_legal_answer

logger = logging.getLogger(__name__)

MAX_CONTEXT_CHARS = 2200
MIN_VALID_LENGTH = 30


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _split_sentences(text: str) -> List[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def _clean_output(text: str) -> str:
    text = _normalize_text(text)
    if not text:
        return ""

    sentences = _split_sentences(text)
    unique = []
    seen = set()
    for sent in sentences:
        key = sent.lower().strip()
        if key in seen:
            continue
        seen.add(key)
        unique.append(sent)
        if len(unique) >= 10:
            break

    return " ".join(unique).strip()


def generate_legal_answer(query: str, context_text: str) -> str:
    try:
        if not query or not query.strip():
            return "Invalid legal query."

        safe_context = _normalize_text(context_text)[:MAX_CONTEXT_CHARS]

        grounded_query = (
            "Answer only from the provided context. "
            "Do not use outside knowledge. "
            "If context is insufficient, explicitly say so. "
            "No hallucination. No repetition. "
            "Respond in 6 to 10 sentences.\n\n"
            f"Question: {query}"
        )

        result = llm_generate_legal_answer(grounded_query, safe_context)

        if isinstance(result, dict):
            answer = result.get("answer", "")
        else:
            answer = str(result)

        answer = _clean_output(answer)

        if not answer or len(answer) < MIN_VALID_LENGTH:
            return "The retrieved context is insufficient to answer this question accurately."

        return answer
    except Exception as exc:
        logger.error(f"Generator fatal error: {exc}", exc_info=True)
        return "Legal context retrieved, but answer generation failed."

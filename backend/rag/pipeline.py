"""
RAG Pipeline for Legal AI
Retrieves relevant legal chunks and generates grounded answers using Ollama phi3.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from embeddings.embedder import generate_embedding
from rag.generator import generate_legal_answer
from rag.reranker import rerank_chunks
from services.legal_analyzer import generate_legal_analysis
from vectorstore.faiss_store import hybrid_search

logger = logging.getLogger(__name__)


def _infer_source_label(chunk: Dict[str, Any], idx: int) -> str:
    """Get a readable source label from a chunk"""
    raw_source = str(chunk.get("source", "")).strip()
    if raw_source and raw_source.lower() not in {"unknown", "none", "null"}:
        return raw_source

    law_type = str(chunk.get("law_type", "")).strip()
    if law_type and law_type.upper() not in {"GENERAL", "UNKNOWN"}:
        return f"{law_type} reference"

    return f"Legal reference {idx + 1}"


def _normalize_page(value: Any) -> Optional[int]:
    try:
        page = int(value)
        return page if page > 0 else None
    except (TypeError, ValueError):
        return None


def _build_context_text(chunks: List[Dict[str, Any]], max_chars: int = 3000) -> str:
    """Combine chunk texts into a single context string"""
    seen = set()
    parts = []
    for chunk in chunks:
        text = str(chunk.get("text", "")).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        parts.append(text)
        if sum(len(p) for p in parts) >= max_chars:
            break
    return " ".join(parts)[:max_chars]


def _extract_legal_sections(text: str) -> List[str]:
    """Extract Section references from text"""
    matches = re.findall(r"(Section\s+\d+[A-Za-z-]*)", text or "", flags=re.IGNORECASE)
    seen = set()
    result = []
    for m in matches:
        norm = re.sub(r"\s+", " ", m).strip().title()
        if norm.lower() not in seen:
            seen.add(norm.lower())
            result.append(norm)
    return result[:10]


def is_general_query(query: str) -> bool:
    """Check if query is non-legal (general knowledge)"""
    q = query.lower()
    general_keywords = ["joke", "funny", "story", "weather", "movie", "music", "science"]
    legal_keywords = ["section", "ipc", "crpc", "court", "case", "bail", "law", "legal", "act", "fir"]

    if any(k in q for k in general_keywords) and not any(k in q for k in legal_keywords):
        return True
    return False


def retrieve_context(
    query: str,
    k: int = 6,
    use_uploaded_context: Optional[bool] = None,
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieve relevant chunks from FAISS using hybrid search"""
    try:
        embedding = generate_embedding(query)
        metadata_filters = None

        if use_uploaded_context:
            metadata_filters = {"law_type": "UPLOADED_DOC"}
            if user_id:
                metadata_filters["user_id"] = user_id

        results = hybrid_search(
            query_text=query,
            query_embedding=embedding,
            k=k,
            metadata_filters=metadata_filters,
        )
        return results
    except Exception as exc:
        logger.error(f"Context retrieval failed: {exc}")
        return []


def run_rag_pipeline(
    query: str,
    use_uploaded_context: Optional[bool] = None,
    user_id: Optional[str] = None,
) -> Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]], Optional[Dict[str, Any]], Dict[str, Any]]:
    """
    Main RAG pipeline:
    1. Check if general query → answer directly with LLM
    2. Retrieve relevant legal chunks from FAISS
    3. Rerank chunks for relevance
    4. Generate grounded answer using Ollama phi3
    5. Build citations from retrieved chunks
    6. Return answer, chunks, citations, analysis, metadata
    """

    try:
        from models.llm_provider import get_llm_provider
        original_query = (query or "").strip()

        if not original_query:
            return "Please enter a valid question.", [], [], None, {}

        # Handle numeric input as IPC/CrPC section query
        if original_query.strip().isdigit():
            original_query = f"What is Section {original_query} of IPC or CrPC?"

        # Step 1 — Route general queries directly to LLM
        if is_general_query(original_query):
            try:
                provider = get_llm_provider()
                answer = provider.generate(
                    f"Answer clearly:\n\n{original_query}",
                    temperature=0.7,
                    max_tokens=400,
                )
                return answer.strip(), [], [], None, {"mode": "general"}
            except Exception as exc:
                logger.error(f"General LLM failed: {exc}")

        # Step 2 — Retrieve legal context
        context_chunks = retrieve_context(
            query=original_query,
            k=8,
            use_uploaded_context=use_uploaded_context,
            user_id=user_id,
        )

        # Step 3 — LLM fallback if no context found
        if not context_chunks:
            try:
                provider = get_llm_provider()
                answer = provider.generate(
                    f"Answer the following legal question clearly:\n\n{original_query}",
                    temperature=0.5,
                    max_tokens=400,
                )
                return answer.strip(), [], [], None, {"mode": "llm_fallback"}
            except Exception as exc:
                logger.error(f"LLM fallback failed: {exc}")
                return "Unable to find relevant legal information for your query.", [], [], None, {}

        # Step 4 — Rerank for relevance
        context_chunks = rerank_chunks(original_query, context_chunks, top_k=6)

        # Step 5 — Build context text and generate answer
        context_text = _build_context_text(context_chunks, max_chars=2400)
        answer_data = generate_legal_answer(original_query, context_text)

        if isinstance(answer_data, dict):
            answer = answer_data.get("answer", "")
        else:
            answer = str(answer_data)

        # Step 6 — Build citations
        citations = []
        seen_citations = set()
        for idx, chunk in enumerate(context_chunks[:6]):
            source_label = _infer_source_label(chunk, idx)
            page = _normalize_page(chunk.get("page"))
            key = (source_label.lower(), page)
            if key in seen_citations:
                continue
            seen_citations.add(key)
            citations.append({
                "source": source_label,
                "page": page,
                "law_type": chunk.get("law_type", "GENERAL"),
                "preview": (chunk.get("text", "")[:140] + "...") if chunk.get("text") else "",
            })

        # Step 7 — Legal analysis
        analysis = None
        try:
            analysis = generate_legal_analysis(original_query, answer, context_chunks)
        except Exception as exc:
            logger.warning(f"Legal analysis failed: {exc}")

        # Step 8 — Metadata
        matched_sections = _extract_legal_sections(
            _build_context_text(context_chunks, max_chars=5000)
        )

        metadata = {
            "mode": "rag_legal",
            "matched_legal_sections": matched_sections,
            "chunks_retrieved": len(context_chunks),
        }

        return answer, context_chunks, citations, analysis, metadata

    except Exception as exc:
        logger.error(f"RAG Pipeline error: {exc}", exc_info=True)
        return "An error occurred while processing your query.", [], [], None, {}
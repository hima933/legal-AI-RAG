import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from embeddings.embedder import generate_embedding
from models.llm_provider import get_llm_provider
from rag.generator import generate_legal_answer
from rag.reranker import rerank_chunks
from services.legal_analyzer import generate_legal_analysis
from vectorstore.faiss_store import hybrid_search

logger = logging.getLogger(__name__)


def _infer_source_label(chunk: Dict[str, Any], idx: int) -> str:
    raw_source = str(chunk.get("source", "")).strip()
    if raw_source and raw_source.lower() not in {"unknown", "none", "null"}:
        return raw_source

    law_type = str(chunk.get("law_type", "")).strip()
    if law_type and law_type.upper() not in {"GENERAL", "UNKNOWN"}:
        return f"{law_type} reference"

    text = str(chunk.get("text", "")).strip()
    match = re.match(r"^\[([A-Z_]+)\]\s*", text)
    if match:
        return f"{match.group(1)} reference"

    return f"Legal reference {idx + 1}"


def _normalize_page(value: Any) -> Optional[int]:
    try:
        page = int(value)
        return page if page > 0 else None
    except (TypeError, ValueError):
        return None


def _build_context_text(chunks: List[Dict[str, Any]], max_chars: int = 3000) -> str:
    seen = set()
    parts: List[str] = []
    for chunk in chunks:
        text = str(chunk.get("text", "")).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        parts.append(text)
        if sum(len(p) for p in parts) >= max_chars:
            break
    return " ".join(parts)[:max_chars]


def _safe_json_extract(text: str) -> Dict[str, Any]:
    payload = (text or "").strip()
    if not payload:
        return {}

    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[\s\S]*\}", payload)
    if not match:
        return {}

    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}


def detect_language(text: str) -> str:
    raw = text or ""
    if re.search(r"[\u0900-\u097F]", raw):
        return "hi"
    if re.search(r"[\u0B80-\u0BFF]", raw):
        return "ta"
    if re.search(r"[\u0C00-\u0C7F]", raw):
        return "te"
    if re.search(r"[\u0980-\u09FF]", raw):
        return "bn"
    return "en"


def translate_text(text: str, target_lang: str) -> str:
    if not text or target_lang.lower() == "en":
        return text

    try:
        provider = get_llm_provider()
        prompt = (
            f"Translate the following legal text into {target_lang}. "
            "Return only translated text without commentary.\n\n"
            f"Text:\n{text}"
        )
        translated = provider.generate(prompt, temperature=0.0, max_tokens=700)
        return translated.strip() or text
    except Exception as exc:
        logger.warning(f"Translation failed ({target_lang}): {exc}")
        return text


def translate_to_english(text: str) -> str:
    if not text:
        return text
    try:
        provider = get_llm_provider()
        prompt = (
            "Translate the following legal query into English. "
            "Return only translated query text.\n\n"
            f"Query:\n{text}"
        )
        translated = provider.generate(prompt, temperature=0.0, max_tokens=300)
        return translated.strip() or text
    except Exception as exc:
        logger.warning(f"Translation to English failed: {exc}")
        return text


def retrieve_context(
    query: str,
    k: int = 6,
    use_uploaded_context: Optional[bool] = None,
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
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

        if use_uploaded_context and user_id and not results:
            results = hybrid_search(
                query_text=query,
                query_embedding=embedding,
                k=k,
                metadata_filters={"law_type": "UPLOADED_DOC"},
            )

        return results
    except Exception as exc:
        logger.error(f"Context retrieval failed: {exc}")
        return []


def _heuristic_faithfulness(answer: str, context_text: str) -> float:
    answer_terms = set(re.findall(r"[a-zA-Z]{3,}", (answer or "").lower()))
    context_terms = set(re.findall(r"[a-zA-Z]{3,}", (context_text or "").lower()))
    if not answer_terms:
        return 0.0
    overlap = len(answer_terms.intersection(context_terms))
    return min(1.0, max(0.0, overlap / max(len(answer_terms), 1)))


def critique_draft(
    query: str,
    draft_answer: str,
    context_chunks: List[Dict[str, Any]],
) -> Dict[str, Any]:
    context_text = _build_context_text(context_chunks, max_chars=2800)
    fallback_score = _heuristic_faithfulness(draft_answer, context_text)
    fallback = {
        "faithfulness_score": round(fallback_score, 3),
        "needs_second_pass": fallback_score < 0.62,
        "rewrite_query": query,
        "reason": "Heuristic critique fallback",
        "missing_points": [],
    }

    try:
        provider = get_llm_provider()
        prompt = f"""You are a legal QA evaluator.
Evaluate if the answer is faithful to context and suggest improvement.
Return ONLY JSON:
{{
  "faithfulness_score": 0.0,
  "needs_second_pass": true,
  "rewrite_query": "string",
  "reason": "string",
  "missing_points": ["string"]
}}

Question:
{query}

Draft Answer:
{draft_answer}

Context:
{context_text}
"""
        raw = provider.generate(prompt, temperature=0.0, max_tokens=280)
        parsed = _safe_json_extract(raw)
        if not parsed:
            return fallback

        faithfulness = parsed.get("faithfulness_score", fallback["faithfulness_score"])
        try:
            faithfulness = float(faithfulness)
        except (TypeError, ValueError):
            faithfulness = fallback["faithfulness_score"]

        missing = parsed.get("missing_points", [])
        if not isinstance(missing, list):
            missing = []

        return {
            "faithfulness_score": round(min(1.0, max(0.0, faithfulness)), 3),
            "needs_second_pass": bool(parsed.get("needs_second_pass", faithfulness < 0.62)),
            "rewrite_query": str(parsed.get("rewrite_query") or query).strip(),
            "reason": str(parsed.get("reason") or "").strip() or "LLM critique",
            "missing_points": [str(item).strip() for item in missing if str(item).strip()][:6],
        }
    except Exception as exc:
        logger.warning(f"Critique stage failed: {exc}")
        return fallback


def _merge_context_chunks(primary: List[Dict[str, Any]], secondary: List[Dict[str, Any]], k: int) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    seen = set()
    for chunk in primary + secondary:
        key = f"{chunk.get('source')}|{chunk.get('page')}|{hash(chunk.get('text', '')[:220])}"
        if key in seen:
            continue
        seen.add(key)
        merged.append(chunk)
        if len(merged) >= k:
            break
    return merged


def _retrieve_multilingual_context(
    original_query: str,
    retrieval_query: str,
    use_uploaded_context: Optional[bool],
    user_id: Optional[str],
    k: int = 8,
) -> List[Dict[str, Any]]:
    primary = retrieve_context(
        retrieval_query,
        k=k,
        use_uploaded_context=use_uploaded_context,
        user_id=user_id,
    )
    if original_query.strip() == retrieval_query.strip():
        return primary

    secondary = retrieve_context(
        original_query,
        k=k,
        use_uploaded_context=use_uploaded_context,
        user_id=user_id,
    )
    return _merge_context_chunks(primary, secondary, k=max(k, 10))


def _extract_legal_sections(text: str) -> List[str]:
    matches = re.findall(r"(Section\s+\d+[A-Za-z-]*)", text or "", flags=re.IGNORECASE)
    unique = []
    seen = set()
    for m in matches:
        norm = re.sub(r"\s+", " ", m).strip().title()
        if norm.lower() in seen:
            continue
        seen.add(norm.lower())
        unique.append(norm)
    return unique[:10]


def _compute_retrieval_metrics(
    query: str,
    context_chunks: List[Dict[str, Any]],
    citations: List[Dict[str, Any]],
    critique: Dict[str, Any],
) -> Dict[str, Any]:
    q_terms = set(re.findall(r"[a-zA-Z]{3,}", query.lower()))
    if not q_terms:
        q_terms = set()

    hits = 0
    covered_terms = set()
    for chunk in context_chunks:
        text = str(chunk.get("text", "")).lower()
        chunk_hit = False
        for term in q_terms:
            if term in text:
                covered_terms.add(term)
                chunk_hit = True
        if chunk_hit:
            hits += 1

    k = max(len(context_chunks), 1)
    precision_at_k = hits / k
    recall_at_k = (len(covered_terms) / max(len(q_terms), 1)) if q_terms else 0.0
    citation_coverage = (
        len([c for c in citations if c.get("source") and "unknown" not in str(c.get("source")).lower()])
        / max(len(citations), 1)
        if citations
        else 0.0
    )

    faithfulness = float(critique.get("faithfulness_score", 0.5))
    return {
        "faithfulness_score": round(faithfulness, 3),
        "hallucination_risk": round(max(0.0, min(1.0, 1.0 - faithfulness)), 3),
        "precision_at_k": round(precision_at_k, 3),
        "recall_at_k": round(recall_at_k, 3),
        "citation_coverage": round(citation_coverage, 3),
    }

def is_general_query(query: str) -> bool:
    q = query.lower()

    general_keywords = [
        "joke", "funny", "story", "science", "ai", "python",
        "who is", "what is", "explain", "define", "weather",
        "history", "movie", "music"
    ]

    legal_keywords = [
        "section", "ipc", "crpc", "court", "case",
        "judgement", "petition", "bail", "law", "legal"
    ]

    if any(word in q for word in general_keywords):
        return True

    if any(word in q for word in legal_keywords):
        return False

    return False

def run_rag_pipeline(
    query: str,
    use_uploaded_context: Optional[bool] = None,
    user_id: Optional[str] = None,
) -> Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]], Optional[Dict[str, Any]], Dict[str, Any]]:

    answer = ""
    context_chunks: List[Dict[str, Any]] = []
    citations: List[Dict[str, Any]] = []
    analysis = None
    metadata: Dict[str, Any] = {}

    try:
        original_query = (query or "").strip()
        q_lower = original_query.lower()
        if original_query.strip().isdigit():
             original_query = f"What is Section {original_query} of IPC or CrPC?"
             q_lower = original_query.lower()

        # 🔥 INLINE GENERAL ROUTING (no extra def used)
        general_keywords = [
            "joke", "funny", "story", "science", "ai", "python",
            "who is", "what is", "weather", "history",
            "movie", "music"
        ]

        legal_keywords = [
            "section", "ipc", "crpc", "court", "case",
            "judgement", "petition", "bail", "law", "legal",
            "act", "fir", "appeal"
        ]

        if any(k in q_lower for k in general_keywords) and not any(k in q_lower for k in legal_keywords):
            provider = get_llm_provider()
            try:
                general_answer = provider.generate(
                    f"Answer clearly and naturally:\n\n{original_query}",
                    temperature=0.7,
                    max_tokens=400,
                )

                return (
                    general_answer.strip(),
                    [],
                    [],
                    None,
                    {"mode": "general_llm"},
                )
            except Exception as exc:
                logger.error(f"General LLM failed: {exc}")

        query_lang = detect_language(original_query)
        retrieval_query = original_query
        translated_query = None

        if query_lang != "en":
            translated_query = translate_to_english(original_query)
            retrieval_query = translated_query or original_query

        first_pass_chunks = _retrieve_multilingual_context(
            original_query=original_query,
            retrieval_query=retrieval_query,
            use_uploaded_context=use_uploaded_context,
            user_id=user_id,
            k=10,
        )

        first_pass_chunks = rerank_chunks(retrieval_query, first_pass_chunks, top_k=3)

        # 🔁 Fallback if no legal context found
        if not first_pass_chunks:
            provider = get_llm_provider()
            try:
                general_answer = provider.generate(
                    f"Answer the following question clearly:\n\n{original_query}",
                    temperature=0.5,
                    max_tokens=400,
                )

                return (
                    general_answer.strip(),
                    [],
                    [],
                    None,
                    {
                        "query_language": query_lang,
                        "translated_query": translated_query,
                        "mode": "llm_fallback",
                    },
                )
            except Exception as exc:
                logger.error(f"LLM fallback failed: {exc}")
                return (
                    "Unable to retrieve legal documents or generate a response.",
                    [],
                    [],
                    None,
                    {},
                )

        first_context = _build_context_text(first_pass_chunks,max_chars=1200)

        draft_answer = generate_legal_answer(retrieval_query, first_context)

        # 🔥 Handle dict response safely
        if isinstance(draft_answer, dict):
            draft_answer = draft_answer.get("answer", "")

        critique = critique_draft(retrieval_query, draft_answer, first_pass_chunks)

        second_pass_used = False
        rewritten_query = critique.get("rewrite_query") or retrieval_query
        final_chunks = first_pass_chunks
        answer = draft_answer

        if critique.get("needs_second_pass", False):
            second_pass_used = True

            second_pass_chunks = _retrieve_multilingual_context(
                original_query=original_query,
                retrieval_query=rewritten_query,
                use_uploaded_context=use_uploaded_context,
                user_id=user_id,
                k=12,
            )

            second_pass_chunks = rerank_chunks(rewritten_query, second_pass_chunks, top_k=8)

            if second_pass_chunks:
                final_chunks = _merge_context_chunks(first_pass_chunks, second_pass_chunks, k=10)
                final_chunks = rerank_chunks(retrieval_query, final_chunks, top_k=10)

            final_context = _build_context_text(final_chunks)

            answer = generate_legal_answer(retrieval_query, final_context)

            if isinstance(answer, dict):
                answer = answer.get("answer", "")

        if query_lang != "en":
            answer = translate_text(answer, query_lang)

        context_chunks = final_chunks

        seen_citations = set()
        for idx, chunk in enumerate(context_chunks[:8]):
            source_label = _infer_source_label(chunk, idx)
            page = _normalize_page(chunk.get("page"))
            key = (source_label.lower(), page)
            if key in seen_citations:
                continue
            seen_citations.add(key)

            citations.append(
                {
                    "source": source_label,
                    "page": page,
                    "law_type": chunk.get("law_type", "GENERAL"),
                    "preview": (chunk.get("text", "")[:140] + "...") if chunk.get("text") else "",
                }
            )

        try:
            analysis = generate_legal_analysis(original_query, answer, context_chunks)
        except Exception as exc:
            logger.warning(f"Legal analysis failed: {exc}")
            analysis = None

        matched_sections = _extract_legal_sections(
            _build_context_text(context_chunks, max_chars=5500)
        )

        evaluation_metrics = _compute_retrieval_metrics(
            retrieval_query,
            context_chunks,
            citations,
            critique,
        )

        metadata = {
            "pipeline_version": "lq-rag-v3",
            "retrieval_strategy": "hybrid_dense_lexical_rrf",
            "query_language": query_lang,
            "translated_query": translated_query,
            "second_pass_used": second_pass_used,
            "matched_legal_sections": matched_sections,
            "evaluation": evaluation_metrics,
            "mode": "rag_legal",
        }

        return answer, context_chunks, citations, analysis, metadata

    except Exception as exc:
        logger.error(f"RAG Pipeline Critical Error: {exc}", exc_info=True)
        return (
            "An internal error occurred while processing your query.",
            [],
            [],
            None,
            {},
        )
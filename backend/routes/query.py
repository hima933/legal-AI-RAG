from datetime import datetime
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel

from database.mongo import db, queries_collection
from rag.pipeline import run_rag_pipeline
from routes.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()
evaluation_collection = db["query_evaluations"]


class QueryRequest(BaseModel):
    question: str
    use_uploaded_context: Optional[bool] = None


class QueryResponse(BaseModel):
    answer: str
    confidence: float
    has_warning: bool = False
    warning: Optional[str] = None
    disclaimer: str = ""
    citations: list = []
    metadata: dict = {}
    summary: Optional[dict] = None
    query_id: Optional[str] = None


@router.post("/query", response_model=QueryResponse)
async def query_legal_ai(request: QueryRequest, current_user = Depends(get_current_user)):
    try:
        query = request.question.strip()
        if not query:
            raise HTTPException(status_code=400, detail="Query cannot be empty")

        answer, context_chunks, citations, analysis, metadata = run_rag_pipeline(
            query,
            use_uploaded_context=request.use_uploaded_context,
            user_id=str(current_user["_id"]),
        )

        if not context_chunks and not answer:
            return QueryResponse(
                answer=answer or "No relevant legal context found.",
                confidence=0.25,
                has_warning=True,
                warning="No supporting legal context found",
                citations=[],
                metadata=metadata or {},
                summary=None,
            )

        # Calculate confidence based on context quality and answer length
        base_confidence = 0.6
        context_boost = min(0.3, len(context_chunks) * 0.05)
        confidence = min(0.95, base_confidence + context_boost)

        query_id = None
        try:
            insert_result = queries_collection.insert_one(
                {
                    "timestamp": datetime.utcnow(),
                    "user_id": str(current_user["_id"]),
                    "question": query,
                    "answer": answer,
                    "confidence": round(confidence, 2),
                    "citations": citations or [],
                    "metadata": metadata or {},
                    "summary": analysis,
                }
            )
            query_id = str(insert_result.inserted_id)

            eval_metrics = (metadata or {}).get("evaluation", {})
            evaluation_collection.insert_one(
                {
                    "timestamp": datetime.utcnow(),
                    "release_version": "lq-rag-v2",
                    "query_id": query_id,
                    "user_id": str(current_user["_id"]),
                    "question": query,
                    "use_uploaded_context": bool(request.use_uploaded_context),
                    "metrics": eval_metrics,
                    "second_pass_used": bool((metadata or {}).get("second_pass_used", False)),
                    "language": (metadata or {}).get("query_language", "en"),
                }
            )
        except Exception as db_error:
            logger.warning(f"DB save error (non-critical): {db_error}")

        return QueryResponse(
            answer=answer,
            confidence=round(confidence, 2),
            citations=citations or [],
            disclaimer="Legal AI informational response. Consult a lawyer for decisions.",
            metadata=metadata or {},
            summary=analysis,
            query_id=query_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}")

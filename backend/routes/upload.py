from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
import hashlib
import logging
import os
import tempfile
import traceback
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

from database.mongo import db
from embeddings.embedder import generate_embedding
from models.document_processor import DocumentManager
from models.llm_config import config
from rag.document_analyzer import analyze_document
from vectorstore.faiss_store import add_document, get_index_info, save_index
from routes.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()
doc_manager = DocumentManager()

analysis_collection = db["document_analyses"]
_embedding_cache: Dict[str, List[float]] = {}


class UploadContext:
    def __init__(self):
        self.temp_files: List[str] = []

    def add_temp_file(self, path: str) -> None:
        self.temp_files.append(path)

    def cleanup_temp_files(self) -> None:
        for path in self.temp_files:
            try:
                if os.path.exists(path):
                    os.unlink(path)
            except Exception as exc:
                logger.warning(f"Temp cleanup failed for {path}: {exc}")


def _embedding_for_chunk(chunk: str) -> np.ndarray:
    key = hashlib.sha256(chunk.encode("utf-8", errors="ignore")).hexdigest()
    cached = _embedding_cache.get(key)
    if cached is not None:
        return np.array(cached, dtype="float32")

    embedding = generate_embedding(chunk)
    _embedding_cache[key] = embedding
    return np.array(embedding, dtype="float32")


def _extract_chunk_page(chunk_text: str) -> int:
    try:
        import re

        match = re.search(r"\[Page\s+(\d+)\]", chunk_text or "", flags=re.IGNORECASE)
        if match:
            return int(match.group(1))
    except Exception:
        return 0
    return 0


@router.post("/upload")
async def upload_document(files: List[UploadFile] = File(...), current_user = Depends(get_current_user)):
    context = UploadContext()

    try:
        if not files:
            raise HTTPException(status_code=400, detail="No files provided")

        if len(files) > config.file_handling.MAX_FILES_PER_UPLOAD:
            raise HTTPException(
                status_code=400,
                detail=f"Too many files. Max {config.file_handling.MAX_FILES_PER_UPLOAD} files per upload.",
            )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"File validation error: {exc}") from exc

    uploaded_summary: Dict[str, Any] = {
        "total_files": len(files),
        "successful": 0,
        "failed": 0,
        "total_chunks": 0,
        "files_processed": [],
        "errors": [],
        "index_state": None,
    }

    for file in files:
        try:
            if not file.filename:
                uploaded_summary["failed"] += 1
                uploaded_summary["errors"].append("Unnamed file detected")
                continue

            file_ext = Path(file.filename).suffix.lower().replace(".", "")
            if not config.file_handling.is_supported(file_ext):
                uploaded_summary["failed"] += 1
                uploaded_summary["errors"].append(f"{file.filename}: Unsupported file type")
                continue

            content = await file.read()
            file_size = len(content)
            max_size = config.file_handling.MAX_FILE_SIZE_MB * 1024 * 1024
            if file_size > max_size:
                uploaded_summary["failed"] += 1
                uploaded_summary["errors"].append(
                    f"{file.filename}: File too large (max {config.file_handling.MAX_FILE_SIZE_MB}MB)"
                )
                continue

            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as tmp:
                tmp.write(content)
                temp_path = tmp.name
            context.add_temp_file(temp_path)

            full_text, chunks, metadata = doc_manager.process_file(temp_path)
            if not full_text.strip() or not chunks:
                uploaded_summary["failed"] += 1
                uploaded_summary["errors"].append(f"{file.filename}: No text extracted")
                continue

            file_chunks_count = 0
            for chunk in chunks:
                chunk_text = chunk.strip()
                if not chunk_text:
                    continue
                try:
                    embedding = _embedding_for_chunk(chunk_text)
                    add_document(
                        text=chunk_text,
                        embedding=embedding,
                        source=file.filename,
                        page=_extract_chunk_page(chunk_text),
                        law_type="UPLOADED_DOC",
                        user_id=str(current_user["_id"]),
                    )
                    file_chunks_count += 1
                    uploaded_summary["total_chunks"] += 1
                except Exception as chunk_error:
                    logger.error(f"Chunk processing failed for {file.filename}: {chunk_error}")

            if file_chunks_count == 0:
                uploaded_summary["failed"] += 1
                uploaded_summary["errors"].append(f"{file.filename}: Failed to process any chunks")
                continue

            analysis = analyze_document(full_text)

            doc_record = {
                "user_id": str(current_user["_id"]),
                "filename": file.filename,
                "file_type": file_ext,
                "size_mb": round(file_size / (1024 * 1024), 2),
                "metadata": metadata,
                "summary": analysis.get("summary", ""),
                "case_type": analysis.get("case_type", "Unknown"),
                "parties": analysis.get("parties", []),
                "court": analysis.get("court", ""),
                "legal_sections": analysis.get("legal_sections", []),
                "judgement": analysis.get("judgement", ""),
                "risks": analysis.get("risks", []),
                "key_clauses": analysis.get("key_clauses", []),
                "key_points": analysis.get("key_points", []),
                "citations": analysis.get("citations", []),
                "case_structure": analysis.get("case_structure", {}),
                "extracted_legal_entities": analysis.get("extracted_legal_entities", {}),
                "chunk_count": file_chunks_count,
                "full_text_preview": full_text[:2000],
            }

            try:
                analysis_collection.insert_one(doc_record)
            except Exception as db_error:
                logger.warning(f"Failed to persist analysis for {file.filename}: {db_error}")

            try:
                save_index()
            except Exception as save_error:
                uploaded_summary["failed"] += 1
                uploaded_summary["errors"].append(f"{file.filename}: Index save failed ({save_error})")
                continue

            uploaded_summary["successful"] += 1
            uploaded_summary["files_processed"].append(
                {
                    "filename": file.filename,
                    "chunks": file_chunks_count,
                    "size_mb": round(file_size / (1024 * 1024), 2),
                    "file_type": file_ext,
                    "metadata": metadata,
                    "analysis": {
                        "summary": doc_record["summary"],
                        "case_type": doc_record["case_type"],
                        "parties": doc_record["parties"],
                        "court": doc_record["court"],
                        "legal_sections": doc_record["legal_sections"],
                        "judgement": doc_record["judgement"],
                        "risks": doc_record["risks"],
                        "key_clauses": doc_record["key_clauses"],
                        "key_points": doc_record["key_points"],
                        "citations": doc_record["citations"],
                        "case_structure": doc_record["case_structure"],
                    },
                }
            )

        except HTTPException:
            raise
        except Exception as file_error:
            logger.error(f"Upload processing error for {getattr(file, 'filename', 'unknown')}: {file_error}\n{traceback.format_exc()}")
            uploaded_summary["failed"] += 1
            uploaded_summary["errors"].append(f"{getattr(file, 'filename', 'unknown')}: {str(file_error)[:140]}")

    context.cleanup_temp_files()

    try:
        uploaded_summary["index_state"] = get_index_info()
    except Exception as idx_error:
        logger.warning(f"Failed to read index info: {idx_error}")

    if uploaded_summary["successful"] == 0:
        raise HTTPException(
            status_code=400,
            detail=uploaded_summary["errors"] if uploaded_summary["errors"] else ["No files processed successfully"],
        )

    return {
        "message": "Document analyzed successfully",
        "status": "success" if uploaded_summary["failed"] == 0 else "partial_success",
        "summary": uploaded_summary,
    }


@router.get("/upload/health")
async def upload_health():
    try:
        index_info = get_index_info()
        return {
            "status": "healthy" if index_info.get("consistent", False) else "warning",
            "message": "Upload service ready",
            "supported_formats": list(config.file_handling.SUPPORTED_FORMATS.keys()),
            "max_file_size_mb": config.file_handling.MAX_FILE_SIZE_MB,
            "max_files_per_upload": config.file_handling.MAX_FILES_PER_UPLOAD,
            "index_state": index_info,
        }
    except Exception as exc:
        return {
            "status": "warning",
            "message": f"Health check failed: {str(exc)[:100]}",
            "error": str(exc),
        }

import faiss
import numpy as np
import os
import pickle
import logging
import threading
import shutil
import math
import re
from collections import Counter
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Thread-safe lock for index operations
_index_lock = threading.Lock()

# PATH SETUP
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_DIR = os.path.join(BASE_DIR, "faiss_index")

INDEX_PATH = os.path.join(INDEX_DIR, "index.faiss")
DOC_PATH = os.path.join(INDEX_DIR, "documents.pkl")
BACKUP_INDEX_PATH = os.path.join(INDEX_DIR, "index.faiss.backup")
BACKUP_DOC_PATH = os.path.join(INDEX_DIR, "documents.pkl.backup")

dimension = 384
_token_pattern = re.compile(r"\w+", flags=re.UNICODE)


def _tokenize(text: str) -> List[str]:
    return _token_pattern.findall((text or "").lower())


def _matches_filters(doc: Dict[str, Any], metadata_filters: Optional[Dict[str, Any]]) -> bool:
    if not metadata_filters:
        return True

    for key, expected in metadata_filters.items():
        value = doc.get(key)
        if isinstance(expected, (list, tuple, set)):
            if value not in expected:
                return False
        elif expected is None:
            continue
        else:
            if value != expected:
                return False
    return True


def _doc_copy_with_score(doc: Dict[str, Any], extra: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(doc)
    payload.update(extra)
    return payload


def _load_or_create_index():
    """Safely load or create FAISS index with backup restore capability."""
    try:
        if os.path.exists(INDEX_PATH):
            logger.info("Loading existing FAISS index...")
            idx = faiss.read_index(INDEX_PATH)
            if os.path.exists(DOC_PATH):
                with open(DOC_PATH, "rb") as f:
                    docs = pickle.load(f)
            else:
                docs = []
        else:
            logger.info("Creating new FAISS index...")
            os.makedirs(INDEX_DIR, exist_ok=True)
            idx = faiss.IndexFlatL2(dimension)
            docs = []
        return idx, docs
    except Exception as exc:
        logger.error(f"Failed to load index: {exc}. Attempting recovery...")
        if os.path.exists(BACKUP_INDEX_PATH) and os.path.exists(BACKUP_DOC_PATH):
            try:
                logger.info("Recovering from backup...")
                idx = faiss.read_index(BACKUP_INDEX_PATH)
                with open(BACKUP_DOC_PATH, "rb") as f:
                    docs = pickle.load(f)
                logger.info("Recovered from backup")
                return idx, docs
            except Exception as backup_exc:
                logger.error(f"Backup recovery failed: {backup_exc}")

        os.makedirs(INDEX_DIR, exist_ok=True)
        idx = faiss.IndexFlatL2(dimension)
        docs = []
        return idx, docs


index, documents = _load_or_create_index()


def add_document(
    text: str,
    embedding: List[float],
    source: str = "unknown",
    page: int = 0,
    law_type: str = "GENERAL",
    user_id: Optional[str] = None,
):
    """Add document with thread-safe access."""
    try:
        with _index_lock:
            if not text:
                raise ValueError("Text cannot be empty")
            if embedding is None:
                raise ValueError("Embedding cannot be empty")
            if hasattr(embedding, "__len__") and len(embedding) == 0:
                raise ValueError("Embedding cannot be empty")

            vector = np.array([embedding], dtype="float32")
            if vector.shape[1] != dimension:
                raise ValueError(f"Embedding dimension mismatch: expected {dimension}, got {vector.shape[1]}")

            index.add(vector)
            documents.append(
                {
                    "text": text,
                    "source": source,
                    "page": page,
                    "law_type": law_type,
                    "user_id": user_id,
                }
            )
    except Exception as exc:
        logger.error(f"Error adding document: {exc}")
        raise


def save_index():
    """Save index with backup and atomic write."""
    try:
        with _index_lock:
            os.makedirs(INDEX_DIR, exist_ok=True)

            if os.path.exists(INDEX_PATH):
                try:
                    shutil.copy2(INDEX_PATH, BACKUP_INDEX_PATH)
                except Exception as exc:
                    logger.warning(f"Failed to backup index file: {exc}")
            if os.path.exists(DOC_PATH):
                try:
                    shutil.copy2(DOC_PATH, BACKUP_DOC_PATH)
                except Exception as exc:
                    logger.warning(f"Failed to backup docs file: {exc}")

            faiss.write_index(index, INDEX_PATH)
            with open(DOC_PATH, "wb") as f:
                pickle.dump(documents, f)

            logger.info(f"Index saved: {len(documents)} docs, {index.ntotal} vectors")
    except Exception as exc:
        logger.error(f"ERROR saving index: {exc}")
        raise


def search_index(
    query_embedding: List[float],
    k: int = 5,
    metadata_filters: Optional[Dict[str, Any]] = None,
    return_scores: bool = False,
) -> List[Dict[str, Any]]:
    """Dense vector search with optional metadata filtering."""
    try:
        with _index_lock:
            if index.ntotal == 0:
                return []

            search_k = min(index.ntotal, max(k * 20, k))
            vector = np.array([query_embedding], dtype="float32")
            distances, indices = index.search(vector, search_k)

            results = []
            for rank, doc_idx in enumerate(indices[0]):
                if doc_idx < 0 or doc_idx >= len(documents):
                    continue

                doc = documents[doc_idx]
                if not _matches_filters(doc, metadata_filters):
                    continue

                if return_scores:
                    results.append(
                        _doc_copy_with_score(
                            doc,
                            {
                                "_dense_rank": rank + 1,
                                "_distance": float(distances[0][rank]),
                            },
                        )
                    )
                else:
                    results.append(doc)

                if len(results) >= k:
                    break

            return results
    except Exception as exc:
        logger.error(f"Search error: {exc}")
        return []


def lexical_search(
    query_text: str,
    k: int = 5,
    metadata_filters: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Simple BM25-style lexical retrieval over indexed chunks."""
    try:
        q_terms = _tokenize(query_text)
        if not q_terms:
            return []

        q_unique = list(dict.fromkeys(q_terms))

        with _index_lock:
            filtered_docs = [doc for doc in documents if _matches_filters(doc, metadata_filters)]
            if not filtered_docs:
                return []

            doc_tokens = [_tokenize(doc.get("text", "")) for doc in filtered_docs]
            avg_doc_len = (sum(len(toks) for toks in doc_tokens) / max(len(doc_tokens), 1)) or 1.0

            df = Counter()
            for toks in doc_tokens:
                for term in set(toks):
                    if term in q_unique:
                        df[term] += 1

            k1 = 1.2
            b = 0.75
            scored = []
            for rank_idx, (doc, toks) in enumerate(zip(filtered_docs, doc_tokens), start=1):
                if not toks:
                    continue

                tf = Counter(toks)
                doc_len = len(toks)
                score = 0.0

                for term in q_unique:
                    term_tf = tf.get(term, 0)
                    if term_tf <= 0:
                        continue

                    n_docs = len(filtered_docs)
                    term_df = df.get(term, 0)
                    idf = math.log(((n_docs - term_df + 0.5) / (term_df + 0.5)) + 1.0)
                    denom = term_tf + k1 * (1.0 - b + b * (doc_len / avg_doc_len))
                    score += idf * ((term_tf * (k1 + 1.0)) / max(denom, 1e-9))

                if score <= 0:
                    continue

                scored.append(
                    _doc_copy_with_score(
                        doc,
                        {
                            "_lexical_score": float(score),
                            "_lexical_rank": rank_idx,
                        },
                    )
                )

            scored.sort(key=lambda item: item.get("_lexical_score", 0.0), reverse=True)
            return scored[:k]
    except Exception as exc:
        logger.error(f"Lexical search error: {exc}")
        return []


def hybrid_search(
    query_text: str,
    query_embedding: List[float],
    k: int = 6,
    metadata_filters: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Hybrid retrieval: Dense + Lexical with reciprocal rank fusion."""
    dense_results = search_index(
        query_embedding,
        k=max(8, k * 2),
        metadata_filters=metadata_filters,
        return_scores=True,
    )
    lexical_results = lexical_search(
        query_text,
        k=max(8, k * 2),
        metadata_filters=metadata_filters,
    )

    if not dense_results and not lexical_results:
        return []

    def key_for(doc: Dict[str, Any]) -> str:
        text = str(doc.get("text", ""))[:220]
        source = str(doc.get("source", ""))
        page = str(doc.get("page", ""))
        return f"{source}|{page}|{hash(text)}"

    merged: Dict[str, Dict[str, Any]] = {}

    for rank, doc in enumerate(dense_results, start=1):
        key = key_for(doc)
        payload = merged.setdefault(key, dict(doc))
        payload["_rrf_score"] = payload.get("_rrf_score", 0.0) + (1.0 / (60.0 + rank))
        payload["_dense_rank"] = rank

    for rank, doc in enumerate(lexical_results, start=1):
        key = key_for(doc)
        payload = merged.setdefault(key, dict(doc))
        payload["_rrf_score"] = payload.get("_rrf_score", 0.0) + (1.0 / (60.0 + rank))
        if "_lexical_score" in doc:
            payload["_lexical_score"] = doc["_lexical_score"]
        payload["_lexical_rank"] = rank

    ranked = sorted(merged.values(), key=lambda item: item.get("_rrf_score", 0.0), reverse=True)
    return ranked[:k]


def reset_index():
    """Reset index safely."""
    global index, documents
    try:
        with _index_lock:
            logger.warning("Resetting FAISS index...")
            index = faiss.IndexFlatL2(dimension)
            documents = []
            logger.info("Index reset successfully")
    except Exception as exc:
        logger.error(f"Error resetting index: {exc}")
        raise


def get_index_info() -> Dict[str, Any]:
    """Get current index state info."""
    try:
        with _index_lock:
            law_type_counts = Counter(str(doc.get("law_type", "GENERAL")) for doc in documents)
            uploaded_docs = sum(1 for doc in documents if doc.get("law_type") == "UPLOADED_DOC")
            return {
                "vectors": index.ntotal,
                "documents": len(documents),
                "uploaded_documents": uploaded_docs,
                "law_type_distribution": dict(law_type_counts),
                "consistent": index.ntotal == len(documents),
            }
    except Exception as exc:
        logger.error(f"Error getting index info: {exc}")
        return {"error": str(exc)}

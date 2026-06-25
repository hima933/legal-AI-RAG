# LQ-RAG Legal AI

Legal AI assistant for document-grounded question answering on legal content.

This project combines:
- FastAPI backend with JWT auth
- Next.js frontend with login/signup flow
- RAG pipeline with hybrid retrieval (dense + lexical), reranking, and recursive answer refinement
- MongoDB for users/query logs/feedback/evaluation
- FAISS vector index for legal chunk retrieval

## What This App Does

Users can:
- Create an account and log in
- Upload legal documents (PDF, DOCX, TXT, RTF, images)
- Ask questions in two modes:
  - `Ask about this document` (uploaded-doc-only retrieval)
  - `Ask general legal question` (full index retrieval)
- Receive:
  - Final answer
  - Confidence score
  - Citations and legal analysis summary
  - Transparency info ("why this answer")
- Submit feedback (`thumbs up/down`, correction text)

## Key Features

1. Authentication and Session Control
- Signup/login with JWT access token
- Protected backend routes for query/upload/feedback/evaluation
- Logout support
- Frontend auth guard: app redirects unauthenticated users to `/login`

2. Document Ingestion and Analysis
- Multi-file upload with progress
- Text extraction and chunking
- Embedding generation and FAISS indexing
- Document analysis metadata extraction:
  - case type, legal sections, court, parties, citations, key points

3. Advanced RAG Pipeline (v2)
- Hybrid retrieval:
  - dense vector search (FAISS)
  - lexical BM25-style search
  - reciprocal-rank-fusion merge
- Optional cross-encoder reranker
- Recursive feedback loop:
  - draft answer
  - critique/faithfulness check
  - query rewrite + second retrieval pass when weak
  - final answer
- Multilingual hook:
  - query language detection
  - translate-to-English retrieval path
  - answer translated back to query language

4. Quality and Trust Controls
- Citation generation with source/page/law_type/preview
- Retrieval + faithfulness evaluation metrics per query:
  - faithfulness score
  - hallucination risk
  - precision@k
  - recall@k
  - citation coverage
- Evaluation dashboard in settings (last 30 days)
- User feedback capture for continuous improvement

## Typical Use Cases

- Law student asks case-law questions using uploaded judgments
- Legal researcher compares extracted sections/arguments from documents
- Operations team evaluates RAG quality across releases
- Domain user asks multilingual legal queries with traceable citations

## End-to-End Functional Flow

1. User opens app
- If not authenticated: redirected to `/login`
- New users can create account at `/signup`

2. Upload (optional but recommended for case-specific Q&A)
- Files sent to `/api/upload`
- Backend extracts text, chunks it, embeds it, adds to FAISS with `law_type=UPLOADED_DOC`
- Analysis saved to MongoDB

3. Ask question
- Frontend sends `/api/query` with:
  - `question`
  - `use_uploaded_context` (true for document mode)
- Backend runs RAG pipeline:
  - retrieval -> rerank -> draft -> critique -> optional second pass -> final answer

4. Render result
- Frontend shows answer, confidence, structured legal analysis, citations, transparency

5. Feedback and evaluation
- User submits feedback to `/api/feedback`
- Query metrics are stored and aggregated in `/api/eval/summary`

## Architecture

### High-level

```text
Next.js UI (React)
   |
   | Axios (JWT bearer token)
   v
FastAPI Backend
   |- Auth routes (signup/login/me/logout)
   |- Upload route (ingest + analyze + index)
   |- Query route (RAG pipeline)
   |- Feedback route
   |- Evaluation route
   |
   |- MongoDB (users, queries, analyses, feedback, eval)
   |- FAISS index (vector chunks + metadata)
   |- Embedding model(s)
   |- LLM provider: Ollama (phi3)
```

### Backend Modules

- `backend/main.py`
  - app setup, CORS, startup checks, route registration
- `backend/routes/`
  - `auth.py`: signup/login/me/change-password/logout
  - `upload.py`: upload, parse, chunk, embed, index, analyze
  - `query.py`: protected query endpoint + query/evaluation persistence
  - `feedback.py`: thumbs up/down + correction capture
  - `evaluation.py`: release-wise metric aggregation
- `backend/rag/pipeline.py`
  - retrieval orchestration, critique loop, final answer generation, metadata
- `backend/vectorstore/faiss_store.py`
  - dense search, lexical search, hybrid fusion, metadata filters
- `backend/embeddings/embedder.py`
  - legal-first embedding model fallback stack

### Frontend Modules

- `legal-ai-frontend/src/app/`
  - `page.js`: main app shell (tabs: Ask/History/Settings)
  - `login/page.js`, `signup/page.js`: auth entry pages
- `legal-ai-frontend/src/components/`
  - `QueryPanel`, `DocumentUpload`, `ResponsePanel`, `HistoryPanel`, `ModelSelector`, `Header`
- `legal-ai-frontend/src/lib/api.js`
  - API client, token handling, storage-safe wrappers, timeouts

## API Overview

Base URL: `http://localhost:8000/api`

Auth:
- `POST /auth/signup`
- `POST /auth/login`
- `GET /auth/me`
- `POST /auth/change-password`
- `POST /auth/logout`

RAG + Upload:
- `POST /query`


Feedback + Evaluation:
- `POST /feedback`
- `GET /feedback`
- `GET /eval/summary`

Model / System:

- `GET /health`


## Data Storage

MongoDB collections:
- `users`
- `queries`
- `document_analyses`
- `query_feedback`
- `query_evaluations`

Local index files:
- `backend/faiss_index/index.faiss`
- `backend/faiss_index/documents.pkl`
- backup copies for recovery

## Setup

### Prerequisites
- Python 3.11
- Node.js 20+ (recommended for current Next.js)
- MongoDB (Atlas or local)
- Optional local LLM: Ollama

### 1) Backend Setup

```powershell
cd backend
copy .env.example .env
pip install -r requirements.txt
```

Fill required values in `.env`:
- `MONGO_URI`
- `MONGO_DB_NAME`
- LLM provider keys/settings as needed

Install dependencies:

```powershell
C:\Users\Malle\AppData\Local\Programs\Python\Python311\python.exe -m pip install -r requirements.txt
```

Run backend:

```powershell
uvicorn main:app --reload
```

### 2) Frontend Setup

```powershell
cd legal-ai-frontend
copy .env.example .env.local
npm install
npm install axios next@16.1.6 react@19.2.3 react-dom@19.2.3
npm install -D @tailwindcss/postcss eslint eslint-config-next@16.1.6 tailwindcss
npm run devcd
```

Frontend default URL:
- `http://localhost:3000`

## Configuration Notes

Frontend timeouts (`legal-ai-frontend/.env.local`):
- `NEXT_PUBLIC_API_TIMEOUT=300000`
- `NEXT_PUBLIC_UPLOAD_TIMEOUT=900000`

Embedding and reranker (optional backend env):
- `EMBEDDING_MODEL_CANDIDATES`
- `EMBEDDING_TARGET_DIM`
- `ENABLE_CROSS_ENCODER_RERANKER=true|false`
- `CROSS_ENCODER_MODEL=...`

## Testing and Validation

Python syntax check (use explicit Python path):

```powershell
C:\Users\Malle\AppData\Local\Programs\Python\Python311\python.exe -m py_compile main.py routes\auth.py routes\query.py routes\upload.py rag\pipeline.py vectorstore\faiss_store.py
```

Frontend lint/build:

```powershell
cd legal-ai-frontend
npx eslint src\app\page.js src\components\ResponsePanel.jsx src\components\ModelSelector.jsx src\lib\api.js
npm run build
```

## Security and Scope Notes

- This app provides informational legal assistance, not legal advice.
- JWT token invalidation is client-side logout; server-side token revocation list is not implemented.
- Uploaded-document mode is enforced through retrieval metadata filters (`law_type=UPLOADED_DOC`, user scope).


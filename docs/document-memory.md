# Document Memory (M11)

Jarvis can index your local files and answer questions about them using Retrieval-Augmented Generation (RAG). The system runs **entirely offline** — all extraction, embeddings, vector search, and (optional) LLM generation happen on your machine. Nothing leaves your computer.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                         │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Documents.tsx: upload, index-folder, search, ask, manage  │ │
│  └───────────────────────────┬────────────────────────────────┘ │
└──────────────────────────────┼──────────────────────────────────┘
                               │  HTTP (REST)
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                     API (FastAPI)                                │
│  /api/documents  — CRUD, search, ask, status, clear             │
└───────────────────────────┬─────────────────────────────────────┘
          ┌─────────────────┼───────────────────┐
          ▼                 ▼                   ▼
┌──────────────────┐  ┌──────────────┐  ┌──────────────────┐
│   extractors.py   │  │  chunker.py  │  │  embeddings.py   │
│  Text + PDF ext.  │  │  1500-char   │  │  Simple / Ollama │
│  Modular provs.   │  │  200 overlap  │  │  (768-dim nomic) │
└────────┬──────────┘  └──────┬───────┘  └────────┬─────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                      indexer.py                                  │
│         extract → chunk → embed → store (orchestrator)          │
└─────────────────────────────────┬───────────────────────────────┘
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    vector_store.py                               │
│  SQLite (WAL mode)                                              │
│  ┌─────────────┐   ┌──────────────────────────────────┐        │
│  │ documents   │◄──│ chunks (id, doc_id, text,        │        │
│  │ (metadata,  │   │  embedding_json, metadata_json)   │        │
│  │  status)    │   │  FK → documents CASCADE          │        │
│  └─────────────┘   └──────────────────────────────────┘        │
│  Cosine similarity search in Python (fine for <10K chunks)     │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                     rag_engine.py                                │
│  1. Embed query  2. Search top_k  3. Build context   4. LLM?    │
│  If LLM available → RAG answer with source citations             │
│  If not → fallback: search results with text previews            │
└─────────────────────────────────────────────────────────────────┘
```

### Component Summary

| Component | File | Role |
|---|---|---|
| **Extractors** | `backend/memory/extractors.py` | Extract raw text from files (`.txt`, `.md`, `.py`, `.pdf`, and 30+ others) |
| **Chunker** | `backend/memory/chunker.py` | Split extracted text into overlapping chunks (1500 chars, 200 overlap) with natural break detection |
| **Embeddings** | `backend/memory/embeddings.py` | Convert text chunks into dense vectors (Simple hash-based or Ollama `nomic-embed-text`) |
| **Vector Store** | `backend/memory/vector_store.py` | SQLite-backed storage with cosine similarity search for documents and chunks |
| **Indexer** | `backend/memory/indexer.py` | Pipeline orchestrator: extract → chunk → embed → store |
| **RAG Engine** | `backend/memory/rag_engine.py` | Semantic search + LLM-powered question answering with source citations |
| **Models** | `backend/memory/models.py` | Pydantic schemas: `Document`, `DocumentChunk`, `SearchResult`, `RAGAnswer`, requests |
| **Skill** | `backend/skills/documents/` | Exposes document actions to Jarvis's skill system (chat-based control) |
| **API** | `backend/api/documents.py` | REST endpoints (`/api/documents`) for the frontend |

---

## Embedding Providers

Three providers are available, configured via `JARVIS_EMBEDDING_PROVIDER` in `.env`:

### Simple (default)

- **Status**: Built-in, always available, zero setup.
- **Method**: Character n-gram hashing (2/3/4-grams) with TF-like weighting.
- **Dimension**: 256
- **Best for**: Small document sets, quick testing, no internet/GPU required.
- **Trade-off**: Less accurate than real embedding models for large or diverse collections.

### Mock

- **Status**: Built-in, deterministic.
- **Method**: Pseudo-random unit vectors seeded from MD5 hash of text.
- **Dimension**: 384
- **Best for**: Development and testing only. Returns repeatable but semantically meaningless results.

### Ollama (nomic-embed-text)

- **Status**: Requires local Ollama installation.
- **Method**: Real transformer embeddings via `nomic-embed-text` (768 dimensions).
- **Dimension**: 768
- **Best for**: Production-quality semantic search. Much better recall for large document collections.
- **How it works**: Jarvis calls `POST http://localhost:11434/api/embeddings` for each text.

**Fallback behavior**: If you set `JARVIS_EMBEDDING_PROVIDER=ollama` but Ollama is unreachable at startup, Jarvis automatically falls back to the Simple provider with a log warning. Your documents still get indexed — just with lower-quality embeddings.

---

## Setup Guide

### Quick start (Simple provider — no setup needed)

The Simple embedding provider works out of the box. Just start Jarvis and you can index documents immediately.

### Ollama embeddings (recommended for quality)

**1. Install Ollama** (local PC, not VPS):

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**2. Pull the embedding model:**

```bash
ollama pull nomic-embed-text
```

This is a ~270 MB download that produces 768-dimensional embeddings — significantly better than the offline simple provider.

**3. Configure Jarvis** in your `.env` file:

```env
JARVIS_EMBEDDING_PROVIDER=ollama
```

**4. Verify:**

```bash
ollama list
# Should show nomic-embed-text:latest
```

Start Jarvis and check the status endpoint — it should report `embedding_provider: "ollama"` and `ready: true`.

---

## Supported File Types

The text extractor handles **30+ plain-text formats**:

| Category | Extensions |
|---|---|
| Documents | `.txt`, `.md`, `.rst`, `.org`, `.tex` |
| Code | `.py`, `.js`, `.ts`, `.tsx`, `.jsx`, `.html`, `.css`, `.sql`, `.rs`, `.go`, `.java`, `.c`, `.cpp`, `.h`, `.hpp`, `.rb`, `.php`, `.swift`, `.kt`, `.scala`, `.r`, `.lua` |
| Config/Data | `.json`, `.csv`, `.xml`, `.yaml`, `.yml`, `.toml`, `.ini`, `.cfg`, `.conf`, `.env` |
| Scripts | `.sh`, `.bash`, `.ps1`, `.bat`, `.vim` |

The PDF extractor handles **`.pdf`** files using `pypdf` (`PdfReader`). If `pypdf` is not installed, Jarvis returns a clear error with the install command (`pip install pypdf`).

> **Note on pypdf**: By default, `pypdf` is an optional dependency. Install it with `pip install pypdf` (or `uv add pypdf`) if you need PDF support. Text-based formats work without any extra dependencies.

---

## How to Index Documents

### Via the Frontend (Documents page)

1. Navigate to the **Documents** page in the Jarvis UI.
2. Use the **Index File** button to pick a single file, or **Index Folder** to scan an entire directory.
3. For folder indexing you can configure:
   - **Recursive** — whether to scan subdirectories (default: on).
   - **Include patterns** — glob patterns for files to include (default: `*.*`).
   - **Exclude patterns** — directories to skip (default: `.git`, `node_modules`, `.venv`, `__pycache__`, `.mypy_cache`, `.pytest_cache`, `dist`, `build`).
4. The system processes each file through the pipeline and shows live results — indexed count, failures, chunk counts.

### Via Chat / Skills

You can ask Jarvis directly in chat:

- `"index the file /home/user/notes/todo.md"`
- `"index all documents in my ~/Documents folder"`
- `"list my indexed documents"`
- `"remove that PDF from the index"`

These are routed through the documents skill (`backend/skills/documents/`).

### Via API

```bash
# Index a single file
curl -X POST http://localhost:8400/api/documents/index \
  -H "Content-Type: application/json" \
  -d '{"path": "/home/user/notes/todo.md"}'

# Index a folder recursively
curl -X POST http://localhost:8400/api/documents/index-folder \
  -H "Content-Type: application/json" \
  -d '{"folder_path": "/home/user/Documents", "recursive": true}'
```

---

## Searching and Asking Questions

### Semantic Search (`/api/documents/search`)

Find document chunks by meaning, not just keywords. Returns ranked results with cosine similarity scores.

```bash
curl -X POST http://localhost:8400/api/documents/search \
  -H "Content-Type: application/json" \
  -d '{"query": "how does the authentication system work?", "top_k": 5}'
```

Response includes `filename`, `chunk_index`, `score`, and `text_preview` for each result.

### Ask with RAG (`/api/documents/ask`)

Ask a question and get an AI-generated answer grounded in your documents.

```bash
curl -X POST http://localhost:8400/api/documents/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "what is the database connection string?", "top_k": 5}'
```

**How it works:**

1. Your question is embedded into a vector.
2. The top-k most similar chunks are retrieved from the vector store.
3. Retrieved chunks are assembled into a context (up to 6,000 characters).
4. If an LLM is available (Ollama or OpenAI-compatible), it generates an answer using the context with source citations.
5. If no LLM is available, Jarvis returns a fallback response listing the most relevant chunks with previews and a tip to set up an LLM.

The RAG prompt template instructs the LLM to only use provided context and cite sources. It never fabricates information not present in your documents.

### Via Chat

In chat you can say:
- `"search my documents for deployment instructions"`
- `"ask my documents: what is the default port?"`

---

## API Reference

All endpoints are under `http://localhost:8400/api/documents`.

### Documents

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/documents` | List all indexed documents. Optional `?status=indexed` filter. |
| `GET` | `/api/documents/{id}` | Get a single document with all its chunks. |
| `POST` | `/api/documents/index` | Index a single file. Body: `{"path": "..."}` |
| `POST` | `/api/documents/index-folder` | Index all supported files in a folder. Body: `{"folder_path": "...", "recursive": true}` |
| `DELETE` | `/api/documents/{id}` | Remove a document and all its chunks from the index. |

### Search & Ask

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/documents/search` | Semantic search. Body: `{"query": "...", "top_k": 5}` |
| `POST` | `/api/documents/ask` | RAG question answering. Body: `{"question": "...", "top_k": 5}` |

### Status & Admin

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/documents/status` | Memory status: document count, chunk count, embedding provider, ready state. |
| `POST` | `/api/documents/clear` | Delete all documents and chunks from the index (dangerous). |

### Response Models

**MemoryStatus:**

```json
{
  "documents": 42,
  "chunks": 287,
  "embedding_provider": "ollama",
  "ready": true,
  "error": null
}
```

**SearchResult:**

```json
{
  "document_id": "uuid",
  "filename": "notes.md",
  "chunk_id": "uuid",
  "chunk_index": 3,
  "score": 0.8742,
  "text_preview": "The authentication system uses JWT tokens with...",
  "metadata": {}
}
```

**RAGAnswer:**

```json
{
  "question": "how does auth work?",
  "answer": "The authentication system uses JWT tokens... [Source: auth.md]",
  "sources": [...],
  "provider": "rag+ollama",
  "error": null
}
```

---

## Limitations

### No OCR

The PDF extractor uses `pypdf` which only reads embedded text layers. Scanned documents, image-based PDFs, and photos of text are **not supported**. If your PDF contains a scanned image of text rather than selectable text, extraction will return empty.

### No ChromaDB (yet)

The vector store is currently **SQLite-based**. All similarity search is computed in Python by loading every chunk into memory. This works well for up to ~10,000 chunks, but:

- Search latency grows linearly with document count.
- No approximate nearest-neighbor (ANN) indexing.
- No GPU acceleration.

ChromaDB, LanceDB, or FAISS integrations are planned for future releases. The `VectorStore` interface is designed to make this swap straightforward — any replacement only needs to implement `search()`, `add_chunks()`, and `delete_chunks()`.

### Embedding quality with Simple provider

The Simple (hash-based) provider trades accuracy for convenience. It works for small collections but will produce lower-quality search results compared to real embedding models like `nomic-embed-text`. For any serious document question-answering, use the Ollama provider.

### No real-time file watching

Documents must be explicitly indexed. There is no filesystem watcher that auto-indexes new or modified files. If you edit an indexed file, re-index it to update the chunks.

---

## Privacy

**Everything runs locally.** The document memory system is designed with privacy as a core principle:

- **Text extraction** happens in-process — files are read directly from your disk.
- **Embeddings** are generated locally (Simple provider is pure Python; Ollama runs on your machine).
- **Vector storage** is a local SQLite file (`data/memory.db`).
- **LLM generation** (if used) queries your local Ollama instance or an API you configure — Jarvis itself does not send document content anywhere.
- **No telemetry, no cloud uploads, no third-party services** are used by the document memory module.

Your documents never leave your computer unless you configure an external LLM API, in which case only the assembled RAG context (up to 6,000 characters of relevant chunks) is sent with the prompt — not the original files.

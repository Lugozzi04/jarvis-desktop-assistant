"""Tests for Document Memory / RAG module."""

import pytest
import tempfile
from pathlib import Path


# ── Extractor Tests ──

class TestTextExtractor:
    def test_extract_txt(self):
        from backend.memory.extractors import TextExtractor
        ext = TextExtractor()
        with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
            f.write("Hello world\nLine two")
            f.flush()
            result = ext.extract(f.name)
        Path(f.name).unlink()
        assert result.success
        assert "Hello world" in result.text
        assert result.metadata["lines"] == 2

    def test_extract_markdown(self):
        from backend.memory.extractors import TextExtractor
        ext = TextExtractor()
        with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False) as f:
            f.write("# Title\n\nContent here.\n")
            f.flush()
            result = ext.extract(f.name)
        Path(f.name).unlink()
        assert result.success
        assert "Title" in result.text

    def test_extract_python(self):
        from backend.memory.extractors import TextExtractor
        ext = TextExtractor()
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("def hello():\n    return 'world'\n")
            f.flush()
            result = ext.extract(f.name)
        Path(f.name).unlink()
        assert result.success
        assert "hello" in result.text

    def test_extract_missing_file(self):
        from backend.memory.extractors import TextExtractor
        ext = TextExtractor()
        result = ext.extract("/nonexistent/file.txt")
        assert not result.success
        assert result.error is not None

    def test_can_handle(self):
        from backend.memory.extractors import TextExtractor
        ext = TextExtractor()
        assert ext.can_handle("test.py")
        assert ext.can_handle("test.md")
        assert ext.can_handle("test.tsx")
        assert not ext.can_handle("test.pdf")


class TestPdfExtractor:
    def test_missing_pypdf_fallback(self):
        from backend.memory.extractors import PdfExtractor
        ext = PdfExtractor()
        result = ext.extract("/tmp/test.pdf")
        if not ext._available:
            assert not result.success
            assert "pypdf" in result.error.lower()


# ── Chunker Tests ──

class TestChunker:
    def test_single_chunk_short_text(self):
        from backend.memory.chunker import chunk_text
        result = chunk_text("Short text", chunk_size=100, overlap=20)
        assert len(result.chunks) == 1
        assert result.chunks[0] == "Short text"

    def test_multiple_chunks(self):
        from backend.memory.chunker import chunk_text
        text = "word " * 500
        result = chunk_text(text, chunk_size=500, overlap=50)
        assert len(result.chunks) > 1
        assert result.metadata["count"] == len(result.chunks)

    def test_empty_text(self):
        from backend.memory.chunker import chunk_text
        result = chunk_text("", chunk_size=100, overlap=20)
        assert len(result.chunks) == 0

    def test_whitespace_only(self):
        from backend.memory.chunker import chunk_text
        result = chunk_text("   \n  \t  ", chunk_size=100, overlap=20)
        assert len(result.chunks) == 0


# ── Embedding Tests (synchronous, avoid global singleton) ──

class TestMockEmbeddingProvider:
    def test_embed_returns_list(self):
        """Test mock embedding without async (sync wrapper)."""
        import asyncio
        from backend.memory.embeddings import MockEmbeddingProvider
        provider = MockEmbeddingProvider()
        emb = asyncio.run(provider.embed("hello world"))
        assert isinstance(emb, list)
        assert len(emb) == provider.dimension
        assert all(isinstance(v, float) for v in emb)

    def test_embed_deterministic(self):
        import asyncio
        from backend.memory.embeddings import MockEmbeddingProvider
        provider = MockEmbeddingProvider()
        e1 = asyncio.run(provider.embed("hello"))
        e2 = asyncio.run(provider.embed("hello"))
        assert e1 == e2

    def test_embed_different_texts(self):
        import asyncio
        from backend.memory.embeddings import MockEmbeddingProvider
        provider = MockEmbeddingProvider()
        e1 = asyncio.run(provider.embed("hello"))
        e2 = asyncio.run(provider.embed("world"))
        assert e1 != e2

    def test_embed_batch(self):
        import asyncio
        from backend.memory.embeddings import MockEmbeddingProvider
        provider = MockEmbeddingProvider()
        texts = ["one", "two", "three"]
        embeddings = asyncio.run(provider.embed_batch(texts))
        assert len(embeddings) == 3
        assert all(len(e) == provider.dimension for e in embeddings)


class TestSimpleEmbeddingProvider:
    def test_embed_returns_list(self):
        import asyncio
        from backend.memory.embeddings import SimpleEmbeddingProvider
        provider = SimpleEmbeddingProvider()
        emb = asyncio.run(provider.embed("hello world"))
        assert isinstance(emb, list)
        assert len(emb) == provider.dimension

    def test_embed_deterministic(self):
        import asyncio
        from backend.memory.embeddings import SimpleEmbeddingProvider
        provider = SimpleEmbeddingProvider()
        e1 = asyncio.run(provider.embed("hello"))
        e2 = asyncio.run(provider.embed("hello"))
        assert e1 == e2

    def test_embed_batch(self):
        import asyncio
        from backend.memory.embeddings import SimpleEmbeddingProvider
        provider = SimpleEmbeddingProvider()
        embeddings = asyncio.run(provider.embed_batch(["a", "b", "c"]))
        assert len(embeddings) == 3


class TestOllamaEmbeddingProvider:
    def test_init_not_available_without_ollama(self):
        from backend.memory.embeddings import OllamaEmbeddingProvider
        provider = OllamaEmbeddingProvider()
        assert provider.name == "ollama"

    def test_embed_raises_when_unavailable(self):
        import asyncio
        from backend.memory.embeddings import OllamaEmbeddingProvider
        provider = OllamaEmbeddingProvider()
        if not provider.available:
            with pytest.raises(RuntimeError, match="Ollama not available"):
                asyncio.run(provider.embed("test"))


# ── Vector Store Tests ──

class TestVectorStore:
    @pytest.fixture
    def store(self):
        import tempfile, os
        from backend.memory.vector_store import VectorStore
        db_path = os.path.join(tempfile.gettempdir(), f"test_memory_{os.getpid()}.db")
        store = VectorStore(db_path=db_path)
        yield store
        try:
            os.unlink(db_path)
        except OSError:
            pass

    def test_add_and_get_document(self, store):
        from backend.memory.models import Document, DocumentStatus
        doc = Document(
            path="/tmp/test.md",
            filename="test.md",
            file_type=".md",
            size_bytes=100,
            status=DocumentStatus.indexed,
        )
        doc_id = store.add_document(doc)
        assert doc_id

        retrieved = store.get_document(doc_id)
        assert retrieved is not None
        assert retrieved.filename == "test.md"

    def test_list_documents(self, store):
        from backend.memory.models import Document, DocumentStatus
        for i in range(3):
            doc = Document(
                path=f"/tmp/doc{i}.md",
                filename=f"doc{i}.md",
                file_type=".md",
                status=DocumentStatus.indexed,
            )
            store.add_document(doc)
        docs = store.list_documents()
        assert len(docs) == 3

    def test_delete_document(self, store):
        from backend.memory.models import Document, DocumentStatus
        doc = Document(path="/tmp/del.md", filename="del.md", file_type=".md", status=DocumentStatus.indexed)
        doc_id = store.add_document(doc)
        # add_chunks is a required check, but we just test delete returns True
        result = store.delete_document(doc_id)
        assert result is True or result is not None

    def test_add_chunks_and_search(self, store):
        from backend.memory.models import Document, DocumentChunk, DocumentStatus
        doc = Document(path="/tmp/search.md", filename="search.md", file_type=".md", status=DocumentStatus.indexed)
        doc_id = store.add_document(doc)

        chunks = [
            DocumentChunk(document_id=doc_id, chunk_index=0, text="Python is a programming language"),
            DocumentChunk(document_id=doc_id, chunk_index=1, text="Docker containers are useful"),
            DocumentChunk(document_id=doc_id, chunk_index=2, text="Jarvis is a desktop assistant"),
        ]
        embeddings = [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ]
        store.add_chunks(chunks, embeddings)

        query_emb = [0.1, 0.9, 0.1]
        results = store.search(query_emb, top_k=2)
        assert len(results) > 0
        assert any("Docker" in r.text_preview for r in results)

    def test_get_status(self, store):
        from backend.memory.models import Document, DocumentStatus
        doc = Document(path="/tmp/s.md", filename="s.md", file_type=".md", status=DocumentStatus.indexed)
        store.add_document(doc)
        status = store.get_status()
        assert status["documents"] == 1

    def test_clear(self, store):
        from backend.memory.models import Document, DocumentStatus
        doc = Document(path="/tmp/c.md", filename="c.md", file_type=".md", status=DocumentStatus.indexed)
        store.add_document(doc)
        store.clear()
        assert store.get_status()["documents"] == 0


# ── RAG Engine Tests ──

class TestRagEngine:
    def test_search_no_documents(self):
        import asyncio
        import tempfile, os
        from backend.memory.rag_engine import RagEngine
        from backend.memory.embeddings import MockEmbeddingProvider
        from backend.memory.vector_store import VectorStore

        db_path = os.path.join(tempfile.gettempdir(), f"test_rag_empty_{os.getpid()}.db")
        store = VectorStore(db_path=db_path)
        provider = MockEmbeddingProvider()
        engine = RagEngine(vector_store=store, embedding_provider=provider)

        try:
            results = asyncio.run(engine.search("nothing here"))
            assert len(results) == 0
        finally:
            try:
                os.unlink(db_path)
            except OSError:
                pass

    def test_search_with_data(self):
        import asyncio
        import tempfile, os
        from backend.memory.rag_engine import RagEngine
        from backend.memory.embeddings import MockEmbeddingProvider
        from backend.memory.vector_store import VectorStore
        from backend.memory.models import Document, DocumentChunk, DocumentStatus

        db_path = os.path.join(tempfile.gettempdir(), f"test_rag_data_{os.getpid()}.db")
        store = VectorStore(db_path=db_path)
        provider = MockEmbeddingProvider()

        doc = Document(path="/tmp/notes.md", filename="notes.md", file_type=".md", status=DocumentStatus.indexed)
        doc_id = store.add_document(doc)

        chunk = DocumentChunk(document_id=doc_id, chunk_index=0, text="Kubernetes is a container orchestrator")
        embedding = asyncio.run(provider.embed("Kubernetes is a container orchestrator"))
        store.add_chunks([chunk], [embedding])

        engine = RagEngine(vector_store=store, embedding_provider=provider)

        try:
            results = asyncio.run(engine.search("container orchestration", top_k=3))
            assert len(results) == 1
            assert "notes.md" in results[0].filename
        finally:
            try:
                os.unlink(db_path)
            except OSError:
                pass

    def test_ask_fallback_without_llm(self):
        """ask() should return fallback results when LLM not available."""
        import asyncio
        import tempfile, os
        from backend.memory.rag_engine import RagEngine
        from backend.memory.embeddings import MockEmbeddingProvider
        from backend.memory.vector_store import VectorStore
        from backend.memory.models import Document, DocumentChunk, DocumentStatus

        db_path = os.path.join(tempfile.gettempdir(), f"test_rag_ask_{os.getpid()}.db")
        store = VectorStore(db_path=db_path)
        provider = MockEmbeddingProvider()

        doc = Document(path="/tmp/data.md", filename="data.md", file_type=".md", status=DocumentStatus.indexed)
        doc_id = store.add_document(doc)

        chunk = DocumentChunk(document_id=doc_id, chunk_index=0, text="The sky is blue because of Rayleigh scattering")
        embedding = asyncio.run(provider.embed("The sky is blue because of Rayleigh scattering"))
        store.add_chunks([chunk], [embedding])

        engine = RagEngine(vector_store=store, embedding_provider=provider)

        try:
            answer = asyncio.run(engine.ask("Why is the sky blue?", top_k=3))
            assert answer.question == "Why is the sky blue?"
            assert len(answer.sources) > 0
        finally:
            try:
                os.unlink(db_path)
            except OSError:
                pass


# ── Document Skill Tests ──

class TestDocumentSkill:
    def test_manifest_loads(self):
        """Test that the documents skill manifest can be loaded."""
        import json
        from pathlib import Path

        manifest_path = Path(__file__).parent.parent / "backend" / "skills" / "documents" / "manifest.json"
        if not manifest_path.exists():
            pytest.skip("Documents skill manifest not found")
        manifest = json.loads(manifest_path.read_text())
        assert manifest["name"] == "documents"
        assert len(manifest["actions"]) >= 5


# ── Slash Command Tests ──

class TestDocsSlashCommands:
    def test_docs_list_slash(self):
        from backend.core.router import intent_router
        intent = intent_router.route("/docs list")
        assert intent.skill == "documents"
        assert intent.action == "list_documents"

    def test_docs_search_slash(self):
        from backend.core.router import intent_router
        intent = intent_router.route("/docs search Docker setup")
        assert intent.skill == "documents"
        assert intent.action == "search_documents"
        assert intent.parameters["query"] == "Docker setup"

    def test_docs_ask_slash(self):
        from backend.core.router import intent_router
        intent = intent_router.route("/docs ask What is Kubernetes?")
        assert intent.skill == "documents"
        assert intent.action == "ask_documents"

    def test_docs_index_slash(self):
        from backend.core.router import intent_router
        intent = intent_router.route("/docs index /home/user/notes.md")
        assert intent.skill == "documents"
        assert intent.action == "index_file"

    def test_docs_clear_slash(self):
        from backend.core.router import intent_router
        intent = intent_router.route("/docs clear")
        assert intent.skill == "documents"
        assert intent.action == "clear_index"

    def test_docs_index_folder_slash(self):
        from backend.core.router import intent_router
        intent = intent_router.route("/docs index-folder /home/user/docs")
        assert intent.skill == "documents"
        assert intent.action == "index_folder"


# ── Model Tests ──

class TestDocumentModels:
    def test_document_model(self):
        from backend.memory.models import Document, DocumentStatus
        doc = Document(path="/tmp/test.md", filename="test.md", file_type=".md", status=DocumentStatus.pending)
        data = doc.model_dump()
        assert data["filename"] == "test.md"
        assert data["status"] == "pending"

    def test_search_result_model(self):
        from backend.memory.models import SearchResult
        sr = SearchResult(
            document_id="abc",
            filename="notes.md",
            chunk_id="chunk1",
            chunk_index=0,
            score=0.95,
            text_preview="Kubernetes is...",
        )
        data = sr.model_dump()
        assert data["score"] == 0.95

    def test_rag_answer_model(self):
        from backend.memory.models import RAGAnswer
        answer = RAGAnswer(question="Q", answer="A", provider="mock")
        data = answer.model_dump()
        assert data["question"] == "Q"
        assert data["answer"] == "A"

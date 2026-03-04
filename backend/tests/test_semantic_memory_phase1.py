"""Phase 1 tests: Embedder and vector memory infrastructure."""
import pytest
import asyncio
from services.embedder import embed_text, embed_batch, EMBEDDING_DIMENSION
from db.vector_memory import VectorMemory


class TestEmbedder:
    """Test embedding service."""
    
    def test_embedder_imports(self):
        """Test that embedder module loads correctly."""
        from services import embedder
        assert hasattr(embedder, 'embed_text')
        assert hasattr(embedder, 'embed_batch')
    
    @pytest.mark.asyncio
    async def test_embed_single_text(self):
        """Test single text embedding returns correct dimensions."""
        text = "This is a test sentence for embedding."
        embedding = await embed_text(text)
        
        assert isinstance(embedding, list)
        assert len(embedding) == EMBEDDING_DIMENSION
        assert all(isinstance(x, float) for x in embedding)
    
    @pytest.mark.asyncio
    async def test_embed_batch(self):
        """Test batch embedding."""
        texts = [
            "First test sentence.",
            "Second test sentence.",
            "Third test sentence."
        ]
        embeddings = await embed_batch(texts)
        
        assert len(embeddings) == len(texts)
        assert all(len(emb) == EMBEDDING_DIMENSION for emb in embeddings)


class TestVectorMemory:
    """Test vector memory storage."""
    
    def test_vector_memory_initialization(self):
        """Test VectorMemory initializes correctly."""
        vm = VectorMemory(persist_directory=".chroma_test")
        assert vm.collection is not None
        assert vm.client is not None
    
    def test_document_chunking(self):
        """Test long text splits into multiple chunks."""
        vm = VectorMemory(persist_directory=".chroma_test")
        
        # Create a long text (more than 512 tokens)
        long_text = " ".join(["This is a test sentence."] * 200)
        chunks = vm.chunk_text(long_text)
        
        assert len(chunks) > 1
        assert all(isinstance(chunk, str) for chunk in chunks)
    
    @pytest.mark.asyncio
    async def test_vector_memory_operations(self):
        """Test add, search, and delete operations.

        Uses a fresh isolated ChromaDB directory and deterministic non-zero
        embeddings so the test does not depend on Ollama being available and
        is not contaminated by leftover data from previous runs.
        """
        import random
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            vm = VectorMemory(persist_directory=tmpdir)

            conv_id = "test_conv_isolated_123"
            chunks = ["This is chunk one.", "This is chunk two."]

            # Deterministic non-zero unit-ish vectors — cosine sim well-defined.
            rng = random.Random(42)
            fake_embeddings = [[rng.uniform(0.1, 1.0) for _ in range(768)] for _ in chunks]
            # Use the first chunk's embedding as the query — perfect match expected.
            fake_query_emb = list(fake_embeddings[0])

            # Add conversation directly with the fake embeddings (no Ollama call).
            success = vm.add_conversation(
                conv_id=conv_id,
                chunks=chunks,
                embeddings=fake_embeddings,
                metadata={"title": "Test Conversation", "message_count": 5}
            )
            assert success is True

            # Search — threshold -1.0 ensures any cosine similarity passes.
            results = vm.search_similar(fake_query_emb, limit=5, score_threshold=-1.0)
            assert len(results) > 0

            # Delete conversation
            deleted = vm.delete_conversation(conv_id)
            assert deleted is True
    
    def test_get_stats(self):
        """Test getting collection statistics."""
        vm = VectorMemory(persist_directory=".chroma_test")
        stats = vm.get_stats()
        
        assert "total_chunks" in stats
        assert "collection_name" in stats
        assert isinstance(stats["total_chunks"], int)

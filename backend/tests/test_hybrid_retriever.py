import pytest
from unittest.mock import AsyncMock
from app.domain.document import ChunkMetadata
from app.domain.rag import RetrievalFilter, RetrievalResult
from app.services.retrieval.hybrid import QdrantHybridRetriever


@pytest.fixture
def sample_candidates():
    meta1 = ChunkMetadata(
        chunk_id="c1",
        document_id="d1",
        document_version=1,
        filename="SB100.pdf",
        page_number=2,
        section="Kazan Kapasitesi",
        document_type="technical_specification",
        department="engineering",
        language="tr",
        chunk_index=0,
        token_count=20,
    )
    meta2 = ChunkMetadata(
        chunk_id="c2",
        document_id="d2",
        document_version=1,
        filename="General.pdf",
        page_number=1,
        section="Emniyet",
        document_type="user_manual",
        department="service",
        language="tr",
        chunk_index=0,
        token_count=15,
    )

    r1 = RetrievalResult(
        chunk_id="c1",
        content="[Doc: SB100.pdf | Page: 2]\nSelnikel SB-100 buhar kazani 1000 kg/h buhar uretir.",
        metadata=meta1,
        score=0.80,
    )
    r2 = RetrievalResult(
        chunk_id="c2",
        content="[Doc: General.pdf | Page: 1]\nGenel endustriyel kazanlarda emniyet ventilleri standarttir.",
        metadata=meta2,
        score=0.85,
    )
    return [r2, r1]  # r2 higher dense, r1 has exact keyword match "SB-100"


@pytest.mark.asyncio
async def test_hybrid_retriever_empty_query():
    retriever = QdrantHybridRetriever()
    results = await retriever.retrieve("")
    assert results == []


@pytest.mark.asyncio
async def test_hybrid_retriever_rrf_scoring(sample_candidates):
    mock_embed = AsyncMock()
    mock_embed.embed_query.return_value = [0.1] * 1024

    mock_qdrant = AsyncMock()
    mock_qdrant.search.return_value = sample_candidates

    retriever = QdrantHybridRetriever(
        embed_provider=mock_embed,
        vector_repo=mock_qdrant,
    )

    # Query specifically for SB-100
    results = await retriever.retrieve(
        query="SB-100 buhar debisi",
        top_k=2,
        filter_criteria=RetrievalFilter(department="engineering"),
    )

    assert len(results) == 2
    # Verify exact keyword boost pushes SB-100 to the top
    assert "SB-100" in results[0].content
    assert results[0].score > results[1].score

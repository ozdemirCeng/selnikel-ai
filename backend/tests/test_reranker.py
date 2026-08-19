import pytest
from app.domain.document import ChunkMetadata
from app.domain.rag import RetrievalResult
from app.services.retrieval.reranker import (
    FlashRankReranker,
    PassThroughReranker,
    RerankerFactory,
)


@pytest.fixture
def sample_results():
    meta1 = ChunkMetadata(
        chunk_id="c1",
        document_id="d1",
        document_version=1,
        filename="Burner.pdf",
        page_number=4,
        section="Nozül",
        document_type="user_manual",
        department="service",
        language="tr",
        chunk_index=0,
        token_count=15,
    )
    meta2 = ChunkMetadata(
        chunk_id="c2",
        document_id="d2",
        document_version=1,
        filename="Boiler.pdf",
        page_number=1,
        section="Giriş",
        document_type="technical_specification",
        department="engineering",
        language="tr",
        chunk_index=0,
        token_count=18,
    )

    r1 = RetrievalResult(
        chunk_id="c1",
        content="Brülör nozül temizliği ve yakıt püskürtme kontrolü 500 saatte bir yapılır.",
        metadata=meta1,
        score=0.70,
    )
    r2 = RetrievalResult(
        chunk_id="c2",
        content="Selnikel endüstriyel kazanlar yüksek verimli üç geçişli duman borulu sistemlerdir.",
        metadata=meta2,
        score=0.75,
    )
    return [r2, r1]


@pytest.mark.asyncio
async def test_passthrough_reranker(sample_results):
    reranker = PassThroughReranker()
    reranked = await reranker.rerank("brülör nozül bakımı", sample_results, top_n=1)
    assert len(reranked) == 1
    assert reranked[0].chunk_id == "c2"  # Preserved top original candidate


@pytest.mark.asyncio
async def test_flashrank_reranker_execution(sample_results):
    reranker = FlashRankReranker()
    
    # Query specifically targeted at burner nozzles
    reranked = await reranker.rerank("brülör nozül bakım periyodu", sample_results, top_n=2)
    assert len(reranked) == 2
    
    # Cross-encoder should recognize r1 is far more relevant to burner nozzles than r2
    assert reranked[0].chunk_id == "c1"
    assert "nozül" in reranked[0].content


@pytest.mark.asyncio
async def test_reranker_factory_resolution():
    passthrough = RerankerFactory.get_reranker(force_passthrough=True)
    assert isinstance(passthrough, PassThroughReranker)

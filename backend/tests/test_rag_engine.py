import pytest
from unittest.mock import AsyncMock, MagicMock
from app.domain.document import ChunkMetadata
from app.domain.rag import GenerationOutput, RetrievalFilter, RetrievalResult
from app.services.rag.engine import DeterministicRAGEngine


@pytest.fixture
def mock_retrieval_result():
    meta = ChunkMetadata(
        chunk_id="chunk_123",
        document_id="doc_456",
        document_version=1,
        filename="SB_100_Datasheet.pdf",
        page_number=3,
        section="Teknik Bilgiler",
        document_type="technical_specification",
        department="engineering",
        language="tr",
        chunk_index=0,
        token_count=25,
        revision_id="rev_789",
        approval_status="approved",
    )
    return RetrievalResult(
        chunk_id="chunk_123",
        content="SB-100 buhar kazanı nominal 1000 kg/h buhar debisine ve 16 bar çalışma basıncına sahiptir.",
        metadata=meta,
        score=0.95,
    )


@pytest.mark.asyncio
async def test_rag_engine_sync_query(mock_retrieval_result):
    mock_retriever = AsyncMock()
    mock_retriever.retrieve.return_value = [mock_retrieval_result]

    mock_reranker = AsyncMock()
    mock_reranker.rerank.return_value = [mock_retrieval_result]

    mock_llm = AsyncMock()
    mock_llm.generate.return_value = (
        "SB-100 model kazan saatte 1000 kg/h buhar üretir [Belge: SB_100_Datasheet.pdf, Sayfa: 3]."
    )

    mock_res = MagicMock()
    mock_res.all.return_value = [("doc_456", "rev_789")]
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.execute.return_value = mock_res

    engine = DeterministicRAGEngine(
        retriever=mock_retriever,
        reranker=mock_reranker,
        llm=mock_llm,
    )

    output = await engine.query(
        query_text="SB-100 buhar debisi nedir?",
        top_k=1,
        filter_criteria=RetrievalFilter(department="engineering"),
        session=mock_session,
    )

    assert isinstance(output, GenerationOutput)
    assert "1000 kg/h" in output.answer
    assert len(output.citations) == 1
    assert output.citations[0].filename == "SB_100_Datasheet.pdf"
    assert output.citations[0].page_number == 3
    assert "SB_100_Datasheet.pdf" in output.sources_used
    assert mock_session.add.called


@pytest.mark.asyncio
async def test_rag_engine_streaming_query(mock_retrieval_result):
    mock_retriever = AsyncMock()
    mock_retriever.retrieve.return_value = [mock_retrieval_result]

    mock_reranker = AsyncMock()
    mock_reranker.rerank.return_value = [mock_retrieval_result]

    async def mock_stream_tokens(*args, **kwargs):
        for token in ["SB-100 ", "1000 kg/h ", "buhar üretir."]:
            yield token

    mock_llm = MagicMock()
    mock_llm.generate_stream = mock_stream_tokens

    engine = DeterministicRAGEngine(
        retriever=mock_retriever,
        reranker=mock_reranker,
        llm=mock_llm,
    )

    mock_stream_res = MagicMock()
    mock_stream_res.all.return_value = [("doc_456", "rev_789")]
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.execute.return_value = mock_stream_res

    events = []
    async for event in engine.query_stream("SB-100 kapasitesi", session=mock_session):
        events.append(event)

    assert len(events) >= 4  # status + 3 tokens + citations + done
    assert any("retrieval_status" in e for e in events)
    assert any("SB-100 " in e for e in events)
    assert any("[DONE]" in e for e in events)

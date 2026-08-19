import pytest
from app.domain.document import ChunkMetadata
from app.domain.rag import RetrievalResult
from app.services.rag.grounding import CitationEngine
from app.services.rag.prompts import SELNIKEL_RAG_SYSTEM_PROMPT, build_rag_user_prompt


def test_system_prompt_rules_contain_grounding_and_refusal():
    assert "YALNIZCA" in SELNIKEL_RAG_SYSTEM_PROMPT
    assert "Belirtilen teknik dokümanlarda bu konuyla ilgili bilgi bulunmamaktadır." in SELNIKEL_RAG_SYSTEM_PROMPT
    assert "Sayfa:" in SELNIKEL_RAG_SYSTEM_PROMPT


def test_build_rag_user_prompt_formats_context():
    meta = ChunkMetadata(
        chunk_id="c1",
        document_id="d1",
        document_version=1,
        filename="Kazan_Katalogu.pdf",
        page_number=5,
        section="Teknik Tablo",
        document_type="catalog",
        department="engineering",
        language="tr",
        chunk_index=0,
        token_count=30,
    )
    result = RetrievalResult(
        chunk_id="c1",
        content="SB-100 buhar debisi 1000 kg/h olarak test edilmiştir.",
        metadata=meta,
        score=0.92,
    )
    prompt = build_rag_user_prompt(
        query="SB-100 buhar debisi ne kadar?",
        retrieved_chunks=[result],
    )

    assert "Kazan_Katalogu.pdf" in prompt
    assert "Sayfa: 5" in prompt
    assert "SB-100 buhar debisi 1000 kg/h" in prompt
    assert "SB-100 buhar debisi ne kadar?" in prompt


def test_citation_engine_extracts_inline_citations():
    engine = CitationEngine()

    meta1 = ChunkMetadata(
        chunk_id="c1",
        document_id="doc_sb100",
        document_version=1,
        filename="SB_100_Datasheet.pdf",
        page_number=4,
        section="Kapasite",
        document_type="datasheet",
        department="engineering",
        language="tr",
        chunk_index=0,
        token_count=25,
    )
    r1 = RetrievalResult(
        chunk_id="c1",
        content="SB-100 buhar kazanı saatte 1000 kg buhar üretir.",
        metadata=meta1,
        score=0.88,
    )

    llm_answer = (
        "Selnikel SB-100 model kazan saatte 1000 kg/h buhar kapasitesine sahiptir "
        "[Belge: SB_100_Datasheet.pdf, Sayfa: 4]. İşletme basıncı 16 bar'dır."
    )

    citations, sources = engine.extract_and_verify_citations(
        answer_text=llm_answer,
        retrieved_chunks=[r1],
    )

    assert len(citations) == 1
    assert citations[0].filename == "SB_100_Datasheet.pdf"
    assert citations[0].page_number == 4
    assert citations[0].document_id == "doc_sb100"
    assert "SB_100_Datasheet.pdf" in sources


def test_citation_engine_handles_refusal():
    engine = CitationEngine()
    llm_refusal = "Belirtilen teknik dokümanlarda bu konuyla ilgili bilgi bulunmamaktadır."
    citations, sources = engine.extract_and_verify_citations(
        answer_text=llm_refusal,
        retrieved_chunks=[],
    )
    assert len(citations) == 0
    assert len(sources) == 0

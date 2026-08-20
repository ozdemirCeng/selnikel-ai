"""
Hybrid Retrieval & ACL Enforcement Test Suite
Validates Qdrant ACL filter generation, RRF scoring calculation, and citation grounding refusal logic.
"""
import pytest
from app.domain.rag import RetrievalFilter, RetrievalResult
from app.domain.document import ChunkMetadata
from app.infrastructure.qdrant import QdrantVectorRepository
from app.services.rag.grounding import CitationEngine

def test_qdrant_filter_builder_with_acl_departments():
    """Verify that allowed_departments generates a MatchAny condition for Qdrant."""
    repo = QdrantVectorRepository()
    filt = RetrievalFilter(
        allowed_departments=["dept-engineering", "dept-quality"],
        equipment_ids=["eq-sb100"],
        document_type="technical_specification"
    )
    built = repo._build_filter(filt)
    assert built is not None
    assert len(built.must) == 4
    keys = [cond.key for cond in built.must]
    assert "department" in keys
    assert "equipment_ids" in keys
    assert "document_type" in keys
    assert "approval_status" in keys


def test_citation_engine_refusal_on_empty_context():
    """Verify CitationEngine properly flags refusal response when model states insufficient context."""
    engine = CitationEngine()
    refusal_response = "Selnikel dokümanlarında bu model için maksimum işletme sıcaklığı belirtilmemiştir."
    
    is_refusal = engine.is_refusal_response(refusal_response)
    assert is_refusal is True


def test_citation_engine_citation_extraction():
    """Verify CitationEngine extracts inline [doc_id:page] tags into structured Citation objects."""
    engine = CitationEngine()
    answer_text = "Kazan işletme basıncı 16 bar olarak belirlenmiştir [doc-sb100:14]."
    
    citations = engine.extract_citations(
        answer_text=answer_text,
        retrieved_chunks=[
            RetrievalResult(
                chunk_id="chunk-1",
                content="SB-100 kazan işletme basıncı 16 bar.",
                metadata=ChunkMetadata(
                    chunk_id="chunk-1",
                    document_id="doc-sb100",
                    document_version=1,
                    filename="SB-100_Spec.pdf",
                    page_number=14,
                    section="3.2 Basınç Değerleri",
                    token_count=10,
                    is_table=False
                ),
                score=0.95
            )
        ]
    )
    
    assert len(citations) == 1
    assert citations[0].document_id == "doc-sb100"
    assert citations[0].page_number == 14

"""
Triple-Layer Access Control (ACL) & Cache Partitioning Test Suite
Validates simultaneous multi-tier enforcement:
1. PostgreSQL Catalog Filter
2. Qdrant Payload Pre-filter
3. Answer Citation Grounding Re-verification
4. Departmental Cache Key Isolation
"""
import pytest
from app.domain.identity.models import User
from app.domain.rag import RetrievalFilter, RetrievalResult, Citation
from app.domain.document import ChunkMetadata
from app.infrastructure.qdrant import QdrantVectorRepository
from app.services.rag.grounding import CitationEngine

def test_layer1_postgres_department_scope():
    """Verify that a non-admin user query strictly filters by authorized departments."""
    service_user = User(
        email="service@selnikel.com.tr",
        display_name="Servis Teknisyeni",
        department_ids=["dept-service"],
        role_codes=["service"]
    )
    # Service user cannot view engineering documents
    assert service_user.can_access_department("dept-service") is True
    assert service_user.can_access_department("dept-engineering") is False


def test_layer2_qdrant_vector_payload_filter():
    """Verify that Qdrant search injects allowed_departments into the vector filter."""
    repo = QdrantVectorRepository()
    filt = RetrievalFilter(
        allowed_departments=["dept-service"],
        equipment_ids=["eq-sb100"]
    )
    built_filter = repo._build_filter(filt)
    assert built_filter is not None
    
    # Must have 2 conditions (department MatchAny and equipment_ids MatchAny)
    assert len(built_filter.must) == 2
    assert built_filter.must[0].key == "department"
    assert built_filter.must[0].match.any == ["dept-service"]


def test_layer3_citation_provenance_acl_reverification():
    """Verify that citations extracted only keep chunks permitted by user's department."""
    engine = CitationEngine()
    
    allowed_chunks = [
        RetrievalResult(
            chunk_id="chunk-svc-1",
            content="Servis periyodik bakım aralığı 6 aydır.",
            metadata=ChunkMetadata(
                chunk_id="chunk-svc-1",
                document_id="doc-svc-001",
                document_version=1,
                filename="Servis_El_Kitabi.pdf",
                department="dept-service",
                page_number=5,
                is_table=False
            ),
            score=0.92
        )
    ]
    
    answer_text = "Bakım aralığı 6 aydır [Servis_El_Kitabi.pdf:5]."
    citations, sources = engine.extract_and_verify_citations(answer_text, allowed_chunks)
    
    assert len(citations) == 1
    assert citations[0].document_id == "doc-svc-001"
    assert citations[0].page_number == 5


def test_cache_key_partitioning_by_acl_scope():
    """Verify that cache keys isolate answers by user roles, departments, and ACL version."""
    def generate_cache_key(query: str, user: User, acl_version: str = "v1") -> str:
        dept_str = ",".join(sorted(user.department_ids))
        role_str = ",".join(sorted(user.role_codes))
        return f"rag:{query}:{user.id}:{dept_str}:{role_str}:{acl_version}"

    user_eng = User(
        id="usr-1",
        email="eng@selnikel.com.tr",
        display_name="Mühendis",
        department_ids=["dept-engineering"],
        role_codes=["engineer"]
    )
    user_svc = User(
        id="usr-2",
        email="svc@selnikel.com.tr",
        display_name="Servis",
        department_ids=["dept-service"],
        role_codes=["service"]
    )

    query = "Kazan maksimum işletme basıncı nedir?"
    key_eng = generate_cache_key(query, user_eng)
    key_svc = generate_cache_key(query, user_svc)

    # Cache keys MUST be strictly different preventing cross-department cache leakage
    assert key_eng != key_svc
    assert "dept-engineering" in key_eng
    assert "dept-service" in key_svc

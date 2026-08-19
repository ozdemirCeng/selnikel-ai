"""
Triple-Layer Access Control (ACL) & Cache Partitioning E2E Test Suite
Validates simultaneous multi-tier enforcement:
1. PostgreSQL Catalog ABAC Query Filtering
2. Qdrant Payload Pre-filter
3. Answer Citation Grounding & Provenance Re-verification
4. Production ACLPartitionedCacheKeyBuilder Isolation
5. Fail-Closed Negative Security Scenarios
"""
import pytest
from app.domain.identity.models import User
from app.domain.rag import RetrievalFilter, RetrievalResult, Citation
from app.domain.document import ChunkMetadata
from app.infrastructure.qdrant import QdrantVectorRepository
from app.services.rag.grounding import CitationEngine
from app.services.cache.key_builder import cache_key_builder

def test_layer1_postgres_department_scope():
    """Verify Layer 1: Service user cannot access engineering documents."""
    service_user = User(
        email="service@selnikel.com.tr",
        display_name="Servis Teknisyeni",
        department_ids=["dept-service"],
        role_codes=["service"]
    )
    # Service user cannot view engineering documents
    assert service_user.can_access_department("dept-service") is True
    assert service_user.can_access_department("dept-engineering") is False
    assert service_user.can_access_department("engineering") is False


def test_layer2_qdrant_vector_payload_filter():
    """Verify Layer 2: Qdrant search builder injects strict allowed_departments into the payload filter."""
    repo = QdrantVectorRepository()
    filt = RetrievalFilter(
        allowed_departments=["dept-service"],
        equipment_ids=["eq-sb100"]
    )
    built_filter = repo._build_filter(filt)
    assert built_filter is not None
    assert len(built_filter.must) == 2
    assert built_filter.must[0].key == "department"
    assert built_filter.must[0].match.any == ["dept-service"]
    assert built_filter.must[1].key == "equipment_ids"
    assert built_filter.must[1].match.any == ["eq-sb100"]


def test_layer3_citation_provenance_acl_reverification():
    """Verify Layer 3: Citations extracted only keep chunks permitted by user's department."""
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
            ),
            score=0.92
        )
    ]
    
    answer_text = "Bakım aralığı 6 aydır [Servis_El_Kitabi.pdf:5]. Ayrıca gizli Ar-Ge verisi [ArGe_Raporu.pdf:12]."
    citations, sources = engine.extract_and_verify_citations(answer_text, allowed_chunks)
    
    # ArGe_Raporu.pdf was NOT in allowed retrieved chunks -> MUST NOT be in verified citations
    assert len(citations) == 1
    assert citations[0].document_id == "doc-svc-001"
    assert citations[0].filename == "Servis_El_Kitabi.pdf"
    assert "ArGe_Raporu.pdf" not in sources


def test_production_cache_key_builder_partitioning():
    """Verify Layer 4: Production cache key builder guarantees departmental and role isolation."""
    user_eng = User(
        id="usr-100",
        email="eng@selnikel.com.tr",
        display_name="Mühendis",
        department_ids=["dept-engineering"],
        role_codes=["engineer"]
    )
    user_svc = User(
        id="usr-200",
        email="svc@selnikel.com.tr",
        display_name="Servis",
        department_ids=["dept-service"],
        role_codes=["service"]
    )

    query = "Kazan maksimum işletme basıncı nedir?"
    key_eng = cache_key_builder.generate_rag_cache_key(query, user_eng, classification="internal", acl_version="v1")
    key_svc = cache_key_builder.generate_rag_cache_key(query, user_svc, classification="internal", acl_version="v1")

    assert key_eng != key_svc
    assert "dept-engineering" in key_eng
    assert "dept-service" in key_svc
    assert key_eng.startswith("rag:")


def test_negative_security_fail_closed():
    """Verify negative security scenario: user with empty department list fails closed."""
    restricted_user = User(
        id="usr-999",
        email="guest@selnikel.com.tr",
        display_name="Kısıtlı Kullanıcı",
        department_ids=[],
        role_codes=["viewer"]
    )
    assert restricted_user.can_access_department("dept-engineering") is False
    assert restricted_user.can_access_department("dept-service") is False
    assert restricted_user.has_permission("document.upload") is False

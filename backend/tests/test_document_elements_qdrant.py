"""
DocumentElement and Qdrant Shadow Indexing Test Suite
Validates structural element representation, bounding boxes, and retrieval chunk metadata payloads.
"""
import pytest
from app.domain.retrieval.models import DocumentElement, ElementType, RetrievalChunk, BoundingBox

def test_document_element_table_structure():
    """Verify that DocumentElement preserves multi-column table JSON data."""
    table_elem = DocumentElement(
        document_id="doc-sb100",
        revision_id="rev-001",
        element_type=ElementType.TABLE,
        sequence=4,
        page_start=14,
        page_end=14,
        section_path=["3. Teknik Veriler", "3.2 Kazan Boyutları"],
        content="| Parametre | Değer | Birim |\n|---|---|---|\n| Nominal Buhar Kapasitesi | 1000 | kg/h |",
        structured_content={
            "headers": ["Parametre", "Değer", "Birim"],
            "rows": [
                ["Nominal Buhar Kapasitesi", "1000", "kg/h"],
                ["Maksimum İşletme Basıncı", "16.0", "bar"],
                ["Su Hacmi", "2.8", "m3"]
            ]
        },
        bounding_boxes=[
            BoundingBox(page=14, x=45.0, y=120.0, w=500.0, h=180.0)
        ],
        equipment_ids=["eq-sb100"],
        standard_references=["EN 12953-3"]
    )

    assert table_elem.element_type == ElementType.TABLE
    assert table_elem.structured_content["headers"] == ["Parametre", "Değer", "Birim"]
    assert len(table_elem.structured_content["rows"]) == 3
    assert table_elem.bounding_boxes[0].page == 14
    assert "EN 12953-3" in table_elem.standard_references


def test_retrieval_chunk_model_metadata_and_versioning():
    """Verify that RetrievalChunk carries explicit model versions and index metadata."""
    chunk = RetrievalChunk(
        document_element_id="elem-12345",
        document_id="doc-sb100",
        revision_id="rev-001",
        content="SB-100 buhar kazanı işletme basıncı 16 bar.",
        content_hash="d41d8cd98f00b204e9800998ecf8427e",
        token_count=12,
        embedding_model="BAAI/bge-m3",
        embedding_model_version="v1.0",
        index_version="v2.0",
        metadata={
            "department_id": "dept-engineering",
            "classification": "confidential",
            "approval_status": "approved",
            "equipment_ids": ["eq-sb100"],
            "page_start": 14
        }
    )

    assert chunk.embedding_model == "BAAI/bge-m3"
    assert chunk.embedding_model_version == "v1.0"
    assert chunk.index_version == "v2.0"
    assert chunk.metadata["department_id"] == "dept-engineering"
    assert chunk.metadata["approval_status"] == "approved"

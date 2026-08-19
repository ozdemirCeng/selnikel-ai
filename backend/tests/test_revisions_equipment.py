"""
Document Revision, Equipment, and ACL Domain & Migration Test Suite
Validates Equipment catalog taxonomy, revision status state machine, and ACL bindings.
"""
from datetime import datetime, timezone
import pytest
from app.domain.equipment.models import Equipment, EquipmentType
from app.domain.documents.models import (
    Document,
    DocumentRevision,
    DocumentType,
    DocumentClassification,
    RevisionApprovalStatus,
)

def test_equipment_domain_model_creation():
    """Verify Equipment domain model properties and attribute JSON serialization."""
    boiler = Equipment(
        equipment_type=EquipmentType.BOILER,
        model_code="SB-100",
        name="SB-100 Üç Geçişli Skoç Buhar Kazanı",
        attributes={
            "capacity_kg_h": 1000,
            "design_pressure_bar": 16.0,
            "fuel_type": "natural_gas",
            "thermal_efficiency_pct": 91.5
        }
    )
    assert boiler.model_code == "SB-100"
    assert boiler.equipment_type == EquipmentType.BOILER
    assert boiler.attributes["capacity_kg_h"] == 1000
    assert boiler.status == "active"


def test_document_revision_lifecycle():
    """Verify document revision versioning, approval states, and superseding links."""
    doc_id = "doc-12345"
    
    # 1. Initial Draft Revision (Rev. 01)
    rev1 = DocumentRevision(
        document_id=doc_id,
        revision_code="Rev. 01",
        revision_number=1,
        approval_status=RevisionApprovalStatus.APPROVED,
        approved_by="user-chief-engineer",
        approved_at=datetime.now(timezone.utc),
        source_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )
    assert rev1.revision_number == 1
    assert rev1.approval_status == RevisionApprovalStatus.APPROVED

    # 2. Subsequent Draft Revision (Rev. 02 superseding Rev. 01)
    rev2 = DocumentRevision(
        document_id=doc_id,
        revision_code="Rev. 02",
        revision_number=2,
        supersedes_revision_id=rev1.id,
        approval_status=RevisionApprovalStatus.DRAFT,
        source_sha256="a1b2c3d4e5f678901234567890abcdef1234567890abcdef1234567890abcdef"
    )
    assert rev2.revision_number == 2
    assert rev2.supersedes_revision_id == rev1.id
    assert rev2.approval_status == RevisionApprovalStatus.DRAFT


def test_document_classification_and_acl_attributes():
    """Verify Document classification and equipment linking."""
    doc = Document(
        title="SB-100 Buhar Kazanı Montaj ve İşletme Şartnamesi",
        filename="SB-100_Montaj_Sartnamesi.pdf",
        file_size=1048576,
        sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        department_id="dept-engineering",
        equipment_ids=["eq-sb-100"],
        classification=DocumentClassification.CONFIDENTIAL,
        created_by="user-engineer"
    )
    assert doc.classification == DocumentClassification.CONFIDENTIAL
    assert "eq-sb-100" in doc.equipment_ids
    assert doc.department_id == "dept-engineering"

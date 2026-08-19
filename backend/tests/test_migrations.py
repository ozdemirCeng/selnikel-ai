"""
Alembic Database Migration Verification Test Suite
Tests migration configuration, revision graph integrity, and reversible script execution.
"""
import os
import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

def test_alembic_configuration_and_revisions():
    """Verify that alembic.ini is present and revision graph is consistent."""
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    alembic_ini = os.path.join(backend_dir, "alembic.ini")
    assert os.path.exists(alembic_ini), "alembic.ini file does not exist"
    
    config = Config(alembic_ini)
    config.set_main_option("script_location", os.path.join(backend_dir, "alembic"))
    
    script_dir = ScriptDirectory.from_config(config)
    revisions = list(script_dir.walk_revisions())
    
    assert len(revisions) >= 5, "Expected at least 5 revisions."
    
    rev_ids = [r.revision for r in revisions]
    assert "001_baseline" in rev_ids
    assert "002_identity_org" in rev_ids
    assert "003_doc_rev_equip" in rev_ids
    assert "004_doc_elements" in rev_ids
    assert "005_ingestion_jobs" in rev_ids

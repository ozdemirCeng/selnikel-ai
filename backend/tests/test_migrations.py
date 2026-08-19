"""
Alembic Database Migration Verification Test Suite
Tests live schema migration execution: upgrade head -> downgrade base -> re-upgrade head.
"""
import os
import pytest
from sqlalchemy import create_engine, inspect
from alembic.config import Config
from alembic import command
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
    
    assert len(revisions) >= 5, "Expected 5 revisions."
    
    rev_ids = [r.revision for r in revisions]
    assert "001_baseline" in rev_ids
    assert "002_identity_org" in rev_ids
    assert "003_doc_rev_equip" in rev_ids
    assert "004_doc_elements" in rev_ids
    assert "005_ingestion_jobs" in rev_ids


def test_live_alembic_upgrade_downgrade_cycle(tmp_path):
    """Execute live two-way migration lifecycle (upgrade head -> downgrade base -> upgrade head)."""
    db_file = tmp_path / "test_migration.db"
    db_url = f"sqlite:///{db_file}"

    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    alembic_ini = os.path.join(backend_dir, "alembic.ini")
    
    config = Config(alembic_ini)
    config.set_main_option("script_location", os.path.join(backend_dir, "alembic"))
    config.set_main_option("sqlalchemy.url", db_url)

    engine = create_engine(db_url)

    # 1. Upgrade to head
    command.upgrade(config, "head")

    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    expected_tables = [
        "documents",
        "document_chunks",
        "query_logs",
        "permissions",
        "roles",
        "departments",
        "users",
        "equipment",
        "document_revisions",
        "document_elements",
        "ingestion_jobs"
    ]
    for table in expected_tables:
        assert table in tables, f"Expected table '{table}' was not created by upgrade head."

    # 2. Downgrade to base (clean rollback)
    command.downgrade(config, "base")
    
    inspector = inspect(engine)
    tables_after_downgrade = inspector.get_table_names()
    for table in expected_tables:
        assert table not in tables_after_downgrade, f"Table '{table}' should have been dropped by downgrade base."

    # 3. Re-upgrade to head (idempotent re-run)
    command.upgrade(config, "head")
    
    inspector = inspect(engine)
    tables_after_reupgrade = inspector.get_table_names()
    for table in expected_tables:
        assert table in tables_after_reupgrade, f"Table '{table}' was missing after re-upgrade."

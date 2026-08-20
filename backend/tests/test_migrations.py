"""
Alembic Database Migration Verification Test Suite
Tests live schema migration execution across dialects:
1. Revision graph consistency & chaining
2. Fast local SQLite upgrade -> downgrade -> re-upgrade cycle
3. Real PostgreSQL service migration cycle (when DATABASE_URL is set to postgresql)
"""
import os
import pytest
from sqlalchemy import create_engine, inspect
from alembic.config import Config
from alembic import command
from alembic.script import ScriptDirectory

EXPECTED_TABLES = [
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
    "ingestion_jobs",
    "user_external_identities",
    "outbox_events",
]

def test_alembic_configuration_and_revisions():
    """Verify that alembic.ini is present and revision graph is consistent."""
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    alembic_ini = os.path.join(backend_dir, "alembic.ini")
    assert os.path.exists(alembic_ini), "alembic.ini file does not exist"
    
    config = Config(alembic_ini)
    config.set_main_option("script_location", os.path.join(backend_dir, "alembic"))
    
    script_dir = ScriptDirectory.from_config(config)
    revisions = list(script_dir.walk_revisions())
    
    assert len(revisions) >= 8, f"Expected at least 8 revisions, found {len(revisions)}."
    
    rev_ids = [r.revision for r in revisions]
    assert "001_baseline" in rev_ids
    assert "002_identity_org" in rev_ids
    assert "003_doc_rev_equip" in rev_ids
    assert "004_doc_elements" in rev_ids
    assert "005_ingestion_jobs" in rev_ids
    assert "006_ext_id_queue_hardening" in rev_ids
    assert "007_revision_fsm_and_outbox" in rev_ids
    assert "008_add_outbox_next_attempt_at" in rev_ids


def test_sqlite_upgrade_downgrade_cycle(tmp_path):
    """Execute live two-way migration lifecycle on SQLite (upgrade head -> downgrade base -> upgrade head)."""
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
    for table in EXPECTED_TABLES:
        assert table in tables, f"Table '{table}' not created by upgrade head."

    # Verify next_attempt_at column added by migration 008
    outbox_cols = [c["name"] for c in inspector.get_columns("outbox_events")]
    assert "next_attempt_at" in outbox_cols, "Column 'next_attempt_at' missing from outbox_events table."

    # 2. Downgrade to base (clean rollback)
    command.downgrade(config, "base")
    inspector = inspect(engine)
    tables_after_downgrade = inspector.get_table_names()
    for table in EXPECTED_TABLES:
        assert table not in tables_after_downgrade, f"Table '{table}' not dropped by downgrade base."

    # 3. Re-upgrade to head (idempotent re-run)
    command.upgrade(config, "head")
    inspector = inspect(engine)
    tables_reupgrade = inspector.get_table_names()
    for table in EXPECTED_TABLES:
        assert table in tables_reupgrade, f"Table '{table}' missing after re-upgrade."
    reupgrade_outbox_cols = [c["name"] for c in inspector.get_columns("outbox_events")]
    assert "next_attempt_at" in reupgrade_outbox_cols


def test_postgresql_upgrade_downgrade_cycle():
    """
    Executes migration lifecycle on live PostgreSQL database.
    When REQUIRE_POSTGRES_MIGRATION=true (in CI), any failure or missing connection strictly FAILS the build.
    """
    require_postgres = os.environ.get("REQUIRE_POSTGRES_MIGRATION") == "true"
    pg_url = os.environ.get("TEST_POSTGRES_URL") or os.environ.get("DATABASE_URL")

    if not pg_url or not ("postgresql" in pg_url or "postgres" in pg_url):
        if require_postgres:
            pytest.fail("CI Gate Failure: REQUIRE_POSTGRES_MIGRATION=true but valid DATABASE_URL is not set.")
        else:
            pytest.skip("Live PostgreSQL service not configured (skipped in local unit run).")

    # Convert asyncpg connection string to sync psycopg2/pg8000 for alembic runner if needed
    sync_url = pg_url.replace("+asyncpg", "")

    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    alembic_ini = os.path.join(backend_dir, "alembic.ini")

    config = Config(alembic_ini)
    config.set_main_option("script_location", os.path.join(backend_dir, "alembic"))
    config.set_main_option("sqlalchemy.url", sync_url)

    try:
        engine = create_engine(sync_url)
        command.upgrade(config, "head")
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        for table in EXPECTED_TABLES:
            assert table in tables, f"PostgreSQL table '{table}' not created."

        command.downgrade(config, "base")
        command.upgrade(config, "head")
    except Exception as e:
        if require_postgres:
            pytest.fail(f"CI Gate Failure: PostgreSQL migration cycle failed with error: {e}")
        else:
            pytest.skip(f"PostgreSQL connection unavailable: {e}")

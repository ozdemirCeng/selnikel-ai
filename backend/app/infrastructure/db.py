from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from app.core.logging import logger
from app.db.base import Base
from app.db.session import engine


async def check_db_connection() -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


async def init_db_tables(custom_engine: AsyncEngine = engine) -> None:
    try:
        async with custom_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {e}")
        raise

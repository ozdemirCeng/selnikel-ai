from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import logger, setup_logging
from app.infrastructure.db import check_db_connection, init_db_tables
from app.infrastructure.qdrant import qdrant_repo


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging()
    logger.info(f"Starting {settings.PROJECT_NAME} backend in {settings.ENVIRONMENT} mode...")

    # Initialize DB tables if database is reachable
    if await check_db_connection():
        await init_db_tables()
    else:
        logger.warning("Database connection unavailable at startup. Retrying during requests.")

    # Check / Initialize Qdrant collection if reachable
    if await qdrant_repo.check_health():
        await qdrant_repo.ensure_collection(dimension=settings.EMBEDDING_DIMENSION)
    else:
        logger.warning("Qdrant connection unavailable at startup. Retrying during requests.")

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.PROJECT_NAME} backend...")
    await qdrant_repo.close()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Internal AI Engineering Knowledge System & Copilot Backend for Selnikel Enerji",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API v1 routes
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME} API",
        "docs": "/docs",
        "health": f"{settings.API_V1_PREFIX}/health",
        "version": "0.1.0",
    }


# Convenience alias for top-level /health check
@app.get("/health", tags=["Health"])
async def root_health():
    from app.api.v1.endpoints.health import health_check

    return await health_check()

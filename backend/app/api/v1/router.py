from fastapi import APIRouter
from app.api.v1.endpoints import agent, documents, evaluation, health, rag

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
api_router.include_router(rag.router, prefix="/rag", tags=["RAG"])
api_router.include_router(evaluation.router, tags=["Evaluation & Benchmarks"])
api_router.include_router(agent.router, tags=["AI Engineering Agent"])

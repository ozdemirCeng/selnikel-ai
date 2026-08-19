from typing import Any, Dict, List, Optional
from qdrant_client import AsyncQdrantClient, QdrantClient
from qdrant_client.http import models as rest_models
from app.core.config import settings
from app.core.logging import logger
from app.domain.document import ChunkMetadata, DomainChunk
from app.domain.rag import RetrievalFilter, RetrievalResult


class QdrantVectorRepository:
    """Repository abstraction encapsulating all Qdrant vector database operations.
    Keeps application domain and service layers decoupled from Qdrant-specific SDK logic.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        api_key: Optional[str] = None,
        collection_name: Optional[str] = None,
    ):
        self.host = host or settings.QDRANT_HOST
        self.port = port or settings.QDRANT_PORT
        self.api_key = api_key or settings.QDRANT_API_KEY
        self.collection_name = collection_name or settings.QDRANT_COLLECTION_NAME
        self._async_client: Optional[AsyncQdrantClient] = None

    @property
    def client(self) -> AsyncQdrantClient:
        if self._async_client is None:
            self._async_client = AsyncQdrantClient(
                host=self.host,
                port=self.port,
                api_key=self.api_key,
                timeout=10.0,
            )
        return self._async_client

    async def close(self) -> None:
        if self._async_client is not None:
            await self._async_client.close()
            self._async_client = None

    async def check_health(self) -> bool:
        """Check whether the Qdrant instance is reachable and responding."""
        try:
            collections = await self.client.get_collections()
            return collections is not None
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return False

    async def ensure_collection(
        self,
        dimension: int = 1024,
        distance: rest_models.Distance = rest_models.Distance.COSINE,
    ) -> bool:
        """Ensure the target Qdrant collection exists with appropriate dense vector parameters."""
        try:
            collections = await self.client.get_collections()
            existing_names = [c.name for c in collections.collections]

            if self.collection_name not in existing_names:
                logger.info(f"Creating Qdrant collection: {self.collection_name} (dim={dimension})")
                await self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=rest_models.VectorParams(
                        size=dimension,
                        distance=distance,
                    ),
                )
                # Create payload index for fast filtering
                for field_name in ["document_id", "department", "document_type", "language"]:
                    await self.client.create_payload_index(
                        collection_name=self.collection_name,
                        field_name=field_name,
                        field_schema=rest_models.PayloadSchemaType.KEYWORD,
                    )
            return True
        except Exception as e:
            logger.error(f"Failed to ensure Qdrant collection: {e}")
            return False

    def _build_filter(self, filter_spec: Optional[RetrievalFilter]) -> Optional[rest_models.Filter]:
        if not filter_spec:
            return None

        must_conditions: List[rest_models.FieldCondition] = []
        if filter_spec.department:
            must_conditions.append(
                rest_models.FieldCondition(
                    key="department",
                    match=rest_models.MatchValue(value=filter_spec.department),
                )
            )
        if filter_spec.allowed_departments:
            must_conditions.append(
                rest_models.FieldCondition(
                    key="department",
                    match=rest_models.MatchAny(any=filter_spec.allowed_departments),
                )
            )
        if filter_spec.document_type:
            must_conditions.append(
                rest_models.FieldCondition(
                    key="document_type",
                    match=rest_models.MatchValue(value=filter_spec.document_type),
                )
            )
        if filter_spec.document_id:
            must_conditions.append(
                rest_models.FieldCondition(
                    key="document_id",
                    match=rest_models.MatchValue(value=filter_spec.document_id),
                )
            )
        if filter_spec.equipment_ids:
            must_conditions.append(
                rest_models.FieldCondition(
                    key="equipment_ids",
                    match=rest_models.MatchAny(any=filter_spec.equipment_ids),
                )
            )
        if filter_spec.language:
            must_conditions.append(
                rest_models.FieldCondition(
                    key="language",
                    match=rest_models.MatchValue(value=filter_spec.language),
                )
            )

        if not must_conditions:
            return None
        return rest_models.Filter(must=must_conditions)

    async def upsert_chunks(
        self,
        chunks: List[DomainChunk],
        vectors: List[List[float]],
    ) -> bool:
        """Upsert chunk vectors and their rich metadata into Qdrant."""
        if len(chunks) != len(vectors):
            raise ValueError("Chunks and vectors lists must be equal in length.")

        points = [
            rest_models.PointStruct(
                id=chunk.metadata.chunk_id,
                vector=vector,
                payload={
                    "content": chunk.content,
                    "document_id": chunk.metadata.document_id,
                    "document_version": chunk.metadata.document_version,
                    "filename": chunk.metadata.filename,
                    "page_number": chunk.metadata.page_number,
                    "section": chunk.metadata.section,
                    "document_type": chunk.metadata.document_type,
                    "department": chunk.metadata.department,
                    "language": chunk.metadata.language,
                    "chunk_index": chunk.metadata.chunk_index,
                    "token_count": chunk.metadata.token_count,
                },
            )
            for chunk, vector in zip(chunks, vectors)
        ]

        try:
            await self.client.upsert(
                collection_name=self.collection_name,
                points=points,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to upsert points to Qdrant: {e}")
            raise

    async def search(
        self,
        query_vector: List[float],
        filter_spec: Optional[RetrievalFilter] = None,
        limit: int = 5,
    ) -> List[RetrievalResult]:
        """Search vector database and return domain RetrievalResult instances."""
        qdrant_filter = self._build_filter(filter_spec)
        try:
            search_result = await self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=qdrant_filter,
                limit=limit,
                with_payload=True,
            )

            results: List[RetrievalResult] = []
            for hit in search_result:
                payload = hit.payload or {}
                metadata = ChunkMetadata(
                    chunk_id=str(hit.id),
                    document_id=payload.get("document_id", ""),
                    document_version=payload.get("document_version", 1),
                    filename=payload.get("filename", ""),
                    page_number=payload.get("page_number", 1),
                    section=payload.get("section"),
                    document_type=payload.get("document_type", "technical_specification"),
                    department=payload.get("department", "engineering"),
                    language=payload.get("language", "tr"),
                    chunk_index=payload.get("chunk_index", 0),
                    token_count=payload.get("token_count"),
                )
                results.append(
                    RetrievalResult(
                        chunk_id=str(hit.id),
                        content=payload.get("content", ""),
                        metadata=metadata,
                        score=hit.score,
                    )
                )
            return results
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            raise

    async def delete_by_document_id(self, document_id: str) -> bool:
        """Delete all chunk vectors belonging to a specific document_id."""
        try:
            await self.client.delete(
                collection_name=self.collection_name,
                points_selector=rest_models.FilterSelector(
                    filter=rest_models.Filter(
                        must=[
                            rest_models.FieldCondition(
                                key="document_id",
                                match=rest_models.MatchValue(value=document_id),
                            )
                        ]
                    )
                ),
            )
            return True
        except Exception as e:
            logger.error(f"Failed to delete points for doc {document_id}: {e}")
            return False


# Global singleton instance for injection
qdrant_repo = QdrantVectorRepository()

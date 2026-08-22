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
                check_compatibility=False,
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
                for field_name in ["document_id", "department", "document_type", "language", "approval_status", "revision_id", "equipment_ids"]:
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
        if filter_spec.document_ids:
            must_conditions.append(
                rest_models.FieldCondition(
                    key="document_id",
                    match=rest_models.MatchAny(any=filter_spec.document_ids),
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
        if filter_spec.approval_status:
            must_conditions.append(
                rest_models.FieldCondition(
                    key="approval_status",
                    match=rest_models.MatchValue(value=filter_spec.approval_status),
                )
            )

        if not must_conditions:
            return None
        return rest_models.Filter(must=must_conditions)

    async def upsert_chunks(
        self,
        chunks: List[Any],
        vectors: Optional[List[List[float]]] = None,
    ) -> bool:
        """Upsert chunk vectors and their rich metadata into Qdrant idempotently using deterministic IDs."""
        if vectors is None:
            points = []
            for chk in chunks:
                chk_id = getattr(chk, "id", None) or getattr(chk, "metadata", {}).get("chunk_id")
                if not chk_id:
                    raise ValueError("Her parçacık (chunk) için deterministik ve benzersiz bir chunk_id sağlanmalıdır.")
                meta = dict(getattr(chk, "metadata", {}))
                vec = meta.pop("vector", None) or getattr(chk, "vector", None)
                if vec is None:
                    raise ValueError(f"Parçacık '{chk_id}' için embedding vektörü bulunamadı.")
                payload = {
                    "content": getattr(chk, "content", ""),
                    "document_id": getattr(chk, "document_id", ""),
                    "revision_id": getattr(chk, "revision_id", ""),
                    "document_element_id": getattr(chk, "document_element_id", ""),
                    "token_count": getattr(chk, "token_count", 0),
                    **meta,
                }
                points.append(
                    rest_models.PointStruct(
                        id=chk_id,
                        vector=vec,
                        payload=payload,
                    )
                )
        else:
            if len(chunks) != len(vectors):
                raise ValueError("Chunks and vectors lists must be equal in length.")

            points = []
            for chunk, vector in zip(chunks, vectors):
                chk_id = chunk.metadata.chunk_id if (hasattr(chunk, "metadata") and hasattr(chunk.metadata, "chunk_id")) else None
                if not chk_id:
                    raise ValueError("Her DomainChunk için deterministik chunk.metadata.chunk_id tanımlanmalıdır.")
                points.append(
                    rest_models.PointStruct(
                        id=chk_id,
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
                            "equipment_ids": getattr(chunk.metadata, "equipment_ids", []),
                            "classification": getattr(chunk.metadata, "classification", "public_internal"),
                            "approval_status": getattr(chunk.metadata, "approval_status", "approved"),
                            "revision_id": getattr(chunk.metadata, "revision_id", None),
                            "revision_number": getattr(chunk.metadata, "revision_number", None),
                            "revision_code": getattr(chunk.metadata, "revision_code", None),
                            "language": chunk.metadata.language,
                            "chunk_index": chunk.metadata.chunk_index,
                            "token_count": chunk.metadata.token_count,
                        },
                    )
                )

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
        filter_criteria: Optional[RetrievalFilter] = None,
        top_k: Optional[int] = None,
    ) -> List[RetrievalResult]:
        """Search vector database and return domain RetrievalResult instances."""
        effective_filter = filter_criteria or filter_spec
        effective_limit = top_k or limit
        qdrant_filter = self._build_filter(effective_filter)
        try:
            search_result = []
            if hasattr(self.client, "search"):
                search_result = await self.client.search(
                    collection_name=self.collection_name,
                    query_vector=query_vector,
                    query_filter=qdrant_filter,
                    limit=effective_limit,
                    with_payload=True,
                )
            elif hasattr(self.client, "query_points"):
                res = await self.client.query_points(
                    collection_name=self.collection_name,
                    query=query_vector,
                    query_filter=qdrant_filter,
                    limit=effective_limit,
                    with_payload=True,
                )
                search_result = getattr(res, "points", res)
            elif hasattr(self.client, "search_points"):
                search_result = await self.client.search_points(
                    collection_name=self.collection_name,
                    vector=query_vector,
                    filter=qdrant_filter,
                    limit=effective_limit,
                    with_payload=True,
                )

            results: List[RetrievalResult] = []
            for hit in search_result:
                payload = getattr(hit, "payload", None) or {}
                metadata = ChunkMetadata(
                    chunk_id=str(getattr(hit, "id", "")),
                    document_id=payload.get("document_id", ""),
                    document_version=payload.get("document_version", 1),
                    filename=payload.get("filename", ""),
                    page_number=payload.get("page_number", 1),
                    section=payload.get("section"),
                    document_type=payload.get("document_type", "technical_specification"),
                    department=payload.get("department", "engineering"),
                    equipment_ids=payload.get("equipment_ids", []),
                    classification=payload.get("classification", "public_internal"),
                    approval_status=payload.get("approval_status", "approved"),
                    revision_id=payload.get("revision_id"),
                    revision_number=payload.get("revision_number"),
                    revision_code=payload.get("revision_code"),
                    language=payload.get("language", "tr"),
                    chunk_index=payload.get("chunk_index", 0),
                    token_count=payload.get("token_count"),
                )
                results.append(
                    RetrievalResult(
                        chunk_id=str(getattr(hit, "id", "")),
                        content=payload.get("content", ""),
                        metadata=metadata,
                        score=getattr(hit, "score", 1.0),
                    )
                )
            return results
        except Exception as e:
            logger.warning(f"Qdrant vector search failed (falling back gracefully): {e}")
            return []

    async def update_revision_payload_status(
        self,
        document_id: str,
        approved_revision_id: str,
    ) -> bool:
        """
        Synchronize Qdrant payload approval statuses when a revision is approved:
        1. Set approval_status='obsolete' and is_active=false on all existing non-approved chunks for this document.
        2. Set approval_status='approved' and is_active=true on the target approved revision chunks.
        """
        try:
            # 1. Obsolete previous revision chunks
            await self.client.set_payload(
                collection_name=self.collection_name,
                payload={
                    "approval_status": "obsolete",
                    "is_active": False,
                },
                points=rest_models.Filter(
                    must=[
                        rest_models.FieldCondition(
                            key="document_id",
                            match=rest_models.MatchValue(value=document_id),
                        ),
                    ],
                    must_not=[
                        rest_models.FieldCondition(
                            key="revision_id",
                            match=rest_models.MatchValue(value=approved_revision_id),
                        ),
                    ],
                ),
            )

            # 2. Approve target revision chunks
            await self.client.set_payload(
                collection_name=self.collection_name,
                payload={
                    "approval_status": "approved",
                    "is_active": True,
                },
                points=rest_models.Filter(
                    must=[
                        rest_models.FieldCondition(
                            key="document_id",
                            match=rest_models.MatchValue(value=document_id),
                        ),
                        rest_models.FieldCondition(
                            key="revision_id",
                            match=rest_models.MatchValue(value=approved_revision_id),
                        ),
                    ],
                ),
            )
            logger.info(f"Updated Qdrant revision payload for document '{document_id}' (Approved Rev: '{approved_revision_id}').")
            return True
        except Exception as e:
            logger.error(f"Failed to update Qdrant revision payload for doc {document_id}: {e}")
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

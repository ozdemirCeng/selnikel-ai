from typing import Dict, List, Optional
from app.core.logging import logger
from app.domain.rag import RetrievalFilter, RetrievalResult
from app.infrastructure.qdrant import QdrantVectorRepository, qdrant_repo
from app.services.embedding.base import BaseEmbeddingProvider
from app.services.embedding.factory import embedding_provider
from app.services.retrieval.base import BaseRetriever


class QdrantHybridRetriever(BaseRetriever):
    """Hybrid Retriever combining dense semantic search and sparse keyword matching
    via Reciprocal Rank Fusion (RRF) with metadata pre-filtering.
    """

    def __init__(
        self,
        embed_provider: BaseEmbeddingProvider = embedding_provider,
        vector_repo: QdrantVectorRepository = qdrant_repo,
        rrf_k: int = 60,
    ):
        self.embedding_provider = embed_provider
        self.vector_repo = vector_repo
        self.rrf_k = rrf_k

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filter_criteria: Optional[RetrievalFilter] = None,
    ) -> List[RetrievalResult]:
        """Perform hybrid retrieval using dense vectors and Reciprocal Rank Fusion."""
        if not query.strip():
            return []

        # Fail-closed: If user has 0 allowed departments assigned, return empty list
        if filter_criteria and filter_criteria.allowed_departments is not None and len(filter_criteria.allowed_departments) == 0:
            logger.warning("Retrieval blocked: User has 0 allowed departments.")
            return []

        # 1. Compute Dense Query Embedding
        dense_vector = await self.embedding_provider.embed_query(query)

        # 2. Search Dense Vectors in Qdrant (fetch 2x top_k candidates for fusion)
        fetch_k = max(10, top_k * 2)
        dense_results = await self.vector_repo.search(
            query_vector=dense_vector,
            top_k=fetch_k,
            filter_criteria=filter_criteria,
        )

        # 3. If dense results found, apply Lexical / Exact Term Re-ranking Boost
        fused_results = self._apply_hybrid_rrf_scoring(
            query=query,
            candidates=dense_results,
            top_k=top_k,
        )

        # 4. If dense retrieval yielded 0 chunks, perform direct relational DB fallback search
        if not fused_results:
            logger.info(f"Dense retrieval produced 0 chunks for '{query[:30]}...'. Triggering relational DB fallback search.")
            fused_results = await self._retrieve_from_db(
                query=query,
                top_k=top_k,
                filter_criteria=filter_criteria,
            )

        logger.info(
            f"Hybrid retrieval for query '{query[:30]}...' yielded {len(fused_results)} chunks (top_k={top_k})."
        )
        return fused_results

    async def _retrieve_from_db(
        self,
        query: str,
        top_k: int = 5,
        filter_criteria: Optional[RetrievalFilter] = None,
    ) -> List[RetrievalResult]:
        """Relational fallback search querying SQL document_chunks directly."""
        try:
            import re
            from app.db.session import AsyncSessionLocal
            from app.db.models.document import DocumentChunkModel, DocumentModel
            from app.domain.document import ChunkMetadata
            from sqlalchemy import select, or_, and_

            async with AsyncSessionLocal() as session:
                stmt = select(DocumentChunkModel).join(DocumentModel, DocumentChunkModel.document_id == DocumentModel.id)

                # Department ACL Filter
                if filter_criteria and filter_criteria.allowed_departments is not None:
                    allowed = filter_criteria.allowed_departments + [d.replace("dept-", "") for d in filter_criteria.allowed_departments]
                    stmt = stmt.where(DocumentModel.department.in_(list(set(allowed))))
                if filter_criteria and filter_criteria.department:
                    stmt = stmt.where(
                        (DocumentModel.department == filter_criteria.department) |
                        (DocumentModel.department == filter_criteria.department.replace("dept-", ""))
                    )
                if filter_criteria and filter_criteria.document_id:
                    stmt = stmt.where(DocumentChunkModel.document_id == filter_criteria.document_id)

                # Keyword / Filename matching
                query_lower = query.lower()
                clean_terms = [t for t in re.findall(r"\w+", query_lower) if len(t) > 2 and t not in {"dokümanının", "dokümanı", "dokuman", "teknik", "özetini", "çıkar", "listele", "nedir", "nelerdir", "hakkında", "için", "olan"}]

                # Check if exact filenames are mentioned in query
                filename_matches = re.findall(r'[\w\-\.]+\.(?:pdf|docx|xlsx|xls|md|txt)', query, flags=re.IGNORECASE)
                chunks = []
                if filename_matches:
                    for fn in filename_matches:
                        fn_stmt = select(DocumentChunkModel).join(DocumentModel, DocumentChunkModel.document_id == DocumentModel.id).where(DocumentModel.filename.ilike(f"%{fn}%"))
                        if filter_criteria and filter_criteria.allowed_departments is not None:
                            allowed = filter_criteria.allowed_departments + [d.replace("dept-", "") for d in filter_criteria.allowed_departments]
                            fn_stmt = fn_stmt.where(DocumentModel.department.in_(list(set(allowed))))
                        fn_stmt = fn_stmt.order_by(DocumentChunkModel.chunk_index.asc()).limit(max(4, top_k))
                        fn_res = await session.execute(fn_stmt)
                        chunks.extend(fn_res.scalars().all())

                if not chunks:
                    conditions = []
                    if clean_terms:
                        term_conditions = []
                        for term in clean_terms[:5]:
                            term_conditions.append(DocumentChunkModel.content.ilike(f"%{term}%"))
                        if term_conditions:
                            conditions.append(or_(*term_conditions))

                    if conditions:
                        stmt = stmt.where(or_(*conditions))

                    stmt = stmt.order_by(DocumentChunkModel.created_at.desc()).limit(top_k * 3)
                    res = await session.execute(stmt)
                    chunks = list(res.scalars().all())

                if not chunks:
                    # Final fallback: retrieve most recent chunks in allowed departments
                    fallback_stmt = select(DocumentChunkModel).join(DocumentModel, DocumentChunkModel.document_id == DocumentModel.id)
                    if filter_criteria and filter_criteria.allowed_departments is not None:
                        allowed = filter_criteria.allowed_departments + [d.replace("dept-", "") for d in filter_criteria.allowed_departments]
                        fallback_stmt = fallback_stmt.where(DocumentModel.department.in_(list(set(allowed))))
                    fallback_stmt = fallback_stmt.order_by(DocumentChunkModel.created_at.desc()).limit(top_k)
                    fallback_res = await session.execute(fallback_stmt)
                    chunks = list(fallback_res.scalars().all())

                # Hydrate results with parent document
                doc_ids = list(set(c.document_id for c in chunks))
                docs_map = {}
                rev_map = {}
                if doc_ids:
                    from app.db.models.revision import DocumentRevisionModel
                    doc_stmt = select(DocumentModel).where(DocumentModel.id.in_(doc_ids))
                    doc_res = await session.execute(doc_stmt)
                    docs_map = {d.id: d for d in doc_res.scalars().all()}

                    rev_stmt = select(DocumentRevisionModel).where(
                        DocumentRevisionModel.document_id.in_(doc_ids),
                        DocumentRevisionModel.approval_status == "approved",
                    )
                    rev_res = await session.execute(rev_stmt)
                    rev_map = {r.document_id: r for r in rev_res.scalars().all()}

                results: List[RetrievalResult] = []
                for chunk in chunks:
                    parent_doc = docs_map.get(chunk.document_id)
                    approved_rev = rev_map.get(chunk.document_id)
                    meta = ChunkMetadata(
                        chunk_id=chunk.id,
                        document_id=chunk.document_id,
                        document_version=parent_doc.version if parent_doc else 1,
                        revision_id=approved_rev.id if approved_rev else None,
                        revision_code=approved_rev.revision_code if approved_rev else None,
                        revision_number=approved_rev.revision_number if approved_rev else None,
                        filename=parent_doc.filename if parent_doc else "",
                        page_number=chunk.page_number or 1,
                        section=chunk.section,
                        document_type=parent_doc.document_type if parent_doc else "technical_specification",
                        department=parent_doc.department if parent_doc else "engineering",
                        language=parent_doc.language if parent_doc else "tr",
                        chunk_index=chunk.chunk_index,
                        token_count=chunk.token_count,
                    )
                    results.append(
                        RetrievalResult(
                            chunk_id=chunk.id,
                            content=chunk.content,
                            metadata=meta,
                            score=0.85,
                        )
                    )
                return results[:max(top_k, len(results))]
        except Exception as e:
            logger.warning(f"Relational fallback retrieval error: {e}")
            return []

    def _apply_hybrid_rrf_scoring(
        self,
        query: str,
        candidates: List[RetrievalResult],
        top_k: int,
    ) -> List[RetrievalResult]:
        """Combine dense rank with exact keyword match scoring using RRF."""
        if not candidates:
            return []

        query_terms = set(query.lower().split())
        scored_candidates: List[RetrievalResult] = []

        for dense_rank, item in enumerate(candidates, start=1):
            content_lower = item.content.lower()

            # Calculate keyword match density
            matched_terms = [t for t in query_terms if t in content_lower and len(t) > 2]
            keyword_score = len(matched_terms) / max(1, len(query_terms))

            # RRF Combination: 1 / (k + dense_rank) + keyword_boost
            dense_rrf = 1.0 / (self.rrf_k + dense_rank)
            keyword_rrf = keyword_score * (1.0 / (self.rrf_k + 1))

            combined_score = (0.7 * dense_rrf) + (0.3 * keyword_rrf)
            
            scored_candidates.append(
                RetrievalResult(
                    chunk_id=item.chunk_id,
                    content=item.content,
                    metadata=item.metadata,
                    score=combined_score,
                )
            )

        # Sort by combined score descending
        scored_candidates.sort(key=lambda x: x.score, reverse=True)
        return scored_candidates[:top_k]


# Default singleton instance
hybrid_retriever = QdrantHybridRetriever()

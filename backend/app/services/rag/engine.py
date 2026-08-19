import json
import time
import uuid
from typing import AsyncGenerator, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging import logger
from app.db.models.query_log import QueryLogModel
from app.domain.rag import Citation, GenerationOutput, RetrievalFilter, RetrievalResult
from app.services.llm.base import BaseLLMProvider
from app.services.llm.factory import llm_provider
from app.services.rag.grounding import CitationEngine, citation_engine
from app.services.rag.prompts import SELNIKEL_RAG_SYSTEM_PROMPT, build_rag_user_prompt
from app.services.retrieval.base import BaseRetriever
from app.services.retrieval.hybrid import hybrid_retriever
from app.services.retrieval.reranker import BaseReranker, reranker_service


class DeterministicRAGEngine:
    """The central RAG engine orchestrating hybrid retrieval, cross-encoder reranking,
    grounded generation, citation attribution, and telemetry logging.
    """

    def __init__(
        self,
        retriever: BaseRetriever = hybrid_retriever,
        reranker: BaseReranker = reranker_service,
        llm: BaseLLMProvider = llm_provider,
        citation_eng: CitationEngine = citation_engine,
    ):
        self.retriever = retriever
        self.reranker = reranker
        self.llm = llm
        self.citation_engine = citation_eng

    async def query(
        self,
        query_text: str,
        top_k: int = 4,
        filter_criteria: Optional[RetrievalFilter] = None,
        session: Optional[AsyncSession] = None,
        user_id: Optional[str] = None,
    ) -> GenerationOutput:
        """Execute deterministic synchronous RAG query."""
        start_time = time.perf_counter()
        query_text = query_text.strip()

        if not query_text:
            return GenerationOutput(
                answer="Lütfen bir soru veya teknik parametre giriniz.",
                citations=[],
                sources_used=[],
            )

        # 1. Stage 1: Hybrid Retrieval (Dense + Sparse with RRF)
        fetch_candidates = max(10, top_k * 3)
        raw_candidates = await self.retriever.retrieve(
            query=query_text,
            top_k=fetch_candidates,
            filter_criteria=filter_criteria,
        )

        # 2. Stage 2: Cross-Encoder Reranking
        reranked_chunks = await self.reranker.rerank(
            query=query_text,
            results=raw_candidates,
            top_n=top_k,
        )

        # 3. Build Grounded Prompt
        user_prompt = build_rag_user_prompt(
            query=query_text,
            retrieved_chunks=reranked_chunks,
        )

        # 4. Generate Answer via LLM
        answer = await self.llm.generate(
            prompt=user_prompt,
            system_prompt=SELNIKEL_RAG_SYSTEM_PROMPT,
        )

        # 5. Extract and Verify Citations
        citations, sources = self.citation_engine.extract_and_verify_citations(
            answer_text=answer,
            retrieved_chunks=reranked_chunks,
        )

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        # 6. Audit Logging to PostgreSQL
        if session is not None:
            await self._log_query(
                session=session,
                query=query_text,
                answer=answer,
                chunks=reranked_chunks,
                citations=citations,
                latency_ms=latency_ms,
                user_id=user_id,
            )

        logger.info(
            f"RAG query completed in {latency_ms:.1f}ms with {len(citations)} citations."
        )

        return GenerationOutput(
            answer=answer,
            citations=citations,
            sources_used=sources,
        )

    async def query_stream(
        self,
        query_text: str,
        top_k: int = 4,
        filter_criteria: Optional[RetrievalFilter] = None,
        session: Optional[AsyncSession] = None,
        user_id: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream RAG response using Server-Sent Events (SSE)."""
        start_time = time.perf_counter()
        query_text = query_text.strip()

        if not query_text:
            yield f"data: {json.dumps({'type': 'token', 'content': 'Lütfen bir soru giriniz.'})}\n\n"
            yield "data: [DONE]\n\n"
            return

        # 1. Retrieve & Rerank
        raw_candidates = await self.retriever.retrieve(
            query=query_text,
            top_k=max(10, top_k * 3),
            filter_criteria=filter_criteria,
        )
        reranked_chunks = await self.reranker.rerank(
            query=query_text,
            results=raw_candidates,
            top_n=top_k,
        )

        # Emit initial event with retrieved sources overview
        initial_sources = list(set(r.metadata.filename for r in reranked_chunks))
        yield f"data: {json.dumps({'type': 'retrieval_status', 'sources': initial_sources, 'count': len(reranked_chunks)})}\n\n"

        # 2. Build Prompt
        user_prompt = build_rag_user_prompt(
            query=query_text,
            retrieved_chunks=reranked_chunks,
        )

        # 3. Stream LLM Tokens
        accumulated_text = ""
        try:
            async for token in self.llm.generate_stream(
                prompt=user_prompt,
                system_prompt=SELNIKEL_RAG_SYSTEM_PROMPT,
            ):
                accumulated_text += token
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
        except Exception as e:
            logger.error(f"Stream generation error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

        # 4. Extract Citations from full accumulated response
        citations, sources = self.citation_engine.extract_and_verify_citations(
            answer_text=accumulated_text,
            retrieved_chunks=reranked_chunks,
        )

        # 5. Emit Citations event
        citations_data = [c.model_dump() for c in citations]
        yield f"data: {json.dumps({'type': 'citations', 'citations': citations_data, 'sources_used': sources})}\n\n"
        yield "data: [DONE]\n\n"

        # 6. Audit Log
        latency_ms = (time.perf_counter() - start_time) * 1000.0
        if session is not None:
            await self._log_query(
                session=session,
                query=query_text,
                answer=accumulated_text,
                chunks=reranked_chunks,
                citations=citations,
                latency_ms=latency_ms,
                user_id=user_id,
            )

    async def _log_query(
        self,
        session: AsyncSession,
        query: str,
        answer: str,
        chunks: List[RetrievalResult],
        citations: List[Citation],
        latency_ms: float,
        user_id: Optional[str] = None,
    ) -> None:
        try:
            chunk_ids = [r.chunk_id for r in chunks]
            citations_data = [c.model_dump() for c in citations]
            log_record = QueryLogModel(
                id=str(uuid.uuid4()),
                query_text=query,
                retrieved_chunk_ids=chunk_ids,
                generated_answer=answer,
                citations=citations_data,
                latency_ms=latency_ms,
                llm_provider=getattr(self.llm, "provider_name", "openai"),
                llm_model=getattr(self.llm, "model_name", "gpt-4o-mini"),
            )
            session.add(log_record)
            await session.commit()
        except Exception as e:
            logger.warning(f"Failed to log query telemetry to database: {e}")


# Default singleton instance
rag_engine = DeterministicRAGEngine()

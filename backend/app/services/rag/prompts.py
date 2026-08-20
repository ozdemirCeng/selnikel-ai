"""
Prompt construction module bound directly to formal PromptContract.
Ensures generation pipeline uses versioned and security-hardened prompt templates.
"""
from typing import List
from app.domain.contracts.prompt import current_prompt_contract
from app.domain.rag import RetrievalResult

SELNIKEL_RAG_SYSTEM_PROMPT = current_prompt_contract.system_prompt


def build_rag_user_prompt(query: str, retrieved_chunks: List[RetrievalResult]) -> str:
    """Construct formatted context prompt from retrieved chunks using formal PromptContract."""
    if not retrieved_chunks:
        context_blocks = []
    else:
        context_blocks = []
        for idx, item in enumerate(retrieved_chunks, start=1):
            meta = item.metadata
            section_str = f" | Bölüm: {meta.section}" if meta.section else ""
            header = f"[Doc: {meta.filename}, P. {meta.page_number}{section_str}]"
            context_blocks.append(f"--- {header} ---\n{item.content}")

    return current_prompt_contract.format_user_prompt(query, context_blocks)

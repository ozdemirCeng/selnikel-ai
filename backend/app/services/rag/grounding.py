import re
from typing import List, Set, Tuple
from app.domain.rag import Citation, RetrievalResult


class CitationEngine:
    """Extracts, verifies, and maps citations from generated LLM text to retrieved chunks."""

    # Matches [Belge: filename.pdf, Sayfa: 2] or [doc-id:2] or [filename.pdf:2]
    CITATION_REGEX = re.compile(
        r"\[(?:(?:Belge|Doc|Kaynak):\s*)?([^,:\]]+?)(?:[:,\s]+(?:Sayfa|Page)?[:\s]*(\d+))?(?:,\s*(?:Bölüm|Section):\s*([^\]]+))?\]",
        re.IGNORECASE,
    )

    def extract_and_verify_citations(
        self,
        answer_text: str,
        retrieved_chunks: List[RetrievalResult],
    ) -> Tuple[List[Citation], List[str]]:
        """Parse inline citations, verify against retrieved chunks, and return structured citations."""
        citations: List[Citation] = []
        sources_used: Set[str] = set()

        # Map chunks by doc_id, filename and page for verification
        chunk_map = {
            (r.metadata.filename.lower(), r.metadata.page_number): r
            for r in retrieved_chunks
        }
        chunk_by_doc_id = {
            (r.metadata.document_id.lower(), r.metadata.page_number): r
            for r in retrieved_chunks
        }
        chunk_by_file = {r.metadata.filename.lower(): r for r in retrieved_chunks}
        chunk_by_id_only = {r.metadata.document_id.lower(): r for r in retrieved_chunks}

        matches = list(self.CITATION_REGEX.finditer(answer_text))

        for match in matches:
            identifier = match.group(1).strip()
            page_str = match.group(2)
            section = match.group(3).strip() if match.group(3) else None

            page_num = int(page_str) if page_str and page_str.isdigit() else 1
            sources_used.add(identifier)

            # Check if this exact (identifier, page) exists in retrieved chunks
            matched_chunk = (
                chunk_map.get((identifier.lower(), page_num))
                or chunk_by_doc_id.get((identifier.lower(), page_num))
                or chunk_by_file.get(identifier.lower())
                or chunk_by_id_only.get(identifier.lower())
            )

            if matched_chunk:
                doc_id = matched_chunk.metadata.document_id
                resolved_filename = matched_chunk.metadata.filename
                snippet = matched_chunk.content[:200] + "..." if len(matched_chunk.content) > 200 else matched_chunk.content
                score = matched_chunk.score
                real_page = matched_chunk.metadata.page_number
                real_section = matched_chunk.metadata.section or section
            else:
                doc_id = "unverified"
                resolved_filename = identifier
                snippet = f"Alıntı: {identifier}, Sayfa {page_num}"
                score = 0.5
                real_page = page_num
                real_section = section

            citation = Citation(
                document_id=doc_id,
                filename=resolved_filename,
                page_number=real_page,
                section=real_section,
                snippet=snippet,
                score=score,
            )

            # Avoid duplicates
            if not any(
                c.filename.lower() == citation.filename.lower()
                and c.page_number == citation.page_number
                for c in citations
            ):
                citations.append(citation)

        # If LLM didn't produce inline citations but answer is present and not a refusal:
        if not citations and retrieved_chunks and "bulunmamaktadır" not in answer_text.lower():
            # Build citations from top retrieved chunks
            for r in retrieved_chunks[:3]:
                sources_used.add(r.metadata.filename)
                citations.append(
                    Citation(
                        document_id=r.metadata.document_id,
                        filename=r.metadata.filename,
                        page_number=r.metadata.page_number,
                        section=r.metadata.section,
                        snippet=r.content[:200] + "...",
                        score=r.score,
                    )
                )

        return citations, sorted(list(sources_used))

    def is_refusal_response(self, answer_text: str) -> bool:
        """Check if generated response is an honest refusal due to missing evidence."""
        lower = answer_text.lower()
        refusal_phrases = [
            "bulunmamaktadır",
            "belirtilmemiştir",
            "yeterli bilgi yoktur",
            "dokümanlarda yer almamaktadır",
            "kaynaklarda bulunamadı",
            "bilgi yer almıyor",
        ]
        return any(phrase in lower for phrase in refusal_phrases)

    def extract_citations(self, answer_text: str, retrieved_chunks: List[RetrievalResult]) -> List[Citation]:
        """Convenience wrapper returning only the extracted citations list."""
        citations, _ = self.extract_and_verify_citations(answer_text, retrieved_chunks)
        return citations


# Default singleton instance
citation_engine = CitationEngine()


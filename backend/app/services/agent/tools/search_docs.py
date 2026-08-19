from typing import Any, Dict, Optional
from app.domain.agent import ToolDefinition, ToolParameter
from app.domain.rag import RetrievalFilter
from app.services.rag.engine import rag_engine


class SearchDocumentsTool:
    """Tool to search technical documents using deterministic hybrid retrieval and FlashRank."""

    @classmethod
    def get_definition(cls) -> ToolDefinition:
        return ToolDefinition(
            name="search_engineering_documents",
            description="Searches Selnikel technical documents (boilers, burners, fans, datasheets) and returns verified citations and extracted content.",
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="The technical search query or equipment model name (e.g. 'SB-100 steam capacity').",
                    required=True,
                ),
                ToolParameter(
                    name="department",
                    type="string",
                    description="Optional filter by department ('engineering', 'production', 'service', 'sales').",
                    required=False,
                ),
                ToolParameter(
                    name="top_k",
                    type="integer",
                    description="Number of relevant chunks to retrieve (default: 4).",
                    required=False,
                    default=4,
                ),
            ],
        )

    @classmethod
    async def execute(cls, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = arguments.get("query", "").strip()
        department = arguments.get("department")
        top_k = int(arguments.get("top_k", 4))

        if not query:
            return {"error": "Query cannot be empty."}

        filter_criteria = RetrievalFilter(department=department) if department else None
        output = await rag_engine.query(
            query_text=query,
            top_k=top_k,
            filter_criteria=filter_criteria,
        )

        return {
            "answer": output.answer,
            "citations": [c.model_dump() for c in output.citations],
            "sources_used": output.sources_used,
        }

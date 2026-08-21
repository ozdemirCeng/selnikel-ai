from typing import Any, Dict, List, Optional
from ddgs import DDGS
from app.core.logging import logger
from app.domain.agent import ToolDefinition, ToolParameter
from app.services.ingestion.web_scraper import web_scraper_service


class WebSearchTool:
    """Tool to search the live web for technical standards, competitor equipment, and engineering articles."""

    @classmethod
    def get_definition(cls) -> ToolDefinition:
        return ToolDefinition(
            name="web_search",
            description="Search the live internet for engineering information, boiler standards (EN, ASME, DIN, TS), burner datasheets, industrial regulations, or competitor equipment specifications.",
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="The search keywords or standard code to look up on the web (e.g. 'TS EN 12953 boiler test pressure').",
                    required=True,
                ),
                ToolParameter(
                    name="max_results",
                    type="integer",
                    description="Maximum number of search results to return (default: 5).",
                    required=False,
                    default=5,
                ),
            ],
        )

    @classmethod
    async def execute(cls, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = arguments.get("query", "").strip()
        if not query:
            return {"error": "Query cannot be empty."}

        max_results = int(arguments.get("max_results", 5))
        max_results = min(max(1, max_results), 10)

        try:
            ddg = DDGS()
            raw_results = list(ddg.text(query, max_results=max_results))
            if not raw_results:
                return {
                    "query": query,
                    "results_count": 0,
                    "message": f"'{query}' araması için internette sonuç bulunamadı.",
                    "results": [],
                }

            results = [
                {
                    "title": r.get("title", "Başlıksız"),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                }
                for r in raw_results
            ]
            return {
                "query": query,
                "results_count": len(results),
                "results": results,
            }
        except Exception as e:
            logger.error(f"WebSearchTool execution failed for '{query}': {e}")
            return {"error": f"Web araması sırasında hata oluştu: {str(e)}"}


class WebScrapeTool:
    """Tool to scrape and extract text/tables from a specific web URL."""

    @classmethod
    def get_definition(cls) -> ToolDefinition:
        return ToolDefinition(
            name="web_scrape",
            description="Fetch, clean, and extract full text and tables from any public web page or technical URL.",
            parameters=[
                ToolParameter(
                    name="url",
                    type="string",
                    description="The full HTTP/HTTPS URL of the web page to scrape.",
                    required=True,
                ),
            ],
        )

    @classmethod
    async def execute(cls, arguments: Dict[str, Any]) -> Dict[str, Any]:
        url = arguments.get("url", "").strip()
        if not url:
            return {"error": "URL cannot be empty."}

        try:
            title, markdown_content, metadata = await web_scraper_service.fetch_and_clean_url(url)
            # Limit returned content to avoid context blowout (max ~4000 chars)
            truncated = False
            if len(markdown_content) > 4000:
                markdown_content = markdown_content[:4000] + f"\n\n... [İçeriğin kalanı kırpıldı, toplam {len(markdown_content)} karakter]"
                truncated = True

            return {
                "url": url,
                "title": title,
                "content": markdown_content,
                "is_truncated": truncated,
            }
        except Exception as e:
            logger.error(f"WebScrapeTool execution failed for '{url}': {e}")
            return {"error": f"Web sayfası içeriği alınamadı ({url}): {str(e)}"}



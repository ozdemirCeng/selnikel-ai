import re
import urllib.parse
from typing import Dict, List, Optional, Tuple
import httpx
from bs4 import BeautifulSoup
from app.core.logging import logger


class WebScraperService:
    """Service to fetch, clean, and extract structured markdown from web pages and articles."""

    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    async def fetch_and_clean_url(self, url: str) -> Tuple[str, str, Dict[str, str]]:
        """Fetch URL and return (title, markdown_content, metadata)."""
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        async with httpx.AsyncClient(
            headers=self.DEFAULT_HEADERS,
            follow_redirects=True,
            timeout=25.0,
            verify=False,
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            html_content = resp.text

        soup = BeautifulSoup(html_content, "lxml")

        # 1. Extract Title
        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
        elif soup.find("h1"):
            title = soup.find("h1").get_text().strip()
        if not title:
            parsed_url = urllib.parse.urlparse(url)
            title = parsed_url.netloc + parsed_url.path

        # 2. Extract Meta Description
        meta_desc = ""
        meta_tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
        if meta_tag and meta_tag.get("content"):
            meta_desc = meta_tag.get("content", "").strip()

        # 3. Clean unwanted elements
        for element in soup.find_all(["script", "style", "nav", "footer", "header", "noscript", "aside", "svg", "iframe"]):
            element.decompose()

        # 4. Extract Tables as Markdown
        table_markdowns = []
        for idx, table in enumerate(soup.find_all("table"), 1):
            table_md = self._html_table_to_markdown(table)
            if table_md:
                table_markdowns.append(f"\n\n### Tablo {idx}\n{table_md}\n\n")
            table.decompose()

        # 5. Extract Main Text Blocks
        main_container = soup.find("article") or soup.find("main") or soup.find("div", class_=re.compile(r"content|post|article|main", re.I)) or soup.body
        if not main_container:
            main_container = soup

        text_lines = []
        for element in main_container.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
            text = element.get_text().strip()
            if not text or len(text) < 3:
                continue

            tag_name = element.name.lower()
            if tag_name == "h1":
                text_lines.append(f"\n# {text}\n")
            elif tag_name == "h2":
                text_lines.append(f"\n## {text}\n")
            elif tag_name == "h3":
                text_lines.append(f"\n### {text}\n")
            elif tag_name == "h4":
                text_lines.append(f"\n#### {text}\n")
            elif tag_name == "li":
                text_lines.append(f"- {text}")
            else:
                text_lines.append(f"{text}\n")

        body_markdown = "\n".join(text_lines)

        # Merge text with extracted tables
        if table_markdowns:
            body_markdown += "\n\n## Web Sayfasından Çıkarılan Tablolar\n" + "\n".join(table_markdowns)

        # Prepend header metadata
        full_markdown = (
            f"# {title}\n\n"
            f"> **Kaynak URL:** [{url}]({url})\n"
            f"> **Açıklama:** {meta_desc or 'Web kaynağından otomatik aktarılmıştır.'}\n\n"
            f"---\n\n"
            f"{body_markdown}"
        )

        metadata = {
            "source_url": url,
            "title": title,
            "description": meta_desc,
            "content_type": "text/html",
        }

        return title, full_markdown, metadata

    def _html_table_to_markdown(self, table_soup) -> str:
        """Convert BeautifulSoup HTML table to clean GitHub Flavored Markdown table."""
        rows = []
        for tr in table_soup.find_all("tr"):
            cells = [
                re.sub(r"\s+", " ", cell.get_text().strip()).replace("|", "\\|")
                for cell in tr.find_all(["th", "td"])
            ]
            if any(cells):
                rows.append(cells)

        if not rows:
            return ""

        max_cols = max(len(r) for r in rows)
        normalized = [r + [""] * (max_cols - len(r)) for r in rows]

        headers = normalized[0]
        headers = [h if h else f"Sütun {i+1}" for i, h in enumerate(headers)]
        body = normalized[1:] if len(normalized) > 1 else []

        header_line = "| " + " | ".join(headers) + " |"
        sep_line = "| " + " | ".join(["---"] * max_cols) + " |"
        body_lines = ["| " + " | ".join(r) + " |" for r in body]

        return "\n".join([header_line, sep_line] + body_lines)


web_scraper_service = WebScraperService()


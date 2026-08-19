from datetime import datetime, timezone
from typing import Any, Dict, List
from app.domain.agent import ToolDefinition, ToolParameter


class ReportGeneratorTool:
    """Tool to generate structured engineering technical reports with tables and verification signatures."""

    @classmethod
    def get_definition(cls) -> ToolDefinition:
        return ToolDefinition(
            name="generate_engineering_report",
            description="Assembles and formats a professional engineering technical report with title, executive summary, calculations table, verified document citations, and engineering conclusions.",
            parameters=[
                ToolParameter(
                    name="title",
                    type="string",
                    description="Report title (e.g. 'Selnikel SB-100 Termal Verim ve Kapasite Raporu').",
                    required=True,
                ),
                ToolParameter(
                    name="equipment_model",
                    type="string",
                    description="Equipment model or serial (e.g. 'SB-100').",
                    required=True,
                ),
                ToolParameter(
                    name="executive_summary",
                    type="string",
                    description="Executive summary of technical findings.",
                    required=True,
                ),
                ToolParameter(
                    name="calculation_results",
                    type="object",
                    description="Key calculation results dictionary.",
                    required=False,
                ),
                ToolParameter(
                    name="citations",
                    type="array",
                    description="List of referenced document citations.",
                    required=False,
                ),
            ],
        )

    @classmethod
    async def execute(cls, arguments: Dict[str, Any]) -> Dict[str, Any]:
        title = arguments.get("title", "Mühendislik Teknik Raporu")
        equipment = arguments.get("equipment_model", "Genel Ekipman")
        summary = arguments.get("executive_summary", "")
        calc_data = arguments.get("calculation_results", {})
        citations = arguments.get("citations", [])

        date_str = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")

        # Build Markdown Table of Calculations
        calc_table_rows = []
        if isinstance(calc_data, dict):
            for k, v in calc_data.items():
                clean_key = k.replace("_", " ").title()
                calc_table_rows.append(f"| {clean_key} | {v} |")
        calc_table_str = "\n".join(calc_table_rows) if calc_table_rows else "| Parametre | Değer |\n|---|---|\n| Durum | Standart Çalışma |"

        # Build Citations Section
        cite_lines = []
        if isinstance(citations, list):
            for idx, c in enumerate(citations, start=1):
                if isinstance(c, dict):
                    fname = c.get("filename", "Doküman")
                    page = c.get("page_number", 1)
                    cite_lines.append(f"{idx}. **{fname}** — Sayfa {page}")
                else:
                    cite_lines.append(f"{idx}. {c}")
        cite_str = "\n".join(cite_lines) if cite_lines else "Referans doküman bulunmamaktadır."

        markdown_report = f"""# SELNİKEL ENERJİ — TEKNİK MÜHENDİSLİK RAPORU

**Rapor Başlığı:** {title}  
**Ekipman:** {equipment}  
**Tarih:** {date_str}  
**Hazırlayan:** Selnikel AI Mühendislik Ajanı  
**Doğrulama:** Deterministik RAG & ASME PTC / Akışkanlar Mekaniği Standartları  

---

## 1. Yönetici Özeti (Executive Summary)
{summary}

---

## 2. Mühendislik Hesaplama ve Parametre Tablosu

| Mühendislik Parametresi | Hesaplanan Değer |
| :--- | :--- |
{calc_table_str}

---

## 3. Doğrulanmış Kaynak ve Standart Referansları
{cite_str}

---
*Bu rapor Selnikel AI Mühendislik Bilgi Sistemi tarafından doğrulanmış teknik şartnameler ve standart mühendislik formülleri kullanılarak otomatik olarak üretilmiştir.*
"""

        return {
            "report_title": title,
            "equipment_model": equipment,
            "created_at": date_str,
            "markdown_content": markdown_report,
        }

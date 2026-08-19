import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.services.reporting.excel_exporter import EngineeringExcelExporter
from app.services.reporting.word_exporter import EngineeringWordExporter
from app.services.reporting.powerpoint_exporter import EngineeringPowerPointExporter

AUTH_HEADERS = {"X-Dev-User": "engineer@selnikel.com.tr"}

SAMPLE_MARKDOWN = """# SB-100 Kazan Test Raporu
## 1. Parametre Tablosu
| Parametre | Nominal Değer | Birim |
|---|---|---|
| Buhar Kapasitesi | 1000 | kg/h |
| İşletme Basıncı | 16 | bar |
| Verim | 91.5 | % |

## 2. Açıklamalar
Sistem testi başarıyla tamamlanmıştır.
"""

def test_excel_exporter():
    excel_bytes = EngineeringExcelExporter.generate_excel(SAMPLE_MARKDOWN, title="SB-100 Test")
    assert isinstance(excel_bytes, bytes)
    assert len(excel_bytes) > 1000
    assert excel_bytes.startswith(b"PK\x03\x04")


def test_word_exporter():
    docx_bytes = EngineeringWordExporter.generate_docx(SAMPLE_MARKDOWN, title="SB-100 Test")
    assert isinstance(docx_bytes, bytes)
    assert len(docx_bytes) > 1000
    assert docx_bytes.startswith(b"PK\x03\x04")


def test_powerpoint_exporter():
    pptx_bytes = EngineeringPowerPointExporter.generate_pptx(SAMPLE_MARKDOWN, title="SB-100 Test")
    assert isinstance(pptx_bytes, bytes)
    assert len(pptx_bytes) > 1000
    assert pptx_bytes.startswith(b"PK\x03\x04")


@pytest.mark.asyncio
async def test_export_endpoints():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Excel Endpoint
        res_excel = await ac.post(
            "/api/v1/agent/report/excel",
            json={"markdown_content": SAMPLE_MARKDOWN, "title": "Test Excel"},
            headers=AUTH_HEADERS,
        )
        assert res_excel.status_code == 200
        assert "spreadsheetml" in res_excel.headers["content-type"]

        # Word Endpoint
        res_word = await ac.post(
            "/api/v1/agent/report/word",
            json={"markdown_content": SAMPLE_MARKDOWN, "title": "Test Word"},
            headers=AUTH_HEADERS,
        )
        assert res_word.status_code == 200
        assert "wordprocessingml" in res_word.headers["content-type"]

        # PowerPoint Endpoint
        res_pptx = await ac.post(
            "/api/v1/agent/report/powerpoint",
            json={"markdown_content": SAMPLE_MARKDOWN, "title": "Test PowerPoint"},
            headers=AUTH_HEADERS,
        )
        assert res_pptx.status_code == 200
        assert "presentationml" in res_pptx.headers["content-type"]

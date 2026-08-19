import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.services.reporting import (
    EngineeringExcelExporter,
    EngineeringPowerPointExporter,
    EngineeringWordExporter,
)

SAMPLE_MARKDOWN = """# SELNİKEL ENERJİ — TEST RAPORU
## 1. Yönetici Özeti
Bu bir test mühendislik raporu ve hesaplama çıktısıdır.

## 2. Hesaplama Parametreleri
| Parametre | Değer | Birim |
|---|---|---|
| Buhar Debisi | 1000 | kg/h |
| İşletme Basıncı | 16 | bar |
| Termal Verim | 91.5 | % |
| Doğal Gaz Tüketimi | 75.4 | Nm3/h |

## 3. Tavsiyeler ve Notlar
- Emniyet ventili yıllık periyodik bakım yapılmalıdır.
- Brülör hava ayarları kontrol edilmelidir.
"""


def test_excel_exporter():
    excel_bytes = EngineeringExcelExporter.generate_excel(SAMPLE_MARKDOWN, "Test Verileri")
    assert isinstance(excel_bytes, bytes)
    assert len(excel_bytes) > 500
    # ZIP/Office open XML header
    assert excel_bytes.startswith(b"PK\x03\x04")


def test_word_exporter():
    docx_bytes = EngineeringWordExporter.generate_docx(SAMPLE_MARKDOWN, "Test Raporu")
    assert isinstance(docx_bytes, bytes)
    assert len(docx_bytes) > 500
    assert docx_bytes.startswith(b"PK\x03\x04")


def test_powerpoint_exporter():
    pptx_bytes = EngineeringPowerPointExporter.generate_pptx(SAMPLE_MARKDOWN, "Test Sunumu")
    assert isinstance(pptx_bytes, bytes)
    assert len(pptx_bytes) > 500
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
        )
        assert res_excel.status_code == 200
        assert res_excel.content.startswith(b"PK\x03\x04")

        # Word Endpoint
        res_word = await ac.post(
            "/api/v1/agent/report/word",
            json={"markdown_content": SAMPLE_MARKDOWN, "title": "Test Word"},
        )
        assert res_word.status_code == 200
        assert res_word.content.startswith(b"PK\x03\x04")

        # PowerPoint Endpoint
        res_pptx = await ac.post(
            "/api/v1/agent/report/powerpoint",
            json={"markdown_content": SAMPLE_MARKDOWN, "title": "Test PPTX"},
        )
        assert res_pptx.status_code == 200
        assert res_pptx.content.startswith(b"PK\x03\x04")

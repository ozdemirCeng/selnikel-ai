import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.services.reporting.pdf_exporter import EngineeringPDFExporter


def test_pdf_exporter_generates_valid_pdf():
    markdown_content = """# SELNİKEL ENERJİ — TEST RAPORU
## 1. Yönetici Özeti
Bu bir test mühendislik raporudur.

## 2. Hesaplama Parametreleri
| Parametre | Değer |
|---|---|
| Buhar Debisi | 1000 kg/h |
| Termal Verim | %91.5 |

## 3. Kaynaklar
- SB-100 Teknik Şartnamesi (Sayfa 4)
"""
    pdf_bytes = EngineeringPDFExporter.generate_pdf(markdown_content, "Test Raporu")
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 500
    # PDF magic header verification
    assert pdf_bytes.startswith(b"%PDF-")


@pytest.mark.asyncio
async def test_pdf_export_endpoint():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/api/v1/agent/report/pdf",
            json={
                "markdown_content": "# Selnikel Raporu\n\nTest içeriği.",
                "title": "Selnikel Test Raporu",
            },
        )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-")

import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.services.reporting.pdf_exporter import EngineeringPDFExporter

AUTH_HEADERS = {"X-Dev-User": "engineer@selnikel.com.tr"}


def test_pdf_exporter_generates_valid_pdf():
    """Verify that EngineeringPDFExporter produces non-empty bytes starting with PDF magic header."""
    markdown_content = """# SB-100 Kazan Test Raporu
## 1. Genel Bilgiler
- **Model**: SB-100
- **Kapasite**: 1000 kg/h
- **İşletme Basıncı**: 16 bar

| Parametre | Değer | Birim |
|---|---|---|
| Termal Verim | 91.5 | % |
| Baca Gazı Sıcaklığı | 145 | °C |
"""
    pdf_bytes = EngineeringPDFExporter.generate_pdf(markdown_content, title="SB-100 Raporu")

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 500
    assert pdf_bytes.startswith(b"%PDF")


@pytest.mark.asyncio
async def test_pdf_export_endpoint():
    """Verify HTTP endpoint streaming of generated PDF."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/api/v1/agent/report/pdf",
            json={
                "markdown_content": "# Selnikel Rapor\nBu bir test raporudur.",
                "title": "Selnikel Test Raporu",
            },
            headers=AUTH_HEADERS,
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert len(response.content) > 500
        assert response.content.startswith(b"%PDF")

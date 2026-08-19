# Selnikel AI — Software Bill of Materials (SBOM.md)

> **Standard**: CycloneDX & SPDX Compatible Inventory  
> **Target**: Selnikel AI Industrial Engineering Platform  
> **Generation Date**: 2026-08-19  

---

## 1. Altyapı ve Çalışma Zamanı Bileşenleri

| Bileşen | Versiyon | Tür / Ekosistem | Lisans | Güvenlik Durumu |
| :--- | :--- | :--- | :--- | :--- |
| **Python** | `3.11.9` | Runtime Engine | PSF License | Sabitlenmiş |
| **Node.js** | `v25.2.1` | Frontend Runtime | MIT | Sabitlenmiş |
| **PostgreSQL** | `16-alpine` | Relational Database | PostgreSQL License | Resmi İmaj |
| **Qdrant** | `v1.11.0` | Vector Database | Apache 2.0 | Resmi İmaj |

---

## 2. Çekirdek Backend Bağımlılıkları (`backend/requirements-lock.txt`)

- **Web & API Framework**: `fastapi==0.141.1`, `uvicorn==0.41.0`, `starlette==0.52.1`, `pydantic==2.12.5`
- **Veritabanı & ORM**: `SQLAlchemy==2.0.52`, `asyncpg==0.31.0`, `aiosqlite==0.22.1`
- **Vektör Veritabanı İstemcisi**: `qdrant-client==1.17.0`
- **Doküman Ayrıştırma & OCR**: `docling==2.120.3`, `docling-core==2.91.0`, `pypdf==6.7.5`
- **Yeniden Sıralama (Reranker)**: `FlashRank==0.2.10`, `onnxruntime==1.23.2`
- **Gömme Modelleri & ML**: `torch==2.10.0`, `transformers==4.57.6`, `tokenizers==0.22.2`
- **Raporlama & Belge Üretimi**: `python-docx==1.2.0`, `python-pptx==1.0.2`, `openpyxl==3.1.5`, `reportlab==4.4.11`
- **Test Altyapısı**: `pytest==9.1.1`, `pytest-asyncio==1.4.0`, `Faker==40.36.0`

---

## 3. Çekirdek Frontend Bağımlılıkları (`frontend/package.json`)

- **Çerçeve & React**: `next==14.2.35`, `react==18.3.1`, `react-dom==18.3.1`
- **Stil & Tasarım**: `tailwindcss==3.4.1`, `postcss==8.4.38`, `lucide-react==0.378.0`
- **Markdown & Render**: `react-markdown==9.0.1`, `remark-gfm==4.0.0`
- **Tip Güvenliği**: `typescript==5.4.5`, `@types/node==20.12.7`, `@types/react==18.3.1`

---

## 4. Güvenlik ve Uyumluluk Notları
- Tüm Python paketleri `requirements-lock.txt` dosyası ile tam hash/sürüm bazında kilitlenmiştir.
- Tüm NPM paketleri `frontend/package-lock.json` ile kilitlenmiştir.
- Repoda hiçbir harici GPL-3 kısıtlayıcı lisanslı kütüphane bulunmamaktadır (Tümü MIT, Apache-2.0, BSD veya PSF uyumludur).

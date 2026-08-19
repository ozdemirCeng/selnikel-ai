# Selnikel AI — Mevcut Durum Denetim Raporu (CURRENT_STATE_AUDIT.md)

> **Tarih**: 2026-08-19  
> **Denetçi**: Principal Product Architect & Security/RAG Architect  
> **Kapsam**: `C:\Users\Diley\dev\workspace\selnikel-ai`  
> **Standart**: Sıfır Varsayım, %100 Kanıtlı Bulgu Standardı

---

## 1. Yönetici Özeti

Mevcut Selnikel AI prototipi üzerinde gerçekleştirilen kapsamlı statik kod analizi, bağımlılık denetimi, güvenlik taraması, canlı ortam testleri ve mimari inceleme neticesinde; temel RAG bileşenlerinin (parser, chunker, hybrid retriever, reranker, export motorları) birim test seviyesinde çalıştığı, ancak **kurumsal endüstriyel üretim standardına geçiş için kritik yapısal, güvenlik ve veri modeli eksikliklerinin bulunduğu** tespit edilmiştir.

### Temel Durum Özeti (Scorecard)
| Alan | Durum | Risk Seviyesi | Ana Tespit |
| :--- | :--- | :--- | :--- |
| **Git & Secrets** | ✅ GÜVENLİ | Düşük | `.gitignore` yapılandırıldı, repoda hiçbir API anahtarı veya `.env` sızıntısı yok. |
| **Runtime & Sürümler** | ⚠️ KISMEN UYUMLU | Orta | Host Python `3.13.14`, venv Python `3.11.9`, Node `v25.2.1`. Docker Desktop kapalı. |
| **Veritabanı & Vektör DB** | ❌ EKSİK/MOCK | Yüksek | PostgreSQL ve Qdrant Docker konteynerleri kapalı; testler in-memory/mock ile geçiyor. |
| **Birim Testleri** | ✅ GEÇİYOR | Düşük | `pytest` 47/47 test PASS (63.62s). |
| **Frontend Derleme** | ✅ DERLENİYOR | Düşük | `npm run build` 0 hata ile derlendi; 4 statik sayfa üretildi. |
| **Veri Modeli (Schema)** | ❌ YETERSİZ | Kritik | Doküman revizyonu, onay akışı, ekipman bağı, ACL, Element hiyerarşisi eksik. |
| **Kimlik & Yetkilendirme** | ❌ YOK | Kritik | API endpoint'lerinde authentication ve authorization (RBAC/ABAC) bulunmuyor. |
| **RAG Değerlendirme Seti** | ⚠️ SENTETİK | Yüksek | Sadece 10 adet sentetik test sorusu mevcut; 200+ endüstriyel vaka seti henüz yok. |
| **UI Marka & Fazlalıklar** | ⚠️ TEMİZLİK GEREKİYOR | Orta | Gemini/NotebookLM kalıntıları, sahte/ikincil araçlar (video, slayt vb.) arayüzde yer alıyor. |

---

## 2. Kanıtlı Teknik Bulgular Tablosu

### 2.1 Git, Secrets ve Çevresel Değişkenler
- **Bulgu**: Repoda gerçek `.env` dosyası takibi bulunmamaktadır. Yalnızca `.env.example`, `backend/.env.example` ve `frontend/.env.example` takip edilmektedir.
- **Kanıt**: 
  ```powershell
  git ls-files | Select-String "\.env"
  # Çıktı: .env.example, backend/.env.example, frontend/.env.example
  ```
- **Durum**: **PASS (Güvenli)**.

---

### 2.2 Çalışma Zamanı ve Paket Bağımlılıkları
- **Bulgu**:
  - Host Python: `Python 3.13.14`
  - Backend Sanal Ortam: `Python 3.11.9` (`backend/.venv`)
  - Node.js: `v25.2.1`, npm: `11.6.2`
  - `frontend/package-lock.json` mevcut ve kilitli.
  - `backend/pyproject.toml` mevcut ancak `poetry.lock` veya `pip-compile` lock dosyası bulunmamakta, paketler `requirements.txt` / loose dependency şeklinde kurulmuştur.
- **Kanıt**:
  ```powershell
  python --version -> Python 3.13.14
  .\backend\.venv\Scripts\python.exe --version -> Python 3.11.9
  node --version -> v25.2.1
  ```
- **Durum**: **UYARI (Backend için deterministik lockfile şart)**.

---

### 2.3 Docker ve Altyapı Servisleri (PostgreSQL & Qdrant)
- **Bulgu**: Docker servisi çalışmadığı için yerel `localhost:5432` PostgreSQL ve `localhost:6333` Qdrant servislerine erişim sağlanamamaktadır.
- **Kanıt**:
  ```text
  docker ps -> failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine
  asyncpg.connect() -> ConnectionRefusedError: [WinError 1225] Uzaktaki bilgisayar ağ bağlantısını reddetti
  ```
- **Etki**: Kod tabanında `app/infrastructure/qdrant.py` ve `app/db/session.py` fallback mekanizmalarıyla çalışsa da gerçek kurumsal PostgreSQL ve Qdrant entegrasyonu canlı Docker ayağa kalkmadan E2E test edilememektedir.
- **Durum**: **BAŞARISIZ (Altyapı ayağa kaldırılmalı)**.

---

### 2.4 Test Paketi ve Kod Kapsamı
- **Bulgu**: `backend/tests/` altındaki 47 testin tamamı başarıyla geçmektedir.
- **Kanıt**:
  ```text
  ================== 47 passed, 2 warnings in 63.62s (0:01:03) ==================
  - test_agent_api.py (4 passed)
  - test_agent_tools.py (4 passed)
  - test_chunker.py (2 passed)
  - test_config.py (1 passed)
  - test_document_api.py (4 passed)
  - test_embedding.py (2 passed)
  - test_evaluation_benchmark.py (2 passed)
  - test_grounding.py (4 passed)
  - test_health.py (2 passed)
  - test_hybrid_retriever.py (2 passed)
  - test_ingestion_pipeline.py (2 passed)
  - test_multiformat_export.py (4 passed)
  - test_parser.py (4 passed)
  - test_pdf_export.py (2 passed)
  - test_rag_api.py (3 passed)
  - test_rag_engine.py (2 passed)
  - test_reranker.py (3 passed)
  ```
- **Uyarılar**:
  - `StarletteDeprecationWarning: 'HTTP_422_UNPROCESSABLE_ENTITY' is deprecated`
  - `qdrant_client: UserWarning: Failed to obtain server version`
- **Durum**: **PASS (Fonksiyonel birim mantığı doğrulanmış)**.

---

### 2.5 Frontend Derleme & Varlık Durumu
- **Bulgu**: Next.js 14 derlemesi `0 hata` ile tamamlanmakta ve port `3005` üzerinde `HTTP 200` vermektedir.
- **Kanıt**:
  ```text
  Route (app)                              Size     First Load JS
  ┌ ○ /                                    68.8 kB         156 kB
  └ ○ /_not-found                          873 B          88.1 kB
  + First Load JS shared by all            87.2 kB
  ✓ Ready in 402ms on http://localhost:3005
  Status: 200 OK
  ```
- **Durum**: **PASS**.

---

### 2.6 Veri Modeli ve Sözleşme Eksiklikleri
- **Bulgu**: Mevcut veritabanı modelleri (`backend/app/db/models.py`) yalnızca `DocumentModel`, `DocumentChunkModel` ve `QueryLogModel` içermektedir:
  1. `DocumentRevision` tablosu yoktur. Revizyon takibi `version` integer alanı ile kısıtlıdır; revizyon onaylayan (`approved_by`), geçerlilik tarihi (`effective_at`), yürürlükten kalkan revizyon (`supersedes_revision_id`) bulunmamaktadır.
  2. `Equipment` (Kazan, Brülör, Fan vb.) tablosu ve doküman-ekipman çoka-çok ilişki tablosu bulunmamaktadır.
  3. `DocumentElement` tablosu yoktur. Dokümanlar hiyerarşik yapısal öğelere (bölüm, tablo, formül, uyarı, prosedür adımı) değil, düz chunk dizilerine bölünmektedir.
  4. `User`, `Role`, `Permission`, `AuditEvent`, `ServiceCase`, `IngestionJob` tabloları veritabanında mevcut değildir.
- **Durum**: **KRİTİK MİMARİ AÇIK (Yeniden Yapılandırma Gerektirir)**.

---

### 2.7 Güvenlik, Kimlik ve Yetkilendirme (Auth/ACL)
- **Bulgu**:
  - Hiçbir API endpoint'inde JWT/OIDC veya oturum kontrolü yoktur.
  - Departman bazlı belge izolasyonu (`department_id`) sadece filtrelenebilir bir string etiketten ibarettir; kullanıcının erişim yetkisi doğrulanmamaktadır.
  - Qdrant vektör sorgularında güvenlik/ACL filtresi zorunlu kılınmamıştır.
  - Yüklenen dosyalarda malware taraması (ClamAV) veya magic byte MIME type doğrulaması bulunmamaktadır.
- **Durum**: **KRİTİK GÜVENLİK AÇIĞI (P0 Düzeltme Şart)**.

---

### 2.8 RAG Değerlendirme Seti ve Ölçüm Kapsamı
- **Bulgu**: `backend/tests/evaluation/questions.json` dosyası yalnızca 10 adet örnek soru içermektedir.
  - Recall@k, nDCG, citation precision, faithfulness, abstention accuracy metrikleri 200+ soruluk gerçek endüstriyel veri seti üzerinde otomatik periyodik ölçüme bağlı değildir.
  - Testlerde "%100 doğruluk" iddiası yer almaktadır; bu durum gerçek endüstriyel dağılımı yansıtmamaktadır.
- **Durum**: **YETERSİZ ÖLÇÜM (200+ Vaka Benchmark Seti Tasarlanmalı)**.

---

### 2.9 Arayüz (UI/UX) ve Ürün Dışı Kalıntılar
- **Bulgu**:
  - `NotebookLMWorkspace.tsx` ve diğer bileşenlerde "NotebookLM", "Gemini" marka terimleri ve ikincil araçlar (Sesli Özet, Videolu Özet, Slayt .pptx vb.) mevcuttur.
  - Monolitik bileşenler (`NotebookLMWorkspace.tsx` 808 satır) domain modüllerine bölünmemiştir.
  - Bazı butonlarda doğrudan `alert()` çağrıları bulunmaktadır.
- **Durum**: **KAPSAM DIŞI UNSURLAR KALDIRILMALI**.

---

## 3. Denetim Sonuç Matrisi

| Madde No | Denetim Kriteri | Mevcut Durum | Hedef Standart | Eylem |
| :--- | :--- | :--- | :--- | :--- |
| **AUD-01** | Git Temizliği & Sırlar | ✅ PASS | Zero secret | Korunacak |
| **AUD-02** | Deterministik Ortam | ⚠️ EKSİK | Lockfile + Docker Compose | P0'da `poetry.lock`/`pip-tools` eklenecek |
| **AUD-03** | Canlı Veritabanı | ❌ FAIL | PostgreSQL 16 + Qdrant Canlı | P0'da Docker servisleri ayağa kaldırılacak |
| **AUD-04** | Domain Veri Şeması | ❌ FAIL | 14 Zorunlu Varlık | P0'da Alembic migration ile eklenecek |
| **AUD-05** | Auth & ACL | ❌ FAIL | OIDC/JWT + RBAC + Qdrant ACL | P0'da Auth middleware yazılacak |
| **AUD-06** | Asenkron Ingestion | ❌ FAIL | Job state machine + Worker | P0'da Background Ingestion Job eklenecek |
| **AUD-07** | RAG Benchmark (200+) | ⚠️ EKSİK | 200+ Soru Seti + Ragas/TruLens | P1'de endüstriyel dataset oluşturulacak |
| **AUD-08** | Selnikel Tasarım Dili | ⚠️ EKSİK | Özgün Endüstriyel İş İstasyonu | P1'de modüler FSD mimarisine geçilecek |

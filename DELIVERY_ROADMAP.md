# Selnikel AI — Teslimat Yol Haritası (DELIVERY_ROADMAP.md)

> **Yönetişim Kuralı**: P0 tamamlanmadan P1'e, P1 tamamlanmadan P2'ye kesinlikle geçilmez. Her aşama bağımsız test, review ve kanıt dosyasıyla onaylanır. Big-bang refactor yasaktır; tüm veri modelleri ve özellikler ayrık domain dilimleri halinde uygulanır.

---

## 1. Teslimat Aşamaları Genel Bakışı

```text
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ FAZ P0: Temel Güvenlik, Altyapı, Kimlik ve Çekirdek Domain Dilimleri (Sıralı 9 Görev)                  │
│ [P0-00] ──> [P0-01] ──> [P0-02] ──> [P0-03] ──> [P0-04] ──> [P0-05] ──> [P0-06] ──> [P0-07] ──> [P0-08] │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                                    │
                                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ FAZ P1: 200+ Sektörel Benchmark, İleri Tablo Çıkarımı ve Revizyon Fark Motoru                           │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                                    │
                                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ FAZ P2: Saha Servis Vakaları, Başmühendis Onay Bankası ve İleri Karar Desteği                           │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Faz P0: Güvenlik, Altyapı ve Domain Dilimleri Durum Matrisi

| Faz Kodu | Modül / Dilim | Denetim Durumu | Doğrulanan Güvenlik / İşlevsellik |
| :--- | :--- | :---: | :--- |
| **P0-00** | **Baseline, Güvenlik & CI** | `VERIFIED` | • Gitleaks CI blocking gate ve non-zero exit scanner.<br>• CycloneDX 1.5 JSON makine tarafından okunabilir SBOM (`sbom-backend.cdx.json`, `sbom-frontend.cdx.json`, `license-report.json`).<br>• Next.js canlı HTTP asset chunk smoke testi. |
| **P0-01** | **ADR Karar Paketi** | `VERIFIED` | • ADR-011'den ADR-019'a 9 zorunlu mimari karar `DECISIONS.md`'de kayıtlı. |
| **P0-02** | **Alembic Migrasyon** | `VERIFIED` | • 5 adet revizyon dosyası (`001` - `005`).<br>• Canlı `upgrade head -> downgrade base -> upgrade head` iki yönlü döngü testi PASS. |
| **P0-03** | **Kimlik & Yetkilendirme** | `VERIFIED` | • Kimliksiz istekler için katı **401 Unauthorized** (arka kapı / varsayılan fallback kapatıldı).<br>• Tüm hassas endpoint'lere (`/documents`, `/rag/*`, `/agent/*`) RBAC & ABAC dependency'leri bağlandı. |
| **P0-04** | **Belge ACL & Revizyon** | `FOUNDATION` | • `DocumentRevision`, `Equipment` modelleri ve `RevisionService` (tek aktif onaylı revizyon ve supersedes zinciri). |
| **P0-05** | **DocumentElement & Vektör** | `FOUNDATION` | • Hiyerarşik `DocumentElement` modelleri (tablo, formül, uyarı adımı) ve BoundingBox şeması. |
| **P0-06** | **Asenkron Ingestion Kuyruğu**| `FOUNDATION` | • `IngestionJob` durum geçiş doğrulayıcısı (geçersiz atlamalar engellenir).<br>• PostgreSQL `SELECT FOR UPDATE SKIP LOCKED` kuyruk reposu (`PostgresIngestionQueue`). |
| **P0-07** | **Hibrit Retrieval & ACL** | `VERIFIED` | • Qdrant upsert payload'una ACL alanları (`allowed_departments`, `equipment_ids`, `classification`) eklendi.<br>• 3 Katmanlı ACL (Postgres + Qdrant + Answer Provenance) ve Cache izolasyon testleri PASS. |
| **P0-08** | **RAG Değerlendirme & Metrik**| `FOUNDATION` | • Matematiksel metrik kütüphanesi (`Recall@5`, `nDCG@5`, `Faithfulness`, `Abstention`, `Safety-Critical`). |

---

## 3. P0 Kabul Kriterleri Doğrulama Listesi

- [x] Temiz Git geçmişi ve doğrulanmış secret scan (Gitleaks + Python regex/entropy scanner, exit 0).
- [x] Deterministik lockfile (`requirements-lock.txt`) ve makine tarafından okunabilir CycloneDX SBOM JSON dosyaları.
- [x] GitHub Actions CI pipeline'ı yapılandırıldı (`.github/workflows/ci.yml`).
- [x] Canlı veritabanında Alembic upgrade / downgrade / re-upgrade çevrim testi PASS.
- [x] 78 backend testi %100 PASS (Authentication 401/403, RBAC, ABAC, Ingestion State, Qdrant ACL, RAG streaming, Export formatları).
- [x] Frontend prod build ve tüm statik CSS/JS bundle'ları için canlı HTTP 200 chunk testi PASS.
- [x] 3 Katmanlı ACL izolasyonu ve yetkisiz sorgu engelleme testleri PASS.


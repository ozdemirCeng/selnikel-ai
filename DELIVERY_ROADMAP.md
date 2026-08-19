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

## 2. Faz P0: Temel Güvenlik, Altyapı ve Domain Dilimleri

### P0-00 — Baseline, Güvenlik ve CI Altyapısı
- [ ] Git geçmişinin tamamında regex/entropi tabanlı secret taraması yapılması.
- [ ] Python ve Node.js bağımlılıklarının deterministik lockfile (`requirements-lock.txt` / `package-lock.json`) ile sabitlenmesi.
- [ ] SBOM (Software Bill of Materials) üretilmesi.
- [ ] GitHub Actions CI workflow'unun (`.github/workflows/ci.yml`) kurulması (Test, Lint, Security Scan).
- [ ] Derleme sonrası Next.js CSS/JS asset'leri ve fontları için HTTP 200 smoke test harness'ının eklenmesi.
- [ ] PostgreSQL ve Qdrant entegrasyon testlerinin CI harness'ına bağlanması.

### P0-01 — Mimari Karar Kayıtları (ADR Paketi)
- [ ] `ADR-011`: OIDC Akış Modeli (SPA PKCE vs Backend-for-Frontend / HttpOnly Cookie).
- [ ] `ADR-012`: Asenkron İş Kuyruğu (PostgreSQL `SKIP LOCKED` vs Harici Broker).
- [ ] `ADR-013`: Güvenli Dosya Depolama ve Malware Tarama Stratejisi.
- [ ] `ADR-014`: 3 Katmanlı ACL Mimarisi (PostgreSQL + Qdrant + Answer Provenance) ve Cache İzolasyonu.
- [ ] `ADR-015`: Üç Ayrı Dağıtım Profili (`cloud-enabled`, `local-private`, `air-gapped`).
- [ ] `ADR-016`: Soft Delete, Retention ve Audit Değiştirilemezlik Standardı.

### P0-02 — Alembic Migrasyon Altyapısı
- [ ] Alembic ortamının `backend/alembic/` altına kurulması.
- [ ] Mevcut `DocumentModel`, `DocumentChunkModel` ve `QueryLogModel` için baseline migrasyon (`001_baseline.py`).
- [ ] Boş veritabanı upgrade testi, mevcut veritabanı upgrade testi ve downgrade/rollback testlerinin yazılması.
- [ ] Yıkıcı (destructive) migrasyon çalıştırmayı engelleyen güvenlik kuralının eklenmesi.

### P0-03 — Kimlik ve Organizasyon Çekirdek Dilimi (Identity Slice)
- [ ] `backend/app/domain/identity/` ve `organization/` modüllerinin oluşturulması.
- [ ] `users`, `roles`, `permissions`, `user_roles`, `departments`, `department_memberships` tablolarının Alembic ile eklenmesi.
- [ ] OIDC token doğrulama modülü ve `get_current_user` FastAPI dependency'si.
- [ ] RBAC yetki kontrol mekanizması (`require_permission("document.read")`).
- [ ] Giriş ve yetki reddi durumlarının `audit_events` tablosuna loglanması.
- [ ] Kimlik doğrulama E2E testleri.

### P0-04 — Belge ACL ve Revizyon Dilimi (Document & Revision Slice)
- [ ] `backend/app/domain/documents/` ve `equipment/` modüllerinin oluşturulması.
- [ ] `documents`, `document_revisions`, `document_acl`, `equipment`, `document_equipment` tablolarının eklenmesi.
- [ ] Mevcut belgelerin "Rev. 01 / Onaylı" olarak `document_revisions` tablosuna backfill edilmesi.
- [ ] Departman bazlı belge erişim kısıtlamasının (ABAC) servis seviyesinde test edilmesi.

### P0-05 — DocumentElement ve Vektör İndeks Dilimi (Element & Vector Slice)
- [ ] `backend/app/domain/retrieval/` altında `DocumentElement` ve `RetrievalChunk` modelleri.
- [ ] `document_elements` tablosunun oluşturulması (hiyerarşik bölüm, tablo, formül, uyarı adımları).
- [ ] Qdrant `selnikel_docs_v2` gölge koleksiyonunun açılması (ACL ve revizyon yükü ile).
- [ ] Veri sayısı/hash doğrulama testi ve alias yönlendirmesi.

### P0-06 — Asenkron Ingestion Kuyruğu (PostgreSQL Job Worker Slice)
- [ ] `ingestion_jobs` tablosu ve PostgreSQL `SELECT ... FOR UPDATE SKIP LOCKED` worker prosesi.
- [ ] Lease, heartbeat, exponential backoff, retry, cancel ve dead-letter durumları.
- [ ] Magic-byte MIME type kontrolü ve 50 MB dosya boyutu sınırı.
- [ ] SHA-256 idempotency kontrolü ile mükerrer dosya yüklemenin engellenmesi.

### P0-07 — Grounded Answer ve 3 Katmanlı Kanıt Doğrulama (Answer Slice)
- [ ] `backend/app/domain/answers/` altında `Query`, `Evidence` ve `Answer` modelleri.
- [ ] 3 Katmanlı ACL kontrolü: (1) PostgreSQL sorgusu, (2) Qdrant payload filtresi, (3) Citation/Provenance katmanı.
- [ ] Yetkisiz kaynakların cevap metninden ve alıntılardan katı izolasyonu.
- [ ] Yetersiz kanıt durumunda zorunlu refusal (`abstained: true`) kuralı.

### P0-08 — Selnikel UI Dönüşümü (Frontend Slice)
- [ ] Arayüzden tüm Gemini, NotebookLM isimlerinin ve sahte `alert()` eylemlerinin temizlenmesi.
- [ ] Selnikel kurumsal tasarım belirteçlerinin (renkler, tipografi, tabular numerals) uygulanması.
- [ ] Gerçek kurumsal navigasyon: `Ekipmanlar`, `Belgeler`, `Teknik Arama`, `Yönetim`. (Servis Vakaları ve Onaylı Cevaplar arka plan modelleri tamamlanana kadar sahte ekran olarak eklenmez).
- [ ] Yetkilendirme, boş durum, yükleme ve hata ekranlarının bağlanması.

---

## 3. P0 Kabul Kriterleri (P0 Gate Sign-off)

- [x] Temiz Git geçmişi ve doğrulanmış secret scan (Gitleaks / entropy scan PASS).
- [ ] Deterministik lockfile ve SBOM mevcut.
- [ ] GitHub Actions CI pipeline'ı yeşil.
- [ ] PostgreSQL ve Qdrant entegrasyon testleri geçiyor.
- [ ] 47+ backend testi ve yeni domain testleri %100 PASS.
- [ ] Frontend build 0 hata ve HTTP asset smoke testleri PASS (200 OK).
- [ ] Yetkisiz kullanıcı Ar-Ge dokümanını Qdrant'tan, DB'den ve cevap alıntılarından kesinlikle çekemiyor.
- [ ] Asenkron Ingestion Worker job durumlarını hatasız ilerletiyor.
- [ ] Arayüz tamamen Selnikel kurumsal kimliğinde ve sahte aksiyonlardan arındırılmış.

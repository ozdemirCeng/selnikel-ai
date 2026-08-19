# Selnikel AI — Teslimat Yol Haritası (DELIVERY_ROADMAP.md)

> **Yönetişim Kuralı**: P0 tamamlanmadan P1'e, P1 tamamlanmadan P2'ye kesinlikle geçilmez. Her aşama bağımsız test ve kanıt dosyasıyla onaylanır.

---

## 1. Teslimat Aşamaları ve Öncelik Hiyerarşisi

```text
[P0: Temel Güvenlik & Kurumsal Altyapı] ──> [P1: Revizyon Bilinci & RAG Kalitesi] ──> [P2: İleri Servis & Otomasyon]
```

---

## 2. Faz P0: Temel Güvenlik, Veri Modeli ve Altyapı (Blocker - Zorunlu)

### P0 Görev Listesi:
1. **TASK-P0-01: Git, Çevresel Değişkenler ve Secret Temizliği Doğrulaması**
   - `.gitignore` kontrolü, sıfır secret doğrulaması.
2. **TASK-P0-02: PostgreSQL 16 & Qdrant Canlı Sağlık ve Docker Doğrulaması**
   - Tek komutla ayağa kalkan Docker Compose yapılandırması ve health check probe'ları.
3. **TASK-P0-03: 14 Temel Kurumsal Domain Modeli & Alembic Migrasyonları**
   - `User`, `Role`, `Equipment`, `Document`, `DocumentRevision`, `DocumentElement`, `AuditEvent` tablolarının oluşturulması.
4. **TASK-P0-04: JWT / OIDC Kimlik Doğrulama ve Rol Bazlı Yetkilendirme (RBAC/ABAC)**
   - API middleware'i, departman bazlı belge erişim kısıtlaması, Qdrant ACL filtreleme enjeksiyonu.
5. **TASK-P0-05: Asenkron Ingestion Job Yaşam Döngüsü & Magic Byte Doğrulaması**
   - `IngestionJob` durumu (`queued` $\rightarrow$ `parsing` $\rightarrow$ `indexing`), malware ve MIME doğrulaması.
6. **TASK-P0-06: Frontend Marka Temizliği & Sahte Aksiyonların Kaldırılması**
   - "Gemini", "NotebookLM" ve `alert()` kalıntılarının temizlenmesi, Selnikel kurumsal başlığı ve 6 ana navigasyon sekmesinin bağlanması.
7. **TASK-P0-07: E2E Entegrasyon Testi & P0 Kabul Kapısı İmzası**
   - `Upload` $\rightarrow$ `Ingest` $\rightarrow$ `ACL-Protected RAG Query` akışının %100 test edilmesi.

### P0 Kabul Kriterleri (Çıkış Kapısı):
- [ ] Git ağacı temiz, sıfır secret.
- [ ] Tek komutla (`docker-compose up`) PostgreSQL ve Qdrant ayağa kalkıyor.
- [ ] Backend testleri 47+ test ile %100 PASS.
- [ ] Frontend derlemesi (`npm run build`) 0 hata.
- [ ] Yetkisiz kullanıcı Ar-Ge dokümanına kesinlikle erişemiyor (ACL doğrulanmış).
- [ ] Sahte UI butonları ve NotebookLM marka kalıntıları arayüzden arındırılmış.

---

## 3. Faz P1: Belge Revizyonları, 200+ Benchmark ve Arama Doğruluğu

### P1 Görev Listesi:
1. **TASK-P1-01: İki Revizyon Arası Değişiklik Karşılaştırma Motoru (Revision Diff Engine)**
   - İki teknik şartname revizyonu arasındaki parametre ve tablo değişikliklerini yan yana sunma.
2. **TASK-P1-02: 200+ Soruluk Sektörel Değerlendirme Veri Seti & Ragas Ölçüm Hattı**
   - `questions_v1.json` veri seti ile Recall@5, nDCG, Faithfulness, Citation Precision ve Safety-Critical hata oranı ölçümü.
3. **TASK-P1-03: Gelişmiş Tablo ve Formül Çıkarımı (Structured Content Preservation)**
   - Çok sütunlu teknik veri föylerinin hücre bazlı doğrulanabilir koordinatlarla kaydedilmesi.
4. **TASK-P1-04: Selnikel Endüstriyel Tasarım Sistemi (FSD Mimarisi)**
   - Yüksek yoğunluklu teknik tablo arayüzü, tabular numerals, onaylı/taslak/obsolete renk rozetleri.

---

## 4. Faz P2: Servis Vakaları ve İleri Mühendislik Karar Desteği

### P2 Görev Listesi:
1. **TASK-P2-01: Saha Servis Vakaları & Arıza Kodu Eşleme Motoru (Service Case Matcher)**
   - Brülör arıza kodları ve geçmiş kazan bakım kayıtları üzerinde vektörel benzerlik araması.
2. **TASK-P2-02: Başmühendis Onay Akışı & Resmi Cevap Bankası (Approved Answers Bank)**
   - AI taslağının başmühendis tarafından incelenip onaylanması ve kalıcı olarak damgalanması.
3. **TASK-P2-03: Otomatik Denetim İzi Raporlama & Yedekleme Otomasyonu**
   - ISO ve CE denetimleri için erişim loglarının şifreli dışa aktarımı.

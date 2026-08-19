# Selnikel AI — Risk Kütüğü ve Azaltma Planı (RISK_REGISTER.md)

> **Risk Yönetim Standardı**: Olasılık (1-5), Etki (1-5), Risk Skoru ($O \times E$), Sorumlu Rol ve Önleyici Eylem Planı.

---

## 1. Risk Matrisi ve Değerlendirme Tablosu

| Risk ID | Risk Tanımı | Kategori | O | E | Skor | Önleyici Eylem & Azaltma Stratejisi | Sorumlu |
| :--- | :--- | :--- | :---: | :---: | :---: | :--- | :--- |
| **RSK-01** | **Eski Revizyon Karışıklığı**: RAG motorunun güncel olmayan bir şartnamedeki eski basınç/sıcaklık değerini güncelmiş gibi vermesi. | Mühendislik Güvenliği | 4 | 5 | **20 (Kritik)** | `revision_policy: approved_latest` varsayılan kuralı. Yürürlükten kalkan revizyonlarda büyük sarı uyarı ve kanıtlarda revizyon kodu zorunluluğu. | `RAG-01` / `ARC-01` |
| **RSK-02** | **Yetkisiz Belge Sızıntısı**: İmalat veya servis personelinin Ar-Ge gizli patent çizimlerine veya maliyet tablolarına erişebilmesi. | Bilgi Güvenliği | 3 | 5 | **15 (Yüksek)** | Katı ABAC filtrelerinin hem API katmanında hem de doğrudan Qdrant vektör yükü seviyesinde zorunlu kılınması. | `BE-01` / `QA-02` |
| **RSK-03** | **Emniyet Parametresi Halüsinasyonu**: Emniyet ventili veya aşırı sıcaklık limitinde LLM'in uydurma sayı üretmesi. | Ürün Güvenliği | 2 | 5 | **10 (Yüksek)** | Kaynaksız cevap vermeyi katı şekilde engelleyen Grounding Engine ve regex tabanlı sayısal alıntı doğrulayıcı. | `RAG-01` / `RAG-02` |
| **RSK-04** | **OCR ve Tablo Bozulması**: Taranmış eski kazan PDF'lerindeki karmaşık çok sütunlu tabloların Docling tarafından yanlış okunması. | Veri Bütünlüğü | 4 | 3 | **12 (Yüksek)** | Docling tablo tanıma + OCR fallback hattı ve `structured_content` JSON formatında hücre doğrulama kontrolü. | `RAG-01` |
| **RSK-05** | **Altyapı Kesintisi / Docker Çökmesi**: Yerel PostgreSQL veya Qdrant servisinin bellek taşması veya Docker arızasıyla durması. | Operasyonel | 3 | 4 | **12 (Yüksek)** | Docker restart policy (`always`), veritabanı bağlantı havuzu (`pool_pre_ping=True`) ve otomatik sağlık probları. | `BE-01` |
| **RSK-06** | **Dış LLM Veri İhlali**: Hassas kurumsal şartnamelerin yetkisiz olarak harici bulut API'lerine (OpenAI) gönderilmesi. | Yasal & Gizlilik | 2 | 5 | **10 (Yüksek)** | `classification: confidential/restricted` belgelerin yalnızca yerel ağda çalışan Air-Gapped Ollama modeline yönlendirilmesi. | `ARC-01` |
| **RSK-07** | **Altın Cevap Etiketleme Eksikliği**: 200+ soruluk benchmark için başmühendislerin vakit ayıramaması ve sentetik veriye bağımlılık. | Kalite & Süreç | 4 | 2 | **8 (Orta)** | Ar-Ge ve Servis şefleriyle haftalık 1 saatlik etiketleme oturumları ve geçmiş onaylı servis raporlarından veri derleme. | `MGR-01` |
| **RSK-08** | **Performans & Bellek Darboğazı**: Büyük 200 sayfalık teknik el kitaplarının ayrıştırılması esnasında sunucu RAM'inin tükenmesi. | Performans | 3 | 3 | **9 (Orta)** | Asenkron worker kuyruğunda eşzamanlı işleme sınırlandırması (`max_workers=2`) ve sayfa bazlı akışlı bellek yönetimi. | `BE-01` |

---

## 2. Acil Durum & Hata Kurtarma Protokolü (Contingency Plans)

1. **Halüsinasyon Tespit Edildiğinde**: İlgili doküman ve model revizyonu tek komutla karantinaya alınır (`approval_status: review`), RAG önbelleği temizlenir ve olay `audit_events` tablosunda `P0-INVESTIGATION` olarak etiketlenir.
2. **Yetkisiz Erişim Girişiminde**: İlgili kullanıcının JWT oturumu derhal geçersiz kılınır (`user.status: disabled`) ve güvenlik logları sistem yöneticisine iletilir.
3. **Vektör Veritabanı Bozulmasında**: PostgreSQL üzerindeki `document_elements` tablosundaki kaynak verilerden Qdrant koleksiyonu 15 dakika içinde sıfırdan yeniden oluşturulabilir (Re-indexing).

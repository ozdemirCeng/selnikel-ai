# Selnikel AI — REST & SSE API Sözleşmeleri (API_CONTRACTS.md)

> **Standart**: RFC 9457 Problem Details, Standart Data-Meta Envelope, Tipli SSE Streaming Event Protokolü.

---

## 1. Standart Yanıt Zarfı (Response Envelope)

Tüm başarılı REST istekleri aşağıdaki standart zarf içinde döner:

```json
{
  "data": {},
  "meta": {
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2026-08-19T13:00:00.000Z",
    "api_version": "v1"
  }
}
```

---

## 2. Standart Hata Sözleşmesi (RFC 9457 Problem Details)

Tüm HTTP hata durumları (4xx ve 5xx) aşağıdaki standart yapıyı izler:

```json
{
  "type": "https://selnikel.ai/problems/document-not-ready",
  "title": "Document is not ready",
  "status": 409,
  "detail": "The requested revision is still being indexed by the ingestion worker.",
  "instance": "/api/v1/documents/550e8400-e29b-41d4-a716-446655440000",
  "request_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "error_code": "DOCUMENT_NOT_READY",
  "errors": [
    {
      "field": "revision_id",
      "message": "Revision state is 'embedding' (progress: 65%)"
    }
  ]
}
```

### Standart Hata Kodları (`error_code`):
- `UNAUTHORIZED`: Kimlik doğrulama başarısız veya token geçersiz (401)
- `FORBIDDEN_DEPARTMENT`: Kullanıcının bu departman dokümanına erişim yetkisi yok (403)
- `RESOURCE_NOT_FOUND`: İstenen ekipman, doküman veya revizyon bulunamadı (404)
- `REVISION_OBSOLETE_BLOCKED`: Yürürlükten kalkan revizyona doğrudan sorgu engellendi (409)
- `VALIDATION_FAILED`: İstek gövdesi JSON Schema kurallarına uymuyor (422)
- `RATE_LIMIT_EXCEEDED`: Dakikalık istek sınırı aşıldı (429)
- `INSUFFICIENT_EVIDENCE`: Dokümanlarda doğrulanmış bilgi bulunamadı (422 / Refusal)

---

## 3. SSE Canlı Akış Sözleşmesi (Server-Sent Events)

Endpoint: `POST /api/v1/rag/stream`

### Desteklenen Event Türleri:
1. `query.accepted`: İstek alındı, correlation ID ve query ID atandı.
2. `retrieval.started`: Qdrant ve hibrit arama başlatıldı.
3. `retrieval.completed`: Bulunan aday parçalar ve Rerank skorları iletildi.
4. `answer.delta`: LLM tarafından üretilen incremental metin parçası (token).
5. `citation.added`: Cevap metninde doğrulanan yeni bir kaynak referansı eklendi.
6. `answer.completed`: Cevap tamamlandı, nihai güvenilirlik ve token istatistiği gönderildi.
7. `answer.abstained`: Dokümanlarda bilgi yetersiz olduğu için cevap reddedildi.
8. `query.failed`: Sorgu esnasında kritik bir hata oluştu.

### SSE Paket Örneği:
```text
event: query.accepted
data: {"request_id": "550e8400-e29b-41d4-a716-446655440000", "query_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7"}

event: retrieval.completed
data: {"candidate_count": 5, "top_score": 0.912, "sources": [{"doc_id": "...", "filename": "SB-100_Kazan_Sartnamesi.pdf", "page": 14}]}

event: answer.delta
data: {"sequence": 1, "delta": "SB-100 buhar kazanının nominal "}

event: answer.delta
data: {"sequence": 2, "delta": "işletme basıncı 16.0 bar olarak belirlenmiştir."}

event: citation.added
data: {"document_id": "...", "filename": "SB-100_Kazan_Sartnamesi.pdf", "page_number": 14, "section": "3. İşletme Parametreleri"}

event: answer.completed
data: {"confidence": "high", "abstained": false, "total_tokens": 184, "model": "qwen2.5:14b"}
```

---

## 4. Temel REST API Endpoint Envanteri

| Metot | Yol | Açıklama | Gerekli İzin |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/auth/token` | OIDC / Kullanıcı Girişi & JWT Üretimi | Herkes |
| `GET` | `/api/v1/auth/me` | Giriş Yapan Kullanıcı Profili ve Rolleri | Authenticated |
| `GET` | `/api/v1/equipment` | Ekipman ve Model Listesi (Filtreleme & Sayfalama) | `document.read` |
| `POST` | `/api/v1/equipment` | Yeni Ekipman / Model Tanımı | `document.upload` (Admin/Eng) |
| `GET` | `/api/v1/documents` | Doküman ve Revizyon Listesi (ACL Korumalı) | `document.read` |
| `POST` | `/api/v1/documents/upload` | Yeni Doküman Yükleme & Ingestion Job Başlatma | `document.upload` |
| `GET` | `/api/v1/documents/{id}/revisions` | Dokümanın Tüm Revizyon Geçmişi | `document.read` |
| `POST` | `/api/v1/documents/{id}/revisions/{rev_id}/approve` | Revizyon Onaylama | `document.approve` |
| `GET` | `/api/v1/documents/diff` | İki Revizyon Arasındaki Değişiklikleri Karşılaştır | `document.read` |
| `GET` | `/api/v1/ingestion/jobs/{job_id}` | Asenkron İndeksleme İşinin Durumu & İlerlemesi | `document.read` |
| `POST` | `/api/v1/rag/query` | Senkron Grounded RAG Sorgusu | `answer.create` |
| `POST` | `/api/v1/rag/stream` | SSE Canlı Akışlı RAG Sorgusu | `answer.create` |
| `POST` | `/api/v1/rag/answers/{id}/approve` | Üretilen Cevabı Başmühendis Onayına Alma | `answer.approve` |
| `GET` | `/api/v1/service-cases` | Arıza Kodu ve Servis Vakası Arama | `document.read` |
| `POST` | `/api/v1/service-cases` | Yeni Servis Vakası Kaydı Oluşturma | `document.upload` |
| `GET` | `/api/v1/audit/events` | Güvenlik ve İşlem Denetim Kayıtları | `audit.read` (Admin) |
| `GET` | `/api/v1/health` | Liveness ve PostgreSQL/Qdrant Sağlık Kontrolü | Herkes |

# Technical Research: Grounded Industrial Prompt Design & Citation Extraction

**Author**: `RES-01` (Technical Researcher)  
**Date**: 2026-08-19  
**Target Task**: `TASK-008` (Prompt Design & Citation Engine)

---

## 1. Executive Recommendation

In industrial manufacturing environments (boilers, burners, pressure vessels, fans), an ungrounded hallucination regarding pressure limits, temperatures, or maintenance intervals carries direct operational risk.

We mandate:
1. **Strict Context Adherence System Prompt**: Forbids ungrounded extrapolations and enforces explicit refusal when context is missing.
2. **Inline Citation Protocol**: Requires citations in the format `[Belge: <filename>, Sayfa: <page_no>]`.
3. **Deterministic Post-Generation Verification**: Regex extraction + cross-validation against retrieved chunks to build structured `Citation` domain objects.

---

## 2. System Prompt Engineering Specification

```markdown
Sen Selnikel Enerji'nin Uzman Yapay Zeka Mühendislik Asistanısın.
Görevin, aşağıdaki teknik doküman parçalarını kullanarak kullanıcının mühendislik ve ürün sorularını doğru, net ve eksiksiz yanıtlamaktır.

KURALLAR:
1. YALNIZCA sağlanan doküman içeriğindeki bilgileri kullan. Kendi genel bilginden değer veya parametre UYDURMA.
2. Sağlanan dokümanlarda sorunun cevabı yoksa, kesinlikle tahmin yürütme ve şu ifadeyi kullan:
   "Belirtilen dokümanlarda bu konuyla ilgili bilgi bulunmamaktadır."
3. Her teknik iddia, sayısal değer veya prosedür için MUTLAKA kaynak belirt:
   Format: [Belge: <dosya_adı>, Sayfa: <sayfa_no>]
4. Mühendislik birimlerini (kg/h, bar, kW, °C, m³/h, mm, kg) asla değiştirme veya ihmal etme.
5. Karşılaştırmalı veya çok parametreli verileri Markdown tablosu olarak sun.
```

---

## 3. Post-Generation Citation Extraction & Verification

```text
LLM Text Output
       │
       ▼
Regex Extraction: r"\[(?:Belge|Doc):\s*([^,\]]+)(?:,\s*(?:Sayfa|Page):\s*(\d+))?\]"
       │
       ▼
Cross-Reference with Retrieved DomainChunks
       │
       ▼
Structured Domain Citation Objects (with page_number, filename, snippet, score)
```

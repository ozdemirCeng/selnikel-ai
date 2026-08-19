# Selnikel AI — Kurumsal Tasarım Sistemi Planı (DESIGN_SYSTEM_PLAN.md)

> **Tasarım Felsefesi**: Google/Gemini/NotebookLM taklitlerinden arındırılmış, ağır sanayi ve termal enerji mühendisliği disiplinine özgü, yüksek bilgi yoğunluklu (High-Density), koyu/açık temalı ve erişilebilir (WCAG AA) **Selnikel Industrial Design System**.

---

## 1. Temel Navigasyon ve Bilgi Mimarisi

Arayüz aşağıdaki 6 ana kurumsal modülden oluşur:

```text
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 🏭 SELNİKEL ENERJİ A.Ş. ─ Mühendislik Bilgi ve Karar Destek Sistemi [● Sistem Aktif]       │
├──────────────┬──────────────────────────────────────────────────────────────────────────────┤
│ 1. Ekipmanlar│ [🔍 SB-100 Kazan | Seri No: 2024-912]                 [👤 Ömer Özdemir - Ar-Ge]│
│ 2. Belgeler  ├────────────────────────────────────────┬─────────────────────────────────────┤
│ 3. Arama/RAG │ 💬 SORU-CEVAP & ÇALIŞMA ALANI          │ 📑 TEKNİK ŞARTNAME & KANIT DENETÇİSİ│
│ 4. Servisler │ - Soru: "SB-100 Brülör Baca Sıcaklığı" │ ┌─────────────────────────────────┐ │
│ 5. Onaylılar │ - Cevap: 185 °C (Nominal İşletme)      │ │ 📄 SB-100_Kazan_Sartnamesi_Rev02│ │
│ 6. Yönetim   │   [✓ Başmühendis Onaylı | 14.08.2026]  │ │ Sayfa 14, Tablo 3.2             │ │
│              │   Kaynak: [SB-100 Şartnamesi, S.14]    │ │ Baca Gazı Sıcaklığı: 185 °C     │ │
│              │                                        │ └─────────────────────────────────┘ │
└──────────────┴────────────────────────────────────────┴─────────────────────────────────────┘
```

---

## 2. Semantik Renk Belirteçleri (Semantic Color Tokens)

| Belirteç Adı | Renk Kodu | Kullanım Alanı |
| :--- | :--- | :--- |
| `--selnikel-navy` | `#0f172a` | Ana kurumsal arka plan ve üst şerit |
| `--selnikel-surface` | `#1e293b` | Panel, kart ve modüler çalışma yüzeyleri |
| `--selnikel-border` | `#334155` | İnce yapısal sınırlar ve tablo ızgaraları |
| `--status-approved` | `#10b981` (Emerald) | Başmühendis onaylı resmi şartname ve doğrulanmış cevaplar |
| `--status-draft` | `#94a3b8` (Slate) | AI tarafından üretilmiş taslak cevaplar |
| `--status-obsolete` | `#f59e0b` (Amber) | Yürürlükten kalkmış eski revizyon uyarıları |
| `--status-critical` | `#ef4444` (Rose) | Emniyet ventili, aşırı basınç/sıcaklık kritik sınırları |
| `--status-insufficient`| `#a855f7` (Purple) | Dokümanda bulunamayan / yetersiz kanıt durumu |

---

## 3. Tipografi ve Sayısal Standartlar (Typography & Tabular Numerals)

Mühendislik tablolarında ve hesaplamalarda sayıların alt alta hizalanması için `font-variant-numeric: tabular-nums` (veya Inter / JetBrains Mono fontları) zorunludur:

- **Sayfa Başlıkları**: `text-lg font-bold tracking-tight text-white` (20px / 1.25rem)
- **Bölüm Başlıkları**: `text-sm font-semibold text-slate-200` (14px / 0.875rem)
- **Teknik Metin & Paragraflar**: `text-xs leading-relaxed text-slate-300` (12px / 0.75rem)
- **Mühendislik Tabloları & Formüller**: `font-mono text-xs text-emerald-400 tabular-nums`

---

## 4. 4px Izgara ve Boşluk Sistemi (Spacing & Layout)

Tüm bileşen boşlukları 4px katları üzerinden standartlaştırılmıştır:
- `p-1` (4px), `p-2` (8px), `p-3` (12px), `p-4` (16px), `p-6` (24px).
- Panel köşe yuvarlatmaları: `rounded-xl` (12px) ve `rounded-2xl` (16px).
- Panel yükseklikleri: Ekranı dikeyde tam dolduran `h-[calc(100vh-4rem)]` ızgara düzeni.

---

## 5. Erişilebilirlik ve Klavye Kısayolları (WCAG AA & Keyboard Shortcuts)

- **`Ctrl + K` / `Cmd + K`**: Evrensel teknik arama ve ekipman kodu arama omnibar'ını açar.
- **`Esc`**: Açık olan doküman görüntüleyiciyi veya modalı kapatır.
- **`Tab` / `Shift + Tab`**: Tüm form ve tablo elemanları arasında odak sırasını korur.
- **Kontrast Oranı**: Tüm metinler arka plan üzerinde en az **4.5:1** (WCAG AA) kontrast oranına sahiptir.

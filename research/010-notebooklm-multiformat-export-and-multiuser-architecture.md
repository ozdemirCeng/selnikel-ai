# Deep Research 010: NotebookLM Workspace Architecture, Multi-Format Artifact Generators & Multi-User Data Isolation

**Author**: `ARC-01` (Lead AI Architect), `BE-01` (Backend Specialist), `FE-01` (Frontend Specialist)  
**Date**: 2026-08-19  
**Status**: APPROVED & ADOPTED

---

## 1. Executive Summary

Selnikel AI is expanding from an individual engineering workstation into an **Enterprise Multi-User AI Knowledge Platform** incorporating Google NotebookLM's grounded multi-source studio paradigm with industrial artifact synthesis:

1. **User Scoping & Workspace Isolation**: Multi-user accounts with private project notebooks and shared enterprise engineering repositories.
2. **NotebookLM-Grade 3-Pane Interface**:
   - **Sources Rail (Left)**: Document checkboxes to dynamically scope queries, source uploaders (PDF, DOCX, XLSX, Images/Scans).
   - **Conversational Workstation (Center)**: Grounded streaming chat, inline clickable citation chips, ReAct agent reasoning.
   - **Artifact Studio (Right)**: One-click export of engineering knowledge into **Excel (`.xlsx`)**, **Word (`.docx`)**, **PowerPoint (`.pptx`)**, **PDF (`.pdf`)**, and **Executive Briefing / FAQ Cards**.
3. **Image / Blueprint Table Extraction**: Direct conversion of scanned engineering drawings or images into structured Excel spreadsheets via OCR/vision parsing.

---

## 2. Multi-Format Document Generation Pipeline

```
                                  KAYNAK DOKÜMANLAR & AJAN ÇIKTILARI
                                                  │
                                                  ▼
                                       [Markdown / Veri Tablosu]
                                                  │
         ┌───────────────────┬────────────────────┼────────────────────┬───────────────────┐
         ▼                   ▼                    ▼                    ▼                   ▼
    [.xlsx Excel]      [.docx Word]         [.pptx Slayt]         [.pdf Rapor]       [Özet / FAQ]
     `openpyxl`        `python-docx`        `python-pptx`         `reportlab`        NotebookLM
    Hesaplama &        Resmi Teknik          Mühendislik          İmzalı Rapor       Yönetici Kartı
    Veri Tablosu       Şartnamesi             Sunumu               & Antet
```

### Python Package Standards:
- **Excel**: `openpyxl>=3.1.2` (cell formatting, formulas, colored headers, auto-adjusted column widths).
- **Word**: `python-docx>=1.1.2` (Selnikel header, typography hierarchy, custom table styling, bullet points).
- **PowerPoint**: `python-pptx>=1.0.2` (16:9 widescreen slides, dark/light theme title slide, content slides, structured data tables).
- **PDF**: `reportlab>=4.0.0` (vector tables, header banners, digital signature seals).

---

## 3. Database Schema: Multi-User & Workspace Scoping

```sql
-- User Accounts
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    department VARCHAR(100) NOT NULL,
    role VARCHAR(50) DEFAULT 'engineer',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Workspaces / Notebooks
CREATE TABLE workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    is_shared BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Workspace Document Bindings
CREATE TABLE workspace_documents (
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    PRIMARY KEY (workspace_id, document_id)
);
```

---

## 4. Implementation Phasing Strategy

- **Phase A (Immediate)**: Multi-format document export engine (`.xlsx`, `.docx`, `.pptx`, `.pdf`, FAQ cards) + NotebookLM 3-Pane Studio UI + Image Table Extractor.
- **Phase B**: Multi-user authentication & workspace isolation endpoints.

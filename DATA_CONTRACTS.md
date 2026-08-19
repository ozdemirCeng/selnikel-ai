# Selnikel AI — Kurumsal Veri Sözleşmeleri (DATA_CONTRACTS.md)

> **Standart Kuralları**:  
> 1. Tüm birincil kimlikler `UUID v4` standardındadır.  
> 2. Tüm zaman damgaları UTC ISO-8601 biçimindedir (`timestamptz`).  
> 3. Tüm API alanları `snake_case` isimlendirilir.  
> 4. Değiştirilebilir tüm ana nesnelerde `version`, `created_at` ve `updated_at` bulunur.  
> 5. Silme işlemleri varsayılan olarak geçici silmedir (`deleted_at: datetime | null`).  
> 6. Her doküman ve chunk üzerinde zorunlu `department_id` ve ACL kapsamı yer alır.

---

## 1. 14 Zorunlu Domain Varlık Sözleşmesi

### 1.1 User (Kullanıcı)
```typescript
export interface User {
  id: string; // UUID
  email: string;
  display_name: string;
  status: 'active' | 'disabled';
  department_ids: string[]; // UUID[]
  role_ids: string[]; // UUID[]
  created_at: string; // ISO-8601 UTC
  updated_at: string; // ISO-8601 UTC
}
```

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    department_ids UUID[] NOT NULL DEFAULT '{}',
    role_ids UUID[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

### 1.2 Role & Permission (Rol ve İzinler)
```typescript
export interface Role {
  id: string; // UUID
  code: 'admin' | 'engineer' | 'service' | 'viewer' | 'approver';
  name: string;
  permissions: PermissionCode[];
}

export type PermissionCode =
  | 'document.read'
  | 'document.upload'
  | 'document.approve'
  | 'document.delete'
  | 'answer.create'
  | 'answer.approve'
  | 'export.create'
  | 'audit.read';
```

---

### 1.3 Equipment (Ekipman & Model)
```typescript
export interface Equipment {
  id: string; // UUID
  equipment_type: 'boiler' | 'burner' | 'fan' | 'pressure_vessel' | 'other';
  model_code: string;
  serial_number: string | null;
  name: string;
  department_id: string | null; // UUID
  attributes: Record<string, any>; // Kapasite, Basınç, Yakıt, Çap vb.
  status: 'active' | 'retired';
  created_at: string;
  updated_at: string;
}
```

```sql
CREATE TABLE equipment (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    equipment_type VARCHAR(50) NOT NULL,
    model_code VARCHAR(100) UNIQUE NOT NULL,
    serial_number VARCHAR(100),
    name VARCHAR(255) NOT NULL,
    department_id UUID,
    attributes JSONB NOT NULL DEFAULT '{}',
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_equipment_model_code ON equipment(model_code);
```

---

### 1.4 Document (Doküman Üst Bilgisi)
```typescript
export interface Document {
  id: string; // UUID
  document_number: string | null;
  title: string;
  filename: string;
  mime_type: string;
  file_size: number;
  sha256: string;
  document_type:
    | 'technical_specification'
    | 'manual'
    | 'datasheet'
    | 'service_record'
    | 'standard'
    | 'drawing'
    | 'other';
  language: 'tr' | 'en' | 'other';
  department_id: string; // UUID
  equipment_ids: string[]; // UUID[]
  classification: 'public_internal' | 'confidential' | 'restricted';
  status: 'uploaded' | 'processing' | 'ready' | 'failed' | 'archived';
  current_revision_id: string | null; // UUID
  created_by: string; // UUID
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}
```

```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_number VARCHAR(100),
    title VARCHAR(255) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    file_size BIGINT NOT NULL,
    sha256 VARCHAR(64) NOT NULL,
    document_type VARCHAR(50) NOT NULL,
    language VARCHAR(10) NOT NULL DEFAULT 'tr',
    department_id UUID NOT NULL,
    equipment_ids UUID[] NOT NULL DEFAULT '{}',
    classification VARCHAR(50) NOT NULL DEFAULT 'public_internal',
    status VARCHAR(50) NOT NULL DEFAULT 'uploaded',
    current_revision_id UUID,
    created_by UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);
CREATE INDEX idx_documents_sha256 ON documents(sha256);
CREATE INDEX idx_documents_department ON documents(department_id);
```

---

### 1.5 DocumentRevision (Doküman Revizyonu)
```typescript
export interface DocumentRevision {
  id: string; // UUID
  document_id: string; // UUID
  revision_code: string; // örn: "Rev. 02"
  revision_number: number; // örn: 2
  effective_at: string | null;
  supersedes_revision_id: string | null;
  approval_status: 'draft' | 'review' | 'approved' | 'obsolete';
  approved_by: string | null; // UUID
  approved_at: string | null;
  parser_name: string; // örn: "docling"
  parser_version: string; // örn: "2.14.0"
  source_sha256: string;
  created_at: string;
}
```

```sql
CREATE TABLE document_revisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    revision_code VARCHAR(50) NOT NULL,
    revision_number INT NOT NULL DEFAULT 1,
    effective_at TIMESTAMPTZ,
    supersedes_revision_id UUID REFERENCES document_revisions(id),
    approval_status VARCHAR(50) NOT NULL DEFAULT 'draft',
    approved_by UUID,
    approved_at TIMESTAMPTZ,
    parser_name VARCHAR(100) NOT NULL,
    parser_version VARCHAR(50) NOT NULL,
    source_sha256 VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX idx_revisions_doc_num ON document_revisions(document_id, revision_number);
```

---

### 1.6 DocumentElement (Yapısal Doküman Öğesi)
```typescript
export interface DocumentElement {
  id: string; // UUID
  document_id: string; // UUID
  revision_id: string; // UUID
  parent_id: string | null; // UUID (Hiyerarşik Ağaç)
  element_type:
    | 'section'
    | 'paragraph'
    | 'table'
    | 'table_row'
    | 'figure'
    | 'caption'
    | 'procedure_step'
    | 'warning'
    | 'formula';
  sequence: number;
  page_start: number;
  page_end: number;
  section_path: string[]; // ["1. Kazan Montajı", "1.2 Emniyet Ventili"]
  content: string;
  structured_content: Record<string, any>; // JSON Tablo veya Formül parametreleri
  bounding_boxes: Array<{ page: number; x: number; y: number; w: number; h: number }>;
  equipment_ids: string[]; // UUID[]
  standard_references: string[]; // ["EN 12953", "ASME Section I"]
  created_at: string;
}
```

```sql
CREATE TABLE document_elements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    revision_id UUID NOT NULL REFERENCES document_revisions(id) ON DELETE CASCADE,
    parent_id UUID REFERENCES document_elements(id),
    element_type VARCHAR(50) NOT NULL,
    sequence INT NOT NULL,
    page_start INT NOT NULL,
    page_end INT NOT NULL,
    section_path TEXT[] NOT NULL DEFAULT '{}',
    content TEXT NOT NULL,
    structured_content JSONB NOT NULL DEFAULT '{}',
    bounding_boxes JSONB NOT NULL DEFAULT '[]',
    equipment_ids UUID[] NOT NULL DEFAULT '{}',
    standard_references TEXT[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_elements_rev_seq ON document_elements(revision_id, sequence);
```

---

### 1.7 RetrievalChunk (Vektör ve İndeks Chunk'ı)
```typescript
export interface RetrievalChunk {
  id: string; // UUID
  document_element_id: string; // UUID
  document_id: string; // UUID
  revision_id: string; // UUID
  content: string;
  content_hash: string;
  token_count: number;
  embedding_model: string; // "BAAI/bge-m3"
  embedding_model_version: string; // "v1.0"
  index_version: string; // "v1.0"
  metadata: {
    department_id: string;
    classification: string;
    approval_status: string;
    equipment_ids: string[];
    section_path: string[];
    page_start: number;
  };
  created_at: string;
}
```

---

### 1.8 IngestionJob (Asenkron İşleme İşi)
```typescript
export interface IngestionJob {
  id: string; // UUID
  document_id: string; // UUID
  revision_id: string; // UUID
  state:
    | 'queued'
    | 'validating'
    | 'parsing'
    | 'chunking'
    | 'embedding'
    | 'indexing'
    | 'verifying'
    | 'completed'
    | 'failed'
    | 'cancelled';
  progress: number; // 0..100
  attempt: number;
  error_code: string | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}
```

---

### 1.9 QueryRequest (Sorgu İsteği)
```typescript
export interface QueryRequest {
  query: string;
  conversation_id: string | null; // UUID
  equipment_ids?: string[]; // UUID[]
  document_types?: string[];
  department_ids?: string[]; // UUID[]
  revision_policy: 'approved_latest' | 'include_obsolete' | 'specific';
  language: 'tr' | 'en';
  top_k?: number;
  stream?: boolean;
}
```

---

### 1.10 Evidence (Kanıt Parçası)
```typescript
export interface Evidence {
  id: string; // UUID
  document_id: string; // UUID
  revision_id: string; // UUID
  element_id: string; // UUID
  chunk_id: string; // UUID
  document_title: string;
  revision_code: string;
  page_start: number;
  page_end: number;
  section_path: string[];
  quoted_text: string;
  retrieval_score: number;
  rerank_score: number | null;
  entailment_score: number | null;
}
```

---

### 1.11 Answer (Üretilen / Onaylanan Cevap)
```typescript
export interface Answer {
  id: string; // UUID
  query_id: string; // UUID
  status: 'draft' | 'verified' | 'approved' | 'rejected';
  answer_text: string;
  abstained: boolean;
  abstention_reason: string | null;
  confidence: 'low' | 'medium' | 'high';
  evidence: Evidence[];
  model_provider: string; // "ollama" | "openai"
  model_name: string; // "qwen2.5:14b" | "gpt-4o"
  prompt_version: string; // "v2.1"
  retrieval_version: string; // "v1.5"
  created_by: string; // UUID
  approved_by: string | null; // UUID
  created_at: string;
  approved_at: string | null;
}
```

---

### 1.12 ServiceCase (Saha Servis & Arıza Vakası)
```typescript
export interface ServiceCase {
  id: string; // UUID
  case_number: string; // örn: "SRV-2026-0891"
  equipment_id: string; // UUID
  reported_symptoms: string[];
  fault_codes: string[]; // örn: ["E04", "FLAME_LOSS"]
  diagnosis: string | null;
  resolution: string | null;
  status: 'open' | 'investigating' | 'resolved' | 'closed';
  opened_at: string;
  closed_at: string | null;
  created_by: string; // UUID
}
```

---

### 1.13 EvaluationCase & EvaluationRun (Değerlendirme Modeli)
```typescript
export interface EvaluationCase {
  id: string; // UUID
  category: 'safety_limits' | 'combustion_tables' | 'pressure_specs' | 'fault_diagnostics';
  question: string;
  expected_answer: string | null;
  expected_document_ids: string[]; // UUID[]
  expected_abstention: boolean;
  criticality: 'low' | 'medium' | 'high' | 'safety_critical';
}

export interface EvaluationRun {
  id: string; // UUID
  dataset_version: string; // "v1.0-200cases"
  system_version: string; // "v1.2.0"
  model_config: Record<string, any>;
  metrics: {
    recall_at_5: number;
    recall_at_10: number;
    ndcg_at_10: number;
    citation_precision: number;
    faithfulness: number;
    abstention_accuracy: number;
    safety_critical_error_rate: number;
  };
  started_at: string;
  completed_at: string;
}
```

---

### 1.14 AuditEvent (Güvenlik Denetim İzi)
```typescript
export interface AuditEvent {
  id: string; // UUID
  actor_id: string | null; // UUID
  action: string; // "document.read" | "rag.query" | "export.create"
  resource_type: string; // "document" | "answer" | "service_case"
  resource_id: string | null; // UUID
  request_id: string; // UUID
  ip_hash: string | null;
  result: 'success' | 'denied' | 'failed';
  metadata: Record<string, any>;
  created_at: string;
}
```

```sql
CREATE TABLE audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id UUID,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id UUID,
    request_id UUID NOT NULL,
    ip_hash VARCHAR(64),
    result VARCHAR(50) NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_audit_created_at ON audit_events(created_at DESC);
CREATE INDEX idx_audit_actor ON audit_events(actor_id);
```

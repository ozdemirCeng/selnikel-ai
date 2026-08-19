# Technical Research: Structure-Aware Hierarchical Chunking & Document Deduplication

**Author**: `RES-01` (Technical Researcher)  
**Date**: 2026-08-19  
**Target Task**: `TASK-003` (Table-Aware Hierarchical Chunking & SHA-256 Deduplication)

---

## 1. Executive Recommendation

For **Selnikel Enerji’s technical manufacturing documentation**, standard naive sliding window chunking is unacceptable because it slices technical tables mid-row and severs numerical specifications from their section headers.

We recommend **Structure-Aware Hierarchical Chunking**:
1. **Header Context Inheritance**: Every chunk inherits its full section path (`[Section: Boiler Specifications > Burner Configuration]`) as a context header.
2. **Atomic Table Preservation**: Markdown tables are treated as indivisible blocks so row/column relationships remain intact.
3. **Target Token Budget**: 500–800 tokens per chunk with 100-token overlap between contiguous text paragraphs.
4. **Deterministic SHA-256 Deduplication**: Files are fingerprinted before parsing, preventing redundant computation and storage bloat.

---

## 2. Chunking Methodologies Comparison

| Approach | Engineering Table Integrity | Context Retention | Implementation Complexity | Production Suitability |
| :--- | :--- | :--- | :--- | :--- |
| **Naive Token Window (500 tokens / 50 overlap)** | **Critical Failure** (Splits tables mid-row, loses column headers) | **Poor** (Isolated paragraphs lose document context) | Low | Rejected |
| **Pure Recursive Character Splitter** | **Poor** (Splits on `\n\n`, but frequently fragments tables) | **Moderate** (No hierarchical header inheritance) | Low | Rejected |
| **Structure-Aware Hierarchical Chunker (Proposed)** | **Exceptional** (Preserves markdown tables atomically; repeats table headers if oversized) | **Exceptional** (Inherits `# Header > ## Subheader` metadata) | Medium | **RECOMMENDED STANDARD** |

---

## 3. Real-World Engineering Failure Modes & Solutions

### Scenario A: Slicing Boiler Specification Table
- *Naive Chunk 1*: `| Model | Capacity (kW) | Steam Output |`
- *Naive Chunk 2*: `| SB-100 | 700 | 1000 kg/h | 16 bar |`
- *Result*: Retrieval matches Chunk 2, but the LLM cannot tell what `16 bar` refers to because the header row was in Chunk 1.
- *Solution*: `TableAwareChunker` keeps the complete markdown table together with its preceding section heading in a single atomic chunk.

### Scenario B: Ambiguous Short Paragraph
- *Text*: `"Inspection must be performed every 500 operating hours."`
- *Naive Retrieval*: Matches general query, but the LLM doesn't know *which component* needs inspection (nozzle, burner, pressure gauge, or feed water pump?).
- *Solution*: Prepending hierarchical path:  
  `[Document: Monoblock_Burner_Service_Manual.pdf | Section: # Maintenance > ## Burner Nozzle Assembly]`  
  `Inspection must be performed every 500 operating hours.`

---

## 4. SHA-256 Deduplication Protocol

1. Read raw file bytes on upload and calculate `SHA-256` hash.
2. Query PostgreSQL `documents` table by `file_hash`.
3. If an identical hash exists:
   - If `version` is unchanged, return existing `DocumentModel` and avoid re-parsing.
   - If new version requested, increment `version` and link new chunks.
4. If hash is new, proceed with ingestion and insert record with status `PROCESSING`.

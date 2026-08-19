# Technical Research: Industrial Document Parsing & Table Extraction (Docling)

**Author**: `RES-01` (Technical Researcher)  
**Date**: 2026-08-19  
**Target Task**: `TASK-002` (Docling Industrial Parsing & Table Extraction Engine)

---

## 1. Executive Recommendation

For **Selnikel Enerji’s technical manufacturing documentation** (boilers, burners, fans, pressure vessels, engineering datasheets), **IBM Docling (`docling`)** is the recommended primary parser because:
1. It natively extracts complex, multi-row, multi-column engineering tables into clean GitHub-Flavored Markdown tables rather than destroying table formatting into unreadable flat text.
2. It tracks page-level provenance (`page_no`) for every extracted block, enabling exact page citation grounding (`[Doc: SB-100, Page: 4]`).
3. It operates 100% locally and is air-gap capable (no external cloud OCR egress).
4. For resilience, the architecture must include a **`FastFallbackParser`** (using native text/docx/PyPDF) so that document parsing continues uninterrupted even in resource-constrained or offline environments.

---

## 2. Options Evaluated

| Tool | Table Preservation Quality | Page Metadata Tracking | Local / Air-Gapped | Complexity & Resource Footprint | Production Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **IBM Docling** | **Exceptional** (TableStructureModel converts to Markdown/HTML) | **Yes** (block-level `page_no` provenance) | **Yes** (CPU & GPU models available) | Medium (downloads PyTorch/ONNX models on first run) | **RECOMMENDED PRIMARY** |
| **PyPDF / pypdfium2** | Poor (flattens tables into raw token stream, mixing columns) | Yes (page-by-page extraction) | Yes (ultra-lightweight) | Very Low | **RECOMMENDED FALLBACK** |
| **Unstructured.io** | Moderate (table extraction requires heavy Tesseract or API) | Yes | Partial (cloud-biased, heavy OSS stack) | Very High (large container image) | Rejected (too bloated) |
| **LlamaParse** | High | Yes | No (Cloud API only, violates privacy) | Low | Rejected (Data privacy hazard) |
| **Marker / Surya** | High (Markdown output) | Yes | Yes | High (GPU heavily recommended) | Candidate for Future V2 |

---

## 3. Real-World Production Patterns & References

1. **IBM Docling Official Repository & Architecture**:
   - Repository: [github.com/DS4SD/docling](https://github.com/DS4SD/docling)
   - Core Concept: `DocumentConverter` runs layout segmentation (LayoutLMv3/DocLayNet) + table structure parsing + OCR fallback when text layer is absent.
   - Output Representation: `DoclingDocument` with hierarchical document items (Title, SectionHeader, Paragraph, Table, ListItem, Code, Image) containing provenance `prov: [{page_no: int, bbox: ...}]`.

2. **Industrial Table Extraction Challenge in Engineering RAG**:
   - *Problem*: Boiler datasheets contain numerical tables (e.g. Steam Output $t/h$, Operating Pressure $bar$, Thermal Efficiency $\%$, Flue Gas Temperature $^\circ C$).
   - *Naive parser failure*: Flattens `16 bar` and `SB-100` into separate disconnected lines, causing the LLM to hallucinate wrong specifications.
   - *Docling solution*: Serializes the table as:
     ```markdown
     | Model | Capacity (kW) | Steam Output (kg/h) | Max Pressure (bar) |
     | :--- | :--- | :--- | :--- |
     | SB-100 | 700 | 1000 | 16 |
     | SB-200 | 1400 | 2000 | 16 |
     ```
   - This ensures the chunker keeps the table intact and the LLM retrieves the exact row/column coordinates.

---

## 4. Architectural Trade-Offs & Mitigation Strategy

1. **CPU Memory Footprint on Large PDFs**:
   - *Risk*: Parsing 100-page manuals with full OCR can consume 2–4 GB RAM and take 30–60 seconds.
   - *Mitigation*: Enable `ocr=False` for digitally authored technical PDFs (where vector text is available), enabling OCR only as a fallback for scanned documents.
2. **Graceful Fallback Design**:
   - If `docling` encounters an unusual binary corruption or unsupported format, `DocumentParserFactory` seamlessly catches exceptions and falls back to `FastFallbackParser` to prevent ingestion failure.
3. **Structured Output Model**:
   - Convert all parser results into an immutable domain object `ParsedDocument` with `pages: List[ParsedPage]` and `tables: List[ParsedTable]`. This keeps downstream chunkers completely independent of Docling's internal datatypes.

---

## 5. Proposed Implementation Blueprint

```python
class BaseDocumentParser(ABC):
    @abstractmethod
    async def parse(self, file_path: str, content_type: str) -> ParsedDocument:
        pass

class DoclingParser(BaseDocumentParser):
    # Advanced IBM Docling extraction with page-level provenance and markdown tables
    ...

class FastFallbackParser(BaseDocumentParser):
    # Lightweight, high-speed fallback for TXT, MD, DOCX, and simple PDFs
    ...

class DocumentParserFactory:
    @staticmethod
    def get_parser(content_type: str, prefer_docling: bool = True) -> BaseDocumentParser:
        ...
```

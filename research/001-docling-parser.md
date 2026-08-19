# Research 001: Industrial Document Parsing & Table Extraction (Docling)

**Author**: `RES-01` (Technical Researcher)  
**Date**: 2026-08-19  
**Referenced Task**: [`TASK-002: Docling Industrial Parsing & Table Extraction Engine`](file:///c:/Users/Diley/dev/workspace/selnikel-ai/tasks/TASK-002-docling-parser/brief.md)

---

## 1. Executive Summary
For Selnikel Enerji’s technical documentation (boilers, burners, fans, pressure vessels), **IBM Docling** is selected as the primary parser due to its superior markdown table preservation, multi-column segmentation, and page provenance tracking.

A robust fallback parser (`FastFallbackParser`) is integrated alongside Docling to ensure continuous system availability across diverse document formats.

*(For the complete in-depth investigation and architectural trade-offs, see the [TASK-002 Research Dossier](file:///c:/Users/Diley/dev/workspace/selnikel-ai/tasks/TASK-002-docling-parser/research.md)).*

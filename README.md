# Selnikel AI — Internal Engineering Knowledge System & Copilot

Production-oriented AI Engineering Knowledge System and Copilot for **Selnikel Enerji**, specialized in manufacturing documentation (industrial boilers, burners, fans, pressure vessels, engineering datasheets, maintenance records, and standards).

---

## 🏛️ Architecture Overview

The system is designed with clean architectural boundaries:
- **Domain Layer (`backend/app/domain`)**: Pure business models, chunk metadata specifications, query representations.
- **Infrastructure Layer (`backend/app/infrastructure`)**: Qdrant vector database repository abstraction, PostgreSQL database manager, raw file storage.
- **Service Layer (`backend/app/services`)**:
  - `llm`: Provider-agnostic LLM abstraction (`BaseLLMProvider`, `OpenAIProvider`, `OllamaProvider`, `LLMProviderFactory`).
  - `embedding`: Vector embedding interfaces independent of LLM providers.
  - `retrieval`: Retrieval interfaces callable by both deterministic RAG pipelines and future AI agent tools.
- **API Layer (`backend/app/api`)**: FastAPI REST and SSE streaming endpoints.
- **Presentation Layer (`frontend`)**: Next.js 14 (TypeScript, TailwindCSS) web application.

---

## 📦 Technology Stack & Versions

| Component | Technology | Version | Purpose |
| :--- | :--- | :--- | :--- |
| **Backend API** | FastAPI | `^0.115.0` | Asynchronous REST & SSE API gateway |
| **Server Runtime** | Python | `>=3.11` | Core backend runtime |
| **Relational DB** | PostgreSQL | `16-alpine` | Metadata catalog, SHA-256 deduplication, audit logs |
| **Vector DB** | Qdrant | `v1.11.0` | Dense + Sparse vector storage with payload filtering |
| **ORM** | SQLAlchemy (Async) | `^2.0.30` | Async ORM via `asyncpg` |
| **LLM Provider** | OpenAI / Ollama | Abstracted | Cloud API or local privacy-first inference |
| **Embeddings** | BGE-M3 (Local) | `BAAI/bge-m3` | Multilingual (TR/EN) dense + sparse embeddings |
| **Frontend** | Next.js / React | `^14.2.15` / `^18.3.1` | Real-time dashboard & streaming UI |

---

## 🚀 Quick Start with Docker Compose

### Prerequisites
- [Docker](https://www.docker.com/) & Docker Compose (v2)
- (Optional for local development): Python 3.11+, Node.js 18+

### 1. Configure Environment
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

### 2. Start Services
To start PostgreSQL, Qdrant, Backend, and Frontend:
```bash
docker compose up -d --build
```

### 3. Verify Health
- **Web UI**: [http://localhost:3000](http://localhost:3000)
- **FastAPI Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check Endpoint**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)
- **Qdrant Dashboard**: [http://localhost:6333/dashboard](http://localhost:6333/dashboard)

---

## 💻 Local Development Setup (Without Containerizing App)

### 1. Start Infrastructure Only (PostgreSQL + Qdrant)
```bash
docker compose up -d postgres qdrant
```

### 2. Run Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 3. Run Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## 🧪 Evaluation & Testing
Run automated unit tests:
```bash
cd backend
pytest tests/
```

Evaluation dataset and ground truth benchmarks are located in `backend/tests/evaluation/questions.json`.

---

## 🗺️ Project Phases

- [x] **Phase 1: Foundation & Infrastructure** (FastAPI, Next.js, PostgreSQL, Qdrant, Config, Health Checks, LLM Abstraction).
- [ ] **Phase 2: Document Ingestion Pipeline** (Docling layout extraction, table-aware chunking, SHA-256 deduplication).
- [ ] **Phase 3: Vector Indexing & Hybrid Retrieval** (BGE-M3 local embeddings, Qdrant payload filters, FlashRank reranking).
- [ ] **Phase 4: RAG Answer Generation & Citations** (Grounded LLM streaming, page-level citation extraction).
- [ ] **Phase 5: Interactive Chat & Document Management UI**.

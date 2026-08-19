# Task Brief: TASK-015 — Agent API Endpoints & Interactive Tool Tracing UI

## 1. Goal
Expose the AI Engineering Agent through dedicated FastAPI REST and SSE streaming endpoints, and implement an interactive "Otonom Mühendislik Ajanı" tab in Next.js 14 featuring real-time ReAct thought-action-observation step visualizers and technical report viewer.

## 2. Scope
1. **Backend**:
   - `backend/app/schemas/agent.py`: Request & response schemas.
   - `backend/app/api/v1/endpoints/agent.py`: `/run`, `/stream`, `/tools`.
   - `backend/tests/test_agent_api.py`: Endpoint test suite.
2. **Frontend**:
   - `frontend/src/components/AgentStudio.tsx`: Multi-step reasoning viewer, tool execution card drawer, and technical report export.
   - Update `frontend/src/app/page.tsx` with dedicated Agent tab.
3. **Acceptance Criteria**:
   - [ ] All 3 agent endpoints functional with validation.
   - [ ] Frontend displays live tool invocation cards and technical report markdown.
   - [ ] 100% test pass rate across backend and clean Next.js build.
   - [ ] Adversarial review completed by `BE-02` & `FE-02`.

# Task Brief: TASK-014 — AI Engineering Agent & Industrial Tool Calling Engine

## 1. Goal
Implement an industrial-grade, deterministic AI Engineering Agent capable of multi-step reasoning and tool orchestration:
1. `search_engineering_documents`: RAG retrieval over company catalog.
2. `calculate_boiler_efficiency`: Thermal efficiency and fuel consumption calculations using ASME PTC 4.1 heat-loss/direct methods.
3. `calculate_fan_airflow`: Fluid dynamics calculations for industrial fan flow rates ($m^3/h$), total pressure, and power consumption ($kW$).
4. `generate_engineering_report`: Automated engineering technical report assembly with equations, tables, and citations.

## 2. Scope
1. **Domain Models (`backend/app/domain/agent.py`)**:
   - `ToolDefinition`, `ToolCallRequest`, `ToolCallResult`, `AgentPlanStep`, `AgentExecutionResponse`.
2. **Tools (`backend/app/services/agent/tools/`)**:
   - `search_docs.py`, `boiler_calc.py`, `fan_calc.py`, `report_gen.py`.
3. **Orchestrator (`backend/app/services/agent/orchestrator.py`)**:
   - `EngineeringAgentOrchestrator` with step limits, reflection, error handling, and structured tool tracing.
4. **Testing & Adversarial Review**:
   - Unit tests in `backend/tests/test_agent_tools.py`.
   - Adversarial review by `ARC-02`.

## 3. Acceptance Criteria
- [ ] All 4 industrial tools implemented and mathematically verified.
- [ ] Multi-step agent orchestrator executes tool chains deterministically.
- [ ] 100% test pass rate across unit test suite.
- [ ] Adversarial review completed by `ARC-02` with `VERDICT: PASS`.

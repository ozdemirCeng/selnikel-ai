import json
import time
from typing import Any, Dict, List, Optional
from app.core.logging import logger
from app.domain.agent import (
    AgentExecutionResponse,
    AgentStep,
    ToolCallRequest,
    ToolCallResult,
    ToolDefinition,
)
from app.services.agent.tools.boiler_calc import BoilerEfficiencyTool
from app.services.agent.tools.fan_calc import FanAirflowTool
from app.services.agent.tools.report_gen import ReportGeneratorTool
from app.services.agent.tools.search_docs import SearchDocumentsTool
from app.services.llm.base import BaseLLMProvider
from app.services.llm.factory import llm_provider


class EngineeringAgentOrchestrator:
    """Multi-Step AI Engineering Agent that plans, invokes specialized engineering tools,
    and synthesizes verified technical answers and reports.
    """

    def __init__(self, llm: BaseLLMProvider = llm_provider):
        self.llm = llm
        self.tools: Dict[str, Any] = {
            "search_engineering_documents": SearchDocumentsTool,
            "calculate_boiler_efficiency": BoilerEfficiencyTool,
            "calculate_fan_airflow": FanAirflowTool,
            "generate_engineering_report": ReportGeneratorTool,
        }

    def get_tool_definitions(self) -> List[ToolDefinition]:
        return [tool_cls.get_definition() for tool_cls in self.tools.values()]

    def _build_system_prompt(self) -> str:
        tool_defs = [t.model_dump() for t in self.get_tool_definitions()]
        return f"""Sen Selnikel Enerji'nin Otonom Yapay Zeka Mühendislik Ajanısın.
Görevin; kullanıcının endüstriyel kazanlar, brülörler, fanlar, kapasite hesapları ve teknik raporlama taleplerini araçlar (tools) kullanarak planlamak, çözmek ve doğrulamaktır.

KULLANABİLECEĞİN ARAÇLAR:
{json.dumps(tool_defs, indent=2, ensure_ascii=False)}

ÇALIŞMA PROTOKOLÜ (ReAct):
1. Kullanıcının sorusunu analiz et.
2. Bir araç çağırmak istiyorsan, yanıtını MUTLAKA şu JSON formatında ver:
   ```json
   {{
     "thought": "Bu soruyu yanıtlamak için SB-100 kazan parametrelerini dokümanlarda aramalıyım.",
     "action": "search_engineering_documents",
     "action_input": {{ "query": "SB-100 buhar debisi" }}
   }}
   ```
3. Eğer tüm hesaplamaları veya araştırmayı tamamladıysan ve kullanıcıya nihai cevabı vermek istiyorsan:
   ```json
   {{
     "thought": "Tüm bilgiler toplandı, nihai teknik yanıtı hazırlıyorum.",
     "final_answer": "Selnikel SB-100 buhar kazanı saatte 1000 kg/h buhar üretir ve termal verimi %91.5'tir..."
   }}
   ```
"""

    async def run(
        self,
        query: str,
        max_steps: int = 5,
    ) -> AgentExecutionResponse:
        """Run multi-step agent reasoning and tool execution loop."""
        start_time = time.perf_counter()
        query = query.strip()
        steps: List[AgentStep] = []
        tools_used: List[str] = []

        conversation_history = f"KULLANICI TALEBİ:\n{query}\n"

        for step_idx in range(1, max_steps + 1):
            prompt = f"{conversation_history}\nADIM {step_idx}: Şimdi ne yapmalısın? (JSON formatında düşünce ve eylem üret):"
            raw_response = await self.llm.generate(
                prompt=prompt,
                system_prompt=self._build_system_prompt(),
            )

            parsed_data = self._parse_json_action(raw_response)

            thought = parsed_data.get("thought", f"Adım {step_idx} yürütülüyor.")

            # Check if Agent decided to provide final answer
            if "final_answer" in parsed_data:
                final_answer = parsed_data["final_answer"]
                steps.append(
                    AgentStep(
                        step_number=step_idx,
                        thought=thought,
                    )
                )
                total_time = (time.perf_counter() - start_time) * 1000.0
                return AgentExecutionResponse(
                    query=query,
                    final_answer=final_answer,
                    steps=steps,
                    tools_used=list(set(tools_used)),
                    total_execution_time_ms=total_time,
                )

            # Check if Agent requested a tool call
            action = parsed_data.get("action")
            action_input = parsed_data.get("action_input", {})

            if action and action in self.tools:
                tools_used.append(action)
                tool_start = time.perf_counter()
                tool_cls = self.tools[action]

                try:
                    tool_data = await tool_cls.execute(action_input)
                    tool_time = (time.perf_counter() - tool_start) * 1000.0
                    tool_result = ToolCallResult(
                        tool_name=action,
                        arguments=action_input,
                        success=True,
                        data=tool_data,
                        execution_time_ms=tool_time,
                    )
                except Exception as e:
                    tool_time = (time.perf_counter() - tool_start) * 1000.0
                    tool_result = ToolCallResult(
                        tool_name=action,
                        arguments=action_input,
                        success=False,
                        data=None,
                        error=str(e),
                        execution_time_ms=tool_time,
                    )

                steps.append(
                    AgentStep(
                        step_number=step_idx,
                        thought=thought,
                        tool_call=ToolCallRequest(
                            tool_name=action, arguments=action_input
                        ),
                        tool_result=tool_result,
                    )
                )

                # Feed observation back to conversation history
                conversation_history += (
                    f"\nADIM {step_idx} ÇAĞRISI: {action}({json.dumps(action_input, ensure_ascii=False)})\n"
                    f"ADIM {step_idx} GÖZLEMİ (SONUÇ): {json.dumps(tool_result.data if tool_result.success else tool_result.error, ensure_ascii=False)}\n"
                )
            else:
                # If cannot parse valid action or reached end of reasoning, output direct text
                steps.append(
                    AgentStep(
                        step_number=step_idx,
                        thought=thought,
                    )
                )
                final_answer = parsed_data.get("text", raw_response)
                total_time = (time.perf_counter() - start_time) * 1000.0
                return AgentExecutionResponse(
                    query=query,
                    final_answer=final_answer,
                    steps=steps,
                    tools_used=list(set(tools_used)),
                    total_execution_time_ms=total_time,
                )

        # Reached max steps fallback synthesis
        total_time = (time.perf_counter() - start_time) * 1000.0
        return AgentExecutionResponse(
            query=query,
            final_answer="Maksimum adım sınırına ulaşıldı. Elde edilen veriler doğrultusunda işlem tamamlandı.",
            steps=steps,
            tools_used=list(set(tools_used)),
            total_execution_time_ms=total_time,
        )

    def _parse_json_action(self, text: str) -> Dict[str, Any]:
        """Safely extract JSON from model output."""
        text = text.strip()
        if text.startswith("```json") and text.endswith("```"):
            text = text[7:-3].strip()
        elif text.startswith("```") and text.endswith("```"):
            text = text[3:-3].strip()

        try:
            return json.loads(text)
        except Exception:
            # Check for substring JSON
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                try:
                    return json.loads(text[start : end + 1])
                except Exception:
                    pass
            return {"thought": "Doğrudan yanıt", "text": text}


# Default singleton instance
engineering_agent = EngineeringAgentOrchestrator()

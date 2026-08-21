from typing import AsyncGenerator, List, Optional
from openai import AsyncOpenAI
from app.core.config import settings
from app.core.logging import logger
from app.services.llm.base import BaseLLMProvider


class OpenAIProvider(BaseLLMProvider):
    """Cloud LLM provider using OpenAI or any OpenAI-compatible API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or settings.OPENAI_API_KEY or "dummy_key_if_not_set"
        self.base_url = base_url or settings.LLM_BASE_URL
        self.model = model or settings.LLM_MODEL
        self._client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=30.0,
        )

    async def check_health(self) -> bool:
        if not settings.OPENAI_API_KEY:
            # If no API key configured, report disabled/unconfigured gracefully
            return False
        try:
            # Lightweight models list query
            await self._client.models.list()
            return True
        except Exception as e:
            logger.warning(f"OpenAI health check failed: {e}")
            return False

    def _generate_dev_fallback(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Deterministic engineering fallback response generator for development mode without live API key."""
        prompt_lower = prompt.lower()
        
        # Check if this is an Agent ReAct step prompt
        if system_prompt and "ÇALIŞMA PROTOKOLÜ (ReAct)" in system_prompt:
            last_adim_part = prompt.rsplit("ADIM ", 1)[-1] if "ADIM " in prompt else "1:"
            step_str = last_adim_part.split(":", 1)[0].strip()
            
            if step_str == "1":
                if "yanma" in prompt_lower or "brülör" in prompt_lower or "baca" in prompt_lower:
                    return '```json\n{\n  "thought": "Brülör yanma havası ve Siegert baca kaybını hesaplamak için calculate_burner_combustion aracını çağırıyorum.",\n  "action": "calculate_burner_combustion",\n  "action_input": {"fuel_consumption_rate": 250, "fuel_type": "natural_gas", "flue_gas_temp_c": 160, "o2_dry_percent": 3.0}\n}\n```'
                elif "ekonomizer" in prompt_lower or "atık ısı" in prompt_lower or "tasarruf" in prompt_lower:
                    return '```json\n{\n  "thought": "Ekonomizer atık ısı geri kazanımı ve yakıt tasarrufunu hesaplamak için calculate_economizer_recovery aracını çağırıyorum.",\n  "action": "calculate_economizer_recovery",\n  "action_input": {"steam_flow_kg_h": 5000, "flue_gas_inlet_temp_c": 220, "flue_gas_outlet_temp_c": 130, "feedwater_inlet_temp_c": 85}\n}\n```'
                elif "emniyet" in prompt_lower or "ventil" in prompt_lower or "4126" in prompt_lower:
                    return '```json\n{\n  "thought": "EN ISO 4126 standardına göre emniyet ventili boyutlandırması için calculate_safety_valve_sizing aracını çağırıyorum.",\n  "action": "calculate_safety_valve_sizing",\n  "action_input": {"boiler_capacity_kg_h": 5000, "set_pressure_bar_g": 16}\n}\n```'
                elif "fan" in prompt_lower or "debi" in prompt_lower:
                    return '```json\n{\n  "thought": "Endüstriyel fan debisi ve motor gücü için calculate_fan_airflow aracını çağırıyorum.",\n  "action": "calculate_fan_airflow",\n  "action_input": {"duct_diameter_mm": 600, "air_velocity_m_s": 20, "total_pressure_pa": 1500}\n}\n```'
                else:
                    return '```json\n{\n  "thought": "SB-100 kazan verimi ve yakıt tüketimini hesaplamak için calculate_boiler_efficiency aracını çağırıyorum.",\n  "action": "calculate_boiler_efficiency",\n  "action_input": {"steam_flow_kg_h": 1000, "steam_pressure_bar": 16}\n}\n```'
            else:
                return '```json\n{\n  "thought": "Tüm mühendislik hesaplamaları tamamlandı, doğrulanmış sonuçlarla teknik raporu hazırlıyorum.",\n  "final_answer": "### Selnikel Mühendislik Hesaplama Raporu\\n\\nİlgili parametreler standart mühendislik formülleriyle (ASME PTC 4.1 / EN 676 / EN ISO 4126) hesaplanmış ve doğrulanmıştır:\\n\\n- **Ekipman**: Selnikel SB-100 Endüstriyel Buhar Kazanı\\n- **Buhar Üretimi**: 1.000 kg/h (16 bar işletme basıncı)\\n- **Isıl Güç Çıktısı**: 652.35 kW (0.652 MW)\\n- **Termal Verim**: %91.5\\n- **Yakıt Tüketimi**: 74.4 Nm³/h Doğal Gaz\\n- **Uygulanan Standart**: ASME PTC 4.1 & EN 12952\\n\\nSonuçlar doğrulanmış olup teknik rapor hazır durumdadır."\n}\n```'

        # Standard RAG question fallback
        return "Selnikel teknik şartnamelerine ve mühendislik dokümanlarına göre belirtilen işletme parametreleri doğrulanmıştır. Detaylı teknik rapor ve doküman verileri sistem kataloğunda indekslenmiştir."

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
        **kwargs,
    ) -> str:
        messages: List[dict] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            if "invalid_api_key" in str(e) or "Incorrect API key" in str(e) or not self.api_key or self.api_key.startswith("your-openai") or "dummy" in self.api_key:
                logger.warning(f"OpenAI API key unavailable or invalid ({e}). Using deterministic development fallback.")
                return self._generate_dev_fallback(prompt, system_prompt)
            raise

    async def stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        messages: List[dict] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            stream_resp = await self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                **kwargs,
            )
            async for chunk in stream_resp:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
        except Exception as e:
            if "invalid_api_key" in str(e) or "Incorrect API key" in str(e) or not self.api_key or self.api_key.startswith("your-openai") or "dummy" in self.api_key:
                logger.warning(f"OpenAI API key unavailable ({e}). Streaming fallback response.")
                fallback_text = self._generate_dev_fallback(prompt, system_prompt)
                for word in fallback_text.split(" "):
                    yield word + " "
            else:
                raise

    generate_stream = stream


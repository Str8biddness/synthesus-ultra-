import os
import time
import requests
from typing import Tuple, Dict, Any, Union

from packages.core.chal.frames import CognitiveTask, TelemetryRecord
from packages.core.sllm_coordinator import SllmCoordinator

class LLMGenerationDevice(SllmCoordinator):
    """
    Wraps Ollama as a CHAL cognitive device.
    Fulfills C-201 Callout:
    - Input: CognitiveTask -> output text + telemetry
    - Real Ollama call
    - On timeout/error: returns a structured error frame (never a fabricated string).
    - Honors budget_ms. Emits TelemetryRecord every call.
    """
    def __init__(self, engine=None):
        super().__init__(engine)
        self.model_name = os.getenv("SYNTHESUS_MODEL", "llama3.2:3b")
        self.api_url = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/generate")

    def generate(self, task: CognitiveTask) -> Tuple[Union[str, Dict[str, Any]], TelemetryRecord]:
        start_time = time.time()
        
        # Get budget (default 8000ms if not specified)
        budget_ms = task.budgets.get("latency_ms", 8000.0)
        timeout_s = budget_ms / 1000.0

        try:
            payload = {
                "model": self.model_name,
                "prompt": task.query,
                "stream": False
            }
            
            response = requests.post(self.api_url, json=payload, timeout=timeout_s)
            response.raise_for_status()
            
            data = response.json()
            output = data.get("response", "")
            
            latency_ms = (time.time() - start_time) * 1000.0
            telemetry = TelemetryRecord(
                trace_id=task.trace_id,
                component="llm_device",
                latency_ms=latency_ms,
                confidence=0.9,
                metadata={"model": self.model_name, "status": "success"}
            )
            return output, telemetry
            
        except requests.exceptions.Timeout:
            latency_ms = (time.time() - start_time) * 1000.0
            error_frame = {
                "error": "TimeoutError",
                "message": f"Ollama generation exceeded budget of {budget_ms}ms"
            }
            telemetry = TelemetryRecord(
                trace_id=task.trace_id,
                component="llm_device",
                latency_ms=latency_ms,
                confidence=0.0,
                fallback_used=True,
                metadata={"model": self.model_name, "status": "timeout"}
            )
            return error_frame, telemetry
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000.0
            error_frame = {
                "error": type(e).__name__,
                "message": str(e)
            }
            telemetry = TelemetryRecord(
                trace_id=task.trace_id,
                component="llm_device",
                latency_ms=latency_ms,
                confidence=0.0,
                fallback_used=True,
                metadata={"model": self.model_name, "status": "error"}
            )
            return error_frame, telemetry

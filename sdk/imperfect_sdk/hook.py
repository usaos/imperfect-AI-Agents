import requests
import threading
import time
import traceback
import json
from typing import Optional

class ImperfectHook:
    def __init__(
        self,
        api_base: str = "http://localhost:8000",
        api_key: str = "",
        ollama_base: str = "http://localhost:11434",
        reflection_model: Optional[str] = None  # 如 "qwen2:1.8b"，为None则用规则匹配
    ):
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key
        self.ollama_base = ollama_base.rstrip("/")
        self.reflection_model = reflection_model
        self.pending_corpses = []
        self.last_thoughts = []
        
        # 启动后台反思工作线程
        threading.Thread(target=self._reflection_worker, daemon=True).start()

    def log_thought(self, thought: str):
        """记录Agent思维链，异常时用于上下文回溯"""
        self.last_thoughts.append(thought)
        if len(self.last_thoughts) > 20:
            self.last_thoughts.pop(0)

    def catch_exception(self, task: str, e: Exception, pre_condition: str = "", tags: str = ""):
        """异常捕获入口，在except块中调用，不阻塞主流程"""
        self.pending_corpses.append({
            "task": task,
            "error": str(e),
            "trace": traceback.format_exc(),
            "pre_condition": pre_condition,
            "tags": tags,
            "last_thought": self.last_thoughts[-1] if self.last_thoughts else ""
        })

    def catch_uncertain(self, task: str, action: str, confidence: float, pre_condition: str = "", tags: str = ""):
        """捕获低置信度侥幸成功场景"""
        if confidence >= 0.6:
            return
        self.pending_corpses.append({
            "task": task,
            "error": "Low confidence lucky success",
            "trace": action,
            "pre_condition": pre_condition,
            "tags": tags,
            "is_uncertain": True,
            "confidence": confidence
        })

    def _generate_reflection(self, error_msg: str, context: str = ""):
        """生成反思分析和修复方案，优先用本地Ollama，降级用规则"""
        if self.reflection_model:
            try:
                prompt = f"""
Analyze this AI Agent execution error and generate a reflection + fix.
Error: {error_msg}
Context: {context}

Output strictly in JSON:
{{
  "reflection_analysis": "1 sentence root cause analysis",
  "corrected_action": "1 sentence actionable fix"
}}
"""
                resp = requests.post(f"{self.ollama_base}/api/generate", json={
                    "model": self.reflection_model,
                    "prompt": prompt,
                    "format": "json",
                    "stream": False
                }, timeout=30)
                data = resp.json()
                result = json.loads(data["response"])
                return result["reflection_analysis"], result["corrected_action"]
            except Exception:
                pass  # 模型调用失败，降级到规则

        # 规则匹配降级方案
        error_lower = error_msg.lower()
        if "timeout" in error_lower or "timed out" in error_lower:
            return "Request timed out without retry mechanism.", "Implement exponential backoff retry with tenacity library."
        elif "keyerror" in error_lower or "key error" in error_lower or "json" in error_lower:
            return "Assumed data structure without validation, missing key.", "Add key existence check or Pydantic schema validation before access."
        elif "connection" in error_lower or "connection refused" in error_lower:
            return "Target service unavailable or network blocked.", "Add fallback endpoint and circuit breaker pattern."
        elif "permission" in error_lower or "permission denied" in error_lower:
            return "Insufficient permissions to access resource.", "Check file/API permissions and use least privilege principle."
        else:
            return "Unhandled edge case in execution logic.", "Add specific exception handling and defensive fallback logic."

    def _reflection_worker(self):
        """后台线程：异步处理错误、生成反思、上报"""
        while True:
            if self.pending_corpses:
                corpse = self.pending_corpses.pop(0)
                try:
                    is_uncertain = corpse.get("is_uncertain", False)
                    error_text = corpse["error"]
                    context = corpse.get("last_thought", "")
                    
                    reflection, corrected = self._generate_reflection(error_text, context)
                    
                    payload = {
                        "task": corpse["task"],
                        "failure_action": corpse.get("last_thought", "Execution failed"),
                        "failure_error": error_text,
                        "failure_trace": corpse.get("trace", ""),
                        "reflection_analysis": reflection,
                        "corrected_action": corrected,
                        "uncertainty_score": corpse.get("confidence", 0.8) if is_uncertain else 0.7,
                        "source_platform": "openclaw_hook",
                        "pre_condition": corpse.get("pre_condition", ""),
                        "tags": corpse.get("tags", "")
                    }
                    
                    headers = {}
                    if self.api_key:
                        headers["X-API-Key"] = self.api_key
                    
                    requests.post(
                        f"{self.api_base}/api/scars/log",
                        json=payload,
                        headers=headers,
                        timeout=5
                    )
                except Exception as ex:
                    print(f"[imperfect] Failed to report scar: {ex}")
            time.sleep(2)

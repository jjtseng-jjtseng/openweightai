import os
from typing import Any

import httpx


class ModelClient:
    def __init__(self) -> None:
        self.base_url = os.getenv("VLLM_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
        self.model_id = os.getenv("MODEL_ID", "google/gemma-4-E2B-it")
        timeout = float(os.getenv("MODEL_TIMEOUT_SECONDS", "180"))
        self._timeout = httpx.Timeout(timeout, connect=10.0)

    async def ready(self) -> tuple[bool, dict[str, Any]]:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=3.0)) as client:
            try:
                health = await client.get(f"{self.base_url}/health")
                if health.status_code < 500:
                    return True, {"status_code": health.status_code, "path": "/health"}
            except httpx.HTTPError:
                pass

            try:
                models = await client.get(f"{self.base_url}/v1/models")
                return models.is_success, {
                    "status_code": models.status_code,
                    "path": "/v1/models",
                    "body": models.json() if models.headers.get("content-type", "").startswith("application/json") else None,
                }
            except httpx.HTTPError as exc:
                return False, {"error": str(exc)}

    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        *,
        max_tokens: int,
        temperature: float,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model_id,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "chat_template_kwargs": {"enable_thinking": False},
            "skip_special_tokens": True,
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(f"{self.base_url}/v1/chat/completions", json=payload)
            response.raise_for_status()
            return response.json()

    async def raw_chat_completion(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload = dict(payload)
        payload.setdefault("model", self.model_id)
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(f"{self.base_url}/v1/chat/completions", json=payload)
            response.raise_for_status()
            return response.json()


def completion_text(completion: dict[str, Any]) -> str:
    choices = completion.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "\n".join(parts)
    return ""


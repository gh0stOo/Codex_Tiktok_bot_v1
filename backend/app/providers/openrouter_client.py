import httpx
from ..config import get_settings

settings = get_settings()


class OpenRouterClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.openrouter_api_key
        self.base_url = settings.openrouter_base_url

    async def complete(self, prompt: str) -> dict:
        if not self.api_key:
            raise RuntimeError("OpenRouter API key not configured")
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {"model": "openrouter/auto", "messages": [{"role": "user", "content": prompt}]}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            message = data["choices"][0]["message"]["content"]
            return {"script": message, "raw": data}

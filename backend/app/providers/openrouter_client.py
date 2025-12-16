import httpx
from typing import Optional, List, Dict
from ..config import get_settings

settings = get_settings()


class OpenRouterClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.openrouter_api_key
        self.base_url = settings.openrouter_base_url

    async def complete(self, prompt: str, max_tokens: int = 4000, model_id: str | None = None) -> dict:
        """
        Führe eine Completion mit OpenRouter aus.
        
        Args:
            prompt: Der Prompt für die Completion
            max_tokens: Maximale Anzahl an Tokens für die Antwort (Standard: 4000)
            model_id: Modell-ID (z.B. "openrouter/auto", "openai/gpt-4o"). Falls None, wird "openrouter/auto" verwendet.
        """
        if not self.api_key:
            raise RuntimeError("OpenRouter API key not configured")
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": model_id or "openai/gpt-4o-mini",  # Standard: GPT-4.0 Mini für Text-Generierung
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens
        }
        async with httpx.AsyncClient(timeout=60) as client:
            try:
                resp = await client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                message = data["choices"][0]["message"]["content"]
                return {"script": message, "raw": data}
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 402:
                    error_detail = "Payment Required"
                    try:
                        error_data = e.response.json()
                        error_detail = error_data.get("error", {}).get("message", "Payment Required")
                    except:
                        pass
                    raise RuntimeError(
                        f"OpenRouter API Fehler 402: {error_detail}. "
                        "Bitte prüfe deinen API-Key und ob du Guthaben auf deinem OpenRouter-Account hast. "
                        "Besuche https://openrouter.ai/ für mehr Informationen."
                    )
                elif e.response.status_code == 401:
                    raise RuntimeError(
                        "OpenRouter API Fehler 401: Ungültiger API-Key. "
                        "Bitte prüfe deinen API-Key im Credentials-Tab."
                    )
                else:
                    error_detail = f"HTTP {e.response.status_code}"
                    try:
                        error_data = e.response.json()
                        error_detail = error_data.get("error", {}).get("message", error_detail)
                    except:
                        pass
                    raise RuntimeError(f"OpenRouter API Fehler: {error_detail}")

    async def list_models(self) -> List[Dict]:
        """Liste alle verfügbaren Modelle von OpenRouter"""
        if not self.api_key:
            raise RuntimeError("OpenRouter API key not configured")
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{self.base_url}/models", headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", [])

    async def get_model_info(self, model_id: str) -> Optional[Dict]:
        """Hole Informationen zu einem spezifischen Modell"""
        models = await self.list_models()
        for model in models:
            if model.get("id") == model_id:
                return model
        return None

import httpx
from typing import Optional, Dict, List
from ..config import get_settings

settings = get_settings()


class VoiceTranslationClient:
    """Basis-Klasse für Voice Translation/Cloning Provider"""
    
    def __init__(self, api_key: str, provider: str):
        self.api_key = api_key
        self.provider = provider
        self.base_url = self._get_base_url(provider)
    
    def _get_base_url(self, provider: str) -> str:
        """Gibt die Base-URL für den Provider zurück"""
        urls = {
            "rask": "https://api.rask.ai/v1",
            "heygen": "https://api.heygen.com/v1",
            "elevenlabs": "https://api.elevenlabs.io/v1",
            "falai": "https://fal.run"
        }
        return urls.get(provider, "")
    
    async def list_models(self) -> List[Dict]:
        """Liste verfügbare Voice Cloning Modelle"""
        if self.provider == "rask":
            return await self._list_rask_models()
        elif self.provider == "heygen":
            return await self._list_heygen_models()
        elif self.provider == "elevenlabs":
            return await self._list_elevenlabs_models()
        elif self.provider == "falai":
            return await self._list_falai_voice_models()
        else:
            return []
    
    async def translate_video(
        self,
        video_url: str,
        target_language: str,
        source_language: Optional[str] = None,
        model_id: Optional[str] = None
    ) -> Dict:
        """
        Übersetze Video mit Voice Cloning (originale Stimme beibehalten)
        
        Returns:
            Dict mit video_url, audio_url, status
        """
        if self.provider == "rask":
            return await self._rask_translate(video_url, target_language, source_language, model_id)
        elif self.provider == "heygen":
            return await self._heygen_translate(video_url, target_language, source_language, model_id)
        elif self.provider == "elevenlabs":
            return await self._elevenlabs_translate(video_url, target_language, source_language, model_id)
        elif self.provider == "falai":
            return await self._falai_translate(video_url, target_language, source_language, model_id)
        else:
            raise RuntimeError(f"Unbekannter Provider: {self.provider}")
    
    # Rask.ai Implementation
    async def _list_rask_models(self) -> List[Dict]:
        """Liste Rask.ai Voice Cloning Modelle"""
        return [
            {
                "id": "rask/voice-clone-v1",
                "name": "Rask Voice Clone v1",
                "provider": "rask",
                "supports_voice_cloning": True,
                "cost_per_minute": 0.20,
                "currency": "USD",
                "description": "Rask.ai Voice Cloning - Übersetzt Video mit originaler Stimme",
                "supported_languages": ["en", "de", "es", "fr", "it", "pt", "ru", "ja", "ko", "zh", "ar", "hi", "nl", "pl", "tr", "sv", "da", "fi", "no", "cs", "hu", "ro", "el", "th", "vi", "id", "ms", "uk", "he", "sk", "bg", "hr", "sr", "sl", "et", "lv", "lt", "mt", "ga", "cy", "is", "mk", "sq", "bs", "be", "eu", "gl", "ca", "oc", "af", "sw", "zu", "xh", "yo", "ig", "ha", "sn", "so", "am", "az", "kk", "ky", "uz", "mn", "my", "ka", "hy", "az", "bn", "gu", "pa", "ta", "te", "ml", "kn", "si", "ne", "sd", "ps", "fa", "ur", "hi", "mr", "as", "or", "bo", "dz", "lo", "km", "my", "th", "vi", "id", "ms", "tl", "jw", "su", "haw", "yi", "co", "br", "ht", "ln", "mg", "mi", "sm", "to", "fj", "ty", "ceb", "ilo", "war", "pam", "bcl"]
            },
            {
                "id": "rask/voice-clone-premium",
                "name": "Rask Voice Clone Premium",
                "provider": "rask",
                "supports_voice_cloning": True,
                "cost_per_minute": 0.50,
                "currency": "USD",
                "description": "Rask.ai Premium Voice Cloning - Höchste Qualität",
                "supported_languages": ["en", "de", "es", "fr", "it", "pt", "ru", "ja", "ko", "zh", "ar", "hi", "nl", "pl", "tr", "sv", "da", "fi", "no", "cs", "hu", "ro", "el", "th", "vi", "id", "ms", "uk", "he", "sk", "bg", "hr", "sr", "sl", "et", "lv", "lt", "mt", "ga", "cy", "is", "mk", "sq", "bs", "be", "eu", "gl", "ca", "oc", "af", "sw", "zu", "xh", "yo", "ig", "ha", "sn", "so", "am", "az", "kk", "ky", "uz", "mn", "my", "ka", "hy", "az", "bn", "gu", "pa", "ta", "te", "ml", "kn", "si", "ne", "sd", "ps", "fa", "ur", "hi", "mr", "as", "or", "bo", "dz", "lo", "km", "my", "th", "vi", "id", "ms", "tl", "jw", "su", "haw", "yi", "co", "br", "ht", "ln", "mg", "mi", "sm", "to", "fj", "ty", "ceb", "ilo", "war", "pam", "bcl"]
            }
        ]
    
    async def _rask_translate(
        self,
        video_url: str,
        target_language: str,
        source_language: Optional[str] = None,
        model_id: Optional[str] = None
    ) -> Dict:
        """Rask.ai Video-Übersetzung mit Voice Cloning"""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "video_url": video_url,
            "target_language": target_language,
            "source_language": source_language or "auto",
            "model": model_id or "rask/voice-clone-v1",
            "preserve_voice": True
        }
        
        async with httpx.AsyncClient(timeout=600.0) as client:
            # Starte Übersetzung
            response = await client.post(
                f"{self.base_url}/translate",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            result = response.json()
            
            # Rask.ai gibt typischerweise eine Job-ID zurück
            job_id = result.get("job_id") or result.get("id")
            if job_id:
                # Polling für Status
                return await self._poll_rask_status(client, job_id, headers)
            
            # Falls direktes Ergebnis
            return {
                "video_url": result.get("video_url") or result.get("url"),
                "audio_url": result.get("audio_url"),
                "status": "completed"
            }
    
    async def _poll_rask_status(
        self,
        client: httpx.AsyncClient,
        job_id: str,
        headers: Dict,
        max_attempts: int = 120,
        poll_interval: float = 5.0
    ) -> Dict:
        """Pollt Rask.ai Übersetzungs-Status"""
        for attempt in range(max_attempts):
            await asyncio.sleep(poll_interval)
            
            try:
                response = await client.get(
                    f"{self.base_url}/jobs/{job_id}",
                    headers=headers
                )
                response.raise_for_status()
                status_data = response.json()
                
                status = status_data.get("status", "pending")
                
                if status == "completed":
                    return {
                        "video_url": status_data.get("video_url") or status_data.get("url"),
                        "audio_url": status_data.get("audio_url"),
                        "status": "completed"
                    }
                elif status == "failed":
                    error = status_data.get("error", "Unbekannter Fehler")
                    raise RuntimeError(f"Rask.ai Übersetzung fehlgeschlagen: {error}")
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    await asyncio.sleep(poll_interval * 2)
                else:
                    raise
        
        raise RuntimeError(f"Rask.ai Übersetzung Timeout nach {max_attempts * poll_interval} Sekunden")
    
    # HeyGen Implementation
    async def _list_heygen_models(self) -> List[Dict]:
        """Liste HeyGen Voice Cloning Modelle"""
        return [
            {
                "id": "heygen/voice-clone-v1",
                "name": "HeyGen Voice Clone v1",
                "provider": "heygen",
                "supports_voice_cloning": True,
                "cost_per_minute": 0.30,
                "currency": "USD",
                "description": "HeyGen Voice Cloning - Video-Übersetzung mit originaler Stimme",
                "supported_languages": ["en", "de", "es", "fr", "it", "pt", "ru", "ja", "ko", "zh", "ar", "hi", "nl", "pl", "tr", "sv", "da", "fi", "no", "cs", "hu", "ro", "el", "th", "vi", "id", "ms", "uk", "he", "sk", "bg", "hr", "sr", "sl", "et", "lv", "lt", "mt", "ga", "cy", "is", "mk", "sq", "bs", "be", "eu", "gl", "ca", "oc", "af", "sw", "zu", "xh", "yo", "ig", "ha", "sn", "so", "am", "az", "kk", "ky", "uz", "mn", "my", "ka", "hy", "az", "bn", "gu", "pa", "ta", "te", "ml", "kn", "si", "ne", "sd", "ps", "fa", "ur", "hi", "mr", "as", "or", "bo", "dz", "lo", "km", "my", "th", "vi", "id", "ms", "tl", "jw", "su", "haw", "yi", "co", "br", "ht", "ln", "mg", "mi", "sm", "to", "fj", "ty", "ceb", "ilo", "war", "pam", "bcl"]
            },
            {
                "id": "heygen/voice-clone-premium",
                "name": "HeyGen Voice Clone Premium",
                "provider": "heygen",
                "supports_voice_cloning": True,
                "cost_per_minute": 0.60,
                "currency": "USD",
                "description": "HeyGen Premium Voice Cloning - Höchste Qualität",
                "supported_languages": ["en", "de", "es", "fr", "it", "pt", "ru", "ja", "ko", "zh", "ar", "hi", "nl", "pl", "tr", "sv", "da", "fi", "no", "cs", "hu", "ro", "el", "th", "vi", "id", "ms", "uk", "he", "sk", "bg", "hr", "sr", "sl", "et", "lv", "lt", "mt", "ga", "cy", "is", "mk", "sq", "bs", "be", "eu", "gl", "ca", "oc", "af", "sw", "zu", "xh", "yo", "ig", "ha", "sn", "so", "am", "az", "kk", "ky", "uz", "mn", "my", "ka", "hy", "az", "bn", "gu", "pa", "ta", "te", "ml", "kn", "si", "ne", "sd", "ps", "fa", "ur", "hi", "mr", "as", "or", "bo", "dz", "lo", "km", "my", "th", "vi", "id", "ms", "tl", "jw", "su", "haw", "yi", "co", "br", "ht", "ln", "mg", "mi", "sm", "to", "fj", "ty", "ceb", "ilo", "war", "pam", "bcl"]
            }
        ]
    
    async def _heygen_translate(
        self,
        video_url: str,
        target_language: str,
        source_language: Optional[str] = None,
        model_id: Optional[str] = None
    ) -> Dict:
        """HeyGen Video-Übersetzung mit Voice Cloning"""
        headers = {"X-API-KEY": self.api_key}
        payload = {
            "video_url": video_url,
            "target_language": target_language,
            "source_language": source_language or "auto",
            "voice_clone": True,
            "model": model_id or "heygen/voice-clone-v1"
        }
        
        async with httpx.AsyncClient(timeout=600.0) as client:
            response = await client.post(
                f"{self.base_url}/video/translate",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            result = response.json()
            
            job_id = result.get("job_id") or result.get("id")
            if job_id:
                return await self._poll_heygen_status(client, job_id, headers)
            
            return {
                "video_url": result.get("video_url") or result.get("url"),
                "audio_url": result.get("audio_url"),
                "status": "completed"
            }
    
    async def _poll_heygen_status(
        self,
        client: httpx.AsyncClient,
        job_id: str,
        headers: Dict,
        max_attempts: int = 120,
        poll_interval: float = 5.0
    ) -> Dict:
        """Pollt HeyGen Übersetzungs-Status"""
        import asyncio
        for attempt in range(max_attempts):
            await asyncio.sleep(poll_interval)
            
            try:
                response = await client.get(
                    f"{self.base_url}/jobs/{job_id}",
                    headers=headers
                )
                response.raise_for_status()
                status_data = response.json()
                
                status = status_data.get("status", "pending")
                
                if status == "completed":
                    return {
                        "video_url": status_data.get("video_url") or status_data.get("url"),
                        "audio_url": status_data.get("audio_url"),
                        "status": "completed"
                    }
                elif status == "failed":
                    error = status_data.get("error", "Unbekannter Fehler")
                    raise RuntimeError(f"HeyGen Übersetzung fehlgeschlagen: {error}")
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    await asyncio.sleep(poll_interval * 2)
                else:
                    raise
        
        raise RuntimeError(f"HeyGen Übersetzung Timeout nach {max_attempts * poll_interval} Sekunden")
    
    # ElevenLabs Implementation
    async def _list_elevenlabs_models(self) -> List[Dict]:
        """Liste ElevenLabs Voice Cloning Modelle"""
        return [
            {
                "id": "elevenlabs/voice-clone-v1",
                "name": "ElevenLabs Voice Clone v1",
                "provider": "elevenlabs",
                "supports_voice_cloning": True,
                "cost_per_minute": 0.18,
                "currency": "USD",
                "description": "ElevenLabs Voice Cloning - Video-Übersetzung mit originaler Stimme",
                "supported_languages": ["en", "de", "es", "fr", "it", "pt", "ru", "ja", "ko", "zh", "ar", "hi", "nl", "pl", "tr", "sv", "da", "fi", "no", "cs", "hu", "ro", "el", "th", "vi", "id", "ms", "uk", "he", "sk", "bg", "hr", "sr", "sl", "et", "lv", "lt", "mt", "ga", "cy", "is", "mk", "sq", "bs", "be", "eu", "gl", "ca", "oc", "af", "sw", "zu", "xh", "yo", "ig", "ha", "sn", "so", "am", "az", "kk", "ky", "uz", "mn", "my", "ka", "hy", "az", "bn", "gu", "pa", "ta", "te", "ml", "kn", "si", "ne", "sd", "ps", "fa", "ur", "hi", "mr", "as", "or", "bo", "dz", "lo", "km", "my", "th", "vi", "id", "ms", "tl", "jw", "su", "haw", "yi", "co", "br", "ht", "ln", "mg", "mi", "sm", "to", "fj", "ty", "ceb", "ilo", "war", "pam", "bcl"]
            }
        ]
    
    async def _elevenlabs_translate(
        self,
        video_url: str,
        target_language: str,
        source_language: Optional[str] = None,
        model_id: Optional[str] = None
    ) -> Dict:
        """ElevenLabs Video-Übersetzung mit Voice Cloning"""
        headers = {"xi-api-key": self.api_key}
        payload = {
            "video_url": video_url,
            "target_language": target_language,
            "source_language": source_language or "auto",
            "voice_clone": True
        }
        
        async with httpx.AsyncClient(timeout=600.0) as client:
            response = await client.post(
                f"{self.base_url}/dubbing",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            result = response.json()
            
            job_id = result.get("dubbing_id") or result.get("id")
            if job_id:
                return await self._poll_elevenlabs_status(client, job_id, headers)
            
            return {
                "video_url": result.get("video_url") or result.get("url"),
                "audio_url": result.get("audio_url"),
                "status": "completed"
            }
    
    async def _poll_elevenlabs_status(
        self,
        client: httpx.AsyncClient,
        job_id: str,
        headers: Dict,
        max_attempts: int = 120,
        poll_interval: float = 5.0
    ) -> Dict:
        """Pollt ElevenLabs Übersetzungs-Status"""
        import asyncio
        for attempt in range(max_attempts):
            await asyncio.sleep(poll_interval)
            
            try:
                response = await client.get(
                    f"{self.base_url}/dubbing/{job_id}",
                    headers=headers
                )
                response.raise_for_status()
                status_data = response.json()
                
                status = status_data.get("status", "pending")
                
                if status == "completed":
                    return {
                        "video_url": status_data.get("video_url") or status_data.get("url"),
                        "audio_url": status_data.get("audio_url"),
                        "status": "completed"
                    }
                elif status == "failed":
                    error = status_data.get("error", "Unbekannter Fehler")
                    raise RuntimeError(f"ElevenLabs Übersetzung fehlgeschlagen: {error}")
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    await asyncio.sleep(poll_interval * 2)
                else:
                    raise
        
        raise RuntimeError(f"ElevenLabs Übersetzung Timeout nach {max_attempts * poll_interval} Sekunden")
    
    # Fal.ai Implementation
    async def _list_falai_voice_models(self) -> List[Dict]:
        """Liste Fal.ai Voice Cloning Modelle (falls verfügbar)"""
        return [
            {
                "id": "fal-ai/voice-clone",
                "name": "Fal.ai Voice Clone",
                "provider": "falai",
                "supports_voice_cloning": True,
                "cost_per_minute": 0.15,
                "currency": "USD",
                "description": "Fal.ai Voice Cloning - Video-Übersetzung mit originaler Stimme",
                "supported_languages": ["en", "de", "es", "fr", "it", "pt", "ru", "ja", "ko", "zh"]
            }
        ]
    
    async def _falai_translate(
        self,
        video_url: str,
        target_language: str,
        source_language: Optional[str] = None,
        model_id: Optional[str] = None
    ) -> Dict:
        """Fal.ai Video-Übersetzung mit Voice Cloning"""
        headers = {"Authorization": f"Key {self.api_key}"}
        payload = {
            "video_url": video_url,
            "target_language": target_language,
            "source_language": source_language or "auto",
            "preserve_voice": True
        }
        
        async with httpx.AsyncClient(timeout=600.0) as client:
            response = await client.post(
                f"{self.base_url}/fal-ai/voice-clone",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            result = response.json()
            
            job_id = result.get("request_id") or result.get("id")
            if job_id:
                return await self._poll_falai_voice_status(client, model_id or "fal-ai/voice-clone", job_id, headers)
            
            return {
                "video_url": result.get("video_url") or result.get("url"),
                "audio_url": result.get("audio_url"),
                "status": "completed"
            }
    
    async def _poll_falai_voice_status(
        self,
        client: httpx.AsyncClient,
        model_id: str,
        job_id: str,
        headers: Dict,
        max_attempts: int = 120,
        poll_interval: float = 5.0
    ) -> Dict:
        """Pollt Fal.ai Voice Cloning Status"""
        import asyncio
        status_url = f"{self.base_url}/{model_id}/status/{job_id}"
        
        for attempt in range(max_attempts):
            await asyncio.sleep(poll_interval)
            
            try:
                response = await client.get(status_url, headers=headers)
                response.raise_for_status()
                status_data = response.json()
                
                status = status_data.get("status", "pending")
                
                if status == "completed":
                    return {
                        "video_url": status_data.get("video_url") or status_data.get("url"),
                        "audio_url": status_data.get("audio_url"),
                        "status": "completed"
                    }
                elif status == "failed":
                    error = status_data.get("error", "Unbekannter Fehler")
                    raise RuntimeError(f"Fal.ai Voice Cloning fehlgeschlagen: {error}")
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    await asyncio.sleep(poll_interval * 2)
                else:
                    raise
        
        raise RuntimeError(f"Fal.ai Voice Cloning Timeout nach {max_attempts * poll_interval} Sekunden")


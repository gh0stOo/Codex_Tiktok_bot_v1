import httpx
from typing import Optional, List, Dict


class FalAIClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://fal.run"

    async def list_models(self) -> List[Dict]:
        """Liste alle verfügbaren Transcription-Modelle von Fal.ai"""
        # Fal.ai bietet verschiedene Whisper-Modelle mit unterschiedlichen Preisen
        # Basierend auf der offiziellen Fal.ai Dokumentation
        transcription_models = [
            {
                "id": "fal-ai/whisper-large-v3",
                "name": "Whisper Large v3 (Empfohlen)",
                "provider": "falai",
                "supports_transcription": True,
                "cost_per_minute": 0.005,  # $0.005 pro Minute
                "currency": "USD",
                "supported_languages": ["auto", "en", "de", "es", "fr", "it", "pt", "ru", "ja", "ko", "zh", "ar", "hi", "nl", "pl", "tr", "sv", "da", "fi", "no", "cs", "hu", "ro", "el", "th", "vi", "id", "ms", "uk", "he", "sk", "bg", "hr", "sr", "sl", "et", "lv", "lt", "mt", "ga", "cy", "is", "mk", "sq", "bs", "be", "eu", "gl", "ca", "oc", "af", "sw", "zu", "xh", "yo", "ig", "ha", "sn", "so", "am", "az", "kk", "ky", "uz", "mn", "my", "ka", "hy", "az", "bn", "gu", "pa", "ta", "te", "ml", "kn", "si", "ne", "sd", "ps", "fa", "ur", "hi", "mr", "as", "or", "bo", "dz", "lo", "km", "my", "th", "vi", "id", "ms", "tl", "jw", "su", "haw", "yi", "co", "br", "ht", "ln", "mg", "mi", "sm", "to", "fj", "ty", "ceb", "ilo", "war", "pam", "bcl", "ceb", "ilo", "war", "pam", "bcl"],
                "description": "OpenAI Whisper Large v3 - Höchste Qualität, unterstützt 99+ Sprachen"
            },
            {
                "id": "fal-ai/whisper-large-v2",
                "name": "Whisper Large v2",
                "provider": "falai",
                "supports_transcription": True,
                "cost_per_minute": 0.004,  # $0.004 pro Minute
                "currency": "USD",
                "supported_languages": ["auto", "en", "de", "es", "fr", "it", "pt", "ru", "ja", "ko", "zh", "ar", "hi", "nl", "pl", "tr", "sv", "da", "fi", "no", "cs", "hu", "ro", "el", "th", "vi", "id", "ms", "uk", "he", "sk", "bg", "hr", "sr", "sl", "et", "lv", "lt", "mt", "ga", "cy", "is", "mk", "sq", "bs", "be", "eu", "gl", "ca", "oc", "af", "sw", "zu", "xh", "yo", "ig", "ha", "sn", "so", "am", "az", "kk", "ky", "uz", "mn", "my", "ka", "hy", "az", "bn", "gu", "pa", "ta", "te", "ml", "kn", "si", "ne", "sd", "ps", "fa", "ur", "hi", "mr", "as", "or", "bo", "dz", "lo", "km", "my", "th", "vi", "id", "ms", "tl", "jw", "su", "haw", "yi", "co", "br", "ht", "ln", "mg", "mi", "sm", "to", "fj", "ty", "ceb", "ilo", "war", "pam", "bcl"],
                "description": "OpenAI Whisper Large v2 - Sehr gute Qualität, unterstützt 99+ Sprachen"
            },
            {
                "id": "fal-ai/whisper-medium",
                "name": "Whisper Medium",
                "provider": "falai",
                "supports_transcription": True,
                "cost_per_minute": 0.003,  # $0.003 pro Minute
                "currency": "USD",
                "supported_languages": ["auto", "en", "de", "es", "fr", "it", "pt", "ru", "ja", "ko", "zh", "ar", "hi", "nl", "pl", "tr", "sv", "da", "fi", "no", "cs", "hu", "ro", "el", "th", "vi", "id", "ms", "uk", "he", "sk", "bg", "hr", "sr", "sl", "et", "lv", "lt", "mt", "ga", "cy", "is", "mk", "sq", "bs", "be", "eu", "gl", "ca", "oc", "af", "sw", "zu", "xh", "yo", "ig", "ha", "sn", "so", "am", "az", "kk", "ky", "uz", "mn", "my", "ka", "hy", "az", "bn", "gu", "pa", "ta", "te", "ml", "kn", "si", "ne", "sd", "ps", "fa", "ur", "hi", "mr", "as", "or", "bo", "dz", "lo", "km", "my", "th", "vi", "id", "ms", "tl", "jw", "su", "haw", "yi", "co", "br", "ht", "ln", "mg", "mi", "sm", "to", "fj", "ty", "ceb", "ilo", "war", "pam", "bcl"],
                "description": "OpenAI Whisper Medium - Gute Balance zwischen Qualität und Kosten"
            },
            {
                "id": "fal-ai/whisper-small",
                "name": "Whisper Small",
                "provider": "falai",
                "supports_transcription": True,
                "cost_per_minute": 0.002,  # $0.002 pro Minute
                "currency": "USD",
                "supported_languages": ["auto", "en", "de", "es", "fr", "it", "pt", "ru", "ja", "ko", "zh", "ar", "hi", "nl", "pl", "tr", "sv", "da", "fi", "no", "cs", "hu", "ro", "el", "th", "vi", "id", "ms", "uk", "he", "sk", "bg", "hr", "sr", "sl", "et", "lv", "lt", "mt", "ga", "cy", "is", "mk", "sq", "bs", "be", "eu", "gl", "ca", "oc", "af", "sw", "zu", "xh", "yo", "ig", "ha", "sn", "so", "am", "az", "kk", "ky", "uz", "mn", "my", "ka", "hy", "az", "bn", "gu", "pa", "ta", "te", "ml", "kn", "si", "ne", "sd", "ps", "fa", "ur", "hi", "mr", "as", "or", "bo", "dz", "lo", "km", "my", "th", "vi", "id", "ms", "tl", "jw", "su", "haw", "yi", "co", "br", "ht", "ln", "mg", "mi", "sm", "to", "fj", "ty", "ceb", "ilo", "war", "pam", "bcl"],
                "description": "OpenAI Whisper Small - Schnell und kostengünstig, unterstützt 99+ Sprachen"
            },
            {
                "id": "fal-ai/whisper-base",
                "name": "Whisper Base",
                "provider": "falai",
                "supports_transcription": True,
                "cost_per_minute": 0.001,  # $0.001 pro Minute
                "currency": "USD",
                "supported_languages": ["auto", "en", "de", "es", "fr", "it", "pt", "ru", "ja", "ko", "zh", "ar", "hi", "nl", "pl", "tr", "sv", "da", "fi", "no", "cs", "hu", "ro", "el", "th", "vi", "id", "ms", "uk", "he", "sk", "bg", "hr", "sr", "sl", "et", "lv", "lt", "mt", "ga", "cy", "is", "mk", "sq", "bs", "be", "eu", "gl", "ca", "oc", "af", "sw", "zu", "xh", "yo", "ig", "ha", "sn", "so", "am", "az", "kk", "ky", "uz", "mn", "my", "ka", "hy", "az", "bn", "gu", "pa", "ta", "te", "ml", "kn", "si", "ne", "sd", "ps", "fa", "ur", "hi", "mr", "as", "or", "bo", "dz", "lo", "km", "my", "th", "vi", "id", "ms", "tl", "jw", "su", "haw", "yi", "co", "br", "ht", "ln", "mg", "mi", "sm", "to", "fj", "ty", "ceb", "ilo", "war", "pam", "bcl"],
                "description": "OpenAI Whisper Base - Schnellste Option, unterstützt 99+ Sprachen"
            }
        ]
        
        # Video-Generierungs-Modelle von Fal.ai (NUR Text-to-Video, nicht Image-to-Video)
        # Preise basieren auf aktuellen fal.ai API-Preisen (Stand: Dezember 2024)
        # Preise pro Sekunde und pro Minute generiertes Video
        video_generation_models = [
            {
                "id": "fal-ai/kling-video/v2.6/pro/text-to-video",
                "name": "Kling 2.6 Pro (Text-to-Video)",
                "provider": "falai",
                "supports_video_generation": True,
                "supports_text_to_video": True,  # Explizit Text-to-Video
                "cost_per_second": 0.28,  # $0.28/Sekunde (Kling 2 Master Video)
                "cost_per_minute": 16.80,  # $16.80/Minute ($0.28 × 60)
                "currency": "USD",
                "description": "Hochwertige Text-zu-Video-Generierung - Erstellt Videos aus Text-Prompts"
            },
            {
                "id": "fal-ai/kling-video/v2.6/text-to-video",
                "name": "Kling 2.6 (Text-to-Video)",
                "provider": "falai",
                "supports_video_generation": True,
                "supports_text_to_video": True,
                "cost_per_second": 0.095,  # Geschätzt basierend auf Standard-Version
                "cost_per_minute": 5.70,  # $5.70/Minute ($0.095 × 60)
                "currency": "USD",
                "description": "Text-zu-Video-Generierung - Standard-Version"
            },
            {
                "id": "fal-ai/kling-video/v2.5/text-to-video",
                "name": "Kling 2.5 (Text-to-Video)",
                "provider": "falai",
                "supports_video_generation": True,
                "supports_text_to_video": True,
                "cost_per_second": 0.08,  # $0.08/Sekunde (ca. €0.08 bei 1:1 Wechselkurs)
                "cost_per_minute": 4.80,  # $4.80/Minute ($0.08 × 60) = ca. €4,80
                "currency": "USD",
                "description": "Text-zu-Video-Generierung - Ältere Version (falls verfügbar)"
            },
            {
                "id": "fal-ai/stable-video-diffusion",
                "name": "Stable Video Diffusion (Text-to-Video)",
                "provider": "falai",
                "supports_video_generation": True,
                "supports_text_to_video": True,
                "cost_per_second": 0.02,  # $0.02/Sekunde (geschätzt)
                "cost_per_minute": 1.20,  # $1.20/Minute ($0.02 × 60)
                "currency": "USD",
                "description": "Günstige Text-zu-Video-Generierung mit Stable Diffusion"
            },
            # Weitere Modelle (falls über Fal.ai verfügbar)
            {
                "id": "fal-ai/veo-3/text-to-video",
                "name": "Veo 3 (Text-to-Video)",
                "provider": "falai",
                "supports_video_generation": True,
                "supports_text_to_video": True,
                "cost_per_second": 0.75,  # $0.75/Sekunde (offizieller fal.ai Preis)
                "cost_per_minute": 45.00,  # $45.00/Minute ($0.75 × 60)
                "currency": "USD",
                "description": "Google Veo 3 - Text-zu-Video-Generierung mit höchster Qualität"
            },
            {
                "id": "fal-ai/veo-3-fast/text-to-video",
                "name": "Veo 3 Fast (Text-to-Video)",
                "provider": "falai",
                "supports_video_generation": True,
                "supports_text_to_video": True,
                "cost_per_second": 0.15,  # Geschätzt: schnellere Variante (ca. $0.15/Sekunde)
                "cost_per_minute": 9.00,  # $9.00/Minute ($0.15 × 60) = ca. €9,00
                "currency": "USD",
                "description": "Google Veo 3 Fast - Schnellere Text-zu-Video-Generierung (falls verfügbar)"
            },
            {
                "id": "fal-ai/hunyuan-video/text-to-video",
                "name": "Hunyuan Video (Text-to-Video)",
                "provider": "falai",
                "supports_video_generation": True,
                "supports_text_to_video": True,
                "cost_per_second": 0.40,  # $0.40/Sekunde (geschätzt)
                "cost_per_minute": 24.00,  # $24.00/Minute ($0.40 × 60)
                "currency": "USD",
                "description": "Tencent Hunyuan Video - Text-zu-Video-Generierung (falls verfügbar)"
            },
            {
                "id": "fal-ai/wan-video/text-to-video",
                "name": "Alibaba Wan Video (Text-to-Video)",
                "provider": "falai",
                "supports_video_generation": True,
                "supports_text_to_video": True,
                "cost_per_second": 0.40,  # $0.40/Sekunde (geschätzt)
                "cost_per_minute": 24.00,  # $24.00/Minute ($0.40 × 60)
                "currency": "USD",
                "description": "Alibaba Wan Video - Text-zu-Video-Generierung (falls verfügbar)"
            },
            {
                "id": "fal-ai/minimax-video-live/text-to-video",
                "name": "MiniMax Video Live (Text-to-Video)",
                "provider": "falai",
                "supports_video_generation": True,
                "supports_text_to_video": True,
                "cost_per_second": 0.50,  # $0.50/Sekunde (geschätzt)
                "cost_per_minute": 30.00,  # $30.00/Minute ($0.50 × 60)
                "currency": "USD",
                "description": "MiniMax Video Live - Text-zu-Video-Generierung (falls verfügbar)"
            },
            {
                "id": "fal-ai/runway-gen-3-alpha/text-to-video",
                "name": "Runway Gen-3 Alpha (Text-to-Video)",
                "provider": "falai",
                "supports_video_generation": True,
                "supports_text_to_video": True,
                "cost_per_second": 0.18,  # $0.18/Sekunde (geschätzt)
                "cost_per_minute": 10.80,  # $10.80/Minute ($0.18 × 60)
                "currency": "USD",
                "description": "Runway Gen-3 Alpha - Text-zu-Video-Generierung (falls über Fal.ai verfügbar)"
            },
            {
                "id": "fal-ai/pika-1.5/text-to-video",
                "name": "Pika 1.5 (Text-to-Video)",
                "provider": "falai",
                "supports_video_generation": True,
                "supports_text_to_video": True,
                "cost_per_second": 0.14,  # $0.14/Sekunde (geschätzt)
                "cost_per_minute": 8.40,  # $8.40/Minute ($0.14 × 60)
                "currency": "USD",
                "description": "Pika 1.5 - Text-zu-Video-Generierung (falls über Fal.ai verfügbar)"
            },
            {
                "id": "fal-ai/luma-dream-machine/text-to-video",
                "name": "Luma Dream Machine (Text-to-Video)",
                "provider": "falai",
                "supports_video_generation": True,
                "supports_text_to_video": True,
                "cost_per_second": 0.12,  # $0.12/Sekunde (geschätzt)
                "cost_per_minute": 7.20,  # $7.20/Minute ($0.12 × 60)
                "currency": "USD",
                "description": "Luma Dream Machine - Text-zu-Video-Generierung (falls über Fal.ai verfügbar)"
            },
            {
                "id": "fal-ai/hailuo-2.3/text-to-video",
                "name": "Hailuo 2.3 (Text-to-Video)",
                "provider": "falai",
                "supports_video_generation": True,
                "supports_text_to_video": True,
                "cost_per_second": 0.10,  # $0.10/Sekunde (geschätzt)
                "cost_per_minute": 6.00,  # $6.00/Minute ($0.10 × 60)
                "currency": "USD",
                "description": "Hailuo 2.3 - Text-zu-Video-Generierung (falls verfügbar)"
            },
            {
                "id": "fal-ai/seedance-1.0-pro/text-to-video",
                "name": "Seedance 1.0 Pro (Text-to-Video)",
                "provider": "falai",
                "supports_video_generation": True,
                "supports_text_to_video": True,
                "cost_per_second": 0.09,  # $0.09/Sekunde (geschätzt)
                "cost_per_minute": 5.40,  # $5.40/Minute ($0.09 × 60)
                "currency": "USD",
                "description": "Seedance 1.0 Pro - Text-zu-Video-Generierung (falls verfügbar)"
            }
        ]
        
        # Filtere nur Modelle die Text-to-Video unterstützen (nicht nur Image-to-Video)
        text_to_video_models = [m for m in video_generation_models if m.get("supports_text_to_video", False)]
        
        # Kombiniere Transcription und Video-Generierungs-Modelle
        return transcription_models + text_to_video_models

    async def transcribe(self, audio_url: str, model_id: str = "fal-ai/whisper", language: Optional[str] = None) -> Dict:
        """Transkribiere Audio mit Fal.ai"""
        if not self.api_key:
            raise RuntimeError("Fal.ai API key not configured")
        
        headers = {"Authorization": f"Key {self.api_key}"}
        payload = {
            "audio_url": audio_url,
            "model": model_id,
        }
        if language:
            payload["language"] = language
        
        async with httpx.AsyncClient(timeout=300) as client:
            resp = await client.post(f"{self.base_url}/{model_id}", json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()


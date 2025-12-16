import httpx
from pathlib import Path
from typing import Optional, Dict
import tempfile
import asyncio


class FalAIVideoProvider:
    """Provider für Text-to-Video Generierung mit Fal.ai"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://fal.run"
    
    async def generate_video(
        self, 
        visual_prompt: str, 
        output_path: str,
        model_id: str = "fal-ai/kling-video/v2.6/pro/text-to-video",
        duration: int = 10  # Sekunden
    ) -> Dict[str, str]:
        """
        Generiere Video aus Text-Prompt (visual_prompt)
        
        Args:
            visual_prompt: Detaillierte visuelle Beschreibung für Video-Generierung
            output_path: Pfad wo das Video gespeichert werden soll
            model_id: Fal.ai Modell-ID für Video-Generierung
            duration: Video-Länge in Sekunden (maximal je nach Modell)
        
        Returns:
            Dict mit video_path und thumbnail_path
        """
        if not self.api_key:
            raise RuntimeError("Fal.ai API key not configured")
        
        headers = {"Authorization": f"Key {self.api_key}"}
        
        # Fal.ai API Payload für Text-to-Video
        payload = {
            "prompt": visual_prompt,
            "duration": min(duration, 10),  # Max 10 Sekunden für die meisten Modelle
            "aspect_ratio": "9:16",  # TikTok Format
        }
        
        # Erstelle Output-Verzeichnis falls nicht vorhanden
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                # Starte Video-Generierung
                response = await client.post(
                    f"{self.base_url}/{model_id}",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                result = response.json()
                
                # Fal.ai gibt typischerweise eine Job-ID zurück, dann muss man den Status pollen
                # Oder direkt eine Video-URL wenn synchron
                video_url = result.get("video", {}).get("url") or result.get("video_url") or result.get("url")
                
                if not video_url:
                    # Falls async Job: Polling erforderlich
                    job_id = result.get("request_id") or result.get("id")
                    if job_id:
                        # Polling-Logik
                        video_url = await self._poll_video_status(client, model_id, job_id, headers)
                
                if not video_url:
                    raise RuntimeError("Keine Video-URL von Fal.ai erhalten")
                
                # Lade Video herunter
                video_response = await client.get(video_url)
                video_response.raise_for_status()
                
                # Speichere Video lokal
                with open(output_path, "wb") as f:
                    f.write(video_response.content)
                
                # Generiere Thumbnail (erste Frame)
                thumbnail_path = str(Path(output_path).with_suffix('.jpg'))
                await self._generate_thumbnail(output_path, thumbnail_path)
                
                return {
                    "video_path": output_path,
                    "thumbnail_path": thumbnail_path
                }
        
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Fal.ai API Fehler: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise RuntimeError(f"Video-Generierung Fehler: {str(e)}")
    
    async def _poll_video_status(
        self, 
        client: httpx.AsyncClient, 
        model_id: str, 
        job_id: str, 
        headers: Dict,
        max_attempts: int = 60,
        poll_interval: float = 2.0
    ) -> Optional[str]:
        """Pollt den Status eines async Video-Generierungs-Jobs"""
        status_url = f"{self.base_url}/{model_id}/status/{job_id}"
        
        for attempt in range(max_attempts):
            await asyncio.sleep(poll_interval)
            
            try:
                response = await client.get(status_url, headers=headers)
                response.raise_for_status()
                status_data = response.json()
                
                status = status_data.get("status", "pending")
                
                if status == "completed":
                    video_url = status_data.get("video", {}).get("url") or status_data.get("video_url")
                    if video_url:
                        return video_url
                
                elif status == "failed":
                    error = status_data.get("error", "Unbekannter Fehler")
                    raise RuntimeError(f"Video-Generierung fehlgeschlagen: {error}")
                
                # Status ist noch "pending" oder "processing", weiter pollen
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    # Job nicht gefunden, warte etwas länger
                    await asyncio.sleep(poll_interval * 2)
                else:
                    raise
        
        raise RuntimeError(f"Video-Generierung Timeout nach {max_attempts * poll_interval} Sekunden")
    
    async def _generate_thumbnail(self, video_path: str, thumbnail_path: str):
        """Generiere Thumbnail aus Video (erste Frame)"""
        try:
            from ..config import get_settings
            settings = get_settings()
            ffmpeg_path = settings.ffmpeg_path
            
            if not ffmpeg_path or not Path(ffmpeg_path).exists():
                # Falls FFmpeg nicht verfügbar, verwende Python-Bibliothek
                try:
                    import cv2
                    cap = cv2.VideoCapture(video_path)
                    ret, frame = cap.read()
                    if ret:
                        cv2.imwrite(thumbnail_path, frame)
                    cap.release()
                    return
                except ImportError:
                    pass
            
            # Verwende FFmpeg
            import subprocess
            cmd = [
                ffmpeg_path,
                "-i", video_path,
                "-frames:v", "1",
                "-y",
                thumbnail_path
            ]
            subprocess.run(cmd, check=True, capture_output=True, timeout=10)
        
        except Exception as e:
            # Falls Thumbnail-Generierung fehlschlägt, verwende Platzhalter
            # Erstelle einfaches schwarzes Bild
            try:
                from PIL import Image
                img = Image.new('RGB', (720, 1280), color='black')
                img.save(thumbnail_path)
            except ImportError:
                # Falls PIL nicht verfügbar, lass Thumbnail leer
                Path(thumbnail_path).touch()


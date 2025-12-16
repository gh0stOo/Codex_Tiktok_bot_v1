import subprocess
from pathlib import Path
from ..config import get_settings

settings = get_settings()


class FFmpegVideoProvider:
    def __init__(self, ffmpeg_path: str | None = None):
        self.ffmpeg_path = ffmpeg_path or settings.ffmpeg_path

    def render(self, script: str, output_path: str, thumbnail_path: str) -> dict:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(thumbnail_path).parent.mkdir(parents=True, exist_ok=True)
        
        # FIX: Verwende textfile= statt text= für komplexe Texte mit Sonderzeichen
        # Erstelle temporäre Textdatei für drawtext (vermeidet Escaping-Probleme)
        import tempfile
        import os
        
        # Bereinige Script-Text: Entferne Zeilenumbrüche, kürze auf sinnvolle Länge
        clean_script = " ".join(script.split())[:300]  # Max 300 Zeichen, entferne Zeilenumbrüche
        
        # Erstelle temporäre Textdatei
        text_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
        text_file.write(clean_script)
        text_file.flush()
        text_file_path = text_file.name
        text_file.close()
        
        try:
            # Generate waveform-like background with text overlay
            # Verwende textfile= für bessere Kompatibilität mit Sonderzeichen (Anführungszeichen, etc.)
            # box=1 fügt einen Hintergrund hinzu für bessere Lesbarkeit
            # Verwende absoluten Pfad und escape Sonderzeichen im Pfad
            abs_path = os.path.abspath(text_file_path).replace("\\", "/")
            # Escape Sonderzeichen im Pfad für drawtext (nur Colons müssen escaped werden)
            escaped_path = abs_path.replace(":", "\\:")
            
            drawtext_filter = (
                f"drawtext=textfile={escaped_path}:"
                "fontcolor=white:"
                "fontsize=36:"
                "x=40:"
                "y=H-th-80:"
                "box=1:"
                "boxcolor=black@0.5:"
                "boxborderw=5,"
                "format=yuv420p"
            )
            
            cmd = [
                self.ffmpeg_path,
                "-f", "lavfi",
                "-i", "color=c=black:s=720x1280:d=10",
                "-vf", drawtext_filter,
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-t", "10",  # 10 Sekunden Video
                "-y",
                output_path,
            ]
            
            # FIX: Bessere Fehlerbehandlung mit stderr/stdout
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=60  # 60 Sekunden Timeout
            )
            
            # Thumbnail generieren
            thumb_cmd = [
                self.ffmpeg_path,
                "-i", output_path,
                "-frames:v", "1",
                "-y",
                thumbnail_path
            ]
            subprocess.run(thumb_cmd, check=True, capture_output=True, text=True, timeout=10)
            
            return {"video_path": output_path, "thumbnail_path": thumbnail_path}
        except subprocess.TimeoutExpired:
            raise RuntimeError("FFmpeg timeout: Video-Generierung dauerte zu lange")
        except subprocess.CalledProcessError as e:
            # Bessere Fehlerbehandlung mit vollständiger Fehlermeldung
            error_output = e.stderr if e.stderr else (e.stdout if e.stdout else str(e))
            raise RuntimeError(f"FFmpeg error (exit code {e.returncode}): {error_output}")
        except Exception as e:
            raise RuntimeError(f"Video rendering error: {str(e)}")
        finally:
            # Lösche temporäre Textdatei
            try:
                if os.path.exists(text_file_path):
                    os.unlink(text_file_path)
            except Exception:
                pass

import subprocess
from pathlib import Path
from app.providers.base import LLMProvider, VideoProvider, TikTokPublisher, ASRProvider, StorageProvider


class MockLLM(LLMProvider):
    def complete(self, prompt: str) -> dict:
        return {"title": "Mock Creative", "script": "This is a mock script for TikTok.", "cta": "Follow for more!"}


class MockVideoProvider(VideoProvider):
    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self.ffmpeg_path = ffmpeg_path

    def render(self, script: str, output_path: str, thumbnail_path: str) -> dict:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(thumbnail_path).parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            self.ffmpeg_path,
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=640x360:d=2",
            "-vf",
            f"drawtext=text='{script[:30]}':fontcolor=white:x=10:y=H-th-10",
            "-c:v",
            "libx264",
            "-y",
            output_path,
        ]
        subprocess.run(cmd, check=True)
        thumb_cmd = [self.ffmpeg_path, "-i", output_path, "-frames:v", "1", "-y", thumbnail_path]
        subprocess.run(thumb_cmd, check=True)
        return {"video_path": output_path, "thumbnail_path": thumbnail_path}


class MockTikTokPublisher(TikTokPublisher):
    def publish(self, video_path: str, caption: str) -> dict:
        return {"status": "published", "id": f"mock-{Path(video_path).stem}", "caption": caption}


class MockASR(ASRProvider):
    def transcribe(self, video_path: str) -> str:
        return "Mock transcript for " + Path(video_path).name


class LocalStorage(StorageProvider):
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save_bytes(self, path: str, content: bytes) -> str:
        target = self.base_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return str(target)

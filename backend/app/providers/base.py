from typing import Protocol, Any


class LLMProvider(Protocol):
    def complete(self, prompt: str) -> dict:
        ...


class VideoProvider(Protocol):
    def render(self, script: str, output_path: str, thumbnail_path: str) -> dict:
        ...


class TikTokPublisher(Protocol):
    def publish(self, video_path: str, caption: str) -> dict:
        ...


class ASRProvider(Protocol):
    def transcribe(self, video_path: str) -> str:
        ...


class StorageProvider(Protocol):
    def save_bytes(self, path: str, content: bytes) -> str:
        ...

import httpx
from pathlib import Path
from datetime import datetime, timedelta
from ..config import get_settings
from ..security import encrypt_secret, decrypt_secret

settings = get_settings()


class TikTokClient:
    def __init__(self, client_key: str | None = None, client_secret: str | None = None):
        self.client_key = client_key or settings.tiktok_client_key
        self.client_secret = client_secret or settings.tiktok_client_secret
        self.redirect_uri = settings.tiktok_redirect_uri
        self.base = settings.tiktok_api_base.rstrip("/")
        if not self.client_key or not self.client_secret:
            raise RuntimeError("TikTok credentials not configured")

    def oauth_authorize_url(self, state: str) -> str:
        scopes = "video.upload,user.info.basic,video.list"
        return f"{self.base}/platform/oauth/connect?client_key={self.client_key}&scope={scopes}&redirect_uri={self.redirect_uri}&state={state}&response_type=code"

    async def exchange_code(self, code: str) -> dict:
        url = f"{self.base}/oauth/token/"
        data = {
            "client_key": self.client_key,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, data=data)
            resp.raise_for_status()
            return resp.json()

    async def refresh(self, refresh_token: str) -> dict:
        url = f"{self.base}/oauth/refresh_token/"
        data = {"client_key": self.client_key, "client_secret": self.client_secret, "grant_type": "refresh_token", "refresh_token": refresh_token}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, data=data)
            resp.raise_for_status()
            return resp.json()

    async def upload_video(self, access_token: str, open_id: str, video_path: str, caption: str, idempotency_key: str | None = None) -> dict:
        url = f"{self.base}/video/upload/"
        data = {"access_token": access_token, "open_id": open_id, "text": caption, "is_aigc": True}
        headers = {}
        if idempotency_key:
            headers["X-Tt-Idempotency-Id"] = idempotency_key
        async with httpx.AsyncClient(timeout=60) as client:
            # TikTok expects multipart; open file explicitly
            with open(video_path, "rb") as f:
                files = {"video": (Path(video_path).name, f, "video/mp4")}
                resp = await client.post(url, data=data, files=files, headers=headers)
            resp.raise_for_status()
            return resp.json()

    async def upload_video_inbox(self, access_token: str, open_id: str, video_path: str, caption: str, idempotency_key: str | None = None) -> dict:
        """
        Inbox-Fallback (sofern API/Policy es verlangt). Nutzt identischen Endpoint mit Inbox-Flag.
        """
        url = f"{self.base}/video/upload/"
        data = {"access_token": access_token, "open_id": open_id, "text": caption, "is_aigc": True, "post_mode": "inbox"}
        headers = {}
        if idempotency_key:
            headers["X-Tt-Idempotency-Id"] = idempotency_key
        async with httpx.AsyncClient(timeout=60) as client:
            with open(video_path, "rb") as f:
                files = {"video": (Path(video_path).name, f, "video/mp4")}
                resp = await client.post(url, data=data, files=files, headers=headers)
            resp.raise_for_status()
            return resp.json()

    async def get_metrics(self, access_token: str, open_id: str) -> dict:
        url = f"{self.base}/video/list/"
        params = {"access_token": access_token, "open_id": open_id}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()

    async def get_video_status(self, access_token: str, open_id: str, video_id: str) -> dict:
        url = f"{self.base}/video/query/"
        params = {"access_token": access_token, "open_id": open_id, "video_id": video_id}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()

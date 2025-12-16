import httpx
from pathlib import Path
from datetime import datetime, timedelta
import asyncio
from ..config import get_settings
from ..security import encrypt_secret, decrypt_secret
from ..services.rate_limiter import get_rate_limiter
from ..services.retry import RetryStrategy, CircuitBreaker

settings = get_settings()


class TikTokClient:
    def __init__(self, client_key: str | None = None, client_secret: str | None = None, organization_id: str | None = None):
        self.client_key = client_key or settings.tiktok_client_key
        self.client_secret = client_secret or settings.tiktok_client_secret
        self.redirect_uri = settings.tiktok_redirect_uri
        self.base = settings.tiktok_api_base.rstrip("/")
        self.organization_id = organization_id or "default"
        if not self.client_key or not self.client_secret:
            raise RuntimeError("TikTok credentials not configured")
        self.rate_limiter = get_rate_limiter()
        # Circuit Breaker: 5 Fehler = OPEN, 60 Sekunden Timeout
        self.circuit_breaker = CircuitBreaker(failure_threshold=5, timeout=60)

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

        async def _request():
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(url, data=data)
                # Handle rate limit (429)
                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", 60))
                    await asyncio.sleep(retry_after)
                    resp.raise_for_status()
                resp.raise_for_status()
                return resp.json()

        return await RetryStrategy.retry_async(
            _request,
            max_retries=3,
            base_delay=1.0,
            max_delay=60.0,
            circuit_breaker=self.circuit_breaker,
        )

    async def refresh(self, refresh_token: str) -> dict:
        url = f"{self.base}/oauth/refresh_token/"
        data = {"client_key": self.client_key, "client_secret": self.client_secret, "grant_type": "refresh_token", "refresh_token": refresh_token}

        async def _request():
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(url, data=data)
                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", 60))
                    await asyncio.sleep(retry_after)
                    resp.raise_for_status()
                resp.raise_for_status()
                return resp.json()

        return await RetryStrategy.retry_async(
            _request,
            max_retries=3,
            base_delay=1.0,
            max_delay=60.0,
            circuit_breaker=self.circuit_breaker,
        )

    async def upload_video(self, access_token: str, open_id: str, video_path: str, caption: str, idempotency_key: str | None = None) -> dict:
        # Rate limiting: TikTok Upload Limits (ca. 10/min pro Org)
        self.rate_limiter.wait_if_needed(self.organization_id, "upload", tokens=1, capacity=10, refill_rate=10.0 / 60.0)
        
        url = f"{self.base}/video/upload/"
        data = {"access_token": access_token, "open_id": open_id, "text": caption, "is_aigc": True}
        headers = {}
        if idempotency_key:
            headers["X-Tt-Idempotency-Id"] = idempotency_key

        async def _request():
            async with httpx.AsyncClient(timeout=120) as client:  # Längeres Timeout für Uploads
                with open(video_path, "rb") as f:
                    files = {"video": (Path(video_path).name, f, "video/mp4")}
                    resp = await client.post(url, data=data, files=files, headers=headers)
                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", 60))
                    await asyncio.sleep(retry_after)
                    resp.raise_for_status()
                resp.raise_for_status()
                return resp.json()

        return await RetryStrategy.retry_async(
            _request,
            max_retries=3,
            base_delay=2.0,  # Längere Delays für Uploads
            max_delay=120.0,
            circuit_breaker=self.circuit_breaker,
        )

    async def upload_video_inbox(self, access_token: str, open_id: str, video_path: str, caption: str, idempotency_key: str | None = None) -> dict:
        """
        Inbox-Fallback (sofern API/Policy es verlangt). Nutzt identischen Endpoint mit Inbox-Flag.
        """
        # Rate limiting
        self.rate_limiter.wait_if_needed(self.organization_id, "upload", tokens=1, capacity=10, refill_rate=10.0 / 60.0)
        
        url = f"{self.base}/video/upload/"
        data = {"access_token": access_token, "open_id": open_id, "text": caption, "is_aigc": True, "post_mode": "inbox"}
        headers = {}
        if idempotency_key:
            headers["X-Tt-Idempotency-Id"] = idempotency_key

        async def _request():
            async with httpx.AsyncClient(timeout=120) as client:
                with open(video_path, "rb") as f:
                    files = {"video": (Path(video_path).name, f, "video/mp4")}
                    resp = await client.post(url, data=data, files=files, headers=headers)
                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", 60))
                    await asyncio.sleep(retry_after)
                    resp.raise_for_status()
                resp.raise_for_status()
                return resp.json()

        return await RetryStrategy.retry_async(
            _request,
            max_retries=3,
            base_delay=2.0,
            max_delay=120.0,
            circuit_breaker=self.circuit_breaker,
        )

    async def get_metrics(self, access_token: str, open_id: str) -> dict:
        # Rate limiting: Read operations (ca. 100/min)
        self.rate_limiter.wait_if_needed(self.organization_id, "read", tokens=1, capacity=100, refill_rate=100.0 / 60.0)
        
        url = f"{self.base}/video/list/"
        params = {"access_token": access_token, "open_id": open_id}

        async def _request():
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", 60))
                    await asyncio.sleep(retry_after)
                    resp.raise_for_status()
                resp.raise_for_status()
                return resp.json()

        return await RetryStrategy.retry_async(
            _request,
            max_retries=3,
            base_delay=1.0,
            max_delay=60.0,
            circuit_breaker=self.circuit_breaker,
        )

    async def get_video_status(self, access_token: str, open_id: str, video_id: str) -> dict:
        # Rate limiting: Read operations
        self.rate_limiter.wait_if_needed(self.organization_id, "read", tokens=1, capacity=100, refill_rate=100.0 / 60.0)
        
        url = f"{self.base}/video/query/"
        params = {"access_token": access_token, "open_id": open_id, "video_id": video_id}

        async def _request():
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", 60))
                    await asyncio.sleep(retry_after)
                    resp.raise_for_status()
                resp.raise_for_status()
                return resp.json()
    
        return await RetryStrategy.retry_async(
            _request,
            max_retries=3,
            base_delay=1.0,
            max_delay=60.0,
            circuit_breaker=self.circuit_breaker,
        )

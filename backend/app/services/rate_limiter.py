"""
Rate Limiter für TikTok API mit Token-Bucket-Algorithmus.
Verhindert API-Bans durch Rate-Limit-Überschreitungen.
"""
import time
from typing import Dict, Optional
from collections import defaultdict
from threading import Lock
import redis
from ..config import get_settings

settings = get_settings()


class TokenBucket:
    """Token-Bucket für Rate-Limiting einer einzelnen Resource."""

    def __init__(self, capacity: int, refill_rate: float):
        """
        Args:
            capacity: Maximale Anzahl Tokens
            refill_rate: Tokens pro Sekunde
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = float(capacity)
        self.last_refill = time.time()
        self.lock = Lock()

    def consume(self, tokens: int = 1) -> bool:
        """
        Versucht Tokens zu konsumieren.
        Returns:
            True wenn erfolgreich, False wenn nicht genug Tokens verfügbar
        """
        with self.lock:
            self._refill()
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    def wait_time(self, tokens: int = 1) -> float:
        """
        Berechnet Wartezeit bis genug Tokens verfügbar sind.
        Returns:
            Sekunden bis Tokens verfügbar sind
        """
        with self.lock:
            self._refill()
            if self.tokens >= tokens:
                return 0.0
            needed = tokens - self.tokens
            return needed / self.refill_rate

    def _refill(self):
        """Füllt Tokens basierend auf vergangener Zeit auf."""
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now


class RateLimiter:
    """
    Rate Limiter mit Token-Bucket pro Organisation.
    Verwendet Redis für verteilte Umgebungen, fällt zurück auf In-Memory.
    """

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.memory_buckets: Dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(capacity=100, refill_rate=10.0)  # Default: 100 requests, 10/sec
        )
        self.memory_lock = Lock()
        self._init_redis()

    def _init_redis(self):
        """Initialisiert Redis-Client falls verfügbar."""
        try:
            if settings.redis_url:
                self.redis_client = redis.from_url(settings.redis_url, decode_responses=False)
                self.redis_client.ping()
        except Exception:
            self.redis_client = None

    def _get_bucket_key(self, org_id: str, endpoint: str) -> str:
        """Generiert Redis-Key für Bucket."""
        return f"rate_limit:{org_id}:{endpoint}"

    def _redis_consume(self, key: str, capacity: int, refill_rate: float, tokens: int = 1) -> tuple[bool, float]:
        """
        Redis-basierte Token-Bucket-Implementierung.
        Returns:
            (success, wait_time)
        """
        if not self.redis_client:
            return False, 0.0

        try:
            now = time.time()
            bucket_key = f"{key}:tokens"
            last_refill_key = f"{key}:last_refill"

            # Lua-Script für atomare Operation
            lua_script = """
            local tokens_key = KEYS[1]
            local last_refill_key = KEYS[2]
            local capacity = tonumber(ARGV[1])
            local refill_rate = tonumber(ARGV[2])
            local requested = tonumber(ARGV[3])
            local now = tonumber(ARGV[4])

            local tokens = tonumber(redis.call('GET', tokens_key) or capacity)
            local last_refill = tonumber(redis.call('GET', last_refill_key) or now)

            local elapsed = now - last_refill
            tokens = math.min(capacity, tokens + elapsed * refill_rate)

            if tokens >= requested then
                tokens = tokens - requested
                redis.call('SET', tokens_key, tokens)
                redis.call('SET', last_refill_key, now)
                return {1, 0.0}
            else
                local needed = requested - tokens
                local wait_time = needed / refill_rate
                return {0, wait_time}
            end
            """

            result = self.redis_client.eval(
                lua_script,
                2,
                bucket_key,
                last_refill_key,
                str(capacity),
                str(refill_rate),
                str(tokens),
                str(now),
            )
            success = result[0] == 1
            wait_time = result[1] if not success else 0.0
            return success, wait_time
        except Exception:
            # Fallback zu Memory
            return False, 0.0

    def consume(self, org_id: str, endpoint: str, tokens: int = 1, capacity: int = 100, refill_rate: float = 10.0) -> tuple[bool, float]:
        """
        Versucht Tokens zu konsumieren.
        Returns:
            (success, wait_time_seconds)
        """
        if self.redis_client:
            key = self._get_bucket_key(org_id, endpoint)
            success, wait_time = self._redis_consume(key, capacity, refill_rate, tokens)
            if success:
                return True, 0.0
            return False, wait_time

        # Memory-Fallback
        with self.memory_lock:
            bucket_key = f"{org_id}:{endpoint}"
            if bucket_key not in self.memory_buckets:
                self.memory_buckets[bucket_key] = TokenBucket(capacity, refill_rate)
            bucket = self.memory_buckets[bucket_key]
            if bucket.consume(tokens):
                return True, 0.0
            wait_time = bucket.wait_time(tokens)
            return False, wait_time

    def wait_if_needed(self, org_id: str, endpoint: str, tokens: int = 1, capacity: int = 100, refill_rate: float = 10.0):
        """
        Wartet falls nötig, bis Tokens verfügbar sind.
        Blockiert bis Tokens verfügbar sind.
        """
        while True:
            success, wait_time = self.consume(org_id, endpoint, tokens, capacity, refill_rate)
            if success:
                return
            if wait_time > 0:
                time.sleep(min(wait_time, 60.0))  # Max 60 Sekunden warten


# Globale Instanz
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Singleton für Rate Limiter."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


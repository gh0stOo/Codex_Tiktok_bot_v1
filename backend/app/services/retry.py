"""
Retry-Strategien mit Exponential Backoff und Circuit Breaker.
"""
import asyncio
import time
from typing import Callable, TypeVar, Optional, Any
from functools import wraps
import httpx
from datetime import datetime, timedelta

T = TypeVar("T")


class CircuitBreaker:
    """Circuit Breaker Pattern für externe APIs."""

    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        """
        Args:
            failure_threshold: Anzahl Fehler bevor Circuit öffnet
            timeout: Sekunden bis Circuit wieder geschlossen wird
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "closed"  # closed, open, half_open

    def call(self, func: Callable[[], T]) -> T:
        """Führt Funktion aus mit Circuit Breaker."""
        if self.state == "open":
            if self.last_failure_time and datetime.utcnow() - self.last_failure_time > timedelta(seconds=self.timeout):
                self.state = "half_open"
            else:
                raise RuntimeError("Circuit breaker is OPEN")

        try:
            result = func()
            if self.state == "half_open":
                self.state = "closed"
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = datetime.utcnow()
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
            raise e


class RetryStrategy:
    """Retry-Strategie mit Exponential Backoff."""

    @staticmethod
    def exponential_backoff(attempt: int, base_delay: float = 1.0, max_delay: float = 60.0, jitter: bool = True) -> float:
        """
        Berechnet Wartezeit für Exponential Backoff.
        Args:
            attempt: Aktueller Versuch (0-indexed)
            base_delay: Basis-Verzögerung in Sekunden
            max_delay: Maximale Verzögerung
            jitter: Zufällige Variation hinzufügen
        """
        delay = min(base_delay * (2 ** attempt), max_delay)
        if jitter:
            import random
            delay = delay * (0.5 + random.random() * 0.5)  # 50-100% der berechneten Zeit
        return delay

    @staticmethod
    def is_retryable_error(exception: Exception) -> bool:
        """Prüft ob Fehler retryable ist."""
        if isinstance(exception, httpx.HTTPStatusError):
            status = exception.response.status_code
            # Retry bei 429 (Rate Limit), 500, 502, 503, 504
            return status in (429, 500, 502, 503, 504)
        if isinstance(exception, httpx.TimeoutException):
            return True
        if isinstance(exception, httpx.NetworkError):
            return True
        return False

    @staticmethod
    async def retry_async(
        func: Callable[[], Any],
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ) -> Any:
        """
        Führt async Funktion mit Retry aus.
        """
        last_exception = None
        for attempt in range(max_retries + 1):
            try:
                if circuit_breaker:
                    # Circuit breaker für async functions
                    if circuit_breaker.state == "open":
                        if circuit_breaker.last_failure_time and datetime.utcnow() - circuit_breaker.last_failure_time > timedelta(seconds=circuit_breaker.timeout):
                            circuit_breaker.state = "half_open"
                        else:
                            raise RuntimeError("Circuit breaker is OPEN")
                    
                    result = await func()
                    if circuit_breaker.state == "half_open":
                        circuit_breaker.state = "closed"
                        circuit_breaker.failure_count = 0
                    return result
                return await func()
            except Exception as e:
                last_exception = e
                if circuit_breaker:
                    circuit_breaker.failure_count += 1
                    circuit_breaker.last_failure_time = datetime.utcnow()
                    if circuit_breaker.failure_count >= circuit_breaker.failure_threshold:
                        circuit_breaker.state = "open"
                
                if not RetryStrategy.is_retryable_error(e):
                    raise e
                if attempt < max_retries:
                    delay = RetryStrategy.exponential_backoff(attempt, base_delay, max_delay)
                    await asyncio.sleep(delay)
                else:
                    raise e
        raise last_exception or RuntimeError("Retry exhausted")

    @staticmethod
    def retry_sync(
        func: Callable[[], T],
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ) -> T:
        """
        Führt sync Funktion mit Retry aus.
        """
        last_exception = None
        for attempt in range(max_retries + 1):
            try:
                if circuit_breaker:
                    return circuit_breaker.call(func)
                return func()
            except Exception as e:
                last_exception = e
                if not RetryStrategy.is_retryable_error(e):
                    raise e
                if attempt < max_retries:
                    delay = RetryStrategy.exponential_backoff(attempt, base_delay, max_delay)
                    time.sleep(delay)
                else:
                    raise e
        raise last_exception or RuntimeError("Retry exhausted")


def retry_on_failure(max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
    """Decorator für Retry-Logik."""

    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await RetryStrategy.retry_async(
                    lambda: func(*args, **kwargs),
                    max_retries=max_retries,
                    base_delay=base_delay,
                    max_delay=max_delay,
                )

            return async_wrapper
        else:

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                return RetryStrategy.retry_sync(
                    lambda: func(*args, **kwargs),
                    max_retries=max_retries,
                    base_delay=base_delay,
                    max_delay=max_delay,
                )

            return sync_wrapper

    return decorator


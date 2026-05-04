"""In-memory rate limiter for auth endpoints."""

import time
from collections import defaultdict


class RateLimiter:
    """Simple sliding-window rate limiter."""

    def __init__(self, max_requests: int = 5, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._attempts: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str) -> bool:
        now = time.monotonic()
        window_start = now - self.window_seconds
        attempts = self._attempts[key]
        # Prune old attempts
        self._attempts[key] = [t for t in attempts if t > window_start]
        if len(self._attempts[key]) >= self.max_requests:
            return False
        self._attempts[key].append(now)
        return True

    def remaining(self, key: str) -> int:
        now = time.monotonic()
        window_start = now - self.window_seconds
        attempts = [t for t in self._attempts[key] if t > window_start]
        return max(0, self.max_requests - len(attempts))

    def retry_after(self, key: str) -> int:
        now = time.monotonic()
        window_start = now - self.window_seconds
        attempts = [t for t in self._attempts[key] if t > window_start]
        if not attempts:
            return 0
        oldest = min(attempts)
        return max(0, int(oldest + self.window_seconds - now))


# Global limiters
login_limiter = RateLimiter(max_requests=5, window_seconds=60)
register_limiter = RateLimiter(max_requests=3, window_seconds=60)
password_reset_limiter = RateLimiter(max_requests=3, window_seconds=300)

"""
Simple in-memory sliding-window rate limiter.
Good enough for a single-process bot; if you scale to multiple
instances, back this with Redis instead (interface stays the same).
"""
import time
from collections import defaultdict, deque

import config


class RateLimiter:
    def __init__(self, max_calls: int = None, window_seconds: int = None):
        self.max_calls = max_calls or config.RATE_LIMIT_COUNT
        self.window = window_seconds or config.RATE_LIMIT_WINDOW
        self._hits: dict[int, deque] = defaultdict(deque)

    def allow(self, user_id: int) -> tuple[bool, float]:
        """Returns (allowed, seconds_until_retry)."""
        now = time.time()
        q = self._hits[user_id]
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.max_calls:
            retry_after = self.window - (now - q[0])
            return False, max(retry_after, 0)
        q.append(now)
        return True, 0.0


rate_limiter = RateLimiter()

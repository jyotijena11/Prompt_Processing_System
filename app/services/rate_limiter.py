import math
import time

import redis

from app.config import settings


class GlobalRateLimiter:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.limit = settings.provider_rate_limit_per_minute

    def _window_state(self) -> tuple[str, int, int]:
        now = int(time.time())
        window = now // 60
        key = f"provider_rate_limit:{window}"
        seconds_until_reset = max(1, 60 - (now % 60))
        return key, now, seconds_until_reset

    def acquire_or_delay(self) -> tuple[bool, int]:
        """
        Fixed-window counter.
        Returns (allowed, delay_seconds).
        """
        key, now, seconds_until_reset = self._window_state()

        current = self.redis.incr(key)
        if current == 1:
            self.redis.expire(key, 61)

        if current <= self.limit:
            return True, 0

        retry_after = 60 - (now % 60)
        return False, max(1, math.ceil(retry_after))

    def get_usage_snapshot(self) -> dict:
        key, _now, seconds_until_reset = self._window_state()
        current = int(self.redis.get(key) or 0)
        remaining = max(0, self.limit - current)
        usage_percent = round(min(100.0, (current / self.limit) * 100), 2) if self.limit else 0.0
        return {
            "window_key": key,
            "limit_per_minute": self.limit,
            "used_in_current_window": current,
            "remaining_in_current_window": remaining,
            "usage_percent": usage_percent,
            "seconds_until_reset": seconds_until_reset,
        }

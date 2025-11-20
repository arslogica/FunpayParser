import asyncio
import time
from typing import Dict
from random import uniform
import aiohttp

RND_COOLDOWN_RANGE = (5, 15)


class CoolDownManager:
    def __init__(
        self,
        base_url: str,
        min_request_interval: float = None,
        cache_ttl: float = 10.0,
    ) -> None:
        self._min_request_interval = min_request_interval
        self._cache_ttl = cache_ttl

        self._cache: Dict[str, float] = {}  # {domain, monotonic()}
        self.session = aiohttp.ClientSession(
            trust_env=True, raise_for_status=False, base_url=base_url
        )

    # def _generate_session(self, headers) -> None:

    async def session_close(self) -> None:
        if self.session and not self.session.closed:
            await self.session.close()

    def update_req_cache(self, domain: str) -> None:
        self._cache[domain] = time.monotonic()

    def _get_cache(self, domain: str) -> float:
        return self._cache.get(domain, 0.0)

    def _cleanup_cache(self) -> None:
        now = time.monotonic()
        expired = [
            domain
            for domain, last_time in self._cache.items()
            if now - last_time > self._cache_ttl
        ]
        for domain in expired:
            del self._cache[domain]

    async def cooldown(self, domain: str) -> None:
        """
        Waits if less than min_request_interval has passed since the last request to the domain.
        If min_request_interval is not set, it selects a random time from RND_COOLDOWN_RANGE.
        """
        now = time.monotonic()
        last_request_time = self._get_cache(domain)
        self._cleanup_cache()

        if last_request_time:
            elapsed = now - last_request_time

            if self._min_request_interval:
                wait_time = self._min_request_interval - elapsed
            else:
                wait_time = uniform(*RND_COOLDOWN_RANGE) - elapsed

            if wait_time > 0:
                await asyncio.sleep(wait_time)

        self.update_req_cache(domain)


async def main():
    manager = CoolDownManager(min_request_interval=None)

    for i in range(3):
        await manager.cooldown("funpay.com")

    await manager.session_close()


if __name__ == "__main__":
    asyncio.run(main())

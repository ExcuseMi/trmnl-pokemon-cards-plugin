import asyncio
import json
import logging
import time

from redis.asyncio import Redis

log = logging.getLogger(__name__)

FAIL_BACKOFF = 60     # upstream failed and nothing is cached: ask again after a minute
EMPTY_TTL = 3600      # upstream answered, no card matches these filters: remember for an hour
LOCK_WAIT = 10.0      # another request is fetching the same filters: wait for its result


class UpstreamError(Exception):
    """The card source failed (network, 429, 5xx): not the same as an answer without cards."""


class BaseProvider:
    def __init__(self, name: str, redis: Redis):
        self.name = name
        self.redis = redis

    def _cache_key(self, **filters) -> str:
        return f'tcg:{self.name}:cache:v2:{json.dumps(filters, sort_keys=True)}'

    def _lock_key(self, **filters) -> str:
        return f'tcg:{self.name}:lock:v2:{json.dumps(filters, sort_keys=True)}'

    async def get_cached(self, **filters) -> list[dict] | None:
        try:
            data = await self.redis.get(self._cache_key(**filters))
            if data:
                return json.loads(data).get('cards')
        except Exception as exc:
            log.error('Redis get error: %s', exc)
        return None

    async def is_expired(self, ttl_seconds: float, **filters) -> bool:
        try:
            data = await self.redis.get(self._cache_key(**filters))
            if not data:
                return True
            return (time.time() - json.loads(data).get('timestamp', 0)) > ttl_seconds
        except Exception as exc:
            log.error('Redis check error: %s', exc)
            return True

    async def store_cards(self, cards: list[dict], **filters):
        try:
            await self.redis.set(
                self._cache_key(**filters),
                json.dumps({'cards': cards, 'timestamp': time.time()}),
            )
        except Exception as exc:
            log.error('Redis store error: %s', exc)

    async def is_empty_match(self, **filters) -> bool:
        """True when the source answered and no card matches these filters (not a failure)."""
        try:
            data = await self.redis.get(self._cache_key(**filters))
            return bool(data) and json.loads(data).get('empty') is True
        except Exception as exc:
            log.error('Redis get error: %s', exc)
            return False

    async def _wait_for_other_refresh(self, **filters) -> list[dict] | None:
        """Another request holds the lock: its result, not an empty answer while it is still fetching."""
        lock_key = self._lock_key(**filters)
        deadline = time.monotonic() + LOCK_WAIT
        while time.monotonic() < deadline:
            cards = await self.get_cached(**filters)
            if cards or not await self.redis.exists(lock_key):
                break
            await asyncio.sleep(0.25)
        return await self.get_cached(**filters)

    async def refresh(self, **filters) -> list[dict] | None:
        lock_key = self._lock_key(**filters)
        try:
            if not await self.redis.set(lock_key, '1', nx=True, ex=60):
                return await self._wait_for_other_refresh(**filters)
            try:
                failed = False
                try:
                    cards = await self._fetch(**filters)
                except UpstreamError as exc:
                    failed, cards = True, None
                    log.warning('%s: fetch failed filters=%s: %s', self.name, filters, exc)
                if cards:
                    await self.store_cards(cards, **filters)
                    log.info('%s: cached %d cards filters=%s', self.name, len(cards), filters)
                    return cards
                if not failed:
                    log.info('%s: no card matches filters=%s, remembered for %ds', self.name, filters, EMPTY_TTL)
                    await self._store_backoff(EMPTY_TTL, empty=True, **filters)
                    return None
                existing = await self.get_cached(**filters)
                if existing:
                    log.warning('%s: keeping stale cache filters=%s', self.name, filters)
                    return existing
                log.warning('%s: nothing cached filters=%s, backing off %ds', self.name, filters, FAIL_BACKOFF)
                await self._store_backoff(FAIL_BACKOFF, **filters)
                return None
            finally:
                await self.redis.delete(lock_key)
        except Exception as exc:
            log.error('%s: refresh error: %s', self.name, exc)
            return None

    async def _store_backoff(self, backoff: int = FAIL_BACKOFF, empty: bool = False, **filters):
        try:
            await self.redis.set(
                self._cache_key(**filters),
                json.dumps({'cards': [], 'timestamp': time.time(), 'empty': empty}),
                ex=backoff,
            )
        except Exception as exc:
            log.error('Redis backoff store error: %s', exc)

    async def _fetch(self, **filters) -> list[dict] | None:
        raise NotImplementedError

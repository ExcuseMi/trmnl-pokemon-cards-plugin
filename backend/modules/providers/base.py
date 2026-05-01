import json
import logging
import time

from redis.asyncio import Redis

log = logging.getLogger(__name__)


class BaseProvider:
    def __init__(self, name: str, redis: Redis):
        self.name = name
        self.redis = redis

    def _cache_key(self, **filters) -> str:
        return f'tcg:{self.name}:cache:{json.dumps(filters, sort_keys=True)}'

    def _lock_key(self, **filters) -> str:
        return f'tcg:{self.name}:lock:{json.dumps(filters, sort_keys=True)}'

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

    async def refresh(self, **filters) -> list[dict] | None:
        lock_key = self._lock_key(**filters)
        try:
            if not await self.redis.set(lock_key, '1', nx=True, ex=60):
                return await self.get_cached(**filters)
            try:
                cards = await self._fetch(**filters)
                if cards:
                    await self.store_cards(cards, **filters)
                    log.info('%s: cached %d cards filters=%s', self.name, len(cards), filters)
                    return cards
                log.warning('%s: fetch returned nothing filters=%s — backing off 5m', self.name, filters)
                await self._store_backoff(**filters)
                return None
            finally:
                await self.redis.delete(lock_key)
        except Exception as exc:
            log.error('%s: refresh error: %s', self.name, exc)
            return None

    async def _store_backoff(self, **filters, backoff: int = 300):
        try:
            await self.redis.set(
                self._cache_key(**filters),
                json.dumps({'cards': [], 'timestamp': time.time()}),
                ex=backoff,
            )
        except Exception as exc:
            log.error('Redis backoff store error: %s', exc)

    async def _fetch(self, **filters) -> list[dict] | None:
        raise NotImplementedError

import asyncio
import logging
import time

log = logging.getLogger(__name__)

class BaseProvider:
    def __init__(self, name: str):
        self.name = name
        self._cache = {} # Key: filter_tuple, Value: (list_of_cards, timestamp)
        self._locks = {} # Key: filter_tuple, Value: Lock

    def get_current_cards(self, **filters) -> list[dict] | None:
        key = tuple(sorted(filters.items()))
        cached = self._cache.get(key)
        if cached:
            return cached[0]
        return None

    def is_cache_expired(self, ttl_seconds, **filters) -> bool:
        key = tuple(sorted(filters.items()))
        cached = self._cache.get(key)
        if not cached:
            return True
        return (time.time() - cached[1]) > ttl_seconds

    async def refresh_cards(self, **filters) -> list[dict] | None:
        key = tuple(sorted(filters.items()))
        
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
            
        async with self._locks[key]:
            cards = await self._fetch_random_cards(**filters)
            if cards:
                self._cache[key] = (cards, time.time())
                log.info('%s cards refreshed (count: %d) with filters %s', self.name.capitalize(), len(cards), filters)
                return cards
            else:
                log.warning('Failed to fetch %s cards with filters %s', self.name, filters)
                return None

    async def _fetch_random_cards(self, **filters) -> list[dict] | None:
        raise NotImplementedError

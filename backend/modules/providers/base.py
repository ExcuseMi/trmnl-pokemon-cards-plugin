import asyncio
import logging
import time

log = logging.getLogger(__name__)

class BaseProvider:
    def __init__(self, name: str):
        self.name = name
        self._cache = {} # Key: filter_tuple, Value: (card_data, timestamp)
        self._locks = {} # Key: filter_tuple, Value: Lock

    def get_current_card(self, **filters) -> dict | None:
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

    async def refresh_card(self, **filters) -> dict | None:
        key = tuple(sorted(filters.items()))
        
        # Get or create lock for this specific filter combo
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
            
        async with self._locks[key]:
            card = await self._fetch_random_card(**filters)
            if card:
                self._cache[key] = (card, time.time())
                log.info('%s card refreshed with filters %s: %s', self.name.capitalize(), filters, card.get('name'))
                return card
            else:
                log.warning('Failed to fetch a %s card with filters %s', self.name, filters)
                return None

    async def _fetch_random_card(self, **filters) -> dict | None:
        raise NotImplementedError

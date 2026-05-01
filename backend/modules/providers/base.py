import json
import logging
import time
import redis
import os

log = logging.getLogger(__name__)

class BaseProvider:
    def __init__(self, name: str):
        self.name = name
        # Initialize Redis client
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = int(os.getenv('REDIS_PORT', 6379))
        self.redis = redis.Redis(host=redis_host, port=redis_port, db=0, decode_responses=True)

    def _get_cache_key(self, **filters) -> str:
        filter_str = json.dumps(filters, sort_keys=True)
        return f"tcg:{self.name}:cache:{filter_str}"

    def get_current_cards(self, **filters) -> list[dict] | None:
        key = self._get_cache_key(**filters)
        try:
            cached = self.redis.get(key)
            if cached:
                data = json.loads(cached)
                return data.get('cards')
        except Exception as e:
            log.error("Redis error in get_current_cards: %s", e)
        return None

    def is_cache_expired(self, ttl_seconds, **filters) -> bool:
        key = self._get_cache_key(**filters)
        try:
            cached = self.redis.get(key)
            if not cached:
                return True
            data = json.loads(cached)
            timestamp = data.get('timestamp', 0)
            return (time.time() - timestamp) > ttl_seconds
        except Exception as e:
            log.error("Redis error in is_cache_expired: %s", e)
            return True

    async def refresh_cards(self, **filters) -> list[dict] | None:
        # Use Redis as a lock to prevent concurrent refreshes for the same filters
        lock_key = f"tcg:{self.name}:lock:{json.dumps(filters, sort_keys=True)}"
        if self.redis.set(lock_key, "1", nx=True, ex=60): # 1 minute lock
            try:
                cards = await self._fetch_random_cards(**filters)
                if cards:
                    key = self._get_cache_key(**filters)
                    self.redis.set(key, json.dumps({
                        'cards': cards,
                        'timestamp': time.time()
                    }))
                    log.info('%s cards refreshed (count: %d) with filters %s', self.name.capitalize(), len(cards), filters)
                    return cards
                else:
                    log.warning('Failed to fetch %s cards with filters %s', self.name, filters)
                    return None
            finally:
                self.redis.delete(lock_key)
        else:
            # Another process is already refreshing
            return self.get_current_cards(**filters)

    async def _fetch_random_cards(self, **filters) -> list[dict] | None:
        raise NotImplementedError

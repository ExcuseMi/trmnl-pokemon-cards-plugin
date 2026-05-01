import asyncio
import logging

log = logging.getLogger(__name__)

class BaseProvider:
    def __init__(self, name: str):
        self.name = name
        self._current_card = None
        self._lock = asyncio.Lock()

    def get_current_card(self) -> dict | None:
        return self._current_card

    async def refresh_card(self) -> None:
        card = await self._fetch_random_card()
        if card:
            async with self._lock:
                self._current_card = card
            log.info('%s card refreshed: %s', self.name.capitalize(), card.get('name'))
        else:
            log.warning('Failed to fetch a %s card', self.name)

    async def _fetch_random_card(self) -> dict | None:
        raise NotImplementedError

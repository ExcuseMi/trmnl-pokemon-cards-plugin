import asyncio
import logging
import random

import aiohttp

from modules.formatters.card import shape_card
from modules.providers.base import BaseProvider

log = logging.getLogger(__name__)

TCGDEX_API = 'https://api.tcgdex.net/v2/en'
SAMPLE_SIZE = 20


class PokemonProvider(BaseProvider):

    async def _fetch(self, **filters) -> list[dict] | None:
        set_id = filters.get('set_id', '').strip()
        rarity = filters.get('rarity', '').strip()
        ptype = filters.get('pokemon_type', '').strip()

        card_ids = await self._fetch_ids(set_id, rarity, ptype)
        if not card_ids:
            return None

        sample = random.sample(card_ids, min(SAMPLE_SIZE, len(card_ids)))
        results = await asyncio.gather(*[self._fetch_card(cid) for cid in sample], return_exceptions=True)
        cards = [r for r in results if isinstance(r, dict)]
        return cards if cards else None

    async def _fetch_ids(self, set_id: str, rarity: str, ptype: str) -> list[str] | None:
        if set_id:
            url = f'{TCGDEX_API}/sets/{set_id}'
            params = {}
        else:
            url = f'{TCGDEX_API}/cards'
            params = {'category': 'Pokemon'}
            if rarity and rarity.lower() != 'any':
                params['rarity'] = rarity
            if ptype and ptype.lower() != 'any':
                params['types'] = ptype

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    resp.raise_for_status()
                    data = await resp.json()

            cards = data.get('cards', []) if set_id else (data if isinstance(data, list) else [])
            return [c['id'] for c in cards if c.get('id')]
        except Exception as exc:
            log.error('Error fetching card IDs: %s', exc)
            return None

    async def _fetch_card(self, card_id: str) -> dict | None:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f'{TCGDEX_API}/cards/{card_id}',
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
            return shape_card(data)
        except Exception as exc:
            log.warning('Error fetching card %s: %s', card_id, exc)
            return None

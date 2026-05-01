import asyncio
import logging
import random

import aiohttp

from modules.formatters.card import shape_card
from modules.providers.base import BaseProvider

log = logging.getLogger(__name__)

TCGDEX_BASE = 'https://api.tcgdex.net/v2'
SAMPLE_SIZE = 20


def _api(language: str) -> str:
    lang = (language or 'en').strip().lower() or 'en'
    return f'{TCGDEX_BASE}/{lang}'


class PokemonProvider(BaseProvider):

    async def _fetch(self, **filters) -> list[dict] | None:
        set_id = filters.get('set_id', '').strip()
        rarity = filters.get('rarity', '').strip()
        ptype = filters.get('pokemon_type', '').strip()
        language = filters.get('language', 'en')
        api = _api(language)

        card_ids = await self._fetch_ids(api, set_id, rarity, ptype)
        if not card_ids and language != 'en':
            log.info('No cards found for language=%s, falling back to en', language)
            api = _api('en')
            card_ids = await self._fetch_ids(api, set_id, rarity, ptype)
        if not card_ids:
            return None

        sample = random.sample(card_ids, min(SAMPLE_SIZE, len(card_ids)))
        results = await asyncio.gather(*[self._fetch_card(api, cid) for cid in sample], return_exceptions=True)
        cards = [r for r in results if isinstance(r, dict)]
        return cards if cards else None

    async def _fetch_ids(self, api: str, set_id: str, rarity: str, ptype: str) -> list[str] | None:
        if set_id:
            url = f'{api}/sets/{set_id}'
            params = {}
        else:
            url = f'{api}/cards'
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

    async def _fetch_card(self, api: str, card_id: str) -> dict | None:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f'{api}/cards/{card_id}',
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
            return shape_card(data)
        except Exception as exc:
            log.warning('Error fetching card %s: %s', card_id, exc)
            return None

import asyncio
import json
import logging
import random

import aiohttp

from modules.formatters.card import shape_card
from modules.providers.base import BaseProvider
from modules.providers.constants import TCGDEX_BASE, VALID_LANGS, CATEGORY_I18N

log = logging.getLogger(__name__)

CARD_DETAIL_TTL = 86400
ID_CAP = 200

_VALID_LANGS = VALID_LANGS
_CATEGORY_I18N = CATEGORY_I18N


def _api(language: str) -> str:
    lang = (language or '').strip().lower().split()[0] if language else ''
    if lang not in _VALID_LANGS:
        lang = 'en'
    return f'{TCGDEX_BASE}/{lang}'


def _parse_multi(value: str) -> list[str]:
    return [v.strip() for v in (value or '').split(',') if v.strip() and v.strip().lower() != 'any']


class PokemonProvider(BaseProvider):

    async def _fetch(self, **filters) -> list | None:
        set_id = filters.get('set_id', '').strip()
        rarities = _parse_multi(filters.get('rarity', ''))
        ptypes = _parse_multi(filters.get('pokemon_type', ''))
        categories = _parse_multi(filters.get('category', ''))
        language = filters.get('language', 'en')
        api = _api(language)

        card_ids = await self._fetch_ids(api, set_id, rarities, ptypes, categories, language)
        if not card_ids and language != 'en':
            log.info('No cards found for language=%s, falling back to en', language)
            card_ids = await self._fetch_ids(_api('en'), set_id, rarities, ptypes, categories, 'en')
        if not card_ids:
            return None

        if not set_id and len(card_ids) > ID_CAP:
            card_ids = random.sample(card_ids, ID_CAP)

        return card_ids

    async def _fetch_ids(self, api: str, set_id: str, rarities: list[str], ptypes: list[str], categories: list[str], language: str = 'en') -> list[str] | None:
        cat_map = _CATEGORY_I18N.get(language, _CATEGORY_I18N['en'])
        loc_categories = [cat_map.get(c, c) for c in categories]
        if set_id:
            sid_list = [s.strip() for s in set_id.split(',') if s.strip()]
            if len(sid_list) == 1:
                set_ids = set(await self._fetch_ids_single(api, sid_list[0], '', '', '') or [])
            else:
                tasks = [self._fetch_ids_single(api, sid, '', '', '') for sid in sid_list]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                set_ids = set()
                for res in results:
                    if isinstance(res, list):
                        set_ids.update(res)
            if not set_ids:
                return None
            if not rarities and not ptypes and not loc_categories:
                return list(set_ids)
            # Intersect set cards with globally-filtered cards to respect rarity/type/category within the set
            c_list = loc_categories or ['']
            r_list = rarities or ['']
            p_list = ptypes or ['']
            tasks = [self._fetch_ids_single(api, '', c, r, p) for c in c_list for r in r_list for p in p_list]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            filter_ids = set()
            for res in results:
                if isinstance(res, list):
                    filter_ids.update(res)
            combined = list(set_ids & filter_ids)
            return combined if combined else None

        c_list = loc_categories or ['']
        r_list = rarities or ['']
        p_list = ptypes or ['']
        tasks = [self._fetch_ids_single(api, '', c, r, p) for c in c_list for r in r_list for p in p_list]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        seen = {}
        for res in results:
            if isinstance(res, list):
                for i in res:
                    seen[i] = None
        return list(seen) if seen else None

    async def _fetch_ids_single(self, api: str, set_id: str, category: str, rarity: str, ptype: str) -> list[str]:
        if set_id:
            url = f'{api}/sets/{set_id}'
            params = {}
        else:
            url = f'{api}/cards'
            params = {}
            if category:
                params['category'] = category
            if rarity:
                params['rarity'] = rarity
            if ptype:
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
            return []

    async def get_card_detail(self, api: str, card_id: str) -> dict | None:
        cache_key = f'pokemon:card:v5:{card_id}'
        try:
            cached = await self.redis.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass
        card = await self._fetch_card(api, card_id)
        if card:
            try:
                await self.redis.set(cache_key, json.dumps(card), ex=CARD_DETAIL_TTL)
            except Exception:
                pass
        return card

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

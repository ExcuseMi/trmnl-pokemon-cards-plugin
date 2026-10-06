import asyncio
import json
import logging
import random

import aiohttp

from modules.formatters.card import shape_card
from modules.providers.base import BaseProvider, UpstreamError
from modules.providers.constants import TCGDEX_BASE, VALID_LANGS, CATEGORY_I18N

log = logging.getLogger(__name__)

CARD_DETAIL_TTL = 86400
SET_MISSING_TTL = 86400
RETRY_DELAY = 1.0
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

        # an UpstreamError (the source failed) goes up to refresh(); None here means "answered, no such cards"
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
        failed = False

        async def gather_ids(tasks) -> dict:
            nonlocal failed
            seen = {}
            for res in await asyncio.gather(*tasks, return_exceptions=True):
                if isinstance(res, list):
                    for i in res:
                        seen[i] = None
                else:
                    failed = True
            return seen

        c_list = loc_categories or ['']
        r_list = rarities or ['']
        p_list = ptypes or ['']
        if set_id:
            sid_list = [s.strip() for s in set_id.split(',') if s.strip()]
            set_ids = await gather_ids([self._fetch_ids_single(api, sid, '', '', '') for sid in sid_list])
            if not set_ids:
                if failed:
                    raise UpstreamError('set lists failed')
                return None
            if not rarities and not ptypes and not loc_categories:
                return list(set_ids)
            # Intersect set cards with globally-filtered cards to respect rarity/type/category within the set
            filter_ids = await gather_ids(
                [self._fetch_ids_single(api, '', c, r, p) for c in c_list for r in r_list for p in p_list])
            combined = [i for i in set_ids if i in filter_ids]
            if not combined and failed:
                raise UpstreamError('card lists failed')
            if not combined:
                # the set has no card of that rarity, type or category (a new set, 30th-c on 2026-10-06):
                # the set's own cards, not an empty screen
                log.info('No card of set %s matches the other filters, serving the whole set', set_id)
                return list(set_ids)
            return combined

        seen = await gather_ids(
            [self._fetch_ids_single(api, '', c, r, p) for c in c_list for r in r_list for p in p_list])
        if not seen and failed:
            raise UpstreamError('card lists failed')
        return list(seen) if seen else None

    async def _fetch_ids_single(self, api: str, set_id: str, category: str, rarity: str, ptype: str) -> list[str]:
        missing_key = f'pokemon:set404:{api.rsplit("/", 1)[-1]}:{set_id}' if set_id else ''
        if set_id:
            try:
                if await self.redis.get(missing_key):
                    return []
            except Exception:
                pass
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
            data = await self._get_json(url, params)
        except aiohttp.ClientResponseError as exc:
            if exc.status == 404 and set_id:
                # the set does not exist in this language (e.g. B1 in de): skip it for a day
                log.info('Set %s not available at %s, skipping for %ds', set_id, api, SET_MISSING_TTL)
                try:
                    await self.redis.set(missing_key, '1', ex=SET_MISSING_TTL)
                except Exception:
                    pass
                return []
            log.error('Error fetching card IDs: %s', exc)
            raise UpstreamError(str(exc)) from exc
        except Exception as exc:
            log.error('Error fetching card IDs: %s', exc)
            raise UpstreamError(str(exc) or type(exc).__name__) from exc

        cards = data.get('cards', []) if set_id else (data if isinstance(data, list) else [])
        return [c['id'] for c in cards if c.get('id')]

    async def _get_json(self, url: str, params: dict, total: float = 15):
        """One GET, tried again once after a transient failure (network, 429, 5xx), as the card details are."""
        for attempt in range(2):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=total)) as resp:
                        resp.raise_for_status()
                        return await resp.json()
            except Exception as exc:
                transient = not isinstance(exc, aiohttp.ClientResponseError) or exc.status == 429 or exc.status >= 500
                if attempt == 0 and transient:
                    await asyncio.sleep(RETRY_DELAY)
                    continue
                raise

    async def get_card_detail(self, api: str, card_id: str) -> dict | None:
        lang = api.rstrip('/').rsplit('/', 1)[-1]
        cache_key = f'pokemon:card:v6:{lang}:{card_id}'
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

    async def get_cached_card_details(self, api: str, card_ids: list[str]) -> list[dict]:
        """Card details already in Redis, no network: the fallback while TCGdex is down."""
        if not card_ids:
            return []
        lang = api.rstrip('/').rsplit('/', 1)[-1]
        try:
            values = await self.redis.mget([f'pokemon:card:v6:{lang}:{cid}' for cid in card_ids])
        except Exception:
            return []
        cards = []
        for v in values:
            try:
                if v:
                    cards.append(json.loads(v))
            except ValueError:
                pass
        return cards

    async def _fetch_card(self, api: str, card_id: str) -> dict | None:
        for attempt in range(2):
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
                transient = not isinstance(exc, aiohttp.ClientResponseError) or exc.status == 429 or exc.status >= 500
                if attempt == 0 and transient:
                    await asyncio.sleep(RETRY_DELAY)
                    continue
                log.warning('Error fetching card %s: %s', card_id, exc)
                return None
        return None

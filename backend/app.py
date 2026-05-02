import asyncio
import json
import logging
import os
import random

import aiohttp
from quart import Quart, Response, jsonify, request
from redis.asyncio import Redis

from modules.providers.pokemon import PokemonProvider, _api as _pokemon_api, _parse_multi
from modules.utils.ip_whitelist import init_ip_whitelist, require_tiered_access

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
log = logging.getLogger(__name__)

app = Quart(__name__)

REFRESH_HOURS = float(os.getenv('REFRESH_HOURS', '1'))
TCGDEX_SETS_API = 'https://api.tcgdex.net/v2/en'

_redis = Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', '6379')),
    db=0,
    decode_responses=True,
)
_provider = PokemonProvider(name='pokemon', redis=_redis)


@app.before_serving
async def _startup():
    await init_ip_whitelist()
    log.info('Pokémon Cards backend started — cache TTL: %sh', REFRESH_HOURS)


@app.route('/card')
@require_tiered_access(lambda: _redis, prefix='card')
async def card():
    args = dict(request.args)
    set_id = args.get('set_id', '')
    if '::' in set_id:
        set_id = set_id.split('::')[0]
    if set_id == 'most_recent':
        set_id = await _resolve_most_recent_set_id() or ''
    args['set_id'] = set_id
    # Normalize multi-select fields so cache key is order-independent
    args['rarity'] = ','.join(sorted(_parse_multi(args.get('rarity', ''))))
    args['pokemon_type'] = ','.join(sorted(_parse_multi(args.get('pokemon_type', ''))))
    ttl = REFRESH_HOURS * 3600

    if await _provider.is_expired(ttl, **args):
        cached_ids = await _provider.get_cached(**args)
        if cached_ids:
            asyncio.create_task(_provider.refresh(**args))
        else:
            cached_ids = await _provider.refresh(**args)
    else:
        cached_ids = await _provider.get_cached(**args)

    if not cached_ids:
        return jsonify({'error': 'Failed to fetch cards'}), 503

    api = _pokemon_api(args.get('language', 'en'))
    pick = random.sample(cached_ids, min(8, len(cached_ids)))
    results = await asyncio.gather(
        *[_provider.get_card_detail(api, cid) for cid in pick],
        return_exceptions=True,
    )
    selected = [r for r in results if isinstance(r, dict) and r.get('image_large')][:4]

    if not selected:
        return jsonify({'error': 'Failed to fetch cards'}), 503

    await _enrich_release_dates(selected)
    return jsonify({'data': selected})


async def _enrich_release_dates(cards: list) -> None:
    if all(c.get('set_release_date') for c in cards):
        return
    try:
        cached = await _redis.get('pokemon:sets:enriched:v2')
        if not cached:
            return
        release_map = {s['id']: s.get('releaseDate', '') for s in json.loads(cached) if s.get('id')}
    except Exception:
        return
    for card in cards:
        if not card.get('set_release_date'):
            sid = (card.get('id') or '').rsplit('-', 1)[0]
            card['set_release_date'] = release_map.get(sid, '')


async def _fetch_set_detail(session: aiohttp.ClientSession, set_id: str) -> dict:
    try:
        async with session.get(f'{TCGDEX_SETS_API}/sets/{set_id}', timeout=aiohttp.ClientTimeout(total=10)) as resp:
            resp.raise_for_status()
            return await resp.json()
    except Exception as exc:
        log.warning('Could not fetch set detail for %s: %s', set_id, exc)
        return {'id': set_id}


async def _fetch_sets_with_dates():
    async with aiohttp.ClientSession() as session:
        async with session.get(f'{TCGDEX_SETS_API}/sets', timeout=aiohttp.ClientTimeout(total=15)) as resp:
            resp.raise_for_status()
            sets_list = await resp.json()

    async with aiohttp.ClientSession() as session:
        details = await asyncio.gather(*[_fetch_set_detail(session, s['id']) for s in sets_list if s.get('id')])

    return list(details)


@app.route('/sets', methods=['GET', 'POST', 'OPTIONS'])
async def sets():
    if request.method == 'OPTIONS':
        return _cors(Response('', status=204))

    search = await _parse_search()

    cache_key = 'pokemon:sets:enriched:v2'
    raw_sets = None
    try:
        cached = await _redis.get(cache_key)
        if cached:
            raw_sets = json.loads(cached)
    except Exception:
        pass

    if raw_sets is None:
        try:
            raw_sets = await _fetch_sets_with_dates()
            try:
                await _redis.set(cache_key, json.dumps(raw_sets), ex=86400)
            except Exception:
                pass
        except Exception as exc:
            log.error('Error fetching sets: %s', exc)
            return _cors(jsonify({'error': 'Failed to fetch sets'})), 503

    result = _build_sets(raw_sets, search)
    return _cors(Response(json.dumps(result), content_type='application/json'))


async def _parse_search() -> str:
    if request.method == 'POST':
        try:
            body = await request.get_json(silent=True) or {}
            term = body.get('query') or body.get('search') or body.get('q') or ''
            return str(term).lower().strip()
        except Exception:
            pass
    # xhrSelectSearch accumulates query= params per keystroke; take the last non-empty one
    queries = request.args.getlist('query')
    for q in reversed(queries):
        if q.strip():
            return q.lower().strip()
    return request.args.get('q', '').lower().strip()


async def _resolve_most_recent_set_id() -> str | None:
    try:
        cached = await _redis.get('pokemon:sets:enriched:v2')
        raw_sets = json.loads(cached) if cached else await _fetch_sets_with_dates()
    except Exception:
        return None
    best = max((s for s in raw_sets if s.get('releaseDate')), key=lambda s: s['releaseDate'], default=None)
    return best.get('id') if best else None


def _build_sets(raw_sets: list, search: str) -> list:
    result = []
    for s in raw_sets:
        sid = s.get('id', '')
        name = s.get('name', '')
        year_text = ""
        release_date = s.get('releaseDate', '')
        if release_date:
            year = release_date[:4]
            year_text = f" ({year})"
        label = f"{name}{year_text}"
        if not sid or not label:
            continue
        if not search or search in label.lower():
            result.append({'id': sid, 'name': label, '_date': release_date})
    result.sort(key=lambda x: x.pop('_date'), reverse=True)
    if not search or 'most recent' in search:
        result.insert(0, {'id': 'most_recent', 'name': 'Most Recent ★'})
    return result


def _cors(response: Response) -> Response:
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = '*'
    return response


@app.route('/health')
async def health():
    return jsonify({'ok': True})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)

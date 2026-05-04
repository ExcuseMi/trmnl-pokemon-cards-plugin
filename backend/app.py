import asyncio
import json
import logging
import os
import random
from datetime import datetime

import aiohttp
from quart import Quart, Response, jsonify, request
from redis.asyncio import Redis

from modules.providers.pokemon import PokemonProvider, _api as _pokemon_api, _parse_multi, _VALID_LANGS
from modules.utils.ip_whitelist import init_ip_whitelist, require_tiered_access

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
log = logging.getLogger(__name__)

app = Quart(__name__)

REFRESH_HOURS = float(os.getenv('REFRESH_HOURS', '1'))
LOW_CARD_WARNING = int(os.getenv('LOW_CARD_WARNING_THRESHOLD', '10'))
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
    raw_lang = ((args.get('language') or '').strip().lower().split() or [''])[0]
    args['language'] = raw_lang if raw_lang in _VALID_LANGS else 'en'
    set_id = args.get('set_id', '')
    # xhrSelect appends '::label' to every value; strip it first
    if '::' in set_id:
        if set_id.startswith('serie::'):
            parts = set_id.split('::')
            set_id = '::'.join(parts[:2])  # keep 'serie::<id>', drop label
        else:
            set_id = set_id.split('::')[0]
    if set_id == 'most_recent':
        set_id = await _resolve_most_recent_set_id() or ''
    elif set_id in ('last_year', 'current_generation'):
        set_id = await _resolve_multi_set_filter(set_id)
    elif set_id.startswith('serie::'):
        set_id = await _resolve_serie_set_ids(set_id[7:])
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
    resp = {'data': selected}
    if len(cached_ids) < LOW_CARD_WARNING:
        resp['pool_warning'] = len(cached_ids)
    return jsonify(resp)


async def _enrich_release_dates(cards: list) -> None:
    if all(c.get('set_release_date') and c.get('serie_name') for c in cards):
        return
    try:
        cache_key = 'pokemon:sets:enriched:v2'
        cached = await _redis.get(cache_key)
        if cached:
            raw_sets = json.loads(cached)
        else:
            raw_sets = await _fetch_sets_with_dates()
            await _redis.set(cache_key, json.dumps(raw_sets), ex=86400)
        release_map = {s['id']: s.get('releaseDate', '') for s in raw_sets if s.get('id')}
        serie_map = {s['id']: (s.get('serie') or {}).get('name', '') for s in raw_sets if s.get('id')}
    except Exception:
        return
    for card in cards:
        sid = (card.get('id') or '').rsplit('-', 1)[0]
        if not card.get('set_release_date'):
            card['set_release_date'] = release_map.get(sid, '')
        if not card.get('serie_name'):
            card['serie_name'] = serie_map.get(sid, '')


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


async def _resolve_multi_set_filter(filter_name: str) -> str:
    """Resolve 'last_year' or 'current_generation' to a comma-separated string of set IDs."""
    try:
        cache_key = 'pokemon:sets:enriched:v2'
        cached = await _redis.get(cache_key)
        if cached:
            raw_sets = json.loads(cached)
        else:
            raw_sets = await _fetch_sets_with_dates()
            await _redis.set(cache_key, json.dumps(raw_sets), ex=86400)

        if filter_name == 'last_year':
            cutoff = (datetime.now().replace(year=datetime.now().year - 1)).strftime('%Y-%m-%d')
            ids = [s['id'] for s in raw_sets if s.get('releaseDate', '') >= cutoff and s.get('id')]
        elif filter_name == 'current_generation':
            ids = _resolve_current_generation_ids(raw_sets)
        else:
            return ''
        return ','.join(ids)
    except Exception as exc:
        log.error('Error resolving set filter %s: %s', filter_name, exc)
        return ''


def _resolve_current_generation_ids(raw_sets: list) -> list[str]:
    """Return IDs of all sets belonging to the current (most recent) TCG series.

    Series are detected from the 'serie.id' field on each set detail record.
    The current series is whichever has the most-recent first-release date.
    """
    serie_first: dict[str, str] = {}
    for s in raw_sets:
        serie = s.get('serie') or {}
        serie_id = serie.get('id') if isinstance(serie, dict) else None
        release = s.get('releaseDate', '')
        if serie_id and release:
            if serie_id not in serie_first or release < serie_first[serie_id]:
                serie_first[serie_id] = release

    if not serie_first:
        return []

    current_serie = max(serie_first, key=lambda k: serie_first[k])
    return [s['id'] for s in raw_sets if (s.get('serie') or {}).get('id') == current_serie and s.get('id')]


async def _resolve_serie_set_ids(serie_id: str) -> str:
    """Return comma-separated set IDs for all sets belonging to a given serie ID."""
    try:
        cache_key = 'pokemon:sets:enriched:v2'
        cached = await _redis.get(cache_key)
        raw_sets = json.loads(cached) if cached else await _fetch_sets_with_dates()
        ids = [s['id'] for s in raw_sets if (s.get('serie') or {}).get('id') == serie_id and s.get('id')]
        return ','.join(ids)
    except Exception as exc:
        log.error('Error resolving serie %s: %s', serie_id, exc)
        return ''


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
    serie_latest: dict[str, str] = {}
    serie_names: dict[str, str] = {}

    for s in raw_sets:
        sid = s.get('id', '')
        name = s.get('name', '')
        release_date = s.get('releaseDate', '')
        year_text = f" ({release_date[:4]})" if release_date else ''
        label = f"{name}{year_text}"
        if not sid or not label:
            continue

        serie = s.get('serie') or {}
        serie_id = serie.get('id') if isinstance(serie, dict) else None
        if serie_id:
            serie_names.setdefault(serie_id, (serie.get('name') or ''))
            if release_date > serie_latest.get(serie_id, ''):
                serie_latest[serie_id] = release_date

        if not search or search in label.lower():
            result.append({'id': sid, 'name': label, '_date': release_date})

    result.sort(key=lambda x: x.pop('_date'), reverse=True)

    specials = []
    if not search or search in 'most recent ★':
        specials.append({'id': 'most_recent', 'name': 'Most Recent ★'})
    if not search or search in 'all sets in the last year ★':
        specials.append({'id': 'last_year', 'name': 'All Sets In The Last Year ★'})
    if not search or search in 'all sets current generation ★':
        specials.append({'id': 'current_generation', 'name': 'All Sets Current Generation ★'})

    for serie_id in sorted(serie_latest, key=lambda k: serie_latest[k], reverse=True):
        label = f'All {serie_names[serie_id]} Sets ★'
        if not search or search in label.lower():
            specials.append({'id': f'serie::{serie_id}', 'name': label})

    for i, entry in enumerate(specials):
        result.insert(i, entry)
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

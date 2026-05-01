import asyncio
import json
import logging
import os
import random

import aiohttp
from quart import Quart, Response, jsonify, request
from redis.asyncio import Redis

from modules.providers.pokemon import PokemonProvider
from modules.utils.ip_whitelist import init_ip_whitelist, require_tiered_access

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
log = logging.getLogger(__name__)

app = Quart(__name__)

REFRESH_HOURS = float(os.getenv('REFRESH_HOURS', '1'))
TCGDEX_API = 'https://api.tcgdex.net/v2/en'

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
    if '::' in args.get('set_id', ''):
        args['set_id'] = args['set_id'].split('::')[0]
    ttl = REFRESH_HOURS * 3600

    if await _provider.is_expired(ttl, **args):
        cached = await _provider.get_cached(**args)
        if cached:
            asyncio.create_task(_provider.refresh(**args))
        else:
            cached = await _provider.refresh(**args)
    else:
        cached = await _provider.get_cached(**args)

    if not cached:
        return jsonify({'error': 'Failed to fetch cards'}), 503

    selected = random.sample(cached, min(4, len(cached)))
    return jsonify({'data': selected})


@app.route('/sets', methods=['GET', 'POST', 'OPTIONS'])
async def sets():
    if request.method == 'OPTIONS':
        return _cors(Response('', status=204))

    search = await _parse_search()

    cache_key = 'pokemon:sets:raw:v1'
    raw_sets = None
    try:
        cached = await _redis.get(cache_key)
        if cached:
            raw_sets = json.loads(cached)
    except Exception:
        pass

    if raw_sets is None:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'{TCGDEX_API}/sets', timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    resp.raise_for_status()
                    raw_sets = await resp.json()
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


def _build_sets(raw_sets: list, search: str) -> list:
    result = []
    for s in raw_sets:
        sid = s.get('id', '')
        name = s.get('name', '')
        if not sid or not name:
            continue
        if not search or search in name.lower():
            result.append({'id': sid, 'name': name})
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

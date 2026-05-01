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


@app.route('/sets', methods=['GET', 'OPTIONS'])
async def sets():
    if request.method == 'OPTIONS':
        return _cors(Response('', status=204))

    cache_key = 'pokemon:sets:v1'
    try:
        cached = await _redis.get(cache_key)
        if cached:
            return _cors(Response(cached, content_type='application/json'))
    except Exception:
        pass

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{TCGDEX_API}/sets', timeout=aiohttp.ClientTimeout(total=15)) as resp:
                resp.raise_for_status()
                data = await resp.json()

        result = [{s['name']: s['id']} for s in data if s.get('id') and s.get('name')]
        payload = json.dumps(result)
        try:
            await _redis.set(cache_key, payload, ex=86400)
        except Exception:
            pass
        return _cors(Response(payload, content_type='application/json'))
    except Exception as exc:
        log.error('Error fetching sets: %s', exc)
        return jsonify({'error': 'Failed to fetch sets'}), 503


def _cors(response: Response) -> Response:
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = '*'
    return response


@app.route('/health')
async def health():
    return jsonify({'ok': True})


@app.route('/refresh', methods=['POST'])
@require_tiered_access(lambda: _redis, prefix='refresh')
async def manual_refresh():
    args = dict(request.args)
    asyncio.create_task(_provider.refresh(**args))
    return jsonify({'ok': True, 'queued': True})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)

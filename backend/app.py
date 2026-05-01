import asyncio
import logging
import os

from quart import Quart, jsonify, request

from modules.providers.pokemon import PokemonProvider
from modules.providers.mtg import MtgProvider
from modules.providers.yugioh import YugiohProvider
from modules.utils.ip_whitelist import init_ip_whitelist, require_trmnl_ip

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = Quart(__name__)

# Default refresh interval is now 1 hour
REFRESH_HOURS = float(os.getenv('REFRESH_HOURS', '1'))

# Registry of providers
PROVIDERS = {
    'pokemon': PokemonProvider(),
    'mtg': MtgProvider(),
    'yugioh': YugiohProvider()
}

@app.before_serving
async def _startup():
    await init_ip_whitelist()
    # We no longer pre-refresh all at startup because filters are dynamic
    log.info('Backend started. Cache TTL: %s hours', REFRESH_HOURS)


@app.route('/card')
@require_trmnl_ip
async def card():
    # Get all query params as filters
    args = request.args.to_dict()
    game = args.pop('game', 'pokemon').lower()
    
    provider = PROVIDERS.get(game)
    if not provider:
        return jsonify({'error': f'Unsupported game: {game}'}), 400
        
    # Check if we need to refresh (if not in cache or expired)
    ttl_seconds = REFRESH_HOURS * 3600
    if provider.is_cache_expired(ttl_seconds, **args):
        # Trigger background refresh but return current if available (stale-while-revalidate style)
        # Or if no card at all, wait for it
        current = provider.get_current_card(**args)
        if current:
            asyncio.create_task(provider.refresh_card(**args))
            return jsonify(current)
        else:
            # Wait for first fetch
            data = await provider.refresh_card(**args)
            if data:
                return jsonify(data)
            return jsonify({'error': f'Failed to fetch {game} card'}), 503
    
    # Return from cache
    data = provider.get_current_card(**args)
    return jsonify(data)


@app.route('/health')
async def health():
    return jsonify({'ok': True})


@app.route('/refresh', methods=['POST'])
@require_trmnl_ip
async def manual_refresh():
    args = request.args.to_dict()
    game = args.pop('game', 'all').lower()
    
    if game == 'all':
        # This is harder now because of dynamic filters, 
        # but we can refresh everything currently in cache
        for p in PROVIDERS.values():
            for filter_key in list(p._cache.keys()):
                filters = dict(filter_key)
                asyncio.create_task(p.refresh_card(**filters))
    else:
        provider = PROVIDERS.get(game)
        if provider:
            asyncio.create_task(provider.refresh_card(**args))
        else:
            return jsonify({'error': f'Unsupported game: {game}'}), 400
            
    return jsonify({'ok': True, 'queued': True})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)

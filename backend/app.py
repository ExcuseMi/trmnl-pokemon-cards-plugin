import asyncio
import logging
import os
import random

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
        
    ttl_seconds = REFRESH_HOURS * 3600
    
    # Check if cache is expired
    if provider.is_cache_expired(ttl_seconds, **args):
        # Trigger refresh in background or wait if nothing in cache
        cached_cards = provider.get_current_cards(**args)
        if cached_cards:
            asyncio.create_task(provider.refresh_cards(**args))
        else:
            cached_cards = await provider.refresh_cards(**args)
            
    else:
        cached_cards = provider.get_current_cards(**args)
        
    if not cached_cards:
        return jsonify({'error': f'Failed to fetch {game} cards'}), 503
        
    # Return 4 random items from the cached batch
    count = min(4, len(cached_cards))
    selected = random.sample(cached_cards, count)
    
    return jsonify({'data': selected})


@app.route('/health')
async def health():
    return jsonify({'ok': True})


@app.route('/refresh', methods=['POST'])
@require_trmnl_ip
async def manual_refresh():
    args = request.args.to_dict()
    game = args.pop('game', 'all').lower()
    
    if game == 'all':
        for p in PROVIDERS.values():
            # In Redis version, we don't easily list all cached filter combos
            # but we can refresh the 'any' filters at least
            asyncio.create_task(p.refresh_cards())
    else:
        provider = PROVIDERS.get(game)
        if provider:
            asyncio.create_task(provider.refresh_cards(**args))
        else:
            return jsonify({'error': f'Unsupported game: {game}'}), 400
            
    return jsonify({'ok': True, 'queued': True})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)

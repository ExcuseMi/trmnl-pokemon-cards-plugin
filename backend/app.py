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

REFRESH_HOURS = float(os.getenv('REFRESH_HOURS', '3'))

# Registry of providers
PROVIDERS = {
    'pokemon': PokemonProvider(),
    'mtg': MtgProvider(),
    'yugioh': YugiohProvider()
}

async def _scheduler_loop():
    while True:
        await asyncio.sleep(REFRESH_HOURS * 3600)
        for provider in PROVIDERS.values():
            await provider.refresh_card()


@app.before_serving
async def _startup():
    await init_ip_whitelist()
    # Initial refresh for all providers
    await asyncio.gather(*(p.refresh_card() for p in PROVIDERS.values()))
    asyncio.create_task(_scheduler_loop())


@app.route('/card')
@require_trmnl_ip
async def card():
    # Allow specifying game via query param, default to pokemon
    game = request.args.get('game', 'pokemon').lower()
    provider = PROVIDERS.get(game)
    
    if not provider:
        return jsonify({'error': f'Unsupported game: {game}'}), 400
        
    data = provider.get_current_card()
    if data is None:
        return jsonify({'error': f'No {game} card loaded yet'}), 503
    return jsonify(data)


@app.route('/health')
async def health():
    return jsonify({'ok': True})


@app.route('/refresh', methods=['POST'])
@require_trmnl_ip
async def manual_refresh():
    game = request.args.get('game', 'all').lower()
    if game == 'all':
        for provider in PROVIDERS.values():
            asyncio.create_task(provider.refresh_card())
    else:
        provider = PROVIDERS.get(game)
        if provider:
            asyncio.create_task(provider.refresh_card())
        else:
            return jsonify({'error': f'Unsupported game: {game}'}), 400
            
    return jsonify({'ok': True, 'queued': True})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)

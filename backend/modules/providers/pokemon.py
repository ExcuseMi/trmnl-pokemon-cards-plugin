import random
import aiohttp
import logging
from modules.formatters.card import shape_card
from modules.providers.base import BaseProvider

log = logging.getLogger(__name__)

TCGDEX_API = 'https://api.tcgdex.net/v2/en'

class PokemonProvider(BaseProvider):
    def __init__(self):
        super().__init__('pokemon')

    async def _fetch_random_card(self, **filters) -> dict | None:
        set_id = filters.get('set_id', '').strip()
        rarity = filters.get('rarity', '').strip()
        ptype = filters.get('pokemon_type', '').strip()

        params = {}
        url = f'{TCGDEX_API}/cards'

        if set_id:
            url = f'{TCGDEX_API}/sets/{set_id}'
        else:
            params['category'] = 'Pokemon'
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

                    if not cards:
                        return None

                    selected_brief = random.choice(cards)
                    card_id = selected_brief['id']

                    async with session.get(f'{TCGDEX_API}/cards/{card_id}', timeout=aiohttp.ClientTimeout(total=15)) as resp_detail:
                        resp_detail.raise_for_status()
                        full_card = await resp_detail.json()
                        
                        mapped_card = {
                            'id': full_card.get('id', ''),
                            'name': full_card.get('name', ''),
                            'hp': str(full_card.get('hp', '')),
                            'types': full_card.get('types', []),
                            'rarity': full_card.get('rarity', ''),
                            'set': {
                                'name': full_card.get('set', {}).get('name', ''),
                                'series': ''
                            },
                            'images': {
                                'large': f"{full_card.get('image', '')}/high.png",
                                'small': f"{full_card.get('image', '')}/low.png"
                            }
                        }
                        return shape_card(mapped_card)
        except Exception as exc:
            log.error('Error fetching Pokemon card: %s', exc)
            return None

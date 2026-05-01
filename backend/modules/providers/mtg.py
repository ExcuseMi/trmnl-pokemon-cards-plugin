import aiohttp
import logging
from modules.formatters.card import shape_card
from modules.providers.base import BaseProvider

log = logging.getLogger(__name__)

SCRYFALL_SEARCH_API = 'https://api.scryfall.com/cards/search'

class MtgProvider(BaseProvider):
    def __init__(self):
        super().__init__('mtg')

    async def _fetch_random_cards(self, **filters) -> list[dict] | None:
        try:
            # For MTG, we'll fetch a batch of cards based on some general criteria
            # to minimize calls. Since there are no specific filters yet, we'll just get 'standard' cards
            # or some other large pool.
            params = {
                'q': 'f:standard', # Fetch cards legal in standard for a decent pool
                'order': 'random'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(SCRYFALL_SEARCH_API, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                    
                    if 'data' not in data:
                        return None
                        
                    results = []
                    for full_card in data['data']:
                        hp = ''
                        if 'power' in full_card and 'toughness' in full_card:
                            hp = f"{full_card['power']}/{full_card['toughness']}"
                        elif 'mana_cost' in full_card:
                            hp = full_card['mana_cost']

                        mapped_card = {
                            'id': full_card.get('id', ''),
                            'name': full_card.get('name', ''),
                            'hp': hp,
                            'types': full_card.get('type_line', '').split(' — '),
                            'rarity': full_card.get('rarity', '').capitalize(),
                            'set': {
                                'name': full_card.get('set_name', ''),
                                'image': '', # Icons require another call or pre-fetching
                                'series': ''
                            },
                            'images': {
                                'large': full_card.get('image_uris', {}).get('large', ''),
                                'small': full_card.get('image_uris', {}).get('small', '')
                            }
                        }
                        results.append(shape_card(mapped_card))
                    return results
        except Exception as exc:
            log.error('Error fetching MTG cards: %s', exc)
            return None

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

    async def _fetch_random_cards(self, **filters) -> list[dict] | None:
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
                    
                    all_cards = data.get('cards', []) if set_id else (data if isinstance(data, list) else [])

                    if not all_cards:
                        return None

                    # Return all cards found in this single call
                    # Map them to the simplified structure TCGdex returns in lists
                    # Note: TCGdex lists don't include full stats like HP, but they have id, name, and image URL.
                    # To minimize API calls as requested, we use what's in the list.
                    
                    results = []
                    for full_card in all_cards:
                        # TCGdex list items have 'image' which is the base URL
                        # and other basic info. We'll map what we can.
                        
                        set_info = full_card.get('set', {})
                        set_id_val = set_info.get('id', '')
                        
                        mapped_card = {
                            'id': full_card.get('id', ''),
                            'name': full_card.get('name', ''),
                            'hp': str(full_card.get('hp', '')), # Might be empty in list
                            'types': full_card.get('types', []),
                            'rarity': full_card.get('rarity', ''),
                            'set': {
                                'name': set_info.get('name', ''),
                                'image': f"{set_info.get('logo')}.png" if set_info.get('logo') else ""
                            },
                            'images': {
                                'large': f"{full_card.get('image', '')}/high.png",
                                'small': f"{full_card.get('image', '')}/low.png"
                            }
                        }
                        results.append(shape_card(mapped_card))
                    
                    return results
                    
        except Exception as exc:
            log.error('Error fetching Pokemon cards: %s', exc)
            return None

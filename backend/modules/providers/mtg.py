import aiohttp
import logging
from modules.formatters.card import shape_card
from modules.providers.base import BaseProvider

log = logging.getLogger(__name__)

SCRYFALL_API = 'https://api.scryfall.com/cards/random'

class MtgProvider(BaseProvider):
    def __init__(self):
        super().__init__('mtg')

    async def _fetch_random_card(self, **filters) -> dict | None:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(SCRYFALL_API, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    resp.raise_for_status()
                    full_card = await resp.json()
                    
                    # For MTG, we map Power/Toughness to HP field if it's a creature
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
                            'series': ''
                        },
                        'images': {
                            'large': full_card.get('image_uris', {}).get('large', ''),
                            'small': full_card.get('image_uris', {}).get('small', '')
                        }
                    }
                    return shape_card(mapped_card)
        except Exception as exc:
            log.error('Error fetching MTG card: %s', exc)
            return None

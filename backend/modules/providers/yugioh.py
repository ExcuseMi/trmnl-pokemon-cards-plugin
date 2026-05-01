import random
import aiohttp
import logging
from modules.formatters.card import shape_card
from modules.providers.base import BaseProvider

log = logging.getLogger(__name__)

YGO_API = 'https://db.ygoprodeck.com/api/v7/cardinfo.php'

class YugiohProvider(BaseProvider):
    def __init__(self):
        super().__init__('yugioh')
        self.total_cards = 14000 # Fallback

    async def _fetch_random_card(self, **filters) -> dict | None:
        try:
            async with aiohttp.ClientSession() as session:
                # First, get a random card by using offset
                # We'll use a large enough range and adjust if we can get the real total
                offset = random.randint(0, self.total_cards)
                params = {'num': 1, 'offset': offset}
                
                async with session.get(YGO_API, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    resp.raise_for_status()
                    result = await resp.json()
                    
                    if not result.get('data'):
                        return None
                    
                    full_card = result['data'][0]
                    
                    # Update total cards for next time
                    if 'meta' in result:
                        self.total_cards = result['meta'].get('total_rows', self.total_cards)

                    # For YGO, we map ATK/DEF to HP field
                    hp = ''
                    if 'atk' in full_card and 'def' in full_card:
                        hp = f"{full_card['atk']}/{full_card['def']}"
                    elif 'level' in full_card:
                        hp = f"Lvl {full_card['level']}"

                    # Get rarity from first set if available
                    rarity = ''
                    if full_card.get('card_sets'):
                        rarity = full_card['card_sets'][0].get('set_rarity', '')

                    mapped_card = {
                        'id': str(full_card.get('id', '')),
                        'name': full_card.get('name', ''),
                        'hp': hp,
                        'types': [full_card.get('race', ''), full_card.get('type', '')],
                        'rarity': rarity,
                        'set': {
                            'name': full_card['card_sets'][0].get('set_name', '') if full_card.get('card_sets') else '',
                            'series': ''
                        },
                        'images': {
                            'large': full_card.get('card_images', [{}])[0].get('image_url', ''),
                            'small': full_card.get('card_images', [{}])[0].get('image_url_small', '')
                        }
                    }
                    return shape_card(mapped_card)
        except Exception as exc:
            log.error('Error fetching Yu-Gi-Oh card: %s', exc)
            return None

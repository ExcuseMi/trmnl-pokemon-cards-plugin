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

    async def _fetch_random_cards(self, **filters) -> list[dict] | None:
        try:
            # We fetch all cards in one go. YGOPRODeck allows this.
            # It's a large payload, but it's only 1 API call per TTL.
            async with aiohttp.ClientSession() as session:
                async with session.get(YGO_API, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    resp.raise_for_status()
                    result = await resp.json()
                    
                    if not result.get('data'):
                        return None
                    
                    results = []
                    for full_card in result['data']:
                        hp = ''
                        if 'atk' in full_card and 'def' in full_card:
                            hp = f"{full_card['atk']}/{full_card['def']}"
                        elif 'level' in full_card:
                            hp = f"Lvl {full_card['level']}"

                        rarity = ''
                        set_name = ''
                        if full_card.get('card_sets'):
                            s = full_card['card_sets'][0]
                            set_name = s.get('set_name', '')
                            rarity = s.get('set_rarity', '')

                        mapped_card = {
                            'id': str(full_card.get('id', '')),
                            'name': full_card.get('name', ''),
                            'hp': hp,
                            'types': [full_card.get('race', ''), full_card.get('type', '')],
                            'rarity': rarity,
                            'set': {
                                'name': set_name,
                                'image': '', # Requires set icons pre-fetching
                                'series': ''
                            },
                            'images': {
                                'large': full_card.get('card_images', [{}])[0].get('image_url', ''),
                                'small': full_card.get('card_images', [{}])[0].get('image_url_small', '')
                            }
                        }
                        results.append(shape_card(mapped_card))
                    return results
        except Exception as exc:
            log.error('Error fetching Yu-Gi-Oh cards: %s', exc)
            return None

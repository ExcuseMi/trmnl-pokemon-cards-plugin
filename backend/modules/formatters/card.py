import json
import logging


def shape_card(raw: dict) -> dict:
    types = raw.get('types') or []
    set_info = raw.get('set') or {}
    logo = set_info.get('logo', '')
    image = raw.get('image', '')
    illustrator = raw.get('illustrator', '')
    hp = raw.get('hp')
    variants = raw.get('variants', {})
    abilities = raw.get('abilities', {})
    pricing = raw.get('pricing', {})
    attacks = raw.get('attacks', {})
    dexId = raw.get('dexId')
    set_symbol = set_info.get('symbol', '')
    return {
        'id': raw.get('id', ''),
        'name': raw.get('name', ''),
        'stage': raw.get('stage', ''),
        'hp': str(hp) if hp else '',
        'types': types,
        'rarity': raw.get('rarity', ''),
        'set_name': set_info.get('name', ''),
        'set_logo': f'{logo}.png' if logo else '',
        'set_symbol': f"{set_symbol}.png" if set_symbol else '',
        'image_large': f'{image}/high.png' if image else '',
        'image_small': f'{image}/low.png' if image else '',
        'variants': variants,
        'abilities': abilities,
        'pricing': pricing,
        'attacks': attacks,
        'illustrator': illustrator,
        'dexId': dexId,
    }

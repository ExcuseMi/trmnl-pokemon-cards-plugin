import json
import logging


def _format_price(pricing: dict) -> dict:
    cm = (pricing or {}).get('cardmarket') or {}
    if not cm:
        return {}
    unit = cm.get('unit', '')
    sym = '€' if unit == 'EUR' else ('$' if unit == 'USD' else unit + ' ')

    def fmt(v):
        return f"{sym}{v:.2f}" if v is not None else ''

    return {
        'avg': fmt(cm.get('avg')),
        'avg7': fmt(cm.get('avg7')),
        'avg30': fmt(cm.get('avg30')),
        'low': fmt(cm.get('low')),
        'trend': fmt(cm.get('trend')),
    }


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
    dex_id = raw.get('dexId')
    set_symbol = set_info.get('symbol', '')
    card_count = set_info.get('cardCount', {})
    release_date = set_info.get('releaseDate', '')
    set_year = release_date[:4] if release_date else ''
    return {
        'id': raw.get('id', ''),
        'name': raw.get('name', ''),
        'stage': raw.get('stage', ''),
        'hp': str(hp) if hp else '',
        'types': types,
        'rarity': raw.get('rarity', ''),
        'set_name': set_info.get('name', ''),
        'set_year': set_year,
        'set_logo': f'{logo}.png' if logo else '',
        'set_symbol': f"{set_symbol}.png" if set_symbol else '',
        'image_large': f'{image}/high.png' if image else '',
        'image_small': f'{image}/low.png' if image else '',
        'variants': variants,
        'abilities': abilities,
        'pricing': pricing,
        'attacks': attacks,
        'illustrator': illustrator,
        'dexId': dex_id,
        'retreat': raw.get('retreat'),
        'regulation_mark': raw.get('regulationMark', ''),
        'price': _format_price(pricing),
        'card_count': {
            'official': card_count.get('official'),
            'total': card_count.get('total'),
        },
    }

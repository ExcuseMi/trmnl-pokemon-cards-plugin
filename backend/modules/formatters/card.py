import json
import logging


def _sym(unit: str) -> str:
    return '€' if unit == 'EUR' else ('$' if unit == 'USD' else (unit + ' ' if unit else ''))


def _fmt(sym: str, v) -> str:
    return f"{sym}{v:.2f}" if v is not None else ''


def _format_price(pricing: dict) -> dict:
    result = {}
    pricing = pricing or {}

    cm = pricing.get('cardmarket') or {}
    if cm:
        sym = _sym(cm.get('unit', ''))
        result['avg']  = _fmt(sym, cm.get('avg'))
        result['avg7'] = _fmt(sym, cm.get('avg7'))
        result['low']  = _fmt(sym, cm.get('low'))
        result['trend'] = _fmt(sym, cm.get('trend'))

    tcg = pricing.get('tcgplayer') or {}
    if tcg:
        sym = _sym(tcg.get('unit', ''))
        normal = tcg.get('normal') or {}
        result['tcg_market'] = _fmt(sym, normal.get('marketPrice'))
        result['tcg_low']    = _fmt(sym, normal.get('lowPrice'))

    return result


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
    return {
        'id': raw.get('id', ''),
        'name': raw.get('name', ''),
        'stage': raw.get('stage', ''),
        'hp': str(hp) if hp else '',
        'types': types,
        'rarity': raw.get('rarity', ''),
        'set_name': set_info.get('name', ''),
        'set_release_date': set_info.get('releaseDate', ''),
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

import json
import logging


def _sym(unit: str) -> str:
    return '€' if unit == 'EUR' else ('$' if unit == 'USD' else (unit + ' ' if unit else ''))


def _fmt(sym: str, v) -> str:
    return f"{sym}{v:.2f}" if v is not None else ''


_TCG_META = {'unit', 'updated'}


def _format_price(pricing: dict) -> dict:
    result = {}
    pricing = pricing or {}

    cm = pricing.get('cardmarket') or {}
    if cm:
        sym = _sym(cm.get('unit', ''))
        cm_normal = {
            'avg':   _fmt(sym, cm.get('avg')),
            'avg7':  _fmt(sym, cm.get('avg7')),
            'low':   _fmt(sym, cm.get('low')),
            'trend': _fmt(sym, cm.get('trend')),
        }
        result['cm'] = {'normal': cm_normal}
        if cm.get('avg-holo') is not None:
            result['cm']['holo'] = {
                'avg':  _fmt(sym, cm.get('avg-holo')),
                'avg7': _fmt(sym, cm.get('avg7-holo')),
                'low':  _fmt(sym, cm.get('low-holo')),
            }

    tcg = pricing.get('tcgplayer') or {}
    if tcg:
        sym = _sym(tcg.get('unit', ''))
        variants = {}
        for key, data in tcg.items():
            if key in _TCG_META or not isinstance(data, dict):
                continue
            variants[key] = {
                'market': _fmt(sym, data.get('marketPrice')),
                'low':    _fmt(sym, data.get('lowPrice')),
            }
        if variants:
            result['tcg'] = variants

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
        'localId': raw.get('localId', ''),
        'retreat': raw.get('retreat'),
        'serie_name': '',
        'regulation_mark': raw.get('regulationMark', ''),
        'price': _format_price(pricing),
        'card_count': {
            'official': card_count.get('official'),
            'total': card_count.get('total'),
        },
        'description': raw.get('description',''),
        'evolve_from': raw.get('evolveFrom', '')
    }

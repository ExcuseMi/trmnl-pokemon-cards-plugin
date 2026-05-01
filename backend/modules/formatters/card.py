def shape_card(raw: dict) -> dict:
    types = raw.get('types') or []
    set_info = raw.get('set') or {}
    logo = set_info.get('logo', '')
    image = raw.get('image', '')
    hp = raw.get('hp')
    return {
        'id': raw.get('id', ''),
        'name': raw.get('name', ''),
        'hp': str(hp) if hp else '',
        'types': types,
        'rarity': raw.get('rarity', ''),
        'set_name': set_info.get('name', ''),
        'set_logo': f'{logo}.png' if logo else '',
        'image_large': f'{image}/high.png' if image else '',
        'image_small': f'{image}/low.png' if image else '',
    }

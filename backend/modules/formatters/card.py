def shape_card(raw: dict) -> dict:
    types = raw.get('types') or []
    images = raw.get('images') or {}
    set_info = raw.get('set') or {}
    return {
        'id': raw.get('id', ''),
        'name': raw.get('name', ''),
        'hp': raw.get('hp', ''),
        'types': types,
        'rarity': raw.get('rarity', ''),
        'set_name': set_info.get('name', ''),
        'set_image': set_info.get('image', ''),
        'series': set_info.get('series', ''),
        'image_large': images.get('large', ''),
        'image_small': images.get('small', ''),
    }

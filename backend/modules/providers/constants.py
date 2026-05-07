TCGDEX_BASE = 'https://api.tcgdex.net/v2'

VALID_LANGS = {'en', 'fr', 'es', 'it', 'pt-br', 'de', 'ja', 'zh-tw', 'id', 'th'}

# Category names as returned by each language's /categories endpoint.
# Verified against: GET /v2/{lang}/categories
CATEGORY_I18N: dict[str, dict[str, str]] = {
    'en':    {'Pokemon': 'Pokemon',  'Trainer': 'Trainer',    'Energy': 'Energy'},
    'fr':    {'Pokemon': 'Pokémon',  'Trainer': 'Dresseur',   'Energy': 'Énergie'},
    'es':    {'Pokemon': 'Pokémon',  'Trainer': 'Entrenador', 'Energy': 'Energía'},
    'it':    {'Pokemon': 'Pokémon',  'Trainer': 'Allenatore', 'Energy': 'Energia'},
    'pt-br': {'Pokemon': 'Pokemon',  'Trainer': 'Trainer',    'Energy': 'Energy'},
    'de':    {'Pokemon': 'Pokémon',  'Trainer': 'Trainer',    'Energy': 'Energie'},
    'ja':    {'Pokemon': 'Pokemon',  'Trainer': 'Trainer',    'Energy': 'Energy'},
    'zh-tw': {'Pokemon': 'Pokemon',  'Trainer': 'Trainer',    'Energy': 'Energy'},
    'id':    {'Pokemon': 'Pokemon',  'Trainer': 'Trainer',    'Energy': 'Energy'},
    'th':    {'Pokemon': 'Pokemon',  'Trainer': 'Trainer',    'Energy': 'Energy'},
}

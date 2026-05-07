"""
Integration tests: verify that CATEGORY_I18N maps each language's canonical
category keys to the exact strings the TCGdex API requires.

Two failure modes these tests catch:
  1. TCGdex changes a localized category name (API drift).
  2. We add a language to VALID_LANGS without updating CATEGORY_I18N.
"""

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import pytest

# Import only from the deps-free constants module
sys.path.insert(0, str(Path(__file__).parent.parent))
from modules.providers.constants import CATEGORY_I18N, TCGDEX_BASE, VALID_LANGS

CANONICAL = ['Pokemon', 'Trainer', 'Energy']


def fetch_json(url: str) -> object:
    with urllib.request.urlopen(url, timeout=10) as resp:
        return json.loads(resp.read())


def fetch_categories(lang: str) -> list[str]:
    return fetch_json(f'{TCGDEX_BASE}/{lang}/categories')


def fetch_cards(lang: str, category: str) -> list:
    params = urllib.parse.urlencode({'category': category})
    data = fetch_json(f'{TCGDEX_BASE}/{lang}/cards?{params}')
    return data if isinstance(data, list) else []


# --- Static tests (no network) ---

def test_all_valid_langs_have_i18n_entry():
    """Every language in VALID_LANGS must have an entry in CATEGORY_I18N."""
    missing = VALID_LANGS - set(CATEGORY_I18N)
    assert not missing, f'Languages missing from CATEGORY_I18N: {missing}'


def test_all_canonical_keys_present_for_each_lang():
    """Every language entry must map all three canonical keys."""
    for lang, mapping in CATEGORY_I18N.items():
        for key in CANONICAL:
            assert key in mapping, f"CATEGORY_I18N['{lang}'] missing key '{key}'"


# --- Live API tests ---

@pytest.mark.parametrize('lang', sorted(VALID_LANGS))
def test_category_map_matches_api(lang: str):
    """Our translation map must match every value the API's /categories endpoint returns."""
    api_categories = fetch_categories(lang)
    mapped = set(CATEGORY_I18N[lang].values())
    api_set = set(api_categories)

    missing = api_set - mapped
    assert not missing, (
        f"[{lang}] API returned categories not in our map: {missing}. "
        f"Update CATEGORY_I18N['{lang}']."
    )


@pytest.mark.parametrize('lang', sorted(VALID_LANGS))
@pytest.mark.parametrize('canonical', CANONICAL)
def test_localized_category_returns_results(lang: str, canonical: str):
    """Using the localized category name must return at least one card."""
    localized = CATEGORY_I18N[lang][canonical]
    api_categories = fetch_categories(lang)

    if localized not in api_categories:
        pytest.skip(f'[{lang}] has no {canonical} category')

    cards = fetch_cards(lang, localized)
    assert len(cards) > 0, (
        f"[{lang}] category='{localized}' (canonical '{canonical}') returned no cards. "
        f"Check CATEGORY_I18N['{lang}']['{canonical}']."
    )


@pytest.mark.parametrize('lang', ['fr', 'es', 'it', 'de'])
@pytest.mark.parametrize('canonical', CANONICAL)
def test_english_category_returns_nothing_for_localized_langs(lang: str, canonical: str):
    """English category strings must NOT work on localized API endpoints where the
    name actually differs. If this test starts failing, TCGdex may have made filters
    language-agnostic and the translation map would become unnecessary.
    """
    localized = CATEGORY_I18N[lang][canonical]
    if localized == canonical:
        pytest.skip(f'[{lang}] {canonical!r} is identical in English and {lang} — filter will naturally work')

    cards = fetch_cards(lang, canonical)
    assert len(cards) == 0, (
        f"[{lang}] English category='{canonical}' unexpectedly returned {len(cards)} cards "
        f"(expected localized value '{localized}'). "
        f"TCGdex may now accept English category names — the translation map may be removable."
    )

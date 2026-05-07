"""
Integration tests: verify that _CATEGORY_I18N maps each language's canonical
category keys to the exact strings the TCGdex API requires.

Two failure modes these tests catch:
  1. TCGdex changes a localized category name (API drift).
  2. We add a language to _VALID_LANGS without updating _CATEGORY_I18N.
"""

import pytest
import aiohttp

from modules.providers.pokemon import _CATEGORY_I18N, _VALID_LANGS, TCGDEX_BASE

CANONICAL = ['Pokemon', 'Trainer', 'Energy']


async def _fetch_categories(session: aiohttp.ClientSession, lang: str) -> list[str]:
    url = f'{TCGDEX_BASE}/{lang}/categories'
    async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
        resp.raise_for_status()
        return await resp.json()


async def _fetch_cards(session: aiohttp.ClientSession, lang: str, category: str) -> list:
    url = f'{TCGDEX_BASE}/{lang}/cards'
    async with session.get(url, params={'category': category}, timeout=aiohttp.ClientTimeout(total=10)) as resp:
        resp.raise_for_status()
        data = await resp.json()
        return data if isinstance(data, list) else []


@pytest.mark.asyncio
@pytest.mark.parametrize('lang', sorted(_VALID_LANGS))
async def test_category_map_matches_api(lang: str):
    """Our translation map must match every value the API's /categories endpoint returns."""
    async with aiohttp.ClientSession() as session:
        api_categories = await _fetch_categories(session, lang)

    mapped = set(_CATEGORY_I18N[lang].values())
    api_set = set(api_categories)

    missing = api_set - mapped
    assert not missing, (
        f"[{lang}] API returned categories not in our map: {missing}. "
        f"Update _CATEGORY_I18N['{lang}']."
    )


@pytest.mark.asyncio
@pytest.mark.parametrize('lang', sorted(_VALID_LANGS))
@pytest.mark.parametrize('canonical', CANONICAL)
async def test_localized_category_returns_results(lang: str, canonical: str):
    """Using the localized category name must return at least one card."""
    localized = _CATEGORY_I18N[lang][canonical]
    async with aiohttp.ClientSession() as session:
        api_categories = await _fetch_categories(session, lang)

    # Skip if this language simply doesn't have this category (e.g. pt-br has no Energy)
    if localized not in api_categories:
        pytest.skip(f'[{lang}] has no {canonical} category')

    async with aiohttp.ClientSession() as session:
        cards = await _fetch_cards(session, lang, localized)

    assert len(cards) > 0, (
        f"[{lang}] category='{localized}' (canonical '{canonical}') returned no cards. "
        f"Check _CATEGORY_I18N['{lang}']['{canonical}']."
    )


@pytest.mark.asyncio
@pytest.mark.parametrize('lang', ['fr', 'es', 'it', 'de'])
@pytest.mark.parametrize('canonical', CANONICAL)
async def test_english_category_returns_nothing_for_localized_langs(lang: str, canonical: str):
    """English category strings must NOT work on localized API endpoints.
    If this test starts failing, TCGdex may have made filters language-agnostic
    and the translation map would become unnecessary.
    """
    async with aiohttp.ClientSession() as session:
        cards = await _fetch_cards(session, lang, canonical)

    assert len(cards) == 0, (
        f"[{lang}] English category='{canonical}' unexpectedly returned {len(cards)} cards. "
        f"TCGdex may now accept English category names — the translation map may be removable."
    )


def test_all_valid_langs_have_i18n_entry():
    """Every language in _VALID_LANGS must have an entry in _CATEGORY_I18N."""
    missing = _VALID_LANGS - set(_CATEGORY_I18N)
    assert not missing, f'Languages missing from _CATEGORY_I18N: {missing}'


def test_all_canonical_keys_present_for_each_lang():
    """Every language entry must map all three canonical keys."""
    for lang, mapping in _CATEGORY_I18N.items():
        for key in CANONICAL:
            assert key in mapping, f"_CATEGORY_I18N['{lang}'] missing key '{key}'"

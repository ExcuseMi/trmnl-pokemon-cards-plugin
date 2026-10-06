"""
The /card endpoint and its provider when the card source (TCGdex) fails or has no card for the filters.

Bug 2026-10-06: TRMNL showed "the host replied 503". Three ways led to that 503:
  1. filters that match no card were answered as an outage (503), for ever;
  2. the card lists were fetched without a retry, and one failure blocked the filter for 5 minutes;
  3. a second request for the same new filter got nothing while the first was still fetching.
No network: the source and Redis are fakes.
"""

import asyncio
import os
import sys
import time
from pathlib import Path

import aiohttp
import pytest

os.environ['ACCESS_MODE'] = 'open'
sys.path.insert(0, str(Path(__file__).parent.parent))
from modules.providers import base, pokemon  # noqa: E402
from modules.providers.base import UpstreamError  # noqa: E402
from modules.providers.pokemon import PokemonProvider  # noqa: E402

FILTERS = dict(language='en', set_id='', rarity='Rare', pokemon_type='', category='')


class FakeRedis:
    def __init__(self):
        self.d, self.ex = {}, {}

    async def get(self, k):
        return self.d.get(k)

    async def set(self, k, v, nx=False, ex=None):
        if nx and k in self.d:
            return None
        self.d[k], self.ex[k] = v, ex
        return True

    async def delete(self, k):
        self.d.pop(k, None)

    async def exists(self, k):
        return 1 if k in self.d else 0

    async def mget(self, keys):
        return [self.d.get(k) for k in keys]


def provider(answers):
    """A provider whose source gives `answers` in turn: a list of ids, [] or an Exception to raise."""
    p = PokemonProvider(name='pokemon', redis=FakeRedis())
    calls = []

    async def get_json(url, params, total=15):
        calls.append(url)
        a = answers.pop(0) if len(answers) > 1 else answers[0]
        if isinstance(a, Exception):
            raise a
        return [{'id': i} for i in a]

    p._get_json = get_json
    p.calls = calls
    return p


def http_error(status):
    return aiohttp.ClientResponseError(request_info=None, history=(), status=status, message='x')


def run(coro):
    return asyncio.run(coro)


def test_source_down_and_nothing_cached_is_a_failure_for_a_minute_only():
    p = provider([http_error(503)])
    assert run(p.refresh(**FILTERS)) is None
    assert run(p.is_empty_match(**FILTERS)) is False
    assert p.redis.ex[p._cache_key(**FILTERS)] == base.FAIL_BACKOFF <= 60


def test_filters_without_cards_are_an_answer_not_a_failure():
    p = provider([[]])
    assert run(p.refresh(**FILTERS)) is None
    assert run(p.is_empty_match(**FILTERS)) is True


def test_source_down_keeps_the_cards_cached_before():
    p = provider([http_error(503)])
    run(p.store_cards(['a-1', 'a-2'], **FILTERS))
    assert run(p.refresh(**FILTERS)) == ['a-1', 'a-2']
    assert run(p.is_empty_match(**FILTERS)) is False


def test_some_lists_failing_still_gives_the_cards_of_the_others():
    p = provider([http_error(503), ['b-1']])
    f = dict(FILTERS, rarity='Common,Rare')
    assert run(p.refresh(**f)) == ['b-1']


def test_card_list_is_tried_again_once_after_a_503(monkeypatch):
    monkeypatch.setattr(pokemon, 'RETRY_DELAY', 0)
    seen = []

    class Resp:
        def __init__(self, n):
            self.n = n

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        def raise_for_status(self):
            if self.n == 0:
                raise http_error(503)

        async def json(self):
            return [{'id': 'c-1'}]

    class Session:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        def get(self, url, params=None, timeout=None):
            seen.append(url)
            return Resp(len(seen) - 1)

    monkeypatch.setattr(aiohttp, 'ClientSession', Session)
    p = PokemonProvider(name='pokemon', redis=FakeRedis())
    assert run(p.refresh(**FILTERS)) == ['c-1']
    assert len(seen) == 2


def test_second_request_waits_for_the_first_fetch():
    p = PokemonProvider(name='pokemon', redis=FakeRedis())

    async def slow(url, params, total=15):
        await asyncio.sleep(0.4)
        return [{'id': 'd-1'}]

    p._get_json = slow

    async def both():
        return await asyncio.gather(p.refresh(**FILTERS), p.refresh(**FILTERS))

    assert run(both()) == [['d-1'], ['d-1']]


@pytest.fixture
def client(monkeypatch):
    import app as backend_app
    p = provider([[]])
    monkeypatch.setattr(backend_app, '_provider', p)
    monkeypatch.setattr(backend_app, '_redis', p.redis)
    return backend_app, p


def get_card(backend_app, query='rarity=Rare'):
    async def go():
        async with backend_app.app.test_request_context('/card?' + query):
            return await backend_app.app.make_response(await backend_app.card())
    return run(go())


def test_card_answers_200_and_no_cards_when_the_filters_match_nothing(client):
    backend_app, p = client
    resp = get_card(backend_app)
    assert resp.status_code == 200
    body = run(resp.get_json())
    assert body['data'] == [] and body['empty'] is True


def test_card_answers_503_only_when_the_source_is_down_and_nothing_is_cached(client, monkeypatch):
    backend_app, _ = client
    p = provider([http_error(503)])
    monkeypatch.setattr(backend_app, '_provider', p)
    assert get_card(backend_app).status_code == 503


def test_liquid_error_text_as_a_filter_is_no_filter(client, monkeypatch):
    backend_app, _ = client
    p = provider([['e-1']])
    monkeypatch.setattr(backend_app, '_provider', p)
    seen = {}

    async def is_expired(ttl, **args):
        seen.update(args)
        return True

    p.is_expired = is_expired

    async def no_detail(api, cid):
        return {'id': cid, 'name': 'x', 'image_large': 'http://img', 'set_release_date': 'd', 'serie_name': 's'}

    p.get_card_detail = no_detail
    bad = 'Liquid%20error%20(line%201)%3A%20Internal%20exception'
    resp = get_card(backend_app, f'pokemon_type={bad}&rarity={bad}&category={bad}')
    assert resp.status_code == 200
    assert seen['rarity'] == '' and seen['pokemon_type'] == '' and seen['category'] == ''
    assert run(resp.get_json())['data'][0]['id'] == 'e-1'


def test_a_set_without_cards_of_the_chosen_rarity_shows_the_set():
    p = PokemonProvider(name='pokemon', redis=FakeRedis())

    async def get_json(url, params, total=15):
        if '/sets/' in url:
            return {'cards': [{'id': 'new-1'}, {'id': 'new-2'}]}
        return [{'id': 'other-9'}]

    p._get_json = get_json
    f = dict(FILTERS, set_id='30th-c', rarity='Ultra Rare')
    assert sorted(run(p.refresh(**f))) == ['new-1', 'new-2']


def test_cards_without_a_picture_at_the_source_are_nothing_to_show_not_an_outage(client, monkeypatch):
    backend_app, _ = client
    p = provider([['n-1', 'n-2']])
    monkeypatch.setattr(backend_app, '_provider', p)

    async def detail_without_image(api, cid):
        return {'id': cid, 'name': 'Charizard', 'image_large': ''}

    p.get_card_detail = detail_without_image
    resp = get_card(backend_app)
    assert resp.status_code == 200
    assert run(resp.get_json())['empty'] is True

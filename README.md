# Pokémon Cards for TRMNL

Discover Pokémon cards on your TRMNL — browse packs, hunt for rares, or enjoy the artwork. Filter by type, rarity, or set. A new selection appears each refresh.

**Data:** [TCGdex](https://tcgdex.net) — free, no API key required.

## Features

- Filter by Pokémon type, rarity, or set
- Card stats: HP, type, stage, rarity, retreat cost, regulation mark, print variants
- Market pricing via Cardmarket (avg, 7-day average)
- Set logo displayed on full view

## Caching

The backend is deliberately gentle on the TCGdex API. Each unique filter combination (type + rarity + set) is cached independently in Redis.

**How it works:**

1. On first request for a filter combo, the backend fetches up to 20 random matching card IDs from TCGdex, then fetches full card data for each in parallel. The result is stored in Redis with a timestamp.
2. On subsequent requests within the refresh window (default: 1 hour), the cached cards are returned immediately — no API calls made.
3. Once the cache is older than the refresh window, the next request triggers a **background refresh** while still returning the stale data instantly. The display never blocks waiting for fresh data.
4. If the TCGdex API returns nothing (e.g. an invalid filter), a 5-minute backoff is stored so the API is not retried immediately.
5. Each TRMNL refresh randomly picks 4 cards from the cached pool of 20, giving variety without any extra API calls.

Cache keys follow the pattern `tcg:pokemon:cache:{filters}` where filters is the JSON-serialised filter combination.

Cards are stored in Redis indefinitely and refreshed on a rolling basis — data accumulates over time and is never purged unless you flush Redis manually.

## Self-hosting

```bash
cp .env.example .env
# edit .env as needed
docker compose up -d
```

Default port: `8694`. Configure via `BACKEND_PORT` in `.env`.

The backend expects a Redis instance. Docker Compose starts one automatically.

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `REFRESH_HOURS` | `1` | How often cached card pools are refreshed |
| `ACCESS_MODE` | `whitelist_only` | `whitelist_only` / `rate_limited` / `open` |
| `PUBLIC_RATE_LIMIT_WINDOW_SECONDS` | `300` | Rate limit window for public callers |
| `REDIS_HOST` | `redis` | Redis hostname |
| `REDIS_PORT` | `6379` | Redis port |
| `BACKEND_PORT` | `8694` | Exposed backend port |

<!-- PLUGIN_STATS_START -->
## 🚀 TRMNL Plugin(s)

*Last updated: 2026-05-04 08:14:37 UTC*


## 🔒 Plugin ID: 297288

**Status**: ⏳ Not yet published on TRMNL or API unavailable

This plugin is configured but either hasn't been published to the TRMNL marketplace yet or the API is temporarily unavailable.

**Plugin URL**: https://usetrmnl.com/recipes/297288

---

<!-- PLUGIN_STATS_END -->

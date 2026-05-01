# trmnl-pokemon-cards-plugin

TRMNL e-paper plugin that displays a random Pokemon TCG card — art, name, type, HP, rarity, and set.

GitHub: https://github.com/ExcuseMi/trmnl-pokemon-cards-plugin
Local: ~/workspace/trmnl-pokemon-cards-plugin/

---

## Concept

Each refresh cycle shows a different Pokemon card pulled from the Pokemon TCG API.
Full view: card art + full stats. Smaller views: card art + name only.

---

## Data source

Pokemon TCG API — https://api.pokemontcg.io/v2/cards
- Free tier: 1000 req/day, no auth needed
- Optional API key (header `X-Api-Key`) for 20 000 req/day
- Filter by set, type, rarity via query params

---

## Architecture: polling backend

Strategy: `polling`
Backend fetches a random card on startup and refreshes every N hours.
TRMNL polls `GET /card` to get the current card JSON.

```
TRMNL  →  GET /card  →  backend  (cached card, refreshed in background)
                              ↕ (startup + scheduled)
                        Pokemon TCG API
```

### Backend stack

Python 3.14, Quart + Hypercorn, aiohttp.
`--workers 1` so background task runs once.

Files:
```
backend/
├── Dockerfile
├── app.py
├── requirements.txt
└── modules/
    ├── providers/
    │   └── pokemon_tcg.py     # fetch random card from API
    ├── formatters/
    │   └── card.py            # shape card dict for template
    └── utils/
        └── ip_whitelist.py    # TRMNL IP guard
```

`app.py` endpoints:
- `GET /card` — returns current card (IP-whitelisted)
- `GET /health` — liveness probe
- `POST /refresh` — trigger manual refresh (IP-whitelisted)

`pokemon_tcg.py` logic:
1. Query `GET /cards?q=<filter>&pageSize=100` → pick random card from results
2. Extract: `id`, `name`, `hp`, `types`, `rarity`, `set.name`, `set.series`, `images.large`, `images.small`
3. Cache in module-level variable; refresh every `REFRESH_HOURS` hours

### Card shape returned by `/card`

```json
{
  "id": "base1-4",
  "name": "Charizard",
  "hp": "120",
  "types": ["Fire"],
  "rarity": "Rare Holo",
  "set_name": "Base Set",
  "series": "Base",
  "image_large": "https://images.pokemontcg.io/base1/4_hires.png",
  "image_small": "https://images.pokemontcg.io/base1/4.png"
}
```

---

## Settings fields (`settings.yml`)

| keyname | field_type | purpose |
|---------|-----------|---------|
| `author_info` | `author_bio` | marketplace description |
| `pokemon_type` | `select` | filter by type (Fire, Water, Grass, …, Any) |
| `rarity` | `select` | filter by rarity (Common, Uncommon, Rare, Rare Holo, Any) |
| `set_id` | `string` | optional: lock to a specific set ID (e.g. `base1`) |
| `api_key` | `password` | optional Pokemon TCG API key for higher rate limit |
| `refresh_hours` | `number` | card refresh interval (default 3) |

category: `games`
refresh_interval: 60 minutes (card refreshes independently on its own schedule)

---

## Template layout (`plugin/src/`)

### transform.js

Input: `{ data: { id, name, hp, types, rarity, set_name, series, image_large, image_small } }`

Output:
```js
{
  card: {
    name, hp, types_str,   // "Fire"  or "Fire · Water"
    rarity, set_name,
    image_large, image_small,
  }
}
```

### shared.liquid structure

```
full (view=1):      image_large left col | name + hp + types + rarity + set right col
half_h (view=2):    image_small left | name + hp + types right
half_v (view=3):    image_small top-left + name + hp stacked
quadrant (view=4):  image_small + name only
```

Title bar: plugin instance name on all views.

Image rendered with `<img>` tag, constrained height.
Stats use `label--small` + `description` classes.

---

## `.trmnlp.yml` mock variables

```yaml
variables:
  trmnl:
    system:
      timestamp_utc: 1700000000
    plugin_settings:
      instance_name: "Pokemon Cards"
      strategy: polling
      dark_mode: "no"
      no_screen_padding: "no"
      custom_fields_values:
        pokemon_type: "any"
        rarity: "any"
        set_id: ""
        refresh_hours: 3
  card:
    name: "Charizard"
    hp: "120"
    types_str: "Fire"
    rarity: "Rare Holo"
    set_name: "Base Set"
    image_large: "https://images.pokemontcg.io/base1/4_hires.png"
    image_small: "https://images.pokemontcg.io/base1/4.png"
```

---

## Docker

`docker-compose.yml`:
- service `backend` on port 8080
- `env_file: .env`
- memory limit 1g

`docker-compose.test.yml`:
- service `test-transform` with `profiles: ["test"]`
- mounts `plugin/src/transform.js` read-only

---

## `.env.example`

```
POKEMON_TCG_API_KEY=
REFRESH_HOURS=3
ENABLE_IP_WHITELIST=true
IP_REFRESH_HOURS=24
```

---

## Build order

1. `gh repo clone ExcuseMi/trmnl-pokemon-cards-plugin ~/workspace/trmnl-pokemon-cards-plugin`
2. `trmnlp init plugin` from project root (registers plugin, writes numeric `id` to `plugin/src/settings.yml`)
3. Write backend files
4. Write `plugin/src/` files (settings.yml, transform.js, *.liquid)
5. Write test data `test/transform/data/sample.json`
6. `trmnlp push -f` from `plugin/`
7. Configure `.env` with optional API key
8. `docker compose up -d backend`
9. Point plugin polling URL to `http://<host>:8080/card`

---

## Key decisions

- **Polling not webhook:** card data is self-contained; no user-side webhook setup needed.
- **Backend caches one card:** avoids hitting TCG API on every TRMNL refresh (TRMNL may refresh every 15 min).
- **Image via `<img>` tag:** TCG images are hosted on CDN; TRMNL fetches and renders them at display time.
- **No `xhrSelect` for sets:** set list is large and changes rarely — user types set ID directly.
- **`--workers 1`:** ensures the background refresh loop runs exactly once.

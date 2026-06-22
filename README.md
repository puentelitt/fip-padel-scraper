# FIP Padel Men's Ranking Scraper

Scrapes the **top 300 male players** from the FIP padel ranking
(<https://www.padelfip.com/es/fip-rankings/>) into `fip_men_ranking.csv`.

## Why a browser is needed

The page ships only the top ~30 men in static HTML. Everything below is
lazy-loaded by a **"Cargar más"** button that fires an AJAX call, so a plain
`requests` + BeautifulSoup GET will not get past the first batch. The scraper
drives **Chromium via Playwright**, clicking the button until the men's table is
full.

The Masculino section is scoped precisely:

- Ranks **1–10** come from the podium **cards** (`.ranking__male .player__card`)
  — they are *not* in the table.
- Ranks **11+** come from the **first** `table.table__ranking` on the page
  (the second one is Femenino).
- Only the **visible** "Cargar más" button is clicked (on a desktop viewport
  exactly one is visible — the Masculino one).

Movement prefixes (`+2 18`, `-1 19`) are parsed down to the trailing integer.
Ties are preserved (two players at #1, two at #3, …). Rows are de-duped by
`(position, player)`, capped at 300, and written as UTF-8.

## Setup & run

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/playwright install chromium

# 1. Scrape the ranking (needs the browser)
.venv/bin/python fip_scraper.py

# 2. Enrich with per-player bio data (plain HTTP, no browser)
.venv/bin/python enrich_players.py

# 3. Build the dashboard, then open index.html in any browser
.venv/bin/python build_dashboard.py
open index.html
```

## Dashboard

`build_dashboard.py` embeds the enriched CSV into a single self-contained
`index.html` (no server, no build step — just open it). It lets you:

- **Search** by player name
- Filter by **nationality** (multi-select, with per-country counts)
- Filter by **playing side** (Right / Left / All)
- Filter by **age** range (min / max)
- Filter by **height** (taller ≥ / shorter ≤, in metres)
- **Sort** by any column (click the header)
- Open each player's **FIP profile** in a new tab

Re-run `build_dashboard.py` whenever the CSV is refreshed.

## Output

### `fip_men_ranking.csv` — the ranking

| column | notes |
|--------|-------|
| position | trailing integer of the rank cell; ties allowed |
| player | full name |
| country | 3-letter code (ESP, ARG, …) |
| points | thousands separators stripped, stored as int |
| profile_url | absolute URL to the player's FIP profile |

The script prints how many rows were actually captured and says so plainly if
it's fewer than 300.

### `fip_men_ranking_enriched.csv` — ranking + biographical data

`enrich_players.py` reads the ranking CSV and fetches each player's profile page
(the bio is in the static HTML, so it uses concurrent `requests` — no browser).
It adds these columns from the "Detalles del jugador" block:

| column | source | example |
|--------|--------|---------|
| birthdate | Edad | `08/03/2002` |
| age | Edad | `24` |
| place_of_birth | Lugar de nacimiento | `Valladolid` |
| height_m | Altura | `1.90` |
| playing_side | Posición de Juego | `Right` / `Left` |

The site uses `--` as a placeholder for unknown values; those are left blank.
Not every player has every field filled in on FIP, so coverage is partial for
`place_of_birth`, `height_m`, and `playing_side` — the script prints exact
coverage counts after running.

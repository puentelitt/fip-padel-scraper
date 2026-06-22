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
.venv/bin/python fip_scraper.py
```

## Output

`fip_men_ranking.csv` with columns:

| column | notes |
|--------|-------|
| position | trailing integer of the rank cell; ties allowed |
| player | full name |
| country | 3-letter code (ESP, ARG, …) |
| points | thousands separators stripped, stored as int |
| profile_url | absolute URL to the player's FIP profile |

The script prints how many rows were actually captured and says so plainly if
it's fewer than 300.

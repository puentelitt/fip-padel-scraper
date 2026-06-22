#!/usr/bin/env python3
"""Scrape the top 300 MALE players from the FIP padel ranking.

Page: https://www.padelfip.com/es/fip-rankings/

Markup reality (verified against the live page):
  MAIN.ranking__main
    H3.ranking__titleMale  "Masculino"
    DIV.ranking__male       -> 10 player CARDS for ranks 1-10 (.player__card)
    TABLE.table__ranking    -> ranks 11+ (the FIRST table on the page)
    H3.ranking__titleFemale "Femenino"
    DIV.ranking__female     -> women's cards
    TABLE.table__ranking    -> women's table (the SECOND table)

Only the top ~30 men ship in static HTML; the rest are lazy-loaded by the
"Cargar mas" button (class .loadMoreRanking) via AJAX. On a desktop viewport
exactly one such button is visible — the Masculino one — so we click it until
the men's table has enough rows (>= 290, since the 10 cards cover ranks 1-10)
or the button stops adding rows.

Output: fip_men_ranking.csv -> position, player, country, points, profile_url
"""

import csv
import re
import sys

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

URL = "https://www.padelfip.com/es/fip-rankings/"
TARGET = 300
OUTPUT = "fip_men_ranking.csv"
BASE = "https://www.padelfip.com"


def dismiss_cookie_banner(page):
    """Best-effort cookie dismissal."""
    candidates = [
        "#onetrust-accept-btn-handler",
        "button:has-text('Aceptar')",
        "button:has-text('Acepto')",
        "button:has-text('ACEPTAR')",
        "button:has-text('Accept')",
        ".cookie-accept",
        "[aria-label*='accept' i]",
    ]
    for sel in candidates:
        try:
            el = page.locator(sel).first
            if el.count() > 0 and el.is_visible():
                el.click(timeout=2000)
                page.wait_for_timeout(500)
                print(f"Dismissed cookie banner via: {sel}")
                return
        except Exception:
            continue
    print("No cookie banner dismissed (best effort).")


def men_table_rows(page):
    """Live row count of the first (Masculino) table's tbody."""
    return page.locator("table.table__ranking").first.locator("tbody tr").count()


def load_more(page):
    """Click the visible Masculino 'Cargar mas' button until the men's table
    has >= (TARGET - 10) rows (10 ranks come from the podium cards) or it
    stops growing."""
    need = TARGET - 10  # cards supply ranks 1-10
    last = men_table_rows(page)
    print(f"Initial men's table rows (ranks 11+): {last}")
    stalls = 0

    while last < need:
        btn = page.locator(".loadMoreRanking:visible").first
        if btn.count() == 0:
            print("No visible 'Cargar mas' button — stopping.")
            break
        try:
            btn.scroll_into_view_if_needed(timeout=3000)
            btn.click(timeout=5000)
        except Exception as e:
            print(f"Could not click 'Cargar mas' ({e}) — stopping.")
            break

        grew = False
        for _ in range(20):  # poll up to ~10s for AJAX rows
            page.wait_for_timeout(500)
            now = men_table_rows(page)
            if now > last:
                grew = True
                last = now
                break

        if not grew:
            stalls += 1
            print(f"No new rows after click (stall {stalls}). Rows: {last}")
            if stalls >= 2:
                print("Button stopped adding rows — stopping.")
                break
        else:
            stalls = 0
            print(f"Men's table rows now: {last}")

    return last


def parse_rank(text):
    """Position may carry a movement prefix ('+2 18', '-1 19'); the actual
    rank is the trailing integer."""
    if not text:
        return None
    nums = re.findall(r"\d+", text)
    return int(nums[-1]) if nums else None


def parse_points(text):
    """Strip thousands separators / spaces -> int."""
    if not text:
        return None
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


def text_of(node):
    return node.get_text(" ", strip=True) if node else ""


def parse_cards(html):
    """Ranks 1-10 from the Masculino podium cards."""
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for card in soup.select(".player__card"):
        position = parse_rank(text_of(card.select_one(".player__rank")))
        if position is None:
            continue
        name_a = card.select_one(".player__name")
        player = text_of(name_a)
        profile_url = name_a["href"].strip() if name_a and name_a.has_attr("href") else ""
        country = text_of(card.select_one(".player__country"))
        if not country:
            flag = card.select_one(".player__flag")
            country = flag.get("alt", "").strip() if flag else ""
        points = parse_points(text_of(card.select_one(".player__pointTNumber")))
        out.append(
            {
                "position": position,
                "player": player,
                "country": country,
                "points": points,
                "profile_url": profile_url,
            }
        )
    return out


def parse_table(html):
    """Ranks 11+ from the Masculino table."""
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for tr in soup.select("tbody tr"):
        rank_cell = tr.select_one(".cell__rank") or tr.find("td")
        position = parse_rank(text_of(rank_cell))
        if position is None:
            continue
        name_a = tr.select_one(".cell__player a.name") or tr.select_one(".cell__player a")
        player = text_of(name_a)
        profile_url = name_a["href"].strip() if name_a and name_a.has_attr("href") else ""
        country = text_of(tr.select_one(".cell__country .player__country"))
        if not country:
            flag = tr.select_one(".cell__country .player__flag")
            country = flag.get("alt", "").strip() if flag else ""
        points = parse_points(text_of(tr.select_one(".cell__points")))
        out.append(
            {
                "position": position,
                "player": player,
                "country": country,
                "points": points,
                "profile_url": profile_url,
            }
        )
    return out


def normalize_url(u):
    if u and u.startswith("/"):
        return BASE + u
    return u


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Desktop viewport so the desktop (visible) Masculino button is used.
        page = browser.new_page(viewport={"width": 1400, "height": 1000})
        page.set_default_timeout(15000)
        print(f"Navigating to {URL} ...")
        page.goto(URL, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)

        dismiss_cookie_banner(page)
        page.wait_for_timeout(500)

        load_more(page)

        cards_html = page.locator(".ranking__male").first.evaluate("el => el.outerHTML")
        table_html = page.locator("table.table__ranking").first.evaluate("el => el.outerHTML")
        browser.close()

    rows = parse_cards(cards_html) + parse_table(table_html)
    for r in rows:
        r["profile_url"] = normalize_url(r["profile_url"])

    # De-dupe by (position, player), preserve first occurrence.
    seen = set()
    deduped = []
    for r in rows:
        key = (r["position"], r["player"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)

    # Stable sort by position (ties allowed).
    deduped.sort(key=lambda r: r["position"])
    deduped = deduped[:TARGET]

    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f, fieldnames=["position", "player", "country", "points", "profile_url"]
        )
        w.writeheader()
        w.writerows(deduped)

    n = len(deduped)
    print(f"\nWrote {n} rows to {OUTPUT}")
    if n < TARGET:
        print(
            f"NOTE: captured only {n} rows (fewer than {TARGET}). The Masculino "
            "list may genuinely be shorter, or the Masculino selector may need "
            "adjusting if the page markup changed."
        )
    else:
        print(f"Captured the full top {TARGET}.")
    return n


if __name__ == "__main__":
    n = main()
    sys.exit(0 if n > 0 else 1)

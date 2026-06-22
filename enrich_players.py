#!/usr/bin/env python3
"""Enrich fip_men_ranking.csv with per-player biographical data.

Each player's profile page (the `profile_url` column) contains a
"Detalles del jugador" block whose fields are present in the STATIC HTML,
so we can fetch them with plain concurrent HTTP requests — no browser needed.

Fields parsed from the `.overview__mirror` blocks:
    Edad                 -> age + birthdate     (e.g. "24 (08/03/2002)")
    Lugar de nacimiento  -> place_of_birth      (e.g. "Valladolid")
    Altura               -> height_m            (e.g. "1.90 CM" -> 1.90)
    Posición de Juego    -> playing_side        (e.g. "Right" / "Left")

Input:  fip_men_ranking.csv
Output: fip_men_ranking_enriched.csv
        columns: position, player, country, points,
                 birthdate, age, place_of_birth, height_m, playing_side,
                 profile_url
"""

import csv
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup

INPUT = "fip_men_ranking.csv"
OUTPUT = "fip_men_ranking_enriched.csv"
WORKERS = 8
TIMEOUT = 30
HEADERS = {"User-Agent": "Mozilla/5.0 (fip-ranking-scraper; +personal use)"}

OUT_COLUMNS = [
    "position",
    "player",
    "country",
    "points",
    "birthdate",
    "age",
    "place_of_birth",
    "height_m",
    "playing_side",
    "profile_url",
]


def parse_age_block(value):
    """'24 (08/03/2002)' -> (age:int|None, birthdate:str|None)."""
    age = None
    birthdate = None
    m_age = re.search(r"\d+", value)
    if m_age:
        age = int(m_age.group())
    m_date = re.search(r"(\d{2}/\d{2}/\d{4})", value)
    if m_date:
        birthdate = m_date.group(1)
    return age, birthdate


def parse_height(value):
    """'1.90 CM' -> 1.90 (metres). The site labels metres as 'CM'."""
    m = re.search(r"(\d+[.,]\d+)", value)
    if m:
        return float(m.group(1).replace(",", "."))
    # Fallback: a bare integer like '190' -> 1.90
    m2 = re.search(r"\d+", value)
    if m2:
        n = int(m2.group())
        return round(n / 100, 2) if n > 100 else float(n)
    return None


def fetch_profile(row, session):
    """Fetch + parse one player's profile; return enriched row dict."""
    out = {
        "position": row["position"],
        "player": row["player"],
        "country": row["country"],
        "points": row["points"],
        "birthdate": "",
        "age": "",
        "place_of_birth": "",
        "height_m": "",
        "playing_side": "",
        "profile_url": row["profile_url"],
    }
    url = row["profile_url"]
    if not url:
        return out, "no-url"

    try:
        r = session.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
    except Exception as e:
        return out, f"error:{e}"

    soup = BeautifulSoup(r.text, "html.parser")
    for mirror in soup.select(".overview__mirror"):
        title_el = mirror.select_one(".overview__title")
        text_el = mirror.select_one(".overview__text")
        if not title_el or not text_el:
            continue
        label = title_el.get_text(" ", strip=True).lower()
        value = text_el.get_text(" ", strip=True)

        # The site uses '--' (or '-- CM') as a placeholder for missing data.
        if value.replace("CM", "").replace("-", "").strip() == "":
            continue

        if "edad" in label:
            age, bd = parse_age_block(value)
            out["age"] = age if age is not None else ""
            out["birthdate"] = bd or ""
        elif "lugar de nacimiento" in label:
            out["place_of_birth"] = value
        elif "altura" in label:
            h = parse_height(value)
            out["height_m"] = h if h is not None else ""
        elif "posición de juego" in label or "posicion de juego" in label:
            out["playing_side"] = value

    return out, "ok"


def main():
    with open(INPUT, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    print(f"Read {len(rows)} players from {INPUT}")

    results = {}
    errors = []
    with requests.Session() as session:
        with ThreadPoolExecutor(max_workers=WORKERS) as pool:
            futures = {
                pool.submit(fetch_profile, row, session): i
                for i, row in enumerate(rows)
            }
            done = 0
            for fut in as_completed(futures):
                i = futures[fut]
                out, status = fut.result()
                results[i] = out
                done += 1
                if status != "ok":
                    errors.append((rows[i]["player"], status))
                if done % 25 == 0 or done == len(rows):
                    print(f"  fetched {done}/{len(rows)}")

    ordered = [results[i] for i in range(len(rows))]

    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=OUT_COLUMNS)
        w.writeheader()
        w.writerows(ordered)

    # Coverage report
    def covered(field):
        return sum(1 for r in ordered if str(r[field]).strip())

    n = len(ordered)
    print(f"\nWrote {n} rows to {OUTPUT}")
    print("Field coverage:")
    for field in ["birthdate", "age", "place_of_birth", "height_m", "playing_side"]:
        c = covered(field)
        print(f"  {field:16s} {c}/{n}")

    if errors:
        print(f"\n{len(errors)} profile(s) had fetch issues:")
        for player, status in errors[:15]:
            print(f"  {player}: {status}")
        if len(errors) > 15:
            print(f"  ... and {len(errors) - 15} more")

    return n


if __name__ == "__main__":
    n = main()
    sys.exit(0 if n > 0 else 1)

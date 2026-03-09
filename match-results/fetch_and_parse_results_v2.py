#!/usr/bin/env python3
"""
parse_rfetm.py
--------------
Parses a RFETM team results page and produces a CSV with one row per
individual game (singles or doubles) within each match.

Usage:
    python parse_rfetm.py [URL] [--output OUTPUT_CSV]

Defaults:
    URL     = https://rfetm.es/resultados/2024-2025/view.php?liga=Mg==&grupo=1&subgrupo=S&jornada=0&equipo=1113&sexo=F
    output  = rfetm_results.csv
"""

import argparse
import csv
import re
import sys
from dataclasses import dataclass, fields, asdict
from typing import Optional

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Missing dependencies. Run:\n  pip install requests beautifulsoup4")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class GameRow:
    # Match context
    jornada: str
    match_date: str
    home_team_id: str
    home_team: str
    away_team_id: str
    away_team: str
    match_score_home: str
    match_score_away: str
    venue: str
    referee: str
    # Game within the match
    home_position: str          # position code for home team player: A, B, C (or D for doubles)
    away_position: str          # position code for away team player: X, Y, Z (or D for doubles)
    game_type: str              # singles / doubles
    home_player_lic: str
    home_player_name: str
    home_player2_lic: str       # doubles only
    home_player2_name: str      # doubles only
    away_player_lic: str
    away_player_name: str
    away_player2_lic: str       # doubles only
    away_player2_name: str      # doubles only
    set1: str
    set2: str
    set3: str
    set4: str
    set5: str
    game_result_home: str       # e.g. 3
    game_result_away: str       # e.g. 1
    running_score_home: str     # cumulative after this game
    running_score_away: str

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BASE_URL = "https://rfetm.es/resultados/2024-2025/"

def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()

def extract_standings(soup: BeautifulSoup) -> list[dict]:
    """Extract the final standings table."""
    rows = []
    tables = soup.find_all("table")
    for table in tables:
        headers = [clean(th.get_text()) for th in table.find_all("th")]
        if "EQUIPO" in headers and "PTOS." in headers:
            for tr in table.find_all("tr")[1:]:
                cells = [clean(td.get_text()) for td in tr.find_all("td")]
                if len(cells) >= len(headers):
                    rows.append(dict(zip(headers, cells)))
            break
    return rows

def parse_players_from_cell(cell) -> list[tuple[str, str]]:
    """Return list of (license, name) from a table cell containing player links."""
    players = []
    for a in cell.find_all("a"):
        href = a.get("href", "")
        m = re.search(r"jugador=(\d+)", href)
        lic = m.group(1) if m else ""
        name = clean(a.get_text())
        if name:
            players.append((lic, name))
    return players

def parse_match_block(jornada_label: str, match_table, detail_table) -> list[GameRow]:
    """
    Parse one match block: the outer summary row + the inner detail table.
    Returns a list of GameRow objects.
    """
    rows_out = []

    # ---- outer summary row ------------------------------------------------
    tds = match_table.find_all("td")
    date_str = ""
    home_team = ""
    away_team = ""
    match_score_home = ""
    match_score_away = ""

    texts = [clean(td.get_text()) for td in tds]

    # Find date (first non-empty text that looks like a date)
    for t in texts:
        if re.search(r"\d{2}/\d{2}/\d{4}", t):
            date_str = t
            break

    # Team names and IDs from links — first = HOME, second = AWAY (as shown in the header)
    team_links = [a for a in match_table.find_all("a") if "equipo=" in (a.get("href") or "")]
    home_team_id = ""
    away_team_id = ""
    if len(team_links) >= 2:
        home_team = clean(team_links[0].get_text())
        away_team = clean(team_links[1].get_text())
        m0 = re.search(r"equipo=(\d+)", team_links[0].get("href", ""))
        m1 = re.search(r"equipo=(\d+)", team_links[1].get("href", ""))
        home_team_id = m0.group(1) if m0 else ""
        away_team_id = m1.group(1) if m1 else ""

    # Scores: two bold standalone numbers
    bold_texts = [clean(b.get_text()) for b in match_table.find_all("b") if re.fullmatch(r"\d+", clean(b.get_text()))]
    if len(bold_texts) >= 2:
        match_score_home = bold_texts[0]
        match_score_away = bold_texts[1]

    # ---- detail table (inner nested table) --------------------------------
    if detail_table is None:
        return rows_out

    venue = ""
    referee = ""

    all_rows = detail_table.find_all("tr")
    for tr in all_rows:
        row_text = clean(tr.get_text())
        if "Árbitro:" in row_text:
            parts = row_text.split("Árbitro:")
            venue = clean(parts[0])
            referee = clean(parts[1]) if len(parts) > 1 else ""

    # Determine column order from the detail table header row.
    # The header row has: '' | team_left | '' | team_right | J1..J5 | '' | ''
    # team_left and team_right may be in either order — we compare against
    # home_team / away_team from the match header to assign correctly.
    detail_header = all_rows[0] if all_rows else None
    col_header_cells = detail_header.find_all("td") if detail_header else []
    detail_col_left  = clean(col_header_cells[1].get_text()) if len(col_header_cells) > 1 else ""
    detail_col_right = clean(col_header_cells[3].get_text()) if len(col_header_cells) > 3 else ""

    # left_is_home=True  → tds[1]=home player, tds[3]=away player
    # left_is_home=False → tds[1]=away player, tds[3]=home player
    left_is_home = (detail_col_left == home_team)

    # Game rows: rows that start with a position label (A/B/C/D)
    for tr in all_rows:
        tds = tr.find_all("td")
        if len(tds) < 7:
            continue

        left_pos  = clean(tds[0].get_text())
        middle_pos = clean(tds[2].get_text()) if len(tds) > 2 else ""
        # Valid game rows have A/B/C/D in td[0] and X/Y/Z/D in td[2]
        if left_pos not in ("A", "B", "C", "D") or middle_pos not in ("X", "Y", "Z", "D"):
            continue

        # Map left/right positions to home/away
        if left_is_home:
            home_position = left_pos
            away_position = middle_pos
        else:
            home_position = middle_pos
            away_position = left_pos

        left_players  = parse_players_from_cell(tds[1])
        right_players = parse_players_from_cell(tds[3])

        # Map left/right → home/away using the column order we detected above
        if left_is_home:
            home_players = left_players
            away_players = right_players
        else:
            home_players = right_players
            away_players = left_players

        game_type = "doubles" if (len(home_players) > 1 or len(away_players) > 1) else "singles"

        def get_player(players, idx):
            if idx < len(players):
                return players[idx]
            return ("", "")

        hp1 = get_player(home_players, 0)
        hp2 = get_player(home_players, 1)
        ap1 = get_player(away_players, 0)
        ap2 = get_player(away_players, 1)

        # Set scores are in tds[4..8]
        sets = []
        for i in range(4, 9):
            val = clean(tds[i].get_text()) if i < len(tds) else ""
            sets.append(val)

        # Game result tds[9], running score tds[10]
        result_text = clean(tds[9].get_text()) if len(tds) > 9 else ""
        running_text = clean(tds[10].get_text()) if len(tds) > 10 else ""

        def split_score(s):
            m = re.search(r"(\d+)\s*[–\-]\s*(\d+)", s)
            return (m.group(1), m.group(2)) if m else ("", "")

        gr_h, gr_a = split_score(result_text)
        rr_h, rr_a = split_score(running_text)

        rows_out.append(GameRow(
            jornada=jornada_label,
            match_date=date_str,
            home_team_id=home_team_id,
            home_team=home_team,
            away_team_id=away_team_id,
            away_team=away_team,
            match_score_home=match_score_home,
            match_score_away=match_score_away,
            venue=venue,
            referee=referee,
            home_position=home_position,
            away_position=away_position,
            game_type=game_type,
            home_player_lic=hp1[0],
            home_player_name=hp1[1],
            home_player2_lic=hp2[0],
            home_player2_name=hp2[1],
            away_player_lic=ap1[0],
            away_player_name=ap1[1],
            away_player2_lic=ap2[0],
            away_player2_name=ap2[1],
            set1=sets[0],
            set2=sets[1],
            set3=sets[2],
            set4=sets[3],
            set5=sets[4],
            game_result_home=gr_h,
            game_result_away=gr_a,
            running_score_home=rr_h,
            running_score_away=rr_a,
        ))

    return rows_out

# ---------------------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------------------

#def parse_page(url: str) -> tuple[list[GameRow], list[dict]]:
def parse_page(url: str) -> list[dict]:
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; rfetm-parser/1.0)"
    }
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    resp.encoding = "utf-8"

    soup = BeautifulSoup(resp.text, "html.parser")

    #standings = extract_standings(soup)
    game_rows: list[GameRow] = []

    # Iterate through jornada headers (tables whose single cell contains "Jornada N")
    all_tables = soup.find_all("table")

    i = 0
    current_jornada = ""
    while i < len(all_tables):
        table = all_tables[i]
        text = clean(table.get_text())

        # Detect jornada header table
        jornada_match = re.search(r"Jornada\s+(\d+)", text)
        if jornada_match and len(table.find_all("td")) <= 2:
            current_jornada = f"Jornada {jornada_match.group(1)}"
            i += 1
            continue

        # Detect match summary table (contains date + bold score + team links)
        if (current_jornada
                and re.search(r"\d{2}/\d{2}/\d{4}", text)
                and len(table.find_all("a")) >= 2):

            # The very next table (or nested inside) is the detail table
            # Look for a nested table first
            nested = table.find("table")
            if nested:
                detail_table = nested
                rows = parse_match_block(current_jornada, table, detail_table)
            elif i + 1 < len(all_tables):
                # Sometimes the detail is the immediately following table
                detail_table = all_tables[i + 1]
                rows = parse_match_block(current_jornada, table, detail_table)
                if rows:
                    i += 1  # skip consumed detail table
            else:
                rows = []

            game_rows.extend(rows)

        i += 1

    results = [asdict(row) for row in game_rows]
    return results

# ---------------------------------------------------------------------------
# CSV output
# ---------------------------------------------------------------------------

def write_games_csv(rows: list[GameRow], path: str):
    if not rows:
        print("⚠  No game rows found – CSV will be empty.")
        return
    col_names = [f.name for f in fields(GameRow)]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=col_names)
        writer.writeheader()
        for r in rows:
            writer.writerow({f.name: getattr(r, f.name) for f in fields(r)})
    print(f"✅  Games CSV  → {path}  ({len(rows)} rows)")

def write_standings_csv(rows: list[dict], path: str):
    if not rows:
        print("⚠  No standings found – standings CSV will be empty.")
        return
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"✅  Standings CSV → {path}  ({len(rows)} rows)")

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

DEFAULT_URL = (
    "https://rfetm.es/resultados/2024-2025/view.php?liga=Mg==&grupo=1&subgrupo=S&jornada=0&equipo=1113&sexo=F"
)

def main():
    parser = argparse.ArgumentParser(description="Parse RFETM results page to CSV.")
    parser.add_argument("url", nargs="?", default=DEFAULT_URL, help="Page URL")
    parser.add_argument("--output", default="rfetm_results.csv", help="Output CSV filename for games")
    parser.add_argument("--standings", default="rfetm_standings.csv", help="Output CSV filename for standings")
    args = parser.parse_args()

    print(f"Fetching: {args.url}")
    game_rows = parse_page(args.url)

    write_games_csv(game_rows, args.output)
    #write_standings_csv(standings, args.standings)

if __name__ == "__main__":
    main()

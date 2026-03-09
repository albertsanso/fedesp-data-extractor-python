"""
RFETM Scraper
=============
Scrapes match results from rfetm.es and produces CSV files.

Output structure:
  output/{season}/{genre}/{category}/grupo_{n}.csv

Usage:
  python rfetm_scraper.py                         # all seasons / all categories
  python rfetm_scraper.py --season 2022-2023
  python rfetm_scraper.py --season 2022-2023 --genre female
  python rfetm_scraper.py --season 2022-2023 --genre female --category super-divisio
  python rfetm_scraper.py --season 2022-2023 --genre female --category super-divisio --group 0

Options:
  --output DIR      Output directory (default: output)
  --delay SECONDS   Pause between requests (default: 1.0)
  --jornada N       Scrape only this jornada number (default: all)
"""

import csv
import os
import re
import time
import argparse
import logging
from enum import Enum
from typing import Optional

import requests
from bs4 import BeautifulSoup

# ─────────────────────────────────────────────────────────────────────────────
# Enums & config
# ─────────────────────────────────────────────────────────────────────────────

class Genre(Enum):
    MALE   = "male"
    FEMALE = "female"


class Category(Enum):
    SUPER_DIVISION   = "super-divisio"
    DIVISION_HONOR   = "divisio-honor"
    PRIMERA_NACIONAL = "primera-nacional"
    SEGUNDA_NACIONAL = "segona-nacional"


class Season(Enum):
    T_2024_2025 = "2024-2025"
    T_2023_2024 = "2023-2024"
    T_2022_2023 = "2022-2023"
    T_2021_2022 = "2021-2022"
    T_2020_2021 = "2020-2021"
    T_2019_2020 = "2019-2020"
    T_2018_2019 = "2018-2019"


def _p(sex, lid, gid, sub):
    return {"league_id": lid, "group_id": str(gid), "subgroup_id": sub, "sex": sex}

M, F = "M", "F"

URL_PARAMS = {
    Season.T_2024_2025: {
        Genre.MALE: {
            Category.SUPER_DIVISION:   [_p(M,"MQ==",0,"S")],
            Category.DIVISION_HONOR:   [_p(M,"Mg==",g,"S") for g in range(1,4)],
            Category.PRIMERA_NACIONAL: [_p(M,"Mw==",g,"S") for g in range(1,7)],
            Category.SEGUNDA_NACIONAL: [_p(M,"NA==",g,"S") for g in range(1,13)],
        },
        Genre.FEMALE: {
            Category.SUPER_DIVISION:   [_p(F,"MQ==",0,"S")],
            Category.DIVISION_HONOR:   [_p(F,"Mg==",g,"S") for g in range(1,4)],
            Category.PRIMERA_NACIONAL: [_p(F,"Mw==",g,"S") for g in range(1,7)],
            Category.SEGUNDA_NACIONAL: [],
        },
    },
    Season.T_2023_2024: {
        Genre.MALE: {
            Category.SUPER_DIVISION:   [_p(M,"MQ==",0,"S")],
            Category.DIVISION_HONOR:   [_p(M,"Mg==",g,"S") for g in range(1,4)],
            Category.PRIMERA_NACIONAL: [_p(M,"Mw==",g,"S") for g in range(1,7)],
            Category.SEGUNDA_NACIONAL: [_p(M,"NA==",g,"S") for g in range(1,13)],
        },
        Genre.FEMALE: {
            Category.SUPER_DIVISION:   [_p(F,"MQ==",0,"S")],
            Category.DIVISION_HONOR:   [_p(F,"Mg==",g,"S") for g in range(1,4)],
            Category.PRIMERA_NACIONAL: [_p(F,"Mw==",g,"S") for g in range(1,7)],
            Category.SEGUNDA_NACIONAL: [],
        },
    },
    Season.T_2022_2023: {
        Genre.MALE: {
            Category.SUPER_DIVISION:   [_p(M,"MQ==",0,"S")],
            Category.DIVISION_HONOR:   [_p(M,"Mg==",g,"S") for g in range(1,4)],
            Category.PRIMERA_NACIONAL: [_p(M,"Mw==",g,"S") for g in range(1,7)],
            Category.SEGUNDA_NACIONAL: [_p(M,"NA==",g,"S") for g in range(1,13)],
        },
        Genre.FEMALE: {
            Category.SUPER_DIVISION:   [_p(F,"MQ==",0,"S")],
            Category.DIVISION_HONOR:   [_p(F,"Mg==",g,"S") for g in range(1,4)],
            Category.PRIMERA_NACIONAL: [_p(F,"Mw==",g,"S") for g in range(1,7)],
            Category.SEGUNDA_NACIONAL: [],
        },
    },
    Season.T_2021_2022: {
        Genre.MALE: {
            Category.SUPER_DIVISION:   [_p(M,"MQ==",g,"S") for g in range(1,3)],
            Category.DIVISION_HONOR:   [_p(M,"Mg==",g,s) for s in ("A","B") for g in range(1,4)],
            Category.PRIMERA_NACIONAL: [_p(M,"Mw==",g,s) for s in ("A","B") for g in range(1,7)],
            Category.SEGUNDA_NACIONAL: [_p(M,"NA==",g,s) for s in ("A","B") for g in range(1,14)],
        },
        Genre.FEMALE: {
            Category.SUPER_DIVISION:   [_p(F,"MQ==",g,"S") for g in range(1,3)],
            Category.DIVISION_HONOR:   [_p(F,"Mg==",g,s) for s in ("A","B") for g in range(1,4)],
            Category.PRIMERA_NACIONAL: [_p(F,"Mw==",g,"S") for g in range(1,7)],
            Category.SEGUNDA_NACIONAL: [],
        },
    },
    Season.T_2020_2021: {
        Genre.MALE: {
            Category.SUPER_DIVISION:   [_p(M,"MQ==",g,None) for g in range(1,3)],
            Category.DIVISION_HONOR:   [_p(M,"Mg==",g,None) for g in range(1,7)],
            Category.PRIMERA_NACIONAL: [_p(M,"Mw==",g,None) for g in range(1,17)],
            Category.SEGUNDA_NACIONAL: [_p(M,"NA==",g,None) for g in range(1,29)],
        },
        Genre.FEMALE: {
            Category.SUPER_DIVISION:   [_p(F,"MQ==",g,None) for g in range(1,3)],
            Category.DIVISION_HONOR:   [_p(F,"Mg==",g,None) for g in range(1,7)],
            Category.PRIMERA_NACIONAL: [_p(F,"Mw==",g,None) for g in range(1,8)],
            Category.SEGUNDA_NACIONAL: [],
        },
    },
    Season.T_2019_2020: {
        Genre.MALE: {
            Category.SUPER_DIVISION:   [_p(M,"MQ==",0,None)],
            Category.DIVISION_HONOR:   [_p(M,"Mg==",g,None) for g in range(1,3)],
            Category.PRIMERA_NACIONAL: [_p(M,"Mw==",g,None) for g in range(1,7)],
            Category.SEGUNDA_NACIONAL: [_p(M,"NA==",g,None) for g in range(1,13)],
        },
        Genre.FEMALE: {
            Category.SUPER_DIVISION:   [_p(F,"MQ==",0,None)],
            Category.DIVISION_HONOR:   [_p(F,"Mg==",g,None) for g in range(1,3)],
            Category.PRIMERA_NACIONAL: [_p(F,"Mw==",g,None) for g in range(1,7)],
            Category.SEGUNDA_NACIONAL: [],
        },
    },
    Season.T_2018_2019: {
        Genre.MALE: {
            Category.SUPER_DIVISION:   [_p(M,"MQ==",0,None)],
            Category.DIVISION_HONOR:   [_p(M,"Mg==",g,None) for g in range(1,3)],
            Category.PRIMERA_NACIONAL: [_p(M,"Mw==",g,None) for g in range(1,7)],
            Category.SEGUNDA_NACIONAL: [_p(M,"NA==",g,None) for g in range(1,13)],
        },
        Genre.FEMALE: {
            Category.SUPER_DIVISION:   [_p(F,"MQ==",0,None)],
            Category.DIVISION_HONOR:   [_p(F,"Mg==",g,None) for g in range(1,3)],
            Category.PRIMERA_NACIONAL: [_p(F,"Mw==",g,None) for g in range(1,7)],
            Category.SEGUNDA_NACIONAL: [],
        },
    },
}

BASE_URL = "https://rfetm.es/public/resultados"

CSV_COLUMNS = [
    "jornada", "match_date",
    "home_team_id", "home_team", "away_team_id", "away_team",
    "match_score_home", "match_score_away",
    "venue", "referee",
    "home_position", "away_position", "game_type",
    "home_player_lic", "home_player_name",
    "home_player2_lic", "home_player2_name",
    "away_player_lic", "away_player_name",
    "away_player2_lic", "away_player2_name",
    "set1", "set2", "set3", "set4", "set5",
    "game_result_home", "game_result_away",
    "running_score_home", "running_score_away",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 rfetm-scraper/2.0"})
REQUEST_DELAY = 1.0

VALID_POSITIONS = {"A", "B", "C", "D", "X", "Y", "Z"}


# ─────────────────────────────────────────────────────────────────────────────
# URL builder
# ─────────────────────────────────────────────────────────────────────────────

def build_url(season: Season, params: dict, jornada: int = 0) -> str:
    base = f"{BASE_URL}/{season.value}/view.php"
    p = f"liga={params['league_id']}&grupo={params['group_id']}"
    if params["subgroup_id"] is not None:
        p += f"&subgrupo={params['subgroup_id']}"
    p += f"&jornada={jornada}&sexo={params['sex']}"
    return f"{base}?{p}"


# ─────────────────────────────────────────────────────────────────────────────
# HTTP
# ─────────────────────────────────────────────────────────────────────────────

def fetch(url: str, retries: int = 3) -> Optional[BeautifulSoup]:
    for attempt in range(retries):
        try:
            resp = SESSION.get(url, timeout=20)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser")
        except requests.RequestException as e:
            log.warning(f"Attempt {attempt+1}/{retries} failed for {url}: {e}")
            time.sleep(2 ** attempt)
    log.error(f"All retries exhausted for {url}")
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_jornada_numbers(soup: BeautifulSoup) -> list:
    nums = set()
    for a in soup.find_all("a", href=True):
        m = re.search(r"jornada=(\d+)", a["href"])
        if m:
            n = int(m.group(1))
            if n > 0:
                nums.add(n)
    return sorted(nums)


def parse_player_cell(td_tag) -> list:
    """Return list of {lic, name} from a player <td> (1 for singles, 2 for doubles)."""
    players = []
    for a in td_tag.find_all("a", href=True):
        href = a["href"]
        name = a.get_text(strip=True)
        if not name:
            continue
        if "jugador=" in href:
            m = re.search(r"jugador=(\d+)", href)
            players.append({"lic": m.group(1) if m else "", "name": name})
        elif re.search(r"#(\d+)#", href):
            m = re.search(r"#(\d+)#", href)
            players.append({"lic": m.group(1) if m else "", "name": name})
    return players


def same_team(a: str, b: str) -> bool:
    def norm(s):
        return re.sub(r"\s+", " ", s).strip().upper()
    return norm(a) == norm(b)


# ─────────────────────────────────────────────────────────────────────────────
# Page parser
# ─────────────────────────────────────────────────────────────────────────────

def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _parse_match_block(jornada_label: str, match_table, detail_table) -> list:
    """Parse one match block into game rows (dicts)."""
    rows_out = []

    # ── Match summary ────────────────────────────────────────────────────────
    date_str = ""
    for td in match_table.find_all("td"):
        t = _clean(td.get_text())
        if re.search(r"\d{2}/\d{2}/\d{4}", t):
            date_str = t
            break

    team_links = [a for a in match_table.find_all("a")
                  if "equipo=" in (a.get("href") or "")]
    home_team    = _clean(team_links[0].get_text()) if len(team_links) > 0 else ""
    away_team    = _clean(team_links[1].get_text()) if len(team_links) > 1 else ""
    m0 = re.search(r"equipo=(\d+)", team_links[0].get("href", "")) if len(team_links) > 0 else None
    m1 = re.search(r"equipo=(\d+)", team_links[1].get("href", "")) if len(team_links) > 1 else None
    home_team_id = m0.group(1) if m0 else ""
    away_team_id = m1.group(1) if m1 else ""

    bold_nums = [_clean(b.get_text()) for b in match_table.find_all("b")
                 if re.fullmatch(r"\d+", _clean(b.get_text()))]
    match_score_home = bold_nums[0] if len(bold_nums) > 0 else ""
    match_score_away = bold_nums[1] if len(bold_nums) > 1 else ""

    if detail_table is None:
        return rows_out

    # ── Detail table ─────────────────────────────────────────────────────────
    all_rows = detail_table.find_all("tr")

    venue, referee = "", ""
    for dtr in all_rows:
        row_text = _clean(dtr.get_text())
        if "Árbitro:" in row_text:
            parts = row_text.split("Árbitro:")
            venue   = _clean(parts[0])
            referee = _clean(parts[1]) if len(parts) > 1 else ""

    hcols = all_rows[0].find_all("td") if all_rows else []
    left_team_hdr = _clean(hcols[1].get_text()) if len(hcols) > 1 else ""
    left_is_home  = (left_team_hdr == home_team)

    VALID_LEFT  = {"A", "B", "C", "D"}
    VALID_RIGHT = {"X", "Y", "Z", "D"}

    for game_tr in all_rows:
        tds = game_tr.find_all("td")
        if len(tds) < 7:
            continue
        left_pos  = _clean(tds[0].get_text())
        right_pos = _clean(tds[2].get_text()) if len(tds) > 2 else ""
        if left_pos not in VALID_LEFT or right_pos not in VALID_RIGHT:
            continue

        left_pl  = parse_player_cell(tds[1])
        right_pl = parse_player_cell(tds[3])

        if left_is_home:
            home_pos, away_pos = left_pos,  right_pos
            hp,       ap       = left_pl,   right_pl
        else:
            home_pos, away_pos = right_pos, left_pos
            hp,       ap       = right_pl,  left_pl

        game_type = "doubles" if (len(hp) > 1 or len(ap) > 1) else "singles"

        sets = [_clean(tds[j].get_text()) if j < len(tds) else "" for j in range(4, 9)]

        def split_score(s):
            sm = re.search(r"(\d+)\s*[–\-]\s*(\d+)", s)
            return (int(sm.group(1)), int(sm.group(2))) if sm else ("", "")

        gr_h, gr_a = split_score(_clean(tds[9].get_text())  if len(tds) > 9  else "")
        rr_h, rr_a = split_score(_clean(tds[10].get_text()) if len(tds) > 10 else "")

        rows_out.append({
            "jornada":            jornada_label,
            "match_date":         date_str,
            "home_team_id":       home_team_id,
            "home_team":          home_team,
            "away_team_id":       away_team_id,
            "away_team":          away_team,
            "match_score_home":   match_score_home,
            "match_score_away":   match_score_away,
            "venue":              venue,
            "referee":            referee,
            "home_position":      home_pos,
            "away_position":      away_pos,
            "game_type":          game_type,
            "home_player_lic":    hp[0]["lic"]  if len(hp) > 0 else "",
            "home_player_name":   hp[0]["name"] if len(hp) > 0 else "",
            "home_player2_lic":   hp[1]["lic"]  if len(hp) > 1 else "",
            "home_player2_name":  hp[1]["name"] if len(hp) > 1 else "",
            "away_player_lic":    ap[0]["lic"]  if len(ap) > 0 else "",
            "away_player_name":   ap[0]["name"] if len(ap) > 0 else "",
            "away_player2_lic":   ap[1]["lic"]  if len(ap) > 1 else "",
            "away_player2_name":  ap[1]["name"] if len(ap) > 1 else "",
            "set1": sets[0], "set2": sets[1], "set3": sets[2],
            "set4": sets[3], "set5": sets[4],
            "game_result_home":   gr_h,
            "game_result_away":   gr_a,
            "running_score_home": rr_h,
            "running_score_away": rr_a,
        })

    return rows_out


def parse_page(soup: BeautifulSoup, jornada_num: int) -> list:
    """
    Walk all_tables index-by-index:
      - Jornada label table  (<=2 TDs, text matches "Jornada N")
      - Match summary table  (date + >=2 links); current_jornada must be set
        → detail is either nested <table> inside it, or all_tables[i+1]
    """
    rows = []
    all_tables = soup.find_all("table")
    current_jornada = ""
    i = 0

    while i < len(all_tables):
        table = all_tables[i]
        text  = _clean(table.get_text())

        jm = re.search(r"Jornada\s+(\d+)", text)
        if jm and len(table.find_all("td")) <= 2:
            current_jornada = f"Jornada {jm.group(1)}"
            i += 1
            continue

        if (current_jornada
                and re.search(r"\d{2}/\d{2}/\d{4}", text)
                and len(table.find_all("a")) >= 2):

            nested = table.find("table")
            if nested:
                detail_table = nested
                match_rows = _parse_match_block(current_jornada, table, detail_table)
            elif i + 1 < len(all_tables):
                detail_table = all_tables[i + 1]
                match_rows = _parse_match_block(current_jornada, table, detail_table)
                if match_rows:
                    i += 1
            else:
                match_rows = []

            rows.extend(match_rows)

        i += 1

    return rows


# ─────────────────────────────────────────────────────────────────────────────
# Scrape one group
# ─────────────────────────────────────────────────────────────────────────────

def scrape_group(season, params, only_jornada=None):
    all_rows = []

    overview_url = build_url(season, params, jornada=0)
    log.info(f"  Overview → {overview_url}")
    soup = fetch(overview_url)
    time.sleep(REQUEST_DELAY)
    if soup is None:
        return all_rows

    jornadas = get_jornada_numbers(soup)
    if not jornadas:
        log.warning("  No jornadas found – skipping.")
        return all_rows

    if only_jornada is not None:
        if only_jornada not in jornadas:
            log.warning(f"  Jornada {only_jornada} not in {jornadas}")
            return all_rows
        jornadas = [only_jornada]

    log.info(f"  Jornadas: {jornadas}")
    for j in jornadas:
        url = build_url(season, params, jornada=j)
        log.info(f"  Jornada {j:>2} → {url}")
        jsoup = fetch(url)
        time.sleep(REQUEST_DELAY)
        if jsoup is None:
            continue
        r = parse_page(jsoup, j)
        log.info(f"           {len(r)} rows")
        all_rows.extend(r)

    return all_rows


# ─────────────────────────────────────────────────────────────────────────────
# CSV writer
# ─────────────────────────────────────────────────────────────────────────────

def write_csv(rows, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        w.writeheader()
        w.writerows(rows)
    log.info(f"  Saved {len(rows)} rows → {path}")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main(
    season: str = "2024-2025",
    genre: str = None,
    category: str = None,
    group: str = None,
    jornada: int = None,
    output: str = "../resources/match-results-details/v3-claude-flat",
    delay: float = 1.0,
):
    """
    Run the scraper programmatically.

    Args:
        season:   Season string e.g. "2024-2025". Default: "2024-2025".
        genre:    "male" or "female". Default: both.
        category: "super-divisio" | "divisio-honor" | "primera-nacional" | "segona-nacional".
                  Default: all.
        group:    Group ID string e.g. "0" or "1". Default: all.
        jornada:  Scrape only this round number. Default: all.
        output:   Output directory. Default: "output".
        delay:    Seconds between HTTP requests. Default: 1.0.

    Examples:
        main()
        main(season="2024-2025", genre="female")
        main(season="2024-2025", genre="male", category="super-divisio", group="0", jornada=3)
        main(season="2023-2024", output="data", delay=2.0)
    """
    global REQUEST_DELAY
    REQUEST_DELAY = delay

    seasons = list(Season)
    if season:
        seasons = [s for s in seasons if s.value == season]
        if not seasons:
            log.error(f"Unknown season '{season}'"); return

    genres = list(Genre)
    if genre:
        genres = [g for g in genres if g.value == genre]
        if not genres:
            log.error(f"Unknown genre '{genre}'"); return

    categories = list(Category)
    if category:
        categories = [c for c in categories if c.value == category]
        if not categories:
            log.error(f"Unknown category '{category}'"); return

    for s in seasons:
        for g in genres:
            for c in categories:
                param_list = URL_PARAMS.get(s, {}).get(g, {}).get(c, [])
                if not param_list:
                    continue
                for params in param_list:
                    if group is not None and params["group_id"] != group:
                        continue
                    log.info(
                        f"=== {s.value} / {g.value} / "
                        f"{c.value} / grupo {params['group_id']} ==="
                    )
                    rows = scrape_group(s, params, only_jornada=jornada)
                    if not rows:
                        log.warning("  No data – skipping."); continue
                    csv_path = os.path.join(
                        output, s.value,
                        f"rfetm-{s.value}-{g.value}-{c.value}-group-{params['group_id']}-teamid-0_matches.csv"
                    )
                    write_csv(rows, csv_path)

    log.info("Done.")


if __name__ == "__main__":
    """
    ap = argparse.ArgumentParser(description="RFETM league scraper")
    ap.add_argument("--season",   default="2024-2025", help="e.g. 2022-2023")
    ap.add_argument("--genre",    help="male or female")
    ap.add_argument("--category", help="super-divisio | divisio-honor | primera-nacional | segona-nacional")
    ap.add_argument("--group",    help="group_id, e.g. 0 or 1")
    ap.add_argument("--jornada",  type=int, help="scrape only this jornada")
    ap.add_argument("--output",   default="../resources/match-results-details/v3-claude")
    ap.add_argument("--delay",    type=float, default=1.0)
    args = ap.parse_args()
    main(season=args.season, genre=args.genre, category=args.category, group=args.group, jornada=args.jornada, output=args.output, delay=args.delay,)
    """
    #main(season="2024-2025", genre="female")
    #main(season="2023-2024", genre="female")
    #main(season="2023-2024", genre="male")
    #main(season="2020-2021", genre="male")
    #main(season="2019-2020", genre="male")
    main(season="2021-2022")
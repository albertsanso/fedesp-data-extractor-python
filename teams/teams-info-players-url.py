import requests
from bs4 import BeautifulSoup
import re
import csv
import base64
import time
from unidecode import unidecode

from common.rfetmcommons import RESOURCES_FOLDER, Genre, Category, Season
from common.resourceadapter import save_to_csv

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/125.0.0.0 Safari/537.36"),
    "Accept-Language": "en-US,en;q=0.9,es;q=0.8"
}

BASE_RESULTS_URL = "https://www.rfetm.es/resultados"

def fetch_page(url):
    s = requests.Session()
    r = s.get(url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    return r

def get_all_division_links_for_season(season):
    # Fetch main results page
    the_url = BASE_RESULTS_URL+"/"+season.value+"/"
    r = fetch_page(the_url)
    soup = BeautifulSoup(r.content, "lxml")

    division_links = []

    # Find all <a> tags inside navigation menus or main content that link to 'view.php?liga=...'
    for a in soup.find_all("a", href=True):
        href = a['href']
        if "view.php" in href and "liga=" in href:
            full_url = href
            if not full_url.startswith("http"):
                full_url = the_url + href.lstrip("./")
            division_name = a.get_text(" ", strip=True)
            division_links.append((division_name, full_url))

    # Remove duplicates (sometimes links appear more than once)
    unique_links = []
    seen = set()
    for name, url in division_links:
        if url not in seen:
            seen.add(url)
            unique_links.append((name, url))

    return unique_links

def find_standings_table(soup):
    for table in soup.find_all("table"):
        headers = []
        thead = table.find("thead")
        if thead:
            headers = [th.get_text(" ", strip=True).upper() for th in thead.find_all("th")]
        else:
            first_tr = table.find("tr")
            if first_tr:
                headers = [td.get_text(" ", strip=True).upper() for td in first_tr.find_all(["th", "td"])]
        if any("EQUIPO" in h for h in headers):
            return table
    return None

def extract_teams_and_ids(table):
    teams = []
    for tr in table.find_all("tr"):
        if tr.find_all("th"):
            continue
        tds = tr.find_all("td")
        if len(tds) < 2:
            continue
        team_cell = tds[1]
        link = team_cell.find("a")
        team_name = ""
        team_id_raw = None
        team_id_decoded = None
        if link:
            team_name = link.get_text(" ", strip=True)
            href = link.get("href", "")
            m = re.search(r"eqdat=([^&]+)", href)
            if m:
                team_id_raw = m.group(1)
                try:
                    team_id_decoded = base64.b64decode(team_id_raw).decode("utf-8")
                except Exception:
                    team_id_decoded = team_id_raw
        else:
            team_name = team_cell.get_text(" ", strip=True)

        team_name = team_name.lstrip("0123456789. ").strip()
        if team_name:
            teams.append({
                "name": team_name,
                "id_raw": team_id_raw,
                "id": team_id_decoded
            })
    if len(teams) > 0:
        print(f"Sample extracted team: {teams[0]}")
    return teams


def scrape_division(name, url, season):
    print(f"Fetching division '{name}' -> {url}")
    r = fetch_page(url)
    soup = BeautifulSoup(r.content, "lxml")
    table = find_standings_table(soup)
    if not table:
        print(f"No standings table found for {name}")
        return []
    teams = extract_teams_and_ids(table)
    for t in teams:
        division_info = extract_category_genre_and_group_from_raw_division(name)
        t["division"] = division_info["original_name"]
        t["group"] = division_info["group"]
        t["genre"] = division_info["genre"].value
        t["category"] = division_info["category"].value
        t["url"] = f"https://www.rfetm.es/resultados/"+season.value+"/view.php?eqdat="+str(t['id_raw'])
    return teams

def scrape_null_division(url):
    return []

def extract_group_and_genre_from_division_name(division):
    division_info = {"original_name": division, "group": 1, "division": 1}
    return division_info

def extract_category_genre_and_group_from_raw_division(raw_division):
    normalized_raw_division = unidecode(raw_division.lower())
    decoded_genre = None
    decoded_category = None
    decoded_group = None

    if unidecode("Masculina".lower()) in normalized_raw_division:
        decoded_genre = Genre.MALE
    elif  unidecode("Femenina".lower()) in normalized_raw_division:
        decoded_genre = Genre.FEMALE

    if unidecode("Superdivisión".lower()) in normalized_raw_division:
        decoded_category = Category.SUPER_DIVISION
    elif  unidecode("División de Honor".lower()) in normalized_raw_division:
        decoded_category = Category.DIVISION_HONOR
    elif unidecode("Primera División".lower()) in normalized_raw_division:
        decoded_category = Category.PRIMERA_NACIONAL
    elif unidecode("1ª División".lower()) in normalized_raw_division:
        decoded_category = Category.PRIMERA_NACIONAL
    elif unidecode("Segunda División".lower()) in normalized_raw_division:
        decoded_category = Category.SEGUNDA_NACIONAL

    group_matcher = re.search(r'^(.*)Grupo (.*)$', raw_division)
    if group_matcher:
        decoded_group = lic = group_matcher.group(2)

    return {"original_name": raw_division, "category": decoded_category, "genre": decoded_genre, "group": decoded_group}

def process_teams_info_for_season(season):
    division_links = get_all_division_links_for_season(season)
    print(f"Found {len(division_links)} divisions to scrape.")

    all_teams = []
    for name, url in division_links:
        teams = []
        if name == '' or unidecode("Fase".lower()) in unidecode(name.lower()):
            #teams = scrape_null_division(url)
            pass
        else:
            teams = scrape_division(name, url, season)
            all_teams.extend(teams)

        time.sleep(0.1)  # polite delay

    csv_filename = RESOURCES_FOLDER+"/teams-info/players-urls/rfetm_teams_info_and_players_urls_"+season.value+".csv"
    save_to_csv(all_teams, csv_filename)
    print(f"Saved {len(all_teams)} teams to "+csv_filename)

if __name__ == "__main__":
    pass
    process_teams_info_for_season(Season.T_2024_2025)
    #process_teams_info_for_season(Season.T_2023_2024)
    #process_teams_info_for_season(Season.T_2022_2023)
    #process_teams_info_for_season(Season.T_2021_2022)
    #process_teams_info_for_season(Season.T_2020_2021)
    #process_teams_info_for_season(Season.T_2019_2020)
    #process_teams_info_for_season(Season.T_2018_2019)
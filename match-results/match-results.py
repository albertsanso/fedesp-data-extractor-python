# rfetm_parser.py
import re
import requests
from bs4 import BeautifulSoup
import pandas as pd
import unicodedata
import os

from common.rfetmcommons import Genre, Category, Season, RESOURCES_FOLDER, get_results_url_params_for_genre_category_all_groups

MATCH_RESULTS_FOR_SEASON_OVERVIEW_TEMPLATE_URL = "https://rfetm.es/resultados/{0}/view.php?liga={1}=&grupo={2}&subgrupo={3}&jornada={4}&sexo={5}"

MATCHES_RESULTS_FOR_YEAR_FOLDER = RESOURCES_FOLDER + "/match-results/{0}"

TIME_RE = re.compile(r'^\d{1,2}:\d{2}$')  # line is *exactly* a time like 19:30
DATE_RE = re.compile(r'^\d{1,2}/\d{1,2}/\d{4}$')  # line is a date exactly

def fetch_soup(url):
    r = requests.get(url)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")

def text_lines_from_soup(soup):
    # get a normalized list of non-empty lines
    text = soup.get_text("\n")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return lines

# helper: normalize accents + uppercase for reliable matching
def normalize(s):
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s.upper().strip()

def find_section_indices(lines, start_keyword_norm, end_keywords_norm=None):
    """Return (start_index, end_index) for a section. Returns (None, None) if not found."""
    start = None
    for i, line in enumerate(lines):
        if start_keyword_norm in normalize(line):
            start = i
            break
    if start is None:
        return None, None

    # default end = end of document
    end = len(lines)
    if end_keywords_norm:
        for j in range(start + 1, len(lines)):
            lj_norm = normalize(lines[j])
            if any(kw in lj_norm for kw in end_keywords_norm) or lines[j].startswith("* * *"):
                end = j
                break
    return start, end

def is_probable_team_line(line):
    # same heuristic as before: text containing letters but no keywords
    bad_keywords = ['ÁRBITRO', 'ARBITRO', 'POLIDEPORTIVO', 'PABELLON', 'PABELLÓN', 'TEMPORADA', 'EQUIPO', 'JORNADA', 'JORNADAS']
    if not re.search(r'[A-Za-zÁÉÍÓÚÜÑáéíóúñ]', line):
        return False
    return not any(k in line.upper() for k in bad_keywords)

def parse_matches(lines):
    matches = []
    jornada_indices = [i for i,l in enumerate(lines) if 'Jornada' in l or 'JORNADA' in l]
    jornada_indices.append(len(lines))  # sentinel

    for j in range(len(jornada_indices)-1):
        start, end = jornada_indices[j], jornada_indices[j+1]
        jornada_label = lines[start]

        i = start + 1
        current_date = None
        current_time = None

        while i < end:
            line = lines[i]

            if DATE_RE.match(line):
                current_date = line
                i += 1
                continue
            if TIME_RE.match(line):
                current_time = line
                i += 1
                continue

            # Check for team-score-score-team pattern strictly:
            if is_probable_team_line(line) and i+3 < end:
                team_a = line
                score_a_line = lines[i+1]
                score_b_line = lines[i+2]
                team_b = lines[i+3]

                # Reject if score lines are times/dates or non-digit
                if (TIME_RE.match(score_a_line) or DATE_RE.match(score_a_line) or
                    TIME_RE.match(score_b_line) or DATE_RE.match(score_b_line)):
                    i += 1
                    continue

                # Scores should be digits only (possibly with whitespace)
                if score_a_line.strip().isdigit() and score_b_line.strip().isdigit() and is_probable_team_line(team_b):
                    score_a = int(score_a_line.strip())
                    score_b = int(score_b_line.strip())

                    # Extract venue/referee similarly, or leave blank for now
                    venue = None
                    referee = None
                    # Advance i past this match
                    i += 4

                    matches.append({
                        "jornada": jornada_label,
                        "date": current_date,
                        "time": current_time,
                        "team_a": team_a,
                        "team_b": team_b,
                        "score_a": score_a,
                        "score_b": score_b,
                        "venue": venue,
                        "referee": referee
                    })
                    continue

            i += 1

    return matches

def process_matches_for(genre, category, season_year):
    all_url_params = get_results_url_params_for_genre_category_all_groups(genre, category)
    for url_params_item in all_url_params:

        group_url_param = url_params_item.get("group")
        league_id_url_param = url_params_item.get("leage_id")
        group_id_url_param = url_params_item.get("group_id")
        subgroup_id_url_param = url_params_item.get("subgroup_id")
        match_day_url_param = url_params_item.get("match_day")
        sex_url_param = url_params_item.get("sex")

        the_url = MATCH_RESULTS_FOR_SEASON_OVERVIEW_TEMPLATE_URL.format(season_year, league_id_url_param, group_id_url_param, subgroup_id_url_param, match_day_url_param, sex_url_param)

        print("Fetching page:", the_url)
        soup = fetch_soup(the_url)
        lines = text_lines_from_soup(soup)

        print("Parsing matches...")
        matches = parse_matches(lines)
        print(f"Found {len(matches)} matches.")
        df_matches = pd.DataFrame(matches)

        render_csv_file(df_matches, season_year, genre.value, category.value, group_url_param)

    return

def render_csv_file(df, season_year, genre, category, group):
    current_folder = MATCHES_RESULTS_FOR_YEAR_FOLDER.format(season_year)
    csv_file_name = f"{current_folder}/rfetm-{season_year}-{genre}-{category}-group-{group}_matches.csv"
    df.to_csv(csv_file_name, index=False, encoding="utf-8-sig")

def fetch_results_for_season(season_year):
    current_folder = MATCHES_RESULTS_FOR_YEAR_FOLDER.format(season_year)

    if not os.path.exists(current_folder):
        # shutil.rmtree(current_folder, ignore_errors=True)
        os.mkdir(current_folder)

    process_matches_for(Genre.MALE, Category.SUPER_DIVISION, season_year)
    process_matches_for(Genre.FEMALE, Category.SUPER_DIVISION, season_year)

    process_matches_for(Genre.MALE, Category.DIVISION_HONOR, season_year)
    process_matches_for(Genre.FEMALE, Category.DIVISION_HONOR, season_year)

    process_matches_for(Genre.MALE, Category.PRIMERA_NACIONAL, season_year)
    process_matches_for(Genre.FEMALE, Category.PRIMERA_NACIONAL, season_year)

    process_matches_for(Genre.MALE, Category.SEGUNDA_NACIONAL, season_year)
    process_matches_for(Genre.FEMALE, Category.SEGUNDA_NACIONAL, season_year)

if __name__ == "__main__":
    #fetch_results_for_season(Season.T_2024_2025.value)
    #fetch_results_for_season(Season.T_2023_2024.value)
    #fetch_results_for_season(Season.T_2022_2023.value)
    #fetch_results_for_season(Season.T_2021_2022.value)
    #fetch_results_for_season(Season.T_2020_2021.value)
    #fetch_results_for_season(Season.T_2019_2020.value)
    fetch_results_for_season(Season.T_2018_2019.value)
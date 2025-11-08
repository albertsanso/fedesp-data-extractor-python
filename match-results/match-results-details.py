import os

import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime
import re
from urllib.parse import urlparse, parse_qs
from pathlib import Path

from common import rfetmcommons
from common import resourceadapter

url1 = 'https://rfetm.es/resultados/2024-2025/view.php?liga=MQ==&grupo=0&subgrupo=S&jornada=0&equipo=1348&sexo=M'
url2 = 'https://rfetm.es/resultados/2024-2025/view.php?liga=Mg==&grupo=1&subgrupo=S&jornada=0&equipo=183&sexo=M'
urlK = 'https://rfetm.es/resultados/{0}      /view.php?liga={1}=&grupo={2}&subgrupo={3}&jornada={4}&sexo={5}'

URL = "https://rfetm.es/resultados/2024-2025/view.php?liga=MQ==&grupo=0&subgrupo=S&jornada=0&equipo=1348&sexo=M"
MATCH_RESULTS_FOR_SEASON_OVERVIEW_TEMPLATE_URL = "https://rfetm.es/resultados/{0}/view.php?liga={1}=&grupo={2}&subgrupo={3}&jornada={4}&sexo={5}"
TEAMS_INFO_FILENAME_TEMPLATE = "rfetm_teams_info_and_players_urls_{0}.csv"

def is_set_score(text):
    # expects '7-5' like format, digits + dash
    return bool(re.match(r'^\d{1,2}-\d{1,2}$', text)) and max(map(int, text.split('-'))) >= 7

def is_final_result(text):
    # expects '3-1' like format, digits + dash, max score <=5
    if not re.match(r'^\d+-\d+$', text):
        return False
    nums = list(map(int, text.split('-')))
    return max(nums) <= 7

def normalize(text):
    # lowercase, strip spaces, reduce multiple spaces to one
    return re.sub(r'\s+', ' ', text.strip().lower())

def parse_player_info(text):
    name = text
    lic = ""
    rnk = ""

    if name.startswith("Lic:"):
        info_matcher = re.search(r'^Lic:(\d+)Rk:(\d+\.\d)(.*)$', text)
        if info_matcher:
            lic = info_matcher.group(1)
            rnk = info_matcher.group(2)
            name = info_matcher.group(3)

        return name.strip(), lic, rnk
    else:
        return name, None, None

def parse_player_info2(element):
    player_license_id = element.next.next.next
    a_el = element.find("a")
    player_name = a_el.get_text()
    return player_name.strip(), player_license_id

def fetch_results(url):
    log_info(url)
    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')

    matches = []
    matches_id_seen = set()

    jornada_number = 0
    current_parse_section = ""

    tables = soup.find_all('table')
    jornada_header_info = None
    for table in tables:
        rows = table.find_all('tr')
        for row in rows:

            selector = "th:nth-child(2) > b > a"
            element = row.select_one(selector)
            if element is not None:

                info_matcher = re.search(r'^Jornada (\d+)$', element.get_text())
                if info_matcher:
                    jornada_number = info_matcher.group(1)
                    current_parse_section = "header-section"
                    continue

            cols = row.find_all('td')

            parsed_info_as_header = parse_for_header_jornada_info(cols)
            if parsed_info_as_header is not None:
                current_parse_section = "header-section"
                jornada_header_info = parsed_info_as_header
                continue

            parsed_body_titles_cols = parse_for_body_titles_cols(cols)
            if parsed_body_titles_cols is not None:
                current_parse_section = "body-section"
                continue

            if current_parse_section != "body-section" or len(cols) < 5:
                jornada_header_info = None
                continue

            match = parse_jornada_body_from_td_cols(cols, jornada_number, jornada_header_info, matches_id_seen)
            if match is not None:
                matches.append(match)

    return matches

def parse_for_body_titles_cols(cols):
    if len(cols) > 10 and cols[5].get_text() == 'J1' and cols[6].get_text() == 'J2' and cols[7].get_text() == 'J3':
        return {"local_team": cols[2].get_text(), "visitor_team": cols[4].get_text()}
    return None

def parse_doubles_team_info(col):
    player1_selector = "td:nth-child(2) > a:nth-child(1)"
    player2_selector = "td:nth-child(2) > a:nth-child(3)"

    doubles_player1_info = parse_double_player_1(col.select_one(player1_selector))
    doubles_player2_info = parse_double_player_2(col.select_one(player2_selector))

    return {"player-1": doubles_player1_info, "player-2": doubles_player2_info}

def parse_double_player_1(a_element):
    if a_element is not None:
        try:
            player_name = a_element.find("b").get_text()
            href_element = a_element.get("href")
            parsed_url = urlparse(href_element)
            params = parse_qs(parsed_url.query)
            player_id = params["jugador"][0]
            return {"name": player_name, "id": player_id}
        except Exception as e:
            return {"name": "", "id": ""}
    return None

def parse_double_player_2(a_element):
    if a_element is not None:
        try:
            player_name = a_element.find("b").get_text()
            href_element = a_element.get("href")
            player_id = href_element[1:-1]
            return {"name": player_name, "id": player_id}
        except Exception as e:
            return  {"name": "", "id": ""}
    return None

def parse_jornada_body_from_td_cols(cols, jornada_number, jornada_header_info, matches_id_seen):
    contender_letter_1 = cols[0].get_text(strip=True)
    contender_letter_2 = cols[2].get_text(strip=True)
    player1_text = cols[1].get_text(strip=True)
    player2_text = cols[3].get_text(strip=True)

    # <td class="tdacta" width="27%"><b>Lic:</b> 28785<br/><a href="view.php?jugador=28785&amp;tempo=MTA="><b>RIESTRA POCIÑO, MARIA</b></a></td>

    info_player1 = None
    info_player2 = None

    info_player12 = None
    info_player22 = None

    match_format = "singles"

    if player1_text.startswith("Lic:"):
        info_player1 = parse_player_info2(cols[1])
        info_player2 = parse_player_info2(cols[3])

        #info_player1 = parse_player_info(player1_text)
        #info_player2 = parse_player_info(player2_text)
        pass

    if contender_letter_1 == "D":
        info = parse_doubles_team_info(cols[1])
        info_player12 = info["player-1"]
        info_player22 = info["player-2"]
        match_format = "doubles"

    final_result = None
    set_scores = []

    # Iterate over the columns that may contain sets/final result (excluding last col)
    for td in cols[2:-1]:
        text_raw = td.get_text(strip=True)

        # Use raw text here for pattern matching!
        if is_final_result(text_raw):
            final_result = text_raw
            break
        elif is_set_score(text_raw):
            set_scores.append(text_raw)

    if final_result is None:
        #continue  # no valid final result, skip
        return None

    while len(set_scores) < 5:
        set_scores.append("")

    score_count_raw = cols[-1].get_text(strip=True)

    # Normalize strings only for duplicate checking:
    match_id = (
        normalize(player1_text),
        normalize(player2_text),
        normalize(final_result),
        normalize(score_count_raw)
    )

    if match_id in matches_id_seen:
        return None
    matches_id_seen.add(match_id)

    match = {
        "Match format": match_format,
        "Day number": jornada_number,
        "Local team id": (jornada_header_info["local_team_id"] if jornada_header_info is not None else ""),
        "Local team name": (jornada_header_info["local_team_name"] if jornada_header_info is not None else ""),
        "Visitor team id": (jornada_header_info["visitor_team_id"] if jornada_header_info is not None else ""),
        "Visitor team name": (jornada_header_info["visitor_team_name"] if jornada_header_info is not None else ""),
        "Player 1 Name": info_player1[0] if info_player1 else '',
        "Player 1 License": info_player1[1] if info_player1 else '',
        "Player 1 Letter": contender_letter_1 if contender_letter_1 else '',
        #"Player 1 Rank": info_player1[2] if info_player1 else '',
        "Player 2 Name": info_player2[0] if info_player1 else '',
        "Player 2 License": info_player2[1] if info_player1 else '',
        "Player 2 Letter": contender_letter_2 if contender_letter_1 else '',
        #"Player 2 Rank": info_player2[2] if info_player1 else '',
        "Player 1-2 Name": (info_player12["name"] if info_player12 is not None else None),
        "Player 1-2 License": (info_player12["id"] if info_player12 is not None else None),
        "Player 2-2 Name": (info_player22["name"] if info_player22 is not None else None),
        "Player 2-2 License": (info_player22["id"] if info_player22 is not None else None),
        "Set 1": set_scores[0],
        "Set 2": set_scores[1],
        "Set 3": set_scores[2],
        "Set 4": set_scores[3],
        "Set 5": set_scores[4],
        "Result": final_result,
        "Score Count": score_count_raw
    }

    return match

def parse_for_header_jornada_info(cols):
    response = {}
    if cols is None or len(cols) == 0:
        return None

    date_and_time_col = cols[0]
    datetime_info = parse_jornada_datetime_header(date_and_time_col)
    if datetime_info is None:
        return None
    response["datetime"] = datetime_info

    teams_info = parse_jornada_teams_header(cols)
    if teams_info is None:
        return None
    response["local_team_id"] = teams_info["local"]["id"]
    response["local_team_name"] = teams_info["local"]["name"]
    response["visitor_team_id"] = teams_info["visitor"]["id"]
    response["visitor_team_name"] = teams_info["visitor"]["name"]
    return response


def parse_jornada_datetime_header(datetime_col):
    # Extract date and time parts
    parts = list(datetime_col.stripped_strings)

    if len(parts) == 2:
        date_str, time_str = parts
        try:
            # Validate date format
            valid_date = datetime.strptime(date_str, '%d/%m/%Y')
            # Validate time format
            valid_time = datetime.strptime(time_str, '%H:%M')

            log_debug("Date is valid:", valid_date.strftime('%Y-%m-%d'))
            log_debug("Time is valid:", valid_time.strftime('%H:%M'))
            return {"date": date_str, "time": time_str}
        except ValueError as e:
            log_debug("Invalid date or time format:", e)
            pass
    else:
        log_debug("Unexpected format or missing date/time:", parts)
        pass
    return None

def parse_jornada_teams_header(header_cols):
    local_col_element = header_cols[1]
    local_team_name = local_col_element.get_text()
    href_element = local_col_element.find("a").get("href")
    parsed_url = urlparse(href_element)
    params = parse_qs(parsed_url.query)
    local_team_id = params["equipo"][0]

    visitor_col_element = header_cols[4]
    visitor_team_name = visitor_col_element.get_text()
    href_element = visitor_col_element.find("a").get("href")
    parsed_url = urlparse(href_element)
    params = parse_qs(parsed_url.query)
    visitor_team_id = params["equipo"][0]

    return {"visitor": {"name": visitor_team_name, "id": visitor_team_id}, "local": {"name": local_team_name, "id": local_team_id}}


def parse_for_footer_jornada_info(cols):
    return None

def process_results_details_for_team(season_year, genre, category, team_id):

    matches_results_for_year_folder = rfetmcommons.RESOURCES_FOLDER + "/match-results-details/{0}"
    current_folder = matches_results_for_year_folder.format(season_year.value)
    if not os.path.exists(current_folder):
        folder_path = Path(current_folder)
        folder_path.parent.mkdir(parents=True, exist_ok=True)


    all_url_params = rfetmcommons.get_results_url_params_for_genre_category_all_groups(genre, category)
    for url_params_item in all_url_params:

        league_id_url_param = url_params_item.get("leage_id")
        group_id_url_param = url_params_item.get("group_id")
        subgroup_id_url_param = url_params_item.get("subgroup_id")
        sex_url_param = url_params_item.get("sex")

        the_base_url = MATCH_RESULTS_FOR_SEASON_OVERVIEW_TEMPLATE_URL.format(season_year.value, league_id_url_param,
                                                                        group_id_url_param, subgroup_id_url_param,
                                                                        0, sex_url_param)
        the_url = the_base_url+'&equipo='+str(team_id)
        results = fetch_results(the_url)
        csv_file_name = f"rfetm-{season_year.value}-{genre.value}-{category.value}-group-{group_id_url_param}-teamid-{team_id}_matches.csv"
        filename_full_path = current_folder + '/' + csv_file_name
        if results:
            resourceadapter.save_to_csv(results, filename_full_path)
            log_debug("writen filename: "+filename_full_path)
        else:
            log_debug("No results found on the page.")

def process_results_for_season_all_teams(the_season):
    filename = TEAMS_INFO_FILENAME_TEMPLATE.format(the_season.value)
    teams_info = resourceadapter.load_by_module_and_file("teams-info/players-urls", filename)

    current_progress = 0
    for i, team_info in enumerate(teams_info):
        genre = rfetmcommons.Genre(team_info['genre'])
        category = rfetmcommons.Category(team_info['category'])
        group = team_info['group']
        team_id = team_info['id_raw']

        current_progress = int(100*i/len(teams_info))
        log_info(f"PROGRESS: {current_progress}%")

        process_results_details_for_team(the_season, genre, category, team_id)

def log_debug(text, args=""):
    pass
    #print(text, args)

def log_info(text, args=""):
    print(text, args)

if __name__ == "__main__":
    pass
    #process_results_details_for_team(rfetmcommons.Season.T_2023_2024, rfetmcommons.Genre.MALE, rfetmcommons.Category.SEGUNDA_NACIONAL, 151)
    #process_results_details_for_team(rfetmcommons.Season.T_2024_2025, rfetmcommons.Genre.FEMALE, rfetmcommons.Category.DIVISION_HONOR, 111)
    #process_results_for_season_all_teams(rfetmcommons.Season.T_2024_2025)
    #process_results_for_season_all_teams(rfetmcommons.Season.T_2023_2024)
    #process_results_for_season_all_teams(rfetmcommons.Season.T_2022_2023)
    process_results_for_season_all_teams(rfetmcommons.Season.T_2021_2022)
    #process_results_for_season_all_teams(rfetmcommons.Season.T_2020_2021)
    #process_results_for_season_all_teams(rfetmcommons.Season.T_2019_2020)
    #process_results_for_season_all_teams(rfetmcommons.Season.T_2018_2019)


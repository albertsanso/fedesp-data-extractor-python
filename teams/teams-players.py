import requests
from bs4 import BeautifulSoup

from common import rfetmcommons
from common import resourceadapter

TEAM_INFO_URL = "https://rfetm.es/resultados/{0}/view.php?eqdat={1}&tempo=MTA="
TEAMS_INFO_FILENAME_TEMPLATE = "rfetm_teams_info_and_players_urls_{0}.csv"

def process_for_team_players(season, genre, category, team_id, url):

    log_info(url)
    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')

    players_table_selector = "body > div > div > div.col-12.col-md-9.mt-4 > div:nth-child(4) > table:nth-child(9)"
    players_table = soup.select_one(players_table_selector)
    players_rows = players_table.find_all("tr")[1:]

    players_list = []
    for player_single_row in players_rows:
        player = parse_player_row(player_single_row, season, genre, category, team_id)
        players_list.append(player)

    return players_list

def parse_player_row(row, season, genre, category, team_id):
    cols = row.find_all('td')
    player_license = cols[0].get_text()
    player_name = cols[1].get_text()

    if season == rfetmcommons.Season.T_2018_2019:
        player_categoria = cols[2].get_text()
        player_tipo = None
        player_rk_1 = cols[3].get_text()
        player_rk_2 = cols[4].get_text()
        player_nacionalidad = cols[5].get_text()
    else:
        player_tipo = cols[2].get_text()
        player_categoria = cols[3].get_text()
        player_rk_1 = cols[4].get_text()
        player_rk_2 = cols[5].get_text()
        player_nacionalidad = cols[6].get_text()

    response = {
        "license": player_license,
        "name": player_name,
        "tipo": player_tipo,
        "categoria": player_categoria,
        "rk_1": player_rk_1,
        "rk_2": player_rk_2,
        "nacionalidad": player_nacionalidad,
        "season": season.value,
        "genre": genre.value,
        "category": category.value,
        "team_id": team_id
    }
    log_debug(response)
    return response

def process_team_data_for_season(the_season):
    filename = TEAMS_INFO_FILENAME_TEMPLATE.format(the_season.value)
    teams_info = resourceadapter.load_by_module_and_file("teams-info/players-urls", filename)

    if teams_info is None:
        return

    for i, team_info in enumerate(teams_info):
        genre = rfetmcommons.Genre(team_info['genre'])
        category = rfetmcommons.Category(team_info['category'])
        team_id = team_info['id_raw']
        url = team_info['url']

        current_progress = int(100*i/len(teams_info))
        log_info(f"PROGRESS: {current_progress}%")

        players_list = process_for_team_players(the_season, genre, category, team_id, url)
        base_folder = rfetmcommons.RESOURCES_FOLDER+"/teams-info/players-info/"+the_season.value
        csv_file_name = "rfetm_team_players_"+the_season.value+"_"+team_id+".csv"
        filename_full_path = base_folder + '/' + csv_file_name
        if players_list:
            resourceadapter.save_to_csv(players_list, filename_full_path)
            log_debug("writen filename: "+filename_full_path)
        else:
            log_debug("No results found on the page.")

def log_debug(text, args=""):
    pass
    #print(text, args)

def log_info(text, args=""):
    print(text, args)

if __name__ == "__main__":
    #process_team_data_for_season(rfetmcommons.Season.T_2024_2025)
    #process_team_data_for_season(rfetmcommons.Season.T_2023_2024)
    #process_team_data_for_season(rfetmcommons.Season.T_2022_2023)
    #process_team_data_for_season(rfetmcommons.Season.T_2021_2022)
    #process_team_data_for_season(rfetmcommons.Season.T_2020_2021)
    #process_team_data_for_season(rfetmcommons.Season.T_2019_2020)
    process_team_data_for_season(rfetmcommons.Season.T_2018_2019)
    pass

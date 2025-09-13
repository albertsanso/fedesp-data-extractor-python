from common import rfetmcommons
from common import resourceadapter

TEAM_INFO_URL = "https://rfetm.es/resultados/{0}/view.php?eqdat={1}&tempo=MTA="
TEAMS_INFO_FILENAME_TEMPLATE = "rfetm_teams_info_and_players_urls_{0}.csv"

def process_for_team(season, genre, category, team_id):
    pass

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

        process_for_team(the_season, genre, category, team_id)

def log_debug(text, args=""):
    pass
    #print(text, args)

def log_info(text, args=""):
    print(text, args)

if __name__ == "__main__":
    process_team_data_for_season(rfetmcommons.Season.T_2024_2025)
    pass

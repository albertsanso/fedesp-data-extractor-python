import os


import requests
from dataclasses import fields, asdict
from bs4 import BeautifulSoup
import csv
from datetime import datetime
import re
from urllib.parse import urlparse, parse_qs
from pathlib import Path

from common import rfetmcommons
from common import resourceadapter

import fetch_and_parse_results_v1
import fetch_and_parse_results_v2

url1 = 'https://rfetm.es/resultados/2024-2025/view.php?liga=MQ==&grupo=0&subgrupo=S&jornada=0&equipo=1348&sexo=M'
url2 = 'https://rfetm.es/resultados/2024-2025/view.php?liga=Mg==&grupo=1&subgrupo=S&jornada=0&equipo=183&sexo=M'
urlK = 'https://rfetm.es/resultados/{0}      /view.php?liga={1}=&grupo={2}&subgrupo={3}&jornada={4}&sexo={5}'

URL = "https://rfetm.es/resultados/2024-2025/view.php?liga=MQ==&grupo=0&subgrupo=S&jornada=0&equipo=1348&sexo=M"
MATCH_RESULTS_FOR_SEASON_OVERVIEW_TEMPLATE_URL = "https://rfetm.es/resultados/{0}/view.php?liga={1}=&grupo={2}&subgrupo={3}&jornada={4}&sexo={5}"
TEAMS_INFO_FILENAME_TEMPLATE = "rfetm_teams_info_and_players_urls_{0}.csv"


def process_results_details_for_team(season_year, genre, category, team_id):

    matches_results_for_year_folder = rfetmcommons.RESOURCES_FOLDER + "/match-results-details/v2/{0}"
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


        # v1
        #results = fetch_and_parse_results_v1.fetch_results(the_url)

        # v2
        results = fetch_and_parse_results_v2.parse_page(the_url)
        if results:
            keys =  results[0].keys()

            csv_file_name = f"rfetm-{season_year.value}-{genre.value}-{category.value}-group-{group_id_url_param}-teamid-{team_id}_matches.csv"
            filename_full_path = current_folder + '/' + csv_file_name
            if results:
                resourceadapter.save_to_csv(results, keys, filename_full_path)
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
    #process_results_details_for_team(rfetmcommons.Season.T_2024_2025, rfetmcommons.Genre.FEMALE, rfetmcommons.Category.DIVISION_HONOR, 1113)
    #process_results_for_season_all_teams(rfetmcommons.Season.T_2024_2025)
    #process_results_for_season_all_teams(rfetmcommons.Season.T_2023_2024)
    #process_results_for_season_all_teams(rfetmcommons.Season.T_2022_2023)
    #process_results_for_season_all_teams(rfetmcommons.Season.T_2021_2022)
    #process_results_for_season_all_teams(rfetmcommons.Season.T_2020_2021)
    process_results_for_season_all_teams(rfetmcommons.Season.T_2019_2020)
    #process_results_for_season_all_teams(rfetmcommons.Season.T_2018_2019)


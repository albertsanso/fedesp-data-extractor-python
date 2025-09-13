from enum import Enum

RESOURCES_FOLDER = "../resources"

class Genre(Enum):
    MALE = "male"
    FEMALE = "female"

class Category(Enum):
    SUPER_DIVISION = "super-divisio"
    DIVISION_HONOR = "divisio-honor"
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

URL_PARAMS = {
    Genre.MALE: {
        Category.SUPER_DIVISION: [
            {'group': '1', 'leage_id': 'MQ==', 'group_id': '0', 'subgroup_id': 'S', 'sex': 'M'}
        ],
        Category.DIVISION_HONOR: [
            {'group': '1', 'leage_id': 'Mg==', 'group_id': '1', 'subgroup_id': 'S', 'sex': 'M'},
            {'group': '2', 'leage_id': 'Mg==', 'group_id': '2', 'subgroup_id': 'S', 'sex': 'M'},
            {'group': '3', 'leage_id': 'Mg==', 'group_id': '3', 'subgroup_id': 'S', 'sex': 'M'}
        ],
        Category.PRIMERA_NACIONAL: [
            {'group': '1', 'leage_id': 'Mw==', 'group_id': '1', 'subgroup_id': 'S', 'sex': 'M'},
            {'group': '2', 'leage_id': 'Mw==', 'group_id': '2', 'subgroup_id': 'S', 'sex': 'M'},
            {'group': '3', 'leage_id': 'Mw==', 'group_id': '3', 'subgroup_id': 'S', 'sex': 'M'},
            {'group': '4', 'leage_id': 'Mw==', 'group_id': '4', 'subgroup_id': 'S', 'sex': 'M'},
            {'group': '5', 'leage_id': 'Mw==', 'group_id': '5', 'subgroup_id': 'S', 'sex': 'M'},
            {'group': '6', 'leage_id': 'Mw==', 'group_id': '6', 'subgroup_id': 'S', 'sex': 'M'}
        ],
        Category.SEGUNDA_NACIONAL: [
            {'group': '1', 'leage_id': 'NA==', 'group_id': '1', 'subgroup_id': 'S', 'sex': 'M'},
            {'group': '2', 'leage_id': 'NA==', 'group_id': '2', 'subgroup_id': 'S', 'sex': 'M'},
            {'group': '3', 'leage_id': 'NA==', 'group_id': '3', 'subgroup_id': 'S', 'sex': 'M'},
            {'group': '4', 'leage_id': 'NA==', 'group_id': '4', 'subgroup_id': 'S', 'sex': 'M'},
            {'group': '5', 'leage_id': 'NA==', 'group_id': '5', 'subgroup_id': 'S', 'sex': 'M'},
            {'group': '6', 'leage_id': 'NA==', 'group_id': '6', 'subgroup_id': 'S', 'sex': 'M'},
            {'group': '7', 'leage_id': 'NA==', 'group_id': '7', 'subgroup_id': 'S', 'sex': 'M'},
            {'group': '8', 'leage_id': 'NA==', 'group_id': '8', 'subgroup_id': 'S', 'sex': 'M'},
            {'group': '9', 'leage_id': 'NA==', 'group_id': '9', 'subgroup_id': 'S', 'sex': 'M'},
            {'group': '10', 'leage_id': 'NA==', 'group_id': '10', 'subgroup_id': 'S', 'sex': 'M'},
            {'group': '11', 'leage_id': 'NA==', 'group_id': '11', 'subgroup_id': 'S', 'sex': 'M'},
            {'group': '12', 'leage_id': 'NA==', 'group_id': '12', 'subgroup_id': 'S', 'sex': 'M'}
        ]
    },
    Genre.FEMALE: {
        Category.SUPER_DIVISION: [
            {'group': '1', 'leage_id': 'MQ==', 'group_id': '1', 'subgroup_id': 'S', 'sex': 'F'}
        ],
        Category.DIVISION_HONOR: [
            {'group': '1', 'leage_id': 'Mg==', 'group_id': '1', 'subgroup_id': 'S', 'sex': 'F'},
            {'group': '2', 'leage_id': 'Mg==', 'group_id': '2', 'subgroup_id': 'S', 'sex': 'F'},
            {'group': '3', 'leage_id': 'Mg==', 'group_id': '3', 'subgroup_id': 'S', 'sex': 'F'}
        ],
        Category.PRIMERA_NACIONAL: [
            {'group': '1', 'leage_id': 'Mw==', 'group_id': '1', 'subgroup_id': 'S', 'sex': 'F'},
            {'group': '2', 'leage_id': 'Mw==', 'group_id': '2', 'subgroup_id': 'S', 'sex': 'F'},
            {'group': '3', 'leage_id': 'Mw==', 'group_id': '3', 'subgroup_id': 'S', 'sex': 'F'},
            {'group': '4', 'leage_id': 'Mw==', 'group_id': '4', 'subgroup_id': 'S', 'sex': 'F'},
            {'group': '5', 'leage_id': 'Mw==', 'group_id': '5', 'subgroup_id': 'S', 'sex': 'F'},
            {'group': '6', 'leage_id': 'Mw==', 'group_id': '6', 'subgroup_id': 'S', 'sex': 'F'}
        ],
        Category.SEGUNDA_NACIONAL: []
    }
}

def get_results_url_params_for_genre_category_group(genre, category, group):
    return get_results_url_params_for_genre_category_all_groups(genre, category)[group-1]

def get_results_url_params_for_genre_category_all_groups(genre, category):
    male_match_results_urls = URL_PARAMS.get(genre)
    male_superdh_results_urls = male_match_results_urls.get(category)
    return [item for item in male_superdh_results_urls]

def count_groups_for_genre_category(genre, category):
    return len(URL_PARAMS.get(genre).get(category))
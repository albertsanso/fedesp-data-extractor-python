# RFETM Scraper — Functional Specification

## 1. Purpose

Scrape national table tennis league match results from the Spanish Table Tennis Federation (RFETM) public results portal (`https://rfetm.es/public/resultados`) and persist them as structured CSV files for downstream analysis.

---

## 2. Scope

| In scope | Out of scope |
|---|---|
| All national leagues (SuperDivisión, División de Honor, Primera, Segunda) | Regional / autonomous community leagues |
| Both male and female competitions | Youth / veterans categories |
| Seasons 2018-2019 → present | Seasons before 2018-2019 |
| Individual game rows per match (singles + doubles) | Player rankings, team standings |
| Venue and referee metadata | Live / in-progress match data |

---

## 3. Data Model

### 3.1 Output: one CSV row per individual game

| Column | Type | Description |
|---|---|---|
| `jornada` | string | `"Jornada N"` |
| `match_date` | string | `DD/MM/YYYY HH:MM` as shown on site |
| `home_team_id` | string | Numeric team ID from `equipo=` URL param |
| `home_team` | string | Team display name |
| `away_team_id` | string | Numeric team ID |
| `away_team` | string | Team display name |
| `match_score_home` | string | Final match score for home team |
| `match_score_away` | string | Final match score for away team |
| `venue` | string | Venue name |
| `referee` | string | Referee name |
| `home_position` | string | Position code: A/B/C/D |
| `away_position` | string | Position code: X/Y/Z/D |
| `game_type` | string | `singles` or `doubles` |
| `home_player_lic` | string | RFETM licence number |
| `home_player_name` | string | Player display name |
| `home_player2_lic` | string | Doubles partner licence (empty for singles) |
| `home_player2_name` | string | Doubles partner name |
| `away_player_lic` | string | |
| `away_player_name` | string | |
| `away_player2_lic` | string | |
| `away_player2_name` | string | |
| `set1`–`set5` | string | Set score `"H-A"`, empty if not played |
| `game_result_home` | int/string | Sets won by home player in this game |
| `game_result_away` | int/string | Sets won by away player in this game |
| `running_score_home` | int/string | Cumulative match score after this game |
| `running_score_away` | int/string | Cumulative match score after this game |

### 3.2 Output directory structure

```
{output_root}/
  {season}/
    rfetm-{season}-{genre}-{category}-group-{group_id}_matches.csv
```

Output root defaults to `../resources/match-results-details/v3-claude`.

Example files under `2024-2025/`:
```
rfetm-2024-2025-male-super-divisio-group-0_matches.csv
rfetm-2024-2025-male-divisio-honor-group-1_matches.csv
rfetm-2024-2025-male-divisio-honor-group-2_matches.csv
rfetm-2024-2025-female-super-divisio-group-0_matches.csv
rfetm-2024-2025-female-primera-nacional-group-3_matches.csv
```

One flat folder per season. No sub-folders for genre or category — all files for a season share the same depth level.

---

## 4. URL Parameters

### 4.1 Pattern

```
https://rfetm.es/public/resultados/{season}/view.php
  ?liga={league_id}
  &grupo={group_id}
  [&subgrupo={subgroup_id}]   # omitted entirely for seasons 2018-2019, 2019-2020, 2020-2021
  &jornada={n}                # 0 = overview/all jornadas, N = specific round
  &sexo={sex}                 # M | F
```

### 4.2 League ID mapping

| Category | `liga` value |
|---|---|
| SuperDivisión | `MQ==` |
| División de Honor | `Mg==` |
| Primera Nacional | `Mw==` |
| Segunda Nacional | `NA==` |

### 4.3 Subgroup

- Seasons ≥ 2021-2022: `subgrupo=S`
- Seasons 2018-2019, 2019-2020, 2020-2021: `subgrupo` parameter **omitted entirely** (not set to empty — the server returns no data if the parameter is present but empty)

### 4.4 Season discovery

Seasons are scraped from `https://rfetm.es/public/resultados`. Season links appear as `<a href=".../{YYYY-YYYY}/...">`. The `Season` enum and `URL_PARAMS` dict must be kept in sync with the live site (see `prompts.md`).

---

## 5. Parsing Rules

### 5.1 Page structure

Each jornada page contains:
1. **Jornada label tables** — small tables (≤2 TDs) whose text matches `"Jornada N"`. Used as section delimiters; match tables are only processed after one has been seen.
2. **Match summary tables** — contain a DD/MM/YYYY date and ≥2 anchor tags.
3. **Detail tables** — either nested inside the match summary table as `<table>`, or the immediately following `<table>` in page order.

### 5.2 Home/away determination

The detail table header row (TR[0]) contains the left-team name at td[1] and right-team name at td[3]. `left_is_home = (left_team_header == home_team)` using exact string match after whitespace normalisation via `_clean()`.

### 5.3 Player cells

- Singles: one `<a href="?jugador=LIC">NAME</a>`
- Doubles: two `<a>` tags; second player may use `href="#LIC#"` pattern

### 5.4 Game type

`"doubles"` when either the home or away player list has more than one entry; `"singles"` otherwise.

### 5.5 Score parsing

Set scores, game results and running scores use regex `(\d+)\s*[–\-]\s*(\d+)` to handle both standard hyphens and en-dash characters.

---

## 6. Configuration (`URL_PARAMS`)

`URL_PARAMS` is a nested dict keyed `Season → Genre → Category → list[ParamDict]` where each `ParamDict` has:

```python
{
    "league_id":   str,        # base64 encoded e.g. "MQ=="
    "group_id":    str,        # "0" for single-group, "1".."N" for multi-group
    "subgroup_id": str | None, # "S" for 2021+, None for older seasons
    "sex":         str,        # "M" | "F"
}
```

An empty list `[]` means the category does not exist for that season/genre combination.

---

## 7. Programmatic Interface

```python
from rfetm_scraper import main

main(
    season   = "2024-2025",
    genre    = None,       # None = both male and female
    category = None,       # None = all categories
    group    = None,       # None = all groups
    jornada  = None,       # None = all rounds
    output   = "../resources/match-results-details/v3-claude",
    delay    = 1.0,
)
```

---

## 8. CLI Interface

```
python rfetm_scraper.py [options]

--season    Season string e.g. "2024-2025"   default: "2024-2025"
--genre     male | female
--category  super-divisio | divisio-honor | primera-nacional | segona-nacional
--group     group_id integer
--jornada   scrape only this round number
--output    output directory   default: ../resources/match-results-details/v3-claude
--delay     seconds between requests   default: 1.0
```

---

## 9. Error Handling

- HTTP errors: retry up to 3 times with exponential back-off (1s, 2s, 4s)
- Empty jornada list on overview page: log warning, skip group
- Unparseable score/date fields: emit empty string, continue
- No rows extracted from a group: log warning, skip CSV write

---

## 10. Known Constraints

- The site serves HTML only; no public API exists
- `requests.Session` with `User-Agent` header required to avoid 403s
- `subgrupo` must be omitted (not empty) for older seasons
- Flat `find_all("table")` walk required — match tables are nested inside a layout table; sibling-TR strategies do not work
- `current_jornada` gating required — without it, layout/nav tables that happen to contain a date are misidentified as match tables
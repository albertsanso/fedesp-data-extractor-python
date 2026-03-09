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
| `game_result_home` | int/string | Sets won by home player |
| `game_result_away` | int/string | Sets won by away player |
| `running_score_home` | int/string | Cumulative match score after this game |
| `running_score_away` | int/string | Cumulative match score after this game |

### 3.2 Output directory structure

```
output/
  {season}/          e.g. 2024-2025
    {genre}/         male | female
      {category}/    super-divisio | divisio-honor | primera-nacional | segona-nacional
        grupo_{n}.csv
```

---

## 4. URL Parameters

### 4.1 Pattern

```
https://rfetm.es/public/resultados/{season}/view.php
  ?liga={league_id}
  &grupo={group_id}
  [&subgrupo={subgroup_id}]   # omitted for seasons 2018-2019, 2019-2020, 2020-2021
  &jornada={n}                # 0 = overview/all, N = specific round
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
- Seasons 2018-2019, 2019-2020, 2020-2021: `subgrupo` parameter omitted entirely

### 4.4 Season discovery

Seasons available on the site can be scraped from the overview page at `https://rfetm.es/public/resultados`. Season links appear as `<a href=".../{YYYY-YYYY}/...">`. The `Season` enum and `URL_PARAMS` dict must be kept in sync with the live site.

---

## 5. Parsing Rules

### 5.1 Page structure

Each jornada page contains:
1. **Jornada label tables** — small tables (≤2 TDs) whose text matches `"Jornada N"`. Used as section delimiters.
2. **Match summary tables** — contain a DD/MM/YYYY date and ≥2 anchor tags. Processed only after a jornada label has been seen.
3. **Detail tables** — either nested inside the match summary table as `<table>`, or the immediately following `<table>` in page order.

### 5.2 Home/away determination

The detail table header row contains left-team (td[1]) and right-team (td[3]) names. `left_is_home = (left_team_header == home_team)` (exact string match after whitespace normalisation).

### 5.3 Player cells

- Singles: one `<a href="?jugador=LIC">NAME</a>`
- Doubles: two `<a>` tags; second player may use `href="#LIC#"` pattern

### 5.4 Game type

`doubles` when either home or away player list has more than one entry; `singles` otherwise.

---

## 6. Configuration (`URL_PARAMS`)

`URL_PARAMS` is a nested dict keyed `Season → Genre → Category → list[params]` where each `params` dict has keys: `league_id`, `group_id`, `subgroup_id`, `sex`.

Adding a new season requires:
1. Adding a `Season` enum member
2. Adding a `URL_PARAMS` entry with correct group counts per category

Group counts must be verified empirically by checking `jornada=0` pages on the live site (see [Season Discovery Prompt](#season-discovery-prompt) in `prompts.md`).

---

## 7. CLI Interface

```
python rfetm_scraper.py [options]

--season    Season string e.g. "2024-2025"   default: "2024-2025"
--genre     male | female
--category  super-divisio | divisio-honor | primera-nacional | segona-nacional
--group     group_id integer
--jornada   scrape only this round number
--output    output directory                  default: "output"
--delay     seconds between requests          default: 1.0
```

---

## 8. Error Handling

- HTTP errors: retry up to 3 times with exponential back-off (1s, 2s, 4s)
- Empty jornada list on overview page: log warning, skip group
- Unparseable score/date fields: emit empty string, continue
- No rows extracted from a group: log warning, skip CSV write

---

## 9. Known Constraints

- The site serves HTML only; no public API exists
- `requests.Session` with `User-Agent` header required to avoid 403s
- `subgrupo` parameter must be omitted (not set to empty) for older seasons or the server returns no data
- `find_all("table")` flat walk is required because match tables are nested inside a layout table — sibling-TR strategies do not work
# RFETM Scraper

Scrapes national table tennis league match results from the Spanish Table Tennis Federation (RFETM) public results portal and saves them as structured CSV files for downstream analysis.

**Source:** https://rfetm.es/public/resultados  
**Output:** one CSV row per individual game (singles or doubles) within each match

---

## Requirements

- Python 3.9+
- `requests`
- `beautifulsoup4`

```bash
pip install requests beautifulsoup4
```

---

## Quick Start

```bash
# Scrape the current season (2024-2025), all categories and groups
python rfetm_scraper.py

# Specific season
python rfetm_scraper.py --season 2022-2023

# Narrow down further
python rfetm_scraper.py --season 2024-2025 --genre male --category super-divisio

# Single jornada only
python rfetm_scraper.py --season 2024-2025 --genre male --category super-divisio --jornada 3
```

---

## CLI Options

| Option | Default | Description |
|---|---|---|
| `--season` | `2024-2025` | Season string e.g. `2022-2023` |
| `--genre` | all | `male` or `female` |
| `--category` | all | See categories below |
| `--group` | all | Group number e.g. `0`, `1`, `2` |
| `--jornada` | all | Scrape only this round number |
| `--output` | `../resources/match-results-details/v3-claude` | Output root directory |
| `--delay` | `1.0` | Seconds between HTTP requests |

### Categories

| `--category` value | Competition |
|---|---|
| `super-divisio` | SuperDivisión |
| `divisio-honor` | División de Honor |
| `primera-nacional` | Primera Nacional |
| `segona-nacional` | Segunda Nacional |

---

## Output Structure

```
../resources/match-results-details/v3-claude/
  {season}/
    rfetm-{season}-{genre}-{category}-group-{group_id}_matches.csv
```

One flat folder per season — no sub-folders for genre or category.

Example files under `2024-2025/`:
```
rfetm-2024-2025-male-super-divisio-group-0_matches.csv
rfetm-2024-2025-male-divisio-honor-group-1_matches.csv
rfetm-2024-2025-male-divisio-honor-group-2_matches.csv
rfetm-2024-2025-female-super-divisio-group-0_matches.csv
rfetm-2024-2025-female-primera-nacional-group-3_matches.csv
```

### CSV Columns

| Column | Description |
|---|---|
| `jornada` | Round label e.g. `Jornada 3` |
| `match_date` | Date and time as shown on site |
| `home_team_id` / `away_team_id` | Numeric RFETM team ID |
| `home_team` / `away_team` | Team display name |
| `match_score_home` / `match_score_away` | Final match score |
| `venue` | Venue name |
| `referee` | Referee name |
| `home_position` / `away_position` | Position code (A/B/C/D or X/Y/Z/D) |
| `game_type` | `singles` or `doubles` |
| `home_player_lic` / `away_player_lic` | RFETM licence number |
| `home_player_name` / `away_player_name` | Player display name |
| `home_player2_*` / `away_player2_*` | Doubles partner (empty for singles) |
| `set1`–`set5` | Set score `H-A`, empty if not played |
| `game_result_home` / `game_result_away` | Sets won in this game |
| `running_score_home` / `running_score_away` | Cumulative match score after this game |

---

## Programmatic Usage

```python
from rfetm_scraper import main

# Default: 2024-2025, all genres, all categories
main()

# Single season and genre
main(season="2024-2025", genre="female")

# Targeted: single group, single jornada
main(season="2024-2025", genre="male", category="super-divisio", group="0", jornada=3)

# Custom output path and request rate
main(season="2023-2024", output="/data/rfetm", delay=2.0)
```

`main()` is a clean Python function — no `sys.argv` parsing. The CLI entry point (`__main__`) is separate and calls `main()` with explicit keyword arguments.

---

## Covered Seasons

| Season | Notes |
|---|---|
| 2024-2025 | Current season (default) |
| 2023-2024 | |
| 2022-2023 | |
| 2020-2021 | No `subgrupo` parameter in URLs |
| 2019-2020 | No `subgrupo` parameter in URLs |
| 2018-2019 | No `subgrupo` parameter in URLs |

> Season 2021-2022 is absent from the RFETM site (COVID interruption).

---

## Adding a New Season

1. Run the **Season Discovery Prompt** in `prompts.md` to probe the live site for valid groups.
2. Add a `Season` enum member:
   ```python
   T_2025_2026 = "2025-2026"
   ```
3. Add the corresponding `URL_PARAMS` entry following the existing pattern.
   Use `subgroup_id="S"` for seasons 2021-2022 and later; `None` for older.

See `prompts.md` for ready-to-use AI prompts that automate all three steps.

---

## Project Files

| File | Description |
|---|---|
| `rfetm_scraper.py` | Main scraper script |
| `spec.md` | Functional specification — data model, URL rules, parsing rules, interfaces |
| `architecture.md` | Technical architecture — module map, data flow, design decisions |
| `prompts.md` | AI prompts and skill definition for maintaining `URL_PARAMS` |
| `README.md` | This file |

---

## Notes

- Requests are spaced by `--delay` seconds to be respectful to the server.
- HTTP errors are retried up to 3 times with exponential back-off.
- The scraper reads HTML only; the site has no public API.
- A `User-Agent` header is required — the server returns 403 without one.
- The `subgrupo` URL parameter must be **omitted entirely** for seasons before 2021-2022; setting it to an empty value causes the server to return no data.
# RFETM Scraper

Scrapes national table tennis league match results from the Spanish Table Tennis Federation (RFETM) public results portal and saves them as structured CSV files.

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

# Single jornada
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
| `--output` | `output` | Output directory |
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
output/
  {season}/
    {genre}/
      {category}/
        grupo_{n}.csv
```

Example: `output/2024-2025/male/super-divisio/grupo_0.csv`

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

# Single season, single genre
main(season="2024-2025", genre="female")

# Single group, single jornada
main(season="2024-2025", genre="male", category="super-divisio", group="0", jornada=3)

# Custom output directory, slower request rate
main(season="2023-2024", output="data", delay=2.0)
```

---

## Covered Seasons

| Season | Notes |
|---|---|
| 2024-2025 | Current season |
| 2023-2024 | |
| 2022-2023 | |
| 2020-2021 | No subgrupo parameter in URLs |
| 2019-2020 | No subgrupo parameter in URLs |
| 2018-2019 | No subgrupo parameter in URLs |

> **Note:** Season 2021-2022 is not present on the RFETM site (COVID interruption).

---

## Adding a New Season

1. Use the **Season Discovery Prompt** in `prompts.md` to probe the live site for valid groups.
2. Add a `Season` enum member to `rfetm_scraper.py`:
   ```python
   T_2025_2026 = "2025-2026"
   ```
3. Add the corresponding `URL_PARAMS` entry following the existing pattern.  
   Use `subgroup_id="S"` for seasons 2021-2022 and later; `None` for older seasons.

See `prompts.md` for ready-to-use AI prompts that automate steps 1–3.

---

## Project Files

| File | Description |
|---|---|
| `rfetm_scraper.py` | Main scraper script |
| `spec.md` | Functional specification (data model, URL rules, parsing rules) |
| `architecture.md` | Technical architecture (module map, data flow, design decisions) |
| `prompts.md` | AI prompts and skill definition for maintaining `URL_PARAMS` |
| `README.md` | This file |

---

## Notes

- Requests are spaced by `--delay` seconds to be respectful to the server.
- HTTP errors are retried up to 3 times with exponential back-off.
- The scraper reads HTML only; the site has no public API.
- A `User-Agent` header is required — the server returns 403 without one.
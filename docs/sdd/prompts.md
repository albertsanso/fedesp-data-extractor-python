# RFETM Scraper — Prompts & Skills

Reusable prompts and skill definitions for maintaining `rfetm_scraper.py`,
primarily for keeping `URL_PARAMS` and the `Season` enum in sync with the live site.

---

## Prompt 1 — Season Discovery

Use this to find all seasons currently available on the RFETM site and their group structure.

```
You are helping maintain a Python scraper for https://rfetm.es/public/resultados

### Task
Fetch the RFETM results overview page and discover all available seasons and
their group structure so I can update URL_PARAMS in rfetm_scraper.py.

### Steps

1. Fetch https://rfetm.es/public/resultados
   Extract all season strings matching pattern YYYY-YYYY from href attributes.
   Report the full list.

2. For each season found, and for each combination of:
   - sex: M and F
   - league_id: MQ== (SuperDiv), Mg== (DivHonor), Mw== (Primera), NA== (Segunda)
   - subgroup_id: use "S" if season year >= 2021, omit the parameter entirely if older

   Probe grupo values starting from 0, then 1, 2, 3... up to 20.
   For each grupo, fetch:
     https://rfetm.es/public/resultados/{season}/view.php?liga={league_id}&grupo={grupo}[&subgrupo={subgroup_id}]&jornada=0&sexo={sex}
   A grupo is VALID if the page contains at least one <a> tag with "equipo=" in the href.
   Stop probing when two consecutive grupos return no equipo= links.

3. Produce a summary table:

   Season     | Sex | Category          | Valid grupos
   -----------|-----|-------------------|-------------
   2024-2025  | M   | SuperDivisión     | [0]
   2024-2025  | M   | División de Honor | [1, 2, 3]
   ...

4. Flag any season/category/sex combinations that exist in the current
   URL_PARAMS but are no longer valid on the live site.

5. Flag any new seasons found on the live site that are missing from URL_PARAMS.
```

---

## Prompt 2 — Add a Single New Season

Use after Prompt 1. Paste the discovery output alongside this prompt.

```
You are updating rfetm_scraper.py to add a new season to URL_PARAMS.

### Current Season enum and URL_PARAMS
[PASTE THE Season ENUM AND URL_PARAMS DICT HERE]

### Discovery data for the new season
[PASTE OUTPUT FROM PROMPT 1 HERE]

### Rules
- _p(sex, league_id, group_id, subgroup_id) is the param factory.
  sex is "M" or "F". subgroup_id is "S" for seasons >= 2021, None for older.
- league_id mapping:
    SuperDivisión      → "MQ=="
    División de Honor  → "Mg=="
    Primera Nacional   → "Mw=="
    Segunda Nacional   → "NA=="
- Empty list [] means the category does not exist for that season/genre.
- grupo=0 with a single entry = single-group category (SuperDiv pattern).
- Multi-group categories use range(1, N+1) where N is the highest valid grupo.

### Task
1. Add the new Season enum member following the naming pattern T_YYYY_YYYY = "YYYY-YYYY".
2. Add the complete URL_PARAMS entry for the new season, matching the existing structure.
3. Output only the new Season enum line and the new URL_PARAMS block — not the full file.
```

---

## Prompt 3 — Full URL_PARAMS Sync

Use for a complete rebuild from scratch after a full discovery run.

```
You are rebuilding URL_PARAMS in rfetm_scraper.py from scratch based on a
fresh discovery of the live RFETM site.

### Current scraper (do not change anything except URL_PARAMS and Season enum)
[PASTE FULL rfetm_scraper.py HERE]

### Fresh discovery data (all seasons, all categories, all groups)
[PASTE OUTPUT FROM PROMPT 1 HERE]

### Rules
- Preserve all existing seasons that are still valid on the site.
- Add any new seasons found.
- Comment out (do not delete) seasons that no longer exist on the site.
- Use _p(sex, league_id, group_id, subgroup_id) for all entries.
- subgroup_id = "S" for seasons 2021-2022 and later, None for older.
- league_id: MQ== SuperDiv, Mg== DivHonor, Mw== Primera, NA== Segunda.
- Empty list [] for category/genre combinations with no valid groups.
- Output the complete updated Season enum and URL_PARAMS dict only.
```

---

## Prompt 4 — Spot-check a Single URL

Use to verify one specific URL returns valid data before adding it to config.

```
Verify that this RFETM URL returns valid match data:

  {PASTE URL HERE}

Fetch the URL and check:
1. Does the page contain at least one table with a DD/MM/YYYY date?
2. Does it contain at least two <a href> tags with "equipo=" in the href?
3. Does it contain a nested <table> inside a match table (the detail table)?

Report: VALID (with match count) or INVALID (with reason).
If invalid, suggest a corrected URL based on these rules:
- subgrupo=S for seasons >= 2021, omit for older
- grupo=0 for SuperDivisión, grupo=1..N for other categories
- sexo=M or sexo=F
```

---

## Skill: rfetm-url-params-update

Structured skill definition for loading into an AI system prompt or skill file.
Gives the assistant persistent context for all URL_PARAMS update tasks.

```
SKILL: rfetm-url-params-update
VERSION: 1.1

PURPOSE:
  Update URL_PARAMS and the Season enum in rfetm_scraper.py to reflect
  the current state of https://rfetm.es/public/resultados

SCRIPT LOCATION: rfetm_scraper.py
OUTPUT ROOT: ../resources/match-results-details/v3-claude

FILE NAMING CONVENTION:
  {output_root}/{season}/rfetm-{season}-{genre}-{category}-group-{group_id}_matches.csv
  Example: ../resources/match-results-details/v3-claude/2024-2025/rfetm-2024-2025-male-super-divisio-group-0_matches.csv

URL STRUCTURE:
  https://rfetm.es/public/resultados/{season}/view.php
    ?liga={league_id}&grupo={group_id}[&subgrupo={subgroup_id}]&jornada={n}&sexo={sex}

KEY FACTS:
  - subgrupo="S" for seasons >= 2021-2022; omit entirely for older seasons
  - liga: MQ== SuperDiv, Mg== DivHonor, Mw== Primera, NA== Segunda
  - A grupo is valid if jornada=0 page contains equipo= links
  - Season enum naming: T_YYYY_YYYY = "YYYY-YYYY"
  - _p(sex, league_id, group_id, subgroup_id) builds a param dict
  - main() is a pure programmatic function; CLI lives in __main__ block only

DISCOVERY PROCEDURE:
  1. Fetch https://rfetm.es/public/resultados, extract YYYY-YYYY from hrefs
  2. For each season × sex × league × grupo (0..20):
     - Fetch jornada=0 page; valid if contains "equipo=" in any href
     - Stop after 2 consecutive invalid grupos
  3. Build new Season enum member + URL_PARAMS entry

OUTPUT FORMAT (when updating):
  (a) New/changed Season enum lines
  (b) New/changed URL_PARAMS blocks
  (c) Summary: added seasons, removed seasons, changed group counts
  Do not output the full file unless explicitly asked.

VALIDATION:
  After proposing changes, verify at least one URL per new season by fetching
  the SuperDivisión grupo=0 jornada=0 page for both sexo=M and sexo=F.
```
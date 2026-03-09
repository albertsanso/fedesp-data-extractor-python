# RFETM Scraper — Prompts & Skills

This file contains reusable prompts you can paste directly to an AI assistant
to automate common maintenance tasks on `rfetm_scraper.py`.

---

## Prompt 1 — Season Discovery

Use this prompt when you want to find out what seasons are currently available
on the RFETM site and what groups each category has, before updating the code.

```
You are helping maintain a Python scraper for https://rfetm.es/public/resultados

### Task
Fetch the RFETM results overview page and discover all available seasons and
their group structure so I can update URL_PARAMS in rfetm_scraper.py.

### Steps to follow

1. Fetch https://rfetm.es/public/resultados
   Extract all season strings matching pattern YYYY-YYYY from href attributes.
   Report the full list.

2. For each season found, and for each combination of:
   - sex: M and F
   - league_id: MQ== (SuperDiv), Mg== (DivHonor), Mw== (Primera), NA== (Segunda)
   - subgroup_id: use "S" if season year >= 2021, omit the parameter if older

   Probe grupo values starting from 0, then 1, 2, 3... up to 20.
   For each grupo, fetch:
     https://rfetm.es/public/resultados/{season}/view.php?liga={league_id}&grupo={grupo}[&subgrupo={subgroup_id}]&jornada=0&sexo={sex}
   A grupo is VALID if the page contains at least one <a> tag with "equipo=" in the href.
   Stop probing when two consecutive grupos return no equipo= links.

3. Produce a summary table like:

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

## Prompt 2 — Add a Single New Season to URL_PARAMS

Use this after running Prompt 1 to get the discovery data, then paste both
the discovery output and this prompt together.

```
You are updating rfetm_scraper.py to add a new season to URL_PARAMS.

### Context
Here is the current Season enum and URL_PARAMS structure from rfetm_scraper.py:

[PASTE THE Season ENUM AND URL_PARAMS DICT HERE]

### Discovery data
Here is the group structure discovered for the new season:

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
- grupo=0 with a single entry means it is a single-group category (SuperDiv).
- Multi-group categories use range(1, N+1) where N is the highest valid grupo.

### Task
1. Add the new Season enum member following the existing naming pattern
   T_YYYY_YYYY = "YYYY-YYYY".
2. Add the complete URL_PARAMS entry for the new season, following the exact
   structure of the existing entries.
3. Output only the new Season enum member line and the new URL_PARAMS block.
   Do not output the full file.
```

---

## Prompt 3 — Full URL_PARAMS Sync

Use this to regenerate the entire URL_PARAMS from scratch based on a fresh
discovery run. More thorough than Prompt 2.

```
You are rebuilding the URL_PARAMS configuration in rfetm_scraper.py from scratch
based on a fresh discovery of the live RFETM site.

### Current scraper skeleton (do not change anything except URL_PARAMS and Season enum)
[PASTE FULL rfetm_scraper.py HERE]

### Fresh discovery data (all seasons, all categories, all groups)
[PASTE OUTPUT FROM PROMPT 1 HERE]

### Rules
- Preserve all existing seasons that are still valid.
- Add any new seasons found.
- Remove seasons that no longer exist on the site (comment them out, do not delete).
- Use _p(sex, league_id, group_id, subgroup_id) for all entries.
- subgroup_id = "S" for seasons 2021-2022 and later, None for older seasons.
- league_id mapping:
    MQ== → SuperDivisión
    Mg== → División de Honor
    Mw== → Primera Nacional
    NA== → Segunda Nacional
- Empty list [] for category/genre combinations with no valid groups.
- Output the complete updated Season enum and URL_PARAMS dict only.
```

---

## Prompt 4 — Verify a Specific Season/Group

Use this for a quick spot-check of one specific URL to confirm it returns data.

```
Verify that this RFETM URL returns valid match data:

  {PASTE URL HERE}

Fetch the URL and check:
1. Does the page contain at least one table with a DD/MM/YYYY date?
2. Does it contain at least two <a href> tags with "equipo=" in the href?
3. Does it contain a nested <table> inside a match table (the detail table)?

Report: VALID (with match count) or INVALID (with reason).
If invalid, suggest the corrected URL based on the URL parameter rules:
- subgrupo=S for seasons >= 2021, omit for older
- grupo=0 for SuperDivisión, grupo=1..N for other categories
- sexo=M or sexo=F
```

---

## Skill: URL_PARAMS Season Update

This is a structured skill definition you can load into an AI system prompt
or skill file to give the assistant persistent context for update tasks.

```
SKILL: rfetm-url-params-update
VERSION: 1.0

PURPOSE:
  Update the URL_PARAMS configuration and Season enum in rfetm_scraper.py
  to reflect the current state of https://rfetm.es/public/resultados

CONTEXT:
  rfetm_scraper.py scrapes Spanish Table Tennis Federation match results.
  URL_PARAMS is a nested dict: Season → Genre → Category → list[ParamDict].
  Each ParamDict has: league_id, group_id, subgroup_id, sex.

KEY FACTS:
  - Base URL: https://rfetm.es/public/resultados/{season}/view.php
  - Parameters: liga, grupo, [subgrupo], jornada, sexo
  - subgrupo="S" for seasons 2021-2022 and later; omit entirely for older
  - liga values: MQ== SuperDiv, Mg== DivHonor, Mw== Primera, NA== Segunda
  - A grupo is valid if the jornada=0 page contains equipo= links
  - Season enum naming: T_YYYY_YYYY = "YYYY-YYYY"
  - _p(sex, league_id, group_id, subgroup_id) builds a param dict

DISCOVERY PROCEDURE:
  1. Fetch https://rfetm.es/public/resultados
  2. Extract YYYY-YYYY patterns from hrefs
  3. For each season × sex × league × grupo (0..20):
     - Fetch jornada=0 page
     - Valid if contains "equipo=" in any href
     - Stop probing after 2 consecutive invalid grupos
  4. Build new Season enum + URL_PARAMS

OUTPUT FORMAT:
  When asked to update URL_PARAMS, output:
  (a) New/changed Season enum lines
  (b) New/changed URL_PARAMS blocks
  (c) Summary of changes (added seasons, removed seasons, changed group counts)
  Never output the full file unless explicitly asked.

VALIDATION:
  After proposing changes, verify at least one URL per new season by fetching
  the SuperDivisión grupo=0 jornada=0 page for both sexo=M and sexo=F.
```
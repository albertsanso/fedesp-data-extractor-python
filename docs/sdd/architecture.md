# RFETM Scraper — Architecture

## 1. Module Overview

Single-file Python script: `rfetm_scraper.py`

```
rfetm_scraper.py
│
├── Enums & Config
│   ├── Genre          (MALE, FEMALE)
│   ├── Category       (SUPER_DIVISION, DIVISION_HONOR, PRIMERA_NACIONAL, SEGUNDA_NACIONAL)
│   ├── Season         (T_2018_2019 → T_2024_2025)
│   ├── _p()           param dict factory
│   └── URL_PARAMS     Season → Genre → Category → list[ParamDict]
│
├── HTTP Layer
│   ├── SESSION        requests.Session with User-Agent header
│   └── fetch(url)     GET with retry + exponential back-off → BeautifulSoup | None
│
├── URL Builder
│   └── build_url(season, params, jornada) → str
│
├── Helpers
│   ├── _clean(text)               whitespace normalisation
│   ├── get_jornada_numbers(soup)  extract round numbers from overview page
│   ├── parse_player_cell(td)      → list[{lic, name}]
│   └── same_team(a, b)            fuzzy team name equality (reference only)
│
├── Page Parser
│   ├── _parse_match_block(jornada_label, match_table, detail_table) → list[dict]
│   └── parse_page(soup, jornada_num) → list[dict]
│
├── Orchestration
│   └── scrape_group(season, params, only_jornada) → list[dict]
│
├── Output
│   └── write_csv(rows, path)
│
├── Programmatic Entry Point
│   └── main(season, genre, category, group, jornada, output, delay)
│
└── CLI Entry Point  (__main__ block)
    └── argparse → main(...)
```

---

## 2. Data Flow

```
__main__ (CLI) or import call
  │
  └─ main(season, genre, category, group, jornada, output, delay)
       │
       ├─ resolve Season / Genre / Category enums from string args
       │
       └─ for each (season, genre, category, params):
            │
            └─ scrape_group(season, params, only_jornada)
                 │
                 ├─ fetch(overview_url jornada=0)
                 ├─ get_jornada_numbers(soup)
                 │
                 └─ for each jornada N:
                      ├─ fetch(jornada_url)
                      ├─ parse_page(soup, N)
                      │    │
                      │    └─ walk all_tables[]
                      │         ├─ detect Jornada label → set current_jornada
                      │         └─ detect match table (after jornada gate)
                      │              ├─ find nested detail table (or all_tables[i+1])
                      │              └─ _parse_match_block()
                      │                   ├─ extract date, teams, scores from match table
                      │                   ├─ extract venue + referee from detail rows
                      │                   ├─ determine left_is_home (exact string match)
                      │                   └─ for each game row → dict
                      │
                      └─ write_csv(rows, {output}/{season}/rfetm-{season}-{genre}-{category}-group-{id}_matches.csv)
```

---

## 3. Output Path Construction

```python
csv_path = os.path.join(
    output,        # e.g. ../resources/match-results-details/v3-claude
    s.value,       # e.g. 2024-2025
    f"rfetm-{s.value}-{g.value}-{c.value}-group-{params['group_id']}_matches.csv"
)
# → ../resources/match-results-details/v3-claude/2024-2025/rfetm-2024-2025-male-super-divisio-group-0_matches.csv
```

Depth is always `output_root / season / filename` — flat within each season folder.

---

## 4. Key Design Decisions

### 4.1 Flat `find_all("table")` walk

The site wraps all content in a layout `<table>`. Using `find_all("tr", recursive=False)` or sibling-TR strategies fails because match tables are not top-level. The working strategy:

1. Collect `soup.find_all("table")` — all tables regardless of nesting depth
2. Walk by integer index `i`
3. Use the jornada label table as a sentinel; only process match tables after one has been seen
4. Look for the detail table as either `table.find("table")` (nested) or `all_tables[i+1]`

### 4.2 `current_jornada` gating

Without the jornada sentinel, navigation/layout tables early in the page that happen to contain a date and links would be misidentified as match tables. The gate ensures we only parse content inside a jornada section.

### 4.3 `left_is_home` via exact equality

The detail table header contains verbatim team names. Exact match after `_clean()` is correct and more reliable than fuzzy matching, which risks false positives when team names share substrings.

### 4.4 `subgroup_id = None` for old seasons

`build_url()` omits the `&subgrupo=` parameter entirely when `subgroup_id is None`. Setting it to an empty string causes the server to return no results.

### 4.5 Separated programmatic and CLI entry points

`main()` is a pure Python function with typed parameters and defaults. All argparse logic lives exclusively in the `if __name__ == "__main__"` block, which calls `main()` with explicit keyword arguments. This avoids `sys.argv` inspection inside `main()`, making it safe to call from notebooks, test suites, and other scripts.

---

## 5. `URL_PARAMS` Configuration Schema

```python
URL_PARAMS: dict[Season, dict[Genre, dict[Category, list[ParamDict]]]]

ParamDict = {
    "league_id":    str,        # base64 encoded e.g. "MQ=="
    "group_id":     str,        # "0" for single-group, "1".."N" for multi-group
    "subgroup_id":  str | None, # "S" for seasons >= 2021, None for older
    "sex":          str,        # "M" | "F"
}
```

Empty list `[]` means the category does not exist for that season/genre combination.

---

## 6. Season Discovery (future automation)

To auto-populate `URL_PARAMS` for a new season:

1. Fetch `https://rfetm.es/public/resultados` and extract season strings matching `YYYY-YYYY`
2. For each new season × (genre, category): probe `grupo=0,1,2,...` on `jornada=0` pages until two consecutive grupos return no `equipo=` links
3. Determine `subgroup_id`: `"S"` if season year ≥ 2021, else `None`
4. Emit new `Season` enum member + `URL_PARAMS` entry

This process is codified as ready-to-use prompts in `prompts.md`.

---

## 7. Extension Points

| Extension | Where to change |
|---|---|
| New season | Add `Season` enum member + `URL_PARAMS` entry (see `prompts.md`) |
| New category | Add `Category` enum + entries in all relevant seasons |
| Different output root | Change `output` default in `main()` and `--output` default in `__main__` |
| Additional output format (JSON, DB) | Add writer alongside `write_csv()` |
| Async / concurrent fetching | Replace `fetch()` + `scrape_group()` with `aiohttp` |
| Resume interrupted scrape | Check for existing CSV before calling `scrape_group()` |
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
│   └── URL_PARAMS     Season → Genre → Category → list[params]
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
│   └── same_team(a, b)            fuzzy team name equality (unused in parse path, kept for reference)
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
└── Entry Point
    └── main(season, genre, category, group, jornada, output, delay)
```

---

## 2. Data Flow

```
main()
  │
  ├─ for each (season, genre, category, params)
  │
  └─ scrape_group()
       │
       ├─ fetch(overview_url jornada=0)
       ├─ get_jornada_numbers(soup)       ← extracts ?jornada=N links
       │
       └─ for each jornada N:
            ├─ fetch(jornada_url)
            ├─ parse_page(soup, N)
            │    │
            │    └─ walk all_tables[]
            │         ├─ detect Jornada label → set current_jornada
            │         └─ detect match table
            │              ├─ find nested detail table (or all_tables[i+1])
            │              └─ _parse_match_block()
            │                   ├─ extract match header (date, teams, scores)
            │                   ├─ extract venue + referee from detail rows
            │                   ├─ determine left_is_home
            │                   └─ for each game row → dict row
            │
            └─ write_csv(rows, path)
```

---

## 3. Key Design Decisions

### 3.1 Flat `find_all("table")` walk

The site wraps all content in a layout `<table>`. Using `find_all("tr", recursive=False)` or sibling-TR strategies fails because match tables are not top-level. The working strategy is:

1. Collect `soup.find_all("table")` — all tables regardless of nesting depth
2. Walk by integer index `i`
3. Use the jornada label table as a sentinel; only process match tables after one has been seen
4. Look for the detail table as either a nested `table.find("table")` or `all_tables[i+1]`

### 3.2 `current_jornada` gating

Without the jornada sentinel, navigation/layout tables early in the page that happen to contain a date and links would be misidentified as match tables. The gate ensures we only parse content inside a jornada section.

### 3.3 `left_is_home` via exact equality

The detail table header contains verbatim team names. Exact match (after `_clean()`) is more reliable than fuzzy `same_team()` which can produce false positives when team names share substrings.

### 3.4 `subgroup_id = None` for old seasons

`build_url()` omits the `&subgrupo=` parameter entirely when `subgroup_id is None`. Setting it to an empty string causes the server to return no results.

---

## 4. `URL_PARAMS` Configuration Schema

```python
URL_PARAMS: dict[Season, dict[Genre, dict[Category, list[ParamDict]]]]

ParamDict = {
    "league_id":    str,   # base64 encoded e.g. "MQ=="
    "group_id":     str,   # "0" for single-group categories, "1".."N" for multi-group
    "subgroup_id":  str | None,  # "S" for 2021+, None for older seasons
    "sex":          str,   # "M" | "F"
}
```

Empty list `[]` means the category does not exist for that season/genre combination.

---

## 5. Season Discovery (future automation)

To auto-populate `URL_PARAMS` for a new season the following steps are needed:

1. **Fetch** `https://rfetm.es/public/resultados` and extract season links matching pattern `/{YYYY-YYYY}/`
2. **For each new season**, for each (genre, category, `jornada=0`):
   - Try `grupo=0` first (single group)
   - If returns no matches, try `grupo=1`, `grupo=2`, ... until empty
   - Record the max valid `grupo` value
3. **Determine subgroup_id**: if season year ≥ 2021 use `"S"`, else `None`
4. **Emit** new `Season` enum member + `URL_PARAMS` entry

This process is codified in `prompts.md` as the **Season Discovery Prompt**.

---

## 6. Extension Points

| Extension | Where to change |
|---|---|
| New season | Add `Season` enum + `URL_PARAMS` entry (see prompts.md) |
| New category | Add `Category` enum + entries in all relevant seasons |
| Additional output format (JSON, DB) | Add writer alongside `write_csv()` |
| Async/concurrent fetching | Replace `fetch()` + `scrape_group()` with `aiohttp` |
| Resume interrupted scrape | Check for existing CSV before calling `scrape_group()` |
| Proxy / rate limit handling | Extend `SESSION` setup and retry logic in `fetch()` |
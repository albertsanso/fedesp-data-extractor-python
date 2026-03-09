#!/usr/bin/env python3
"""
migrate_to_flat.py
------------------
Migrates RFETM CSV files from the old nested directory structure to the
current flat-per-season structure.

Old structure:
  {root}/{season}/{genre}/{category}/grupo_{n}.csv

New structure:
  {root}/{season}/rfetm-{season}-{genre}-{category}-group-{n}_matches.csv

Usage:
  # Dry run (no files moved, just shows what would happen)
  python migrate_to_flat.py --source /old/output --dest ../resources/match-results-details/v3-claude

  # Actually migrate
  python migrate_to_flat.py --source /old/output --dest ../resources/match-results-details/v3-claude --apply

  # Migrate in-place (source == dest, old files removed after copy)
  python migrate_to_flat.py --source ../resources/match-results-details/v3-claude --apply

  # Delete old nested folders after migration
  python migrate_to_flat.py --source /old/output --dest ../resources/match-results-details/v3-claude --apply --cleanup
"""

import argparse
import os
import re
import shutil
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Known valid enum values (used for path segment validation) ────────────────

VALID_GENRES     = {"male", "female"}
VALID_CATEGORIES = {"super-divisio", "divisio-honor", "primera-nacional", "segona-nacional"}
SEASON_RE        = re.compile(r"^\d{4}-\d{4}$")
GRUPO_RE         = re.compile(r"^grupo_(\w+)\.csv$")


def discover_old_files(source_root: str) -> list[dict]:
    """
    Walk source_root looking for files matching:
      {source_root}/{season}/{genre}/{category}/grupo_{n}.csv

    Returns a list of dicts with keys:
      source_path, season, genre, category, group_id
    """
    found = []

    if not os.path.isdir(source_root):
        log.error(f"Source directory not found: {source_root}")
        return found

    for season in sorted(os.listdir(source_root)):
        season_dir = os.path.join(source_root, season)
        if not os.path.isdir(season_dir) or not SEASON_RE.match(season):
            continue

        for genre in sorted(os.listdir(season_dir)):
            genre_dir = os.path.join(season_dir, genre)
            if not os.path.isdir(genre_dir) or genre not in VALID_GENRES:
                continue

            for category in sorted(os.listdir(genre_dir)):
                category_dir = os.path.join(genre_dir, category)
                if not os.path.isdir(category_dir) or category not in VALID_CATEGORIES:
                    continue

                for filename in sorted(os.listdir(category_dir)):
                    m = GRUPO_RE.match(filename)
                    if not m:
                        continue
                    group_id = m.group(1)
                    found.append({
                        "source_path": os.path.join(category_dir, filename),
                        "season":      season,
                        "genre":       genre,
                        "category":    category,
                        "group_id":    group_id,
                    })

    return found


def build_dest_path(dest_root: str, entry: dict) -> str:
    """Build the new flat destination path for a given entry."""
    filename = (
        f"rfetm-{entry['season']}-{entry['genre']}-"
        f"{entry['category']}-group-{entry['group_id']}_matches.csv"
    )
    return os.path.join(dest_root, entry["season"], filename)


def migrate(source_root: str, dest_root: str, apply: bool, cleanup: bool) -> int:
    """
    Discover old files and migrate them.
    Returns the number of files processed.
    """
    entries = discover_old_files(source_root)

    if not entries:
        log.warning("No old-format CSV files found under: %s", source_root)
        return 0

    log.info(f"Found {len(entries)} file(s) to migrate.")
    if not apply:
        log.info("DRY RUN — pass --apply to perform the migration.\n")

    errors   = 0
    migrated = 0

    for entry in entries:
        src  = entry["source_path"]
        dest = build_dest_path(dest_root, entry)

        # Skip if source and destination are the same file
        if os.path.abspath(src) == os.path.abspath(dest):
            log.info(f"  SKIP (already at target path): {dest}")
            continue

        log.info(f"  {'COPY' if apply else 'WOULD COPY'}:")
        log.info(f"    {src}")
        log.info(f"    → {dest}")

        if apply:
            try:
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                shutil.copy2(src, dest)
                migrated += 1
            except Exception as e:
                log.error(f"    ERROR: {e}")
                errors += 1

    # Cleanup: remove old nested genre/category directories
    if apply and cleanup:
        log.info("\nCleaning up old nested directories...")
        for season in sorted(os.listdir(source_root)):
            season_dir = os.path.join(source_root, season)
            if not os.path.isdir(season_dir) or not SEASON_RE.match(season):
                continue
            for genre in sorted(os.listdir(season_dir)):
                genre_dir = os.path.join(season_dir, genre)
                if os.path.isdir(genre_dir) and genre in VALID_GENRES:
                    try:
                        shutil.rmtree(genre_dir)
                        log.info(f"  Removed: {genre_dir}")
                    except Exception as e:
                        log.error(f"  ERROR removing {genre_dir}: {e}")

    # Summary
    if apply:
        log.info(f"\nDone. {migrated} file(s) migrated, {errors} error(s).")
    else:
        log.info(f"\nDry run complete. {len(entries)} file(s) would be migrated.")
        log.info("Re-run with --apply to perform the migration.")

    return migrated


# ── Entry points ─────────────────────────────────────────────────────────────

def main(
    source: str = "../resources/match-results-details/v3-claude",
    dest: str = None,
    apply: bool = False,
    cleanup: bool = False,
) -> int:
    """
    Migrate RFETM CSVs from old nested structure to flat-per-season.

    Args:
        source:  Root of the OLD nested output.
                 Default: ../resources/match-results-details/v3-claude
        dest:    Root of the NEW flat output.
                 Defaults to source (in-place migration).
        apply:   Actually copy files. False = dry run only.
        cleanup: After migrating, delete old nested genre/category sub-directories.

    Returns:
        Number of files migrated (0 on dry run or nothing found).

    Examples:
        # Dry run
        main(source="/old/output", dest="../resources/match-results-details/v3-claude")

        # Apply
        main(source="/old/output", dest="../resources/match-results-details/v3-claude", apply=True)

        # In-place with cleanup
        main(source="../resources/match-results-details/v3-claude", apply=True, cleanup=True)
    """
    dest_root = dest if dest else source

    log.info(f"Source : {os.path.abspath(source)}")
    log.info(f"Dest   : {os.path.abspath(dest_root)}")
    log.info(f"Mode   : {'APPLY' if apply else 'DRY RUN'}")
    if cleanup and apply:
        log.info("Cleanup: enabled (old nested dirs will be removed)")
    log.info("")

    return migrate(source, dest_root, apply=apply, cleanup=cleanup)


if __name__ == "__main__":
    """
    ap = argparse.ArgumentParser(
        description="Migrate RFETM CSVs from old nested structure to flat-per-season.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument(
        "--source",
        default="../resources/match-results-details/v3-claude",
        help="Root of the OLD nested output (default: %(default)s)",
    )
    ap.add_argument(
        "--dest",
        default=None,
        help="Root of the NEW flat output. Defaults to --source (in-place migration).",
    )
    ap.add_argument(
        "--apply",
        action="store_true",
        help="Actually copy files. Without this flag, runs as a dry run.",
    )
    ap.add_argument(
        "--cleanup",
        action="store_true",
        help="After migrating, delete the old nested genre/category sub-directories.",
    )
    args = ap.parse_args()
    result = main(
        source=args.source,
        dest=args.dest,
        apply=args.apply,
        cleanup=args.cleanup,
    )
    """
    result = main(source="../resources/match-results-details/v3-claude", dest="../resources/match-results-details/v3-claude-flat", apply=True)
    sys.exit(0 if result >= 0 else 1)
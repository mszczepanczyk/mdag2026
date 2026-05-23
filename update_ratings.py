#!/usr/bin/env -S uvx --with httpx python
# /// script
# requires-python = ">=3.10"
# dependencies = ["httpx"]
# ///
"""Update Filmweb ratings in CSV by scraping filmweb.pl pages."""

import argparse
import csv
import json
import re
import time
from pathlib import Path

import httpx

SCRIPT_DIR = Path(__file__).parent
CSV_FILE = SCRIPT_DIR / "mdag2026.csv"
SLEEP_SECONDS = 1.5

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pl,en;q=0.9",
}


def extract_rating(html: str) -> tuple[float | None, int | None]:
    """Extract rating and vote count from Filmweb page HTML."""
    # Look for: window.IRI.setSource('filmRating', {count: "124", rate: "7.37097", ...})
    match = re.search(r"window\.IRI\.setSource\('filmRating',\s*(\{[^}]+\})\)", html)
    if not match:
        return None, None

    try:
        # Parse the JS object (it's almost JSON, just needs quote fixing)
        js_obj = match.group(1)
        # Convert JS object to valid JSON
        js_obj = re.sub(r'(\w+):', r'"\1":', js_obj)
        data = json.loads(js_obj)

        rate = float(data.get("rate", 0)) if data.get("rate") else None
        count = int(data.get("count", 0)) if data.get("count") else None

        # Round rating to 1 decimal place
        if rate:
            rate = round(rate, 1)

        return rate, count
    except (json.JSONDecodeError, ValueError, KeyError):
        return None, None


def fetch_rating(url: str, client: httpx.Client) -> tuple[float | None, int | None]:
    """Fetch page and extract rating."""
    try:
        resp = client.get(url, follow_redirects=True)
        resp.raise_for_status()
        return extract_rating(resp.text)
    except httpx.HTTPError as e:
        print(f"  HTTP error: {e}")
        return None, None


def main():
    parser = argparse.ArgumentParser(description="Update Filmweb ratings in CSV")
    parser.add_argument("--dry-run", "-n", action="store_true", help="Don't write changes, just show what would change")
    parser.add_argument("--sleep", "-s", type=float, default=SLEEP_SECONDS, help=f"Sleep between requests (default: {SLEEP_SECONDS}s)")
    args = parser.parse_args()

    # Read CSV
    with open(CSV_FILE, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    updated_count = 0
    skipped_count = 0

    with httpx.Client(headers=HEADERS, timeout=30.0) as client:
        for i, row in enumerate(rows):
            title = row["Tytuł polski"]
            url = row.get("Link Filmweb", "").strip()

            if not url:
                print(f"[{i+1}/{len(rows)}] {title}: no Filmweb link, skipping")
                skipped_count += 1
                continue

            old_rating = row.get("Ocena Filmweb", "").strip()
            old_votes = row.get("Głosy Filmweb", "").strip()

            print(f"[{i+1}/{len(rows)}] {title}...")
            new_rating, new_votes = fetch_rating(url, client)

            # Format for comparison
            old_rating_str = old_rating if old_rating else "—"
            old_votes_str = old_votes if old_votes else "—"
            new_rating_str = str(new_rating) if new_rating else "—"
            new_votes_str = str(new_votes) if new_votes else "—"

            changed = False
            if new_rating_str != old_rating_str or new_votes_str != old_votes_str:
                changed = True
                print(f"  Rating: {old_rating_str} -> {new_rating_str}")
                print(f"  Votes:  {old_votes_str} -> {new_votes_str}")
                updated_count += 1
            else:
                print(f"  No change ({old_rating_str}, {old_votes_str} votes)")

            if not args.dry_run and changed:
                row["Ocena Filmweb"] = str(new_rating) if new_rating else ""
                row["Głosy Filmweb"] = str(new_votes) if new_votes else ""

            time.sleep(args.sleep)

    # Write CSV
    if not args.dry_run:
        with open(CSV_FILE, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"\nDone! Updated {updated_count} entries, skipped {skipped_count}.")
    else:
        print(f"\n[DRY RUN] Would update {updated_count} entries, skipped {skipped_count}.")


if __name__ == "__main__":
    main()

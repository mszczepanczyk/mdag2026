#!/usr/bin/env -S uvx --with jinja2 python
# /// script
# requires-python = ">=3.10"
# dependencies = ["jinja2"]
# ///
"""Build index.html by inlining CSV data into HTML template using Jinja2."""

import csv
import json
import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

SCRIPT_DIR = Path(__file__).parent
CSV_FILE = SCRIPT_DIR / "mdag2026.csv"
TEMPLATE_FILE = SCRIPT_DIR / "mdag2026.html.j2"
OUTPUT_FILE = SCRIPT_DIR / "index.html"

MDAG_BASE = "https://mdag.pl/pl/ogladaj-online/23/film/"
FILMWEB_BASE = "https://www.filmweb.pl/film/"


def extract_slug(url: str, base: str) -> str | None:
    """Extract slug from URL by removing base."""
    if not url:
        return None
    url = url.strip()
    if url.startswith(base):
        return url[len(base):] or None
    return None


def parse_int(val: str) -> int | None:
    """Parse integer, return None if empty or invalid."""
    if not val or not val.strip():
        return None
    try:
        return int(val.strip())
    except ValueError:
        return None


def parse_float(val: str) -> float | None:
    """Parse float, return None if empty or invalid."""
    if not val or not val.strip():
        return None
    try:
        return float(val.strip())
    except ValueError:
        return None


def load_csv_data() -> list[list]:
    """Load CSV and transform to JavaScript array format."""
    data = []
    with open(CSV_FILE, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # [pl, en, dur, wins, noms, country, rating, votes, mdag_slug, fw_slug]
            entry = [
                row["Tytuł polski"],
                row["Tytuł angielski"],
                parse_int(row["Czas (min)"]),
                parse_int(row["Nagrody MDAG"]) or 0,
                parse_int(row["Nominacje MDAG"]) or 0,
                row["Kraj"] or "—",
                parse_float(row["Ocena Filmweb"]),
                parse_int(row["Głosy Filmweb"]),
                extract_slug(row["Link MDAG"], MDAG_BASE),
                extract_slug(row["Link Filmweb"], FILMWEB_BASE),
            ]
            data.append(entry)
    return data


def format_js_array(data: list[list]) -> str:
    """Format data as JavaScript array with proper indentation."""
    lines = []
    for entry in data:
        lines.append(f"      {json.dumps(entry, ensure_ascii=False)},")
    return "[\n" + "\n".join(lines) + "\n    ]"


def main():
    data = load_csv_data()
    js_array = format_js_array(data)

    env = Environment(loader=FileSystemLoader(SCRIPT_DIR))
    template = env.get_template(TEMPLATE_FILE.name)

    html = template.render(RAW_DATA=js_array)

    OUTPUT_FILE.write_text(html, encoding="utf-8")
    print(f"Generated {OUTPUT_FILE} with {len(data)} entries")


if __name__ == "__main__":
    main()

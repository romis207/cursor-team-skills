#!/usr/bin/env python3
"""Refresh versions_cache.json from FPAAEB Confluence page when accessible."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
CACHE_FILE = SKILL_DIR / "versions_cache.json"
PAGE_ID = "259580052"


def parse_table_from_markdown(content: str) -> list[dict]:
    """Best-effort parse of Confluence markdown/html tables with bundle paths."""
    rows: list[dict] = []
    # Look for trees_archive paths in page content
    pattern = re.compile(
        r"/mobileye/trees_archive/PSW/bundle/([^/]+)/pre-release/([^/]+)/executables/([^/]+)/([^/]+)/"
    )
    for match in pattern.finditer(content):
        bundle_version, cf_notation, eyeq, build_mode = match.groups()
        rows.append(
            {
                "bundle_version": bundle_version,
                "cf_notation": cf_notation,
                "eyeq": eyeq,
                "build_mode": build_mode,
            }
        )
    return rows


def main() -> int:
    print(
        "To refresh versions_cache.json, fetch Confluence page "
        f"{PAGE_ID} (FPAAEB / Latest versions and cmls) via MCP and update profiles manually."
    )
    print(f"Cache file: {CACHE_FILE}")

    if len(sys.argv) > 1 and sys.argv[1] == "--from-file":
        src = Path(sys.argv[2])
        content = src.read_text(encoding="utf-8", errors="replace")
        rows = parse_table_from_markdown(content)
        print(json.dumps(rows, indent=2))
        if not rows:
            print("No bundle paths found in input file.", file=sys.stderr)
            return 1
        return 0

    cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    print(json.dumps(cache, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

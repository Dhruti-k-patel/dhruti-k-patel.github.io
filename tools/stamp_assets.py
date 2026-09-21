#!/usr/bin/env python3
"""
Make browsers pick up style and script changes immediately.

    python tools/stamp_assets.py

Run by publish.bat automatically - you should never need to run it by hand.

WHY THIS EXISTS
---------------
GitHub serves style.css and the scripts with "cache for 10 minutes". So for up
to ten minutes after you publish, anyone who visited recently - including you -
keeps seeing the OLD stylesheet with the NEW page. That looks like your change
did not work, or worse, like the site is broken.

This adds a short fingerprint of each file's contents to the address the page
asks for:

    assets/css/style.css?v=8f3c1a92

Change the file and the fingerprint changes, so the browser treats it as a new
address and fetches it at once. Leave the file alone and the fingerprint stays,
so the cache keeps working as it should.
"""

from __future__ import annotations

import hashlib
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Files whose addresses get a fingerprint. Anything a browser caches and that
# changes when the site changes belongs here.
ASSETS = [
    "assets/css/style.css",
    "assets/js/main.js",
    "assets/js/subscribe.js",
    "assets/js/config.js",
    "data/substack.js",
    "data/site-posts.js",
]


def fingerprint(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()[:8]


def stamp_file(page: Path, versions: dict[str, str]) -> int:
    """Rewrite one HTML file's asset links. Returns how many were changed."""
    text = page.read_text(encoding="utf-8")
    before = text

    for asset, version in versions.items():
        name = asset.split("/")[-1]
        # Matches src="…/style.css", src="…/style.css?v=old", any depth of ../
        pattern = re.compile(
            r'((?:src|href)=")((?:\.\./)*' + re.escape(asset.rsplit("/", 1)[0]) +
            r"/" + re.escape(name) + r')(\?v=[a-f0-9]+)?(")'
        )
        text = pattern.sub(lambda m: f"{m.group(1)}{m.group(2)}?v={version}{m.group(4)}", text)

    if text != before:
        page.write_text(text, encoding="utf-8")
        return sum(1 for a in versions if a.split("/")[-1] in text)
    return 0


def main() -> int:
    versions: dict[str, str] = {}
    for asset in ASSETS:
        p = ROOT / asset
        if p.exists():
            versions[asset] = fingerprint(p)

    if not versions:
        print("  No assets found to stamp.")
        return 0

    pages = [ROOT / "index.html"]
    pages += sorted((ROOT / "writing").glob("*/index.html"))

    touched = 0
    for page in pages:
        if page.exists() and stamp_file(page, versions):
            touched += 1

    print(f"  Fingerprinted {len(versions)} file(s) across {touched} page(s):")
    for asset, version in versions.items():
        print(f"    {asset:<28} v={version}")
    print("  Browsers will fetch the new versions straight away.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
Refresh the Substack content used by the website.

Writes:
    data/articles.json  - newsletter posts from mpulseindia.substack.com
    data/notes.json     - Substack Notes from the author's profile
    data/substack.js    - the same data as a plain <script> payload, so the
                          site also works when index.html is opened straight
                          from disk (file://), where fetch() is blocked.

Usage:
    python tools/fetch_substack.py

No third-party packages required (standard library only).
"""

from __future__ import annotations

import json
import re
import sys

# Windows consoles default to cp1252; never let an un-encodable character
# crash a script whose whole job is to report problems clearly.
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html import unescape
from pathlib import Path

PUBLICATION = "https://mpulseindia.substack.com"
AUTHOR_ID = 546321467  # Dr. Dhruti Patel (@mpulseindia)

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


def get_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def reading_minutes(words: int) -> int:
    return max(1, round((words or 0) / 225))


def hearts(reactions) -> int:
    if not isinstance(reactions, dict):
        return 0
    return sum(v for v in reactions.values() if isinstance(v, int))


# --------------------------------------------------------------------------
# Categories
#
# Substack's own tags overlap far too much to filter on - nearly every post
# carries "IPO", "Equity Research" and "Stock Analysis" at once, so every tag
# filter showed the same articles. These three buckets describe what a piece
# actually is:
#
#   company  a named company's prospectus or post-listing read
#   method   a repeatable framework, not about one company
#   markets  macro, sector or seasonality work
#
# The rules below get all current posts right. If a future post lands in the
# wrong bucket, add its slug to CATEGORY_OVERRIDES rather than bending them.
# --------------------------------------------------------------------------

CATEGORY_OVERRIDES: dict[str, str] = {
    # "some-post-slug": "method",
}

# A title opening with one of these is talking about a subject, not a company.
GENERIC_OPENERS = {
    "the", "a", "an", "do", "does", "why", "how", "what", "when", "where",
    "is", "are", "can", "should", "five", "four", "three", "two", "inside",
    "reading", "understanding",
}

IPO_TAGS = {"ipo", "main board ipo", "sme ipo", "post ipo analysis"}


def categorise(title: str, tags: list[str], slug: str) -> str:
    if slug in CATEGORY_OVERRIDES:
        return CATEGORY_OVERRIDES[slug]

    t = (title or "").strip()
    low = t.lower()
    tagset = {x.lower() for x in tags}
    first_word = low.split(" ")[0].strip(".,:--") if low else ""
    names_a_company = first_word not in GENERIC_OPENERS

    # Reading a specific company's prospectus.
    if "rhp" in low or "drhp" in low:
        return "company"
    if names_a_company and ("ipo" in low or "after listing" in low or "listing" in low):
        return "company"

    # Talks about IPOs, but not about one company: a framework or guide.
    if "ipo" in low or (tagset & IPO_TAGS):
        return "method"

    return "markets"


def fetch_articles() -> list[dict]:
    posts, offset = [], 0
    while True:
        batch = get_json(f"{PUBLICATION}/api/v1/archive?sort=new&limit=50&offset={offset}")
        if not batch:
            break
        posts.extend(batch)
        if len(batch) < 50:
            break
        offset += 50

    out = []
    for p in posts:
        title = p.get("title") or ""
        tags = [t.get("name") for t in (p.get("postTags") or []) if t.get("name")]
        slug = p.get("slug") or ""
        out.append(
            {
                "id": p.get("id"),
                "title": title,
                "subtitle": (p.get("subtitle") or p.get("description") or "").strip(),
                "excerpt": (p.get("truncated_body_text") or "").strip(),
                "slug": slug,
                "url": p.get("canonical_url") or f"{PUBLICATION}/p/{slug}",
                "date": p.get("post_date"),
                "image": p.get("cover_image"),
                "wordcount": p.get("wordcount") or 0,
                "readingMinutes": reading_minutes(p.get("wordcount") or 0),
                "likes": hearts(p.get("reactions")),
                "tags": tags,
                "category": categorise(title, tags, slug),
            }
        )
    out.sort(key=lambda a: a["date"] or "", reverse=True)
    return out


URL_RE = re.compile(r"https?://[^\s<>\"']+")


def fetch_notes() -> list[dict]:
    items, cursor, pages = [], None, 0
    while pages < 10:
        url = f"https://substack.com/api/v1/reader/feed/profile/{AUTHOR_ID}?types%5B%5D=note&limit=30"
        if cursor:
            cursor_q = urllib.parse.quote(str(cursor), safe="")
            url += f"&cursor={cursor_q}"
        payload = get_json(url)
        batch = payload.get("items") or []
        if not batch:
            break
        items.extend(batch)
        cursor = payload.get("nextCursor")
        pages += 1
        if not cursor:
            break

    out = []
    for item in items:
        c = item.get("comment")
        if not c:
            continue
        body = unescape((c.get("body") or "").strip())
        attachments = c.get("attachments") or []

        image = next((a.get("imageUrl") for a in attachments if a.get("type") == "image"), None)
        linked_post = next((a for a in attachments if a.get("type") == "post" and a.get("post")), None)
        post = (linked_post or {}).get("post") or {}

        # First external link inside the note body, if any.
        link = next((m.group(0).rstrip(".,)") for m in URL_RE.finditer(body)), None)

        if not body and not image and not post:
            continue  # e.g. bare publication recommendations

        out.append(
            {
                "id": c.get("id"),
                "date": c.get("date"),
                "body": body,
                "image": image,
                "likes": c.get("reaction_count") or 0,
                "restacks": c.get("restacks") or 0,
                "link": link,
                "linkedPost": (
                    {"title": post.get("title"), "url": post.get("canonical_url")} if post else None
                ),
                "url": f"https://substack.com/@mpulseindia/note/c-{c.get('id')}",
            }
        )
    out.sort(key=lambda n: n["date"] or "", reverse=True)
    return out


def write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"  wrote {path.relative_to(ROOT)}")


def main() -> int:
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        print("Fetching articles...")
        articles = fetch_articles()
        print(f"  {len(articles)} articles")
        # Print the split so a mis-filed post is obvious at a glance.
        for key, label in (
            ("company", "IPO & RHP analysis"),
            ("method", "Frameworks"),
            ("markets", "Markets & sectors"),
        ):
            in_bucket = [a for a in articles if a["category"] == key]
            print(f"    {label} ({len(in_bucket)})")
            for a in in_bucket:
                print(f"      - {a['title'][:66]}")
        print("Fetching notes...")
        notes = fetch_notes()
        print(f"  {len(notes)} notes")
    except urllib.error.URLError as exc:
        print(f"Network error: {exc}. Existing data files were left untouched.", file=sys.stderr)
        return 1

    articles_payload = {"updated": stamp, "source": PUBLICATION, "items": articles}
    notes_payload = {"updated": stamp, "source": "https://substack.com/@mpulseindia", "items": notes}

    write(DATA_DIR / "articles.json", articles_payload)
    write(DATA_DIR / "notes.json", notes_payload)

    bundle = {"updated": stamp, "articles": articles, "notes": notes}
    js = (
        "/* Generated by tools/fetch_substack.py - do not edit by hand. */\n"
        "window.SUBSTACK_DATA = "
        + json.dumps(bundle, indent=2, ensure_ascii=False)
        + ";\n"
    )
    js_path = DATA_DIR / "substack.js"
    js_path.write_text(js, encoding="utf-8")
    print(f"  wrote {js_path.relative_to(ROOT)}")
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

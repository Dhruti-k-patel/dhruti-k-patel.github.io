#!/usr/bin/env python3
"""
Turn the articles you write in posts/*.md into pages on your website.

    python tools/build_posts.py

Each .md file becomes a page at  writing/<name>/  and is listed in the Writing
section of the home page alongside the Substack ones.

Run by publish.bat automatically - you should never need to run it by hand.

WRITING AN ARTICLE
------------------
Create a file in posts/, named however you want the address to read, e.g.
posts/nse-first-results.md becomes yoursite.com/writing/nse-first-results/

Start it with a details block between two lines of three dashes:

    ---
    title: What NSE's first results tell us
    subtitle: One quarter after listing, the options share is the number to watch
    date: 2026-10-02
    tags: NSE, Equity Research, valuation
    category: company
    ---

    Then write the article here.

title and date are required; the rest are optional.
category is one of: company, method, markets  (it picks the filter tab).

No third-party packages required (standard library only).
"""

from __future__ import annotations

import html
import json
import re
import sys

# Windows consoles default to cp1252; never let an un-encodable character
# crash a script whose whole job is to report problems clearly.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTS_DIR = ROOT / "posts"
OUT_DIR = ROOT / "writing"
DATA_FILE = ROOT / "data" / "site-posts.js"

SITE_URL = "https://dhrutikp.com"
VALID_CATEGORIES = {"company", "method", "markets"}


# ---------------------------------------------------------------- markdown ---
#
# A deliberately small Markdown subset - headings, paragraphs, bold, italic,
# links, images, lists, quotes, tables, code and rules. Enough for an analysis
# piece, small enough to read and fix. Everything is HTML-escaped first, so
# text can never break the page.


def inline(text: str) -> str:
    """Bold, italic, code, links and images inside a line of text."""
    text = html.escape(text, quote=False)

    # `code` first, so formatting inside it is left alone.
    codes: list[str] = []

    def stash(m: re.Match) -> str:
        codes.append(m.group(1))
        return f"\x00{len(codes) - 1}\x00"

    text = re.sub(r"`([^`]+)`", stash, text)

    text = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)",
                  r'<img src="\2" alt="\1" loading="lazy">', text)
    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)",
                  r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<em>\1</em>", text)
    text = re.sub(r"(?<![\w_])_([^_\n]+)_(?![\w_])", r"<em>\1</em>", text)

    for i, code in enumerate(codes):
        text = text.replace(f"\x00{i}\x00", f"<code>{html.escape(code, quote=False)}</code>")
    return text


def table(rows: list[str]) -> str:
    """A pipe table. Row two (---|---) separates the header."""
    def cells(line: str) -> list[str]:
        return [c.strip() for c in line.strip().strip("|").split("|")]

    head = cells(rows[0])
    body = [cells(r) for r in rows[2:]]
    out = ["<div class='table-wrap'><table><thead><tr>"]
    out += [f"<th>{inline(c)}</th>" for c in head]
    out.append("</tr></thead><tbody>")
    for row in body:
        out.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in row) + "</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def markdown(src: str) -> str:
    lines = src.replace("\r\n", "\n").split("\n")
    out: list[str] = []
    para: list[str] = []
    i = 0

    def flush() -> None:
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>")
            para.clear()

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            flush(); i += 1; continue

        if stripped.startswith("```"):                       # fenced code
            flush(); i += 1
            block = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                block.append(lines[i]); i += 1
            i += 1
            out.append("<pre><code>" + html.escape("\n".join(block)) + "</code></pre>")
            continue

        if re.match(r"^(-{3,}|\*{3,}|_{3,})$", stripped):    # horizontal rule
            flush(); out.append("<hr>"); i += 1; continue

        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)          # heading
        if m:
            flush()
            level = len(m.group(1))
            out.append(f"<h{level}>{inline(m.group(2))}</h{level}>")
            i += 1; continue

        if stripped.startswith(">"):                          # blockquote
            flush()
            quote = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip().lstrip(">").strip()); i += 1
            out.append("<blockquote><p>" + inline(" ".join(quote)) + "</p></blockquote>")
            continue

        if "|" in stripped and i + 1 < len(lines) and re.match(
                r"^\s*\|?[\s:-]*\|[\s:|-]*$", lines[i + 1]):  # table
            flush()
            rows = []
            while i < len(lines) and "|" in lines[i]:
                rows.append(lines[i]); i += 1
            out.append(table(rows))
            continue

        if re.match(r"^[-*+]\s+", stripped):                  # bullet list
            flush()
            items = []
            while i < len(lines) and re.match(r"^\s*[-*+]\s+", lines[i]):
                items.append(re.sub(r"^\s*[-*+]\s+", "", lines[i])); i += 1
            out.append("<ul>" + "".join(f"<li>{inline(x)}</li>" for x in items) + "</ul>")
            continue

        if re.match(r"^\d+[.)]\s+", stripped):                # numbered list
            flush()
            items = []
            while i < len(lines) and re.match(r"^\s*\d+[.)]\s+", lines[i]):
                items.append(re.sub(r"^\s*\d+[.)]\s+", "", lines[i])); i += 1
            out.append("<ol>" + "".join(f"<li>{inline(x)}</li>" for x in items) + "</ol>")
            continue

        para.append(stripped)
        i += 1

    flush()
    return "\n".join(out)


# ------------------------------------------------------------- front matter ---

def split_front_matter(text: str, path: Path) -> tuple[dict, str]:
    text = text.replace("\r\n", "\n").lstrip("﻿").lstrip()
    if not text.startswith("---"):
        raise ValueError(
            f"{path.name}: missing the details block.\n"
            "    The file must start with three dashes, then title: and date:,\n"
            "    then three dashes again. See posts/EXAMPLE.md."
        )
    end = text.find("\n---", 3)
    if end == -1:
        raise ValueError(f"{path.name}: the details block is never closed with ---")

    meta: dict[str, str] = {}
    for line in text[3:end].strip().split("\n"):
        if not line.strip() or ":" not in line:
            continue
        key, _, value = line.partition(":")
        meta[key.strip().lower()] = value.strip()

    body = text[end + 4:].lstrip("\n")
    return meta, body


# --------------------------------------------------------------- page build ---

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title_esc} — Dr. Dhruti Kunjit Patel</title>
<meta name="description" content="{desc_esc}">
<meta name="author" content="Dr. Dhruti Kunjit Patel">
<link rel="canonical" href="{site}/writing/{slug}/">
<meta property="og:type" content="article">
<meta property="og:title" content="{title_esc}">
<meta property="og:description" content="{desc_esc}">
<meta property="og:url" content="{site}/writing/{slug}/">
{og_image}
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:site" content="@dhruti_kp">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' rx='20' fill='%23235b63'/><text y='66' x='50' text-anchor='middle' font-size='46' font-family='Georgia,serif' fill='%23f2c9a8'>DK</text></svg>">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400;6..72,500;6..72,600;6..72,700&family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="../../assets/css/style.css">
<script>
  // Inline so the page never flashes the wrong theme before styles load.
  (function () {{
    try {{
      var t = localStorage.getItem('dkp-theme');
      if (t !== 'dark' && t !== 'light') {{
        t = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
      }}
      document.documentElement.setAttribute('data-theme', t);
    }} catch (e) {{ document.documentElement.setAttribute('data-theme', 'light'); }}
  }})();
</script>
<script type="application/ld+json">
{ld_json}
</script>
</head>
<body>
<a class="skip-link" href="#article">Skip to content</a>

<header class="site-header is-stuck">
  <div class="wrap header-inner">
    <a class="brand" href="../../">
      <span class="brand-mark">DK</span>
      <span class="brand-text">
        <strong>Dr. Dhruti Kunjit Patel</strong>
        <small>Stock Market Analyst</small>
      </span>
    </a>
    <div class="header-actions">
      <a class="btn-subscribe" href="../../#contact">
        <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path d="M18 8.6a6 6 0 1 0-12 0c0 6.1-2.3 7.4-2.3 7.4h16.6S18 14.7 18 8.6Z" stroke-linecap="round" stroke-linejoin="round"/><path d="M13.7 19.5a2 2 0 0 1-3.4 0" stroke-linecap="round"/></svg>
        <span>Subscribe</span>
      </a>
      <button class="icon-btn" id="themeToggle" type="button" aria-label="Toggle theme" title="Toggle theme">
        <svg class="i-sun" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><circle cx="12" cy="12" r="4.2"/><g stroke-linecap="round"><path d="M12 2.6v2.3M12 19.1v2.3M2.6 12h2.3M19.1 12h2.3M5.2 5.2l1.7 1.7M17.1 17.1l1.7 1.7M18.8 5.2l-1.7 1.7M6.9 17.1l-1.7 1.7"/></g></svg>
        <svg class="i-moon" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M20.5 14.3A8.5 8.5 0 0 1 9.7 3.5a8.5 8.5 0 1 0 10.8 10.8Z"/></svg>
      </button>
    </div>
  </div>
</header>

<main>
<article class="article" id="article">
  <div class="wrap article-wrap">
    <a class="back-link" href="../../#writing">
      <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path d="M19 12H5M11 6l-6 6 6 6" stroke-linecap="round" stroke-linejoin="round"/></svg>
      All writing
    </a>

    <p class="article-kicker">{kicker}</p>
    <h1>{title_esc}</h1>
    {subtitle_html}
    <p class="article-meta">
      <time datetime="{date_iso}">{date_human}</time>
      <span class="dot">·</span><span>{minutes} min read</span>
      <span class="dot">·</span><span>{words:,} words</span>
    </p>
    {tags_html}
    {cover_html}

    <div class="article-body">
{body}
    </div>

    <p class="article-disclaimer">
      <strong>Disclaimer.</strong> I am not a SEBI-registered Research Analyst or
      Investment Adviser. This is educational analysis of publicly available
      information and is not investment advice, nor a recommendation to
      subscribe, buy, sell, hold or avoid any security.
    </p>

    <a class="back-link" href="../../#writing">
      <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path d="M19 12H5M11 6l-6 6 6 6" stroke-linecap="round" stroke-linejoin="round"/></svg>
      All writing
    </a>
  </div>
</article>
</main>

<footer class="site-footer">
  <div class="wrap footer-inner">
    <div>
      <p class="footer-name">Dr. Dhruti Kunjit Patel</p>
      <p class="footer-line">Stock Market Analyst · Dubai, UAE</p>
    </div>
    <p class="footer-copy">© <span id="year">2026</span> Dr. Dhruti Kunjit Patel. All rights reserved.</p>
  </div>
</footer>

<script>
  document.getElementById('year').textContent = new Date().getFullYear();
  document.getElementById('themeToggle').addEventListener('click', function () {{
    var next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    try {{ localStorage.setItem('dkp-theme', next); }} catch (e) {{}}
  }});
</script>
</body>
</html>
"""

KICKERS = {
    "company": "IPO &amp; RHP analysis",
    "method": "Framework",
    "markets": "Markets &amp; sectors",
}


def human_date(iso: str) -> str:
    try:
        return datetime.strptime(iso, "%Y-%m-%d").strftime("%-d %b %Y")
    except ValueError:
        try:  # Windows has no %-d
            return datetime.strptime(iso, "%Y-%m-%d").strftime("%d %b %Y").lstrip("0")
        except ValueError:
            return iso


def build_one(path: Path) -> dict:
    meta, body_md = split_front_matter(path.read_text(encoding="utf-8"), path)

    title = meta.get("title", "").strip()
    date = meta.get("date", "").strip()
    if not title:
        raise ValueError(f"{path.name}: needs a 'title:' line in the details block.")
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
        raise ValueError(
            f"{path.name}: 'date:' must look like 2026-10-02 (year-month-day), got {date!r}."
        )

    category = meta.get("category", "").strip().lower() or "markets"
    if category not in VALID_CATEGORIES:
        raise ValueError(
            f"{path.name}: category must be one of "
            f"{', '.join(sorted(VALID_CATEGORIES))} - got {category!r}."
        )

    slug = re.sub(r"[^a-z0-9-]+", "-", path.stem.lower()).strip("-")
    subtitle = meta.get("subtitle", "").strip()
    tags = [t.strip() for t in meta.get("tags", "").split(",") if t.strip()]
    cover = meta.get("cover", "").strip()

    body_html = markdown(body_md)
    words = len(re.findall(r"\w+", re.sub(r"<[^>]+>", " ", body_html)))
    minutes = max(1, round(words / 225))

    desc = subtitle or re.sub(r"<[^>]+>", " ", body_html)[:180].strip()

    cover_url = ""
    if cover:
        cover_url = cover if cover.startswith("http") else f"{SITE_URL}/{cover.lstrip('/')}"

    page = PAGE.format(
        title_esc=html.escape(title),
        desc_esc=html.escape(re.sub(r"\s+", " ", desc)),
        site=SITE_URL,
        slug=slug,
        og_image=(f'<meta property="og:image" content="{html.escape(cover_url)}">'
                  if cover_url else ""),
        kicker=KICKERS[category],
        subtitle_html=(f'<p class="article-subtitle">{inline(subtitle)}</p>'
                       if subtitle else ""),
        date_iso=date,
        date_human=human_date(date),
        minutes=minutes,
        words=words,
        tags_html=("<div class='article-tags'>" +
                   "".join(f"<span class='post-tag'>{html.escape(t)}</span>" for t in tags) +
                   "</div>") if tags else "",
        cover_html=(f'<img class="article-cover" src="../../{html.escape(cover.lstrip("/"))}" alt="">'
                    if cover and not cover.startswith("http") else
                    (f'<img class="article-cover" src="{html.escape(cover)}" alt="">' if cover else "")),
        body=body_html,
        ld_json=json.dumps({
            "@context": "https://schema.org",
            "@type": "BlogPosting",
            "headline": title,
            "description": re.sub(r"\s+", " ", desc),
            "datePublished": date,
            "author": {"@type": "Person", "name": "Dr. Dhruti Kunjit Patel"},
            "mainEntityOfPage": f"{SITE_URL}/writing/{slug}/",
        }, indent=2),
    )

    out = OUT_DIR / slug / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")

    return {
        "title": title,
        "subtitle": subtitle,
        "url": f"writing/{slug}/",
        "date": f"{date}T09:00:00.000Z",
        "image": cover or None,
        "wordcount": words,
        "readingMinutes": minutes,
        "likes": 0,
        "tags": tags,
        "category": category,
        "own": True,
    }


def main() -> int:
    POSTS_DIR.mkdir(exist_ok=True)
    files = sorted(p for p in POSTS_DIR.glob("*.md") if not p.name.startswith("_"))

    posts, errors = [], []
    for path in files:
        if path.name.upper() == "EXAMPLE.MD":
            continue  # the template, not an article
        try:
            posts.append(build_one(path))
            print(f"  built  posts/{path.name}  ->  writing/{posts[-1]['url'].split('/')[1]}/")
        except ValueError as exc:
            errors.append(str(exc))

    if errors:
        print("\n  Could not build these:\n")
        for e in errors:
            print(f"    x {e}")
        print()
        return 1

    # Remove pages whose source file has gone.
    live = {p["url"].strip("/").split("/")[1] for p in posts}
    if OUT_DIR.exists():
        for folder in OUT_DIR.iterdir():
            if folder.is_dir() and folder.name not in live:
                for f in folder.rglob("*"):
                    f.unlink()
                folder.rmdir()
                print(f"  removed  writing/{folder.name}/  (source .md is gone)")

    posts.sort(key=lambda p: p["date"], reverse=True)
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(
        "/* Generated by tools/build_posts.py - do not edit by hand. */\n"
        "window.SITE_POSTS = " + json.dumps(
            {"updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             "items": posts}, indent=2, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )

    print(f"  {len(posts)} article(s) written on this site.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

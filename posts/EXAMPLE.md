---
title: The headline of your article goes here
subtitle: One sentence under the title. Optional, but it shows in the article list.
date: 2026-10-02
tags: IPO, Equity Research, valuation
category: company
---

This file is a template. It is **not** published — the builder skips anything
called EXAMPLE.md. Copy it, rename the copy, and write.

## How to publish an article

1. Copy this file. Name it however you want the web address to read, using
   dashes instead of spaces — `nse-first-results.md` becomes
   `yoursite.com/writing/nse-first-results/`
2. Fill in the details block at the top (between the two `---` lines).
3. Write the article below it.
4. Save, then double-click `publish.bat`.

That is the whole process. The article appears on your site, and in the Writing
section alongside the Substack ones.

## The details block

| Line | Needed? | Notes |
|---|---|---|
| title | Yes | The headline |
| date | Yes | Always `year-month-day`, e.g. `2026-10-02` |
| subtitle | No | One line shown under the title and in the list |
| tags | No | Separated by commas |
| category | No | `company`, `method` or `markets` — picks the filter tab |
| cover | No | A picture, e.g. `assets/img/posts/nse.png` |

`category` decides which tab the article appears under:

- **company** — a named company's prospectus or post-listing read
- **method** — a repeatable framework, not about one company
- **markets** — macro, sector or seasonality work

## How to format the writing

Write plain sentences and leave a blank line between paragraphs. That is enough
for most of an article. When you need more:

A heading looks like this:

```
## Why the cash flow matters
```

For **bold** type two stars either side, and for *italic* one star either side.

A link is the words in square brackets, then the address in round brackets:
[the RHP](https://example.com).

- A bullet list starts each line with a dash
- Like this

1. A numbered list starts each line with a number and a dot
2. Like this

> A quote is a line starting with a greater-than sign. Useful for pulling out a
> line from a prospectus.

A table — genuinely useful for figures:

| Year | Revenue | Profit |
|---|---|---|
| FY24 | 1,240 | 96 |
| FY25 | 1,655 | 141 |
| FY26 | 1,702 | 88 |

Three dashes on their own line draw a dividing rule:

---

To add a picture, put the image file in `assets/img/posts/` and write:

```
![A description of the picture](../../assets/img/posts/your-picture.png)
```

## Things worth knowing

- The SEBI disclaimer is added to every article automatically. You do not need
  to type it.
- Reading time and word count are worked out for you.
- If you delete a `.md` file, its page is removed from the site on the next
  publish.
- If you get the details block wrong, `publish.bat` stops and tells you which
  line to fix. Nothing is uploaded until it is right.

#!/usr/bin/env python3
"""
Safety check to run before pushing the site to GitHub.

    python tools/check_before_publish.py

The repository is public, so everything committed to it can be read by anyone,
for ever - deleting a file later does NOT remove it from the history. This
looks at what you are about to publish and refuses if it finds:

  * a PDF, DOC or spreadsheet (your CV and anything like it)
  * an email address that is not one of yours
  * a phone number
  * anything that looks like a password, API key or token

Deliberately generic: it does not contain anyone's actual details, because
this file is itself published.

Exit code 0 = safe to push. 1 = stop and look.
"""

from __future__ import annotations

import re
import subprocess
import sys

# Windows consoles default to cp1252; never let an un-encodable character
# crash a script whose whole job is to report problems clearly.
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Addresses that are meant to be on the public site.
ALLOWED_EMAILS = {
    "dkpatel1888@gmail.com",   # your published contact address
    "you@example.com",         # placeholder in the form
    "noreply@anthropic.com",   # commit trailer
}

# Extensions that should never be committed - CVs, letters, spreadsheets.
RISKY_SUFFIXES = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".key", ".pem", ".env"}

SECRET_PATTERNS = {
    "password":        r'password\s*[:=]\s*["\'][^"\']{3,}',
    "API key/secret":  r'(api[_-]?key|secret[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret)\s*[:=]\s*["\'][^"\']{8,}',
    "GitHub token":    r'gh[pousr]_[A-Za-z0-9]{20,}',
    "Google API key":  r'AIza[0-9A-Za-z_\-]{30,}',
    "AWS key":         r'AKIA[0-9A-Z]{16}',
    "private key":     r'-----BEGIN [A-Z ]*PRIVATE KEY-----',
}

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]{2,}")

# A plus sign, then a country code, then ten or more digits, spaces, dashes or
# brackets. Written without a sample number on purpose: this file is published,
# so an example here would be the very kind of leak the check exists to catch,
# and it would also make the checker flag itself on every run.
PHONE_RE = re.compile(r"\+\d[\d\s().-]{8,}\d")

# Files whose content is data from Substack - her own published words, which
# legitimately quote other people and URLs.
SKIP_CONTENT = {"data/articles.json", "data/notes.json", "data/substack.js"}


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, errors="ignore"
    ).stdout


def tracked_files() -> list[str]:
    """Everything committed or staged - i.e. what a push would publish."""
    out = set(git("ls-files").split("\n"))
    out |= set(git("diff", "--cached", "--name-only").split("\n"))
    return sorted(f for f in out if f.strip())


def main() -> int:
    if not (ROOT / ".git").exists():
        print("Not a git repository - nothing to check.")
        return 0

    files = tracked_files()
    problems: list[str] = []
    notes: list[str] = []

    print(f"\nChecking {len(files)} file(s) that would be published...\n")

    # 1. Risky file types.
    for f in files:
        if Path(f).suffix.lower() in RISKY_SUFFIXES:
            problems.append(f"{f} - document/data file, should not be published")

    # 2. Content checks.
    for f in files:
        if f in SKIP_CONTENT:
            continue
        p = ROOT / f
        if not p.exists():
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue  # binary, e.g. the photo

        for label, pattern in SECRET_PATTERNS.items():
            m = re.search(pattern, text, re.I)
            if m:
                problems.append(f"{f} - looks like a {label}: {m.group(0)[:40]}...")

        for email in set(EMAIL_RE.findall(text)):
            if email.lower() not in ALLOWED_EMAILS and "@" in email and "." in email:
                # Ignore CSS/font fragments like wght@6..72
                if re.match(r"^[\w.+-]+@[\w-]+\.[a-z]{2,}$", email, re.I):
                    problems.append(f"{f} - someone else's email address: {email}")

        for phone in set(PHONE_RE.findall(text)):
            problems.append(f"{f} - looks like a phone number: {phone.strip()}")

    # 3. History check - deleting a file does not unpublish it.
    hist = git("log", "--all", "--pretty=format:", "--name-only", "--diff-filter=A")
    for name in {n.strip() for n in hist.split("\n") if n.strip()}:
        if Path(name).suffix.lower() in RISKY_SUFFIXES:
            problems.append(
                f"{name} - was committed at some point and is still in the history"
            )

    # 4. Confirm the ignore rules are doing their job.
    ignored = [
        line[3:].strip().strip('"')
        for line in git("status", "--porcelain", "--ignored").split("\n")
        if line.startswith("!!")
    ]
    if ignored:
        notes.append("Kept private (on your computer only):")
        for i in ignored:
            notes.append(f"    {i}")

    for n in notes:
        print(f"  {n}")

    print()
    if problems:
        print("  STOP - do not push yet:\n")
        for p in problems:
            print(f"    x {p}")
        print(
            "\n  Remove the file, add it to .gitignore, then re-run this check.\n"
            "  If it was already committed, tell Claude - deleting it in a new\n"
            "  commit is NOT enough, the history has to be rewritten.\n"
        )
        return 1

    print("  OK No documents, personal contact details or credentials found.")
    print("  OK Safe to push.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

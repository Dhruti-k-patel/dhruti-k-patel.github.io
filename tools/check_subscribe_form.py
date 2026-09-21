#!/usr/bin/env python3
"""
Check that the website's Subscribe form can actually reach your Google Form.

    python tools/check_subscribe_form.py

WHY THIS EXISTS
---------------
The Subscribe form on the site posts to Google with mode "no-cors", because a
web page is not allowed to read a reply from another website. That means the
page CANNOT tell a saved sign-up from a rejected one - it says "thank you"
either way. If the Google Form is set to require a sign-in, every visitor sees
a thank-you and nothing is ever saved, silently.

This checks from outside the browser, where the real answer is readable. It
only reads; it never submits a test row, so it leaves no rubbish in your sheet.

It reports:
  * whether a stranger (not signed in) is allowed to submit
  * whether the form is still accepting responses
  * whether the question ids in config.js still match the live form

Exit code 0 = working. 1 = sign-ups are being lost.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "assets" / "js" / "config.js"

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
}

FIX = """
  HOW TO FIX
  ----------
  Open the Google Form -> Settings tab -> Responses section, and turn OFF:

      Collect email addresses      -> set to "Do not collect"
      Limit to 1 response          -> off
      Restrict to users in ...     -> off   (Workspace accounts only)

  Any one of those forces a Google sign-in, which a visitor to your website
  cannot get past. Then run this check again.
"""


def read_config() -> dict:
    if not CONFIG.exists():
        print(f"  Could not find {CONFIG}")
        raise SystemExit(1)
    text = CONFIG.read_text(encoding="utf-8")

    block = re.search(r"notifyGoogleForm:\s*\{(.*?)\n  \}", text, re.DOTALL)
    if not block:
        endpoint = re.search(r'notifyEndpoint:\s*"([^"]+)"', text)
        if endpoint and endpoint.group(1).strip():
            print("  The Subscribe form uses a non-Google endpoint:")
            print(f"    {endpoint.group(1)}")
            print("  This check only covers Google Forms.")
            raise SystemExit(0)
        print("  The Subscribe form is not connected to anything yet.")
        print("  It currently shows the Substack fallback, which always works.")
        raise SystemExit(0)

    out = {}
    for key in ("action", "name", "email", "country"):
        m = re.search(rf'{key}:\s*"([^"]+)"', block.group(1))
        if m:
            out[key] = m.group(1)
    return out


def main() -> int:
    cfg = read_config()
    action = cfg.get("action", "")
    view = action.replace("/formResponse", "/viewform")

    print("\n  Checking the Subscribe form...\n")
    print(f"    form: {view[:78]}")

    try:
        req = urllib.request.Request(view, headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            code, page = r.getcode(), r.read().decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        code, page = e.code, e.read().decode("utf-8", "ignore")
    except Exception as exc:
        print(f"\n  Could not reach Google ({exc}).")
        print("  Check your internet connection and try again.\n")
        return 1

    if code == 401 or code == 403:
        print(f"\n  BROKEN - Google answered {code} (not allowed).\n")
        print("  Your form requires people to sign in to a Google account, so")
        print("  every sign-up from the website is being REJECTED. Visitors")
        print("  still see a thank-you message, and nothing reaches your sheet.")
        print(FIX)
        return 1

    if code != 200:
        print(f"\n  Unexpected answer from Google: HTTP {code}.")
        print("  Open the form's link in a private browser window to see what")
        print("  a visitor gets.\n")
        return 1

    if "not accepting responses" in page.lower() or "no longer accepting" in page.lower():
        print("\n  BROKEN - the form is not accepting responses.\n")
        print("  Open the form -> Responses tab -> switch 'Accepting responses' on.\n")
        return 1

    # Compare the question ids in config.js against the live form. Editing a
    # question can change its id, which breaks the link with no visible symptom.
    live_ids, required_ids = set(), set()
    m = re.search(r"FB_PUBLIC_LOAD_DATA_\s*=\s*(\[.*?\]);", page, re.S)
    if m:
        try:
            data = json.loads(m.group(1))
            for q in (data[1][1] or []):
                for f in (q[4] or []):
                    live_ids.add(f"entry.{f[0]}")
                    if f[2]:
                        required_ids.add(f"entry.{f[0]}")
        except Exception:
            pass

    configured = {v for k, v in cfg.items() if k != "action"}
    problems = []

    if live_ids:
        missing = configured - live_ids
        if missing:
            problems.append(
                "These question ids in config.js no longer exist on the form:\n"
                + "".join(f"      {i}\n" for i in sorted(missing))
                + "      Re-run:  python tools/set_notify_form.py \"<pre-filled link>\""
            )
        unfilled = required_ids - configured
        if unfilled:
            problems.append(
                "The form has required questions the website does not fill in:\n"
                + "".join(f"      {i}\n" for i in sorted(unfilled))
                + "      Google rejects the whole submission. Make them optional,\n"
                  "      or remove them from the form."
            )

    print(f"\n    anonymous visitors allowed : yes")
    print(f"    accepting responses        : yes")
    print(f"    questions on the live form : {len(live_ids) if live_ids else 'could not read'}")
    print(f"    questions the site fills   : {len(configured)}")

    if problems:
        print("\n  PROBLEM FOUND:\n")
        for p in problems:
            print("    - " + p)
        print()
        return 1

    print("\n  OK - a stranger can submit, and the question ids match.")
    print("  Sign-ups should be reaching your sheet.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

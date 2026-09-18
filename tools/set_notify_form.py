#!/usr/bin/env python3
"""
Point the site's Subscribe form at your Google Form — in one command.

You do NOT need to read any page source or hunt for field ids. Instead:

  1. Build the Google Form with three short-answer questions, in any order:
        Name        Email        Country
  2. In the form editor, click the ⋮ menu (top right) → "Get pre-filled link".
  3. Type these exact words as the answers, then click "Get link" → "Copy link":
        Name    -> NAME
        Email   -> EMAIL
        Country -> COUNTRY
  4. Run:

        python tools/set_notify_form.py "<paste the copied link here>"

     (Keep the quotes — the URL contains & characters.)

The script reads the field ids out of that link, works out which is which from
the words you typed, and rewrites assets/js/config.js. Reload the site and the
Subscribe button shows the real Name / Email / Country form.

Re-run it any time the form changes.
  --check   show what is configured right now
  --reset   disconnect the form again (Subscribe goes back to Substack)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlparse

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "assets" / "js" / "config.js"

# Which typed word marks which field. Matched case-insensitively, and only as a
# whole word, so a country literally called "Chad" cannot be read as the name.
MARKERS = {
    "name": "name",
    "email": "email",
    "country": "country",
}


def fail(msg: str) -> "NoReturn":  # type: ignore[valid-type]
    print(f"\nError: {msg}\n", file=sys.stderr)
    raise SystemExit(1)


def action_url(url: str) -> str:
    """Turn any Google Form url into its /formResponse POST endpoint."""
    m = re.match(r"(https://docs\.google\.com/forms/d/e/[^/]+)/", url)
    if m:
        return m.group(1) + "/formResponse"

    # The easiest mistake to make: copying the address bar of the prefill or
    # edit page instead of finishing the flow and copying the generated link.
    # Those urls use the editor's form id (/forms/d/ID/) rather than the public
    # responder id (/forms/d/e/LONG_ID/), and carry no entry.* fields.
    if re.match(r"https://docs\.google\.com/forms/d/[^/e][^/]*/(prefill|edit)", url):
        fail(
            "that is the prefill/edit PAGE, not the pre-filled LINK.\n\n"
            "You are on the right page — just finish the flow:\n"
            "  1. Type NAME, EMAIL and COUNTRY into the three answer boxes.\n"
            "  2. Click 'Get link' at the bottom of the screen.\n"
            "  3. Click 'COPY LINK' in the bar that appears.\n"
            "  4. Re-run this command with THAT link.\n\n"
            "The right link looks like:\n"
            "  https://docs.google.com/forms/d/e/1FAIpQLS.../viewform"
            "?usp=pp_url&entry.123=NAME&entry.456=EMAIL&entry.789=COUNTRY"
        )

    fail(
        "that does not look like a Google Forms pre-filled link.\n"
        "It should start with https://docs.google.com/forms/d/e/..."
    )


EMAIL_LIKE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def read_fields(url: str) -> tuple[dict[str, str], dict[str, str], bool]:
    """Map name/email/country -> entry id.

    Preferred: the answers were typed as the words NAME, EMAIL, COUNTRY.
    Otherwise fall back to inferring from whatever sample answers were used —
    anything shaped like an address is the email field, and the two remaining
    fields are taken in the order Google wrote them, which is the order the
    questions appear on the form. That guess is printed for checking.
    """
    # parse_qsl, not parse_qs: question order is the fallback's whole basis.
    pairs = [
        (k, v) for k, v in parse_qsl(urlparse(url).query, keep_blank_values=True)
        if k.startswith("entry.")
    ]
    entries = dict(pairs)

    if not entries:
        fail(
            "no entry.* fields found in that link.\n"
            "Make sure you copied the PRE-FILLED link (⋮ menu → Get pre-filled\n"
            "link → fill the answers → Get link → Copy link), not the plain\n"
            "form url."
        )

    found: dict[str, str] = {}
    for entry_id, value in pairs:
        text = value.strip().lower()
        for field, marker in MARKERS.items():
            if re.fullmatch(rf"\W*{marker}\W*", text) and field not in found:
                found[field] = entry_id

    exact = len(found) >= 2

    if not exact:
        # Address-shaped value wins the email slot.
        if "email" not in found:
            for entry_id, value in pairs:
                if EMAIL_LIKE.match(value.strip()):
                    found["email"] = entry_id
                    break
        # Then name, then country, in the order the questions appear.
        rest = [eid for eid, _ in pairs if eid not in found.values()]
        for field in ("name", "country"):
            if field not in found and rest:
                found[field] = rest.pop(0)

    missing = [f for f in ("name", "email") if f not in found]
    if missing:
        print("\nThis is what the link contained:\n")
        for entry_id, value in pairs:
            print(f"    {entry_id} = {value!r}")
        fail(
            "could not work out which field is the "
            + " and the ".join(missing) + ".\n"
            "Redo the pre-filled link typing exactly NAME, EMAIL and COUNTRY\n"
            "as the three answers."
        )

    if "country" not in found:
        print("  ! No country field found — the form will send name and email only.")

    return found, entries, exact


def patch_config(action: str, fields: dict[str, str]) -> None:
    if not CONFIG.exists():
        fail(f"{CONFIG} not found.")

    text = CONFIG.read_text(encoding="utf-8")

    country_line = (
        f'\n    country: "{fields["country"]}"' if "country" in fields else ""
    )
    block = (
        "  notifyGoogleForm: {\n"
        f'    action:  "{action}",\n'
        f'    name:    "{fields["name"]}",\n'
        f'    email:   "{fields["email"]}",'
        f"{country_line}\n"
        "  },"
    )

    # Replace either the `null` placeholder or a previously written block.
    new_text, n = re.subn(
        r"  notifyGoogleForm:\s*(?:null|\{.*?\n  \}),",
        block.replace("\\", "\\\\"),
        text,
        count=1,
        flags=re.DOTALL,
    )
    if not n:
        fail(
            "could not find the notifyGoogleForm setting in config.js.\n"
            "If you edited that file by hand, restore the line:\n"
            "    notifyGoogleForm: null,"
        )

    CONFIG.write_text(new_text, encoding="utf-8")


def show_current() -> None:
    text = CONFIG.read_text(encoding="utf-8") if CONFIG.exists() else ""
    m = re.search(r"  notifyGoogleForm:\s*(null|\{.*?\n  \}),", text, re.DOTALL)
    ep = re.search(r'  notifyEndpoint:\s*"([^"]*)"', text)
    print("\nCurrent configuration in assets/js/config.js:\n")
    print("  notifyGoogleForm:", (m.group(1) if m else "not found"))
    print("  notifyEndpoint:  ", repr(ep.group(1)) if ep else "not found")
    configured = bool(m and m.group(1) != "null") or bool(ep and ep.group(1).strip())
    print(
        "\n  => The Subscribe button shows "
        + ("the Name / Email / Country form." if configured else "the Substack fallback.")
        + "\n"
    )


def reset() -> None:
    text = CONFIG.read_text(encoding="utf-8")
    new_text, n = re.subn(
        r"  notifyGoogleForm:\s*(?:null|\{.*?\n  \}),",
        "  notifyGoogleForm: null,",
        text,
        count=1,
        flags=re.DOTALL,
    )
    if not n:
        fail("could not find the notifyGoogleForm setting in config.js.")
    CONFIG.write_text(new_text, encoding="utf-8")
    print("\nDisconnected. Subscribe now shows the Substack fallback again.\n")


def main(argv: list[str]) -> int:
    if len(argv) == 1 and argv[0] == "--check":
        show_current()
        return 0

    if len(argv) == 1 and argv[0] == "--reset":
        reset()
        return 0

    if len(argv) != 1 or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0 if argv and argv[0] in ("-h", "--help") else 1

    url = argv[0].strip().strip('"').strip("'")

    action = action_url(url)
    fields, samples, exact = read_fields(url)

    patch_config(action, fields)

    print("\nDone. assets/js/config.js now points at your Google Form.\n")
    print(f"  action   {action}\n")

    header = "  Field     Entry id             Your sample answer"
    print(header)
    print("  " + "-" * (len(header) - 2))
    for key in ("name", "email", "country"):
        if key in fields:
            eid = fields[key]
            print(f"  {key:9} {eid:20} {samples.get(eid, '')!r}")

    if not exact:
        print(
            "\n  ^ CHECK THIS TABLE. You used your own answers rather than the\n"
            "    words NAME/EMAIL/COUNTRY, so the mapping above was inferred\n"
            "    from them. If any row is matched to the wrong question, redo\n"
            "    the pre-filled link typing NAME, EMAIL and COUNTRY and re-run."
        )

    print(
        "\nNext: reload the site, click Subscribe, and send yourself a test\n"
        "sign-up. Then check the row actually landed in the form's Responses\n"
        "tab — the browser cannot read Google's reply, so the page reports\n"
        "success as long as the request was sent.\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

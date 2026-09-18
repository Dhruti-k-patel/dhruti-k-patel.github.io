# Dr. Dhruti Kunjit Patel — personal website

A single-page personal site: profile, IPO/RHP research work, the full mPulse
India Substack archive, Substack Notes, career timeline, achievements and
publications.

Plain HTML, CSS and JavaScript. No build step, no framework, no dependencies.

---

## Files

```
index.html                 The whole page
assets/css/style.css       All styling (light + dark themes)
assets/js/main.js          Rendering, filters, search, theme toggle
assets/img/dhruti-patel.jpg  Portrait (extracted from the CV PDF)
data/articles.json         Substack posts          ─┐
data/notes.json            Substack Notes            ├─ generated
data/substack.js           Both, as a <script> file ─┘
tools/fetch_substack.py    Regenerates the three files above
tools/set_notify_form.py   Connects the Subscribe form to your Google Form
assets/js/config.js        Subscribe-form settings (the only file to edit)
Links.txt                  Source list of social links
Professional CV Resume.pdf Source CV
```

`index.html` loads `data/substack.js`, not the JSON. The JSON files are there
for reference and for any other tool that wants them; the `.js` file is what
the page actually reads, because `fetch()` of a local JSON file is blocked when
the page is opened directly from disk.

---

## Viewing it locally

Double-clicking `index.html` works. To serve it properly:

```bash
python -m http.server 5173
```

Then open <http://localhost:5173>.

---

## Updating the Substack content

Whenever you publish a new article or note, run:

```bash
python tools/fetch_substack.py
```

That re-reads the Substack API and rewrites `data/articles.json`,
`data/notes.json` and `data/substack.js`. Refresh the page and the new content
is there — no other edit needed. Article counts, tags, reading times and the
"last synced" line all update themselves.

Requires Python 3 and an internet connection. Nothing else to install. If the
network call fails the script exits without touching the existing files, so a
failed run can never blank the site.

### The three article filters

The Writing section filters on what a piece *is*, not on Substack tags — the
tags overlap so much (nearly every post carries `IPO`, `Equity Research` and
`Stock Analysis` at once) that filtering on them showed the same articles under
every heading. The three buckets are:

| Bucket | Means |
|---|---|
| **IPO & RHP analysis** | A named company's prospectus or post-listing read |
| **Frameworks** | A repeatable method, not about one company |
| **Markets & sectors** | Macro, sector or seasonality work |

`tools/fetch_substack.py` assigns these automatically and prints the split every
time it runs, so a mis-filed post is obvious:

```
IPO & RHP analysis (6)
  - NSE IPO at ₹1,785: What One Lot Actually Buys You
  ...
Frameworks (2)
  ...
```

If a future post lands in the wrong bucket, add its slug to
`CATEGORY_OVERRIDES` near the top of the script:

```python
CATEGORY_OVERRIDES = {
    "some-post-slug": "method",   # "company" | "method" | "markets"
}
```

The slug is the last part of the Substack URL. Don't edit the rules themselves —
the override list is there so you never have to.

---

## The notification sign-up  ⚠️ needs one setting before you publish

The bell in the header opens a form collecting **name, email and country**.

This site is static — it has no server of its own — so the form has to hand the
details to a service that stores them. **Until you configure one, the bell shows
a Substack subscribe link instead of the form.** That is deliberate: a visitor
never meets a form that cannot submit. But you won't collect any names or
countries until you do the five minutes below.

Everything is set in **`assets/js/config.js`**. Pick one option.

### Option A — Google Forms (free, unlimited, and you already use Google Forms)

**You don't need to read any page source or hunt for field ids.** There's a
script for it.

1. Create a Google Form with three short-answer questions, in any order:
   **Name**, **Email**, **Country**.
2. In the form editor, click the **⋮** menu (top right) → **Get pre-filled
   link**.
3. Type these exact words as the three answers, then **Get link** → **Copy
   link**:

   | Question | Type this |
   |---|---|
   | Name | `NAME` |
   | Email | `EMAIL` |
   | Country | `COUNTRY` |

4. Run, with the link in quotes (it contains `&`):

```bash
python tools/set_notify_form.py "PASTE_THE_COPIED_LINK_HERE"
```

That reads the field ids out of the link, works out which is which from the
words you typed, and writes `config.js` for you. Reload the site — the Subscribe
button now shows the real Name / Email / Country form.

Other commands:

```bash
python tools/set_notify_form.py --check
```

```bash
python tools/set_notify_form.py --reset
```

`--check` prints what's configured; `--reset` disconnects the form so Subscribe
goes back to Substack.

Responses land in the form's **Responses** tab and its linked Google Sheet.

**One caveat worth knowing.** The browser will not let this page read Google's
reply, so the form reports success as long as the request left the browser — it
cannot tell a saved row from a rejected one. After setting it up, send yourself
a test sign-up and confirm the row actually appears in the Responses tab. Do the
same if you ever edit the form's questions, because changing a question can
change its entry id and silently break the link.

### Option B — Formspree, Basin, Netlify Forms

Create a form, copy its endpoint, and set `notifyEndpoint: "https://formspree.io/f/abcdwxyz"`.
These return a real response, so genuine failures show an error. Free tiers are
usually capped around 50 submissions a month.

### Then: sending the notifications

The form **collects** addresses into your Google Sheet; it does not send
anything. When you publish a new analysis, email the list yourself.

To get the addresses out: open the responses Sheet → **File → Download →
Comma-separated values**, or just copy the Email column.

Two limits worth knowing before you plan around this, because they apply to
sending by hand as much as to anything automated:

- **Gmail, personal account:** 500 recipients per day, 100 per individual
  message when using To/Cc/Bcc.
- **Google Workspace:** 2,000 recipients per day.

Above that you need a proper email service (Brevo, MailerLite and Mailchimp all
have free tiers). They also handle unsubscribes, bounces and spam compliance,
which matters once the list is real — your form collects country, so you will
have EU and UK readers who have removal rights.

If you would rather not run a list at all, leave `config.js` untouched — the
Subscribe button keeps pointing at Substack, which already emails subscribers on
every new post.

### What the form does

- Validates name, email and country before sending
- Requires a consent tick, and states what the details are used for
- Has a hidden honeypot field that silently drops bot submissions
- Remembers a successful sign-up in that browser and hides the bell's dot
- On failure, keeps the details on screen and offers your email address

---

## Updating everything else

The CV content is written directly into `index.html`, in clearly labelled
sections. To change a job, an award or a publication, edit the matching block:

| Section | Anchor in `index.html` |
|---|---|
| Headline, intro, stats | `<section class="hero" id="top">` |
| About, OWNERS framework | `id="about"` |
| Articles | `id="writing"` (content is generated) |
| Notes | `id="notes"` (content is generated) |
| Career timeline | `id="experience"` |
| Awards, patents, talks, service | `id="achievements"` |
| Publications, education, skills | `id="research"` |
| Links | `id="contact"` |

The hero statistics near the top of `index.html` are hardcoded except the
article count, which comes from the Substack data.

---

## Publishing

The site is static, so anything that serves files will host it.

**GitHub Pages** (you already use `dhruti-k-patel.github.io` for the IPO test):

1. Create a repository — `dhruti-k-patel.github.io` for the root domain, or any
   name for a subpath.
2. Push the contents of this folder to it.
3. Settings → Pages → Source: *Deploy from a branch*, branch `main`, folder `/`.

**Netlify or Cloudflare Pages:** drag the folder onto their dashboard. No build
command, publish directory `.`.

After publishing, update the `<link rel="canonical">` and `og:image` URLs near
the top of `index.html` to the real address.

---

## Notes on what was left out

Several details from the CV are deliberately **not** on the public site and
**not** in this repository: personal identifying details, the personal mobile
number, and the referees' contact details.

Those belong on a CV sent to a named recipient, not on a public page — the
referees' details especially, which are other people's data to protect, not
mine. Email and city are published; add anything else
back if you want it.

Every page that shows research content also carries the SEBI disclaimer, in the
Writing section intro and again in the footer.

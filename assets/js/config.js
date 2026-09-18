/* =============================================================================
   Site configuration — edit this file, not the others.

   ─────────────────────────────────────────────────────────────────────────
   THE NOTIFICATION FORM NEEDS ONE OF THE TWO OPTIONS BELOW FILLED IN.
   Until then the bell still works, but it offers Substack instead of the
   name/email/country form — a visitor never sees a form that cannot submit.
   ─────────────────────────────────────────────────────────────────────────

   This site is static (no server of its own), so the form has to hand the
   details to a service that stores them. Pick either option.

   ── Option A — Google Forms (free, unlimited, you already use it) ──────────
   1. Create a Google Form with three short-answer questions:
      Name, Email, Country. Mark them required.
   2. Open the live form, right-click → View Page Source, and search for
      "entry." — you will find one id per question, like entry.1234567890.
   3. Copy the form's POST url. It looks like:
      https://docs.google.com/forms/d/e/1FAIpQLS.../formResponse
      (note: formResponse, not viewform)
   4. Fill in notifyGoogleForm below.
   Responses land in the form's linked Google Sheet.

   ── Option B — Formspree, Basin, Netlify Forms, etc. ──────────────────────
   Create a form, copy its endpoint (e.g. https://formspree.io/f/abcdwxyz)
   and put it in notifyEndpoint below. Free tiers are usually capped at
   around 50 submissions a month.

   Option A is used if both are filled in.
   ========================================================================= */

window.SITE_CONFIG = {

  // ── Option A ──────────────────────────────────────────────────────────
  notifyGoogleForm: {
    action:  "https://docs.google.com/forms/d/e/1FAIpQLSed5OQea0oPwEMW-g1228-HKjdAVv32nOqhdWsZiUJrswFB1A/formResponse",
    name:    "entry.34281303",
    email:   "entry.1042287105",
    country: "entry.1055462253"
  },
  /* Example — replace every value with your own:
  notifyGoogleForm: {
    action:  "https://docs.google.com/forms/d/e/1FAIpQLSxxxxxxxx/formResponse",
    name:    "entry.1111111111",
    email:   "entry.2222222222",
    country: "entry.3333333333"
  },
  */

  // ── Option B ──────────────────────────────────────────────────────────
  notifyEndpoint: "",

  // Shown as the fallback, and after a successful sign-up.
  substackUrl: "https://mpulseindia.substack.com/",

  // Pinned to the top of the country list.
  topCountries: ["IN", "AE"]
};

/* =============================================================================
   Notification sign-up — name, email and country.

   Where the details go is set in assets/js/config.js. Two transports:

     Google Forms  posted as form-data with mode:"no-cors". The browser will
                   not let us read the response, so a submission that reaches
                   Google looks identical to one that did not. We therefore
                   treat "the request did not throw" as success — which is the
                   normal trade-off for this approach.
     JSON endpoint (Formspree, Basin, Netlify) returns a real response, so
                   errors surface properly.

   With neither configured, the form is hidden and the Substack fallback is
   shown instead, so a visitor never meets a form that cannot submit.
   ========================================================================== */

(function () {
  'use strict';

  var cfg = window.SITE_CONFIG || {};
  var $ = function (id) { return document.getElementById(id); };

  var dlg      = $('notifyDialog');
  var openBtn  = $('notifyToggle');
  var closeBtn = $('notifyClose');
  var form     = $('notifyForm');
  var fallback = $('notifyFallback');
  var statusEl = $('notifyStatus');
  var dot      = $('notifyDot');

  if (!dlg || !openBtn) return;

  var gf = cfg.notifyGoogleForm;
  var useGoogle = !!(gf && gf.action && gf.email);
  var endpoint = (cfg.notifyEndpoint || '').trim();
  var configured = useGoogle || !!endpoint;

  var STORE_KEY = 'dkp-notified';

  function readStore() {
    try { return localStorage.getItem(STORE_KEY); } catch (e) { return null; }
  }
  function writeStore(v) {
    try { localStorage.setItem(STORE_KEY, v); } catch (e) { /* private mode */ }
  }

  /* ------------------------------------------------------- country list --- */

  // ISO 3166-1 alpha-2. Names come from Intl.DisplayNames so we don't ship
  // 250 English strings; the code itself is the fallback.
  var CODES = ('AD AE AF AG AI AL AM AO AR AS AT AU AW AX AZ BA BB BD BE BF BG BH BI BJ BL BM BN BO BQ ' +
    'BR BS BT BW BY BZ CA CC CD CF CG CH CI CK CL CM CN CO CR CU CV CW CX CY CZ DE DJ DK DM DO DZ EC ' +
    'EE EG EH ER ES ET FI FJ FK FM FO FR GA GB GD GE GF GG GH GI GL GM GN GP GQ GR GT GU GW GY HK HN ' +
    'HR HT HU ID IE IL IM IN IO IQ IR IS IT JE JM JO JP KE KG KH KI KM KN KP KR KW KY KZ LA LB LC LI ' +
    'LK LR LS LT LU LV LY MA MC MD ME MF MG MH MK ML MM MN MO MP MQ MR MS MT MU MV MW MX MY MZ NA NC ' +
    'NE NF NG NI NL NO NP NR NU NZ OM PA PE PF PG PH PK PL PM PN PR PS PT PW PY QA RE RO RS RU RW SA ' +
    'SB SC SD SE SG SH SI SJ SK SL SM SN SO SR SS ST SV SX SY SZ TC TD TG TH TJ TK TL TM TN TO TR TT ' +
    'TV TW TZ UA UG US UY UZ VA VC VE VG VI VN VU WF WS YE YT ZA ZM ZW').split(' ');

  function buildCountries() {
    var sel = $('notifyCountry');
    if (!sel) return;

    var namer = null;
    try { namer = new Intl.DisplayNames(['en'], { type: 'region' }); } catch (e) { /* older browser */ }

    var seen = {};
    var list = [];
    CODES.forEach(function (code) {
      if (seen[code]) return;
      seen[code] = true;
      var name = code;
      if (namer) { try { name = namer.of(code) || code; } catch (e) { /* bad code */ } }
      list.push({ code: code, name: name });
    });
    list.sort(function (a, b) { return a.name.localeCompare(b.name); });

    var top = (cfg.topCountries || []).map(function (code) {
      return list.filter(function (c) { return c.code === code; })[0];
    }).filter(Boolean);

    var frag = document.createDocumentFragment();

    function option(c) {
      var o = document.createElement('option');
      o.value = c.name;      // store the readable name, not the code
      o.textContent = c.name;
      return o;
    }

    if (top.length) {
      top.forEach(function (c) { frag.appendChild(option(c)); });
      var rule = document.createElement('option');
      rule.disabled = true;
      rule.textContent = '──────────';
      frag.appendChild(rule);
    }
    list.forEach(function (c) { frag.appendChild(option(c)); });

    sel.appendChild(frag);
  }

  /* -------------------------------------------------------------- dialog --- */

  var lastFocus = null;

  function open() {
    lastFocus = document.activeElement;
    setStatus('', '');
    if (typeof dlg.showModal === 'function') {
      dlg.showModal();
    } else {
      dlg.setAttribute('open', '');  // very old browsers: renders inline
    }
    var first = configured ? $('notifyName') : $('notifyFallbackLink');
    if (first) setTimeout(function () { first.focus(); }, 40);
  }

  function close() {
    if (typeof dlg.close === 'function') dlg.close();
    else dlg.removeAttribute('open');
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }

  openBtn.addEventListener('click', open);
  if (closeBtn) closeBtn.addEventListener('click', close);

  // Click on the backdrop (outside the panel) closes.
  dlg.addEventListener('click', function (e) {
    if (e.target === dlg) close();
  });

  /* ----------------------------------------------------------- validation --- */

  function setError(id, msg) {
    var field = document.querySelector('.field-error[data-for="' + id + '"]');
    var input = $(id);
    if (field) field.textContent = msg || '';
    if (input) {
      input.classList.toggle('has-error', !!msg);
      if (msg) input.setAttribute('aria-invalid', 'true');
      else input.removeAttribute('aria-invalid');
    }
  }

  function setStatus(msg, kind) {
    if (!statusEl) return;
    statusEl.textContent = msg || '';
    statusEl.className = 'notify-status' + (kind ? ' is-' + kind : '');
  }

  // Deliberately permissive: the job here is to catch typos, not to police
  // what a valid address looks like.
  var EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

  function validate() {
    var ok = true;
    var name = $('notifyName').value.trim();
    var email = $('notifyEmail').value.trim();
    var country = $('notifyCountry').value;
    var consent = $('notifyConsent').checked;

    setError('notifyName', '');
    setError('notifyEmail', '');
    setError('notifyCountry', '');
    setError('notifyConsent', '');

    if (name.length < 2) { setError('notifyName', 'Please enter your name.'); ok = false; }
    if (!EMAIL_RE.test(email)) { setError('notifyEmail', 'Please enter a valid email address.'); ok = false; }
    if (!country) { setError('notifyCountry', 'Please choose your country.'); ok = false; }
    if (!consent) { setError('notifyConsent', 'Please tick the box to continue.'); ok = false; }

    return ok ? { name: name, email: email, country: country } : null;
  }

  /* --------------------------------------------------------------- submit --- */

  function sendGoogle(data) {
    var body = new FormData();
    body.append(gf.name, data.name);
    body.append(gf.email, data.email);
    if (gf.country) body.append(gf.country, data.country);
    // no-cors: the response is opaque, so this resolves as long as the
    // request left the browser.
    return fetch(gf.action, { method: 'POST', mode: 'no-cors', body: body });
  }

  function sendEndpoint(data) {
    return fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
      body: JSON.stringify(data)
    }).then(function (res) {
      if (!res.ok) throw new Error('Request failed with status ' + res.status);
      return res;
    });
  }

  if (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();

      // Honeypot filled means a bot. Pretend it worked and drop it.
      if ($('notifyWebsite') && $('notifyWebsite').value) {
        setStatus('Thanks — you are on the list.', 'ok');
        return;
      }

      var data = validate();
      if (!data) { setStatus('Please check the fields above.', 'error'); return; }

      var btn = $('notifySubmit');
      btn.disabled = true;
      var label = btn.textContent;
      btn.textContent = 'Sending…';
      setStatus('', '');

      (useGoogle ? sendGoogle(data) : sendEndpoint(data))
        .then(function () {
          form.hidden = true;
          writeStore(data.email);
          if (dot) dot.hidden = true;
          setStatus('Thank you, ' + data.name.split(' ')[0] +
            '. You will get an email when the next analysis is published.', 'ok');
        })
        .catch(function (err) {
          btn.disabled = false;
          btn.textContent = label;
          setStatus('Sorry — that did not go through. Please try again, or email ' +
            'dkpatel1888@gmail.com directly.', 'error');
          if (window.console) console.error('[notify] submission failed:', err);
        });
    });

    // Clear a field's error as soon as the visitor starts fixing it.
    ['notifyName', 'notifyEmail', 'notifyCountry', 'notifyConsent'].forEach(function (id) {
      var el = $(id);
      if (el) el.addEventListener('input', function () { setError(id, ''); });
      if (el) el.addEventListener('change', function () { setError(id, ''); });
    });
  }

  /* ----------------------------------------------------------------- init --- */

  if (configured) {
    buildCountries();
  } else {
    if (form) form.hidden = true;
    if (fallback) fallback.hidden = false;
    var link = $('notifyFallbackLink');
    if (link && cfg.substackUrl) link.href = cfg.substackUrl;
    if (window.console) {
      console.info('[notify] No form endpoint configured — showing the Substack ' +
        'fallback. Set notifyGoogleForm or notifyEndpoint in assets/js/config.js.');
    }
  }

  // Someone who already signed up does not need the attention dot.
  if (dot && readStore()) dot.hidden = true;
})();

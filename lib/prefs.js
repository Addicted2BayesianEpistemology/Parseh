// SPDX-License-Identifier: GPL-3.0-or-later
/* Parseh — the reading place and the settings, kept by the toolbox (§4.9).

   Every browser used to keep its own: the phone knew nothing of where the
   computer had stopped, and a speed set at the desk had to be set again in
   bed.  Now the toolbox keeps them (lib/prefs.py, config/prefs.json) and
   every page asks for them at load:

     - **the settings that follow a person** -- the narration's speed, the
       pause between repetitions, how far ↺ and ↻ carry, whether a chapter's
       start waits for play, and the theme.  THE LAST CHANGE WINS, plainly,
       and each value carries the moment it was made so that a device which
       was away does not undo a newer one;
     - **the reading place**, per book.  NOTHING IS OVERRULED HERE.  A book
       opens where THIS device left it, as it always did, and when the
       toolbox's place is somewhere else it is ASKED, in a line at the top of
       the page: "On the computer you were at 3 · 12.1, 2 hours ago. Go
       there?" (the owner's choice, 2026-09-22).

   WHAT IS SHOWN STAYS WITH THE DEVICE THAT SHOWS IT: which passes are open,
   the size of the text, the margins.  A phone is not a desk.

   HOW A CHANGE IS NOTICED.  Every page of the toolbox keeps these in
   localStorage, and the readers -- built pages, thousands of them, built
   before any of this existed -- write theirs straight from their own
   handlers.  So rather than ask each page to tell us, setItem itself is
   wrapped: whatever writes one of these keys, the toolbox hears it.  Where a
   browser will not have its setItem wrapped, the keys are read again
   whenever the page comes back to the front. */
(function () {
  'use strict';
  if (window.ParsehPrefs) return;

  var KEYS = ['bk_rate', 'bk_gap', 'bk_skip', 'bk_stopbnd', 'parseh_theme'];
  var AT = 'parseh_at';                 // when this device last set each of them
  var POS = /^bk_pos:/;                 // a reader's own reading place
  var WAIT = 900;                       // a moment's grace before the toolbox is told
  var here = null, asked = false, timer = null, out = {settings: {}, place: null};
  // Until the toolbox has answered, a reading place written by this page is
  // NOT a person reading: a reader saves its place as it restores it at load,
  // and taking that for fresh reading would both silence the question below
  // and push an untouched place over a newer one made elsewhere.
  var ready = false;

  function get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function put(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  function ats() {
    try { return JSON.parse(get(AT) || '{}') || {}; } catch (e) { return {}; }
  }
  function setAt(k, when) {
    var m = ats();
    m[k] = when;
    put(AT, JSON.stringify(m));
  }
  function now() { return Date.now() / 1000; }

  /* The device, named by itself -- "Android phone · Chrome" -- so that the
     line asking about a reading place can say whose place it is.  Nothing to
     type, and nothing that leaves this machine. */
  function device() {
    var ua = navigator.userAgent || '';
    var what = /Android/i.test(ua) ? (/Mobile/.test(ua) ? 'Android phone' : 'Android tablet')
             : /iPhone/i.test(ua) ? 'iPhone'
             : /iPad/i.test(ua) ? 'iPad'
             : /Windows/i.test(ua) ? 'Windows computer'
             : /Macintosh|Mac OS/i.test(ua) ? 'Mac'
             : /CrOS/i.test(ua) ? 'Chromebook'
             : /Linux/i.test(ua) ? 'Linux computer' : 'this device';
    var who = /Edg\//.test(ua) ? 'Edge'
            : /OPR\//.test(ua) ? 'Opera'
            : /Firefox\//.test(ua) ? 'Firefox'
            : /Chrome\//.test(ua) ? 'Chrome'
            : /Safari\//.test(ua) ? 'Safari' : '';
    return who ? what + ' · ' + who : what;
  }

  function when(at) {
    var s = Math.max(0, now() - (at || 0));
    if (s < 90) return 'a moment ago';
    if (s < 3600) return Math.round(s / 60) + ' minutes ago';
    if (s < 7200) return 'an hour ago';
    if (s < 86400) return Math.round(s / 3600) + ' hours ago';
    if (s < 172800) return 'yesterday';
    return Math.round(s / 86400) + ' days ago';
  }

  /* ---- telling the toolbox ---- */
  function send() {
    clearTimeout(timer);
    timer = null;
    var body = {by: device()};
    var any = false;
    if (Object.keys(out.settings).length) { body.settings = out.settings; any = true; }
    if (out.place) { body.place = out.place; any = true; }
    if (!any) return;
    out = {settings: {}, place: null};
    try {
      fetch('/__prefs', {method: 'POST', headers: {'Content-Type': 'application/json'},
                         body: JSON.stringify(body)}).catch(function () {});
    } catch (e) {}
  }
  function later() {
    if (timer) return;
    timer = setTimeout(send, WAIT);
  }
  function changed(key, value) {
    var at = now();
    if (KEYS.indexOf(key) >= 0) {
      setAt(key, at);
      out.settings[key] = {v: value, at: at};
      later();
      return;
    }
    if (here && key === here.key) {
      if (!ready) return;                 // the page settling in, not reading
      var p = placeNow(at);
      // a reader that has read nothing yet keeps {i: -1}: that is not a
      // place, and it must not be taken for one -- neither told to the
      // toolbox, nor remembered here as a moment when this device read
      if (!p) return;
      setAt(key, at);
      out.place = p;
      later();
    }
  }

  /* ---- a reader's place ---- */
  function placeNow(at) {
    var p = {path: location.pathname, i: 0, at: at || now()};
    try {
      var v = JSON.parse(get(here.key) || 'null');
      if (!v || typeof v.i !== 'number' || v.i < 0) return null;
      p.i = v.i;
      // said in words, so the OTHER device can ask about it plainly, and as
      // a percentage, so the shelf can show how far the book has been read
      try {
        p.label = (SUBS[v.i] && (SUBS[v.i][5] || SUBS[v.i][4])) || '';
        p.pct = Math.max(1, Math.min(100, Math.round((v.i + 1) * 100 / SUBS.length)));
      } catch (e) {}
    } catch (e) { return null; }
    return p;
  }
  function goTo(i) {
    // the reader's own state, as lib/narrctl.js moves it: the mark, the
    // place kept for next time, and where the playing stops
    try {
      void [cur, hl, save, SUBS];
      if (!(i >= 0 && i < SUBS.length)) return false;
      cur = i;
      hl(i, true);
      save();
      return true;
    } catch (e) { return false; }
  }
  /* A SHEET OVER THE PAGE IS SOMEBODY IN THE MIDDLE OF SOMETHING.  The
     question below is drawn at the foot of the window, over everything (it
     has to be seen), and the reader's own sheets stand there too: the card
     panel, a note, the card kit's cut editor, the timings.  Asked while one
     of them is open, it lands on top of that sheet's own buttons -- Save
     under a line about where you were reading -- and the reader cannot
     press what they came for.  So the question waits, and is asked when the
     page is the page again.  It is never dropped: where you were is worth
     saying whenever the reading starts. */
  function sheetOver() {
    var open = document.querySelector(
      '#ankiback:not([hidden]), #ntback:not([hidden]), .pc-root, .tl-root');
    return !!(open && (!open.getClientRects || open.getClientRects().length));
  }
  function ask(rec) {
    if (asked || !rec) return;
    if (sheetOver()) { setTimeout(function () { ask(rec); }, 700); return; }
    asked = true;
    var bar = document.createElement('div');
    bar.className = 'pf-bar';
    bar.setAttribute('role', 'status');
    var says = document.createElement('span');
    says.textContent = 'On ' + (rec.by || 'another device') + ' you were at ' +
                       (rec.label ? '⁨' + rec.label + '⁩' : 'a later place') +
                       ', ' + when(rec.at) + '.';
    bar.appendChild(says);
    var go = document.createElement('button');
    go.type = 'button';
    go.className = 'pf-go';
    go.textContent = 'Go there';
    go.addEventListener('click', function () {
      goTo(rec.i);
      bar.remove();
    });
    var stay = document.createElement('button');
    stay.type = 'button';
    stay.className = 'pf-stay';
    stay.textContent = 'Stay here';
    stay.addEventListener('click', function () {
      bar.remove();
      // staying is a decision: this device's place is the newer one now
      var p = placeNow(now());
      if (p) { out.place = p; later(); }
    });
    bar.appendChild(go);
    bar.appendChild(stay);
    document.body.appendChild(bar);
  }

  /* ---- what the toolbox has, at load ---- */
  function apply(doc) {
    var mine = ats(), settings = (doc && doc.settings) || {};
    KEYS.forEach(function (k) {
      var srv = settings[k];
      var at = +mine[k] || 0;
      if (srv && typeof srv.v === 'string') {
        if ((+srv.at || 0) > at + 0.5) {          // the toolbox knows better
          if (get(k) !== srv.v) {
            put(k, srv.v);
            wear(k, srv.v);
          }
          setAt(k, +srv.at || now());
          return;
        }
      }
      var v = get(k);
      if (v !== null && (at > (+((srv || {}).at) || 0) || !srv)) {
        out.settings[k] = {v: v, at: at || now()};   // this device knows better
        later();
      }
    });
    if (!here) { ready = true; return; }
    var rec = (doc && doc.places && doc.places[location.pathname]) || null;
    var own = null;
    try { own = JSON.parse(get(here.key) || 'null'); } catch (e) {}
    var mineAt = +ats()[here.key] || 0;
    if (own && !(typeof own.i === 'number' && own.i >= 0)) own = null;   // nothing read here yet
    if (!rec) {
      // nobody has told the toolbox about this book: what this device knows
      if (own) { out.place = placeNow(mineAt || now()); later(); }
      ready = true;
      return;
    }
    // the same place, or this device's is the newer one: nothing to ask
    if (own) {
      if (own.i === rec.i) { ready = true; return; }
      if (mineAt > (+rec.at || 0)) { out.place = placeNow(mineAt); later(); ready = true; return; }
    }
    ready = true;
    ask(rec);
  }
  // a setting the toolbox brought: worn at once where the page can wear it
  function wear(key, v) {
    try {
      if (key === 'parseh_theme' && window.Parseh && Parseh.theme) { Parseh.theme.apply(); return; }
      if (key === 'bk_rate' && window.ParsehNarr) { ParsehNarr.setRate(parseFloat(v), true); return; }
      if (key === 'bk_skip' && window.ParsehNarr) { ParsehNarr.setSecs(parseInt(v, 10)); return; }
      if (key === 'bk_gap') {
        var g = document.getElementById('gap');
        if (g) { g.value = v; g.dispatchEvent(new Event('change', {bubbles: true})); }
        return;
      }
      if (key === 'bk_stopbnd') {
        var b = document.getElementById('stopbnd');
        if (b && (b.classList.contains('on') !== (v === '1'))) b.click();
      }
    } catch (e) {}
  }

  /* ---- hearing every write ---- */
  function listen() {
    try {
      var was = localStorage.setItem.bind(localStorage);
      localStorage.setItem = function (k, v) {
        was(k, v);
        try { changed(String(k), String(v)); } catch (e) {}
      };
    } catch (e) { /* a browser that will not have it: the sweep below */ }
    // another tab, and a browser whose setItem stayed its own
    window.addEventListener('storage', function (e) {
      if (!e.key) return;
      if (KEYS.indexOf(e.key) >= 0 || (here && e.key === here.key)) changed(e.key, e.newValue || '');
    });
    document.addEventListener('visibilitychange', function () {
      if (document.visibilityState === 'visible') sweep();
    });
    window.addEventListener('pagehide', send);
  }
  var last = {};
  function sweep() {
    KEYS.concat(here ? [here.key] : []).forEach(function (k) {
      var v = get(k);
      if (last[k] === undefined) { last[k] = v; return; }
      if (last[k] !== v) { last[k] = v; changed(k, v || ''); }
    });
  }

  function start() {
    if (location.protocol === 'file:') return;
    // a reader keeps its place under its own address (lib/tex2html.py, MINE)
    if (/^\/books\/(?:[^\/]+\/){1,2}reader\/(?:index\.html)?$/.test(location.pathname))
      here = {key: 'bk_pos:' + location.pathname};
    KEYS.concat(here ? [here.key] : []).forEach(function (k) { last[k] = get(k); });
    listen();
    fetch('/__prefs', {headers: {'Accept': 'application/json'}})
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (j) { if (j && j.ok) apply(j); else ready = true; })
      .catch(function () { ready = true; });
  }

  window.ParsehPrefs = {keys: KEYS, device: device, send: send, ask: ask};
  if (document.readyState === 'loading')
    document.addEventListener('DOMContentLoaded', start);
  else start();
})();

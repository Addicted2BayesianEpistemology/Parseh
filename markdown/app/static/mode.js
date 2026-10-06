// SPDX-License-Identifier: GPL-3.0-or-later
/* The Browser | Mobile switch, for the studio's library and its documents
   (docs/mobile.md, TO-DO §4.3).

   The deck pages carry the same thing inside decks.js; these two pages load
   app.js, which is the editor and everything else, so the few lines a page
   needs to KNOW WHICH LAYOUT IT IS IN live here on their own and are loaded
   by a tag of their own.  What it does:

     - reads the mode as every page of the toolbox reads it (localStorage,
       then the cookie, then the browser interface), and puts it on
       <html data-mode> -- the head has done that already, before anything was
       painted (deckroutes.MODE_SCRIPT); this keeps it in step afterwards;
     - wires the switch (the library's bar has one; a document's is in the
       gear, which asks ParsehStudioMode.set below);
     - follows a switch made in another tab;
     - registers the service worker in the mobile mode, so that a phone can
       install the interface as an app from any of its pages (lib/sw.js);
     - puts the bar away as the page goes down and brings it back on the
       smallest move up, at every width in the mobile layout.

   THE THEME IS NOT HERE.  The ◐ on these pages, the colours of the sheet and
   what the computer says of them are app.js's (paintTheme, bindStudioLook),
   one function for every page of the studio; this file used to cycle the
   theme on its own and repaint <html> alone, which left the sheet as it was.

   Nothing here edits, and nothing here knows what a document is: that is
   app.js's, and the mobile layout simply does not show what it opens. */
(function () {
  'use strict';
  var KEY = 'parseh_mode';

  function get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function put(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  function now() {
    var m = get(KEY);
    if (m !== 'browser' && m !== 'mobile') {
      var c = /(?:^|;\s*)parseh_mode=(browser|mobile)(?:;|$)/.exec(document.cookie || '');
      m = c ? c[1] : 'browser';
    }
    return m;
  }
  function isMobile() { return document.documentElement.getAttribute('data-mode') === 'mobile'; }
  function apply() {
    var m = now();
    document.documentElement.setAttribute('data-mode', m);
    if (!new RegExp('(?:^|;\\s*)' + KEY + '=' + m + '(?:;|$)').test(document.cookie || ''))
      document.cookie = KEY + '=' + m + '; Path=/; SameSite=Lax; Max-Age=31536000';
    Array.prototype.forEach.call(document.querySelectorAll('[data-parseh-mode]'), function (b) {
      b.setAttribute('aria-pressed', String(b.dataset.parsehMode === m));
    });
    if (m === 'mobile') appRegister();
  }
  function set(m) {
    if (m !== 'browser' && m !== 'mobile') return;
    put(KEY, m);
    document.cookie = KEY + '=' + m + '; Path=/; SameSite=Lax; Max-Age=31536000';
    apply();
  }
  function appRegister() {
    if (!('serviceWorker' in navigator) || !window.isSecureContext) return;
    navigator.serviceWorker.register('/sw.js').catch(function () {});
  }
  /* the bar goes on the way down and comes back on the way up */
  function bindBarFollow() {
    var lastY = Math.max(0, window.scrollY), ticking = false, off = false;
    function set_(v) {
      if (v === off) return;
      off = v;
      document.body.classList.toggle('barhidden', v);
    }
    function read() {
      ticking = false;
      var y = Math.max(0, window.scrollY), d = y - lastY;
      if (Math.abs(d) < 4) return;
      lastY = y;
      set_(isMobile() && y > 56 && d > 0);
    }
    window.addEventListener('scroll', function () {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(read);
    }, {passive: true});
  }

  apply();
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('[data-parseh-mode]');
    if (b) set(b.dataset.parsehMode);
  });
  window.addEventListener('storage', function (e) {
    if (!e.key || e.key === KEY) apply();
  });
  window.addEventListener('pageshow', function (e) { if (e.persisted) apply(); });
  if (document.readyState === 'loading')
    document.addEventListener('DOMContentLoaded', bindBarFollow);
  else bindBarFollow();
  window.ParsehStudioMode = {get: now, set: set, isMobile: isMobile};
})();

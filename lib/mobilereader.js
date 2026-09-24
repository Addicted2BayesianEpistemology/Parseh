// SPDX-License-Identifier: GPL-3.0-or-later
/* Parseh — a book's reader in the mobile interface (docs/mobile.md).

   Loaded into EVERY book's reader by lib/parseh.js, from beside it: a reader
   is a page built for its book (lib/tex2html.py), and one built before the
   mobile interface existed has nothing of it in its own markup -- so the
   layer lives here, in lib/, and reaches every edition, however old,
   without a rebuild.  Its sheet is lib/mobile.css (html.m-reader), which
   parseh.js links too.

   THE READER AS A READER ONLY.  The page is the same in both modes: the
   text, the passes, the glosses and the gloss cloud, the narration in step,
   the contents, the notes, looking a word up.  What the mobile mode takes
   away is everything that writes the book, builds it or administers it:
   the sheet hides every such control and every sheet they open, and lays
   the header out for a thumb.  This script does the things a sheet cannot:
     - it adds the header's ⋯, which opens the rest of the controls under
       the first line, a group to a line, each group with a line saying what
       it is -- and a group this book offers nothing of has no line;
     - it adds the Browser | Mobile switch, into that last group;
     - it refuses the gestures that write while the mode is mobile: a
       modifier-click on a word (a card) and E (the chunk's editor).
   The narration's own controls -- ▶, ↺ and ↻, the speed, and how far a skip
   carries -- are lib/narrctl.js's, in both modes: on a phone they float at
   the foot of the screen (the dock), not in this header.
   And it marks the page as a mobile page, so parseh.js sends the reader's
   links (the shelf, the hub) to their mobile versions.

   Nothing here runs until the mode is mobile, and going back to the browser
   mode leaves the page exactly as the reader built it: the sheet's rules are
   all mobile-mode rules, the added controls are data-layout="mobile", and
   no control of the reader's own is moved, copied or rewritten. */
(function () {
  'use strict';
  if (window.ParsehMobileReader) return;
  window.ParsehMobileReader = {};

  var P = function () { return window.Parseh; };
  function mobile() { var p = P(); return !!(p && p.mode && p.mode.isMobile()); }
  function header() { return document.querySelector('header'); }

  /* ---- the groups under ⋯ ----
     Each is a line saying what it is and the reader's own controls that
     belong to it; the sheet places them (order) and draws the line.  The
     selectors name the reader's controls, whichever of them this book has. */
  var GROUPS = [
    {g: 'passes', words: 'Passes',
     sel: '.pgrp, [data-toggle=nogloss], #hovermode'},
    {g: 'listening', words: 'Listening',
     sel: '#cont, #loop, #gapwrap, #stopbnd, .m-rskip, #listen, #listenfollow, #listenscroll, #seekwrap, #pos, #warn'},
    {g: 'looking', words: 'Looking a word up',
     sel: '#dictmode, #defmode, #defmt'},
    {g: 'page', words: 'This page',
     sel: '#theme, #bars, .parseh-mode, .kp-btn'}
  ];

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined) e.textContent = text;
    return e;
  }

  var built = false, more = null;
  function build() {
    if (built) return;
    var h = header();
    var row = h && h.querySelector('.hrow');
    if (!row) return;
    built = true;
    more = el('button', 'm-rmore', '⋯');
    more.type = 'button';
    more.setAttribute('data-layout', 'mobile');
    more.setAttribute('aria-expanded', 'false');
    more.setAttribute('aria-label', 'more: the passes, the listening, looking a word up, the page');
    more.title = 'the passes, the listening, looking a word up, the theme';
    more.addEventListener('click', function () { setMore(!h.classList.contains('m-more')); });
    row.appendChild(more);
    GROUPS.forEach(function (grp) {
      var lab = el('span', 'm-rlab', grp.words);
      lab.setAttribute('data-layout', 'mobile');
      lab.setAttribute('data-g', grp.g);
      row.appendChild(lab);
    });
    // the switch, as the hub's (lib/mobile.py writes the same two buttons);
    // parseh.js wires every [data-parseh-mode] on the page and keeps its
    // aria-pressed, and the pressed half is drawn from <html data-mode>
    var sw = el('span', 'parseh-mode');
    sw.setAttribute('role', 'group');
    sw.setAttribute('aria-label', 'interface');
    sw.setAttribute('data-layout', 'mobile');
    [['browser', 'Browser', 'the browser interface: every page, with everything that edits'],
     ['mobile', 'Mobile', 'the mobile interface: pages made for a phone, to read and to study, ' +
                          'with nothing on them that edits']].forEach(function (m) {
      var b = el('button', '', m[1]);
      b.type = 'button';
      b.setAttribute('data-parseh-mode', m[0]);
      b.setAttribute('aria-pressed', String(m[0] === 'mobile' && mobile()));
      b.title = m[2];
      sw.appendChild(b);
    });
    row.appendChild(sw);
    // a control of a group coming or going (the loop's gap, the listening's
    // seek, a dictionary switched on) may empty a group or fill it again
    if (window.MutationObserver) {
      var watch = new MutationObserver(tidy);
      GROUPS.forEach(function (grp) {
        Array.prototype.forEach.call(h.querySelectorAll(grp.sel), function (c) {
          watch.observe(c, {attributes: true, attributeFilter: ['hidden', 'style', 'class', 'disabled']});
        });
      });
      watch.observe(document.body, {attributes: true, attributeFilter: ['class']});
    }
  }

  /* ⋯ open or shut.  Not remembered: a page opens on its text, with the
     controls one tap away, never with half the screen taken by them. */
  function setMore(on) {
    var h = header();
    if (!h || !more) return;
    h.classList.toggle('m-more', on);
    more.setAttribute('aria-expanded', String(on));
    // while the controls are open the header stays where it is: the page
    // scrolled under a finger reaching for one must not take them away
    hold('more', on);
    tidy();
  }

  /* The header, held where it is: parseh.js (bars()) leaves it alone while
     <body data-bars-held> is said.  ⋯ open holds it -- the page scrolled
     under a finger reaching for one of the controls must not take them away
     -- and it goes free when ⋯ shuts.  The recording's own buttons no longer
     need it: they float at the foot and stay wherever the page goes. */
  var holds = {};
  function hold(why, on) {
    if (on) holds[why] = true; else delete holds[why];
    if (Object.keys(holds).length) document.body.setAttribute('data-bars-held', '');
    else document.body.removeAttribute('data-bars-held');
  }

  /* A group none of whose controls is drawn -- a book with no narration has
     no listening, a language with no dictionary installed nothing to look
     up -- has no line.  Asked of the drawn boxes, with ⋯ open, since that is
     the only time the lines are on the screen. */
  function tidy() {
    var h = header();
    if (!h || !h.classList.contains('m-more')) return;
    GROUPS.forEach(function (grp) {
      var lab = h.querySelector('.m-rlab[data-g="' + grp.g + '"]');
      if (!lab) return;
      var any = Array.prototype.some.call(h.querySelectorAll(grp.sel), function (c) {
        return c.getClientRects().length > 0;
      });
      lab.classList.toggle('m-empty-g', !any);
    });
  }

  /* ---- the writing gestures, refused ----
     Capture, on the window, so they are stopped before the reader's own
     listeners -- which sit on the document -- ever hear them.  A plain
     click and a shift-click (a copy: reading, not writing) pass untouched,
     and so does every key typed into a field. */
  function isField(t) {
    return !!(t && t.closest && t.closest('input, textarea, select, [contenteditable]'));
  }
  window.addEventListener('click', function (e) {
    if (!mobile() || !(e.altKey || e.ctrlKey || e.metaKey)) return;
    var t = e.target;
    if (!t || !t.closest || t.closest('a[href], header, #tocwrap, .parseh-typo')) return;
    // a modifier-click on a word is a card (lib/tex2html.py): there is no
    // card to make on a phone
    if (!t.closest('.wd, .w, .row, .sub, [data-c]')) return;
    e.preventDefault();
    e.stopImmediatePropagation();
  }, true);
  window.addEventListener('keydown', function (e) {
    if (!mobile() || e.altKey || e.ctrlKey || e.metaKey || isField(e.target)) return;
    // E writes the chunk under the cloud or the pencil (lib/tex2html.py)
    if (e.key === 'e' || e.key === 'E') e.stopImmediatePropagation();
  }, true);

  /* ---- the mode ---- */
  function onMode(m) {
    if (m === 'mobile') { build(); tidy(); }
    // the browser header has no ⋯ to hold the bar for
    else if (more) setMore(false);
  }
  function start() {
    // a mobile page: in the mobile mode parseh.js routes its links (the
    // shelf's ▤ to /m/books/), and in the browser mode it routes nothing
    document.body.setAttribute('data-mobile-page', '');
    var p = P();
    if (p && p.mode && p.mode.onChange) p.mode.onChange(onMode);
    if (mobile()) onMode('mobile');
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})();

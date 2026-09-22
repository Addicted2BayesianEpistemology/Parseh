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
     - on a narrated book, it adds ↺ and ↻ either side of ▶: the recording
       back and on by so many seconds (ten, until the Listening group's
       "skip by" says otherwise, which every book keeps as `bk_skip`);
     - it refuses the gestures that write while the mode is mobile: a
       modifier-click on a word (a card) and E (the chunk's editor).
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
     sel: '#cont, #loop, #gapwrap, #stopbnd, #speed, #listen, #listenfollow, #listenscroll, #seekwrap, #pos, #warn'},
    {g: 'looking', words: 'Looking a word up',
     sel: '#dictmode, #defmode, #defmt'},
    {g: 'page', words: 'This page',
     sel: '#theme, #bars, .parseh-mode, #draftmark'}
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
    // the speed is a <select> that says "1": on a phone it says what it is
    if (document.getElementById('speed')) {
      var says = el('label', 'm-rnote', 'speed');
      says.htmlFor = 'speed';
      says.setAttribute('data-layout', 'mobile');
      row.appendChild(says);
    }
    buildSkips(row);
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
     <body data-bars-held> is said.  Two things hold it -- ⋯ open, and the
     scroll a skip makes to the new reading place, which would otherwise
     take ↺ and ↻ away from under the thumb that pressed them, before a
     second press -- and it goes free when neither does. */
  var holds = {};
  function hold(why, on) {
    if (on) holds[why] = true; else delete holds[why];
    if (Object.keys(holds).length) document.body.setAttribute('data-bars-held', '');
    else document.body.removeAttribute('data-bars-held');
  }
  var skipHeld = 0;
  function holdForSkip() {
    hold('skip', true);
    clearTimeout(skipHeld);
    // the reader's scroll is a smooth one: well over by then
    skipHeld = setTimeout(function () { hold('skip', false); }, 1200);
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

  /* ---- the recording, back and on by so many seconds ----
     ↺ and ↻, either side of ▶ (the sheet places them: on the first line
     where it is wide enough, a landscape phone's, and on a line of their
     own with ▶ under it on a phone held upright).  How far they move is
     one number for every book, kept beside the reader's own habits (the
     gap, the rate) as `bk_skip`; the Listening group has the field that
     sets it.  A book with no narration has neither: the reader's
     body.noaudio, which hides ▶, hides them too (the sheet). */
  var SKIP_KEY = 'bk_skip', SKIP_DEF = 10, SKIP_MAX = 600;
  function skipSecs() {
    var v = NaN;
    try { v = parseInt(localStorage.getItem(SKIP_KEY), 10); } catch (e) {}
    return v >= 1 && v <= SKIP_MAX ? v : SKIP_DEF;
  }
  var skipBack = null, skipOn = null, skipField = null;
  function skipSay() {
    var n = skipSecs();
    if (skipBack) {
      skipBack.textContent = '↺ ' + n;
      skipBack.setAttribute('aria-label', 'back ' + n + ' seconds');
      skipBack.title = 'the recording back ' + n + ' seconds';
    }
    if (skipOn) {
      skipOn.textContent = n + ' ↻';
      skipOn.setAttribute('aria-label', 'on ' + n + ' seconds');
      skipOn.title = 'the recording on ' + n + ' seconds';
    }
    if (skipField && document.activeElement !== skipField) skipField.value = String(n);
  }
  function buildSkips(row) {
    if (!document.getElementById('play') || !document.getElementById('audio')) return;
    // on a phone held upright ▶ and the two go under the first line: this
    // is where that line ends (the sheet draws it only there)
    var br = el('span', 'm-rbreak');
    br.setAttribute('data-layout', 'mobile');
    br.setAttribute('aria-hidden', 'true');
    row.appendChild(br);
    skipBack = el('button', 'm-skip');
    skipOn = el('button', 'm-skip');
    [[skipBack, -1], [skipOn, 1]].forEach(function (b) {
      b[0].type = 'button';
      b[0].setAttribute('data-layout', 'mobile');
      b[0].setAttribute('data-skip', String(b[1]));
      b[0].addEventListener('click', function () { holdForSkip(); skipBy(b[1] * skipSecs()); });
      row.appendChild(b[0]);
    });
    // "skip by 10 seconds", in the Listening group: a field, since any
    // number will do -- a phone brings up its keypad of figures for it
    var set = el('label', 'm-rskip');
    set.setAttribute('data-layout', 'mobile');
    set.appendChild(document.createTextNode('skip by '));
    skipField = el('input');
    skipField.type = 'number';
    skipField.min = '1';
    skipField.max = String(SKIP_MAX);
    skipField.step = '1';
    skipField.inputMode = 'numeric';
    skipField.id = 'm-skipby';
    skipField.setAttribute('aria-label', 'how many seconds ↺ and ↻ move the recording');
    skipField.title = 'how many seconds ↺ and ↻ move the recording: every book, on this browser';
    skipField.addEventListener('change', function () {
      var v = Math.round(+skipField.value);
      // nothing, or nothing sensible, typed: the number it was
      if (!(v >= 1)) v = skipSecs();
      v = Math.min(SKIP_MAX, v);
      try { localStorage.setItem(SKIP_KEY, String(v)); } catch (e) {}
      skipField.value = String(v);
      skipSay();
    });
    skipField.addEventListener('blur', skipSay);
    set.appendChild(skipField);
    set.appendChild(document.createTextNode(' seconds'));
    row.appendChild(set);
    skipSay();
    // another tab set it: these say the new number
    window.addEventListener('storage', function (e) { if (e.key === SKIP_KEY || e.key === null) skipSay(); });
  }

  /* The move itself.  The reader plays by SUBPARAGRAPH (lib/tex2html.py):
     the mark is on the one playing, and it stops at that one's end, where
     "continuous" takes it on.  So a jump into another subparagraph takes the
     reading place with it -- the mark, the place kept for next time, and
     where the playing stops -- or the next stop would fall at the end of
     the one it left.  Listening on its own has no reading place: there only
     the fold ahead is worked out again from where the recording now is.
     All of that is the reader's own state, the top-level bindings of its
     script, which every classic script of the page shares; a reader built
     before one of them existed has the recording moved and follows as it
     can.  Within the recording that is loaded, a book read from several
     files being one file at a time: from its start to its end. */
  function skipBy(secs) {
    var a = document.getElementById('audio');
    if (!a) return;
    var d = a.duration, to = Math.max(0, (a.currentTime || 0) + secs);
    if (d > 0 && isFinite(d)) to = Math.min(to, d - 0.05);
    try {
      // every name below but a, to and i is the reader's; each is read
      // before anything is written, so a reader that lacks one throws
      // before it is half moved
      if (listening) {
        void armListen;
        seekTo(to, function () {});
        if (!a.paused) armListen();
        return;
      }
      var i = subAtTime(to);
      void [waiting, atBound, previewing, cur, stopAt, hl, save, SUBS, seekTo];
      clearTimeout(waiting); waiting = null;
      // a wait at a change of chapter, or a preview's window: this is
      // where the playing is now
      atBound = null; previewing = false;
      if (i >= 0 && i !== cur) { cur = i; hl(i, true); save(); }
      if (!a.paused && i >= 0) stopAt = SUBS[i][1];
      seekTo(to, function () {});
      return;
    } catch (e) { /* a reader older than one of the above */ }
    a.currentTime = to;
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

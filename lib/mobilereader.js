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

  /* ---- the dictionary, on a phone (the owner, 2026-09-24; TO-DO §4.18) ----
     The reader's cloud opens the dictionary's panel by itself only for a
     chunk nobody has glossed, and only with the header's switch on; a
     reader on a phone may want the dictionary's senses of a chunk that HAS
     a gloss too, and the switch is under ⋯.  So beside "copy" the cloud
     gets a button for it.  And an entry read INSIDE the cloud -- a small box
     scrolling inside a scrolling page, over the word it is about -- was, in
     the owner's words, "basically unusable" on a phone: so what the button
     opens is the dictionary's SHEET (Parseh.dictSheet, lib/parseh.js), and
     a tap on a chunk with no gloss at all, with the switch on, opens the
     sheet straight away, with no cloud.  THE CLOUD STAYS FOR THE GLOSSES: a
     glossed chunk nobody asks the dictionary about opens its cloud exactly
     as it always did.

     WHAT A GLOSS IS, HERE (the owner, 2026-09-25): ANY line of one -- a
     meaning, a transliteration (a reading, in a language that has one) or
     a vocabulary line.  The reader's own rule is the vocabulary line alone
     (fillCloud pours the dictionary's panel into the cloud of any chunk
     without one), and on a phone that sent a chunk with a meaning written
     under it straight to the sheet, its meaning lost at the top of a long
     entry.  So a chunk with any line opens its cloud, the dictionary one
     press away, as a chunk with a vocabulary line does -- the panel the
     reader poured in taken out again -- and only a chunk with nothing
     written opens the sheet by itself.  One rule for the press and for the
     count of a book with few glosses (below): hasGloss.

     The cloud is the READER'S, drawn by the script its build wrote
     (lib/tex2html.py, fillCloud), so the button is added here each time
     the cloud is filled, and the entry is drawn by that same script's own
     dictInto -- every reader built since the dictionary existed has it, as
     globals of its classic script; one built before has no dictionary to
     open, and gets no button.

     THE CLOUD IS HIDDEN WHILE THE SHEET IS UP, AND NOT CLOSED.  The reader's
     dictInto puts its answer in the box only while its cloud is still open
     on that chunk (cloudC), and closing the cloud forgets the chunk: closed,
     the sheet would wait for ever on "looking it up…".  Hidden, the chunk is
     remembered, the word keeps its mark, and the page's "a click outside
     closes the cloud" -- which asks whether the cloud is showing -- leaves
     it alone.  When the sheet goes, the cloud goes with it: nothing is left
     open (the owner's 4). */
  function readerHas() {
    try {
      return typeof dictInto === 'function' && typeof chunkData === 'function' &&
             typeof DICT === 'object' && typeof cloudC === 'number';
    } catch (e) { return false; }
  }
  // what the reader's own fillCloud asks before it pours an entry into the
  // cloud of a chunk nobody has glossed
  function autoPanel() {
    try { return !!((DICT.ready || (typeof MT === 'object' && MT.ready)) && DICT.on); }
    catch (e) { return false; }
  }
  /* WHETHER A CHUNK HAS A GLOSS: any line of one, as the .tex holds it --
     the reader's SRC, one entry per chunk of the whole book in data-c order,
     [colour, text, kana, tr, voc, en, words] (lib/tex2html.py; every reader
     since a0.2.0 carries it).  The kana counts where the language has a
     reading, as the transliteration always does.  But a reading a draft
     SEEDED from the chunk's word line -- the kana where there is one, the
     transliteration where not -- with nothing else written, is nobody's
     gloss: lib/draft.py proposes it, the reader marks such a row data-seed,
     and the video's player asks the same seed (hasGloss there);
     ParsehWordline, which the reader loads, works it out as they do. */
  function srcAll() {
    try { return typeof SRC === 'object' && SRC && SRC.length ? SRC : null; } catch (e) { return null; }
  }
  function srcGlossed(s) {
    if (!s) return false;
    var L = null;
    try { L = typeof LANG === 'object' ? LANG : null; } catch (e) {}
    var kana = !!(L && L.reading);
    var line = function (k) { return String(s[k] || '').trim(); };
    if (line(4) || line(5) || (kana && line(3))) return true;
    // what is left is the reading alone: the chunk's own, unless it is still
    // exactly what the draft seeded it with
    var field = kana ? 'kana' : 'tr', v = line(kana ? 2 : 3), sd = null;
    if (!v) return false;
    try {
      var W = window.ParsehWordline;
      if (W && W.seed && L) sd = W.seed({words: String(s[6] || '')}, L);
    } catch (e) {}
    return !(sd && sd[0] === field && sd[1] && v === sd[1]);
  }
  // a reader with no SRC: the row's own gloss lines are all it can say
  function rowGlossed(r) {
    if (!r || r.hasAttribute('data-seed')) return false;
    return Array.prototype.some.call(r.querySelectorAll('.gl .kana, .gl .tr, .gl .voc, .gl .en'), function (g) {
      return !!g.textContent.trim();
    });
  }
  function hasGloss(n) {
    var src = srcAll();
    if (src) return srcGlossed(src[n]);
    return rowGlossed(document.querySelector('.pass.p2 .row[data-c="' + n + '"]'));
  }
  /* A TAP OPENS THE SHEET, A MOUSE AT REST DOES NOT.  A modal sheet must not
     spring up because a mouse wandered over a chunk (a desktop in the mobile
     mode, hover mode on): only a cloud opened by a click or a tap turns into
     the sheet.  Heard first of all, on the window, before the reader's own
     listeners on the document open the cloud. */
  var tapping = false;
  window.addEventListener('click', function () {
    tapping = true;
    setTimeout(function () { tapping = false; }, 0);
  }, true);
  function addDict() {
    var cloud = document.getElementById('cloud');
    var row = cloud && cloud.querySelector('.mkrow');
    if (!mobile() || !row || !readerHas()) return;
    /* THE CLOUD FILLED AGAIN UNDER THE SHEET.  The reader opens its cloud
       again, on the same chunk, when something arrives that the cloud would
       show -- the translation model, found a moment after the page loaded
       (two fetches, slow over a tunnel), is the usual one -- and placing it
       shows it.  Shown, the page's "a click outside closes the cloud" is
       live again, and the next tap in the sheet closed it: the chunk
       forgotten, and the answer the sheet was waiting for thrown away.  So
       while the sheet is up for this chunk, its cloud stays hidden. */
    if (sheet && sheet.open() && cloudC === sheetN) { cloud.hidden = true; return; }
    // the entry the reader has just poured into the cloud of a chunk with no
    // vocabulary line.  A chunk with nothing written at all: into the sheet
    // it goes, the very box -- its answer is on its way into it -- and the
    // cloud is not shown.  A chunk with a meaning or a reading written under
    // it has a gloss (WHAT A GLOSS IS, above): the panel comes out again,
    // and the cloud is the gloss, with the dictionary a press away beside
    // "copy" -- the reader's lookup, already asked, lands in the cache for
    // that press
    var auto = cloud.querySelector('.dict:not(.m-dict)');
    if (auto) {
      if (!hasGloss(cloudC)) {
        if (tapping && autoPanel()) toSheet(auto);
        return;
      }
      auto.remove();
    }
    if (row.querySelector('.mkdict')) return;
    var b = el('button', 'mkdict', 'dictionary');
    b.type = 'button';
    b.setAttribute('data-layout', 'mobile');
    b.setAttribute('aria-expanded', 'false');
    b.title = 'what the dictionary says of these words, in a sheet over the foot of the screen';
    var copy = row.querySelector('.mkcopy');
    row.insertBefore(b, copy ? copy.nextSibling : null);
    // The reader placed its cloud before the button was in it, at the size
    // it had then: near the edge of the screen the button went to a line of
    // its own, and the cloud, grown by it, came down over the very word it
    // glosses.  So the reader places it again, by its own rules, as it does
    // whenever something lands in it.
    if (typeof refitCloud === 'function') refitCloud(b);
  }
  /* THE NARRATION WAITS WHILE THE SHEET IS UP, as a video does: the dock
     that could pause it is under the dimmed page, and a narration going on
     -- the page following it -- scrolls the word the sheet is about away
     from above the sheet.  Paused, and started again when the sheet goes,
     through the reader's own ▶, the very button the dock presses, so the
     loop, a chapter's start and the reading place stay the reader's own
     business; and started again only when it is the sheet that paused it. */
  function narrHold() {
    var a = document.querySelector('audio'), b = document.getElementById('play');
    if (!a || !b || a.paused) return false;
    b.click();
    return a.paused;
  }
  function narrGoOn() {
    var a = document.querySelector('audio'), b = document.getElementById('play');
    if (a && b && a.paused) b.click();
  }
  var sheet = null, sheetN = -1;       // the sheet up, and the chunk it is for
  function toSheet(box) {
    var cloud = document.getElementById('cloud'), p = P();
    if (!cloud || !p || !p.dictSheet) return;
    var n = cloudC, at = null, lang = {code: '', dir: 'ltr'}, d = chunkData(n);
    try { at = cloudFor; } catch (e) {}
    try { lang = {code: LANG.code, dir: LANG.dir}; } catch (e) {}
    // the gloss the cloud was showing, over the entry
    var carry = Array.prototype.filter.call(cloud.children, function (c) {
      return c.matches('.kana, .tr, .voc, .en');
    });
    cloud.hidden = true;
    var held = narrHold();
    sheetN = n;
    sheet = p.dictSheet({box: box, lang: lang, title: d ? d.fa : '', anchor: at, carry: carry,
                         onClose: function (how) {
                           if (cloudC === n && typeof closeCloud === 'function') closeCloud();
                           // (a sheet opened over this one keeps it waiting)
                           if (held && how !== 'again') narrGoOn();
                         }});
  }
  function openDict(b) {
    var cloud = document.getElementById('cloud');
    if (!cloud || !readerHas()) return;
    var n = cloudC;
    if (!(n >= 0)) return;
    var box = el('div', 'dict m-dict');
    b.setAttribute('aria-expanded', 'true');
    toSheet(box);
    var ready = false;
    try { ready = !!(DICT.ready || (typeof MT === 'object' && MT.ready)); } catch (e) {}
    if (ready) {
      var d = chunkData(n);
      dictInto(box, n, d ? d.fa : '');
    } else {
      // nothing to look it up with: said -- in the book's language's name,
      // as a video's cloud says it -- with the way to set one up
      var name = '';
      try { name = (typeof LANG === 'object' && LANG && LANG.name) || ''; } catch (e) {}
      var none = el('div', 'dnone', 'Nothing is set up to look ' + (name ? name : 'these') +
                    ' words up: a dictionary, a corpus of translated sentences or a model. ');
      var to = el('a', '', 'Set any of them up');
      to.href = '/settings/reading-help/';
      none.appendChild(to);
      none.appendChild(document.createTextNode(' — it takes a couple of minutes.'));
      box.appendChild(none);
    }
  }
  var dictWatch = null;
  function watchCloud() {
    var cloud = document.getElementById('cloud');
    if (dictWatch || !cloud || !window.MutationObserver) return;
    // filled all at once (textContent emptied, then every line appended):
    // the observer hears it as one batch, after the fill is over
    dictWatch = new MutationObserver(addDict);
    dictWatch.observe(cloud, {childList: true});
    cloud.addEventListener('click', function (e) {
      var b = e.target && e.target.closest ? e.target.closest('.mkdict') : null;
      if (b && cloud.contains(b)) openDict(b);
    });
  }

  /* ---- a book with few glosses (the owner, 2026-09-24) ----
     Fewer than half of its chunks with a gloss -- any line of one
     (hasGloss, above: the owner, 2026-09-25) -- and a press on a chunk does
     one of two different things -- the gloss beside it, or the dictionary's
     sheet -- with nothing to say which.  So in such a book, on a phone,
     every chunk that has one is marked (m-gl, in every pass it is drawn in)
     and the page says the book is sparse (m-sparse): lib/mobile.css draws
     the mark.  A book glossed half or more is left exactly as it was, and
     so is the browser mode.

     COUNTED OVER THE WHOLE BOOK, AND MARKED AS EACH CHAPTER ARRIVES.  A book
     of more than one chapter is sent with its first chapter only; the others
     come when they are wanted (lib/tex2html.py, one_chapter_at_a_time).
     Counted on the page, a book glossed from the front -- which is how books
     get glossed -- was judged by its first chapter and never marked, and in
     a book judged sparse a chapter that came later had no mark at all.  So
     the count is the reader's SRC, the whole book's chunks as the .tex holds
     them (every reader since a0.2.0 has it); and whatever chapter comes in
     later is marked as it comes (watchChapters). */
  var glossed = {};                    // the book's glossed chunks, by data-c
  function countGlossed() {
    var g = {}, count = 0, total = 0;
    var src = srcAll();
    if (src) {
      total = src.length;
      for (var i = 0; i < src.length; i++)
        if (srcGlossed(src[i])) { g[i] = 1; count++; }
    } else {
      // a reader with no SRC: the chunks on the page are all it can say
      var rows = document.querySelectorAll('.pass.p2 .row[data-c]');
      total = rows.length;
      Array.prototype.forEach.call(rows, function (r) {
        if (rowGlossed(r)) { g[r.getAttribute('data-c')] = 1; count++; }
      });
    }
    return {glossed: g, sparse: total > 0 && count * 2 < total};
  }
  function markIn(scope) {
    Array.prototype.forEach.call(scope.querySelectorAll('.pass [data-c]'), function (e) {
      if (glossed[e.getAttribute('data-c')]) e.classList.add('m-gl');
    });
  }
  function markGlossed() {
    var root = document.documentElement, on = mobile();
    var got = on ? countGlossed() : {glossed: {}, sparse: false};
    glossed = got.glossed;
    if (root.classList.contains('m-sparse') !== got.sparse) root.classList.toggle('m-sparse', got.sparse);
    Array.prototype.forEach.call(document.querySelectorAll('.m-gl'), function (e) {
      e.classList.remove('m-gl');
    });
    if (got.sparse) markIn(document);
  }
  // a chapter filled in (the reader's fillChapter puts its markup in and
  // takes the section's data-part away): marked before it is drawn
  var chapWatch = null;
  function watchChapters() {
    var main = document.querySelector('main');
    if (chapWatch || !main || !window.MutationObserver ||
        !main.querySelector('section.chapter[data-part]')) return;
    chapWatch = new MutationObserver(function (ms) {
      if (!document.documentElement.classList.contains('m-sparse')) return;
      ms.forEach(function (m) {
        var t = m.target;
        if (t.nodeType === 1 && t.matches('section.chapter') && !t.hasAttribute('data-part')) markIn(t);
      });
    });
    chapWatch.observe(main, {attributes: true, attributeFilter: ['data-part'], subtree: true});
  }

  /* ---- the mode ---- */
  function onMode(m) {
    if (m === 'mobile') { build(); tidy(); watchCloud(); addDict(); markGlossed(); watchChapters(); return; }
    // the browser header has no ⋯ to hold the bar for
    if (more) setMore(false);
    markGlossed();
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

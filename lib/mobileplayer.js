// SPDX-License-Identifier: GPL-3.0-or-later
/* Parseh — a video's page in the mobile interface (docs/mobile.md, §4.2).

   The video player is a page the server writes for its video
   (youtube/lib/ytpages.py from player.html), and this is its mobile layer,
   loaded by lib/parseh.js the way a book reader's is: the sheet is
   lib/mobile.css (html.m-player), and this script does what a sheet cannot.

   THE PAGE IS THE SAME PAGE: the video, the transcript, the glosses and the
   cloud, looking a word up, the notes.  What the mobile mode takes away is
   everything that writes the video or administers it -- its details, the
   caption timings, the download, the dictionary setup, stop -- and what it
   adds is a header a thumb can use:
     - ⋯ opens the rest of the controls under the first line, a group to a
       line, each group with a line saying what it is (as the reader's does);
     - the Browser | Mobile switch, in the last group;
     - the recording's controls float at the foot of the screen: ↺, ⏯ and ↻
       with the speed chip -- lib/narrctl.js, which drives the video through
       the handle the player hands out (window.ParsehPlayer);
     - HELD SIDEWAYS the video goes to the left and the transcript to the
       right, with the divider between them draggable (the player's own #grip,
       which takes a finger as well as a mouse), and a ⛶ button puts the video
       on the whole screen with the playing line over it as subtitles -- which
       answer a tap with the gloss cloud, exactly as the transcript does (the
       owner's choices, 2026-09-22, the whole screen rebuilt 2026-09-23).
   A card is not made here and a chunk is not edited: those gestures are
   refused while the mode is mobile, as they are in a book. */
(function () {
  'use strict';
  if (window.ParsehMobilePlayer) return;
  window.ParsehMobilePlayer = {};

  var P = function () { return window.Parseh; };
  function mobile() { var p = P(); return !!(p && p.mode && p.mode.isMobile()); }
  function header() { return document.querySelector('header'); }
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined) e.textContent = text;
    return e;
  }
  function sideways() {
    try { return window.matchMedia('(orientation: landscape) and (min-width: 600px)').matches; }
    catch (e) { return false; }
  }

  /* ---- the groups under ⋯ ----
     The reader's device, with this page's own controls: what follows the
     video, what is looked up, and the page itself. */
  var GROUPS = [
    {g: 'following', words: 'Following the video',
     sel: '#follow, #hoverpause, #aloud, #pin'},
    {g: 'looking', words: 'Looking a word up',
     sel: '#dictmode, #defmode, #defmt'},
    {g: 'page', words: 'This page',
     sel: '#theme, #typo, .parseh-mode, .kp-btn'}
  ];

  var built = false, more = null, full = null;
  function build() {
    if (built) return;
    // the reader's header holds its controls in rows (.hrow); the player's
    // holds them itself
    var h = header(), row = h && (h.querySelector('.hrow') || h);
    if (!row) return;
    built = true;
    more = el('button', 'm-rmore', '⋯');
    more.type = 'button';
    more.setAttribute('data-layout', 'mobile');
    more.setAttribute('aria-expanded', 'false');
    more.setAttribute('aria-label', 'more: following the video, looking a word up, the page');
    more.title = 'following the video, looking a word up, the theme';
    more.addEventListener('click', function () { setMore(!h.classList.contains('m-more')); });
    row.appendChild(more);
    GROUPS.forEach(function (grp) {
      var lab = el('span', 'm-rlab', grp.words);
      lab.setAttribute('data-layout', 'mobile');
      lab.setAttribute('data-g', grp.g);
      row.appendChild(lab);
    });
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
    buildFull(row);
  }

  function setMore(on) {
    var h = header();
    if (!h || !more) return;
    h.classList.toggle('m-more', on);
    more.setAttribute('aria-expanded', String(on));
    if (on) document.body.setAttribute('data-bars-held', '');
    else document.body.removeAttribute('data-bars-held');
  }

  /* ---- the whole screen, with the playing line over the video ----
     Sideways only (the owner's choice): upright a video on the whole screen
     is a strip of picture with nothing to read.

     THE FULL-SCREEN ELEMENT IS THE PAGE, AND PARSEH LAYS THE VIDEO OUT ITSELF.
     ⛶ used to ask the browser to enlarge #playerwrap, and that box holds
     YouTube's own cross-origin iframe: on Android the iframe takes the top
     layer, nothing of Parseh's is drawn over it, and the viewer was left with
     no subtitles and a bar saying how to get out that would not go away (the
     owner, on a real phone, 2026-09-23).  So the whole PAGE goes full screen
     -- document.documentElement -- and the layout over it is this toolbox's
     own (html.m-vfullon in lib/mobile.css): #playerwrap pinned over the page,
     the video centred on black, the line being said lying over its foot, and
     the dock still where the thumb left it.  Where a phone refuses the
     request, the pinned layout is all there is, which is the same picture
     with the browser's own bars still showing -- and the refusal is SAID, not
     swallowed, since a button that does nothing and explains nothing is the
     whole of what was wrong.

     THREE WAYS OUT, because nobody may be trapped inside a video: the ⛶ in
     the corner (which fades with the dock and comes back at a touch), the
     phone's back gesture (an entry is pushed on the way in, and popstate is
     the way out), and a tap on the black beside the picture. */
  var on = false, out = null, pushed = false;
  function buildFull(row) {
    full = el('button', 'm-vfull', '⛶');
    full.type = 'button';
    full.setAttribute('data-layout', 'mobile');
    full.setAttribute('aria-pressed', 'false');
    full.setAttribute('aria-label', 'the video on the whole screen, with the line being said over it');
    full.title = 'the whole screen: the video, with the line being said over it';
    full.addEventListener('click', function () { setFull(!on); });
    row.appendChild(full);
    document.addEventListener('fullscreenchange', onFullChange);
    window.addEventListener('popstate', onPop);
    var box = document.getElementById('playerwrap');
    if (box) box.addEventListener('click', function (e) {
      // the black beside the picture is the box itself: the video swallows
      // its own taps, and the subtitles answer theirs below
      if (on && e.target === box) setFull(false);
    });
  }

  /* ASKING THE BROWSER FOR THE SCREEN, AND WHEN NOT TO BOTHER (the owner's
     1 of 2026-09-23: "a black cloud appears at the bottom explaining how to
     exit full screen, that doesn't vanish unless one swipes on it").

     THAT CLOUD IS NOT OURS.  Parseh has no words anywhere about leaving the
     whole screen except the corner button's own label, and none of the three
     black things this overlay draws -- the matte, the ⛶, the subtitle pill
     -- says anything of the kind.  It is Android Chrome's own notice about
     the Fullscreen API, drawn by the browser over the page, and nothing here
     can remove it or change a word of it.  It does not appear on an iPhone
     for the plainest reason: `Element.requestFullscreen` does not exist
     there, the call below throws, and no full screen is ever entered -- yet
     the picture is the same, because the layout is drawn by our own
     `m-vfullon` and not by the browser (lib/mobile.css, and it says so).

     WHICH IS THE WAY OUT OF IT.  If the whole screen is ALREADY ours --
     the app installed, where the manifest asks for `display: fullscreen`
     and the system bars are gone before any video is opened -- then asking
     the browser for it again buys nothing at all and costs that cloud.  So
     we do not ask.  Where it is worth asking, in a browser tab with an
     address bar to be rid of, the cloud comes with it and is the browser's
     to draw; there the video says once, briefly, what it is and how to be
     rid of it, because a notice you must SWIPE to dismiss is not a thing
     anybody guesses.  Said only where it happens: Android, and a screen we
     really did ask for. */
  function ownScreen() {
    try {
      return !!(window.matchMedia &&
                window.matchMedia('(display-mode: fullscreen)').matches);
    } catch (e) { return false; }
  }
  function android() { return /Android/i.test(navigator.userAgent || ''); }
  function askScreen() {
    // already the whole screen, and nothing to ask for: the app was
    // installed that way
    if (ownScreen()) return;
    var asked = null;
    try { asked = document.documentElement.requestFullscreen(); } catch (e) { return; }
    if (!asked || !asked.then) return;
    asked.then(function () {
      if (!android()) return;
      var p = P();
      if (p && p.toast)
        p.toast('Android has put its own notice at the foot of the screen — swipe it away. ' +
                'Parseh’s ⛶ in the corner, or the back gesture, leaves the video.');
    }).catch(function () {
      var p = P();
      if (p && p.toast)
        p.toast('this phone would not give the whole screen — the video is over the page instead');
    });
  }

  /* `theirs`: some other element of this page has just taken the whole screen
     for itself, so the overlay comes down but the screen is left where its
     new owner put it -- cancelling that would be answering a button nobody
     here drew. */
  function setFull(want, theirs) {
    if (want === on || !full) return;
    on = want;
    full.setAttribute('aria-pressed', String(on));
    // on <html>, beside the layer's other marks (m-player, data-mode): the
    // page itself is what the overlay takes over, and a rule on <html> is the
    // only one that can stop the page scrolling behind it
    document.documentElement.classList.toggle('m-vfullon', on);
    if (on) {
      outButton();
      subsOn();
      // the back gesture is the first thing a thumb reaches for, and it must
      // be a way out of the video and not a way off the page
      try { history.pushState({parsehVideoFull: 1}, ''); pushed = true; }
      catch (e) { pushed = false; }
      askScreen();
    } else {
      subsOff();
      if (out && out.parentNode) out.parentNode.removeChild(out);
      if (!theirs && document.fullscreenElement && document.exitFullscreen) {
        var left = document.exitFullscreen();
        if (left && left.catch) left.catch(function () {});
      }
      // the entry pushed on the way in, spent: a back gesture has already
      // spent it (onPop says so), and then there is nothing to go back to
      if (pushed) { pushed = false; try { history.back(); } catch (e) {} }
    }
  }
  function onPop() {
    if (!on) return;
    pushed = false;
    setFull(false);
  }
  /* ELEMENT-AWARE, because this page has more than one thing that can be put
     on the whole screen: a film of this machine carries its own controls, ⛶
     and all, and while THAT element is full screen nothing outside it is
     drawn -- the overlay would be there, invisible, with no way back to it.
     So any full screen that is not this page's own takes the overlay down,
     and every ending tidies up after whatever moved. */
  function onFullChange() {
    var e = document.fullscreenElement;
    if (!on) { homeCloud(); return; }
    // something else of this page owns the screen now: down, but not off
    if (e && e !== document.documentElement) { setFull(false, true); return; }
    // the browser's own way out -- Escape, the system gesture, the phone's
    // own button -- and the overlay goes with it
    if (!e) setFull(false);
  }
  /* The gloss cloud belongs to <body>: it is fixed to the window and drawn
     over everything the page has (z-index 80 in the player's sheet), so the
     overlay never needs to hold it.  An earlier layer DID move it into the
     video's box -- that box was the full-screen element, and nothing outside
     one is drawn -- and a page left in that state, by another element taking
     the screen or by a mode switched under it, would keep its cloud inside a
     box that is over nothing.  So wherever a full screen ends, it goes home. */
  function homeCloud() {
    var cloud = document.getElementById('cloud');
    if (cloud && cloud.parentNode !== document.body) document.body.appendChild(cloud);
  }
  /* the way out in the corner: ⛶ again, faint with the dock and whole at a
     touch (lib/narrctl.js keeps the page's one idle clock) */
  function outButton() {
    if (!out) {
      out = el('button', 'm-vout', '⛶');
      out.type = 'button';
      out.setAttribute('data-layout', 'mobile');
      out.setAttribute('aria-label', 'leave the whole screen');
      out.title = 'leave the whole screen — the back gesture and a tap beside the picture do it too';
      out.addEventListener('click', function (e) { e.stopPropagation(); setFull(false); });
    }
    var box = document.getElementById('playerwrap');
    if (box && out.parentNode !== box) box.appendChild(out);
    if (window.ParsehNarr && ParsehNarr.fade) ParsehNarr.fade(out);
  }

  /* ---- the subtitles ----
     The caption the page is following, copied over the video's foot.  A COPY
     CARRIES NO LISTENERS, and the transcript opens its gloss cloud from a
     listener hung on each phrase as it was drawn (youtube/lib/player.js): a
     tap on a copied phrase did nothing at all, so the one thing the whole
     screen was for had never been seen working (the owner, 2026-09-23).  So
     the copy says which caption and which phrase it is, and the player opens
     its own cloud ANCHORED TO THE COPY -- the gloss stands over the subtitle,
     where the finger is, and not over a transcript the video is covering. */
  var subs = null, subsAt = -1, subsTimer = 0;
  function subsOn() {
    var box = document.getElementById('playerwrap');
    if (!box) return;
    if (!subs) {
      subs = el('div', 'm-subs');
      subs.setAttribute('aria-live', 'polite');
      subs.addEventListener('click', onSubTap);
    }
    if (subs.parentNode !== box) box.appendChild(subs);
    subsAt = -1;
    paintSubs();
    clearInterval(subsTimer);
    subsTimer = setInterval(paintSubs, 250);
  }
  function subsOff() {
    clearInterval(subsTimer);
    subsTimer = 0;
    ungloss();
    if (subs && subs.parentNode) subs.parentNode.removeChild(subs);
  }
  function onSubTap(e) {
    var p = window.ParsehPlayer;
    var line = subs && subs.querySelector('.m-subline');
    var w = e.target && e.target.closest ? e.target.closest('.w') : null;
    if (!w || !line || !p || !p.gloss) return;
    // as the transcript's own phrase does: the page closes the cloud on any
    // click that lands outside it, and this click lands on a copy it has
    // never heard of
    e.stopPropagation();
    p.gloss(+line.dataset.i, +w.dataset.j, w);
  }
  // the cloud hangs on a copy; when the copy goes, the cloud must go with it
  function ungloss() {
    var p = window.ParsehPlayer;
    if (subs && subs.querySelector('.w.hot') && p && p.ungloss) p.ungloss();
  }
  function paintSubs() {
    if (!subs) return;
    // the caption in play is the one the player marks .on-air
    var seg = document.querySelector('#segs .seg.on-air');
    if (!seg) return;
    var i = seg.dataset.i;
    if (i === subsAt) return;
    ungloss();
    subsAt = i;
    subs.replaceChildren();
    var line = seg.cloneNode(true);
    line.classList.add('m-subline');
    line.removeAttribute('id');
    // a phrase the transcript had open is not open here
    Array.prototype.forEach.call(line.querySelectorAll('.hot'), function (h) {
      h.classList.remove('hot');
    });
    subs.appendChild(line);
  }

  /* ---- what writes, refused (as in a book's reader) ---- */
  function isField(t) {
    return !!(t && t.closest && t.closest('input, textarea, select, [contenteditable]'));
  }
  window.addEventListener('click', function (e) {
    if (!mobile() || !(e.altKey || e.ctrlKey || e.metaKey)) return;
    var t = e.target;
    if (!t || !t.closest || t.closest('a[href], header, .wt-menu')) return;
    if (!t.closest('.wd, .w, .seg')) return;
    e.preventDefault();
    e.stopImmediatePropagation();
  }, true);
  window.addEventListener('keydown', function (e) {
    if (!mobile() || e.altKey || e.ctrlKey || e.metaKey || isField(e.target)) return;
    if (e.key === 'e' || e.key === 'E') e.stopImmediatePropagation();
  }, true);

  /* ---- the mode ---- */
  function onMode(m) {
    if (m === 'mobile') {
      build();
      if (full) full.hidden = !sideways();
    } else if (more) {
      setMore(false);
      // the browser mode is the page as its own script built it: the overlay
      // is this layer's and goes with the layer
      setFull(false);
    }
  }
  function turned() {
    if (full) full.hidden = !sideways();
    // upright the video fills a strip and there is nothing left to read, so
    // a phone turned back upright leaves the whole screen with it
    if (!sideways()) setFull(false);
  }
  function start() {
    document.body.setAttribute('data-mobile-page', '');
    var p = P();
    if (p && p.mode && p.mode.onChange) p.mode.onChange(onMode);
    if (mobile()) onMode('mobile');
    try {
      window.matchMedia('(orientation: landscape) and (min-width: 600px)')
        .addEventListener('change', turned);
    } catch (e) {}
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})();

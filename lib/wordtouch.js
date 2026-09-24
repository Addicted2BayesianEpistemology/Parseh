// SPDX-License-Identifier: GPL-3.0-or-later
/* Parseh — a finger's way to what a modifier-click does (TO-DO §4.6).

   In the book reader and in a video's transcript alike, copying is a
   SHIFT-click and a card is an ALT- (or Ctrl-) click.  A finger can hold
   neither key, so on a tablet -- and on a phone, for the copying -- those two
   doors did not exist at all.  Here they are one gesture: HOLD A FINGER on a
   word and a small menu opens, saying what can be done with it.

       Card for “word”        (the browser mode only: a card writes, and
                               the mobile mode makes none -- docs/mobile.md)
       Copy “the chunk”
       Copy the sentence

   NOTHING HERE DOES THE WORK.  Each line dispatches the very click the page
   already listens for -- a click with altKey on the word, a click with
   shiftKey on the chunk or on the line -- so the card that opens is the page's
   own card, with its cut editor and its place in the text, and the copy is the
   page's own copy, with its toast.  The reader and the player answer those
   clicks in their own way and neither had to be touched.

   A tap is left alone: it still plays, or opens a gloss.  Only a press held
   for half a second on a TOUCH screen opens the menu -- a mouse must not lose
   its ordinary press-and-drag to select text -- and the click that a phone
   sends when the finger is lifted is swallowed, or the word under the menu
   would be played the moment it opened. */
(function () {
  'use strict';
  if (window.ParsehWordTouch) return;
  window.ParsehWordTouch = {};

  var HOLD = 500, MOVED = 10, SAY = 18;
  var menu = null, swallow = 0, press = null;

  function P() { return window.Parseh; }
  function mobile() { var p = P(); return !!(p && p.mode && p.mode.isMobile()); }
  function text(el) {
    var p = P();
    var s = (p && p.baseText ? p.baseText(el) : el.textContent) || '';
    return s.replace(/\s+/g, ' ').trim();
  }
  function shorten(s) { return s.length > SAY ? s.slice(0, SAY - 1) + '…' : s; }
  function fire(el, how) {
    var e = {bubbles: true, cancelable: true, view: window};
    for (var k in how) e[k] = how[k];
    el.dispatchEvent(new MouseEvent('click', e));
  }

  /* ---- what is under the finger ----
     The reader: a word is .wd, a chunk .w (pass 1) or a pass-2 row's .fa,
     the sentence a .pass inside the .sub.  The player: a word is .wd, a
     chunk .w, the sentence the caption's .seg.  Where a page has neither,
     nothing opens. */
  function what(t) {
    if (!t || !t.closest) return null;
    if (t.closest('button, input, select, textarea, a[href], #cloud, #anki, #tocwrap, header, .wt-menu'))
      return null;
    var seg = t.closest('.seg');                       // a video's caption
    var sub = t.closest('.sub');                       // a book's subparagraph
    if (!seg && !sub) return null;
    var wd = t.closest('.wd');
    var unit = t.closest('.w') || t.closest('.row .fa');
    if (!unit) { var row = t.closest('.row'); if (row) unit = row.querySelector('.fa'); }
    var whole = seg || t.closest('.pass') || (sub && sub.querySelector('.p1'));
    if (!wd && !unit && !whole) return null;
    return {wd: wd, unit: unit, whole: whole, seg: !!seg};
  }
  // a card writes, so the mobile mode offers none (§18); and a page with no
  // card sheet at all (an old reader, a page of another kind) offers none
  function cardable(at) {
    return !!(at.wd && !mobile() && document.getElementById('anki'));
  }

  /* ---- the menu ---- */
  function shut() {
    if (!menu) return;
    menu.remove();
    menu = null;
  }
  function open(at, x, y) {
    shut();
    var rows = [];
    if (cardable(at))
      rows.push(['Card for “' + shorten(text(at.wd)) + '”',
                 function () { fire(at.wd, {altKey: true}); }]);
    if (at.unit)
      rows.push(['Copy “' + shorten(text(at.unit)) + '”',
                 function () { fire(at.unit, {shiftKey: true}); }]);
    if (at.whole)
      rows.push([at.seg ? 'Copy the caption' : 'Copy the sentence',
                 function () { fire(at.whole, {shiftKey: true}); }]);
    if (!rows.length) return;
    menu = document.createElement('div');
    menu.className = 'wt-menu';
    menu.setAttribute('role', 'menu');
    menu.setAttribute('aria-label', 'what to do with this word');
    rows.forEach(function (r) {
      var b = document.createElement('button');
      b.type = 'button';
      b.setAttribute('role', 'menuitem');
      b.textContent = r[0];
      b.addEventListener('click', function (e) {
        e.preventDefault(); e.stopPropagation();
        shut();
        r[1]();
      });
      menu.appendChild(b);
    });
    (document.fullscreenElement || document.body).appendChild(menu);
    var w = menu.offsetWidth, h = menu.offsetHeight, pad = 8;
    var left = Math.max(pad, Math.min(Math.round(x - w / 2), window.innerWidth - w - pad));
    var top = y - h - 12;
    if (top < pad) top = Math.min(y + 16, window.innerHeight - h - pad);
    menu.style.left = left + 'px';
    menu.style.top = Math.max(pad, top) + 'px';
    var first = menu.querySelector('button');
    if (first) { try { first.focus(); } catch (e) {} }
    // a selection the press may have started, let go: the menu is the answer
    try { var s = getSelection(); if (s && s.removeAllRanges) s.removeAllRanges(); } catch (e) {}
  }

  /* ---- the press ---- */
  function start(e) {
    if (menu) { shut(); return; }
    if (e.touches && e.touches.length !== 1) { stop(); return; }
    var t = e.touches ? e.touches[0] : e;
    var at = what(e.target);
    if (!at) return;
    press = {x: t.clientX, y: t.clientY, at: at, timer: setTimeout(function () {
      press.fired = true;
      swallow = Date.now();
      open(at, press.x, press.y);
    }, HOLD)};
  }
  function moved(e) {
    if (!press) return;
    var t = e.touches ? e.touches[0] : e;
    if (Math.abs(t.clientX - press.x) > MOVED || Math.abs(t.clientY - press.y) > MOVED) stop();
  }
  function stop() {
    if (!press) return;
    clearTimeout(press.timer);
    press = null;
  }
  document.addEventListener('touchstart', start, {passive: true});
  document.addEventListener('touchmove', moved, {passive: true});
  document.addEventListener('touchend', stop, {passive: true});
  document.addEventListener('touchcancel', stop, {passive: true});
  // the click a phone sends when the finger is lifted, and the menu a long
  // press raises on Android, are both this gesture's own
  document.addEventListener('click', function (e) {
    if (!swallow || Date.now() - swallow > 900) return;
    if (menu && menu.contains(e.target)) return;
    swallow = 0;
    e.preventDefault();
    e.stopImmediatePropagation();
  }, true);
  document.addEventListener('contextmenu', function (e) {
    if (press || menu) e.preventDefault();
  });
  document.addEventListener('pointerdown', function (e) {
    if (menu && !menu.contains(e.target)) shut();
  }, true);
  window.addEventListener('keydown', function (e) {
    if (menu && e.key === 'Escape') { e.preventDefault(); shut(); }
  });
  window.addEventListener('scroll', shut, {passive: true});
  window.addEventListener('resize', shut);
})();

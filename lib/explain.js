// SPDX-License-Identifier: GPL-3.0-or-later
/* Parseh — “?”, so that nothing is known only to a mouse (TO-DO §4.7).

   Much of what a button does is written in its `title`, which a browser shows
   when a MOUSE rests on it.  A finger never rests: on a phone and on a tablet
   those sentences did not exist.  So on a screen with no hover, a ? joins the
   page's bar.  Press it and the page is in EXPLAIN: the next tap on any
   control says what that control does, in a bubble beside it, instead of
   pressing it.  Press ? again (or Escape, or Done in the bubble) and the page
   is itself again.  The owner chose this over a long press, which is already
   taken -- holding ↺ or ↻ picks the seconds -- and over printing every
   sentence under its button, which would take half the screen.

   IT IS THE SAME SENTENCE THE MOUSE GETS: `title` first, then aria-label,
   then the control's own words.  Nothing anywhere has to be written twice,
   and a control added later is explained the day it is added.

   IT IS LOADED BY BOTH WORLDS: lib/parseh.js puts it on every page of the
   toolbox, and the studio's templates (the decks, a document, the library)
   carry a tag of their own, since those pages do not load parseh.js.  So its
   few rules are written from here, in the tokens of whichever sheet is in
   force -- the toolbox's --card/--ink/--rule, the studio's
   --chrome-panel/--chrome-fg/--chrome-line -- with a plain colour behind
   both. */
(function () {
  'use strict';
  if (window.ParsehExplain) return;

  var CSS = [
    '.px-ask{font:inherit;font-size:15px;line-height:1;min-width:48px;min-height:48px;',
    '  padding:6px 8px;border:1px solid var(--rule,var(--chrome-line,#ddd));border-radius:10px;',
    '  background:var(--card,var(--chrome-panel,#fff));color:var(--dim,var(--chrome-mut,#555));',
    '  cursor:pointer;-webkit-tap-highlight-color:transparent}',
    '.px-ask[aria-pressed=true]{background:var(--accent,#be3455);border-color:var(--accent,#be3455);',
    '  color:var(--accent-fg,#fff)}',
    'body.px-on{cursor:help}',
    '.px-tip{position:fixed;z-index:430;max-width:min(330px,92vw);padding:12px 14px;',
    '  background:var(--card,var(--chrome-panel,#fff));color:var(--ink,var(--chrome-fg,#222));',
    '  border:1px solid var(--accent,#be3455);border-radius:12px;font-size:14.5px;line-height:1.45;',
    '  box-shadow:0 8px 24px rgba(0,0,0,.2)}',
    '.px-tip b{display:block;font-size:12px;letter-spacing:.1em;text-transform:uppercase;',
    '  color:var(--dim,var(--chrome-mut,#666));margin-bottom:4px}',
    '.px-tip .px-done{display:block;margin:10px 0 0;margin-inline-start:auto;font:inherit;font-size:13px;',
    '  min-height:40px;padding:6px 12px;border:1px solid var(--rule,var(--chrome-line,#ddd));',
    '  border-radius:8px;background:transparent;color:var(--dim,var(--chrome-mut,#555));cursor:pointer}',
    // what is being explained, lit while the bubble is up
    '.px-lit{outline:2px solid var(--accent,#be3455);outline-offset:2px;border-radius:6px}'
  ].join('\n');

  var on = false, ask = null, tip = null, lit = null, said = false;

  function touch() {
    try { return window.matchMedia('(hover: none)').matches; } catch (e) { return false; }
  }
  function style() {
    if (document.getElementById('px-style')) return;
    var s = document.createElement('style');
    s.id = 'px-style';
    s.textContent = CSS;
    (document.head || document.documentElement).appendChild(s);
  }
  /* Where the ? goes: the bar this page wears -- and a page that carries
     both layouts (the decks, a document) wears two, one of them not drawn.
     So the bar is the first of these that is actually ON THE SCREEN, and
     the ? moves when the mode changes under it. */
  function drawn(el) { return !!(el && el.getClientRects && el.getClientRects().length); }
  function bar() {
    var tries = ['header .hrow', 'header.m-topbar', 'header.topbar', '.parseh-bar', 'header'];
    for (var i = 0; i < tries.length; i++) {
      var all = document.querySelectorAll(tries[i]);
      for (var k = 0; k < all.length; k++) if (drawn(all[k])) return all[k];
    }
    return null;
  }
  function what(el) {
    if (!el || !el.closest) return null;
    var c = el.closest('button, a[href], [role=button], [role=menuitem], input, select, textarea, label, [title]');
    if (!c || (tip && tip.contains(c))) return null;
    return c;
  }
  function words(el) {
    var t = (el.getAttribute('title') || '').trim();
    if (t) return t;
    var a = (el.getAttribute('aria-label') || '').trim();
    if (a) return a;
    var id = el.getAttribute('aria-labelledby');
    if (id) { var l = document.getElementById(id); if (l) return (l.textContent || '').trim(); }
    return '';
  }
  function name(el) {
    var n = (el.getAttribute('aria-label') || el.textContent || '').replace(/\s+/g, ' ').trim();
    if (!n && el.tagName === 'INPUT') n = el.getAttribute('placeholder') || el.type || 'this box';
    return n.length > 40 ? n.slice(0, 39) + '…' : (n || 'this control');
  }
  function hide() {
    if (tip) { tip.remove(); tip = null; }
    if (lit) { lit.classList.remove('px-lit'); lit = null; }
  }
  function show(el, text) {
    hide();
    tip = document.createElement('div');
    tip.className = 'px-tip';
    tip.setAttribute('role', 'status');
    var head = document.createElement('b');
    head.textContent = name(el);
    tip.appendChild(head);
    tip.appendChild(document.createTextNode(text));
    var done = document.createElement('button');
    done.type = 'button';
    done.className = 'px-done';
    done.textContent = 'done explaining';
    done.addEventListener('click', function (e) { e.stopPropagation(); set(false); });
    tip.appendChild(done);
    document.body.appendChild(tip);
    el.classList.add('px-lit');
    lit = el;
    var r = el.getBoundingClientRect(), w = tip.offsetWidth, h = tip.offsetHeight, pad = 8;
    var left = Math.max(pad, Math.min(Math.round(r.left + r.width / 2 - w / 2), window.innerWidth - w - pad));
    var top = r.bottom + pad;
    if (top + h > window.innerHeight - pad) top = Math.max(pad, r.top - h - pad);
    tip.style.left = left + 'px';
    tip.style.top = top + 'px';
  }
  function set(v) {
    on = !!v;
    if (ask) {
      ask.setAttribute('aria-pressed', String(on));
      ask.title = on ? 'stop explaining' : 'what does this button do? — press, then tap anything';
    }
    document.body.classList.toggle('px-on', on);
    hide();
    if (on && !said) {
      said = true;
      show(ask, 'Tap anything on the page and it will say what it does, instead of doing it. ' +
                'Press ? again when you are done.');
    }
  }

  /* While it is on, a tap SAYS instead of doing: the capture phase, before
     any page's own listener, and the event goes no further. */
  document.addEventListener('click', function (e) {
    if (!on) return;
    if (ask && (e.target === ask || (ask.contains && ask.contains(e.target)))) return;
    if (tip && tip.contains(e.target)) return;
    var el = what(e.target);
    e.preventDefault();
    e.stopImmediatePropagation();
    if (!el) { hide(); return; }
    var t = words(el);
    show(el, t || 'This one has no explanation written for it yet — it does what its name says.');
  }, true);
  // and nothing it would have done on the way down happens either
  ['pointerdown', 'mousedown', 'touchstart'].forEach(function (n) {
    document.addEventListener(n, function (e) {
      if (!on) return;
      if (ask && (e.target === ask || (ask.contains && ask.contains(e.target)))) return;
      if (tip && tip.contains(e.target)) return;
      e.stopImmediatePropagation();
    }, true);
  });
  window.addEventListener('keydown', function (e) {
    if (on && e.key === 'Escape') { e.preventDefault(); set(false); }
  });
  window.addEventListener('scroll', function () { if (on) hide(); }, {passive: true});

  function build() {
    if (!touch()) return;
    var b = bar();
    if (!b) return;
    style();
    if (!ask) {
      ask = document.createElement('button');
      ask.type = 'button';
      ask.className = 'px-ask';
      ask.textContent = '?';
      ask.setAttribute('aria-pressed', 'false');
      ask.setAttribute('aria-label', 'explain the buttons');
      ask.title = 'what does this button do? — press, then tap anything';
      ask.addEventListener('click', function (e) { e.stopPropagation(); set(!on); });
    }
    if (ask.parentNode !== b) b.appendChild(ask);
  }
  window.ParsehExplain = {on: function () { return on; }, set: set, build: build};
  if (document.readyState === 'loading')
    document.addEventListener('DOMContentLoaded', build);
  else build();
  // A page whose bar is drawn later (the studio's deck list), or whose bar
  // CHANGES under it -- a page carrying both layouts, switched from the
  // browser interface to the mobile one -- is followed: the ? goes to
  // whichever bar is on the screen now.
  if (window.MutationObserver) {
    var watch = new MutationObserver(function () {
      if (ask && ask.isConnected && drawn(ask.parentNode)) return;
      build();
    });
    watch.observe(document.documentElement, {childList: true, subtree: true,
                                             attributes: true, attributeFilter: ['data-mode', 'hidden', 'class']});
    setTimeout(function () { watch.disconnect(); }, 10000);
  }
})();

// SPDX-License-Identifier: GPL-3.0-or-later
/* Parseh — the page zoom (a0.5.0): everything on a page bigger or smaller
   TOGETHER -- the bars, the buttons, the clouds, the sheets, the subtitles --
   by ONE number a person keeps for the whole device.  It is what Ctrl + and
   Ctrl − do in a browser, for the places that have no such keys: the
   installed app, and a phone.  The gear's Zoom row (lib/pagesettings.js)
   turns it; this file is the whole of it.

   THE NUMBER: `parseh_zoom` in localStorage, an integer percent, absent
   meaning 100.  It is a fact about THIS device's screen, so it is never in
   lib/prefs.js's KEYS and never follows a person to another device.  The
   steps are the browser's own (70 80 90 100 110 125 150 175 200).

   LOADED FIRST, AND SYNCHRONOUSLY, on every page of the toolbox: lib/parseh.js
   writes a <script> for this file at its own top (so a reader built before
   zoom existed has it without being built again), and the studio's templates
   carry a tag of their own in their <head>, since they do not load
   parseh.js.  The guide's pages and a note's bare page do not load it and are
   not zoomed.  Off the disk (file:) nothing is done at all: the browser's
   own zoom is there, and a sheet read off the disk cannot be read by a
   script.

   AT 100 % IT DOES NOTHING.  No property is replaced, no style is written, no
   observer is started: a page at its own size is the page it always was, to
   the byte.  Only the answers below (ParsehZoom) exist, so that the gear can
   offer the steps, and a step taken while the page is open starts everything
   that is needed -- and the step back to 100 % puts every thing back.

   WHAT A STEP DOES, AND WHY THIS FILE IS MORE THAN ONE LINE.  `html{zoom:Z}`
   makes the page Z times bigger, and by itself it breaks three things
   (measured in Chromium 151, whose zoom is the standardized one):
     1. The geometry the page's own scripts read and write no longer agree.
        A rect from getBoundingClientRect() is in what is SEEN (zoomed), but
        a number written to style.left is zoomed AGAIN: a cloud asked to sit
        at 90,358 lands at 135,537.  So every script that places a thing --
        the gloss cloud, the dictionary's sheet, the timeline's strip, the
        explain bubble -- would be Z times out.
     2. `100vw` stays the window's real width, which is Z times too wide for
        a page now laid out in 1/Z of it: the page scrolls sideways and its
        fixed bars overhang.
     3. A media query reads the window as it really is.
   (1) is cured by the SHIM below: once a zoom is in force, the APIs that
   hand a script a position or a size in what is seen (rects, the window's
   size and scroll, an event's coordinates, a point to look under) answer in
   the page's own zoomed px instead, and the ones that take one (scrollTo,
   elementFromPoint) take it in the same px.  Every script then computes in
   one coordinate system, as it did at 100 %, and none of them has to know
   there is a zoom.  (2) is cured by rewriting every viewport length in every
   stylesheet and inline style to `calc(N vw / var(--z))`.  (3) is NOT cured,
   on purpose (the owner's decision, a0.5.0 plan, section 5): a media query,
   in a stylesheet and in window.matchMedia, keeps reading the window as it
   is, and the 320 RULE below keeps that honest -- a window is never zoomed to
   where the page would be narrower than 320 px, so no breakpoint can be
   crossed far.  (What it does mean: a layout that wakes at `min-width:860px`
   wakes at 860 REAL px, which at 200 % is a page 430 px wide in its own.)

   THE 320 RULE: a step is allowed only where (the window's real width in px)
   / (the zoom) is at least 320.  On a 390 px phone that allows 110 and
   nothing more; sideways, at 844, everything.  What a person CHOSE is kept
   as it was chosen (`get`) and what is IN FORCE is the largest step the
   window allows (`applied`), so that a phone turned upright and back is at
   the size it was left at.  Zooming OUT never fits badly (the page gets
   wider), so only the steps above 100 are ever refused.

   AN ENGINE THAT DOES NOT BEHAVE LIKE THAT IS LEFT ALONE.  Whether `zoom`
   reports rects in what is seen is asked of the engine itself (supported()),
   with an element that is built and thrown away; and after a first step the
   result is measured again on the real page.  An engine that fails either
   test (one whose zoom reports a rect in the page's own px, as zoom was before
   it was standardized, or has no zoom at all) gets no zoom -- the steps are
   refused with a sentence -- and no half of one.  What that engine is, and
   whether a phone's own is one, is for a real device to say: the tests of
   this file ran in Chromium. */
(function () {
  'use strict';
  if (window.ParsehZoom || location.protocol === 'file:') return;

  var KEY = 'parseh_zoom';
  var STEPS = [70, 80, 90, 100, 110, 125, 150, 175, 200];
  var MIN_WIDTH = 320;
  var NARROW = 'this screen is too narrow for more';
  var SMALLEST = 'this is the smallest size';
  var LARGEST = 'this is the largest size';
  var UNSUPPORTED = 'this browser cannot zoom the page';

  /* ---- the two rules, as pure functions of numbers (the unit tests run
     these very lines) ---- */
  // whether a zoom of `pct` percent may be put on a window `width` px wide;
  // 100 and below always may, and a width that is not known (0, in a window
  // that is not shown) refuses nothing.  Whole numbers, not a division, so
  // that 352 px at 110 % is exactly on the line and not a rounding off it
  function fits(pct, width) {
    return pct <= 100 || !(width > 0) || width * 100 >= MIN_WIDTH * pct;
  }
  // the step nearest to a number, 100 for anything that is not one
  function snap(pct) {
    var n = Number(pct), best = 100, gap = Infinity;
    // anything that is not a percent in a believable range (a stored 1.5, a
    // ratio mistaken for one) is not a size: 100
    if (pct === null || pct === '' || !isFinite(n) || n < 50 || n > 300) return 100;
    for (var i = 0; i < STEPS.length; i++) {
      var d = Math.abs(STEPS[i] - n);
      if (d < gap) { gap = d; best = STEPS[i]; }
    }
    return best;
  }
  // what a window `width` px wide is given of what was chosen: the largest
  // step not above it that fits
  function clampTo(chosen, width) {
    for (var i = STEPS.indexOf(snap(chosen)); i >= 0; i--)
      if (fits(STEPS[i], width)) return STEPS[i];
    return 100;
  }
  function allowedFor(width) {
    for (var i = STEPS.length - 1; i >= 0; i--) if (fits(STEPS[i], width)) return STEPS[i];
    return 100;
  }

  /* ---- what the engine says before anything is replaced ----
     Kept here, at the top, because the 320 rule needs the window's REAL
     width (what the shim answers is the page's) and the shim, once in, is
     what every other line of this file would be asking. */
  var de = document.documentElement;
  function accessor(obj, name) {
    var d = obj && Object.getOwnPropertyDescriptor(obj, name);
    return d && d.get;
  }
  var VV = window.VisualViewport && window.visualViewport ? Object.getPrototypeOf(window.visualViewport) : null;
  var raw = {
    innerWidth: accessor(window, 'innerWidth'),
    innerHeight: accessor(window, 'innerHeight'),
    scrollY: accessor(window, 'scrollY'),
    clientWidth: accessor(Element.prototype, 'clientWidth'),
    vvWidth: accessor(VV, 'width'),
    vvScale: accessor(VV, 'scale'),
    rect: Element.prototype.getBoundingClientRect,
    pointsAt: Document.prototype.elementsFromPoint,
    scrollBy: window.scrollBy,
    scrollTo: window.scrollTo
  };
  function read(get, on, dflt) { return get ? get.call(on) : dflt; }
  /* THE WINDOW'S REAL WIDTH, in the px a page would have at 100 %.  Not
     innerWidth, which is the LAYOUT viewport, and a phone widens that to fit
     a page whose content is wider than the screen (a page 422 px wide on a
     390 px phone has an innerWidth of 422, and one made wider by a zoom would
     read wider again): the rule would then allow a bigger zoom the wider the
     page overflowed.  The visual viewport's width times its scale is what
     the glass really is -- 390 there, whatever the page is, and whether the
     person has pinched -- plus the scrollbar a desktop window takes from it.
     Where there is no visual viewport, the larger of the two readings of the
     layout one stands in (and neither is smaller than it is for a browser
     whose innerWidth follows a pinch, or a root not yet laid out). */
  function realWidth() {
    var inner = read(raw.innerWidth, window, window.innerWidth) || 0;
    var client = read(raw.clientWidth, de, 0) || 0;
    var seen = window.visualViewport && raw.vvWidth
      ? read(raw.vvWidth, window.visualViewport, 0) * read(raw.vvScale, window.visualViewport, 1) : 0;
    return seen > 0 ? seen + Math.max(0, inner - client) : Math.max(inner, client);
  }

  var shown = 100;         // the zoom in force, in percent (100 = nothing is replaced)
  var factor = 1;          // the same as a multiplier, which every replaced answer reads
  var memory = null;       // what was chosen, kept here when the browser will not store it
  var listeners = [];
  var told = null;         // what the listeners were last told
  var broken = false;      // the first step, measured on the real page, was wrong

  /* ---- what a person chose, kept on this device ---- */
  function chosen() {
    var v = null;
    try { v = window.localStorage.getItem(KEY); } catch (e) { v = memory; }
    return v == null ? 100 : snap(v);
  }
  function keep(pct) {
    memory = pct === 100 ? null : String(pct);
    try {
      if (pct === 100) window.localStorage.removeItem(KEY);
      else window.localStorage.setItem(KEY, String(pct));
    } catch (e) {}
  }

  /* ---- does this engine zoom the way this file knows? ----
     A child with `zoom:2` reports a rect twice its own width, and its
     offsetWidth is its own: that is the standardized zoom (Chromium 128 and
     after), the one every number below was measured on.  Asked once, the
     first time a step is wanted -- never at 100 %, so a page nobody zooms
     pays nothing. */
  var PROBE = 'position:fixed;left:0;top:0;width:100px;height:100px;margin:0;padding:0;' +
              'border:0;box-sizing:content-box;visibility:hidden;pointer-events:none;';
  var verdict = null;
  function supported() {
    if (verdict !== null) return verdict && !broken;
    verdict = false;
    try {
      if (!('zoom' in de.style) || !window.DOMRect) return false;
      var host = document.body || de, p = document.createElement('div');
      p.style.cssText = PROBE + 'zoom:2';
      host.appendChild(p);
      var seen = raw.rect.call(p).width, own = p.offsetWidth;
      host.removeChild(p);
      verdict = own === 100 && Math.abs(seen - 200) < 1;
    } catch (e) {}
    return verdict && !broken;
  }

  /* ================= THE SHIM: geometry in the page's own px =================
     Each entry below is registered with the thing that puts it back, so that
     the step to 100 % leaves the engine as it found it. */
  var undo = [];
  function swap(obj, name, make) {
    var was = obj && Object.getOwnPropertyDescriptor(obj, name);
    if (!was) return;
    var now = make(was);
    if (!now) return;
    now.configurable = true;
    now.enumerable = was.enumerable;
    try {
      Object.defineProperty(obj, name, now);
      undo.push(function () { try { Object.defineProperty(obj, name, was); } catch (e) {} });
    } catch (e) {}
  }
  // an attribute that tells a script a size or place in what is SEEN, said
  // instead in the page's px: divided by the zoom (or multiplied, for a
  // density).  `only` limits it to one object -- the document's root -- for
  // the metrics that are the page's own for every other element
  function scaled(obj, name, div, only) {
    swap(obj, name, function (d) {
      if (!d.get) return null;
      var get = d.get;
      return {
        get: function () {
          var v = get.call(this);
          if (typeof v !== 'number' || (only && this !== only)) return v;
          return div ? v / factor : v * factor;
        },
        set: d.set && function (v) {
          // a number written to the root's scroll is in the page's px too
          if (typeof v === 'number' && only && this === only) v = v * factor;
          d.set.call(this, v);
        }
      };
    });
  }
  function rect(r) {
    if (!r) return r;
    var z = factor, x = (r.x !== undefined ? r.x : r.left) / z, y = (r.y !== undefined ? r.y : r.top) / z;
    try { return new DOMRect(x, y, r.width / z, r.height / z); }
    catch (e) {
      return {x: x, y: y, left: x, top: y, width: r.width / z, height: r.height / z,
              right: x + r.width / z, bottom: y + r.height / z};
    }
  }
  function rects(list) {
    var out = [];
    for (var i = 0; i < list.length; i++) out.push(rect(list[i]));
    out.item = function (i) { return this[i] || null; };
    return out;
  }
  // a method that hands back rects
  function rectMethod(proto, name, many) {
    swap(proto, name, function (d) {
      if (typeof d.value !== 'function') return null;
      var f = d.value;
      return {writable: true, value: function () {
        var r = f.apply(this, arguments);
        return many ? rects(r) : rect(r);
      }};
    });
  }
  // a method that takes a point in the page's px, and is asked in what is seen
  function pointMethod(proto, name) {
    swap(proto, name, function (d) {
      if (typeof d.value !== 'function') return null;
      var f = d.value;
      return {writable: true, value: function (x, y) {
        var a = Array.prototype.slice.call(arguments);
        a[0] = x * factor; a[1] = y * factor;
        return f.apply(this, a);
      }};
    });
  }
  // scrollTo / scroll / scrollBy: a number, or {left, top, behavior}.  `only`
  // as above: the root's own methods take the page's px, any other element's
  // are in its own and are left alone
  function scrollMethod(proto, name, only) {
    swap(proto, name, function (d) {
      if (typeof d.value !== 'function') return null;
      var f = d.value;
      return {writable: true, value: function () {
        if (only && this !== only) return f.apply(this, arguments);
        var a = arguments[0], args = [], i;
        if (a && typeof a === 'object') {
          var o = {};
          for (var k in a) o[k] = a[k];
          if (typeof o.left === 'number') o.left = o.left * factor;
          if (typeof o.top === 'number') o.top = o.top * factor;
          return f.call(this, o);
        }
        for (i = 0; i < arguments.length; i++)
          args.push(typeof arguments[i] === 'number' ? arguments[i] * factor : arguments[i]);
        return f.apply(this, args);
      }};
    });
  }

  function install() {
    // THE RECTS: an element's, and a range's (the selection's, a word's)
    rectMethod(Element.prototype, 'getBoundingClientRect', false);
    rectMethod(Element.prototype, 'getClientRects', true);
    if (window.Range) {
      rectMethod(Range.prototype, 'getBoundingClientRect', false);
      rectMethod(Range.prototype, 'getClientRects', true);
    }
    // THE WINDOW: its size, where it is scrolled, and how dense it is.  The
    // density is what a canvas is drawn at (lib/timeline.js, the player's
    // waveform): a page px is now `factor` device px, and a canvas drawn at
    // the old density would be stretched and soft
    ['innerWidth', 'innerHeight', 'scrollX', 'scrollY', 'pageXOffset', 'pageYOffset'].forEach(function (n) {
      scaled(window, n, true);
    });
    scaled(window, 'devicePixelRatio', false);
    // THE ROOT ELEMENT's metrics are the window's (an element's own are
    // already in the page's px, as its style is, and are left as they are)
    ['clientWidth', 'clientHeight', 'scrollWidth', 'scrollHeight', 'scrollTop', 'scrollLeft'].forEach(function (n) {
      scaled(Element.prototype, n, true, de);
    });
    // SCROLLING THE WINDOW takes the page's px, and so does the root
    ['scrollTo', 'scroll', 'scrollBy'].forEach(function (n) {
      scrollMethod(window, n);
      scrollMethod(Element.prototype, n, de);
    });
    // WHAT IS UNDER A POINT: asked in the page's px, answered by the engine
    // in what is seen
    ['elementFromPoint', 'elementsFromPoint', 'caretRangeFromPoint', 'caretPositionFromPoint'].forEach(function (n) {
      pointMethod(Document.prototype, n);
    });
    if (window.ShadowRoot) {
      pointMethod(ShadowRoot.prototype, 'elementFromPoint');
      pointMethod(ShadowRoot.prototype, 'elementsFromPoint');
    }
    // WHERE AN EVENT HAPPENED: a mouse, a pen, a finger (PointerEvent and
    // WheelEvent inherit these from MouseEvent).  A synthetic event built
    // with coordinates is not corrected: no page of Parseh makes one
    if (window.MouseEvent)
      ['clientX', 'clientY', 'pageX', 'pageY', 'x', 'y'].forEach(function (n) {
        scaled(MouseEvent.prototype, n, true);
      });
    if (window.Touch)
      ['clientX', 'clientY', 'pageX', 'pageY'].forEach(function (n) { scaled(Touch.prototype, n, true); });
    // THE VISUAL VIEWPORT (the pinch's window): sizes and offsets, not its scale
    if (window.VisualViewport)
      ['width', 'height', 'offsetLeft', 'offsetTop', 'pageLeft', 'pageTop'].forEach(function (n) {
        scaled(VisualViewport.prototype, n, true);
      });
    // WHAT AN OBSERVER SAYS IS WHERE: an IntersectionObserver's rects are in
    // what is seen.  (A ResizeObserver's are an element's own, in the page's
    // px already, and a rootMargin is the engine's business.)
    if (window.IntersectionObserverEntry)
      ['boundingClientRect', 'intersectionRect', 'rootBounds'].forEach(function (n) {
        swap(IntersectionObserverEntry.prototype, n, function (d) {
          if (!d.get) return null;
          var get = d.get;
          return {get: function () { return rect(get.call(this)); }};
        });
      });
  }
  function uninstall() {
    while (undo.length) undo.pop()();
  }

  /* ============ VIEWPORT UNITS: written again in every stylesheet ============
     `100vw` is the window's real width and means Z times too much in a page
     that is Z times larger, so each is rewritten to `calc(100vw / var(--z, 1))`.
     (With the zoom out, `--z` goes and the fallback 1 makes a left-over one
     the same as it was.)  Done to the CSSOM, where a rule's values are
     already parsed -- the sheets are not fetched again -- to every rule, in
     nested @media, @supports, @layer and @import; to the sheets that arrive
     after this file (a <link> that loads later, a <style> a script adds); and
     to the style attributes of elements, in the page and as scripts set
     them.  The rules' originals are kept so that going back to 100 % can put
     them back.  Not touched: a media query (see above), a string, a url().

     A VALUE A SCRIPT SETS ON `el.style`, or a <style> it adds, is rewritten
     when the browser next lets scripts run (a mutation observer), not in the
     setter: a script that sets a viewport length and measures in the same
     breath sees the page's own.  No page of Parseh does; the one that sets
     one (lib/making.js) does not measure. */
  var UNIT = '(?:dvh|svh|lvh|vh|dvw|svw|lvw|vw|dvmin|svmin|lvmin|vmin|dvmax|svmax|lvmax|vmax)';
  // 1: a string or url() to leave alone; 2: what stands before a number (so
  // that `a-10vw` or the 1.5 of 1.5vw is read whole); 3 and 4: the number and
  // its unit, unless it is already followed by the division this writes (by
  // --z itself: the card sheet has a --zoom of its own, whose division is not it)
  var VIEWPORT = new RegExp('("(?:[^"\\\\]|\\\\.)*"|\'(?:[^\'\\\\]|\\\\.)*\'|url\\([^)]*\\))|' +
    '(^|[^\\w.#-])(-?(?:\\d+\\.?\\d*|\\.\\d+))(' + UNIT + ')(?![\\w-])(?!\\s*\\/\\s*var\\(--z\\s*[,)])', 'gi');
  function rewrite(v) {
    return v.indexOf('v') < 0 ? v : v.replace(VIEWPORT, function (m, skip, pre, num, unit) {
      return skip ? m : pre + 'calc(' + num + unit + ' / var(--z, 1))';
    });
  }
  var rewritten = [];      // {style, name, was, now, priority}: what to put back
  function declarations(style, keepIt) {
    // the list first and the writing after: writing a longhand can change
    // how a shorthand is listed, and a loop over `style` would lose its place
    var todo = [], i, name, v, n;
    if (!style) return;
    for (i = 0; i < style.length; i++) {
      name = style[i];
      v = style.getPropertyValue(name);
      if (!v) continue;
      n = rewrite(v);
      if (n !== v) todo.push([name, v, n, style.getPropertyPriority(name)]);
    }
    todo.forEach(function (t) {
      try {
        style.setProperty(t[0], t[2], t[3]);
        // what the engine reads back, which is what a later look will find
        if (keepIt) rewritten.push({style: style, name: t[0], was: t[1], now: style.getPropertyValue(t[0]), priority: t[3]});
      } catch (e) {}
    });
  }
  var done = typeof WeakMap === 'function' ? new WeakMap() : null;
  function rules(list) {
    for (var i = 0; i < list.length; i++) {
      var rule = list[i];
      if (window.CSSPageRule && rule instanceof CSSPageRule) continue;
      if (window.CSSFontFaceRule && rule instanceof CSSFontFaceRule) continue;
      if (rule.style) declarations(rule.style, true);
      if (rule.cssRules && rule.cssRules.length) rules(rule.cssRules);
      if (rule.styleSheet) sheet(rule.styleSheet);               // an @import
    }
  }
  function sheet(s) {
    var list = null;
    // a sheet from another origin cannot be read, and is left as it is
    try { list = s && s.cssRules; } catch (e) { return; }
    if (!list) return;
    // a sheet whose number of rules is the one already walked is not walked again
    if (done) { if (done.get(s) === list.length) return; done.set(s, list.length); }
    rules(list);
  }
  function sheets() {
    for (var i = 0; i < document.styleSheets.length; i++) sheet(document.styleSheets[i]);
    var adopted = document.adoptedStyleSheets;
    if (adopted) for (var k = 0; k < adopted.length; k++) sheet(adopted[k]);
  }
  var INLINE = '[style*="vw"],[style*="vh"],[style*="vmin"],[style*="vmax"]';
  function inline(el) {
    var attr = el.getAttribute && el.getAttribute('style');
    if (attr && attr.indexOf('v') >= 0) declarations(el.style, false);
  }
  function inlines(root) {
    if (root.matches && root.matches(INLINE)) inline(root);
    if (root.querySelectorAll) {
      var all = root.querySelectorAll(INLINE);
      for (var i = 0; i < all.length; i++) inline(all[i]);
    }
  }
  function restore() {
    while (rewritten.length) {
      var r = rewritten.pop();
      try {
        // not over a value the page has changed since
        if (r.style.getPropertyValue(r.name) === r.now) r.style.setProperty(r.name, r.was, r.priority);
      } catch (e) {}
    }
    if (done && typeof WeakMap === 'function') done = new WeakMap();
  }

  /* what arrives later: a sheet, a style element, an element with a style */
  var watch = null, heard = null;
  function arrived(nodes) {
    for (var i = 0; i < nodes.length; i++) {
      var n = nodes[i];
      if (n.nodeType !== 1) continue;
      if ((n.tagName === 'STYLE' || n.tagName === 'LINK') && n.sheet) sheet(n.sheet);
      inlines(n);
      var inner = n.querySelectorAll ? n.querySelectorAll('style, link[rel~="stylesheet"]') : [];
      for (var k = 0; k < inner.length; k++) if (inner[k].sheet) sheet(inner[k].sheet);
    }
  }
  function whole() {
    if (shown === 100) return;
    sheets();
    inlines(de);
  }
  function observe() {
    if (window.MutationObserver) {
      watch = new MutationObserver(function (list) {
        for (var i = 0; i < list.length; i++) {
          var m = list[i];
          if (m.type === 'attributes') inline(m.target);
          else {
            arrived(m.addedNodes);
            // the text of a <style> replaced under it
            if (m.target.tagName === 'STYLE' && m.target.sheet) { if (done) done['delete'](m.target.sheet); sheet(m.target.sheet); }
          }
        }
      });
      watch.observe(de, {childList: true, subtree: true, attributes: true, attributeFilter: ['style']});
    }
    // a <link> that finishes loading after this file ran: its sheet is
    // there to read when `load` is heard, and not before.  `load` does not
    // bubble, so it is heard on the way down
    heard = function (e) {
      var t = e.target;
      if (t && t.tagName === 'LINK' && t.sheet) sheet(t.sheet);
    };
    document.addEventListener('load', heard, true);
    // and once more when the page is whole, for whatever slipped between
    document.addEventListener('DOMContentLoaded', whole);
    window.addEventListener('load', whole);
  }
  function unobserve() {
    if (watch) { watch.disconnect(); watch = null; }
    if (heard) { document.removeEventListener('load', heard, true); heard = null; }
    document.removeEventListener('DOMContentLoaded', whole);
    window.removeEventListener('load', whole);
  }

  /* a printed page is the page at its own size */
  var printSheet = null;
  function printOwn(on) {
    if (on && !printSheet) {
      printSheet = document.createElement('style');
      printSheet.setAttribute('data-parseh-zoom', '');
      printSheet.textContent = '@media print{:root{zoom:1!important;--z:1!important}}';
      (document.head || de).appendChild(printSheet);
    } else if (!on && printSheet) {
      if (printSheet.parentNode) printSheet.parentNode.removeChild(printSheet);
      printSheet = null;
    }
  }

  /* ---- is what was just put on right?  measured on the real page ----
     Two boxes, built, measured and thrown away.  A box 100 px square: the
     engine's own rect must be `factor` times that and the shim's must be
     100.  And a box that fills the window: the shim's rect and the shim's
     innerWidth must say the same (a scrollbar apart), which they would not if
     the engine already gave the window in the page's px, as the one answer
     would then be divided twice.  (Its width, not its height: a phone's
     toolbar moves the height of the window and not of a fixed box.) */
  function right() {
    try {
      var host = document.body || de, p = document.createElement('div'), q = document.createElement('div');
      p.style.cssText = PROBE;
      q.style.cssText = PROBE.replace('width:100px;height:100px', 'width:100%;height:100%');
      host.appendChild(p);
      host.appendChild(q);
      var seen = raw.rect.call(p).width, said = p.getBoundingClientRect().width, fill = q.getBoundingClientRect();
      host.removeChild(p);
      host.removeChild(q);
      return Math.abs(seen - 100 * factor) < 1 && Math.abs(said - 100) < 1 &&
             Math.abs(fill.width - window.innerWidth) < 24;
    } catch (e) { return false; }
  }

  /* ---- putting a zoom in force, changing it, taking it out ---- */
  function engage(pct) {
    var first = shown === 100;
    factor = pct / 100;
    if (first) {
      install();
      observe();
      printOwn(true);
    }
    de.style.setProperty('--z', String(factor));
    de.style.zoom = String(factor);
    de.setAttribute('data-zoom', String(pct));
    shown = pct;
    if (first) {
      whole();
      if (!right()) { disengage(); broken = true; }
    }
  }
  function disengage() {
    unobserve();
    restore();
    printOwn(false);
    uninstall();
    de.style.removeProperty('zoom');
    de.style.removeProperty('--z');
    de.removeAttribute('data-zoom');
    if (!de.getAttribute('style')) de.removeAttribute('style');
    shown = 100;
    factor = 1;
  }

  /* WHERE THE PAGE WAS READ stays where it is on the screen when the step is
     taken: the element under the upper third of the window, out of anything
     fixed, is found before and put back after (the window's own scroll is in
     what is seen and scales with the page, so it cannot simply be kept; a
     scroller inside the page is in the page's px and keeps its place by
     itself).  Done with the engine's own functions and its own numbers, which
     are the same whether the shim is in or not. */
  function view() {
    var at = {y: read(raw.scrollY, window, 0), f: factor, el: null, top: 0};
    try {
      var list = raw.pointsAt.call(document, realWidth() / 2, Math.max(1, read(raw.innerHeight, window, 0) * 0.3));
      for (var i = 0; i < list.length && !at.el; i++) {
        var el = list[i], pinned = false;
        if (el === de || el === document.body) continue;
        for (var p = el; p && p !== document.body; p = p.parentElement) {
          var pos = getComputedStyle(p).position;
          if (pos === 'fixed' || pos === 'sticky') { pinned = true; break; }
        }
        if (!pinned) { at.el = el; at.top = raw.rect.call(el).top; }
      }
    } catch (e) {}
    return at;
  }
  function back(at) {
    try {
      if (at.el && at.el.isConnected) {
        var dy = raw.rect.call(at.el).top - at.top;
        if (dy) raw.scrollBy.call(window, 0, dy);
      } else if (at.y) {
        // no element to hold: the same place in the page's own px
        raw.scrollTo.call(window, 0, at.y / at.f * factor);
      }
    } catch (e) {}
  }

  /* ---- what is in force, made to be what the person chose ---- */
  function apply(fresh) {
    var want = clampTo(chosen(), realWidth());
    if (want !== 100 && !supported()) want = 100;
    if (want === shown) return false;
    var at = fresh ? view() : null;
    if (want === 100) disengage(); else engage(want);
    if (at) back(at);
    // a resize, as a window made smaller would give: whatever lays itself out
    // on resize lays itself out again in the page's new px
    if (fresh) { try { window.dispatchEvent(new Event('resize')); } catch (e) {} }
    return true;
  }
  // the listeners are told what changed, once
  function announce() {
    var now = shown + ':' + chosen();
    if (now === told) return;
    told = now;
    var detail = {zoom: shown, chosen: chosen(), factor: factor};
    try { document.dispatchEvent(new CustomEvent('parseh:zoom', {detail: detail})); } catch (e) {}
    listeners.slice().forEach(function (fn) { try { fn(shown, detail); } catch (e) {} });
  }

  /* ================================ the answers ================================ */
  // what is in force: what was chosen, as much of it as the window allows --
  // and nothing where this engine does not zoom the way this file knows
  function current() {
    var c = clampTo(chosen(), realWidth());
    return c !== 100 && !supported() ? 100 : c;
  }
  function can(dir) {
    if (!supported()) return UNSUPPORTED;
    var i = STEPS.indexOf(current()) + (dir > 0 ? 1 : -1);
    if (i < 0) return SMALLEST;
    if (i >= STEPS.length) return LARGEST;
    return fits(STEPS[i], realWidth()) ? true : NARROW;
  }
  function set(pct) {
    var n = snap(pct);
    if (n !== 100 && !supported()) return UNSUPPORTED;
    if (!fits(n, realWidth())) return NARROW;
    keep(n);
    apply(true);
    announce();
    return true;
  }
  window.ParsehZoom = {
    KEY: KEY,
    STEPS: Object.freeze ? Object.freeze(STEPS.slice()) : STEPS.slice(),
    MIN_WIDTH: MIN_WIDTH,
    // what the person chose, on this device; 100 where nothing was
    get: chosen,
    // what is in force: the chosen step, or the largest this window allows
    applied: current,
    // true once it is stored and in force, or the reason it was refused
    set: set,
    // one step from what is in force; true, or the reason there is none
    step: function (dir) {
      var why = can(dir);
      return why === true ? set(STEPS[STEPS.indexOf(current()) + (dir > 0 ? 1 : -1)]) : why;
    },
    // true, or the sentence that says why not (the gear greys the button with it)
    can: can,
    // the largest step this window allows
    allowedMax: function () { return allowedFor(realWidth()); },
    reset: function () { return set(100); },
    // fn(percent in force, {zoom, chosen, factor}) when either changes; the
    // same is the `parseh:zoom` event on the document.  Returns a function
    // that stops it
    onChange: function (fn) {
      if (typeof fn !== 'function') return function () {};
      listeners.push(fn);
      return function () { var i = listeners.indexOf(fn); if (i >= 0) listeners.splice(i, 1); };
    },
    // the multiplier in force, 1 when nothing is replaced
    factor: function () { return factor; },
    fits: fits
  };

  /* ---- what moves it from outside: another tab, a window made narrower, a
     page brought back from the browser's memory ---- */
  function follow() { apply(true); announce(); }
  window.addEventListener('storage', function (e) { if (e.key === null || e.key === KEY) follow(); });
  // the stored number is untouched by a window made too narrow: a window that
  // grows again gets the chosen size back
  window.addEventListener('resize', follow);
  window.addEventListener('orientationchange', follow);
  window.addEventListener('pageshow', function (e) { if (e.persisted) follow(); });

  // a page is opened at the size it was left at, before anything is drawn
  apply(false);
  told = shown + ':' + chosen();
})();

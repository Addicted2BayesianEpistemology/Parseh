// SPDX-License-Identifier: GPL-3.0-or-later
/* The Parseh guide -- the little script every page of it loads in <head>.

   It works the same opened straight from the disk (file://), served by
   Parseh under /guide/, and published on GitHub Pages: nothing here fetches
   a file (a file:// page may not), every address is worked out relative to
   the page (data-guide-root on <html> says how far up html-guide/ is), and
   what only the Parseh server can answer -- compiling the guide, the way
   back to the hub -- is offered only once the server has said it is Parseh
   (parseh() below).

   THE THEME IS THE TOOLBOX'S.  One choice for all of Parseh, `parseh_theme`
   in localStorage, the three palettes light, dark and sepia cycled by the ◐
   button, 'auto' before anything is picked -- lib/parseh.js's rule, restated
   here because a guide copied out of Parseh has no lib/parseh.js to load.
   Served by Parseh, the guide shares the origin and the choice with every
   other page.  The studio's sheet names its themes paper, sepia and dark;
   data-sheet on <html> carries that name for the article's stylesheet.

   Applied as soon as this file is parsed (it is in <head>), so the page
   never flashes the wrong palette; the rest waits for the document. */
(function () {
  'use strict';
  var KEY = 'parseh_theme';
  var ORDER = ['light', 'dark', 'sepia'];
  var GLYPH = { light: '○', dark: '●', sepia: '◐' };
  var SIDE_KEY = 'parseh_guide_side';        // the sidebar, open or closed
  var OPEN_KEY = 'parseh_guide_open';        // the sections opened by hand
  var NARROW = '(max-width: 900px)';
  var root = document.documentElement;

  function store(k, v) {
    try {
      if (v === undefined) return localStorage.getItem(k);
      if (v === null) localStorage.removeItem(k); else localStorage.setItem(k, v);
    } catch (e) { /* a private window: the choice lasts as long as the page */ }
    return null;
  }

  // ------------------------------------------------------------ the theme
  function themeGet() {
    var t = store(KEY);
    return (t === 'auto' || ORDER.indexOf(t) >= 0) ? t : 'auto';
  }
  function systemDark() {
    return !!(window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches);
  }
  function resolved() {
    var t = themeGet();
    return t === 'auto' ? (systemDark() ? 'dark' : 'light') : t;
  }
  function themeApply() {
    var t = themeGet(), now = resolved();
    if (t === 'auto') root.removeAttribute('data-theme');
    else root.setAttribute('data-theme', t);
    root.setAttribute('data-sheet', now === 'light' ? 'paper' : now);
    var next = ORDER[(ORDER.indexOf(now) + 1) % ORDER.length];
    var btns = document.querySelectorAll('[data-parseh-theme]');
    for (var i = 0; i < btns.length; i++) {
      btns[i].textContent = GLYPH[now];
      btns[i].title = 'theme: ' + now + (t === 'auto' ? ' (following the system)' : '') +
        ' — click for ' + next;
    }
  }
  function themeCycle() {
    store(KEY, ORDER[(ORDER.indexOf(resolved()) + 1) % ORDER.length]);
    themeApply();
  }
  themeApply();
  if (store(SIDE_KEY) === 'closed') root.setAttribute('data-side', 'closed');
  // a page that was not served -- opened from the disk -- sends no Referer,
  // which YouTube's player needs (videos(), below); said on <html> at once,
  // so the stylesheet can keep a player that will only say "Error 153" out
  // of sight until the card that replaces it is drawn
  var SERVED = /^https?:$/.test(location.protocol);
  if (!SERVED) root.setAttribute('data-guide-disk', '');

  // ------------------------------------------------------------ helpers
  function $(sel, el) { return (el || document).querySelector(sel); }
  function $$(sel, el) { return Array.prototype.slice.call((el || document).querySelectorAll(sel)); }
  function up() { return root.getAttribute('data-guide-root') || ''; }

  /* Was this page served by Parseh?  The address cannot say: Parseh puts
     the guide under /guide/, but so may any website that publishes it (a
     static host has no hub and no compile).  So the server is
     asked, once: GET __status beside the front page, which only Parseh
     answers, with {parseh: true} and the state of the compiled site.  A page
     not under /guide/ over http (the disk, GitHub Pages at /<repository>/)
     is not asked at all.  -> a promise of the status, or null. */
  var parsehAsked = null;
  function parseh() {
    if (!parsehAsked) {
      parsehAsked = (SERVED && /^\/guide\//.test(location.pathname))
        ? status(up() + '__status').then(function (st) {
            return st && st.parseh === true ? st : null;
          }, function () { return null; })
        : Promise.resolve(null);
    }
    return parsehAsked;
  }
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function narrow() { return !!(window.matchMedia && window.matchMedia(NARROW).matches); }

  // ------------------------------------------------------------ the sidebar
  function sideToggle() {
    var btn = $('[data-guide-side]');
    if (narrow()) {
      var open = !root.classList.contains('g-drawer');
      root.classList.toggle('g-drawer', open);
      var bd = $('.g-backdrop');
      if (bd) bd.hidden = !open;
      if (btn) btn.setAttribute('aria-expanded', open ? 'true' : 'false');
      if (open) { var here = $('.g-side .g-here') || $('.g-side .g-link'); if (here) here.focus({preventScroll: true}); }
      return;
    }
    var closed = root.getAttribute('data-side') !== 'closed';
    if (closed) root.setAttribute('data-side', 'closed'); else root.removeAttribute('data-side');
    store(SIDE_KEY, closed ? 'closed' : null);
    if (btn) btn.setAttribute('aria-expanded', closed ? 'false' : 'true');
  }
  function drawerClose() {
    root.classList.remove('g-drawer');
    var bd = $('.g-backdrop');
    if (bd) bd.hidden = true;
    var btn = $('[data-guide-side]');
    if (btn) btn.setAttribute('aria-expanded', narrow() ? 'false' : String(root.getAttribute('data-side') !== 'closed'));
  }

  /* The front page has no tree of its own (it is written by hand, and works
     before anything is compiled): it draws it from site/nav.js. */
  function drawNav(nav) {
    var box = $('#g-nav');
    if (!box || box.children.length) return;
    var base = up();
    function item(n) {
      if (n.c) {
        var head = n.u ? '<a class="g-link" href="' + esc(base + n.u) + '">' + esc(n.t) + '</a>'
                       : '<span class="g-sec-t">' + esc(n.t) + '</span>';
        return '<li class="g-sec"><details data-sec="' + esc(n.p || '') + '"><summary>' + head +
          '</summary><ul class="g-tree">' + n.c.map(item).join('') + '</ul></details></li>';
      }
      return '<li><a class="g-link" href="' + esc(base + n.u) + '">' + esc(n.t) + '</a></li>';
    }
    box.innerHTML = '<ul class="g-tree g-top-tree"><li><a class="g-link g-home g-here" aria-current="page" href="' +
      esc(base + 'index.html') + '">Home</a></li></ul><ul class="g-tree">' +
      nav.tree.map(item).join('') + '</ul>';
  }

  /* A section opened or closed by hand stays so on the next page; the
     section holding the page being read is always open. */
  function bindSections() {
    var opened = {};
    try { opened = JSON.parse(store(OPEN_KEY) || '{}') || {}; } catch (e) { opened = {}; }
    $$('.g-side details[data-sec]').forEach(function (d) {
      var key = d.getAttribute('data-sec');
      var holdsHere = !!$('.g-here', d);
      if (!holdsHere && opened[key] !== undefined) d.open = !!opened[key];
      d.addEventListener('toggle', function () {
        opened[key] = d.open;
        store(OPEN_KEY, JSON.stringify(opened));
      });
    });
  }

  // ------------------------------------------------------------ search
  /* The index is site/search-index.js, a script like nav.js, fetched the
     first time the box is used.  A page matches when every word typed is in
     it; its title counts most, its headings next, its text least. */
  var searchWaiting = null;
  function loadSearch(done) {
    if (window.GUIDE_SEARCH) return done();
    if (searchWaiting) { searchWaiting.push(done); return; }
    searchWaiting = [done];
    var s = document.createElement('script');
    s.src = up() + 'site/search-index.js';
    s.onload = s.onerror = function () {
      var waiting = searchWaiting;
      searchWaiting = null;
      waiting.forEach(function (fn) { fn(); });
    };
    document.head.appendChild(s);
  }
  function fold(s) {
    return String(s || '').normalize('NFKD').replace(/[\u0300-\u036f]/g, '')
      .replace(/[\u0130\u0131]/g, 'i').toLowerCase();
  }
  function search(q) {
    var words = fold(q).split(/\s+/).filter(Boolean);
    if (!words.length || !window.GUIDE_SEARCH) return [];
    var out = [];
    window.GUIDE_SEARCH.forEach(function (p) {
      var t = fold(p.t), h = fold((p.h || []).join(' ')), x = fold(p.x), d = fold(p.d);
      var score = 0;
      for (var i = 0; i < words.length; i++) {
        var w = words[i], s = 0;
        if (t.indexOf(w) >= 0) s += 10;
        if (h.indexOf(w) >= 0) s += 4;
        if (d.indexOf(w) >= 0) s += 2;
        if (x.indexOf(w) >= 0) s += 1;
        if (!s) return;
        score += s;
      }
      out.push({ p: p, score: score });
    });
    out.sort(function (a, b) { return b.score - a.score || a.p.t.localeCompare(b.p.t); });
    return out.slice(0, 12);
  }
  function snippet(text, q) {
    var words = fold(q).split(/\s+/).filter(Boolean);
    var f = fold(text), at = -1;
    for (var i = 0; i < words.length && at < 0; i++) at = f.indexOf(words[i]);
    if (at < 0) return '';
    var from = Math.max(0, at - 40), piece = text.slice(from, from + 150);
    var html = esc(piece);
    words.forEach(function (w) {
      if (w.length < 2) return;
      var re = new RegExp('(' + w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'ig');
      html = html.replace(re, '<mark>$1</mark>');
    });
    return (from ? '… ' : '') + html + ' …';
  }
  function bindSearch() {
    var input = $('[data-guide-search]');
    var list = $('.g-results');
    if (!input || !list) return;
    var hits = [], on = -1;
    function draw() {
      var q = input.value.trim();
      if (!q) { list.hidden = true; return; }
      loadSearch(function () {
        if (!window.GUIDE_SEARCH) {
          list.innerHTML = '<div class="g-r-none">The search needs the compiled guide (site/search-index.js), and it is not there yet.</div>';
          list.hidden = false;
          return;
        }
        hits = search(input.value.trim());
        on = hits.length ? 0 : -1;
        list.innerHTML = hits.length ? hits.map(function (h, i) {
          return '<a href="' + esc(up() + h.p.u) + '" role="option" class="' + (i === on ? 'on' : '') + '">' +
            '<span class="g-r-t">' + esc(h.p.t) + '</span>' +
            (h.p.s ? '<span class="g-r-s">' + esc(h.p.s) + '</span>' : '') +
            '<span class="g-r-x">' + snippet(h.p.x, input.value.trim()) + '</span></a>';
        }).join('') : '<div class="g-r-none">No page has all of these words.</div>';
        list.hidden = false;
      });
    }
    input.addEventListener('focus', function () { loadSearch(function () {}); });
    input.addEventListener('input', draw);
    input.addEventListener('keydown', function (e) {
      var links = $$('a', list);
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        if (!links.length) return;
        e.preventDefault();
        on = (on + (e.key === 'ArrowDown' ? 1 : -1) + links.length) % links.length;
        links.forEach(function (a, i) { a.classList.toggle('on', i === on); });
      } else if (e.key === 'Enter') {
        if (links[on >= 0 ? on : 0]) { e.preventDefault(); location.href = links[on >= 0 ? on : 0].href; }
      } else if (e.key === 'Escape') {
        input.value = ''; list.hidden = true;
      }
    });
    document.addEventListener('click', function (e) {
      if (!e.target.closest('.g-search')) list.hidden = true;
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === '/' && !/^(INPUT|TEXTAREA|SELECT)$/.test((document.activeElement || {}).tagName || '')) {
        e.preventDefault();
        if (narrow() && !root.classList.contains('g-drawer')) sideToggle();
        input.focus();
      }
    });
  }

  // ------------------------------------------------------------ copying code
  /* The exact source, line for line: every .g-line's text without its
     number.  The Clipboard API where the page may use it (a secure origin,
     and file:// is one), the old execCommand where it may not. */
  function codeText(block) {
    return $$('.g-line', block).map(function (line) {
      var copy = line.cloneNode(true);
      $$('.g-ln', copy).forEach(function (n) { n.remove(); });
      return copy.textContent;
    }).join('\n');
  }
  function copyText(text) {
    function fallback() {
      var ta = document.createElement('textarea');
      ta.value = text;
      ta.setAttribute('readonly', '');
      ta.style.position = 'fixed'; ta.style.top = '-1000px'; ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      var ok = false;
      try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
      ta.remove();
      return ok ? Promise.resolve() : Promise.reject(new Error('copy refused'));
    }
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text).catch(fallback);
    }
    return fallback();
  }
  function bindCopy() {
    document.addEventListener('click', function (e) {
      var btn = e.target.closest('.g-copy');
      if (!btn) return;
      var block = btn.closest('.g-code');
      copyText(codeText(block)).then(function () {
        btn.textContent = 'Copied'; btn.classList.add('done');
      }, function () {
        btn.textContent = 'Select and copy'; btn.classList.add('failed');
      }).then(function () {
        setTimeout(function () { btn.textContent = 'Copy'; btn.classList.remove('done', 'failed'); }, 1600);
      });
    });
  }

  // ------------------------------------------------------------ pictures, large
  function bindLightbox() {
    document.addEventListener('click', function (e) {
      var img = e.target.closest('.sheet img, .g-sheet img');
      if (!img || img.closest('a, button, .exercise, .g-lightbox, .g-qr')) return;
      var box = document.createElement('div');
      box.className = 'g-lightbox';
      box.setAttribute('role', 'dialog');
      box.setAttribute('aria-label', img.alt || 'picture');
      box.innerHTML = '<img alt=""><button type="button">Close ✕</button>';
      $('img', box).src = img.currentSrc || img.src;
      $('img', box).alt = img.alt || '';
      function close() { box.remove(); document.removeEventListener('keydown', key, true); }
      function key(ev) { if (ev.key === 'Escape') { ev.preventDefault(); close(); } }
      box.addEventListener('click', close);
      document.addEventListener('keydown', key, true);
      document.body.appendChild(box);
      $('button', box).focus();
    });
  }

  // ------------------------------------------------------------ a video, off the disk
  /* YOUTUBE PLAYS IN THE PAGE ONLY WHEN THE PAGE WAS SERVED.  Its embedded
     player refuses a page that sends no Referer -- "Video player
     configuration error", Error 153 -- and a page opened from the disk sends
     none.  So there each YouTube player becomes a card that opens the video
     on YouTube, at the clip's start, with its still, and one line under
     the figure saying that the player works when the guide is served.  Served (by
     Parseh, on the web) the players are left as they are.  Vimeo's player
     does play off the disk, and is kept. */
  function clockOf(s) {
    s = Math.max(0, parseInt(s, 10) || 0);
    var h = Math.floor(s / 3600), m = Math.floor(s / 60) % 60, r = s % 60;
    return (h ? h + ':' + (m < 10 ? '0' : '') : '') + m + ':' + (r < 10 ? '0' : '') + r;
  }
  function videos(scope) {
    if (SERVED) return;
    $$('iframe[src*="youtube-nocookie.com/embed/"], iframe[src*="youtube.com/embed/"]', scope).forEach(function (ifr) {
      var id = /\/embed\/([\w-]{11})/.exec(ifr.src);
      if (!id) return;
      var start = (/[?&]start=(\d+)/.exec(ifr.src) || [])[1] || '';
      var a = document.createElement('a');
      a.className = 'g-yt';
      a.href = 'https://www.youtube.com/watch?v=' + id[1] + (+start ? '&t=' + (+start) + 's' : '');
      a.target = '_blank';
      a.rel = 'noopener';
      a.title = 'Open the video on YouTube, in a new tab';
      // the words a narrow card leaves out are g-yt-long (guide.css): the
      // start time stays
      a.innerHTML = '<img alt="" src="https://i.ytimg.com/vi/' + id[1] + '/hqdefault.jpg">' +
        '<span class="g-yt-play" aria-hidden="true"></span>' +
        '<span class="g-yt-say"><span class="g-yt-long">Watch on </span>YouTube' +
        (+start ? ', <span class="g-yt-long">from </span>' + clockOf(start) : '') + ' ↗</span>';
      // no network: the card without its still, which still opens the video
      var still = $('img', a);
      still.addEventListener('error', function () { still.remove(); });
      ifr.replaceWith(a);
      // the line goes last in the figure, under the caption: the caption
      // says what the video is, this only where it plays
      var note = document.createElement('p');
      note.className = 'g-yt-note';
      note.textContent = 'The player works when the guide is served; from the disk, ' +
        'the video opens on YouTube.';
      var fig = a.closest('figure');
      if (fig) fig.appendChild(note);
      else a.parentNode.insertBefore(note, a.nextSibling);
    });
  }

  // ------------------------------------------------------------ this page's contents
  function bindToc() {
    var toc = $('.g-toc');
    if (!toc) return;
    if (narrow()) toc.open = false;
    var links = $$('a', toc);
    var heads = links.map(function (a) { return document.getElementById(decodeURIComponent(a.hash.slice(1))); });
    if (!('IntersectionObserver' in window)) return;
    var seen = new Map();
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) { seen.set(en.target, en.isIntersecting); });
      var k = heads.findIndex(function (h) { return h && seen.get(h); });
      links.forEach(function (a, i) { a.classList.toggle('on', i === k); });
    }, { rootMargin: '-48px 0px -60% 0px' });
    heads.forEach(function (h) { if (h) io.observe(h); });
  }

  // ------------------------------------------------------------ Parseh
  /* Served by Parseh, the bar gains the way back to the hub. */
  function bindLinks() {
    parseh().then(function (st) {
      if (!st) return;
      $$('.g-hub').forEach(function (a) { a.hidden = false; });
      loadActivity();
    });
  }
  /* SERVED BY PARSEH, THE GUIDE IS ONE OF ITS PAGES, and shows what the
     server is working on as every other page does: lib/activity.js, the
     pill in the corner -- a book being built, a backup being packed, this
     guide being compiled.  Asked for only then: off the disk, on GitHub
     Pages, there is no such list and no /lib/ to load it from. */
  function loadActivity() {
    if (window.ParsehActivity || $('script[data-guide-activity]')) return;
    var s = document.createElement('script');
    s.src = '/lib/activity.js';
    s.async = true;
    s.setAttribute('data-guide-activity', '');
    document.head.appendChild(s);
  }

  // ------------------------------------------------------------ compiling, from the page
  /* The front page, when it came from the Parseh server, asks whether the
     compiled site is there and up to date, and offers the button that
     compiles it (POST __compile, then __status until the job ends). */
  function status(url) {
    return fetch(url, { cache: 'no-store' }).then(function (r) {
      if (!r.ok) throw new Error(r.status + ' ' + r.statusText);
      return r.json();
    });
  }
  function bindCompile() {
    var box = $('[data-guide-compile]');
    if (!box) return;
    parseh().then(function (st) {
      if (st) compileBox(box, st);
      else if (!window.GUIDE_NAV) {
        box.className = 'g-notice';
        box.innerHTML = '<p><b>The guide has not been compiled yet.</b> Its pages are written in ' +
          '<code>html-guide/markdown/</code> and become web pages when they are compiled. Parseh’s ' +
          'installer compiles them every time it runs; and when Parseh is running, its <b>guide</b> ' +
          'button opens this page with a <b>Compile the guide</b> button on it.</p>';
        box.hidden = false;
      }
    });
  }
  function compileBox(box, first) {
    var base = up();
    var act = null;      // this page's entry on the activity list, while it compiles
    function show(st) {
      var job = st.state === 'running';
      if (st.built && !st.stale && !job && st.ok !== false) { box.hidden = true; return; }
      var say;
      if (job) say = '<p><b>Compiling the guide…</b></p>';
      else if (st.ok === false) say = '<p><b>The last compile failed.</b> What it said is below.</p>';
      else if (!st.built) say = '<p><b>The guide has not been compiled yet.</b> Its pages are written in ' +
        '<code>html-guide/markdown/</code>; compiling turns them into these web pages.</p>';
      else say = '<p><b>The guide was compiled from older pages.</b> Compile it again to see the newest.</p>';
      var log = (st.log || []).slice(-40).join('\n');
      box.className = 'g-notice' + (st.ok === false ? ' g-bad' : '');
      box.innerHTML = say + '<p><button type="button" data-compile' + (job ? ' disabled' : '') + '>' +
        (job ? 'Compiling…' : (st.built ? 'Compile the guide again' : 'Compile the guide')) + '</button></p>' +
        (log && (job || st.ok === false) ? '<pre>' + esc(log) + '</pre>' : '');
      box.hidden = false;
      var b = $('[data-compile]', box);
      if (b) b.addEventListener('click', start);
    }
    function poll() {
      status(base + '__status').then(function (st) {
        show(st);
        if (st.state === 'running') { setTimeout(poll, 700); return; }
        if (act) { act.end(!!st.ok); act = null; }
        if (st.ok) {
          box.className = 'g-notice g-ok';
          box.innerHTML = '<p><b>Compiled.</b> Opening the new pages…</p>';
          setTimeout(function () { location.reload(); }, 400);
        } else if (st.built) {
          // a compile that ends with errors still writes every page it can:
          // open them too -- the reloaded page says again that it failed,
          // with what it said, now beside the list of pages
          box.className = 'g-notice g-bad';
          box.innerHTML = '<p><b>The compile ended with errors.</b> Opening the pages it wrote…</p>';
          setTimeout(function () { location.reload(); }, 400);
        }
      }).catch(function (e) {
        // no answer: the entry is let go, not left saying "Compiling" for
        // a compile this page can no longer follow
        if (act) { act.end(false); act = null; }
        box.className = 'g-notice g-bad';
        box.innerHTML = '<p>The server did not answer: ' + esc(e.message) + '</p>';
        box.hidden = false;
      });
    }
    function start() {
      // on the activity list at once, as this page's own work; the answer
      // names the server's entry for the compile (the one already running,
      // when that is the answer), which this one then is -- shown once.  The
      // hub and every other page hear of it from that entry.
      var A = window.ParsehActivity;
      if (A && !act) act = A.local('Compiling the guide');
      var b = $('[data-compile]', box);
      if (b) { b.disabled = true; b.textContent = 'Compiling…'; }
      fetch(base + '__compile', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' })
        .then(function (r) { return r.json(); })
        .then(function (j) { if (act) act.adopt(j.activity); poll(); })
        .catch(function (e) {
          if (act) { act.end(false); act = null; }
          box.className = 'g-notice g-bad';
          box.innerHTML = '<p>The compile could not start: ' + esc(e.message) + '</p>';
        });
    }
    show(first);
  }

  /* The front page's list of what is in the guide, from nav.js. */
  function drawContents() {
    var box = $('[data-guide-contents]');
    var nav = window.GUIDE_NAV;
    if (!box || !nav) return;
    function item(n) {
      var head = n.u ? '<a href="' + esc(up() + n.u) + '">' + esc(n.t) + '</a>' : esc(n.t);
      return '<li>' + head + (n.c && n.c.length ? '<ul class="g-contents">' + n.c.map(item).join('') + '</ul>' : '') + '</li>';
    }
    box.innerHTML = '<ul class="g-contents">' + nav.tree.map(item).join('') + '</ul>';
    box.hidden = false;
  }

  // ------------------------------------------------------------ the page's own
  function init() {
    themeApply();
    var nav = window.GUIDE_NAV;
    if (nav) drawNav(nav);
    else if ($('#g-nav') && !$('#g-nav').children.length) {
      $('#g-nav').innerHTML = '<p class="g-nav-empty">The list of pages appears once the guide is compiled.</p>';
    }
    bindSections();
    $$('[data-parseh-theme]').forEach(function (b) { b.addEventListener('click', themeCycle); });
    $$('[data-guide-side]').forEach(function (b) {
      b.addEventListener('click', sideToggle);
      b.setAttribute('aria-expanded', narrow() ? 'false' : String(root.getAttribute('data-side') !== 'closed'));
    });
    $$('[data-guide-close]').forEach(function (b) { b.addEventListener('click', drawerClose); });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && root.classList.contains('g-drawer')) drawerClose();
    });
    if (window.matchMedia) {
      var mq = window.matchMedia(NARROW);
      var follow = function () { if (!mq.matches) drawerClose(); };
      if (mq.addEventListener) mq.addEventListener('change', follow);
      var sys = window.matchMedia('(prefers-color-scheme: dark)');
      var again = function () { if (themeGet() === 'auto') themeApply(); };
      if (sys.addEventListener) sys.addEventListener('change', again);
    }
    bindSearch();
    bindCopy();
    bindLightbox();
    bindToc();
    bindLinks();
    drawContents();
    bindCompile();
    // the article: the studio's exercises (app.js, loaded on a page that has
    // some) and its maths (mathjax.js) -- bindExercises draws the maths too
    var article = $('.g-article');
    // before the studio's script binds the article: an exercise's card
    // copied for the enlarged view copies the video's card, not its player
    videos(document);
    if (article) {
      if (typeof window.bindExercises === 'function') window.bindExercises(article);
      else if (window.ParsehMath) window.ParsehMath.typeset(article);
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();

  window.Guide = { theme: { get: themeGet, apply: themeApply, cycle: themeCycle, resolved: resolved },
                   copyText: copyText, codeText: codeText, search: search, toggleSide: sideToggle };
})();

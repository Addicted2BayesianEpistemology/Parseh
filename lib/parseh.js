// SPDX-License-Identifier: GPL-3.0-or-later
/* Parseh — the little shared script: the theme, the language preference,
   the browser or mobile mode, a toast, the clipboard, the stop button.
   Served at /lib/parseh.js; loaded early in <head> so the theme (and the
   mode) is on the page before it paints.

   Theme: ONE preference for the whole toolbox, `parseh_theme` in
   localStorage, applied as data-theme on <html>.  The button cycles the
   three palettes -- light, dark, and the sepia paper the studio's reading
   sheet has always had.  'auto' is a fourth value, but not a step in the
   cycle: it is the state before anything has been picked, when no
   attribute is set and the stylesheet follows the system.  The button then
   shows whichever palette the system resolved to, so the first click always
   changes something.  The older per-tool keys (bk_theme, yt_theme) are read
   once as a migration and never written again. */
(function () {
  'use strict';
  var KEY = 'parseh_theme';
  var ORDER = ['light', 'dark', 'sepia'];
  var GLYPH = { light: '○', dark: '●', sepia: '◐' };

  function get() {
    var t = null;
    try { t = localStorage.getItem(KEY); } catch (e) {}
    if (t !== 'auto' && ORDER.indexOf(t) < 0) {
      t = 'auto';
      try {
        var old = localStorage.getItem('yt_theme') || localStorage.getItem('bk_theme');
        if (old === 'light' || old === 'dark') t = old;
      } catch (e) {}
    }
    return t;
  }
  function systemDark() {
    return !!(window.matchMedia &&
      window.matchMedia('(prefers-color-scheme: dark)').matches);
  }
  /* the palette actually on screen: 'auto' resolves to whichever of light
     and dark the stylesheet's media query picked */
  function resolved() {
    var t = get();
    return t === 'auto' ? (systemDark() ? 'dark' : 'light') : t;
  }
  function apply() {
    var t = get(), now = resolved();
    if (t === 'auto') document.documentElement.removeAttribute('data-theme');
    else document.documentElement.setAttribute('data-theme', t);
    var next = ORDER[(ORDER.indexOf(now) + 1) % ORDER.length];
    var btns = document.querySelectorAll('[data-parseh-theme]');
    for (var i = 0; i < btns.length; i++) {
      btns[i].textContent = GLYPH[now];
      btns[i].title = 'theme: ' + now +
        (t === 'auto' ? ' (following the system)' : '') + ' — click for ' + next;
    }
  }
  function set(t) {
    try { localStorage.setItem(KEY, t); } catch (e) {}
    apply();
  }
  function cycle() { set(ORDER[(ORDER.indexOf(resolved()) + 1) % ORDER.length]); }
  /* sepia is a light paper: only 'dark' is night */
  function isDark() { return resolved() === 'dark'; }

  /* ---- the mode: browser or mobile ----
     ONE switch for the whole toolbox, set from the hub's top bar.  In the
     browser mode every page is what it has always been, editing and all.
     The mobile mode is a second set of pages made to be READ on a phone --
     streamlined, and without a single editing control on them.  It is NOT
     the phone adjustments the pages already make (the bar that hides on a
     scroll, the layouts under 560px): those follow the width of the screen
     and go on doing so in either mode.  This follows a choice.

     Stored as `parseh_mode` in localStorage, 'browser' or 'mobile', where
     nothing stored means browser; and mirrored in a cookie of the same name,
     because the server and the studio's and the exercises' pages (which do
     not load this script) have to be able to read it too.  When storage
     holds nothing -- blocked, or never written on this origin -- the cookie
     answers.  It is put on <html> as data-mode as soon as this script is
     parsed, as the theme is, so a page's stylesheet has switched layouts
     before the first paint.

     A page that HAS a mobile version is listed in MOBILE_PAGES, and
     route(url) says where a link to url leads in the mode the toolbox is
     in: to the mobile version when there is one and the mode is mobile,
     and to url itself otherwise.  The browser page is always the fallback,
     so a page nobody has written a mobile version of yet simply opens as it
     is.  On a page that is itself a mobile page (<body data-mobile-page>)
     every link is routed that way.  Nothing is refused, in either mode: a
     browser page reached by its address works as it always has.  The design
     and the way to add a mobile page are in docs/mobile.md. */
  var MODE_KEY = 'parseh_mode';
  var MODES = ['browser', 'mobile'];
  /* {match: a RegExp over the whole path, to: its mobile path}; `to` is
     handed to String.replace, so it may say $1 for a part of the match (or
     be a function), and the query and the fragment are carried over */
  var MOBILE_PAGES = [
    // the hub is its own mobile version: the one page carries both layouts
    { match: /^\/(index\.html)?$/, to: '/' },
    // the book library is a static page (make_index.py): its mobile version is
    // a page of its own, written by the server on every request (lib/mobile.py)
    { match: /^\/books\/(index\.html)?$/, to: '/m/books/' },
    // a book's reader is its own mobile version: every reader, however old,
    // gets the mobile layer from this script (the loader at the end of this
    // file), so nothing has to be built again
    { match: /^(\/books\/(?:[^\/]+\/){1,2}reader\/)(index\.html)?$/, to: '$1' },
    // the exercise decks, a deck, studying it and cramming it: each page
    // carries both layouts (markdown/app/templates, static/mobile.css)
    { match: /^\/exercises\/(.*)$/, to: '/exercises/$1' },
    // the licences, which carry both layouts in one column (lib/notices.py)
    { match: /^\/licences\/$/, to: '/licences/' }
  ];
  function modeCookie() {
    var m = null;
    try { m = /(?:^|;\s*)parseh_mode=(browser|mobile)(?:;|$)/.exec(document.cookie || ''); }
    catch (e) {}
    return m ? m[1] : null;
  }
  function modeGet() {
    var m = null;
    try { m = localStorage.getItem(MODE_KEY); } catch (e) {}
    if (MODES.indexOf(m) < 0) m = modeCookie();
    return m === 'mobile' ? 'mobile' : 'browser';
  }
  function isMobile() { return modeGet() === 'mobile'; }
  function modeCookieSet(m) {
    // a year, for the whole site; Lax, because it only ever travels with
    // the toolbox's own pages; not Secure, since serve.py can speak plain
    // http (--http, or a Windows machine without OpenSSL)
    try { document.cookie = MODE_KEY + '=' + m + '; Path=/; SameSite=Lax; Max-Age=31536000'; }
    catch (e) {}
  }
  var modeFns = [], modeShown = null;
  function modeApply() {
    var m = modeGet();
    document.documentElement.setAttribute('data-mode', m);
    // the server's copy follows whatever this page found, so the two never
    // disagree for longer than one page load
    if (modeCookie() !== m) modeCookieSet(m);
    var btns = document.querySelectorAll('[data-parseh-mode]');
    for (var i = 0; i < btns.length; i++)
      btns[i].setAttribute('aria-pressed',
                           btns[i].getAttribute('data-parseh-mode') === m ? 'true' : 'false');
    if (m !== 'mobile') unrouteLinks();
    // the switch may just have put a sideways chip row on the screen
    langReveal(false);
    var was = modeShown;
    modeShown = m;
    if (was !== null && was !== m) {
      for (var j = 0; j < modeFns.length; j++) { try { modeFns[j](m); } catch (e) {} }
      // A PAGE THAT IS ONLY A MOBILE VERSION (/m/books/) has nothing of its
      // own to show in the browser mode: switched there, here or in another
      // tab, it goes to the page it is the mobile version of, which its body
      // names in data-browser-page.  Only on a switch and never at load --
      // an address opened in the browser mode opens as it is -- and never the
      // other way round: a browser page may hold somebody's unsaved work.
      var back = m === 'browser' && document.body &&
                 document.body.getAttribute('data-browser-page');
      if (back) location.replace(back);
    }
  }
  function modeSet(m) {
    if (MODES.indexOf(m) < 0) return;
    try { localStorage.setItem(MODE_KEY, m); } catch (e) {}
    modeCookieSet(m);
    modeApply();
  }
  /* fn(mode) after every change of the mode on this page: a click here, or
     a switch made in another tab (the storage event); gives back a function
     that takes fn off again */
  function modeOnChange(fn) {
    modeFns.push(fn);
    return function () { var k = modeFns.indexOf(fn); if (k >= 0) modeFns.splice(k, 1); };
  }
  function modeRoute(url) {
    if (modeGet() !== 'mobile' || !/^https?:$/.test(location.protocol)) return url;
    var u;
    try { u = new URL(url, location.href); } catch (e) { return url; }
    if (u.origin !== location.origin) return url;
    for (var i = 0; i < MOBILE_PAGES.length; i++) {
      var p = MOBILE_PAGES[i];
      if (!p.match.test(u.pathname)) continue;
      return u.pathname.replace(p.match, p.to) + u.search + u.hash;
    }
    return url;
  }
  /* A link on a mobile page, followed in the mobile mode, goes where
     route() says.  The href itself is rewritten, in the capture phase and
     before the browser acts on the click, instead of the click being
     cancelled and the page moved by hand: that way everything a browser
     does with a link -- ctrl- or cmd-click into a new tab, shift-click into
     a window, a middle click, a long press's "open in new tab", a
     target=_blank -- it does with the mobile address, and none of it has to
     be imitated here.  The address the page was written with is kept in
     data-parseh-href and put back when the mode goes back to browser.  A
     link that must open the browser page whatever the mode says so with
     data-no-route; a download is never routed. */
  function routeLink(e) {
    if (!document.body || !document.body.hasAttribute('data-mobile-page')) return;
    if (modeGet() !== 'mobile') return;
    var a = e.target && e.target.closest && e.target.closest('a[href]');
    if (!a || a.hasAttribute('download') || a.hasAttribute('data-no-route')) return;
    var own = a.getAttribute('data-parseh-href') || a.getAttribute('href');
    if (!own || own.charAt(0) === '#') return;
    var to = modeRoute(own);
    if (to === own) return;
    a.setAttribute('data-parseh-href', own);
    a.setAttribute('href', to);
  }
  function unrouteLinks() {
    var as = document.querySelectorAll('a[data-parseh-href]');
    for (var i = 0; i < as.length; i++) {
      as[i].setAttribute('href', as[i].getAttribute('data-parseh-href'));
      as[i].removeAttribute('data-parseh-href');
    }
  }
  document.addEventListener('click', routeLink, true);
  document.addEventListener('auxclick', routeLink, true);
  document.addEventListener('contextmenu', routeLink, true);
  // a switch made in another tab, and a page brought back from the
  // back-forward cache, which ran none of its script on the way back
  window.addEventListener('storage', function (e) {
    if (e.key === MODE_KEY || e.key === null) modeApply();
  });
  window.addEventListener('pageshow', function (e) { if (e.persisted) modeApply(); });
  /* The toggle: any button with data-parseh-mode="browser|mobile".  The
     pressed look comes from <html data-mode> in the stylesheet, so it is
     right from the first paint; aria-pressed is kept for the screen reader.
     The button clicked may belong to the layout the switch just hid: the
     focus then goes to its twin in the layout now on the screen. */
  function modeClick(e) {
    var b = e.target && e.target.closest && e.target.closest('[data-parseh-mode]');
    if (!b) return;
    var m = b.getAttribute('data-parseh-mode'), had = document.activeElement === b;
    modeSet(m);
    if (!had || b.offsetParent) return;
    var twins = document.querySelectorAll('[data-parseh-mode="' + m + '"]');
    for (var i = 0; i < twins.length; i++)
      if (twins[i].offsetParent) { twins[i].focus(); break; }
  }

  /* ---- a toast ---- */
  var toastTimer = null;
  function toast(msg, isErr) {
    var t = document.getElementById('parseh-toast');
    if (!t) {
      t = document.createElement('div');
      t.id = 'parseh-toast';
      (document.body || document.documentElement).appendChild(t);
    }
    t.textContent = msg;
    t.classList.toggle('err', !!isErr);
    // force a reflow so a toast right after the last one animates again
    void t.offsetWidth;
    t.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { t.classList.remove('show'); },
                            isErr ? 4200 : 2000);
  }

  /* ---- taking something off the shelf ----
     The studio has had this since it had a library: an x on the card, a
     question, and the document is gone.  A book and a video get the same
     gesture from the same place, because the card is where a person looks
     to manage a library and the reading page is where they look to read --
     a red button in the reader would be a red button under the pointer of
     somebody turning a page.

     One difference, and it is the content's: a note is a page somebody can
     write again, and a reading edition is weeks of glossing with a
     recording beside it that may exist nowhere else.  So this does not
     remove anything.  The server moves the directory to books/.trash/ or
     videos/.trash/ -- a dot directory, so every walker here already skips
     it and the thing is off the shelf the moment it lands -- and says where
     it went.  The question below says so too, because a person about to
     press a red button should be told what it does, not reassured.

     The card carries the address: data-del is what to POST to, data-what is
     what to call it in the question.  Delegated and in the capture phase,
     because the x lives inside the card's own <a> and a click that reached
     it would follow the link instead. */
  function cardDelete(e) {
    var b = e.target && e.target.closest && e.target.closest('[data-del]');
    if (!b) return;
    e.preventDefault();
    e.stopPropagation();
    var url = b.getAttribute('data-del');
    var what = b.getAttribute('data-what') || 'this';
    var body = b.getAttribute('data-body') || '';
    if (!window.confirm('Take \u201c' + what + '\u201d off the shelf?\n\n'
                        + 'It is moved to the trash beside the others, not '
                        + 'deleted: nothing is lost, and it stops being part '
                        + 'of the library.')) return;
    b.disabled = true;
    fetch(url, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: body || '{}'
    }).then(function (r) { return r.json(); }).then(function (j) {
      if (!j || !j.ok) throw new Error((j && j.error) || 'it was refused');
      /* j.warn means it was moved but something after it did not run --
         the library page, which is about to reload, is the stale one.  Say
         that instead of the cheerful line, and leave it up longer. */
      if (j.warn) { toast(j.warn, true); return; }
      toast(what + ' \u2192 ' + (j.trash || 'the trash'));
      setTimeout(function () { location.reload(); }, 900);
    }).catch(function (err) {
      b.disabled = false;
      toast((err && err.message) || String(err), true);
    });
  }

  /* ---- building a book from its card ----
     The card's build button -- and a card whose book has no reader yet, which
     is all button -- POSTs data-build, the book's own __build, and the server
     runs ./build.sh as a job (lib/bookbuild.py).  buildBook polls the job,
     says the build's last line as it goes, and calls back when it ends: the
     library page reloads, so the card shows what the reader now says; the
     reader page marks its PDF current.  A book already building answers 409
     with that build, which is polled the same.

       buildBook(url, what, opts)   what: the subject of the page's own
                                    messages ("<what> — building…"): the
                                    card's title, the reader's "the PDF"
         opts.book     the book's name, for the activity list's label
         opts.what     'html' for the reader alone, else the PDF
         opts.button, opts.say, opts.done, opts.failed */
  function cardBuild(e) {
    if (e.target && e.target.closest && e.target.closest('[data-del]')) return;
    var b = e.target && e.target.closest && e.target.closest('[data-build]');
    if (!b) return;
    e.preventDefault();
    e.stopPropagation();
    var name = b.getAttribute('data-what') || '';
    buildBook(b.getAttribute('data-build'), name || 'the book', {
      book: name,
      button: b.tagName === 'BUTTON' ? b : null,
      done: function () { setTimeout(function () { location.reload(); }, 900); }
    });
  }
  /* WHY A BUILD FAILED, in its own words.  The last lines of a failed build
     are whatever TeX printed last -- "Type X to quit or <RETURN> to proceed"
     -- and the line that says what went wrong is higher up: build.sh prints
     TeX's first error under "PDF FAILED", and the Python build does the
     same.  So: that error, after the line naming what failed; the line naming
     it alone where there is no TeX error; and only then the last two. */
  function buildWhy(log) {
    log = (log || []).map(function (l) { return String(l).trim(); }).filter(Boolean);
    var err = log.filter(function (l) { return l.charAt(0) === '!'; })[0];
    var failed = log.filter(function (l) { return /FAILED|could not run|no lualatex/i.test(l); })[0];
    if (err) return (failed ? failed.replace(/\s*--.*$/, '') + ': ' : '') + err;
    return failed || log.slice(-2).join(' / ') || 'the server log says why';
  }
  function buildBook(url, what, opts) {
    opts = opts || {};
    var button = opts.button || null;
    var say = opts.say || toast;
    if (button) button.disabled = true;
    // on the activity list at once (lib/activity.js), before the server's
    // own entry for the build has been asked for; the answer names that
    // entry, and this page's is then the same one, shown once.  Its label
    // names the book as that entry will (serve.py named(): quoted, and
    // isolated for a title in another direction), so nothing moves when the
    // entry takes over.  `what` is no name for it: the reader and the
    // new-book page say "the PDF" and "the reader" in their own messages,
    // and the label was "Building the PDF of the PDF".  A caller that does
    // not pass the book's name -- a reader built before opts.book -- gets
    // the label without one, until the server's entry names it.
    var verb = opts.what === 'html' ? 'Rebuilding the reader' : 'Building the PDF';
    var act = working(opts.book ? verb + ' of \u201c\u2068' + opts.book + '\u2069\u201d' : verb + '\u2026');
    function fail(err) {
      act.end(false);
      if (button) button.disabled = false;
      say((err && err.message) || String(err), true);
    }
    function poll() {
      fetch(url + '/status', {cache: 'no-store'}).then(function (r) { return r.json(); })
        .then(function (j) {
          if (j.state === 'running') {
            var last = (j.log || []).slice(-1)[0];
            say(what + ' — ' + (last || 'building…'));
            setTimeout(poll, 1500);
            return;
          }
          act.end(j.state === 'done');
          if (button) button.disabled = false;
          if (j.state === 'done') {
            say(what + ': built');
            if (opts.done) opts.done(j);
          } else {
            say(what + ': the build failed — ' + buildWhy(j.log), true);
            if (opts.failed) opts.failed(j);
          }
        }).catch(fail);
    }
    fetch(url, {method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({what: opts.what || 'pdf'})})
      .then(function (r) { return r.json().then(function (j) { return {status: r.status, j: j}; }); })
      .then(function (res) {
        if (!res.j.ok && res.status !== 409) throw new Error(res.j.error || 'it was refused');
        act.adopt(res.j.activity);
        say(what + ' — ' + (res.status === 409 ? 'already building…' : 'building…'));
        setTimeout(poll, 1200);
      }).catch(fail);
  }

  /* THIS PAGE'S OWN ENTRY on the activity list (lib/activity.js, loaded
     below), for work started here: shown at once, ended by the caller.
     Where the list is not there -- a page opened off the disk, or before
     the script has arrived -- the work goes on without it, and the handle
     answers every call with nothing. */
  function working(label, opts) {
    var A = window.ParsehActivity;
    if (A) return A.local(label, opts);
    return {job: '', url: function (u) { return u; }, end: function () {},
            progress: function () {}, set: function () {}, adopt: function () {}};
  }

  /* ---- the clipboard ----
     navigator.clipboard needs a secure context, which every page of the
     toolbox now has (https); the execCommand path is only a fallback for
     an old browser. */
  function shorten(s) { return s.length > 48 ? s.slice(0, 48) + '…' : s; }
  function copy(text, raw) {
    text = String(text == null ? '' : text);
    /* A word, a slug, an id -- what this was written for -- are better for
       having their whitespace squeezed.  A shell script and a ~15,000
       character PROMPT.md are destroyed by it: both add pages hand over
       heredoc-bearing sh and fenced Markdown, and every one of them arrived
       as a single unrunnable line.  `raw` asks for the text exactly as it
       stands; every caller that passes nothing keeps the old behaviour, and
       BOTH paths keep the toast and the execCommand fallback below (which
       preserves whitespace natively, and which a private clipboard call in
       the pages would have thrown away). */
    if (!raw) text = text.replace(/\s+/g, ' ').trim();
    if (!text) return Promise.resolve(false);
    var p = (navigator.clipboard && navigator.clipboard.writeText)
      ? navigator.clipboard.writeText(text)
      : Promise.reject(new Error('no clipboard API'));
    return p.then(function () {
      toast('copied: ' + shorten(text));
      return true;
    }).catch(function () {
      try {
        var ta = document.createElement('textarea');
        ta.value = text;
        ta.setAttribute('readonly', '');
        ta.style.cssText = 'position:fixed;top:0;left:0;opacity:0';
        document.body.appendChild(ta);
        ta.select();
        var ok = document.execCommand('copy');
        document.body.removeChild(ta);
        if (ok) { toast('copied: ' + shorten(text)); return true; }
      } catch (e) {}
      toast('clipboard unavailable', true);
      return false;
    });
  }

  /* ---- shift held: the readers show their copy affordance ---- */
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Shift') document.body.classList.add('shiftdown');
  });
  document.addEventListener('keyup', function (e) {
    if (!e.shiftKey) document.body.classList.remove('shiftdown');
  });
  window.addEventListener('blur', function () {
    document.body.classList.remove('shiftdown');
  });

  /* ---- stopping the server, from any page ----
     NOT WHILE IT IS WORKING, unless that is what is meant: a build, a
     restore or an upload still running is cut off by the stop, so the
     question names them first -- even where the page has already asked
     its own question (the reader's "really stop?", which passes `silent`),
     because that one was about stopping and this one is about the work.
     Asked of the activity list (/__activity); a server that does not
     answer it gets the plain question. */
  function stillRunning() {
    return fetch('/__activity', {cache: 'no-store'})
      .then(function (r) { return r.ok ? r.json() : {}; })
      .then(function (j) { return (j && j.running) || []; })
      .catch(function () { return []; });
  }
  function stopQuestion(list) {
    if (!list.length) return 'Stop the Parseh server?';
    var names = list.slice(0, 5).map(function (e) { return '  \u2022 ' + e.label; });
    if (list.length > 5) names.push('  \u2026 and ' + (list.length - 5) + ' more');
    return (list.length === 1 ? '1 task is' : list.length + ' tasks are') +
      ' still running:\n\n' + names.join('\n') + '\n\nStopping the server now cuts ' +
      (list.length === 1 ? 'it' : 'them') + ' off. Stop the Parseh server anyway?';
  }
  function stopServer(opts) {
    opts = opts || {};
    stillRunning().then(function (list) {
      if ((list.length || !opts.silent) && !confirm(stopQuestion(list))) return;
      stopNow(opts);
    });
  }
  function stopNow(opts) {
    if (opts.before) { try { opts.before(); } catch (e) {} }
    fetch('/__shutdown', { method: 'POST' }).catch(function () {}).then(function () {
      document.body.className = '';
      document.body.style.cssText = '';
      document.body.innerHTML =
        '<div style="max-width:640px;margin:22vh auto;text-align:center;' +
        'font:16px/1.6 -apple-system,sans-serif;color:var(--dim)">' +
        '<p style="font-size:19px;color:var(--ink)">Parseh stopped.</p>' +
        '<p>Start it again with <code>./serve.sh</code> in the project ' +
        'directory and reload this page.</p></div>';
    });
  }

  /* ---- text size and margins ----
     The studio has sliders for its sheet; this is the same idea for the
     readers, as one panel both can open: each caller names its fields
     (label, range, default, the CSS custom property it drives) and the
     localStorage key its values live under.  Applying a value is setting
     the property on <html>, so the stylesheet does the rest. */
  function typo(opts) {
    var key = opts.key, fields = opts.fields || [], btn = opts.button;
    var root = document.documentElement;
    function defaults() {
      var d = {};
      fields.forEach(function (f) { d[f.name] = f.def; });
      return d;
    }
    function load() {
      var d = defaults();
      try {
        var s = JSON.parse(localStorage.getItem(key) || '{}');
        fields.forEach(function (f) {
          var v = s[f.name];
          if (typeof v === 'number' && isFinite(v))
            d[f.name] = Math.min(f.max, Math.max(f.min, v));
        });
      } catch (e) {}
      return d;
    }
    var vals = load();
    function save() {
      // Preserve language-specific fields when another language saves its panel.
      var saved = {};
      try { saved = JSON.parse(localStorage.getItem(key) || '{}'); } catch (e) {}
      try { localStorage.setItem(key, JSON.stringify(Object.assign({}, saved, vals))); }
      catch (e) {}
    }
    function fmt(f, v) {
      if (f.unit === 'px') return (Math.round(v * 10) / 10) + 'px';
      return (Math.round(v * 100) / 100) + (f.unit || '');
    }
    function apply() {
      fields.forEach(function (f) {
        if (!f.prop) return;
        var v = vals[f.name];
        root.style.setProperty(f.prop, f.cssUnit ? v + f.cssUnit : (f.unit === 'px' ? v + 'px' : String(v)));
      });
      if (opts.onChange) { try { opts.onChange(vals); } catch (e) {} }
    }
    apply();
    var api = {
      get: function () { return vals; },
      set: function (name, v) {
        var field = fields.find(function (f) { return f.name === name; });
        if (!field || typeof v !== 'number' || !isFinite(v)) return;
        vals[name] = Math.min(field.max, Math.max(field.min, v));
        save(); apply(); if (btn) refresh();
      },
      reset: function () { vals = defaults(); save(); apply(); if (btn) refresh(); }
    };
    if (!btn) return api;

    var panel = document.createElement('div');
    panel.className = 'parseh-typo';
    panel.hidden = true;
    panel.setAttribute('dir', 'ltr');
    var h = '<div class="thead">text &amp; margins<span class="sp"></span>' +
            '<button type="button" class="tclose" title="close (Esc)">\u2715</button></div>';
    fields.forEach(function (f) {
      h += '<div class="trow"><label for="st-' + f.name + '">' + f.label + '</label>' +
           '<input type="range" id="st-' + f.name + '" data-f="' + f.name + '" min="' + f.min +
           '" max="' + f.max + '" step="' + f.step + '"><output data-o="' + f.name + '"></output></div>';
    });
    h += '<div class="tfoot"><span class="hint">remembered in this browser</span>' +
         '<span class="sp"></span><button type="button" class="treset">reset</button></div>';
    panel.innerHTML = h;
    document.body.appendChild(panel);
    function refresh() {
      fields.forEach(function (f) {
        panel.querySelector('[data-f="' + f.name + '"]').value = vals[f.name];
        panel.querySelector('[data-o="' + f.name + '"]').textContent = fmt(f, vals[f.name]);
      });
    }
    panel.addEventListener('input', function (e) {
      var name = e.target.getAttribute('data-f');
      if (!name) return;
      vals[name] = parseFloat(e.target.value);
      save(); apply(); refresh();
    });
    panel.querySelector('.treset').addEventListener('click', api.reset);
    function place() {
      var r = btn.getBoundingClientRect();
      var vw = document.documentElement.clientWidth || window.innerWidth;
      panel.style.top = (r.bottom + 6) + 'px';
      panel.style.left = Math.max(8, Math.min(r.left, vw - panel.offsetWidth - 8)) + 'px';
    }
    function open() { refresh(); panel.hidden = false; place(); btn.classList.add('on'); }
    function close() { panel.hidden = true; btn.classList.remove('on'); }
    panel.querySelector('.tclose').addEventListener('click', close);
    btn.addEventListener('click', function () { if (panel.hidden) open(); else close(); });
    document.addEventListener('click', function (e) {
      if (panel.hidden || panel.contains(e.target) || btn.contains(e.target)) return;
      close();
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && !panel.hidden) close();
    });
    window.addEventListener('resize', function () { if (!panel.hidden) place(); });
    refresh();
    return api;
  }

  // CJK controls share defaults and units between the two readers.
  function readingFields(lang) {
    var fields = [];
    if (lang === 'ja' || lang === 'zh') fields.push({name: 'cjkSpace',
      label: 'character spacing', min: 0, max: 1, step: 0.025, unit: 'em',
      cssUnit: 'em', def: 0, prop: '--cjk-space'});
    if (lang === 'ja') fields.push(
      {name: 'kanaContrast', label: 'reading contrast', min: 0, max: 100,
       step: 1, unit: '%', cssUnit: '%', def: 0, prop: '--kana-contrast'},
      {name: 'kanaSize', label: 'reading / kanji size', min: 10, max: 200,
       step: 5, unit: '%', cssUnit: '%', def: 50, prop: '--kana-size'});
    return fields;
  }
  function baseText(el) {
    var copy = el.cloneNode(true);
    copy.querySelectorAll('rt, rp').forEach(function (rt) { rt.remove(); });
    return copy.textContent;
  }
  function kanjiOf(text) {
    return Array.from(new Set(Array.from(text).filter(function (c) {
      return /\p{Script=Han}/u.test(c);
    })));
  }
  function kanaFold(s) {
    return s.normalize('NFC').replace(/[\u30a1-\u30f6]/g, function (c) {
      return String.fromCharCode(c.charCodeAt(0) - 0x60);
    });
  }
  // Kana in the spelling anchors the reading. Only accept a unique split;
  // compounds and irregular readings remain a single ruby, never guessed.
  function readingParts(text, kana) {
    var tokens = text.match(/\p{Script=Han}+[々〆ヶ]?|[\p{Script=Hiragana}\p{Script=Katakana}ー]+|[^\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}ー]+/gu) || [];
    var folded = kanaFold(kana), answers = [], visits = 0;
    function walk(i, at, parts) {
      if (++visits > 4000 || answers.length > 1) return;
      if (i === tokens.length) {
        if (at === kana.length) answers.push(parts);
        return;
      }
      var token = tokens[i];
      if (!kanjiOf(token).length) {
        var fixed = kanaFold(token);
        if (folded.slice(at, at + fixed.length) === fixed)
          walk(i + 1, at + fixed.length, parts.concat({text: token, kana: ''}));
        else if (/^[\p{P}\p{Z}\s]+$/u.test(token))
          walk(i + 1, at, parts.concat({text: token, kana: ''}));
      } else {
        for (var end = at + 1; end <= kana.length; end++)
          walk(i + 1, end, parts.concat({text: token, kana: kana.slice(at, end)}));
      }
    }
    walk(0, 0, []);
    if (!kanjiOf(text).length) return [{text: text, kana: ''}];
    return visits <= 4000 && answers.length === 1 ? answers[0] : [{text: text, kana: kana}];
  }
  /* A chunk with a word line (lib/wordline.js) is known a WORD at a time:
     its token is its identity, so 山(やま) and 山(さん) are two words and a
     word said twice is one.  Those go in a second store beside the kanji
     one, parseh_known_word:<scope>.  A word also counts as known when every
     kanji of it is already marked, so nothing a person marked a kanji at a
     time is lost -- and nothing is migrated: the kanji store goes on
     working exactly as it did for every chunk that has no words. */
  function wordline() { return window.ParsehWordline; }
  function readings(opts) {
    var key = 'parseh_known_kanji:' + opts.scope, known = new Set();
    var wordKey = 'parseh_known_word:' + opts.scope, knownWords = null, rows = [];
    function load() {
      try {
        var saved = JSON.parse(localStorage.getItem(key) || '[]');
        known = new Set(Array.isArray(saved) ? saved.filter(function (s) {
          return typeof s === 'string' && kanjiOf(s).length === 1 && Array.from(s).length === 1;
        }) : []);
      } catch (_) { known = new Set(); }
      knownWords = null;
    }
    load();
    // read on first use, not at load: parseh.js is in <head> and
    // wordline.js may not be on the page yet
    function words() {
      if (knownWords) return knownWords;
      var W = wordline(), saved;
      if (!W) return new Set();
      try { saved = JSON.parse(localStorage.getItem(wordKey) || '[]'); } catch (_) { saved = []; }
      knownWords = new Set();
      (Array.isArray(saved) ? saved : []).forEach(function (s) {
        if (typeof s !== 'string') return;
        try {
          var p = W.parse(s);
          if (p.length === 1) knownWords.add(W.key(p[0][0], p[0][1]));
        } catch (_) {}
      });
      return knownWords;
    }
    function byKanji(surface) {
      var chars = kanjiOf(surface);
      return chars.length > 0 && chars.every(function (c) { return known.has(c); });
    }
    function wordKnown(token, surface) { return words().has(token) || byKanji(surface); }
    var surfaces = Object.create(null);
    function surfaceOf(token) {
      if (!(token in surfaces)) {
        try { surfaces[token] = wordline().parse(token)[0][0]; } catch (_) { surfaces[token] = ''; }
      }
      return surfaces[token];
    }
    function apply() {
      document.querySelectorAll(opts.selector + ' ruby').forEach(function (ruby) {
        if (ruby.closest('.wd[data-w]')) return;
        var chars = kanjiOf(baseText(ruby));
        ruby.classList.toggle('reading-known', chars.length > 0 && chars.every(function (c) {
          return known.has(c);
        }));
      });
      document.querySelectorAll(opts.selector + ' .wd[data-w]').forEach(function (wd) {
        var on = wordKnown(wd.dataset.w, surfaceOf(wd.dataset.w));
        wd.querySelectorAll('ruby').forEach(function (ruby) {
          ruby.classList.toggle('reading-known', on);
        });
      });
      document.querySelectorAll('[data-known-kanji]').forEach(function (button) {
        var c = button.dataset.knownKanji, on = known.has(c);
        button.textContent = c + (on ? ': show reading' : ': I know this');
        button.setAttribute('aria-pressed', String(on));
      });
      // a row leaves the list once it has been on the page and is gone from
      // it (a cloud redrawn); one built before it is placed stays, labelled
      rows = rows.filter(function (r) {
        r.seen = r.seen || r.row.isConnected;
        return !r.seen || r.row.isConnected;
      });
      rows.forEach(function (r) {
        r.row.querySelectorAll('[data-known-word]').forEach(function (button) {
          var t = button.dataset.knownWord, s = surfaceOf(t);
          var on = wordKnown(t, s), kanjiOnly = on && !words().has(t);
          button.textContent = s + (on ? ': show reading' : ': I know this');
          button.setAttribute('aria-pressed', String(on));
          button.title = kanjiOnly
            ? 'Hidden because every kanji of it is marked known in this ' + opts.kind
            : 'Remember for every appearance in this ' + opts.kind;
        });
      });
    }
    function render(into, text, kana) {
      into.textContent = '';
      readingParts(text, kana).forEach(function (p) {
        if (!p.kana) { into.appendChild(document.createTextNode(p.text)); return; }
        var ruby = document.createElement('ruby');
        ruby.textContent = p.text;
        var rt = document.createElement('rt'); rt.textContent = p.kana;
        ruby.appendChild(rt); into.appendChild(ruby);
        var chars = kanjiOf(p.text);
        ruby.classList.toggle('reading-known', chars.length > 0 && chars.every(function (c) {
          return known.has(c);
        }));
      });
    }
    function controls(into, text) {
      var chars = kanjiOf(text);
      if (!chars.length) return;
      var row = document.createElement('div'); row.className = 'reading-controls';
      chars.forEach(function (c) {
        var b = document.createElement('button'); b.type = 'button';
        b.dataset.knownKanji = c;
        b.title = 'Remember for every appearance in this ' + opts.kind;
        b.onclick = function (e) {
          e.preventDefault(); e.stopPropagation();
          if (known.has(c)) known.delete(c); else known.add(c);
          try { localStorage.setItem(key, JSON.stringify(Array.from(known))); }
          catch (_) { toast('This browser could not save the reading preference.', true); }
          apply();
        };
        row.appendChild(b);
      });
      var hint = document.createElement('small');
      hint.textContent = 'For this ' + opts.kind + '. Shared compound readings hide when all their kanji are known.';
      row.appendChild(hint); into.insertBefore(row, into.querySelector('.mkrow')); apply();
    }
    /* A chunk drawn from its word line: one .wd per word, its reading over
       it, the whitespace of the text kept between.  A line that does not
       parse, or does not rejoin into the text, draws the text plain and says
       so with .words-bad -- a reader never loses the sentence to bad data. */
    function renderWords(into, fa, line) {
      into.textContent = '';
      into.classList.remove('words-bad');
      var W = wordline(), pairs, spans, keys;
      // 山(( parses, as 山( with no reading, and has no token: a word with
      // no identity to be known by falls back with the rest
      try {
        pairs = W.parse(line); spans = W.align(fa, pairs);
        keys = pairs.map(function (p) { return W.key(p[0], p[1]); });
      } catch (_) {
        into.textContent = fa;
        into.classList.add('words-bad');
        return false;
      }
      spans.forEach(function (sp) {
        if (sp[2] === null) { into.appendChild(document.createTextNode(sp[0])); return; }
        var p = pairs[sp[2]], wd = document.createElement('span');
        wd.className = 'wd';
        wd.dataset.w = keys[sp[2]];
        wd.dataset.k = String(sp[2]);
        if (sp[1]) {
          var ruby = document.createElement('ruby');
          ruby.textContent = sp[0];
          var rt = document.createElement('rt'); rt.textContent = sp[1];
          ruby.appendChild(rt); wd.appendChild(ruby);
          ruby.classList.toggle('reading-known', wordKnown(wd.dataset.w, p[0]));
        } else wd.textContent = sp[0];
        into.appendChild(wd);
      });
      return true;
    }
    function wordControls(into, line) {
      var W = wordline(), pairs, keys, seen = Object.create(null);
      try {
        pairs = W.parse(line);
        keys = pairs.map(function (p) { return W.key(p[0], p[1]); });
      } catch (_) { return null; }
      var row = document.createElement('div'); row.className = 'reading-controls word-controls';
      pairs.forEach(function (p, k) {
        if (!p[1]) return;
        var t = keys[k];
        if (seen[t]) return;
        seen[t] = true;
        var b = document.createElement('button'); b.type = 'button';
        b.dataset.knownWord = t;
        b.onclick = function (e) {
          e.preventDefault(); e.stopPropagation();
          var store = words(), hidden = byKanji(p[0]), had = store.has(t);
          if (had) store.delete(t); else if (!hidden) store.add(t);
          if (had || !hidden) {
            try { localStorage.setItem(wordKey, JSON.stringify(Array.from(store))); }
            catch (_) { toast('This browser could not save the reading preference.', true); }
          }
          // a word hidden by its kanji is not shown from here: that would
          // unmark a kanji every other word written with it shares
          if (hidden) toast('Every kanji of ' + p[0] + ' is marked known in this ' + opts.kind +
                            ': unmark one of them to show its reading.', true);
          apply();
        };
        row.appendChild(b);
      });
      if (!row.children.length) return null;
      var hint = document.createElement('small');
      hint.textContent = 'For this ' + opts.kind + '. A word marked here hides its reading wherever it appears.';
      row.appendChild(hint); into.insertBefore(row, into.querySelector('.mkrow'));
      rows.push({row: row, seen: false}); apply();
      return row;
    }
    window.addEventListener('storage', function (e) {
      if (e.key === key || e.key === wordKey || e.key === null) { load(); apply(); }
    });
    return {render: render, controls: controls, apply: apply,
            renderWords: renderWords, wordControls: wordControls};
  }

  /* ---- the word strip ----
     The editor of a chunk's word line, for both readers' sheets: one chip
     per word, its text on top and its reading in a box underneath.  ⊕
     joins two words, ✂ cuts one where it is pointed at, and ← → on a word's
     text move where that word begins.  Under the chips is a textarea that
     always holds the line: the chips rewrite it, typing in it redraws the
     chips whenever it parses, and it is what the page sends -- as in the
     divide sheets, no offset crosses the wire.  Everything here counts code
     points, never UTF-16 units.

       Parseh.wordstrip({lang, fa, value, reading, reorders, door, propose, onchange})
         -> {el, value(), set(line), destroy()}

     `lang` is the registry record the page embeds; `reading` the chunk's own
     kana or tr, which check() only compares with the words; `propose` an
     async () => line or ''.  onchange(line, result) runs on every change a
     person makes, with check()'s {errors, warnings}; set() is the caller's
     own and runs none.  The caller places `el`. */
  // Python's str.isspace, the set lib/wordline.js splits words on
  var SPACES = /[\t-\r\x1c-\x20\x85\xa0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]/g;
  function wordstrip(opts) {
    var lang = opts.lang || {}, fa = String(opts.fa || ''), dir = lang.dir || 'ltr';
    var chips = [], proposed = null, stale = false, tokenErr = null, gone = false;
    var el = document.createElement('div');
    el.className = 'wordstrip';
    if (lang.code) el.setAttribute('data-lang', lang.code);
    el.innerHTML = '<div class="ws-chips"></div>' +
      '<div class="ws-bar"><button type="button" class="ws-propose">propose</button>' +
      '<button type="button" class="ws-hand">divide by hand</button>' +
      '<span class="ws-say"></span><span class="ws-sp"></span>' +
      '<button type="button" class="ws-astext" aria-expanded="false">edit as text</button></div>' +
      '<textarea class="ws-text" rows="2" spellcheck="false" hidden></textarea>' +
      '<div class="ws-note" aria-live="polite" hidden></div>';
    function $(sel) { return el.querySelector(sel); }
    var row = $('.ws-chips'), box = $('.ws-text'), note = $('.ws-note'), say = $('.ws-say');
    row.setAttribute('dir', dir); box.setAttribute('dir', dir);
    if (lang.code) box.lang = lang.code;
    $('.ws-propose').hidden = !opts.propose;

    function tell(msg, isErr) { say.textContent = msg; say.classList.toggle('err', !!isErr); }
    function fit(input) {
      var n = Array.from(input.value || input.placeholder).length;
      input.size = Math.max(4, n * (lang.reading ? 2 : 1) + 1);
    }
    function draw(focus) {
      row.textContent = '';
      chips.forEach(function (c, i) {
        if (i) {
          var j = document.createElement('button');
          j.type = 'button'; j.className = 'ws-join'; j.textContent = '⊕';
          j.title = 'join ' + chips[i - 1].s + ' and ' + c.s + ' into one word';
          j.onclick = function () { join(i - 1); };
          row.appendChild(j);
        }
        var chip = document.createElement('span'); chip.className = 'ws-chip';
        var surf = document.createElement('span'); surf.className = 'ws-surf';
        surf.tabIndex = 0;
        if (lang.code) surf.lang = lang.code;
        surf.title = '← → move where this word begins';
        // the ✂ is drawn by the stylesheet, so the chip's text is the word
        Array.from(c.s).forEach(function (ch, k) {
          if (k) {
            var cut = document.createElement('button');
            cut.type = 'button'; cut.className = 'ws-cut'; cut.tabIndex = -1;
            cut.title = 'cut the word here';
            cut.onclick = function () { cutAt(i, k); };
            surf.appendChild(cut);
          }
          surf.appendChild(document.createTextNode(ch));
        });
        surf.onkeydown = function (e) { nudge(e, i); };
        var input = document.createElement('input');
        input.className = 'ws-read'; input.value = c.r;
        input.placeholder = lang.reading_label || lang.translit_label || '';
        input.setAttribute('aria-label', 'the reading of ' + c.s);
        if (lang.reading && lang.code) input.lang = lang.code;
        fit(input);
        input.oninput = function () { chips[i].r = input.value; fit(input); fromChips(); };
        chip.appendChild(surf); chip.appendChild(input);
        row.appendChild(chip);
      });
      if (!focus) return;
      var at = row.querySelectorAll('.ws-chip')[focus[0]];
      var f = at && at.querySelector(focus[1]);
      if (f) {
        f.focus();
        if (f.setSelectionRange) f.setSelectionRange(f.value.length, f.value.length);
      }
    }
    // the chips rewrite the line; a word that cannot be written (a reading
    // that begins with '(') goes in as typed, and its refusal leads the note
    function fromChips() {
      var bad = null, W = wordline();
      box.value = chips.map(function (c) {
        try { return W.token(c.s, c.r); }
        catch (e) { bad = bad || e; return c.s + (c.r ? '(' + c.r + ')' : ''); }
      }).join(' ');
      tokenErr = bad; stale = false;
      changed();
    }
    function parsed(line) {
      try {
        chips = wordline().parse(line).map(function (p) { return {s: p[0], r: p[1]}; });
        stale = false;
      } catch (_) { stale = true; }
      tokenErr = null;
      if (!stale) draw();
    }
    function fromText() { parsed(box.value); changed(); }
    function paint() {
      var W = wordline(), line = box.value, empty = !!W && !line.trim();
      // no checker on the page is not a clean line
      var res = W ? W.check(fa, line, lang, opts.reading || '', !!opts.reorders, opts.door || 'book')
                  : {errors: [{code: 'no_wordline', message: 'lib/wordline.js is not on this page, so these words can be neither read nor checked'}], warnings: []};
      if (tokenErr) res.errors.unshift({code: tokenErr.code || 'token', message: tokenErr.message});
      row.classList.toggle('ws-stale', stale);
      $('.ws-hand').hidden = !empty || !fa.replace(SPACES, '');
      note.textContent = '';
      function add(cls, text) {
        var d = document.createElement('div'); d.className = cls; d.textContent = text;
        note.appendChild(d);
      }
      if (empty) add('ws-empty', 'This chunk has no words yet.');
      else {
        res.errors.forEach(function (e) { add('ws-err', e.message); });
        res.warnings.forEach(function (w) { add('ws-warn', w.message); });
      }
      note.hidden = !note.childNodes.length;
      return res;
    }
    function changed() {
      var res = paint();
      if (opts.onchange) opts.onchange(box.value, res);
    }

    function cutAt(i, k) {
      var chars = Array.from(chips[i].s);
      if (k < 1 || k >= chars.length) return;
      chips.splice(i, 1, {s: chars.slice(0, k).join(''), r: chips[i].r},
                         {s: chars.slice(k).join(''), r: ''});
      draw([i + 1, '.ws-read']); fromChips();
    }
    function join(i) {
      var a = chips[i], b = chips[i + 1];
      chips.splice(i, 2, {s: a.s + b.s, r: a.r + b.r});
      draw([i, '.ws-read']); fromChips();
    }
    // the word's first boundary, a character at a time: ← takes one from the
    // word before, → gives one back, and neither ever leaves a word empty
    function nudge(e, i) {
      if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
      if (e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return;
      e.preventDefault(); e.stopPropagation();
      if (i === 0) return;
      var take = (e.key === 'ArrowLeft') === (dir !== 'rtl');
      var before = Array.from(chips[i - 1].s), mine = Array.from(chips[i].s);
      if (take) { if (before.length < 2) return; mine.unshift(before.pop()); }
      else { if (mine.length < 2) return; before.push(mine.shift()); }
      chips[i - 1].s = before.join(''); chips[i].s = mine.join('');
      draw([i, '.ws-surf']); fromChips();
    }

    $('.ws-propose').onclick = function () {
      var b = this, line = box.value;
      // what is written and was not the last proposal is somebody's work
      if (line.trim() && line !== proposed &&
          !window.confirm('Replace these words with a proposal? What is written here now is lost.')) return;
      b.disabled = true; tell('proposing…');
      Promise.resolve().then(function () { return opts.propose(); }).then(function (got) {
        b.disabled = false;
        if (gone) return;
        if (!got) { tell('nothing was proposed for this chunk: divide it by hand'); return; }
        tell('');
        proposed = box.value = String(got);
        fromText();
      }, function (err) {
        b.disabled = false;
        if (!gone) tell((err && err.message) || String(err), true);
      });
    };
    $('.ws-hand').onclick = function () {
      var whole = fa.replace(SPACES, '');
      if (!whole) return;
      chips = [{s: whole, r: ''}];
      draw([0, '.ws-surf']); fromChips();
    };
    $('.ws-astext').onclick = function () {
      box.hidden = !box.hidden;
      this.setAttribute('aria-expanded', String(!box.hidden));
      this.classList.toggle('on', !box.hidden);
      if (!box.hidden) box.focus();
    };
    box.addEventListener('input', fromText);

    function set(line) {
      box.value = line == null ? '' : String(line);
      chips = [];
      parsed(box.value);
      if (stale) draw();
      paint();
    }
    set(opts.value);
    return {
      el: el,
      value: function () { return box.value; },
      set: set,
      destroy: function () { gone = true; el.remove(); }
    };
  }

  function escapeHTML(s) {
    return String(s || '').replace(/[&<>"']/g, function (c) {
      return {'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c];
    });
  }
  // Keep offsets into the original spelling while matching folded words,
  // including vocalised Arabic/Persian and case-folded Latin text.
  function pairMarkup(pair, result, lang, gloss) {
    var marks = lang.strip ? new RegExp('[' + lang.strip + ']', 'g') : null;
    function fold(s) {
      s = String(s || '').normalize('NFC').replace(/[\u0130\u0131]/g, 'i').toLowerCase();
      return marks ? s.replace(marks, '') : s;
    }
    var text = pair.src || '', flat = '', offsets = [], endOffsets = [];
    var at = 0;
    Array.from(text).forEach(function (c) {
      var f = fold(c);
      for (var n = 0; n < f.length; n++) { offsets.push(at); endOffsets.push(at + c.length); }
      if (!f && endOffsets.length) endOffsets[endOffsets.length - 1] = at + c.length;
      flat += f; at += c.length;
    });
    var matched = (pair.matched || []).map(fold).filter(Boolean), ranges = [];
    matched.forEach(function (word) {
      var pos = 0, hit;
      while ((hit = flat.indexOf(word, pos)) !== -1) {
        var end = hit + word.length;
        var left = Array.from(flat.slice(0, hit)).pop() || '';
        var right = Array.from(flat.slice(end))[0] || '';
        if (lang.word_sep === '' || (!/[\p{L}\p{N}]/u.test(left) && !/[\p{L}\p{N}]/u.test(right)))
          ranges.push([offsets[hit], endOffsets[end - 1]]);
        pos = end;
      }
    });
    ranges.sort(function (a, b) { return a[0] - b[0]; });
    var merged = [];
    ranges.forEach(function (r) {
      var last = merged[merged.length - 1];
      if (last && r[0] <= last[1]) last[1] = Math.max(last[1], r[1]); else merged.push(r);
    });
    var source = '', cursor = 0;
    merged.forEach(function (r) {
      source += escapeHTML(text.slice(cursor, r[0])) + '<mark class="pair-match">' +
        escapeHTML(text.slice(r[0], r[1])) + '</mark>'; cursor = r[1];
    });
    source += escapeHTML(text.slice(cursor));
    var target = escapeHTML(pair.dst);
    if (window.ParsehMT) {
      var words = (result.words || []).filter(function (w) {
        return matched.indexOf(fold(w.word)) >= 0 || (w.hits || []).some(function (h) {
          return matched.indexOf(fold(h.headword)) >= 0;
        });
      });
      // Align each matched word independently so separate equivalents can
      // both be coloured. No model call and no change to the human translation.
      var spans = words.map(function (w) {
        return ParsehMT.align(pair.dst, '', [w], gloss.code);
      }).filter(Boolean);
      if (spans.length) {
        var hot = new Set();
        spans.forEach(function (span) {
          var index = 0;
          ParsehMT.marked(pair.dst, span).forEach(function (p) {
            if (p.here) {
              var first = p.text.search(/[\p{L}\p{N}]/u);
              var last = p.text.replace(/[^\p{L}\p{N}\p{M}]+$/u, '').length;
              if (first >= 0) for (var i = index + first; i < index + last; i++) hot.add(i);
            }
            index += p.text.length;
          });
        });
        target = ''; var start = 0, active = hot.has(0);
        for (var i = 1; i <= pair.dst.length; i++) {
          if (i === pair.dst.length || hot.has(i) !== active) {
            var chunk = escapeHTML(pair.dst.slice(start, i));
            target += active ? '<mark class="pair-match">' + chunk + '</mark>' : chunk;
            start = i; active = hot.has(i);
          }
        }
      }
    }
    return {src: source, dst: target};
  }

  /* ---- the language ----
     ONE preference for the whole toolbox, `parseh_lang` in localStorage:
     'all', or a registry code ('fa', 'ja', ...).  The index pages (the
     hub, /books/, /youtube/, the studio's library) render a chip row --
     languages.chips_html, class .parseh-langs, one .chip per language with
     data-pick -- and this marks the picked chip .on.  A row that carries
     data-lang-filter="<selector>" also filters: every element matching the
     selector inside <main> (or <body> when the page has no <main>) whose
     data-lang is not the picked language is hidden, and a heading (h1-h6
     or .lang-head) with data-lang whose group has nothing left visible is
     hidden with it.  The hub's row has no filter: there the chips only
     record the preference the other pages then open with -- and rewrite the
     counts on its doors, each of which carries its per-language numbers in
     data-counts.  <html> gets data-parseh-lang so a page's own stylesheet
     can react. */
  var LANG_KEY = 'parseh_lang';
  function langGet() {
    var v = null;
    try { v = localStorage.getItem(LANG_KEY); } catch (e) {}
    if (!v || !/^[a-z][a-z0-9_-]{0,15}$/i.test(v)) v = 'all';
    return v;
  }
  function isHeading(el) {
    return /^H[1-6]$/.test(el.tagName) || el.classList.contains('lang-head');
  }
  function langApply(smooth) {
    var pick = langGet();
    var rows = document.querySelectorAll('.parseh-langs');
    // A stored code no chip on this page offers -- a language since taken
    // out of the registry, or a value another tool wrote -- would hide every
    // card and heading and mark no chip, an empty page with nothing to
    // click.  Such a preference is stale: read it as 'all', and write that
    // back so the pages that wire the row themselves (the studio's library)
    // open on the same footing.
    if (rows.length && pick !== 'all' &&
        !document.querySelector('.parseh-langs .chip[data-pick="' + pick + '"]')) {
      pick = 'all';
      try { localStorage.setItem(LANG_KEY, pick); } catch (e) {}
    }
    document.documentElement.dataset.parsehLang = pick;
    for (var r = 0; r < rows.length; r++) {
      var row = rows[r];
      var chips = row.querySelectorAll('.chip');
      for (var c = 0; c < chips.length; c++)
        chips[c].classList.toggle('on', chips[c].getAttribute('data-pick') === pick);
      var sel = row.getAttribute('data-lang-filter');
      if (!sel) continue;
      var scope = document.querySelector('main') || document.body;
      var els;
      try { els = scope.querySelectorAll(sel); } catch (e) { continue; }
      var heads = [];
      for (var i = 0; i < els.length; i++) {
        var el = els[i];
        // the row and its chips carry lang/data-lang of their own: never those
        if (el === row || row.contains(el) || el.closest('.parseh-langs')) continue;
        if (isHeading(el)) { heads.push(el); continue; }
        var lang = el.getAttribute('data-lang');
        el.hidden = pick !== 'all' && lang !== pick;
      }
      // a heading stands for the cards after it, up to the next heading:
      // with none of them visible it goes too
      for (var h = 0; h < heads.length; h++) {
        var head = heads[h], any = false, sib = head.nextElementSibling;
        while (sib && !isHeading(sib)) {
          if (!sib.hidden && sib.hasAttribute('data-lang')) { any = true; break; }
          sib = sib.nextElementSibling;
        }
        head.hidden = !any;
      }
    }
    // A count that knows its languages -- the hub's door tags -- carries
    // data-counts, {"all": "12 videos", "fa": "3 videos", ...}: it says the
    // picked language's number, so the one count answers for whichever
    // language is chosen instead of a row of per-language tags beside it.
    var tags = document.querySelectorAll('[data-counts]');
    for (var t = 0; t < tags.length; t++) {
      var tag = tags[t], map = tag.parsehCounts;
      if (map === undefined) {
        try { map = JSON.parse(tag.getAttribute('data-counts')); } catch (e) { map = null; }
        if (!map || typeof map !== 'object') map = null;
        tag.parsehCounts = map;
      }
      if (!map) continue;
      var say = map[pick] !== undefined ? map[pick] : map.all;
      if (say !== undefined) tag.textContent = say;
    }
    langReveal(smooth);
  }
  function langSet(v) {
    try { localStorage.setItem(LANG_KEY, v || 'all'); } catch (e) {}
    langApply(true);
  }
  /* A chip row that scrolls sideways instead of wrapping -- the mobile
     hub's -- always opens at its start, and the picked chip may be well past
     the edge of the screen: the doors' counts would then answer for a
     language nothing in view says is picked.  So such a row is scrolled to
     bring the picked chip to its middle whenever that chip is not wholly in
     view: when the page opens, when a chip is picked, and when the mode
     puts the row on the screen.  The row's own scrollLeft is moved, never
     scrollIntoView, which would scroll the page as well.  A row that wraps,
     or is not drawn, does not scroll, and is left alone.  The row's padding
     is where its edges fade out, so a chip there does not count as in view.
     The arithmetic is on the drawn boxes, so it holds for a right-to-left
     row as well. */
  function langReveal(smooth) {
    var rows = document.querySelectorAll('.parseh-langs');
    for (var i = 0; i < rows.length; i++) {
      var row = rows[i], on = row.querySelector('.chip.on');
      if (!on || row.scrollWidth <= row.clientWidth) continue;
      var r = row.getBoundingClientRect(), c = on.getBoundingClientRect();
      var cs = getComputedStyle(row);
      if (c.left >= r.left + (parseFloat(cs.paddingLeft) || 0) - 0.5 &&
          c.right <= r.right - (parseFloat(cs.paddingRight) || 0) + 0.5) continue;
      var by = (c.left + c.width / 2) - (r.left + r.width / 2);
      // a pick glides there, unless motion is better left out
      if (smooth && row.scrollBy && !(window.matchMedia &&
          matchMedia('(prefers-reduced-motion: reduce)').matches))
        row.scrollBy({ left: by, behavior: 'smooth' });
      else row.scrollLeft += by;
    }
  }

  /* ---- the bar, on a phone ----
     A phone screen is mostly bar: the reader's header wraps into three rows
     and what is left over is too little to read in.  So on a narrow screen
     the bar goes away as soon as the page moves down, and comes back on the
     smallest move up -- not only at the top of the page, which would mean
     scrolling a chapter back to reach one button.

     NOTHING CHANGES ON A WIDE SCREEN.  The listener is wired only while the
     media query matches, and the class it toggles is defined only inside
     the same query in every stylesheet that answers it.

     The class goes on <body> and each page's own sheet says what to do with
     it, because the bars differ: the hub-level `.parseh-bar` is in the flow
     (it is made sticky there first), while the reader's and the player's
     headers are fixed.  Both move by a transform and nothing else -- the
     reader writes its header's height into body's inline padding from a
     ResizeObserver, and the player hangs its video off --headh, so a bar
     that changed height instead would drag the page or the video with it.

     A STRONGER HAND CAN STAND THIS DOWN.  The book reader also lets the bar
     be put away by hand (chrome-off, the same class and the same idea as
     the studio's own bars button); while that holds, the header is already
     away, and this has nothing to add -- worse, if it went on toggling
     `barhidden` regardless, that could come back true however the reader
     last scrolled, and bringing the header back by hand would hand it
     straight off-screen again.  So it simply does not touch `barhidden`
     while chrome-off is set, and the page that sets it clears `barhidden`
     itself when the bar comes back, so that pressing the button is what
     decides, not the scroll.  A page can hold the bar where it is for a
     while the same way, with <body data-bars-held>: the reader's mobile
     layer does while its ⋯ controls are open.

     IN THE MOBILE MODE IT FOLLOWS THE SCROLL AT EVERY WIDTH.  A phone held
     sideways is wider than 560px and has the least height of all, and the
     mobile pages' sheet (lib/mobile.css) answers `barhidden` at any width in
     that mode; the browser pages' sheets still answer it only under 560px,
     so a browser page opened in the mobile mode is as it was. */
  var PHONE = '(max-width: 560px)';
  function bars() {
    if (!window.matchMedia || !document.body) return;
    var mq = window.matchMedia(PHONE);
    var lastY = 0, ticking = false, off = false, on = false;
    function set(v) {
      if (v === off) return;
      off = v;
      document.body.classList.toggle('barhidden', v);
    }
    function read() {
      ticking = false;
      var y = window.pageYOffset || document.documentElement.scrollTop || 0;
      if (y < 0) y = 0;                     // the rubber band at either end
      var d = y - lastY;
      if (Math.abs(d) < 4) return;          // a finger resting is not a move
      // where the page is, kept even while the bar is not to move: the
      // first move after is then measured from here, not from before
      lastY = y;
      if (document.body.classList.contains('chrome-off') ||
          document.body.hasAttribute('data-bars-held')) return;
      // near the top the bar always stands; below that, down takes it away
      // and any move up at all brings it back
      set(y > 56 && d > 0);
    }
    function onScroll() {
      if (ticking) return;
      ticking = true;
      if (window.requestAnimationFrame) requestAnimationFrame(read);
      else setTimeout(read, 16);
    }
    function follow() {
      var want = mq.matches || isMobile();
      if (want === on) return;
      on = want;
      if (want) {
        lastY = window.pageYOffset || 0;
        addEventListener('scroll', onScroll, {passive: true});
      } else {
        removeEventListener('scroll', onScroll);
        set(false);                          // back to a desktop: bar stays
      }
    }
    follow();
    if (mq.addEventListener) mq.addEventListener('change', follow);
    else if (mq.addListener) mq.addListener(follow);
    modeOnChange(follow);
  }

  function wire() {
    apply();
    modeApply();
    langApply();
    bars();
    appWire();
    // while nothing has been picked the page follows the system, so a system
    // that flips has to move the button's glyph with it
    if (window.matchMedia) {
      var mq = window.matchMedia('(prefers-color-scheme: dark)');
      var onFlip = function () { if (get() === 'auto') apply(); };
      if (mq.addEventListener) mq.addEventListener('change', onFlip);
      else if (mq.addListener) mq.addListener(onFlip);
    }
    var tb = document.querySelectorAll('[data-parseh-theme]');
    for (var i = 0; i < tb.length; i++) tb[i].addEventListener('click', cycle);
    var sb = document.querySelectorAll('[data-parseh-stop]');
    for (var j = 0; j < sb.length; j++)
      sb[j].addEventListener('click', function () { stopServer(); });
    // delegated, so a row a page renders later (the studio's library draws
    // its cards from JSON) is wired the moment it exists
    document.addEventListener('click', function (e) {
      var chip = e.target && e.target.closest && e.target.closest('.parseh-langs .chip');
      if (!chip) return;
      var pick = chip.getAttribute('data-pick');
      if (pick) langSet(pick);
    });
    document.addEventListener('click', modeClick);
    document.addEventListener('click', cardDelete, true);
    document.addEventListener('click', cardBuild, true);
  }

  /* A SENSE'S LABELS, as the reader of an entry wants them: the book
     reader's definitions and the player's both draw them from here.  The
     dictionary keeps a sense's tags beside it (lookup.py's `marks`,
     wiktextract's own, comma-joined), and most of them are Wiktionary's
     labels -- (transitive), (countable), (slang), (UK).  Three kinds are
     not, and go: the notation lookup writes for what a sense governs
     (`obj:acc`, with its colon); the part of speech the entry already names
     (`pronoun` on a pronoun); and what the FORM is, which a pronoun's or a
     noun's table lends every sense under it -- person, number, case, the
     kind of pronoun -- so that `thee` came out "(archaic, literary,
     objective, second person, singular)" where Wiktionary prints "(archaic,
     literary)".  Hyphens are spaces, as Wiktionary prints them.
     -> an array of labels, [] for none. */
  var FORM_TAGS = Object.create(null);
  ('first-person second-person third-person singular plural dual nominative ' +
   'objective subjective accusative dative genitive personal demonstrative ' +
   'interrogative indefinite definite invariable no-gloss form-of alt-of')
    .split(' ').forEach(function (t) { FORM_TAGS[t] = 1; });
  var POS_TAG = { adj: 'adjective', adv: 'adverb', conj: 'conjunction', det: 'determiner',
                  intj: 'interjection', num: 'numeral', prep: 'preposition',
                  postp: 'postposition', pron: 'pronoun', name: 'proper-noun' };
  function senseLabels(mark, pos) {
    var own = Object.prototype.hasOwnProperty.call(POS_TAG, pos) ? POS_TAG[pos] : (pos || '');
    var seen = Object.create(null);
    return String(mark || '').split(',').map(function (t) { return t.trim(); })
      .filter(function (t) {
        if (!t || t.indexOf(':') >= 0 || FORM_TAGS[t] || t === own || t === pos || seen[t]) return false;
        seen[t] = 1;
        return true;
      })
      .map(function (t) { return t.replace(/-/g, ' '); });
  }

  /* ---- the mobile interface as an app (docs/mobile.md) ----
     Installed from a phone's browser, the mobile interface opens from an
     icon, on the whole screen: /manifest.webmanifest describes it, and
     /sw.js (lib/sw.js) is the service worker a browser asks for before it
     offers to install anything.  Here:
       - the app opens at /?mode=mobile: the mode is set from the address and
         the address given back without it, before anything is painted;
       - in the mobile mode the service worker is registered (again, which
         costs nothing) on every page, so whichever page a phone is on, it
         can be installed from there;
       - the browser's offer to install (beforeinstallprompt, Chrome's) is
         kept, in the mobile mode, for the page's own Install buttons --
         [data-parseh-install], drawn only while there is an offer -- rather
         than a bar of the browser's over whatever is being read;
       - a page built without the app's tags (a book's reader) gets them. */
  (function () {
    var m = /(?:^\?|&)mode=(browser|mobile)(?=&|$)/.exec(location.search);
    if (!m) return;
    try { localStorage.setItem(MODE_KEY, m[1]); } catch (e) {}
    modeCookieSet(m[1]);
    if (!window.history || !history.replaceState) return;
    var rest = location.search.replace(/(?:^\?|&)mode=(?:browser|mobile)(?=&|$)/, '').replace(/^&/, '');
    try { history.replaceState(history.state, '', location.pathname + (rest ? '?' + rest : '') + location.hash); }
    catch (e) {}
  })();
  var installOffer = null, appFns = [];
  function appStandalone() {
    return !!((window.matchMedia && window.matchMedia(
      '(display-mode: standalone), (display-mode: fullscreen), (display-mode: minimal-ui)').matches) ||
      window.navigator.standalone === true);
  }
  function appPaint() {
    var bs = document.querySelectorAll('[data-parseh-install]');
    for (var i = 0; i < bs.length; i++) bs[i].hidden = !installOffer;
    for (var j = 0; j < appFns.length; j++) { try { appFns[j](); } catch (e) {} }
  }
  function appInstall() {
    if (!installOffer) return Promise.resolve(false);
    var offer = installOffer;
    installOffer = null;                   // an offer is good for one prompt
    appPaint();
    offer.prompt();
    return offer.userChoice.then(function (c) { return !!c && c.outcome === 'accepted'; },
                                 function () { return false; });
  }
  function appRegister() {
    if (!('serviceWorker' in navigator) || !window.isSecureContext ||
        !/^https?:$/.test(location.protocol)) return Promise.resolve(null);
    // refused where the phone does not trust the certificate: the install
    // page says so, and nothing else here needs to
    return navigator.serviceWorker.register('/sw.js').catch(function () { return null; });
  }
  window.addEventListener('beforeinstallprompt', function (e) {
    if (!isMobile()) return;               // the browser mode: the browser's own way
    e.preventDefault();
    installOffer = e;
    appPaint();
  });
  window.addEventListener('appinstalled', function () { installOffer = null; appPaint(); });
  document.addEventListener('click', function (e) {
    var b = e.target && e.target.closest && e.target.closest('[data-parseh-install]');
    if (b) appInstall();
  });
  function appHead() {
    if (location.protocol === 'file:' || document.querySelector('link[rel=manifest]')) return;
    var head = document.head;
    if (!head) return;
    // the same tags lib/mobile.py (app_head) writes into the pages it makes
    [['link', {rel: 'manifest', href: '/manifest.webmanifest'}],
     ['link', {rel: 'apple-touch-icon', href: '/lib/icons/apple-touch-icon.png'}],
     ['meta', {name: 'mobile-web-app-capable', content: 'yes'}],
     ['meta', {name: 'apple-mobile-web-app-capable', content: 'yes'}],
     ['meta', {name: 'apple-mobile-web-app-title', content: 'Parseh'}]].forEach(function (t) {
      var el = document.createElement(t[0]);
      for (var k in t[1]) el.setAttribute(k, t[1][k]);
      head.appendChild(el);
    });
  }
  function appWire() {
    appHead();
    appPaint();
    if (isMobile()) appRegister();
    modeOnChange(function (m) { if (m === 'mobile') appRegister(); });
  }

  window.Parseh = { KEY: KEY, theme: { get: get, set: set, apply: apply,
                    cycle: cycle, isDark: isDark, resolved: resolved },
                    lang: { KEY: LANG_KEY, get: langGet, set: langSet, apply: langApply },
                    mode: { KEY: MODE_KEY, get: modeGet, set: modeSet, isMobile: isMobile,
                            route: modeRoute, onChange: modeOnChange, apply: modeApply,
                            pages: MOBILE_PAGES },
                    app: { standalone: appStandalone, canPrompt: function () { return !!installOffer; },
                           prompt: appInstall, register: appRegister,
                           onChange: function (fn) { appFns.push(fn); } },
                    toast: toast, copy: copy, stopServer: stopServer, buildBook: buildBook, typo: typo, readingFields: readingFields,
                    working: working, stopQuestion: stopQuestion,
                    readings: readings, wordstrip: wordstrip, baseText: baseText, pairMarkup: pairMarkup,
                    senseLabels: senseLabels };
  apply();
  modeApply();
  if (document.readyState === 'loading')
    document.addEventListener('DOMContentLoaded', wire);
  else wire();

  /* ---- what the server is working on: lib/activity.js ----
     Loaded from BESIDE THIS SCRIPT, by whatever address this one was
     loaded by: the book reader links lib/ relatively (it also opens off the
     disk), so a built reader gets the list without being built again, and
     every other page gets it without a tag of its own.  Off the disk there
     is no server to ask, and nothing is loaded. */
  (function () {
    if (window.ParsehActivity || location.protocol === 'file:') return;
    var me = document.currentScript;
    var src = me && me.src ? me.src.replace(/parseh\.js(?=[?#]|$).*$/, 'activity.js')
                           : '/lib/activity.js';
    var s = document.createElement('script');
    s.src = src;
    s.async = true;
    (document.head || document.documentElement).appendChild(s);
  })();

  /* ---- a book's reader, in the mobile interface: lib/mobilereader.js ----
     A reader is a page BUILT for its book (lib/tex2html.py), and a book built
     before the mobile interface existed has no mobile layout written into it
     -- which is most books, on any shelf, for any feature.  But every reader,
     however old, loads this script from lib/, so the mobile layer is loaded
     from here, beside it, as activity.js is above: the sheet (lib/mobile.css,
     whose reader rules all hang off html.m-reader) and the script that fits
     the header to a phone and keeps every writing door of the page shut
     (lib/mobilereader.js).  Both are loaded in either mode, because the mode
     can change while the page is open -- a switch made in another tab -- and
     neither does anything until the mode is mobile.
     A reader is known by its address, /books/<language>/<slug>/reader/ (or,
     for a book from before languages, /books/<slug>/reader/).  Opened off the
     disk it has no mobile interface, as it has no server. */
  (function () {
    if (location.protocol === 'file:' ||
        !/^\/books\/(?:[^\/]+\/){1,2}reader\/(?:index\.html)?$/.test(location.pathname)) return;
    var me = document.currentScript;
    var base = me && me.src ? me.src.replace(/parseh\.js(?=[?#]|$).*$/, '') : '/lib/';
    document.documentElement.classList.add('m-reader');
    if (!document.querySelector('link[href$="/mobile.css"]')) {
      var l = document.createElement('link');
      l.rel = 'stylesheet';
      l.href = base + 'mobile.css';
      // held until it is in, where the browser knows how: without it the
      // header can be drawn once as the browser's before it is the phone's
      l.setAttribute('blocking', 'render');
      (document.head || document.documentElement).appendChild(l);
    }
    if (window.ParsehMobileReader) return;
    var s = document.createElement('script');
    s.src = base + 'mobilereader.js';
    s.async = true;
    (document.head || document.documentElement).appendChild(s);
  })();
})();

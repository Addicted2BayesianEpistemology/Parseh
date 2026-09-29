// SPDX-License-Identifier: GPL-3.0-or-later
/* Parseh — what a reader of a book being made by an agent adds to itself
   (lib/making.py, TO-DO §8.40).

   Loaded into EVERY book's reader by lib/parseh.js, from beside it: a reader
   is a page built for its book, and one built before a book could be made
   this way has nothing of it in its own markup -- so it all lives here, and
   reaches every edition without a rebuild.  It asks the server one question,
   `<book>/__making`, and does nothing at all for a book nobody is making.

   For a book being made it adds four things:

     - THE MAKING PANEL, from a button in the header: where the making stands
       (source recovered, chapter table, batch N of M, and when the agent last
       wrote), what it is on, the tools' last words, the end of its notes;
       LOOK AT IT NOW, which rebuilds this page from what has been written so
       far (the build job the page already polls), and THE PDF OF THESE
       CHAPTERS, where the computer has a shell to make one; the box WHAT TO
       CHANGE FROM NOW ON, which appends to ASKS.md, the file the agent reads
       again before every batch; the folder, to copy and to open; and FINISH.
       The panel is any device's to read and to write an ask in; the folder
       and Finish are the computer's, and say so where they are not yours.
     - NO EDITING WHILE IT IS MADE.  The pipeline's truth is annot/*.json and
       the .tex is assembled from it, so a hand edit would be erased by the
       agent's next batch: the pencil says why, the chunk sheet shows the chunk
       and shuts what writes it, and offers ASK ABOUT THIS CHUNK -- the chunk's
       address and text, and the person's line, appended to ASKS.md.  The
       passes, the clouds and the dictionary work as ever, and the server
       refuses the doors that write (lib/making.py LOCKED) whatever this page
       does.
     - THE CHAPTERS STILL TO COME, said under the last batch there is.
     - and when Finish ends the making, the page reloads as an ordinary book.

   Nothing here is drawn for a phone that a phone cannot use: the sheet works at
   every width, and the chunk sheet (which the phone's reader never opens)
   is the only place ask-about-this-chunk lives. */
(function () {
  'use strict';
  if (window.ParsehMaking) return;
  var here = location.pathname.match(/^(\/books\/(?:[^\/]+\/){1,2})reader\//);
  if (!here || location.protocol === 'file:') return;
  window.ParsehMaking = {};

  var BASE = here[1];                       // /books/<folder>/<slug>/
  var STATUS = BASE + '__making';
  var OPEN_KEY = 'parseh_making_open';
  var S = null;                             // the last answer of the server
  var ui = null;                            // the panel, once built
  var seen = 0;                             // when S arrived, to say "3 minutes ago" truthfully
  var timer = null, panelOpen = false, finishAsked = false;
  var $ = function (id) { return document.getElementById(id); };

  function ask(url, init) {
    return (window.Parseh && Parseh.ask ? Parseh.ask(url, init) : fetch(url, init))
      .then(function (r) { return r.json(); });
  }
  function post(url, body) {
    return ask(url, {method: 'POST', headers: {'Content-Type': 'application/json'},
                     body: JSON.stringify(body || {})});
  }
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined) e.textContent = text;
    return e;
  }
  function btn(text, cls, fn) {
    var b = el('button', cls || 'mk-b', text);
    b.type = 'button';
    if (fn) b.addEventListener('click', fn);
    return b;
  }
  function ago(s) {
    s = Math.max(0, Math.round(s));
    if (s < 90) return 'just now';
    if (s < 5400) return Math.round(s / 60) + ' minutes ago';
    if (s < 129600) return Math.round(s / 3600) + ' hours ago';
    return Math.round(s / 86400) + ' days ago';
  }
  function said(msg, bad) {
    if (window.Parseh && Parseh.toast) Parseh.toast(msg, !!bad);
  }
  function store(k, v) {
    try { if (v === null) sessionStorage.removeItem(k); else sessionStorage.setItem(k, v); } catch (e) {}
  }
  function stored(k) {
    try { return sessionStorage.getItem(k); } catch (e) { return null; }
  }

  /* ---------------------------------------------------------------- the look
     Its own sheet, in the reader's own tokens, so that all three themes and
     a right-to-left page follow without a line of the reader's CSS changing. */
  function style() {
    if ($('mk-style')) return;
    var s = el('style');
    s.id = 'mk-style';
    s.textContent =
      '.mk-btn .mk-dot{display:inline-block;width:8px;height:8px;border-radius:50%;' +
      'background:var(--faint);margin-inline-end:6px;vertical-align:1px}' +
      '.mk-btn.mk-live .mk-dot{background:var(--accent);animation:mk-pulse 1.6s ease-in-out infinite}' +
      '.mk-btn.mk-new{border-color:var(--accent)}' +
      '@keyframes mk-pulse{50%{opacity:.35}}' +
      '@media (prefers-reduced-motion:reduce){.mk-btn.mk-live .mk-dot{animation:none}}' +
      '#mkbox{position:fixed;z-index:75;top:56px;inset-inline-end:12px;width:min(470px,calc(100vw - 24px));' +
      'max-height:calc(100vh - 72px);overflow:auto;background:var(--card);color:var(--ink);' +
      'border:1px solid var(--rule);border-radius:12px;padding:14px 16px 16px;' +
      'box-shadow:0 10px 34px rgba(0,0,0,.22);font:14px/1.55 system-ui,sans-serif;text-align:start}' +
      '#mkbox[hidden]{display:none}' +
      '#mkbox h2{font:600 15px/1.3 system-ui,sans-serif;margin:0;display:flex;align-items:center;gap:8px}' +
      '#mkbox h2 .mk-x{margin-inline-start:auto}' +
      '#mkbox h3{font:600 11.5px/1.3 system-ui,sans-serif;letter-spacing:.1em;text-transform:uppercase;' +
      'color:var(--dim);margin:16px 0 6px}' +
      '#mkbox .mk-where{font-size:16px;margin:10px 0 2px}' +
      '#mkbox .mk-where b{font-weight:600}' +
      '#mkbox .mk-dim,#mkbox .mk-small{color:var(--dim);font-size:12.5px}' +
      '#mkbox .mk-row{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:8px 0}' +
      '#mkbox button.mk-b{font:inherit;font-size:13px;padding:6px 12px;border:1px solid var(--rule);' +
      'background:var(--bg);color:var(--ink);border-radius:7px;cursor:pointer}' +
      '#mkbox button.mk-b:hover:not(:disabled){border-color:var(--accent);color:var(--accent)}' +
      '#mkbox button.mk-go{background:var(--accent);border-color:var(--accent);color:var(--accent-fg)}' +
      '#mkbox button.mk-go:hover:not(:disabled){color:var(--accent-fg);filter:brightness(1.1)}' +
      '#mkbox button.mk-danger{border-color:var(--danger);color:var(--danger)}' +
      '#mkbox button:disabled{opacity:.5;cursor:not-allowed}' +
      '#mkbox a.mk-a{color:var(--accent)}' +
      '#mkbox textarea{width:100%;font:inherit;font-size:13.5px;padding:7px 9px;border:1px solid var(--rule);' +
      'border-radius:7px;background:var(--bg);color:var(--ink);resize:vertical;min-height:64px}' +
      '#mkbox code{font-family:ui-monospace,Menlo,monospace;font-size:12px;overflow-wrap:anywhere}' +
      '#mkbox code.mk-path{display:block;background:var(--boxbg);border:1px solid var(--rule);' +
      'border-radius:6px;padding:6px 8px;user-select:all}' +
      '#mkbox pre{font:12px/1.5 ui-monospace,Menlo,monospace;background:var(--boxbg);' +
      'border:1px solid var(--rule);border-radius:6px;padding:8px 10px;margin:6px 0 0;' +
      'max-height:220px;overflow:auto;white-space:pre-wrap;overflow-wrap:anywhere}' +
      '#mkbox .mk-note{border-inline-start:3px solid var(--warn);background:var(--boxbg);' +
      'padding:7px 10px;margin:10px 0;font-size:13px;border-radius:0 6px 6px 0}' +
      '#mkbox .mk-note.mk-bad{border-color:var(--danger)}' +
      '#mkbox .mk-note.mk-lock{border-color:var(--faint)}' +
      '#mkbox .mk-note.mk-fresh{border-color:var(--accent)}' +
      '#mkbox ul{margin:4px 0;padding-inline-start:20px}' +
      '#mkbox li{margin:2px 0}' +
      '#mkbox .mk-ok{color:var(--ok)}#mkbox .mk-no{color:var(--danger)}' +
      '#mkbox details summary{cursor:pointer;color:var(--dim);font-size:13px}' +
      '.mk-tocome{max-width:46rem;margin:2.5rem auto 3rem;padding:12px 16px;border:1px dashed var(--rule);' +
      'border-radius:10px;color:var(--dim);font:14px/1.6 system-ui,sans-serif;text-align:center}' +
      '.mk-tocome b{color:var(--ink)}' +
      // the chunk sheet of a book being made: shown, and shut where it writes
      '#chbox.mk-locked :is(#chsave,#chrevert,#chdel,#chundo,#chdivrow,#chfreerow,#chrgnrow,#chins,' +
      '#chwords button){display:none!important}' +
      '#chbox.mk-locked #chcol{pointer-events:none;opacity:.55}' +
      '#chbox.mk-locked .afoot{display:none}' +
      '#chbox.mk-locked :is(#chfa,#chkana,#chtr,#chvoc,#chen,#chwords input,#chwords textarea){opacity:.85}' +
      '#chbox .mk-chnote{border-inline-start:3px solid var(--accent);background:var(--boxbg);' +
      'padding:8px 10px;margin:0 0 10px;font-size:13px;line-height:1.55;border-radius:0 6px 6px 0}' +
      '#chbox .mk-ask textarea{width:100%;min-height:54px;font:inherit;padding:6px 8px}' +
      '#chbox .mk-ask .mk-said{font-size:12.5px;color:var(--dim);margin-inline-start:8px}';
    (document.head || document.documentElement).appendChild(s);
  }

  /* -------------------------------------------------------------- the panel */
  function build() {
    if (ui) return;
    style();
    var box = el('div');
    box.id = 'mkbox';
    box.hidden = true;
    box.setAttribute('role', 'dialog');
    box.setAttribute('aria-label', 'the making of this book');
    box.lang = 'en';
    box.dir = 'ltr';
    var u = {box: box};
    var head = el('h2', '', 'being made by an agent');
    head.appendChild(btn('✕', 'mk-b mk-x', function () { showPanel(false); }));
    head.lastChild.title = 'close (Esc)';
    box.appendChild(head);

    u.where = el('p', 'mk-where');
    u.on = el('p', 'mk-dim');
    u.notes = el('div');
    box.appendChild(u.where);
    box.appendChild(u.on);
    box.appendChild(u.notes);

    // look at it
    box.appendChild(el('h3', '', 'look at it'));
    var row = el('div', 'mk-row');
    u.look = btn('look at it now', 'mk-b mk-go', lookNow);
    u.look.title = 'rebuild this page from what the agent has written so far';
    row.appendChild(u.look);
    u.draft = btn('the PDF of these chapters', 'mk-b', draftNow);
    u.draft.title = 'typeset the chapters written so far, in a PDF beside the book';
    row.appendChild(u.draft);
    box.appendChild(row);
    u.built = el('p', 'mk-small');
    u.built.setAttribute('aria-live', 'polite');
    box.appendChild(u.built);
    u.pdf = el('p', 'mk-small');
    box.appendChild(u.pdf);

    // the chapters, and what the tools said
    u.chaptersH = el('h3', '', 'the chapters');
    u.chapters = el('p', 'mk-small');
    u.checksH = el('h3', '', 'what the tools said');
    u.checks = el('ul');
    box.appendChild(u.chaptersH);
    box.appendChild(u.chapters);
    box.appendChild(u.checksH);
    box.appendChild(u.checks);
    u.notesBox = el('details');
    u.notesBox.appendChild(el('summary', '', 'the agent’s notes (the end of NOTES.md)'));
    u.notesText = el('pre');
    u.notesBox.appendChild(u.notesText);
    box.appendChild(u.notesBox);

    // steering
    box.appendChild(el('h3', '', 'what to change from now on'));
    u.ask = el('textarea');
    u.ask.rows = 3;
    u.ask.placeholder = 'for example: keep the vocabulary lines shorter; write the meanings more literally';
    u.ask.setAttribute('aria-label', 'what to change from now on');
    box.appendChild(u.ask);
    var arow = el('div', 'mk-row');
    u.askBtn = btn('ask', 'mk-b mk-go', function () { sendAsk(u.ask.value, null, u.askBtn, u.askSaid, function () { u.ask.value = ''; }); });
    u.askSaid = el('span', 'mk-small');
    u.askSaid.setAttribute('aria-live', 'polite');
    arow.appendChild(u.askBtn);
    arow.appendChild(u.askSaid);
    box.appendChild(arow);
    u.asks = el('p', 'mk-small');
    box.appendChild(u.asks);

    // the folder and finishing: the computer's
    u.folderH = el('h3', '', 'the folder');
    u.folder = el('div');
    u.finishH = el('h3', '', 'finish');
    u.finish = el('div');
    box.appendChild(u.folderH);
    box.appendChild(u.folder);
    box.appendChild(u.finishH);
    box.appendChild(u.finish);

    document.body.appendChild(box);
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && panelOpen && !document.querySelector('#chbox:not([hidden])')) showPanel(false);
    });
    ui = u;
  }

  // under the header, wherever the header ends on this device (two rows in the
  // browser, taller when a phone's ⋯ is open), and no taller than what is left
  function place() {
    if (!ui) return;
    var h = document.querySelector('header');
    var top = Math.max(8, Math.round(h ? h.getBoundingClientRect().bottom + 8 : 56));
    ui.box.style.top = top + 'px';
    ui.box.style.maxHeight = 'calc(100vh - ' + (top + 12) + 'px)';
  }
  window.addEventListener('resize', function () { if (panelOpen) place(); });

  function showPanel(on) {
    build();
    panelOpen = !!on;
    ui.box.hidden = !on;
    store(OPEN_KEY, on ? '1' : null);
    if (on) { place(); paint(); refresh(); }
    Array.prototype.forEach.call(document.querySelectorAll('.mk-btn'), function (b) {
      b.setAttribute('aria-expanded', String(!!on));
    });
    schedule();
  }

  function buildIn(what, url, opts) {
    var b = opts.button;
    opts.say = function (msg, bad) {
      ui.built.textContent = msg + (bad && /failed/.test(msg)
        ? ' — the agent may have been writing just then: try again in a moment' : '');
      ui.built.className = 'mk-small' + (bad ? ' mk-no' : '');
    };
    if (window.Parseh && Parseh.buildBook) Parseh.buildBook(url, what, opts);
    else opts.say('this page cannot start a build', true);
    if (b) b.blur();
  }
  function lookNow() {
    // the page is what is rebuilt, so it is reloaded when it is done, and the panel comes back open
    buildIn('the reader', BASE + '__build', {what: 'html', book: bookName(), button: ui.look,
      done: function () { store(OPEN_KEY, '1'); setTimeout(function () { location.reload(); }, 400); }});
  }
  function draftNow() {
    buildIn('the PDF of these chapters', BASE + '__build', {what: 'draft', book: bookName(),
      button: ui.draft, done: function () { refresh(); }, failed: function () { refresh(); }});
  }
  function bookName() {
    return (S && S.name) || (document.title || '').replace(/\s*[—\-].*$/, '') || '';
  }

  // one ask, to the file the agent reads before every batch: the sentence it
  // is answered with is shown where the ask was made, and never thrown away
  function sendAsk(line, chunk, button, out, done) {
    line = String(line || '').trim();
    function say(text, bad) { out.textContent = text; out.classList.toggle('mk-no', !!bad); }
    if (!line) { say('write what to change first', true); return; }
    button.disabled = true;
    say('writing…');
    post(BASE + '__making/ask', {line: line, chunk: chunk})
      .then(function (j) {
        button.disabled = false;
        if (!j.ok) { say(j.error || 'it was refused', true); return; }
        say('written to ASKS.md at ' + j.at + ' — the agent reads it before its next batch');
        if (done) done();
        refresh();
      })
      .catch(function (e) {
        button.disabled = false;
        say((e && e.away) ? 'the computer cannot be reached: the ask was not written' : String(e), true);
      });
  }

  function chaptersLine(j) {
    var t = j.chapters || [];
    var parts = t.map(function (c) {
      return c.chapter + (c.paragraphs ? ' (' + c.paragraphs + (c.paragraphs === 1 ? ' paragraph)' : ' paragraphs)') : '');
    });
    var out = t.length ? 'The chapter table: ' + parts.join(', ') + '. ' : '';
    out += j.present && j.present.length ? 'Written so far: ' + j.present.join(', ') + '. ' : 'No chapter is written yet. ';
    if (j.to_come && j.to_come.length) out += 'Still to come: ' + j.to_come.join(', ') + '.';
    return out.trim();
  }

  // EACH PART OF THE PANEL IS DRAWN AGAIN ONLY WHEN WHAT IT SAYS HAS CHANGED.  The panel is asked
  // every few seconds, and a button replaced under a finger between the press and the release is a
  // press that goes nowhere -- as a text being read or selected would be lost.  What only ages
  // ("last written 3 minutes ago") is text in a node of its own, set every time.
  var sig = {};
  function changed(name, value) {
    var s = JSON.stringify(value);
    if (sig[name] === s) return false;
    sig[name] = s;
    return true;
  }

  function paint() {
    if (!ui || !S || !S.making) return;
    var j = S, d = j.draft || {};
    function since(t) { return ago((j.now - t) + (Date.now() - seen) / 1000); }
    ui.where.textContent = '';
    ui.where.appendChild(el('b', '', j.words));
    // a folder nobody has written in yet was only made, not written
    ui.where.appendChild(document.createTextNode(j.updated
      ? ' · ' + (j.stage === 'folder' ? 'made ' : 'last written ') + since(j.updated) : ''));
    ui.on.textContent = j.on ? 'on: ' + j.on : (j.stage === 'folder'
      ? 'The agent has not written anything yet. Open the folder in the agent you use, and tell it: read AGENTS.md and begin.'
      : '');
    // what is wrong or worth knowing, each in its own box
    var older = !!(j.stale && j.present && j.present.length);
    if (changed('notes', [j.updated_by_parseh, j.parseh, j.parseh_now, j.broken, older])) {
      ui.notes.textContent = '';
      var note = function (text, cls) { ui.notes.appendChild(el('div', 'mk-note' + (cls ? ' ' + cls : ''), text)); };
      if (j.updated_by_parseh)
        note('Parseh was updated during the making: it began under ' + j.parseh + ' and this is ' + j.parseh_now +
             '. The tools the agent calls may have changed under it.');
      if (j.broken) note(j.broken, 'mk-bad');
      // the page shown is older than the newest batch: the one thing look at it now is for
      if (older) note('The agent has written more since this page was built. Look at it now brings it.', 'mk-fresh');
    }
    // look at it
    var busy = !!(j.build && j.build.state === 'running');
    ui.look.disabled = busy;
    ui.draft.hidden = !d.can;
    ui.draft.disabled = busy;
    if (changed('pdf', [d.can, d.why, d.pdf, d.pdf_at, d.pdf_old])) {
      ui.pdf.textContent = '';
      ui.pdfAge = null;
      if (!d.can) {
        ui.pdf.textContent = d.why || '';
      } else if (d.pdf) {
        var a = el('a', 'mk-a', 'open the PDF');
        a.href = BASE + d.pdf + '?t=' + Math.round(d.pdf_at || 0);
        a.target = '_blank';
        a.rel = 'noopener';
        ui.pdf.appendChild(a);
        ui.pdfAge = el('span');
        ui.pdf.appendChild(ui.pdfAge);
      }
    }
    if (ui.pdfAge) ui.pdfAge.textContent = ' — made ' + since(d.pdf_at) +
      (d.pdf_old ? ', and older than the newest batch: make it again' : '');
    // the chapters and the tools' words
    if (changed('chapters', [j.chapters, j.present, j.to_come])) {
      var hasCh = (j.chapters && j.chapters.length) || (j.present && j.present.length);
      ui.chaptersH.hidden = ui.chapters.hidden = !hasCh;
      ui.chapters.textContent = hasCh ? chaptersLine(j) : '';
    }
    if (changed('checks', j.checks)) {
      var checks = j.checks || {}, names = Object.keys(checks);
      ui.checksH.hidden = ui.checks.hidden = !names.length;
      ui.checks.textContent = '';
      names.forEach(function (k) {
        var li = el('li');
        li.appendChild(el('b', '', k + ': '));
        li.appendChild(document.createTextNode(checks[k]));
        ui.checks.appendChild(li);
      });
    }
    if (changed('notestext', j.notes)) {
      ui.notesBox.hidden = !j.notes;
      ui.notesText.textContent = j.notes || '';
    }
    // the asks so far
    ui.asks.textContent = j.asks && j.asks.count
      ? j.asks.count + (j.asks.count === 1 ? ' ask' : ' asks') + ' written so far.' : 'No ask has been written yet.';
    if (changed('folder', [j.path, j.may && j.may.folder, j.said && j.said.folder])) paintFolder(j);
    if (changed('finish', [j.may, j.said && j.said.finish, j.finish, finishAsked])) paintFinish(j);
  }

  function paintFolder(j) {
    var f = ui.folder;
    f.textContent = '';
    if (j.path) {
      f.appendChild(el('code', 'mk-path', j.path));
      var row = el('div', 'mk-row');
      row.appendChild(btn('copy the path', 'mk-b', function () { if (window.Parseh) Parseh.copy(j.path, true); }));
      row.appendChild(btn('open the folder', 'mk-b', function () {
        post(BASE + '__making/open').then(function (o) { said(o.ok ? 'opened' : (o.error || 'it could not be opened'), !o.ok); })
          .catch(function (e) { said(String(e), true); });
      }));
      f.appendChild(row);
      f.appendChild(el('p', 'mk-small', 'Open this folder in the agent you use, and tell it: read AGENTS.md and begin. ' +
        'Parseh does not start an agent and does not choose one for you.'));
    } else {
      f.appendChild(el('div', 'mk-note mk-lock', 'The folder is on the computer Parseh runs on, and is opened there. ' +
        ((j.said && j.said.folder) || '')));
    }
  }

  function stepLine(s) {
    var li = el('li');
    var mark = s.state === 'done' ? '✓ ' : s.state === 'failed' ? '✗ ' : s.state === 'running' ? '… ' : '– ';
    var name = {check: 'checking every paragraph against its source', build: 'building the book'}[s.name] || s.name;
    li.appendChild(el('span', s.state === 'done' ? 'mk-ok' : s.state === 'failed' ? 'mk-no' : '', mark));
    li.appendChild(document.createTextNode(s.said ? s.said : name + (s.state === 'running' ? '…' : '')));
    (s.lines || []).forEach(function (l) {
      var sub = el('div', 'mk-small', l);
      sub.style.marginInlineStart = '1.3em';
      li.appendChild(sub);
    });
    return li;
  }

  function paintFinish(j) {
    var f = ui.finish, fin = j.finish || {};
    f.textContent = '';
    if (!j.may || !j.may.finish) {
      f.appendChild(el('div', 'mk-note mk-lock', 'Finish is done on the computer Parseh runs on. ' + ((j.said && j.said.finish) || '')));
      return;
    }
    var running = fin.state === 'running';
    if (fin.state && fin.state !== 'idle') {
      var ul = el('ul');
      (fin.steps || []).forEach(function (s) { ul.appendChild(stepLine(s)); });
      f.appendChild(ul);
      if (fin.said) f.appendChild(el('p', fin.ok ? 'mk-ok' : 'mk-small', fin.said));
    }
    if (fin.state === 'done' && fin.ok) {
      // the making is over: this page is an ordinary book now
      setTimeout(function () { store(OPEN_KEY, null); location.reload(); }, 1600);
      return;
    }
    if (running) return;
    f.appendChild(el('p', 'mk-small',
      'Finish checks every paragraph against its source and builds the whole book. When both are clean the ' +
      'making ends: this page edits again, and the agent has to stop.'));
    if (!finishAsked) {
      f.appendChild(btn('finish…', 'mk-b mk-danger', function () { finishAsked = true; paint(); }));
      return;
    }
    f.appendChild(el('p', '', 'Has the agent stopped?'));
    var row = el('div', 'mk-row');
    row.appendChild(btn('yes, finish now', 'mk-b mk-danger', function () {
      finishAsked = false;
      post(BASE + '__making/finish').then(function (o) {
        if (!o.ok) said(o.error || 'it was refused', true);
        refresh();
      }).catch(function (e) { said(String(e), true); });
    }));
    row.appendChild(btn('not yet', 'mk-b', function () { finishAsked = false; paint(); }));
    f.appendChild(row);
  }

  /* ---------------------------------------------- the header, and the page */
  var headBtns = [];
  function header() {
    if (headBtns.length) return;
    var h = document.querySelector('header');
    if (!h) return;
    function make(layout) {
      var b = el('button', 'mk-btn');
      b.type = 'button';
      b.setAttribute('data-layout', layout);
      b.setAttribute('aria-haspopup', 'dialog');
      b.setAttribute('aria-expanded', 'false');
      b.title = 'an agent is making this book: see how far it has got, look at it now, and steer it';
      b.appendChild(el('span', 'mk-dot'));
      b.appendChild(el('span', 'mk-txt', 'being made'));
      b.addEventListener('click', function () { showPanel(!panelOpen); });
      headBtns.push(b);
      return b;
    }
    // the browser's, in the second row beside the builds it is kin to; the phone's, in the first
    var rows = h.querySelectorAll('.hrow');
    var second = rows[1] || rows[0];
    var after = $('buildhtml');
    var bb = make('browser');
    if (after && after.parentNode) after.parentNode.insertBefore(bb, after.nextSibling);
    else if (second) second.insertBefore(bb, second.firstChild);
    var mb = make('mobile');
    mb.style.order = '8';
    if (rows[0]) rows[0].appendChild(mb);
  }

  function paintHeader() {
    if (!S || !S.making) return;
    header();
    var recent = S.updated && (S.now - S.updated) + (Date.now() - seen) / 1000 < 120;
    headBtns.forEach(function (b) {
      b.classList.toggle('mk-live', !!recent);
      b.classList.toggle('mk-new', !!(S.stale && S.present && S.present.length));
      b.querySelector('.mk-txt').textContent = 'being made · ' + S.words;
    });
  }

  // the chapters still to come, said under the last batch there is
  function toCome() {
    var main = document.querySelector('main');
    if (!main) return;
    var t = $('mktocome');
    if (!t) { t = el('section', 'mk-tocome'); t.id = 'mktocome'; main.appendChild(t); }
    t.textContent = '';
    var none = !(S.present && S.present.length);
    var fresh = S.stale && !none;
    if (fresh) {
      t.appendChild(el('b', '', 'More is written than this page shows.'));
      t.appendChild(document.createTextNode(' Look at it now brings it' + (S.to_come && S.to_come.length
        ? '; still to come after that: chapter ' + S.to_come.join(', chapter ') : '') + '.'));
    } else if (none) {
      t.appendChild(el('b', '', 'Nothing to read yet.'));
      t.appendChild(document.createTextNode(' The agent has not written a batch. What it writes shows here after look at it now.'));
    } else if (S.to_come && S.to_come.length) {
      t.appendChild(el('b', '', 'Still to come: '));
      t.appendChild(document.createTextNode('chapter ' + S.to_come.join(', chapter ') +
        '. The agent writes this book batch by batch; look at it now brings what it has written since.'));
    } else {
      t.appendChild(el('b', '', 'Still being made.'));
      t.appendChild(document.createTextNode(' The agent writes this book batch by batch; look at it now brings what it has written since.'));
    }
  }

  /* ---------------------------------------------------- no editing, and why */
  var WHY = 'Editing is off while an agent makes this book: it writes the book from its own files, so an edit made ' +
            'here would be erased by its next batch. Ask about this chunk instead.';
  function lockPage() {
    if (document.documentElement.hasAttribute('data-making')) return;
    document.documentElement.setAttribute('data-making', '');
    var pen = $('chpen');
    if (pen) pen.title = 'editing is off while an agent makes this book — this opens the chunk so you can ask about it';
    [['bookinfo', 'the details are changed after the making is finished'],
     ['rgn', 'an LLM’s answer would be erased by the agent’s next batch: ask about the chunk instead']]
      .forEach(function (p) {
        var b = $(p[0]);
        if (!b) return;
        b.disabled = true;
        b.title = 'this book is being made by an agent: ' + p[1];
      });
    // the pencil in a cloud is drawn afresh every time a cloud opens
    var cloud = $('cloud');
    function retitle() {
      Array.prototype.forEach.call(document.querySelectorAll('#cloud .mkedit'), function (e) {
        e.title = 'editing is off while an agent makes this book — this opens the chunk so you can ask about it';
      });
    }
    if (cloud && window.MutationObserver) new MutationObserver(retitle).observe(cloud, {childList: true, subtree: true});
    // and the sheet, on every opening
    var sheet = $('chbox');
    if (sheet && window.MutationObserver)
      new MutationObserver(function () { if (!sheet.hidden) lockSheet(sheet); })
        .observe(sheet, {attributes: true, attributeFilter: ['hidden']});
    // Ctrl+Enter saves a chunk: here it asks instead of writing
    window.addEventListener('keydown', function (e) {
      if (!(e.key === 'Enter' && (e.ctrlKey || e.metaKey))) return;
      var t = e.target && e.target.closest ? e.target.closest('#chbox') : null;
      if (!t || !document.documentElement.hasAttribute('data-making')) return;
      e.preventDefault();
      e.stopImmediatePropagation();
      var b = t.querySelector('.mk-ask button');
      if (b) b.click();
    }, true);
  }

  function chunkNumber() {
    var m = /chunk (\d+)/.exec(($('chref') || {}).textContent || '');
    return m ? +m[1] : -1;
  }
  function chunkAddress() {
    var n = chunkNumber();
    var row = n >= 0 ? document.querySelector('.row[data-c="' + n + '"]') : null;
    var para = row && row.closest ? row.closest('.para') : null;
    var key = para && para.dataset ? para.dataset.p : '';
    var lab = String((($('chref') || {}).textContent || '').split('·')[0] || '').trim();
    var bits = [];
    if (key && key.indexOf(':') > 0) { var k = key.split(':'); bits.push('chapter ' + k[0], 'paragraph ' + k[1]); }
    if (lab && !/^chunk \d+$/.test(lab)) bits.push('subparagraph ' + lab);
    if (n >= 0) bits.push('chunk ' + n);
    return bits.join(', ');
  }

  function lockSheet(sheet) {
    sheet.classList.add('mk-locked');
    ['chfa', 'chkana', 'chtr', 'chvoc', 'chen'].forEach(function (id) {
      var e = $(id);
      if (e) e.readOnly = true;
    });
    var free = $('chfree');
    if (free) free.disabled = true;
    Array.prototype.forEach.call(sheet.querySelectorAll('#chwords input, #chwords textarea'), function (e) { e.readOnly = true; });
    var main = sheet.querySelector('.chmain');
    if (!main) return;
    if (!main.querySelector('.mk-chnote')) {
      var n = el('div', 'mk-chnote', WHY);
      main.insertBefore(n, main.firstChild);
    }
    if (!main.querySelector('.mk-ask')) {
      var row = el('div', 'arow mk-ask');
      row.appendChild(el('span', 'alab', 'ask'));
      var ctl = el('div', 'actl');
      var ta = el('textarea');
      ta.rows = 2;
      ta.placeholder = 'what should change in this chunk?';
      ta.setAttribute('aria-label', 'ask about this chunk');
      var said_ = el('span', 'mk-said');
      said_.setAttribute('aria-live', 'polite');
      var b = btn('ask about this chunk', '', null);
      b.id = 'mkchask';
      b.addEventListener('click', function () {
        sendAsk(ta.value, {address: chunkAddress(), text: ($('chfa') || {}).value || ''}, b, said_,
                function () { ta.value = ''; });
      });
      ctl.appendChild(ta);
      var line = el('div');
      line.appendChild(b);
      line.appendChild(said_);
      ctl.appendChild(line);
      row.appendChild(ctl);
      var foot = main.querySelector('.afoot');
      main.insertBefore(row, foot || null);
    }
    var q = main.querySelector('.mk-ask textarea');
    if (q) q.value = '';
    var s = main.querySelector('.mk-ask .mk-said');
    if (s) s.textContent = '';
  }

  /* --------------------------------------------------------- asking, timing */
  function apply(j) {
    var was = S;
    S = j;
    seen = Date.now();
    if (!j || !j.ok) return;
    if (!j.making) {
      // it ended while the page was open: an ordinary book now
      if (was && was.making) { store(OPEN_KEY, null); location.reload(); }
      return;
    }
    if (j.name === undefined) j.name = '';
    lockPage();
    paintHeader();
    toCome();
    if (panelOpen) paint();
  }
  function refresh() {
    return ask(STATUS, {cache: 'no-store'}).then(apply).catch(function () {});
  }
  function schedule() {
    clearTimeout(timer);
    timer = setTimeout(function () {
      if (!document.hidden) refresh();
      schedule();
    }, panelOpen ? 4000 : 20000);
  }

  refresh().then(function () {
    if (S && S.making && stored(OPEN_KEY) === '1') showPanel(true);
  });
  schedule();
  window.ParsehMaking = {refresh: refresh, open: function () { if (S && S.making) showPanel(true); }};
})();

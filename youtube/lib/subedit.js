/* Parseh — the transcript editor of the add-a-video page.

     ParsehSubedit.open(opts) -> Promise<string|null>   the transcript, edited

   WHAT YOUTUBE HEARD IS OFTEN NOT WHAT WAS SAID, and it is cut in the wrong
   places: a sentence split across two captions, a caption that starts three
   seconds late, two words glued to the caption before.  Every road out of
   the add page — the prompt, the blank-gloss draft, the checker — reads the
   pasted panel as it stands, so a panel that is wrong makes a video that is
   wrong, and the only way to mend it used to be typing in the textarea with
   nothing to hear.

   So: a small Subtitle Edit (nikse.dk), for the one moment it is wanted.
   THIS IS A STEP OF ADDING A VIDEO AND OF NOTHING ELSE.  There is no editor
   for a video already in the player: its transcript is what its annotations
   were checked against, and a door that could rewrite it would quietly
   unmake that check.  Here nothing has been built yet.

   It round-trips through the box.  The captions are read from the pasted
   text and written back to it by the server (POST <base>/api/transcript,
   check_annotations.parse_transcript_text and transcript_text), so the panel
   this page hands on is a panel in the one format everything downstream
   already reads, and no road needed a single change.

   A TENTH OF A SECOND AT A TIME.  Each row carries the six steps the book's
   timing editor and the card kit's cut editor carry — −1 −.5 −.1, the time
   itself, +.1 +.5 +1 — and the panel keeps what they make: the clock line
   takes a fraction (check_annotations.TIMESTAMP reads "0:08.4" and stamp_of
   writes it), and the player seeks to one as readily as to a whole second.
   A panel of whole seconds still goes back as whole seconds.  The video
   stands over the list and ▶ plays a caption from its start to where the
   next one begins, which is how a nudge is answered: press, play, press
   again.

   Plain ES2017, no build step; served at /youtube/lib/subedit.js. */
(function () {
  'use strict';
  if (window.ParsehSubedit) return;

  var YT_API = 'https://www.youtube.com/iframe_api';

  /* ---------------------------------------------------------------- small */
  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }
  function button(text, attrs) {
    var b = el('button', null, text);
    b.type = 'button';
    Object.keys(attrs || {}).forEach(function (k) { b.setAttribute(k, attrs[k]); });
    return b;
  }
  // A caption's start, as a transcript line writes it — the same rule as
  // check_annotations.stamp_of, fraction and all: "0:08", "1:02:03", and
  // "0:08.4" where the start is not a whole second.  Written only where
  // there is one, so a panel of whole seconds goes back as it came.
  function stamp(sec) {
    var t = Math.max(0, Math.round((+sec || 0) * 1000) / 1000);
    var n = Math.floor(t), frac = Math.round((t - n) * 1000) / 1000;
    if (frac >= 0.9995) { n += 1; frac = 0; }
    var two = function (x) { return (x < 10 ? '0' : '') + x; };
    var out = n >= 3600 ? (Math.floor(n / 3600) + ':' + two(Math.floor(n / 60) % 60) + ':' + two(n % 60))
                        : (Math.floor(n / 60) + ':' + two(n % 60));
    return frac ? out + frac.toFixed(3).slice(1).replace(/0+$/, '') : out;
  }
  // …and back: "8", "8.4", "0:08", "0:08.4", "1:02:03".  NaN for anything else.
  function seconds(text) {
    var t = String(text == null ? '' : text).trim().replace(',', '.');
    if (!t) return NaN;
    if (/^\d+(\.\d{1,3})?$/.test(t)) return +t;
    var m = /^(\d+):([0-5]?\d)(?::([0-5]?\d))?(\.\d{1,3})?$/.exec(t);
    if (!m) return NaN;
    var whole = m[3] != null ? +m[1] * 3600 + +m[2] * 60 + +m[3] : +m[1] * 60 + +m[2];
    return m[4] ? Math.round((whole + +m[4]) * 1000) / 1000 : whole;
  }

  /* --------------------------------------------------------------- the API */
  function open(opts) {
    return new Promise(function (resolve) { start(opts || {}, resolve); });
  }

  function start(opts, resolve) {
    var base = String(opts.base || '/youtube');
    var lang = String(opts.lang || '');
    var vid = String(opts.video || '');      // a YouTube id, or "" for a film
    var caps = [], done = false;
    var player = null, playReady = false, stopAt = null, ticker = 0;

    var root = el('div', 'se-root');
    var box = el('div', 'se-box');
    box.setAttribute('role', 'dialog');
    box.setAttribute('aria-modal', 'true');
    box.setAttribute('aria-label', 'Edit the transcript');
    root.appendChild(box);

    var head = el('div', 'se-head');
    head.appendChild(el('b', null, 'The transcript'));
    var count = el('span', 'se-count');
    var stat = el('span', 'se-stat');
    stat.setAttribute('role', 'status');
    var closeBtn = button('✕', {'class': 'se-x', 'title': 'leave it as it was (Esc)',
                                     'aria-label': 'Cancel'});
    [count, el('span', 'se-sp'), stat, closeBtn].forEach(function (n) { head.appendChild(n); });
    box.appendChild(head);

    // the video itself, where there is one to show
    var stage = el('div', 'se-stage');
    if (vid) {
      // THE API REPLACES THE ELEMENT IT IS GIVEN with the iframe, keeping
      // its id and nothing else -- so the box that gives the player its
      // size is the one AROUND the element, never the element itself, or
      // the frame would come back unstyled and full of the page
      var hold = el('div', 'se-yt');
      var seat = el('div');
      seat.id = 'se-yt-' + Math.random().toString(36).slice(2);
      hold.appendChild(seat);
      stage.appendChild(hold);
      box.appendChild(stage);
    }

    var note = el('div', 'se-note');
    note.innerHTML =
      'A caption runs until the next one begins, so moving one moves where the one before ' +
      'it ends. The buttons move it by a second, a half or a <b>tenth</b>; the time itself ' +
      'can be typed — <code>0:08</code>, <code>0:08.4</code>, <code>1:02:03</code>, or a ' +
      'number of seconds.' +
      (vid ? ' <b>▶</b> plays the caption, so a nudge can be answered by ear.' : '') +
      ' Nothing is written until <b>Use this transcript</b>.';
    box.appendChild(note);

    var tools = el('div', 'se-tools');
    var shiftIn = el('input', 'se-shift');
    shiftIn.type = 'number';
    shiftIn.step = '0.1';
    shiftIn.value = '0';
    shiftIn.setAttribute('aria-label', 'seconds to move every caption by');
    var shiftBtn = button('move them all', {'class': 'se-btn se-quiet',
      'title': 'add these seconds to every caption’s start — a panel copied from a ' +
               're-uploaded video is often late or early by the same amount throughout'});
    tools.appendChild(el('span', 'se-tlab', 'shift'));
    tools.appendChild(shiftIn);
    tools.appendChild(el('span', 'se-tlab', 's'));
    tools.appendChild(shiftBtn);
    tools.appendChild(el('span', 'se-sp'));
    var addBtn = button('+ caption at the end', {'class': 'se-btn se-quiet'});
    tools.appendChild(addBtn);
    // THE ONE BUTTON THAT READS THE WHOLE TRANSCRIPT.  An automatic
    // transcript is cut where YouTube ran out of room and carries no
    // punctuation; this asks the server to cut it into sentences instead and
    // time each one again (youtube/lib/tidy.py).  It is a guess, so it is a
    // button and not a rule, and the way back is kept for one press.
    var tidyBtn = button('\u2728 tidy up', {'class': 'se-btn se-quiet',
      'title': 'cut the captions into sentences and time them again \u2014 a guess, ' +
               'and one you can undo'});
    var undoBtn = button('undo the tidy', {'class': 'se-btn se-quiet'});
    // THE OTHER ROAD, and the one the add page already walks for the
    // glossing: the toolbox writes the prompt, a model reads the transcript,
    // the answer comes back into the box.  The two fail differently -- the
    // algorithm cannot hear a misheard word and will never invent one, a
    // model hears the sense and may invent anything -- so both are offered
    // and neither is the default.
    var llmBtn = button('or with an LLM\u2026', {'class': 'se-btn se-quiet',
      'title': 'copy a prompt that asks a model to do the same thing, and paste its ' +
               'answer back here'});
    tidyBtn.hidden = undoBtn.hidden = true;
    tools.appendChild(tidyBtn);
    tools.appendChild(undoBtn);
    tools.appendChild(llmBtn);
    box.appendChild(tools);

    // the prompt, and the box its answer comes back in
    var llm = el('div', 'se-llm');
    llm.hidden = true;
    llm.appendChild(el('div', 'se-llmnote',
      'Copy the prompt into any model, then paste its whole answer here. What comes ' +
      'back is read as an ordinary transcript, so look it over before using it \u2014 ' +
      'a model may mend a misheard word, and may invent one.'));
    var llmRow = el('div', 'se-llmrow');
    var copyBtn = button('copy the prompt again', {'class': 'se-btn se-quiet'});
    var llmStat = el('span', 'se-stat');
    llmRow.appendChild(copyBtn);
    llmRow.appendChild(llmStat);
    llm.appendChild(llmRow);
    var answer = el('textarea', 'se-answer');
    answer.rows = 4;
    answer.placeholder = '0:08\n\u2026the answer, pasted whole\u2026';
    answer.setAttribute('aria-label', 'the model\u2019s answer');
    llm.appendChild(answer);
    var useAnswer = button('use the answer', {'class': 'se-btn se-use'});
    var dropAnswer = button('close', {'class': 'se-btn se-quiet'});
    var llmFoot = el('div', 'se-llmrow');
    llmFoot.appendChild(useAnswer);
    llmFoot.appendChild(dropAnswer);
    llm.appendChild(llmFoot);
    box.appendChild(llm);

    var list = el('div', 'se-list');
    box.appendChild(list);

    var foot = el('div', 'se-foot');
    var useBtn = button('Use this transcript', {'class': 'se-btn se-use'});
    var cancelBtn = button('Cancel', {'class': 'se-btn'});
    var fstat = el('span', 'se-stat');
    fstat.setAttribute('role', 'status');
    [useBtn, cancelBtn, fstat].forEach(function (n) { foot.appendChild(n); });
    box.appendChild(foot);

    /* ---- drawing ---- */
    function say(msg, bad, where) {
      var s = where || stat;
      s.textContent = msg || '';
      s.classList.toggle('se-bad', !!bad);
    }
    // the first caption whose start does not come after the one before it:
    // the panel is read in order, and a video whose captions go backwards is
    // refused by the checker long after this page could have said so
    function outOfOrder() {
      for (var i = 1; i < caps.length; i++)
        if (!(caps[i].start > caps[i - 1].start)) return i;
      return -1;
    }
    function paintOrder() {
      var bad = outOfOrder();
      Array.prototype.forEach.call(list.children, function (row, i) {
        row.classList.toggle('se-wrong', i === bad);
      });
      count.textContent = caps.length + (caps.length === 1 ? ' caption' : ' captions');
      if (bad > 0)
        say('caption ' + (bad + 1) + ' starts at ' + stamp(caps[bad].start) +
            ', which is not after the one before it (' + stamp(caps[bad - 1].start) + ')',
            true, fstat);
      else say('', false, fstat);
      return bad;
    }
    // THE NUDGES, ON EITHER SIDE OF THE TIME.  The same steps as the book's
    // timing editor and the card kit's cut editor -- a second, a half, a
    // tenth -- so a hand that has timed either already knows them.  A tenth
    // is the finest because a tenth is what the panel carries: the clock
    // line takes a fraction (check_annotations.TIMESTAMP, stamp_of), and
    // the player seeks to one as readily as to a whole second.
    var STEPS = [-1, -0.5, -0.1, 0.1, 0.5, 1];
    function label(d) { return (d > 0 ? '+' : '−') + String(Math.abs(d)).replace(/^0/, ''); }
    function nudge(i, d) {
      return button(label(d), {'data-a': 'by', 'data-d': String(d),
        'title': (d > 0 ? 'later by ' : 'earlier by ') + Math.abs(d) + ' s'});
    }

    function rowFor(i) {
      var c = caps[i];
      var row = el('div', 'se-row');
      row.dataset.i = String(i);
      row.appendChild(el('span', 'se-n', String(i + 1)));

      var when = el('span', 'se-when');
      STEPS.filter(function (d) { return d < 0; })
           .forEach(function (d) { when.appendChild(nudge(i, d)); });
      var at = el('input', 'se-at');
      at.value = stamp(c.start);
      at.setAttribute('aria-label', 'caption ' + (i + 1) + ', when it starts');
      at.addEventListener('change', function () {
        var n = seconds(at.value);
        if (isNaN(n)) { at.value = stamp(c.start); say('a time is 0:08, or 1:02:03.5, or a number of seconds', true); return; }
        c.start = n;
        at.value = stamp(n);
        say('');
        paintOrder();
      });
      when.appendChild(at);
      STEPS.filter(function (d) { return d > 0; })
           .forEach(function (d) { when.appendChild(nudge(i, d)); });
      row.appendChild(when);

      var text = el('textarea', 'se-text');
      text.rows = 1;
      text.value = c.text;
      text.dir = 'auto';
      text.setAttribute('aria-label', 'caption ' + (i + 1) + ', what is said');
      text.addEventListener('input', function () { c.text = text.value; fit(text); });
      row.appendChild(text);

      var acts = el('span', 'se-acts');
      acts.appendChild(button('▶', {'data-a': 'play',
        'title': 'play this caption — from its start to where the next one begins'}));
      acts.appendChild(button('✂', {'data-a': 'split',
        'title': 'cut this caption in two where the cursor is in its text'}));
      acts.appendChild(button('⤓', {'data-a': 'join',
        'title': 'join the caption after this one to it'}));
      acts.appendChild(button('✕', {'data-a': 'del', 'title': 'delete this caption'}));
      row.appendChild(acts);
      return row;
    }
    function fit(t) {
      t.style.height = 'auto';
      t.style.height = Math.min(160, t.scrollHeight + 2) + 'px';
    }
    function paint(focus) {
      list.textContent = '';
      caps.forEach(function (_c, i) { list.appendChild(rowFor(i)); });
      Array.prototype.forEach.call(list.querySelectorAll('.se-text'), fit);
      paintOrder();
      if (focus != null) {
        var row = list.children[Math.max(0, Math.min(caps.length - 1, focus))];
        if (row) {
          var t = row.querySelector('.se-text');
          if (t) { t.focus(); t.setSelectionRange(t.value.length, t.value.length); }
          row.scrollIntoView({block: 'nearest'});
        }
      }
    }

    /* ---- what the buttons do ---- */
    function play(i) {
      if (!player || !playReady) { say('the video is still loading', true); return; }
      var to = i + 1 < caps.length ? caps[i + 1].start : null;
      try {
        player.seekTo(Math.max(0, caps[i].start), true);
        player.playVideo();
      } catch (x) { say('the video would not play', true); return; }
      stopAt = to;
      say('playing caption ' + (i + 1));
    }
    function watch() {
      if (!player || stopAt == null) return;
      var t = 0;
      try { t = +player.getCurrentTime() || 0; } catch (x) { return; }
      if (t >= stopAt - 0.05) {
        stopAt = null;
        try { player.pauseVideo(); } catch (x) {}
        say('');
      }
    }
    function split(i, row) {
      var t = row.querySelector('.se-text');
      var at = t.selectionStart;
      var before = t.value.slice(0, at).trim(), after = t.value.slice(at).trim();
      if (!before || !after) { say('put the cursor where the caption should be cut in two', true); return; }
      // the second half starts halfway to the next caption -- a guess, and
      // the one a hand would make; the nudges and \u25b6 are how it stops
      // being a guess
      var next = i + 1 < caps.length ? caps[i + 1].start : caps[i].start + 4;
      var mid = Math.round((caps[i].start + next) / 2 * 10) / 10;
      if (!(mid > caps[i].start)) mid = Math.round((caps[i].start + 1) * 10) / 10;
      caps[i].text = before;
      caps.splice(i + 1, 0, {start: mid, text: after, chapter: null});
      say('cut in two — set where the second half begins');
      paint(i + 1);
    }
    function join(i) {
      if (i + 1 >= caps.length) { say('there is no caption after this one', true); return; }
      var next = caps.splice(i + 1, 1)[0];
      caps[i].text = (caps[i].text + ' ' + next.text).replace(/\s+/g, ' ').trim();
      say('joined');
      paint(i);
    }
    function remove(i) {
      if (caps.length === 1) { say('a transcript needs one caption at least', true); return; }
      caps.splice(i, 1);
      say('deleted');
      paint(Math.min(i, caps.length - 1));
    }
    // one caption moved, by one of the six steps: the box shows where it
    // now is, and the row says so at once so a press can be answered by ear
    // against the video playing beside it
    function moveBy(i, d, row) {
      var c = caps[i];
      c.start = Math.max(0, Math.round((c.start + d) * 1000) / 1000);
      var at = row.querySelector('.se-at');
      if (at) at.value = stamp(c.start);
      say('caption ' + (i + 1) + ' at ' + stamp(c.start));
      paintOrder();
    }
    list.addEventListener('click', function (e) {
      var b = e.target.closest('button[data-a]');
      if (!b) return;
      var row = b.closest('.se-row'), i = +row.dataset.i;
      var what = b.dataset.a;
      if (what === 'play') play(i);
      else if (what === 'by') moveBy(i, parseFloat(b.dataset.d), row);
      else if (what === 'split') split(i, row);
      else if (what === 'join') join(i);
      else if (what === 'del') remove(i);
    });
    shiftBtn.addEventListener('click', function () {
      var by = parseFloat(shiftIn.value);
      if (!isFinite(by) || !by) { say('say how many seconds — negative to move them earlier', true); return; }
      var first = caps[0].start + by;
      if (first < 0) { say('that would take the first caption before the video begins', true); return; }
      // a tenth is kept, as everywhere else here: a panel that is late by
      // 1.4 s is moved by 1.4 s and not by one
      caps.forEach(function (c) { c.start = Math.max(0, Math.round((c.start + by) * 1000) / 1000); });
      say('every caption moved by ' + by + ' s');
      paint();
    });
    // what the captions were before the tidy, for one press of undo
    var before = null;
    function tidyUp() {
      tidyBtn.disabled = true;
      say('reading the whole transcript\u2026');
      var was = caps.map(function (c) { return {start: c.start, text: c.text, chapter: c.chapter}; });
      post('/api/transcript', {lang: lang, tidy: true, captions: was}).then(function (j) {
        tidyBtn.disabled = false;
        if (done) return;
        if (!j.ok) { say(j.error || 'the tidy was refused', true); return; }
        before = was;
        caps = (j.captions || []).map(function (c) {
          return {start: +c.start || 0, text: String(c.text || ''), chapter: c.chapter || null};
        });
        undoBtn.hidden = false;
        say((j.notes || []).join(' \u00b7 ') || 'tidied');
        paint();
      }, function (err) {
        tidyBtn.disabled = false;
        if (!done) say(err.message || String(err), true);
      });
    }
    tidyBtn.addEventListener('click', tidyUp);

    var thePrompt = '';
    function askPrompt(again) {
      var was = caps.map(function (c) { return {start: c.start, text: c.text, chapter: c.chapter}; });
      if (thePrompt && again) { copyOut(); return; }
      say('writing the prompt\u2026');
      post('/api/transcript', {lang: lang, prompt: true, captions: was}).then(function (j) {
        if (done) return;
        if (!j.ok) { say(j.error || 'the prompt could not be written', true); return; }
        thePrompt = j.prompt || '';
        llm.hidden = false;
        say('');
        copyOut();
        answer.focus();
      }, function (err) { if (!done) say(err.message || String(err), true); });
    }
    function copyOut() {
      // raw: the prompt is a fenced transcript, and squeezing its whitespace
      // would hand the model one unreadable line (lib/parseh.js says so)
      if (window.Parseh && Parseh.copy) Parseh.copy(thePrompt, true);
      llmStat.textContent = 'copied \u00b7 ' + thePrompt.length + ' characters';
      llmStat.classList.remove('se-bad');
    }
    llmBtn.addEventListener('click', function () { askPrompt(false); });
    copyBtn.addEventListener('click', function () { askPrompt(true); });
    dropAnswer.addEventListener('click', function () { llm.hidden = true; });
    useAnswer.addEventListener('click', function () {
      var text = answer.value.trim();
      if (!text) { llmStat.textContent = 'paste the answer first'; llmStat.classList.add('se-bad'); answer.focus(); return; }
      useAnswer.disabled = true;
      llmStat.textContent = 'reading it\u2026';
      llmStat.classList.remove('se-bad');
      var was = caps.map(function (c) { return {start: c.start, text: c.text, chapter: c.chapter}; });
      post('/api/transcript', {lang: lang, transcript: text}).then(function (j) {
        useAnswer.disabled = false;
        if (done) return;
        if (!j.ok) { llmStat.textContent = j.error || 'that is not a transcript'; llmStat.classList.add('se-bad'); return; }
        before = was;
        caps = (j.captions || []).map(function (c) {
          return {start: +c.start || 0, text: String(c.text || ''), chapter: c.chapter || null};
        });
        undoBtn.hidden = false;
        llm.hidden = true;
        // A MODEL MAY HAVE CHANGED THE WORDS, which is sometimes the point
        // (a misheard name) and sometimes the trouble.  Nothing here forbids
        // it -- the whole reason to ask a model is that it hears the sense --
        // but the reader is told how much moved.
        say(was.length + ' captions became ' + caps.length + letters(was, caps));
        paint();
      }, function (err) {
        useAnswer.disabled = false;
        if (!done) { llmStat.textContent = err.message || String(err); llmStat.classList.add('se-bad'); }
      });
    });
    // how far the words themselves moved, in plain letters
    function letters(a, b) {
      var bare = function (cs) {
        return cs.map(function (c) { return c.text; }).join(' ')
          .replace(/[\s.,!?…؟۔،؛;:。！？]+/g, '');
      };
      var x = bare(a), y = bare(b);
      if (x === y) return ', and not one letter of the words changed';
      var d = Math.abs(x.length - y.length);
      return ' \u2014 and the words are not the same: ' +
             (d ? d + ' letters more or fewer' : 'the same length, different letters') +
             '. Look them over.';
    }
    undoBtn.addEventListener('click', function () {
      if (!before) return;
      caps = before.map(function (c) { return {start: c.start, text: c.text, chapter: c.chapter}; });
      before = null;
      undoBtn.hidden = true;
      say('back as it was');
      paint();
    });
    addBtn.addEventListener('click', function () {
      var last = caps.length ? caps[caps.length - 1] : null;
      caps.push({start: last ? last.start + 4 : 0, text: '', chapter: null});
      say('a caption at the end — give it its words and its time');
      paint(caps.length - 1);
    });

    /* ---- the two ways out ---- */
    function finish(text) {
      if (done) return;
      done = true;
      clearInterval(ticker);
      document.removeEventListener('keydown', onKey, true);
      try { if (player && player.pauseVideo) player.pauseVideo(); } catch (x) {}
      try { if (player && player.destroy) player.destroy(); } catch (x) {}
      root.remove();
      resolve(text);
    }
    useBtn.addEventListener('click', function () {
      if (paintOrder() > 0) return;
      var words = caps.filter(function (c) { return c.text.trim(); });
      if (!words.length) { say('every caption is empty', true, fstat); return; }
      useBtn.disabled = true;
      say('checking…', false, fstat);
      post('/api/transcript', {captions: caps.map(function (c) {
        return {start: c.start, text: c.text, chapter: c.chapter || null};
      }), lang: lang}).then(function (j) {
        useBtn.disabled = false;
        if (!j.ok) { say(j.error || 'the transcript was refused', true, fstat); return; }
        finish(j.text);
      }, function (err) {
        useBtn.disabled = false;
        say(err.message || String(err), true, fstat);
      });
    });
    cancelBtn.addEventListener('click', function () { finish(null); });
    closeBtn.addEventListener('click', function () { finish(null); });
    function onKey(e) {
      if (e.key !== 'Escape' || done) return;
      // the cut editor is over this one, and Escape is its own
      if (document.querySelector('.pc-root')) return;
      e.preventDefault();
      finish(null);
    }
    document.addEventListener('keydown', onKey, true);

    /* ---- the server, and the video ---- */
    function post(path, body) {
      return fetch(base + path, {method: 'POST', headers: {'Content-Type': 'application/json'},
                                 body: JSON.stringify(body)})
        .then(function (r) { return r.json().catch(function () { return {ok: false, error: r.status + ' ' + r.statusText}; }); });
    }
    function mountPlayer() {
      if (!vid) return;
      var id = stage.querySelector('.se-yt > div').id;
      var make = function () {
        player = new YT.Player(id, {
          videoId: vid,
          playerVars: {rel: 0, playsinline: 1},
          events: {onReady: function () { playReady = true; }}
        });
      };
      if (window.YT && window.YT.Player) { make(); return; }
      var was = window.onYouTubeIframeAPIReady;
      window.onYouTubeIframeAPIReady = function () {
        if (typeof was === 'function') { try { was(); } catch (x) {} }
        make();
      };
      if (!document.querySelector('script[data-se-yt]')) {
        var tag = document.createElement('script');
        tag.src = YT_API;
        tag.setAttribute('data-se-yt', '1');
        document.head.appendChild(tag);
      }
      // offline, or YouTube unreachable: say so where the video would be
      // rather than leave a black rectangle and "still loading" under every
      // \u25b6.  The list itself works regardless: the times are typed and
      // nudged whether or not there is anything to play them against
      setTimeout(function () {
        if (done || player) return;
        var h = stage.querySelector('.se-yt');
        if (h) h.replaceWith(el('div', 'se-noyt',
          'the video did not load \u2014 the times can still be typed'));
      }, 8000);
    }

    document.body.appendChild(root);
    say('reading the transcript…');
    post('/api/transcript', {transcript: String(opts.transcript || ''), lang: lang})
      .then(function (j) {
        if (done) return;
        if (!j.ok) { say(j.error || 'the transcript could not be read', true); useBtn.disabled = true; return; }
        caps = (j.captions || []).map(function (c) {
          return {start: +c.start || 0, text: String(c.text || ''), chapter: c.chapter || null};
        });
        // the button appears only where there is something behind it: the
        // server says whether this language gives the cue it reads, and why
        // not where it does not
        tidyBtn.hidden = !j.can_tidy;
        if (j.why) tidyBtn.title = j.why;
        say('');
        paint();
        mountPlayer();
        ticker = setInterval(watch, 120);
      }, function (err) {
        if (!done) { say(err.message || String(err), true); useBtn.disabled = true; }
      });
  }

  window.ParsehSubedit = {open: open, stamp: stamp, seconds: seconds};
})();

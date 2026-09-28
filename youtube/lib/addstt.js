// SPDX-License-Identifier: GPL-3.0-or-later
/* Parseh — the speech to text of the add-a-video page.

     ParsehAddStt.mount(opts) -> {sourceChanged, langChanged, modelChanged, redraw,
                                  busy, guardEdit, wave, videoAdded}

   ONE OPTIONAL BLOCK in the transcript's step, and nothing else of Parseh's
   knows it is there: it writes the transcript into the box the page already
   has, in the format the page already reads, and the video is added the way a
   pasted transcript adds one.  A person who never installs speech to text
   sees a link to where it is installed; nothing is fetched, downloaded or
   asked of anyone because this page was opened.

   WHAT IT READS.  POST /lookup/api/speech, the slim slice Settings -> Speech to
   text keeps (lib/getstt.py summary): is it installed, which models, how the
   processor may be chosen, which languages.  It is asked again whenever this
   page is looked at again (window focus), so an install made in another tab
   shows here with no reload.  Only the models that are ready are offered
   (never more than the two), and the NVIDIA GPU only when the computer says
   the card is ready; CPU always works.

   WHAT IT DOES, by the routes under <base>/api/transcribe/ (lib/sttjobs.py):

     a film on this computer:  start -> status ... -> result.  The computer
        reads the file itself: nothing is played and any browser will do.  The
        path is a path on THAT computer's disk, whoever is looking at this page.
     a YouTube video:  start (the computer says which video: its own id, never
        this page's guess) -> the video is put in a frame here -> the person
        presses "Start recording" (the browser only shares a tab for a click,
        and the frame has to be there first) -> youtube/lib/tabcapture.js
        plays it from its beginning while it records this tab's sound, and
        each chunk goes to audio; the marks and the shape of the sound go
        before the last piece; then status ... -> result.

   THE RESULT GOES IN THE BOX THE PAGE HAS.  Never over words the person wrote
   without asking (before it starts, and again when it arrives if the box
   changed meanwhile), never adds the video, and whatever LLM prompt was
   prepared is out of date (opts.invalidate).  The box is tied to the video, the
   language and the model that made it: change one of them and the tie is
   dropped, quietly.  Changing the processor alone changes nothing about the
   transcript, so it does not.

   WHAT IT NEVER DOES: put a control on a video already added (this page is
   the only one that has it), fail into a traceback (every refusal and every
   end of a capture is a sentence), overwrite the box on a failure, or start a
   second job while one runs.

   Plain ES2017, no build step, a classic script: served at
   /youtube/lib/addstt.js, after youtube/lib/tabcapture.js. */
(function () {
  'use strict';
  if (window.ParsehAddStt) return;

  var SLICE = '/lookup/api/speech';
  var SETTINGS = '/settings/speech/';
  var POLL_MS = 1200;              // how often a running job is asked how it is
  var DEADLINE_MS = 8000;          // one ask: a silent computer is not a refusal
  var PIECE_TRIES = 3;             // a piece of the recording is sent this often before giving up
  var PIECE_DEADLINE_MS = 40000;   // one piece is 5 s of sound, 160 KB
  var READY_MS = 8 * 60 * 1000;    // a loaded video nobody records: the computer would give up at 10 minutes
  var PREFS = 'yt_add_stt';        // the model and the processor last chosen, in this browser only
  var STATE = 'yt_add_stt_state';  // what a reload must find again: the tie, the held waveform, a running job

  /* ---------------------------------------------------------------- words */
  var SAY_START_OVER = 'Replace the transcript in the box with a new one made by speech to text? ' +
                       'What is written there now is lost.';
  var SAY_RESULT_OVER = 'The transcript in the box changed while this was running. Replace it with ' +
                        'the one speech to text made? What is written there now is lost.';
  var SAY_LOCKED = 'a transcription is running — cancel it first';
  var SAY_ABSENT = 'Speech to text is not set up on this computer. It is optional: Parseh can write ' +
                   'a transcript for you, here on this computer and without sending anything anywhere, ' +
                   'but pasting one works exactly as it always did.';
  var SAY_FILM = 'The film named above is read from its file on the computer Parseh runs on, so ' +
                 'nothing is played and any browser will do. The path is a path on that computer’s ' +
                 'disk, even when this page is open on another device.';
  var SAY_YOUTUBE = 'The video plays here in real time, from its beginning, while this page records ' +
                    'its sound — an hour of video takes an hour. Your browser will ask which tab to ' +
                    'share: choose this tab, and turn on “Share tab audio”. Keep this tab in front ' +
                    'until it is done. The sound is processed on this computer and deleted once the ' +
                    'transcript is made.';
  var SAY_READY = 'The video is loaded. Press Start recording: it plays here in real time, from its ' +
                  'beginning, while this page records its sound. Your browser will ask which tab to ' +
                  'share — choose this tab, and turn on “Share tab audio”. Keep this tab in front ' +
                  'until it is done.';
  var SAY_KEEP = 'Keep this tab in front until it is done. Cancel stops the recording and writes nothing.';
  var SAY_NO_TAB = 'Automatic transcription of a YouTube video records this tab’s sound while the ' +
                   'video plays, and this browser cannot: ';
  var SAY_STALLED = 'The video stopped moving for ten seconds, so the recording was stopped and ' +
                    'nothing was written.';
  var SAY_HIDDEN = 'This tab is not in front. Bring it back, or the recording may fall behind.';
  var SAY_LEFT = 'The recording was stopped when the page was left, so nothing was written. Press ' +
                 'Transcribe to start again.';
  var SAY_GIVE_UP = 'The recording was not started, so the transcription was let go. Press ' +
                    'Transcribe to begin again.';
  var SAY_SILENT = 'Parseh has not answered for a moment — still waiting.';

  /* ---------------------------------------------------------------- small */
  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }
  function button(text, id, cls) {
    var b = el('button', cls || 'wbtn', text);
    b.type = 'button';
    b.id = id;
    return b;
  }
  // A small string that says whether two texts are the same: enough to know
  // "the box still holds what was put in it", without keeping a second copy of
  // a 150 KB transcript in the browser's storage.
  function hash(s) {
    var h = 5381;
    s = String(s == null ? '' : s);
    for (var i = 0; i < s.length; i++) h = ((h << 5) + h + s.charCodeAt(i)) | 0;
    return (h >>> 0).toString(36) + ':' + s.length;
  }
  function clock(sec) {
    sec = Math.max(0, Math.floor(sec || 0));
    var h = Math.floor(sec / 3600), m = Math.floor(sec / 60) % 60, s = sec % 60;
    var two = function (x) { return (x < 10 ? '0' : '') + x; };
    return h ? h + ':' + two(m) + ':' + two(s) : m + ':' + two(s);
  }
  // THE BROWSER'S STORAGE IS A CONVENIENCE, never something the page depends
  // on: it can be blocked, full or gone, and every read and write is guarded.
  function load(key) {
    try { var v = JSON.parse(localStorage.getItem(key) || 'null'); return v && typeof v === 'object' ? v : {}; }
    catch (e) { return {}; }
  }
  function store(key, v) { try { localStorage.setItem(key, JSON.stringify(v)); } catch (e) {} }
  function forget(key) { try { localStorage.removeItem(key); } catch (e) {} }

  // One ask of the computer, with a deadline of its own: what comes back is
  // {status, j}; a server that answers nothing rejects, and that is not the
  // same as one that refuses.  `body` is JSON, or a typed array of sound.
  function ask(url, body, ms, outer) {
    var ctl = new AbortController();
    var timer = setTimeout(function () { ctl.abort(); }, ms || DEADLINE_MS);
    function stop() { ctl.abort(); }
    if (outer) {
      if (outer.aborted) ctl.abort();
      else outer.addEventListener('abort', stop, {once: true});
    }
    var opts = {method: 'POST', signal: ctl.signal};
    if (body && ArrayBuffer.isView(body)) {
      opts.headers = {'Content-Type': 'application/octet-stream'};
      opts.body = body;
    } else {
      opts.headers = {'Content-Type': 'application/json'};
      opts.body = JSON.stringify(body || {});
    }
    return fetch(url, opts).then(function (r) {
      return r.text().then(function (t) {
        var j = null;
        try { j = JSON.parse(t); } catch (e) {}
        return {status: r.status, j: j && typeof j === 'object' ? j
                : {ok: false, error: 'Parseh answered with something that was not an answer.'}};
      });
    }).then(function (x) {
      clearTimeout(timer);
      if (outer) outer.removeEventListener('abort', stop);
      return x;
    }, function (e) {
      clearTimeout(timer);
      if (outer) outer.removeEventListener('abort', stop);
      throw e;
    });
  }

  // Why the browser cannot record a tab, in the words of the one module that
  // knows -- or that the module did not even load.
  function tabProblem() {
    var TC = window.ParsehTabCapture;
    if (!TC || !TC.capability) return 'the part of this page that records a tab did not load';
    var c = TC.capability();
    return c.ok ? '' : c.why;
  }
  // What a failed capture says.  tabcapture's own messages are sentences; the
  // browser's are "Permission denied".
  function whyCapture(err) {
    var name = err && err.name, msg = err && err.message;
    if (name === 'NotAllowedError' || name === 'SecurityError')
      return 'The browser was not allowed to record this tab. Press Start recording again, choose ' +
             'this tab, and press “Share”.';
    if (name === 'NotFoundError' || name === 'NotReadableError' || name === 'AbortError')
      return 'The browser could not record this tab (' + name + '). Press Start recording to try again.';
    // an Error of tabcapture's own is a sentence already (the browser's are
    // DOMExceptions with a name of their own, and say things like "TypeError")
    if (msg && (!name || name === 'Error')) {
      msg = msg.charAt(0).toUpperCase() + msg.slice(1);
      return /[.!?]$/.test(msg) ? msg : msg + '.';
    }
    return 'The recording could not be made' + (name ? ' (' + name + ')' : '') + '.';
  }

  /* ---------------------------------------------------------------- mount */
  function mount(o) {
    var root = o.root, base = o.base || '/youtube';
    var toast = o.toast || function () {};
    var confirmOver = o.confirm || function (m) { return window.confirm(m); };
    var route = function (name) { return base + '/api/transcribe/' + name; };

    // THE STATE.  `phase`: idle | starting | loading (the video is being put
    // in its frame) | ready (it is there, waiting for the click that shares the
    // tab) | recording | sending (the end of the recording) | working (the
    // computer is listening) | stopping.  `run` counts starts and ends, so that
    // an answer that arrives after a Cancel finds it is not wanted.
    var S = {slice: null, phase: 'idle', run: 0, job: '', kind: '', key: '', lang: '', model: '',
             startHash: '', video: '', player: null, rec: null, sent: 0, timer: 0, readyTimer: 0,
             abort: null, held: null, said: '', pct: null};
    var AUTO = null;   // {source, lang, model, hash}: the box holds what THIS video, language and model made
    var WAVE = null;   // {job, source}: the shape of the sound, held by the computer for this video
    var LOCKED = null; // while a job runs: [[element, value]] what the controls read when it began
    var lastToast = 0;

    /* ---------------------------------------------------------- the block */
    root.textContent = '';
    root.hidden = true;
    var title = el('p', 'stt-title');
    title.appendChild(el('b', null, 'Speech to text'));
    title.appendChild(el('span', 'stt-opt', 'optional'));
    var absent = el('div', 'stt-absent');
    absent.id = 'stt_absent';
    absent.appendChild(el('p', 'fieldnote', SAY_ABSENT));
    var setup = el('a', 'wbtn small quiet', 'Set up speech to text');
    setup.id = 'stt_setup';
    setup.href = SETTINGS;
    setup.target = '_blank';
    setup.rel = 'noopener';
    var why = el('p', 'fieldnote warn');
    why.id = 'stt_why';
    absent.appendChild(el('div', 'row')).appendChild(setup);

    var form = el('div', 'stt-form');
    form.id = 'stt_form';
    var intro = el('p', 'fieldnote', 'Have this computer listen to the video and write the transcript. ' +
                   'It is done on this computer: nothing is sent anywhere.');
    var selModel = el('select'), selProc = el('select');
    selModel.id = 'stt_model';
    selProc.id = 'stt_proc';
    var rowModel = el('div', 'row'), rowProc = el('div', 'row');
    var lblModel = el('label', 'inline', 'Model '), lblProc = el('label', 'inline', 'Processing ');
    lblModel.appendChild(selModel);
    lblProc.appendChild(selProc);
    rowModel.appendChild(lblModel);
    rowProc.appendChild(lblProc);
    var modelNote = el('span', 'fieldnote'), now = el('span', 'fieldnote'), gpu = el('span', 'fieldnote warn');
    var langNote = el('span', 'fieldnote'), busyNote = el('span', 'fieldnote warn'), how = el('p', 'fieldnote');
    modelNote.id = 'stt_modelnote';
    now.id = 'stt_now';
    gpu.id = 'stt_gpu';
    langNote.id = 'stt_lang';
    busyNote.id = 'stt_busy';
    how.id = 'stt_how';
    var go = button('Transcribe', 'stt_go'), rec = button('Start recording', 'stt_rec');
    var cancel = button('Cancel', 'stt_cancel', 'wbtn quiet');
    var use = button('Use the new transcript instead', 'stt_use', 'wbtn small quiet');
    var actions = el('div', 'row');
    [go, rec, cancel].forEach(function (b) { actions.appendChild(b); });
    var frame = el('div', 'stt-frame');
    frame.id = 'stt_frame';
    var bar = el('div', 'stt-bar');
    bar.id = 'stt_bar';
    bar.setAttribute('role', 'progressbar');
    bar.setAttribute('aria-valuemin', '0');
    bar.setAttribute('aria-valuemax', '100');
    bar.appendChild(el('i'));
    var sayEl = el('p', 'stt-say');
    sayEl.id = 'stt_say';
    sayEl.setAttribute('role', 'status');
    sayEl.setAttribute('aria-live', 'polite');
    [intro, rowModel, modelNote, rowProc, now, gpu, busyNote, langNote, how, actions, frame, bar, sayEl,
     el('div', 'row')].forEach(function (n) { form.appendChild(n); });
    form.lastChild.appendChild(use);

    var tied = el('p', 'fieldnote');
    tied.id = 'stt_tied';
    var noteEl = el('div', 'note');
    noteEl.id = 'stt_note';
    noteEl.setAttribute('aria-live', 'polite');
    [title, absent, why, form, tied, noteEl].forEach(function (n) { root.appendChild(n); });

    /* -------------------------------------------------- what is remembered */
    var prefs = load(PREFS);
    function savePrefs() { store(PREFS, {model: selModel.value, processing: selProc.value}); }
    function persist() {
      store(STATE, {auto: AUTO, wave: WAVE,
                    job: S.job ? {id: S.job, kind: S.kind, key: S.key, lang: S.lang, model: S.model,
                                  hash: S.startHash} : null});
    }
    var was = load(STATE);

    /* ------------------------------------------------------- what is asked */
    function key(src) { return src.kind + ':' + src.value; }
    function models() { return ((S.slice && S.slice.models) || []).filter(function (m) { return m.ready; }).slice(0, 2); }
    function modelLabel(id) {
      var m = ((S.slice && S.slice.models) || []).filter(function (x) { return x.id === id; })[0];
      return m ? m.label : String(id || '');
    }
    function card() {
      return ((S.slice && S.slice.processing) || []).filter(function (p) { return p.id === 'cuda'; })[0] || null;
    }
    function autoNow() {
      return ((S.slice && S.slice.processing) || []).filter(function (p) { return p.id === 'auto'; })[0] || null;
    }
    function fill() {
      var have = models().map(function (m) { return m.id; });
      var pick = selModel.value || prefs.model || (S.slice && S.slice.default_model);
      selModel.textContent = '';
      models().forEach(function (m) {
        var op = el('option', null, m.label + ' — ' + m.tag);
        op.value = m.id;
        selModel.appendChild(op);
      });
      var dflt = S.slice && S.slice.default_model;
      selModel.value = have.indexOf(pick) >= 0 ? pick : (have.indexOf(dflt) >= 0 ? dflt : (have[0] || ''));
      var c = card(), proc = selProc.value || prefs.processing || 'auto';
      selProc.textContent = '';
      [['auto', 'Automatic — recommended'], ['cpu', 'CPU']].concat(c && c.ready ? [['cuda', 'NVIDIA GPU']] : [])
        .forEach(function (p) {
          var op = el('option', null, p[1]);
          op.value = p[0];
          selProc.appendChild(op);
        });
      selProc.value = ['auto', 'cpu'].concat(c && c.ready ? ['cuda'] : []).indexOf(proc) >= 0 ? proc : 'auto';
    }

    /* ------------------------------------------------------------ painting */
    function say(text, pct) {
      S.said = text || '';
      S.pct = pct == null ? null : pct;
      paint();
    }
    function note(text, kind) {
      noteEl.className = 'note' + (kind ? ' ' + kind : '');
      noteEl.textContent = text || '';
      noteEl.hidden = !text;
    }
    function paint() {
      var s = S.slice, idle = S.phase === 'idle';
      var src = o.source(), lang = o.lang();
      var ok = !!(s && s.installed);
      var yt = src.kind === 'yt';
      var noLang = ok && s.languages && s.languages[lang.code] === false;
      var noTab = ok && yt ? tabProblem() : '';
      var mode = !src.kind || !s ? 'off' : !ok ? 'absent'
        : (idle && noLang) ? 'nolang' : (idle && noTab) ? 'notab' : 'form';
      root.hidden = mode === 'off';
      root.setAttribute('data-state', mode === 'form' ? S.phase : mode);
      absent.hidden = mode !== 'absent';
      form.hidden = mode !== 'form';
      why.hidden = mode !== 'nolang' && mode !== 'notab';
      if (mode === 'nolang') {
        why.textContent = 'Speech to text cannot listen for ' + lang.name +
          '. Paste the transcript instead, as always.';
      } else if (mode === 'notab') {
        why.textContent = SAY_NO_TAB + noTab + '. Pasting the transcript works as it always did.';
      }
      if (mode === 'absent' && s) {
        var rt = s.runtime || {};
        setup.href = s.settings || SETTINGS;
        // an install that needs attention says what: "built by an older Parseh"
        var extra = rt.state === 'ready' ? ' The program is installed, but a model still has to be added.'
          : rt.state && rt.state !== 'absent' && rt.why ? ' ' + rt.why : '';
        absent.firstChild.textContent = SAY_ABSENT + extra;
      }
      if (mode === 'form') {
        var film = src.kind === 'film', c = card(), a = autoNow(), m = selModel.value;
        var info = models().filter(function (x) { return x.id === m; })[0];
        modelNote.textContent = info ? info.hint : '';
        modelNote.hidden = !info || !info.hint;
        // "Processing: Automatic · currently CPU", said in the person's terms
        var proc = selProc.value, cname = (c && c.name) || 'the NVIDIA graphics card';
        now.textContent = 'Processing: ' + (proc === 'cpu' ? 'CPU'
          : proc === 'cuda' ? 'NVIDIA GPU · ' + cname
          : 'Automatic · currently ' + (a && a.now === 'cuda' ? cname : 'CPU'));
        // a card that is there but not ready is said, once, with what is missing
        gpu.hidden = !(c && !c.ready && c.name && c.why);
        gpu.textContent = gpu.hidden ? '' : c.why;
        busyNote.hidden = !(idle && s.busy);
        busyNote.textContent = busyNote.hidden ? '' : 'Speech to text is busy right now (a transcription or an ' +
          'install is running): starting one now may be refused.';
        langNote.textContent = '';
        // the language's own name is set apart (<bdi>), and the dash stays out of
        // it: inside, a right-to-left name would take the dash to its far side
        // (English is "English — English" in the selector; here it is said once)
        var own = lang.native && lang.native !== lang.name ? lang.native : '';
        langNote.appendChild(document.createTextNode('Listens for ' + lang.name + (own ? ' — ' : '')));
        if (own) langNote.appendChild(el('bdi', null, own));
        langNote.appendChild(document.createTextNode(', the language chosen above.'));
        how.textContent = film ? SAY_FILM : S.phase === 'ready' ? SAY_READY
          : (S.phase === 'recording' || S.phase === 'sending') ? SAY_KEEP : SAY_YOUTUBE;
        go.hidden = !idle;
        rec.hidden = S.phase !== 'ready';
        cancel.hidden = !(S.phase === 'loading' || S.phase === 'ready' || S.phase === 'recording'
                          || S.phase === 'sending' || S.phase === 'working');
        frame.hidden = !(S.phase === 'loading' || S.phase === 'ready' || S.phase === 'recording');
        var live = S.phase !== 'idle' && S.said !== '';
        sayEl.hidden = !live;
        sayEl.textContent = live ? S.said : '';
        bar.hidden = !(S.phase === 'recording' || S.phase === 'sending' || S.phase === 'working');
        bar.classList.toggle('wait', S.pct == null);
        bar.firstChild.style.width = S.pct == null ? '' : Math.max(0, Math.min(100, S.pct)) + '%';
        if (S.pct == null) bar.removeAttribute('aria-valuenow');
        else bar.setAttribute('aria-valuenow', String(Math.round(S.pct)));
        use.hidden = !S.held;
        use.parentNode.hidden = !S.held;
      }
      // what the box holds, and whose it is
      var box = o.transcript();
      tied.hidden = !AUTO || !box.trim();
      if (!tied.hidden) {
        tied.textContent = hash(box) === AUTO.hash
          ? 'The transcript in the box was made by speech to text (' + modelLabel(AUTO.model) +
            '). Read it through: it is yours to edit before the video is added.'
          : 'The transcript in the box began as speech to text (' + modelLabel(AUTO.model) +
            ') and has been edited since.';
      }
    }

    /* ------------------------------------------------- locking while a job runs */
    function targets() {
      var out = (o.lock || []).map(function (sel) { return document.querySelector(sel); }).filter(Boolean);
      return out.concat([selModel, selProc]);
    }
    function lock(on) {
      var list = targets();
      if (on) LOCKED = list.map(function (e) { return [e, e.value]; });
      else LOCKED = null;
      list.forEach(function (e) {
        e.classList.toggle('stt-locked', on);
        if (on) e.setAttribute('aria-disabled', 'true'); else e.removeAttribute('aria-disabled');
        if (e.tagName === 'INPUT') e.readOnly = on;
      });
    }
    // A control that is locked still looks like one, so it answers: the click
    // or the key is turned away, said once, and a value that was changed by
    // any other means is put back.  Not `disabled`: a disabled control answers
    // nothing at all, and says nothing about why.
    function turnedAway(e) {
      if (!LOCKED) return;
      var t = e.target;
      if (!t || !t.closest) return;
      var hit = targets().some(function (x) { return x === t || x.contains(t); });
      if (!hit) return;
      if (e.type === 'keydown' && (e.key === 'Tab' || e.key === 'Shift' || e.key === 'Escape')) return;
      // a text box that is read-only can still be clicked into, and its words
      // selected and copied; only a key that would change it, or a paste, is
      // an attempt
      if (t.tagName === 'INPUT') {
        if (e.type === 'mousedown' || e.type === 'click') return;
        if (e.type === 'keydown' && !(e.key.length === 1 && !e.ctrlKey && !e.metaKey)
            && e.key !== 'Backspace' && e.key !== 'Delete') return;
      }
      if (e.type === 'change' || e.type === 'input') {
        LOCKED.forEach(function (p) { if (p[0] === t) t.value = p[1]; });
      }
      e.preventDefault();
      e.stopPropagation();
      if (Date.now() - lastToast > 1500) { lastToast = Date.now(); toast(SAY_LOCKED, true); }
    }
    ['mousedown', 'click', 'keydown', 'paste', 'change', 'input'].forEach(function (type) {
      document.addEventListener(type, turnedAway, true);
    });

    /* ------------------------------------------------------- ties and drops */
    function drop(what) {
      AUTO = null;
      persist();
      note('The transcript in the box is no longer tied to speech to text: the ' + what + ' changed. It ' +
           'stays as it is, and a new transcription asks before it replaces it.');
    }
    function sourceChanged() {
      var k = key(o.source());
      if (AUTO && AUTO.source !== k) drop('video');
      if (WAVE && WAVE.source !== k) { WAVE = null; persist(); }
      paint();
    }
    function langChanged() {
      if (AUTO && AUTO.lang !== o.lang().code) drop('language');
      paint();
    }
    function modelChanged() {
      savePrefs();
      if (AUTO && AUTO.model !== selModel.value) drop('model');
      paint();
    }
    selModel.addEventListener('change', modelChanged);
    selProc.addEventListener('change', function () { savePrefs(); paint(); });

    /* ------------------------------------------------------------ the job */
    function post(name, body, ms, outer) { return ask(route(name), body, ms, outer); }
    function stopTimers() {
      clearTimeout(S.timer);
      clearTimeout(S.readyTimer);
      S.timer = S.readyTimer = 0;
    }
    // Everything of a job that is over, put away: no timer, no frame, no
    // player, no tab left shared, nothing remembered, the controls free.
    function tidy() {
      stopTimers();
      S.run++;
      var p = S.player;
      S.player = null;
      S.rec = null;
      if (S.abort) { try { S.abort.abort(); } catch (e) {} S.abort = null; }
      if (p) {
        try { p.pauseVideo(); } catch (e) {}
        try { if (p.destroy) p.destroy(); } catch (e) {}
      }
      frame.textContent = '';
      S.job = S.kind = S.key = S.video = '';
      S.sent = 0;
      S.phase = 'idle';
      lock(false);
      persist();
    }
    function cancelServer(job) {
      if (!job) return Promise.resolve();
      return post('cancel', {job: job}, 6000).then(function () {}, function () {});
    }
    // A job that ended badly: the sentence, the box left exactly as it was.
    function fail(run, text, tell) {
      if (run !== S.run) return;
      var job = S.job;
      tidy();
      if (tell !== false) cancelServer(job);
      note(text || 'Transcription failed.', 'bad');
      paint();
    }
    function begin() {
      if (S.phase !== 'idle') return;
      var src = o.source(), lang = o.lang(), film = src.kind === 'film';
      if (!src.value) {
        toast(film ? 'name the film on this machine' : 'paste the URL', true);
        if (o.focusSource) o.focusSource();
        return;
      }
      var model = selModel.value;
      if (!model) return;
      var box = o.transcript();
      // NEVER OVER A PERSON'S WORDS WITHOUT ASKING: before anything is
      // recorded or uploaded, not after an hour of it
      if (box.trim() && (!AUTO || hash(box) !== AUTO.hash) && !confirmOver(SAY_START_OVER)) return;
      note('');
      S.held = null;
      var run = ++S.run;
      S.kind = src.kind;
      S.key = key(src);
      S.lang = lang.code;
      S.model = model;
      S.startHash = hash(o.transcript());
      S.phase = 'starting';
      lock(true);
      say('Starting…');
      var body = {source: film ? 'film' : 'youtube', lang: lang.code, model: model, processing: selProc.value};
      if (film) body.path = src.value; else body.url = src.value;
      post('start', body).then(function (r) {
        if (run !== S.run) { if (r.j && r.j.job) cancelServer(r.j.job); return; }
        var j = r.j;
        if (!j.ok) {
          tidy();
          note(j.error + (j.code === 'busy' ? ' Wait for it to finish, or stop it from the page that started it.' : ''),
               'bad');
          if (j.code === 'not-installed' || j.code === 'no-model') refresh();
          paint();
          return;
        }
        S.job = j.job;
        S.video = j.video_id || '';
        persist();
        if (film) { S.phase = 'working'; say(j.say || 'Getting ready…'); poll(run); return; }
        S.phase = 'loading';
        say('Loading the video…');
        window.ParsehTabCapture.embed(frame, S.video, {}).then(function (player) {
          if (run !== S.run) { try { if (player.destroy) player.destroy(); } catch (e) {} return; }
          S.player = player;
          S.phase = 'ready';
          say('');
          // the computer gives up on a recording that never starts; so does this page, first
          S.readyTimer = setTimeout(function () { fail(run, SAY_GIVE_UP); }, READY_MS);
        }, function (err) {
          fail(run, (err && err.message ? err.message : 'The video could not be loaded') +
                    (/[.!?]$/.test((err && err.message) || '') ? '' : '.'));
        });
      }, function () {
        if (run !== S.run) return;
        tidy();
        note('Parseh did not answer, so nothing was started.', 'bad');
        paint();
      });
    }

    // THE RECORDING.  Called from the click itself: the browser shares a tab
    // only in answer to one, and the video was put in its frame before it.
    function record() {
      if (S.phase !== 'ready' || !S.player) return;
      var TC = window.ParsehTabCapture, run = S.run, job = S.job;
      clearTimeout(S.readyTimer);
      var marks = [], peaks = null, ctl = new AbortController(), started = false;
      S.abort = ctl;
      S.sent = 0;
      S.phase = 'recording';
      say('Waiting for you to share this tab…');
      var r = TC.record({
        player: S.player, wave: true, pcm: true, keepShare: false, unmute: true,
        onStart: function () { started = true; if (run === S.run) say('Recording 0:00…', 0); },
        onProgress: function (sec, total) {
          if (run !== S.run) return;
          say('Recording ' + clock(sec) + ' / ' + clock(total) + '…', total > 0 ? 100 * sec / total : null);
        },
        onChunk: function (pcm, offset, signal) { return sendPiece(run, pcm, offset, signal); },
        onMark: function (frameNo, sec) { marks.push([frameNo, sec]); },
        onPeaks: function (p, rate) { peaks = {rate: rate, peaks: p}; }
      });
      S.rec = r;
      r.promise.then(function (res) {
        if (run !== S.run) return;
        if (res.reason === 'stalled') { fail(run, SAY_STALLED); return; }
        if (res.reason !== 'ended') { fail(run, 'The recording ended early, so nothing was written.'); return; }
        finishRecording(run, job, marks, peaks, ctl);
      }, function (err) {
        if (run !== S.run) return;
        // A share that was refused, or came without its sound, or a browser that
        // could not open its 16 kHz half: nothing has played yet, so the video
        // and the job are still good, and the button can be pressed again.
        if (!started && S.player) {
          S.rec = null;
          S.abort = null;
          S.phase = 'ready';
          note(whyCapture(err), 'bad');
          say('');
          S.readyTimer = setTimeout(function () { fail(run, SAY_GIVE_UP); }, READY_MS);
          return;
        }
        fail(run, whyCapture(err));
      });
    }
    // One piece of the sound, sent and answered before the next is handed over.
    // A piece sent twice is written once by the computer, so one that timed out
    // is simply sent again; a gap asks to be sent from where the computer is.
    function sendPiece(run, pcm, offset, signal) {
      var tries = 0;
      function once(data, at) {
        if (run !== S.run) return Promise.reject(new Error('The recording was stopped.'));
        var url = route('audio') + '?job=' + encodeURIComponent(S.job) + '&offset=' + at;
        return ask(url, data, PIECE_DEADLINE_MS, signal).then(function (r) {
          var j = r.j;
          if (j.ok) { S.sent = Math.max(S.sent, at + data.length); return; }
          if (j.code === 'gap' && typeof j.have === 'number') {
            var from = j.have - offset;
            if (from >= 0 && from < pcm.length && tries++ < PIECE_TRIES) return once(pcm.subarray(from), j.have);
            throw new Error('A piece of the recording went missing on its way, so it was stopped.');
          }
          throw new Error(j.error || 'The recording could not be sent.');
        }, function (e) {
          if (signal && signal.aborted) throw e;
          if (++tries < PIECE_TRIES) {
            return new Promise(function (ok) { setTimeout(ok, 600 * tries); }).then(function () { return once(data, at); });
          }
          throw new Error('Parseh did not answer while the recording was being sent, so it was stopped.');
        });
      }
      return once(pcm, offset);
    }
    function finishRecording(run, job, marks, peaks, ctl) {
      // the video has done its part: out of the frame, and the tab is free
      var p = S.player;
      S.player = null;
      if (p) { try { if (p.destroy) p.destroy(); } catch (e) {} }
      frame.textContent = '';
      S.phase = 'sending';
      say('Sending the end of the recording…', null);
      // a refusal is thrown as its sentence; a computer that says nothing, as
      // that; `needed: false` is for what nothing depends on
      function step(name, body, needed, ms) {
        return post(name, body, ms, ctl.signal).then(function (r) {
          if (r.j.ok || !needed) return r;
          throw new Error(r.j.error || 'The recording could not be sent.');
        }, function () {
          if (!needed) return {j: {ok: false}};
          throw new Error('Parseh did not answer while the recording was being sent.');
        });
      }
      // marks first (they put the sound on the video's own clock), then the shape
      // of the sound (nothing depends on it: a video with no waveform is still a
      // video), and the last piece -- empty, the recording is all there -- seals it
      step('marks', {job: job, marks: marks}, true, DEADLINE_MS).then(function () {
        return peaks ? step('wave', {job: job, rate: peaks.rate, peaks: peaks.peaks}, false, 4 * DEADLINE_MS) : null;
      }).then(function () {
        var url = route('audio') + '?job=' + encodeURIComponent(job) + '&offset=' + S.sent + '&last=1';
        return ask(url, new Uint8Array(0), DEADLINE_MS * 2, ctl.signal);
      }).then(function (r) {
        if (run !== S.run) return;
        if (!r.j.ok) { fail(run, r.j.error || 'The recording could not be sealed.'); return; }
        S.phase = 'working';
        say('Audio captured.', null);
        poll(run);
      }, function (e) {
        if (run !== S.run) return;
        fail(run, (e && e.message) || 'The recording could not be sent.');
      });
    }

    // THE COMPUTER LISTENING: asked how it is, over and over, each ask with a
    // deadline of its own.  A computer that says nothing is waited for and said
    // so; only what it says ends a job.
    function poll(run) {
      var misses = 0;
      (function tick() {
        if (run !== S.run) return;
        post('status', {job: S.job}).then(function (r) {
          if (run !== S.run) return;
          var j = r.j;
          misses = 0;
          if (S.phase === 'working' && noteEl.textContent === SAY_SILENT) note('');
          if (!j.ok) { fail(run, j.error || 'That transcription is not here any more.', false); return; }
          if (j.state === 'done') { finishJob(run); return; }
          if (j.state === 'failed') { fail(run, j.error, false); return; }
          if (j.state === 'cancelled') { fail(run, 'The transcription was cancelled.', false); return; }
          say(j.say, j.pct);
          S.timer = setTimeout(tick, POLL_MS);
        }, function () {
          if (run !== S.run) return;
          if (++misses >= 3) note(SAY_SILENT, 'warn');
          S.timer = setTimeout(tick, POLL_MS);
        });
      })();
    }
    function finishJob(run) {
      post('result', {job: S.job}).then(function (r) {
        if (run !== S.run) return;
        if (!r.j.ok) { fail(run, r.j.error || 'The transcript could not be read.', false); return; }
        deliver(run, r.j);
      }, function () {
        if (run !== S.run) return;
        fail(run, 'Parseh did not answer when the transcript was asked for. Press Transcribe to try again.', false);
      });
    }
    // The transcript arrives.  If the box was changed while this ran it is not
    // overwritten without a word: the person is asked, and a "no" keeps what is
    // written and offers the new one to be taken later.
    function deliver(run, res) {
      var box = o.transcript(), t = {job: S.job, key: S.key, lang: S.lang, model: S.model};
      var over = box.trim() && hash(box) !== S.startHash;
      tidy();
      if (over && !confirmOver(SAY_RESULT_OVER)) {
        S.held = {res: res, t: t};
        note('The transcript in the box was kept as you have it. The one speech to text made is not lost yet: ' +
             'you can still use it, until you leave this page.', 'warn');
        paint();
        return;
      }
      apply(res, t);
    }
    function apply(res, t) {
      S.held = null;
      o.setTranscript(res.text);
      AUTO = {source: t.key, lang: t.lang, model: t.model, hash: hash(o.transcript())};
      if (res.wave && res.wave.held) WAVE = {job: t.job, source: t.key};
      persist();
      o.invalidate();
      var n = res.captions;
      var out = 'The transcript is in the box' + (n ? ': ' + n + ' caption' + (n === 1 ? '' : 's') : '') +
                '. Read it through and edit it as you like — the video has not been added.';
      var extra = (res.notes || []).length ? ' ' + res.notes.join(' ') : '';
      note(out + extra + (res.warning ? ' ' + res.warning : ''), res.warning ? 'warn' : 'good');
      paint();
    }
    use.addEventListener('click', function () { if (S.held) apply(S.held.res, S.held.t); });

    /* ----------------------------------------------- Cancel, and leaving */
    function stop(text) {
      if (S.phase === 'idle' || S.phase === 'starting' || S.phase === 'stopping') return;
      var job = S.job, r = S.rec;
      S.phase = 'stopping';
      S.run++;
      stopTimers();
      if (S.abort) { try { S.abort.abort(); } catch (e) {} }
      say('Stopping…');
      (r ? r.cancel() : Promise.resolve()).then(function () {
        return cancelServer(job);
      }).then(function () {
        tidy();
        note(text || 'The transcription was cancelled. The transcript in the box was not touched.');
        paint();
      });
    }
    go.addEventListener('click', begin);
    rec.addEventListener('click', record);
    cancel.addEventListener('click', function () { stop(); });
    // a page left during a recording ends it: the sound would go on arriving from nowhere
    window.addEventListener('pagehide', function () {
      var live = S.phase === 'loading' || S.phase === 'ready' || S.phase === 'recording' || S.phase === 'sending';
      if (!live || S.kind !== 'yt' || !S.job || !navigator.sendBeacon) return;
      try { navigator.sendBeacon(route('cancel'), new Blob([JSON.stringify({job: S.job})], {type: 'application/json'})); }
      catch (e) {}
      forget(STATE);
    });
    document.addEventListener('visibilitychange', function () {
      if (S.phase !== 'recording') return;
      if (document.hidden) note(SAY_HIDDEN, 'warn'); else if (noteEl.textContent === SAY_HIDDEN) note('');
    });

    /* ------------------------------------------------- the computer's word */
    function refresh() {
      return ask(SLICE, {}, DEADLINE_MS).then(function (r) { return r.j && r.j.ok ? r.j : null; },
                                              function () { return null; }).then(function (s) {
        // asked again while it is being used, it would only change under a job's feet
        if (S.phase !== 'idle') return;
        if (s || !S.slice) S.slice = s;
        if (S.slice) fill();
        paint();
      });
    }
    function again() { if (document.visibilityState !== 'hidden' && S.phase === 'idle') refresh(); }
    window.addEventListener('focus', again);
    document.addEventListener('visibilitychange', again);

    /* ----------------------------------------- what a reload finds again */
    // A job the computer is still listening for is taken up again; a recording
    // cannot be (its tab share and its video are gone with the page), so it is
    // let go, and said.
    function resume() {
      var src = o.source(), lang = o.lang(), j = was.job;
      if (!j || !j.id) return;
      post('status', {job: j.id}).then(function (r) {
        var s = r.j;
        function over(text, kind) {
          if (text) note(text, kind);
          if (text && s.state !== 'failed') cancelServer(j.id);
          S.job = '';
          persist();
          paint();
        }
        if (!s.ok || s.state === 'cancelled') { over(''); return; }
        if (s.state === 'failed') { over(s.error || 'The earlier transcription failed.', 'bad'); return; }
        var same = j.key === key(src) && j.lang === lang.code && S.phase === 'idle';
        if (!same) { over('A transcription that was running for another video or language was stopped.'); return; }
        if (s.state === 'awaiting-audio' || s.state === 'receiving') { over(SAY_LEFT); return; }
        var run = ++S.run;
        S.job = j.id; S.kind = src.kind; S.key = j.key; S.lang = j.lang; S.model = j.model;
        S.startHash = j.hash || '';
        S.phase = 'working';
        lock(true);
        say(s.say, s.pct);
        if (s.state === 'done') finishJob(run); else poll(run);
      }, function () { S.job = ''; persist(); });
    }

    // What the page was a moment ago: the tie of the box to its video (only if
    // it is still that video's), and the waveform held for it.  A running job
    // is asked about once the computer has said what it has.
    (function restore() {
      var k = key(o.source());
      AUTO = was.auto && was.auto.source === k ? was.auto : null;
      WAVE = was.wave && was.wave.source === k ? was.wave : null;
    })();
    lock(false);
    refresh().then(resume);
    return {
      sourceChanged: sourceChanged,
      langChanged: langChanged,
      modelChanged: modelChanged,
      redraw: paint,
      busy: function () { return S.phase !== 'idle'; },
      // "Edit the transcript…" opens a video of its own: two would both be heard
      guardEdit: function () {
        return o.source().kind === 'yt' && (S.phase === 'loading' || S.phase === 'ready' || S.phase === 'recording')
          ? 'the video in the frame above is being recorded — finish or cancel that first' : '';
      },
      // the token of the waveform held for THIS video, or '' (the doors that make a video take it)
      wave: function () {
        var src = o.source();
        return WAVE && src.kind === 'yt' && WAVE.source === key(src) ? WAVE.job : '';
      },
      videoAdded: function () { AUTO = WAVE = null; S.held = null; forget(STATE); paint(); }
    };
  }

  window.ParsehAddStt = {mount: mount, hash: hash};
})();

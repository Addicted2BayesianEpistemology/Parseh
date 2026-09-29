// SPDX-License-Identifier: GPL-3.0-or-later
/* Parseh — THE LLM ROW: the controls around a prompt, drawn once for every
   page that hands one out (brief §3.5 and §3.6).

   A person copies a prompt from a page of Parseh, pastes it into a chatbot
   and brings the answer back.  The pages that hand a prompt out were seven
   pieces of code that each drew their own button, said the length or did not,
   and told the person what to do next in their own words.  This is the one
   place these controls are built:

       [ prompt: Parseh's ▾ ]  [ copy the prompt ]  [ copy the request for the skill ]
       about 12,500 characters (about 3,100 tokens)
       some chatbots take less at once — ask for less, or send the rules …   (past 8,000 tokens)
       paste it into a chatbot, then bring its answer back here.

   THE SIZE IS SAID BEFORE THE COPY, never after it: what the button copies is
   held (`update`), and the line above is worked out from that very text.  The
   press copies the HELD text inside the click itself, which is what Safari and
   Firefox want of a clipboard write; a page that makes its prompt on the
   server asks for it as soon as it can (`refresh`), so that by the time the
   button is pressed there is nothing left to wait for.  A held text is only a
   picture of the files it was made from, so a page that changes them drops it
   (`invalidate`, `forget`) and nothing stale is ever copied.

   IT LOADS IN BOTH WORLDS, as lib/explain.js does: the toolbox's pages (the
   video player, the book reader, the add page) link it from /lib/, and the
   studio's pages link the same file, which the studio run on its own serves
   itself (markdown/app/server.py).  So its few rules are written in the tokens
   of whichever sheet is in force -- the toolbox's --dim/--rule/--warn, the
   studio's --chrome-mut -- with a plain colour behind both, and its buttons
   take the page's own classes (`cls`) so a button is the page's button.

   THE API (a page mounts one row per place it hands a prompt out):

     var row = ParsehLLMRow.mount(element, options)      // Parseh.llmRow is the same function
                                                         // where the page has `Parseh`
   options
     surface   the prompt's surface, as lib/promptkit.py names it (studio-doc,
               studio-exercises, video-new, video-region, book-region,
               transcript-tidy, ask, book-new).  Keys what the row remembers.
     getText   function ({press}) -> string | Promise<string>: the prompt as it
               stands NOW, for a page that makes it when asked.  `press` is
               true when the person pressed copy and false when the row is only
               measuring; an empty string means there is nothing to copy.  A
               page that has the text in hand calls `row.update(text)` instead.
     label     the copy button's words (default "copy the prompt"); title, its tooltip
     remind    the one line under the buttons: what to do with the copy, and how
               to bring the answer back (a string; default a generic sentence)
     cls       classes the page's own buttons wear: {copy, skill} or one string
     ids       ids for the elements, so a page's scripts and tests find them:
               {copy, skill, size, note, say, hand, handRow}
     box       a function returning the page's own box that shows the prompt: when
               the clipboard is refused the row selects it there instead of
               drawing a box of its own
     measure   function () -> bool: whether `invalidate` should measure again
               (a sheet shut, or nothing picked yet, has nothing to measure)
     fresh     function (which) -> bool: asked at a press, of a text that is held:
               is it still what the page would make?  A page whose source changes
               in more ways than it can list (a transcript being typed into) says
               no, and the row makes the prompt again before it copies
     onPress   function (which): at the start of a press, before anything is made or
               copied: for a page that has a line of its own about the last copy
     onCopied  function (ok, text, which): after every press.  ok is true, false
               (refused) or null (there was nothing to copy)
     onError   function (error, which, press): when getText fails; press is true when
               the person pressed copy.  The row says the error itself only where
               there is no onError: a page that has a line of its own says it there

   the handle
     row.el                       the row's element (already in `element`)
     row.update(text[, which])    this is what the button copies now; the size
     row.refresh([which])         ask getText and hold the answer -> Promise
     row.invalidate([which])      drop what is held; measure again soon
     row.forget([which])          drop what is held and the size, and put away the
                                  box shown for a copy by hand
     row.copy([which])            what the button does -> Promise<bool|null>
     row.text([which])            what is held, or null
     row.disable(why) / row.enable([title])    the button off, its reason its tooltip; on again
     row.label(text)              the copy button's words, for a page whose copy changes with
                                  what is written beside it: a button says what it copies
     row.say(text, bad)           the line for what just happened
     row.remind(text | node)      the one line of reminder
     row.setMenu(spec | null)     THE PROMPT MENU (Lane F, W5).  Hidden until a
                                  caller supplies items: {items: [{id, label}],
                                  value, onChange(id, item)} draws "prompt: [name ▾]".
                                  row.menuSlot is the slot itself, for a richer menu.
     row.setSkill(spec | null)    THE SKILL BUTTON (Lane G, W6).  Hidden until a
                                  caller supplies {getText, label, note, link:
                                  {text, href}, onCopied, onError}; `which` is
                                  "skill" for update/refresh/invalidate/forget/
                                  copy/text.  The size line is the prompt's alone:
                                  the skill's note is its caller's words.
     row.destroy()

   WHAT A PAGE MAY STYLE AND A TEST MAY READ: .llmrow (the row), .llmrow-bar,
   .llmrow-menu, .llmrow-copy, .llmrow-skill, .llmrow-size (its data-chars and
   data-tokens hold the numbers it says: the exact count of characters, and the
   estimate), .llmrow-warn, .llmrow-note, .llmrow-skillnote, .llmrow-say (role
   status: "copied ✓", or why not) and .llmrow-hand (the box for a copy by hand,
   made the first time the clipboard refuses).

   ParsehLLMRow.promptSize(text) -> {chars, tokens, line, over}: the one helper
   that counts.  About 4 characters a token in Latin script and about 2 in
   Arabic script, CJK and Devanagari, worked out from the mix of scripts in the
   text; `over` is true past 8,000 tokens.  The pages that show a total of
   their own (the studio's boxes) call it, so no page counts differently.

   WHICH BUTTON WAS USED LAST is kept on this device, per surface
   (localStorage `parseh_llmrow_<surface>`, every access inside try: the row
   works with storage refused) and that button is put first.  Neither is ever
   hidden for it. */
(function (root) {
  'use strict';
  if (root.ParsehLLMRow) return;
  var doc = root.document;

  var WARN_TOKENS = 8000;
  var TOO_MUCH = 'some chatbots take less at once — ask for less, or send the rules ' +
                 'and the data in two messages.';
  var REMIND = 'paste it into a chatbot, then bring its answer back here.';
  var REFUSED = 'the browser would not put it on the clipboard';
  var HAND = 'select this and copy it — or press the button again';
  var KEY = 'parseh_llmrow_';
  var MEASURE_WAIT = 250;
  var COPY_TITLE = 'put the prompt on the clipboard, to paste into a chatbot';

  /* ---- the size ------------------------------------------------------- */
  // AN ARABIC-SCRIPT, CJK OR DEVANAGARI CHARACTER IS ABOUT HALF A TOKEN, a
  // Latin one about a quarter (the owner's rule, §3.5).  Script_Extensions
  // for the two that carry marks of "inherited" script (the harakat, the
  // danda), Script for the rest.  WHY NO LIST OF BLOCKS BEHIND IT: the
  // escapes are older than the CSS these pages already need (color-mix,
  // :where), so a browser that lacks them draws nothing else of Parseh either.
  var WIDE;
  try {
    WIDE = new RegExp('[\\p{Script_Extensions=Arabic}\\p{Script_Extensions=Devanagari}' +
      '\\p{Script=Han}\\p{Script=Hiragana}\\p{Script=Katakana}\\p{Script=Hangul}]', 'gu');
  } catch (e) {
    WIDE = /(?!)/g;
  }
  var PAIRS = /[\uD800-\uDBFF][\uDC00-\uDFFF]/g;

  // "12,500": to the nearest hundred once it is in the thousands, to the
  // nearest ten below that -- it says "about", so it does not pretend
  function said(n) {
    n = n < 100 ? n : n < 1000 ? Math.round(n / 10) * 10 : Math.round(n / 100) * 100;
    return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  }
  function promptSize(text) {
    text = String(text == null ? '' : text);
    var pairs = text.match(PAIRS);
    var chars = text.length - (pairs ? pairs.length : 0);
    var wide = (text.match(WIDE) || []).length;
    var tokens = Math.ceil((chars - wide) / 4 + wide / 2);
    return {chars: chars, tokens: tokens, over: tokens > WARN_TOKENS,
            line: chars ? 'about ' + said(chars) + ' characters (about ' + said(tokens) + ' tokens)' : ''};
  }

  /* ---- the clipboard -------------------------------------------------- */
  // EXACTLY THE TEXT, not squeezed and not trimmed: a prompt is fenced JSON
  // and numbered captions, and the size above it is of this very string
  function put(text) {
    var api = root.navigator && root.navigator.clipboard;
    var first;
    try {
      first = api && api.writeText ? api.writeText(text) : Promise.reject(new Error('no clipboard API'));
    } catch (e) {
      first = Promise.reject(e);
    }
    return first.then(function () { return true; }, function () {
      // the old way, for a browser that will not give the new one: a box made for the
      // purpose, selected, copied, and taken away -- with the focus put back where it was
      var was = doc.activeElement;
      try {
        var ta = doc.createElement('textarea');
        ta.value = text;
        ta.setAttribute('readonly', '');
        ta.style.cssText = 'position:fixed;top:0;left:0;opacity:0';
        doc.body.appendChild(ta);
        ta.select();
        var ok = doc.execCommand('copy');
        doc.body.removeChild(ta);
        if (was && was.focus) was.focus();
        return !!ok;
      } catch (e) {
        return false;
      }
    });
  }

  /* ---- what is remembered on this device -------------------------------- */
  function recall(surface) {
    try { return root.localStorage.getItem(KEY + surface) === 'skill' ? 'skill' : 'prompt'; }
    catch (e) { return 'prompt'; }
  }
  function remember(surface, which) {
    try { root.localStorage.setItem(KEY + surface, which); } catch (e) {}
  }

  /* ---- the few rules it needs, in the tokens of whichever sheet is in force */
  var CSS = [
    '.llmrow{display:block;min-width:0;margin:8px 0 0;font-size:12.5px;line-height:1.5}',
    '.llmrow [hidden]{display:none!important}',
    '.llmrow-bar{display:flex;flex-wrap:wrap;align-items:center;gap:8px}',
    '.llmrow-menu{display:inline-flex;align-items:center;gap:6px;min-width:0;',
    '  color:var(--dim,var(--chrome-mut,#635358))}',
    '.llmrow-menu select{font:inherit;max-width:100%;min-width:0;padding:4px 6px;',
    '  border:1px solid var(--rule,var(--chrome-line,#ddd));border-radius:6px;',
    '  background:var(--card,var(--chrome-panel,#fff));color:var(--ink,var(--chrome-fg,#222))}',
    // ITS WORDS ARE ENGLISH: each line takes its direction from what it says, so
    // a full stop never lands at the wrong end of a sentence in a page that reads
    // right to left -- while the line itself still starts where the page's does
    '.llmrow-size,.llmrow-warn,.llmrow-note,.llmrow-skillnote,.llmrow-say{margin:6px 0 0;',
    '  color:var(--dim,var(--chrome-mut,#635358));font-size:1em;overflow-wrap:anywhere;',
    '  unicode-bidi:plaintext}',
    '.llmrow-size:empty,.llmrow-say:empty,.llmrow-note:empty{display:none}',
    '.llmrow-warn{color:var(--warn,#a8760a)}',
    '.llmrow-say.bad{color:var(--danger,#9b3327)}',
    '.llmrow-note a,.llmrow-skillnote a{color:var(--accent,#be3455)}',
    '.llmrow-hand{margin:6px 0 0}',
    '.llmrow-hand textarea{display:block;box-sizing:border-box;width:100%;min-height:6em;',
    '  resize:vertical;padding:6px 8px;direction:ltr;text-align:left;',
    '  font:11.5px/1.45 ui-monospace,Menlo,Consolas,monospace;',
    '  border:1px solid var(--rule,var(--chrome-line,#ddd));border-radius:6px;',
    '  background:var(--bg,var(--chrome-bg,#f3eff1));color:var(--ink,var(--chrome-fg,#222))}',
    '.llmrow-hand .llmrow-handnote{margin:4px 0 0;color:var(--faint,var(--chrome-mut,#a2949a));',
    '  font-size:.92em}'
  ].join('\n');
  function style() {
    if (doc.getElementById('llmrow-style')) return;
    var s = doc.createElement('style');
    s.id = 'llmrow-style';
    s.textContent = CSS;
    (doc.head || doc.documentElement).appendChild(s);
  }

  // A PAGE'S OWN CALLBACK is the page's: if it throws, the row goes on (a press that
  // never finished would leave its button busy for good) and the fault is on the console
  function tell(fn) {
    if (!fn) return;
    try { fn.apply(null, Array.prototype.slice.call(arguments, 1)); }
    catch (e) { if (root.console && console.error) console.error(e); }
  }

  function make(tag, cls, text) {
    var n = doc.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }

  /* ---- the row ---------------------------------------------------------- */
  function mount(container, opts) {
    opts = opts || {};
    style();
    var surface = String(opts.surface || 'prompt');
    var ids = opts.ids || {};
    var cls = typeof opts.cls === 'string' ? {copy: opts.cls, skill: opts.cls} : (opts.cls || {});
    var gone = false, busy = false, off = '';

    var el = make('div', 'llmrow');
    el.setAttribute('data-surface', surface);
    var bar = make('div', 'llmrow-bar');
    var menu = make('span', 'llmrow-menu');
    menu.hidden = true;
    function button(which, label, title, extra, id) {
      var b = make('button', 'llmrow-' + which + (extra ? ' ' + extra : ''), label);
      b.type = 'button';
      b.title = title;
      if (id) b.id = id;
      return b;
    }
    var title = opts.title || COPY_TITLE;
    var copyBtn = button('copy', opts.label || 'copy the prompt', title, cls.copy, ids.copy);
    var skillBtn = button('skill', 'copy the request for the skill',
                          'put a short request on the clipboard, for a chat where the skill is installed',
                          cls.skill, ids.skill);
    skillBtn.hidden = true;
    bar.appendChild(menu);
    bar.appendChild(copyBtn);
    bar.appendChild(skillBtn);
    var sizeEl = make('div', 'llmrow-size');
    if (ids.size) sizeEl.id = ids.size;
    var warnEl = make('div', 'llmrow-warn', TOO_MUCH);
    warnEl.hidden = true;
    var noteEl = make('div', 'llmrow-note');
    if (ids.note) noteEl.id = ids.note;
    var skillNote = make('div', 'llmrow-skillnote');
    skillNote.hidden = true;
    var sayEl = make('div', 'llmrow-say');
    sayEl.setAttribute('role', 'status');
    sayEl.setAttribute('aria-live', 'polite');
    if (ids.say) sayEl.id = ids.say;
    [bar, sizeEl, warnEl, noteEl, skillNote, sayEl].forEach(function (n) { el.appendChild(n); });
    container.appendChild(el);

    var slots = {
      prompt: {btn: copyBtn, get: opts.getText || null, text: null, gen: 0, timer: 0, pending: null,
               onCopied: opts.onCopied || null, onError: opts.onError || null},
      skill: {btn: skillBtn, get: null, text: null, gen: 0, timer: 0, pending: null,
              onCopied: null, onError: null}
    };
    function slot(which) { return which === 'skill' ? slots.skill : slots.prompt; }
    function shown(which) { return which === 'skill' ? 'skill' : 'prompt'; }

    // THE COPY BUTTON IS OFF for the reason the page gave (disable), or while
    // there is neither a text held nor a way to make one
    function paint() {
      var s = slots.prompt, k = slots.skill;
      copyBtn.disabled = !!off || (!s.text && !s.get);
      copyBtn.title = off || title;
      skillBtn.disabled = !k.text && !k.get;
    }
    /* what is said above the buttons follows the main prompt's text */
    function sizeOf(text) {
      var s = promptSize(text);
      sizeEl.textContent = s.line;
      if (s.chars) {
        sizeEl.setAttribute('data-chars', String(s.chars));
        sizeEl.setAttribute('data-tokens', String(s.tokens));
      } else {
        sizeEl.removeAttribute('data-chars');
        sizeEl.removeAttribute('data-tokens');
      }
      warnEl.hidden = !s.over;
    }
    function say(text, bad) {
      sayEl.textContent = text || '';
      sayEl.classList.toggle('bad', !!bad);
    }
    /* THE PROMPT, TO COPY BY HAND, where the clipboard was refused and the page
       has no box of its own that shows it.  Made the first time it is needed,
       not before: a page that looks for the textarea of a sheet it mounted the
       row in should not find a hidden one of the row's */
    var hand = null, handBox = null;
    function offer(text) {
      // a copy by hand: the page's own box when it has one, else ours
      var box = typeof opts.box === 'function' ? opts.box() : null;
      if (box) {
        try { box.focus(); box.select(); } catch (e) {}
        return REFUSED + ': the prompt is selected in the box — copy it from there';
      }
      if (!hand) {
        hand = make('div', 'llmrow-hand');
        if (ids.handRow) hand.id = ids.handRow;
        handBox = make('textarea');
        handBox.readOnly = true;
        handBox.rows = 5;
        handBox.spellcheck = false;
        handBox.setAttribute('dir', 'ltr');
        handBox.setAttribute('aria-label', 'the prompt, to copy by hand');
        if (ids.hand) handBox.id = ids.hand;
        hand.appendChild(handBox);
        hand.appendChild(make('div', 'llmrow-handnote', HAND));
        el.appendChild(hand);
      }
      handBox.value = text;
      hand.hidden = false;
      try { handBox.focus(); handBox.select(); } catch (e) {}
      return REFUSED;
    }
    function putAway() {
      if (!hand) return;
      hand.hidden = true;
      handBox.value = '';
    }

    function update(text, which) {
      var s = slot(which);
      s.gen++;
      s.pending = null;
      s.text = text == null ? null : String(text);
      if (s === slots.prompt) sizeOf(s.text);
      paint();
      putAway();
      // "copied" was about the text before this one
      say('');
    }
    function forget(which) {
      var s = slot(which);
      s.gen++;
      s.pending = null;
      clearTimeout(s.timer);
      s.text = null;
      if (s === slots.prompt) sizeOf(null);
      paint();
      putAway();
      say('');
    }
    // ASK THE PAGE FOR THE TEXT and hold what it says -- unless something
    // changed while it was being made, and then the answer is about files
    // that are not there any more
    function ask(which, press) {
      var s = slot(which);
      if (!s.get) return Promise.resolve(null);
      var gen = s.gen;
      if (s === slots.prompt && !press) {
        sizeOf(null);
        sizeEl.textContent = 'measuring…';
      }
      var made = new Promise(function (ok) { ok(s.get({press: !!press})); }).then(function (text) {
        text = text == null ? '' : String(text);
        if (gen !== s.gen) return null;
        s.text = text;
        if (s === slots.prompt) sizeOf(text);
        paint();
        return text;
      });
      s.pending = made;
      made.then(null, function () {}).then(function () { if (s.pending === made) s.pending = null; });
      return made;
    }
    function refresh(which) {
      var s = slot(which);
      return ask(which, false).then(function (text) { return text; }, function (err) {
        if (s === slots.prompt) sizeOf(null);
        tell(s.onError, err, shown(which), false);
        return null;
      });
    }
    function invalidate(which) {
      var s = slot(which);
      forget(which);
      if (gone || !s.get) return;
      if (opts.measure && !opts.measure()) return;
      s.timer = setTimeout(function () { refresh(which); }, MEASURE_WAIT);
    }

    /* THE PRESS.  A held text is copied inside the click, before anything is
       awaited; one that is not held is asked for first (and a browser that
       will not copy after a wait is met by the box, and by a second press
       that copies the held text at once) */
    function done(s, which, text, ok) {
      if (ok) {
        say('copied ✓');
        putAway();
      } else {
        say(offer(text), true);
      }
      tell(s.onCopied, ok, text, shown(which));
      return ok;
    }
    function copy(which) {
      var s = slot(which);
      if (busy) return Promise.resolve(null);
      // what was said of the last press is not about this one; and a measuring
      // that was about to start is the press's own business now
      say('');
      clearTimeout(s.timer);
      remember(surface, shown(which));
      tell(opts.onPress, shown(which));
      if (s.text && opts.fresh && !opts.fresh(shown(which))) forget(which);
      var held = s.text;
      if (held) return put(held).then(function (ok) { return done(s, which, held, ok); });
      if (!s.get) {
        tell(s.onCopied, null, '', shown(which));
        return Promise.resolve(null);
      }
      busy = true;
      s.btn.setAttribute('aria-busy', 'true');
      say('making the prompt…');
      var wait = s.pending ? s.pending.then(null, function () {}) : Promise.resolve();
      return wait.then(function () {
        return s.text ? s.text : ask(which, true);
      }).then(function (text) {
        if (!text) {
          say('');
          tell(s.onCopied, null, '', shown(which));
          return null;
        }
        return put(text).then(function (ok) { return done(s, which, text, ok); });
      }).then(null, function (err) {
        if (s.onError) { say(''); tell(s.onError, err, shown(which), true); }
        else say((err && err.message) || String(err), true);
        return null;
      }).then(function (result) {
        busy = false;
        s.btn.removeAttribute('aria-busy');
        return result;
      });
    }
    copyBtn.addEventListener('click', function () { copy('prompt'); });
    skillBtn.addEventListener('click', function () { copy('skill'); });

    /* THE TWO SLOTS THE LATER LANES FILL.  Nothing is drawn for either until a
       caller supplies it: a menu with one dead entry, or a button that does
       nothing, is worse than no menu and no button. */
    function order() {
      var last = recall(surface);
      if (skillBtn.hidden) return;
      bar.insertBefore(last === 'skill' ? skillBtn : copyBtn,
                       last === 'skill' ? copyBtn : skillBtn);
    }
    function setMenu(spec) {
      menu.textContent = '';
      if (!spec || !spec.items || !spec.items.length) { menu.hidden = true; return; }
      var lab = make('label', null, 'prompt: ');
      var sel = make('select');
      spec.items.forEach(function (it) {
        var o = make('option', null, it.label);
        o.value = it.id;
        sel.appendChild(o);
      });
      if (spec.value != null) sel.value = spec.value;
      sel.addEventListener('change', function () {
        var chosen = null;
        spec.items.forEach(function (it) { if (it.id === sel.value) chosen = it; });
        if (spec.onChange) spec.onChange(sel.value, chosen);
      });
      lab.appendChild(sel);
      menu.appendChild(lab);
      menu.hidden = false;
    }
    function setSkill(spec) {
      var s = slots.skill;
      forget('skill');
      skillNote.textContent = '';
      if (!spec) {
        skillBtn.hidden = true;
        skillNote.hidden = true;
        s.get = s.onCopied = s.onError = null;
        return;
      }
      s.get = spec.getText || null;
      s.onCopied = spec.onCopied || null;
      s.onError = spec.onError || null;
      paint();
      skillBtn.textContent = spec.label || 'copy the request for the skill';
      skillBtn.hidden = false;
      if (spec.note) skillNote.appendChild(doc.createTextNode(spec.note));
      if (spec.link) {
        var a = make('a', null, spec.link.text);
        a.href = spec.link.href;
        a.target = '_blank';
        a.rel = 'noopener';
        if (spec.note) skillNote.appendChild(doc.createTextNode(' '));
        skillNote.appendChild(a);
      }
      skillNote.hidden = !(spec.note || spec.link);
      order();
    }
    function remind(what) {
      noteEl.textContent = '';
      if (what && what.nodeType) noteEl.appendChild(what);
      else noteEl.textContent = what == null ? '' : String(what);
    }
    remind(opts.remind == null ? REMIND : opts.remind);
    paint();

    var row = {
      el: el, menuSlot: menu,
      update: function (text, which) { update(text, which); return row; },
      refresh: refresh, invalidate: invalidate, forget: forget, copy: copy,
      text: function (which) { return slot(which).text; },
      disable: function (why) { off = why || 'not yet'; paint(); },
      enable: function (why) { off = ''; if (why) title = why; paint(); },
      label: function (words) { copyBtn.textContent = words; },
      say: say, remind: remind, setMenu: setMenu, setSkill: setSkill,
      destroy: function () {
        gone = true;
        clearTimeout(slots.prompt.timer);
        clearTimeout(slots.skill.timer);
        slots.prompt.gen++;
        slots.skill.gen++;
        if (el.parentNode) el.parentNode.removeChild(el);
      }
    };
    return row;
  }

  root.ParsehLLMRow = {mount: mount, promptSize: promptSize, TOO_MUCH: TOO_MUCH};
  if (root.Parseh && !root.Parseh.llmRow) root.Parseh.llmRow = mount;
})(typeof window !== 'undefined' ? window : globalThis);

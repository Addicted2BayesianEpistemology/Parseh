// SPDX-License-Identifier: GPL-3.0-or-later
/* Parseh — THE LLM ROW: the controls around a prompt, drawn once for every
   page that hands one out (brief §3.5 and §3.6).

   A person copies a prompt from a page of Parseh, pastes it into a chatbot
   and brings the answer back.  The pages that hand a prompt out were seven
   pieces of code that each drew their own button, said the length or did not,
   and told the person what to do next in their own words.  This is the one
   place these controls are built:

       [ prompt: Parseh's ▾ ]  [ copy the prompt ]  [ copy the request for the skill ]
       rōmaji: [ usual scheme ▾ ]   short vowels: [ as they are ▾ ]          (the options: below)
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
     lang      the language's code: with it the row asks the server which OPTIONS
               this prompt has in this language (see below) and draws them
     book, video
               the book's address (/books/persian/mini-fa) or the video's id: the
               options then start from what its own record says of them
     optionsUrl
               where the options are asked for (default /__prompt/options, which
               the toolbox and the studio run alone both answer); `options: false`
               asks nowhere, for a page that gives them with setOptions
     onOption  function (name, value, all): after the person changes an option
     setFact   function (name, value) -> Promise: where the page can write a choice
               into the book's or the video's own record (offered as a button when
               the person chooses against it)
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
     row.setOptions(list | null)  THE OPTIONS (Lane T, W1: brief 3.9 and 3.10).  Which
                                  choices a prompt has is the SERVER'S to say
                                  (lib/promptkit.py OPTIONS: the scheme of the
                                  transliteration, the short vowels of a language
                                  that has them), never this file's: a row mounted
                                  with `lang` asks for them itself, and a page that
                                  has them already -- the studio's answers carry
                                  `options` -- gives them here.  Each is
                                  {name, label, value, default, fact, choices:
                                  [{id, label}], remember}: drawn as "label: [choice ▾]"
                                  and shown only where it applies, so a language with
                                  no short vowels has no such control
     row.options()                the options as they are shown now, {translit: 'ipa',
                                  marks: 'nomarks'} -- what a page puts in the request
                                  that makes the prompt.  {} until the server has said
     row.setLang(code[, {book, video}])
                                  another language (the add page's and the studio's
                                  select), or another book or video: asks again
     row.optionsReady()           a promise, kept when the options have been asked for
     row.destroy()

   THE OPTIONS WITHOUT THE ROW: ParsehLLMRow.options(element, {surface, lang, book|video,
   onOption, setFact}) draws the same controls on their own, for a page that has them
   somewhere else than between the buttons and the size -- the studio's, beside the level and
   the length; the add page's, above the button that makes the prompt -- and answers
   options() / setOptions(list) / setLang(code) / optionsReady() as the row does.

   THE OPTIONS ARE REMEMBERED ON THIS DEVICE, each under what its descriptor says
   (`remember`: the language's code for the scheme of the transliteration, the
   surface for the short vowels): localStorage parseh_llmrow_<name>_<remember>,
   every access inside try.  A BOOK'S OR A VIDEO'S OWN RECORD wins over what the
   device remembers (`fact`): the control shows the book's setting, and choosing
   against it says that a book mixing two schemes is harder to read.  The
   getText of a page is not called before the options are known (or have failed
   to come, which is not waited for long), so the first prompt is already made
   the way it will be asked for.

   WHAT A PAGE MAY STYLE AND A TEST MAY READ: .llmrow (the row), .llmrow-bar,
   .llmrow-menu, .llmrow-copy, .llmrow-skill, .llmrow-opts (the options; each
   .llmrow-opt holds a select, its data-option the option's name), .llmrow-optnote,
   .llmrow-size (its data-chars and
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
  var OPTIONS_URL = '/__prompt/options';
  var OPTIONS_WAIT = 1500;       // how long a prompt waits for the options before it is made without them
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
  // an option's choice, under the key its descriptor names; null where nothing valid is kept
  function recallOption(d) {
    try {
      var v = root.localStorage.getItem(KEY + d.name + '_' + d.remember);
      return d.choices.some(function (c) { return c.id === v; }) ? v : null;
    } catch (e) { return null; }
  }
  function rememberOption(d, value) {
    try { root.localStorage.setItem(KEY + d.name + '_' + d.remember, value); } catch (e) {}
  }

  /* ---- the few rules it needs, in the tokens of whichever sheet is in force */
  var CSS = [
    '.llmrow{display:block;min-width:0;margin:8px 0 0;font-size:12.5px;line-height:1.5}',
    '.llmrow [hidden]{display:none!important}',
    '.llmrow-bar{display:flex;flex-wrap:wrap;align-items:center;gap:8px}',
    '.llmrow-menu{display:inline-flex;align-items:center;gap:6px;min-width:0;',
    '  color:var(--dim,var(--chrome-mut,#635358))}',
    '.llmrow-menu select,.llmrow-opt select{font:inherit;max-width:100%;min-width:0;padding:4px 6px;',
    '  border:1px solid var(--rule,var(--chrome-line,#ddd));border-radius:6px;',
    '  background:var(--card,var(--chrome-panel,#fff));color:var(--ink,var(--chrome-fg,#222))}',
    // THE OPTIONS: "rōmaji: [usual scheme ▾]" -- each its own label and select, wrapping on a phone
    '.llmrow-opts{display:flex;flex-wrap:wrap;align-items:center;gap:6px 16px;margin:8px 0 0}',
    '.llmrow-opt{display:inline-flex;align-items:center;gap:6px;min-width:0;max-width:100%;',
    '  color:var(--dim,var(--chrome-mut,#635358))}',
    '.llmrow-opts[hidden],.llmrow-optnote[hidden]{display:none!important}',
    '.llmrow-optnote{margin:6px 0 0;color:var(--warn,#a8760a);unicode-bidi:plaintext;',
    '  overflow-wrap:anywhere}',
    '.llmrow-optnote button{font:inherit;margin-inline-start:8px;cursor:pointer}',
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
    // THE OPTIONS (below): what a prompt has beside the copy button.  A held prompt, and the
    // request for a skill, were made for other choices when one changes
    var optBox = optionsBox(surface, opts, {
      changed: function () { dropHeld(); },
      say: function (text, bad) { say(text, bad); }
    });

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
    [bar, optBox.el, optBox.note, sizeEl, warnEl, noteEl, skillNote, sayEl].forEach(function (n) { el.appendChild(n); });
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
    // that are not there any more.  Not before the options are known: a prompt
    // asked for first would be made the way nobody chose
    function ask(which, press) {
      var s = slot(which);
      if (!s.get) return Promise.resolve(null);
      var gen = s.gen;
      if (s === slots.prompt && !press) {
        sizeOf(null);
        sizeEl.textContent = 'measuring…';
      }
      var go = function () { return s.get({press: !!press}); };
      var waiting = optBox.pending();
      var called = waiting ? waiting.then(go) : new Promise(function (ok) { ok(go()); });
      var made = called.then(function (text) {
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

    // WHAT A CHOICE OF AN OPTION DOES to what is held: a prompt made for other choices is dropped (and
    // measured again where the page lets it), and so is the request for a skill, which carries them too
    function dropHeld() {
      invalidate('prompt');
      invalidate('skill');
    }

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
    optBox.start();

    var row = {
      el: el, menuSlot: menu,
      update: function (text, which) { update(text, which); return row; },
      refresh: refresh, invalidate: invalidate, forget: forget, copy: copy,
      text: function (which) { return slot(which).text; },
      disable: function (why) { off = why || 'not yet'; paint(); },
      enable: function (why) { off = ''; if (why) title = why; paint(); },
      label: function (words) { copyBtn.textContent = words; },
      say: say, remind: remind, setMenu: setMenu, setSkill: setSkill,
      setOptions: optBox.set, options: optBox.now, setLang: optBox.setLang, optionsReady: optBox.ready,
      destroy: function () {
        gone = true;
        optBox.destroy();
        clearTimeout(slots.prompt.timer);
        clearTimeout(slots.skill.timer);
        slots.prompt.gen++;
        slots.skill.gen++;
        if (el.parentNode) el.parentNode.removeChild(el);
      }
    };
    return row;
  }

  /* ---- the options of a prompt: "label: [choice ▾]" ----------------------------- */
  // THE OPTIONS (brief 3.9, 3.10): what the server says a prompt has -- the scheme its transliteration
  // is written in, the short vowels of a language that has them -- drawn as one select each and
  // remembered on this device.  A box of its own because two kinds of page want it: the row, which draws
  // it between the buttons and the size, and a page that has the choices somewhere else (the studio's,
  // beside level and length; the add page's, above the button that makes the prompt).
  //
  // `hooks` are the owner's: {changed(): a choice was made (the row drops what it holds), say(text,
  // bad): a sentence for the person}.  Asked of the server once at start() when `opts.lang` is given, and
  // again by setLang(); never by a page that gives the choices with set().
  function optionsBox(surface, opts, hooks) {
    hooks = hooks || {};
    var el = make('div', 'llmrow-opts');
    el.hidden = true;
    var note = make('div', 'llmrow-optnote');
    note.hidden = true;
    note.setAttribute('role', 'status');
    var descs = [], chosen = {}, pending = null, asked = '', gone = false;
    var scope = {lang: opts.lang, book: opts.book, video: opts.video};
    var what = /^book-/.test(surface) ? 'book' : /^video-/.test(surface) ? 'video' : '';

    function wordsOf(d, id) {
      var said = id;
      d.choices.forEach(function (c) { if (c.id === id) said = c.label; });
      return said;
    }
    function now() {
      var out = {};
      descs.forEach(function (d) { out[d.name] = chosen[d.name]; });
      return out;
    }
    // THE BOOK'S OR THE VIDEO'S OWN RECORD wins over what the device remembers (`fact`): the control
    // shows its setting, and a choice against it says that a book mixing two is harder to read -- and,
    // where the page can write it, offers to make the choice the record's
    function paintNote() {
      note.textContent = '';
      var against = descs.filter(function (d) { return d.fact && chosen[d.name] !== d.value; })[0];
      if (!against || !what) { note.hidden = true; return; }
      var chose = chosen[against.name];
      note.appendChild(doc.createTextNode(
        'this ' + what + "'s " + against.label + ' is ' + wordsOf(against, against.value) +
        ' and this prompt asks for ' + wordsOf(against, chose) + ': a ' + what +
        ' that mixes the two is harder to read.'));
      if (typeof opts.setFact === 'function') {
        var b = make('button', null, 'make ' + wordsOf(against, chose) + ' the ' + what + "'s setting");
        b.type = 'button';
        b.addEventListener('click', function () {
          b.disabled = true;
          new Promise(function (ok) { ok(opts.setFact(against.name, chose)); }).then(function () {
            against.value = chose;
            against.fact = chose !== against.default;
            paintNote();
          }, function (e) {
            b.disabled = false;
            tell(hooks.say, (e && e.message) || String(e), true);
          });
        });
        note.appendChild(b);
      }
      note.hidden = false;
    }
    function set(list) {
      var was = JSON.stringify(now());
      descs = (list || []).filter(function (d) { return d && d.name && d.choices && d.choices.length; });
      chosen = {};
      el.textContent = '';
      descs.forEach(function (d) {
        var kept = d.fact ? null : recallOption(d);
        chosen[d.name] = kept || d.value;
        var lab = make('label', 'llmrow-opt');
        lab.setAttribute('data-option', d.name);
        lab.appendChild(doc.createTextNode(d.label + ': '));
        var sel = make('select');
        d.choices.forEach(function (c) {
          var o = make('option', null, c.label);
          o.value = c.id;
          sel.appendChild(o);
        });
        sel.value = chosen[d.name];
        sel.addEventListener('change', function () {
          chosen[d.name] = sel.value;
          if (!d.fact) rememberOption(d, sel.value);
          paintNote();
          tell(opts.onOption, d.name, sel.value, now());
          tell(hooks.changed);
        });
        lab.appendChild(sel);
        el.appendChild(lab);
      });
      el.hidden = !descs.length;
      paintNote();
      // what was held, or asked for, was made for other choices
      if (JSON.stringify(now()) !== was) tell(hooks.changed);
    }
    // ASKED FOR WHEN THE BOX IS MOUNTED WITH A LANGUAGE (and again when it changes): the server knows
    // which language has what, so no page holds a table of it.  A server that does not answer leaves the
    // prompt without options, which is the prompt it has always been
    function ask() {
      var q = 'surface=' + encodeURIComponent(surface) + '&lang=' + encodeURIComponent(scope.lang || '');
      if (scope.book) q += '&book=' + encodeURIComponent(scope.book);
      else if (scope.video) q += '&video=' + encodeURIComponent(scope.video);
      var url = (opts.optionsUrl || OPTIONS_URL) + '?' + q;
      asked = url;
      var timer = 0;
      var mine = new Promise(function (ok) {
        function done(list) {
          clearTimeout(timer);
          if (!gone && asked === url) set(list);
          ok();
        }
        timer = setTimeout(function () { ok(); }, OPTIONS_WAIT);
        if (!root.fetch) return done([]);
        root.fetch(url, {cache: 'no-store'}).then(function (r) { return r.json(); }).then(function (j) {
          done(j && j.ok ? j.options : []);
        }, function () { done([]); });
      });
      pending = mine;
      mine.then(function () { if (pending === mine) pending = null; });
      return mine;
    }
    return {
      el: el, note: note, set: set, now: now,
      start: function () { if (scope.lang && opts.options !== false) ask(); },
      setLang: function (code, where) {
        where = where || {};
        scope = {lang: code, book: where.book, video: where.video};
        if (code) return ask();
        asked = '';
        set([]);
        return Promise.resolve();
      },
      pending: function () { return pending; },
      ready: function () { return pending || Promise.resolve(); },
      destroy: function () { gone = true; }
    };
  }

  // THE OPTIONS ALONE, for a page that draws them somewhere other than the row:
  //     var box = ParsehLLMRow.options(element, {surface, lang, book|video, onOption, setFact})
  // box.options() / box.setOptions(list) / box.setLang(code[, {book, video}]) / box.optionsReady() are the
  // row's own; box.note is the sentence under them, which this puts after the select in `element`.
  function options(container, opts) {
    opts = opts || {};
    style();
    var surface = String(opts.surface || 'prompt');
    var wrap = make('div', 'llmrow llmrow-optionsonly');
    wrap.setAttribute('data-surface', surface);
    var box = optionsBox(surface, opts, {changed: function () {}, say: function () {}});
    wrap.appendChild(box.el);
    wrap.appendChild(box.note);
    container.appendChild(wrap);
    box.start();
    return {el: wrap, note: box.note, options: box.now, setOptions: box.set, setLang: box.setLang,
            optionsReady: box.ready,
            destroy: function () { box.destroy(); if (wrap.parentNode) wrap.parentNode.removeChild(wrap); }};
  }

  root.ParsehLLMRow = {mount: mount, options: options, promptSize: promptSize, TOO_MUCH: TOO_MUCH};
  if (root.Parseh && !root.Parseh.llmRow) root.Parseh.llmRow = mount;
})(typeof window !== 'undefined' ? window : globalThis);

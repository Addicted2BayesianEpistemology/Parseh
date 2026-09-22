// SPDX-License-Identifier: GPL-3.0-or-later
/* Translation inside the page, for the chunk nobody has glossed.
 *
 * WHAT THIS IS.  A translation model -- one job, no prompt, no endpoint, no
 * key, no conversation, and the same answer every time for the same
 * sentence.  It runs as WebAssembly in a worker in this page, so the chunk
 * being translated never leaves the machine and the toolbox keeps no server
 * and no Python dependency for it.  The engine is bergamot-translator, the
 * one Firefox's own translations feature uses; the models are Mozilla's.
 * Both are downloaded by lib/getmt.py into mt/, and nothing here works --
 * or is offered -- until they are.
 *
 * WHAT IT IS NOT.  It is not a gloss and it is not offered as one.  It is
 * a machine's reading of the line, drawn in the same borrowed panel as the
 * dictionary and under the same rule: it is evidence, the reader decides,
 * and nothing is written into a book or a video by it.
 *
 * THE MODEL IS LOADED ONCE AND KEPT.  It is about 20 MB, so it is fetched on
 * the first translation a reader asks for and not on the chance of one, and
 * the worker holds it for the life of the page.
 */
(function (root) {
  'use strict';

  var MT = {
    base: '/mt/',
    worker: null,
    seq: 0,
    waiting: {},
    loaded: {},          // "fa-en" -> Promise, so a pair is loaded once
    started: null,       // the engine's own initialise, awaited once
    failed: ''
  };

  function key(from, to) { return from + '-' + to; }

  /* THE SYNONYM TABLE.  lib/getsyn.py's own words: a WEAKER match than the
     word itself, used only where nothing stronger is found (see `meet`
     below and SYN_Q).  null = not asked for yet, {} = asked for and either
     absent or not back yet, an object = loaded.  synLoad is idempotent --
     called from `has()`, the moment a reader learns a model exists for this
     pair, well before anyone hovers a word -- and again from `translate`,
     which every align() caller already awaits, as a backstop. Nothing reads
     the promise: align() just reads whatever SYN holds at the moment it
     runs, and an unanswered fetch simply means no synonym is offered yet,
     the same as a pair with none installed. */
  var SYN = null;
  function synLoad() {
    if (SYN !== null) return;
    SYN = {};
    fetch(MT.base + 'synonyms.en.json').then(function (r) {
      return r.ok ? r.json() : null;
    }).then(function (j) {
      SYN = (j && j.synonyms) || {};
    }).catch(function () { /* SYN stays {}: the aligner works without it */ });
  }

  /* The worker's protocol is {id, name, args} in and {id, result|error} out;
     everything below is one call of that. */
  function call(name, args, transfer) {
    if (!MT.worker) return Promise.reject(new Error('no engine'));
    var id = ++MT.seq;
    return new Promise(function (resolve, reject) {
      MT.waiting[id] = { resolve: resolve, reject: reject };
      MT.worker.postMessage({ id: id, name: name, args: args },
                            transfer || []);
    });
  }

  function start() {
    if (MT.started) return MT.started;
    // The engine's own glue does importScripts('bergamot-translator-worker.js')
    // and fetches the .wasm beside itself, so the worker must be created from
    // the directory both live in.
    MT.worker = new Worker(MT.base + 'engine/translator-worker.js');
    MT.worker.addEventListener('message', function (e) {
      var d = e.data || {};
      var w = MT.waiting[d.id];
      if (!w) return;
      delete MT.waiting[d.id];
      if (d.error) reject(w, d.error);
      else w.resolve(d.result);
    });
    MT.worker.addEventListener('error', function (e) {
      MT.failed = (e && e.message) || 'the engine did not start';
      for (var id in MT.waiting) {
        MT.waiting[id].reject(new Error(MT.failed));
        delete MT.waiting[id];
      }
    });
    // THE ENGINE HAS TO BE ASKED TO START.  `initialize` is what reads the
    // WebAssembly and builds the translation service; without it every later
    // call reaches a worker whose `module` is still undefined, and the first
    // thing it touches is AlignedMemory.
    MT.started = call('initialize', [{ cacheSize: 1 << 14,
                                       useNativeIntGemm: false }]);
    return MT.started;
  }

  function reject(w, err) {
    var e = new Error((err && err.message) || 'the engine refused');
    e.name = (err && err.name) || 'Error';
    w.reject(e);
  }

  function buffer(url) {
    return fetch(url).then(function (r) {
      if (!r.ok) throw new Error(url + ' -> ' + r.status);
      return r.arrayBuffer();
    });
  }

  /* Load one pair: its three files, into the worker, once. */
  function load(from, to) {
    var k = key(from, to);
    if (MT.loaded[k]) return MT.loaded[k];
    var ready = start();
    var dir = MT.base + k + '/';
    MT.loaded[k] = ready.then(function () { return fetch(dir + 'meta.json'); })
      .then(function (r) {
        if (!r.ok) throw new Error('no model for ' + k);
        return r.json();
      })
      .then(function (meta) {
        var f = meta.files || {};
        // A few pairs split the vocabulary in two and name the halves
        // separately; the rest carry one, which the engine wants twice.
        var vocabs = f.srcvocab && f.trgvocab ? [f.srcvocab, f.trgvocab]
                                              : [f.vocab, f.vocab];
        return Promise.all([
          buffer(dir + f.model),
          buffer(dir + f.lex),
          buffer(dir + vocabs[0]),
          vocabs[0] === vocabs[1] ? null : buffer(dir + vocabs[1])
        ]);
      })
      .then(function (bufs) {
        var model = bufs[0], lex = bufs[1], v1 = bufs[2], v2 = bufs[3];
        var vocabList = v2 ? [v1, v2] : [v1, v1];
        var send = [model, lex, v1];
        if (v2) send.push(v2);
        return call('loadTranslationModel',
                    [{ from: from, to: to },
                     { model: model, shortlist: lex, vocabs: vocabList }],
                    send);
      });
    return MT.loaded[k];
  }

  /* Is there a model here at all?  Asked before the switch is offered and
     before anything is read ahead, because a switch nobody can use is a
     switch that should not be there -- and BOTH
     halves have to be here.  The model is fetched per pair and the engine
     once, so a reader who removed the engine, or whose first download failed
     partway, can have one without the other; asking only about the model drew
     a button that could never work. */
  function has(from, to) {
    return Promise.all([
      fetch(MT.base + key(from, to) + '/meta.json'),
      fetch(MT.base + 'engine/meta.json')
    ]).then(function (rs) {
      if (!rs[0].ok || !rs[1].ok) return null;
      // A MODEL IS ABOUT TO BE OFFERED: fetch the synonym table now, so it
      // has the whole time between page load and a reader's first hover to
      // arrive -- rather than starting it only when a translation is first
      // asked for, which is also when the reading is first shown.
      synLoad();
      return rs[0].json();
    }).catch(function () { return null; });
  }

  /* One text or many.  MANY IS WHAT MATTERS: the engine translates a batch
     in one call and the cost is almost all fixed -- ten Persian sentences
     came back in 74 ms against 30 ms for one -- so preparing the next ten
     sentences costs about what preparing one does, which is the whole reason
     the panel can open already filled. */
  function translate(from, to, text) {
    var many = Array.isArray(text);
    var texts = (many ? text : [text]).map(function (t) { return String(t || ''); });
    if (!texts.length || (!many && !texts[0]))
      return Promise.resolve(many ? [] : '');
    synLoad();          // a backstop: has() already started this, normally
    return load(from, to).then(function () {
      return call('translate', [{
        models: [{ from: from, to: to }],
        texts: texts.map(function (t) {
          return { text: t, html: false, qualityScores: false };
        })
      }]);
    }).then(function (res) {
      var out = (res || []).map(function (r) {
        return (r && r.target && r.target.text) || '';
      });
      return many ? out : (out[0] || '');
    });
  }

  /* ---------- which words of the translation are this chunk's -------------
     The engine gives no word alignment -- its WebAssembly build exposes
     getTranslatedText and the sentence ranges, and nothing below that -- so
     this is a GUESS and is drawn as one.

     IT GOES BY MEANING, NEVER BY PLACE.  It used to prefer the run of the
     translation sitting where the chunk sits in its sentence, and to fall
     back on that place when nothing matched.  Word order is exactly what a
     translation changes: Persian puts its verb last and English second,
     Chinese puts a modifier before what it modifies, Spanish an adjective
     after, and the fixture's `هنوز چشمم` (my eye still) sits a third of the
     way into its sentence and nowhere near where "still" lands in English.
     So the place is not used at all.  What is used is what the chunk MEANS:

       - the DICTIONARY's senses for each of the chunk's words (the lookup
         the panel has already made): `باکو` is Baku, `رشت` Rasht, `کلاه`
         hat, `کوتاه` short -- and "the short hat of Baku and Rasht" is found
         word by word, wherever the translation put it;
       - the chunk translated ON ITS OWN, as a bag of words (poor prose, but
         `کاسب کارهای لباده دراز` alone says "business" and "Deraz", which
         the sentence's "businessman of the work of Labadde Deraz" has too).

     Only a word that CARRIES meaning can anchor a mark.  `از` is "of,
     from", `به` "to", `و` "and": those are in every English sentence, so
     a function word matched by the chunk's senses only extends a mark it
     touches.  Where nothing anchors, nothing is marked and the reader is
     told so -- a mark put by arithmetic looked exactly as confident as one
     put by the words, and was wrong wherever the order changed. */

  /* THREE KINDS OF ENGLISH WORD.  A FUNCTION word -- the, of, to, and --
     is in every sentence, and a match on it proves nothing: it may extend
     a mark it touches, never start one.  A LIGHT word -- up, down, under,
     all, not, without -- means something, and 下 is "under", بالا "up";
     but it is common enough that it starts a mark only where the dictionary
     gives it as the word's first meaning, and never on the chunk's own
     translation's say-so: 没有目标的 translated alone said "without", and
     the sentence's one "without" was the chunk before's ("without him").  Everything else is a CONTENT word, and
     one of those, matched, is what a mark stands on. */
  var STOP = ('a an the of to in on at is are was were be been being am and '
              + 'or but nor that this these those it its his her hers their '
              + 'theirs my mine your yours our ours for with as by from do '
              + 'does did done doing have has had having will would shall '
              + 'should can could may might must i you he she we they me him '
              + 'them us ones oneself someone something somebody sth sb etc s '
              + "one's someone's something's").split(' ');
  var LIGHT = ('up down out off over under into onto upon about all any some '
               + 'such very just also too there here then so if when where '
               + 'which who whom whose what how why than not no without within '
               + 'through across against among between behind beyond toward '
               + 'towards despite except during since until above below '
               + 'beneath beside along around near').split(' ');
  var STOPSET = {}, LIGHTSET = {};
  STOP.forEach(function (w) { STOPSET[w] = 1; });
  LIGHT.forEach(function (w) { LIGHTSET[w] = 1; });
  // one function word said two ways: آن is "that", the sentence says "those"
  var FN_SAME = { those: 'that', these: 'this', an: 'a' };
  function kind(k) { return STOPSET[k] ? 'fn' : LIGHTSET[k] ? 'light' : 'content'; }
  function fnKey(k) { return FN_SAME[k] || k; }

  /* A SENSE IS SOMETIMES A DEFINITION, and its words are not the word's.
     `را` is "Used to mark certain noun phrases as the direct object…",
     `یکی` a "Combination of the numeral…", a name "a female given name,
     Iran, from Middle Persian": matched, those would put "object", "mark" or
     "name" wherever the sentence has them.  So a sense is cut into its
     equivalents (at `;`, `,` and `.`, brackets out), and an equivalent
     longer than five words, one that describes grammar (GRAMMAR), or one
     that points elsewhere or names (META: "synonym of…", "See Usage notes",
     "a surname") is dropped: what is left is what a gloss line would
     print.  "See Usage notes", kept, put a mark on "see" for را. */
  var GRAMMAR = /^(used|only used|expresses|expressing|indicates|indicating|denotes|marks|makes|forms|follows|suffix|prefix|classifier|measure word|(an? )?(dummy )?pronoun|(an? )?(genitive |possessive |object |subject |topic |definite )?(particle|marker|case marker)|(genitive|possessive|dative|accusative|nominative|ablative|locative|instrumental|vocative)\b)\b/i;
  var META = /^(see|compare|cf|e\.?g|i\.?e|synonym|alternative|abbreviation|initialism|acronym|clipping|obsolete|archaic|dated|plural|singular|form|romanization|transliteration|(an? )?(male |female )?(given name|surname|name)|(the |an? )?\w+ (letter|character) of|an? (city|town|village|township|county|province|district|river|country|letter))\b/i;

  // the forms the stemmer below cannot reach by cutting a suffix off
  var IRREGULAR = {};
  ('arose:arise arisen:arise ate:eat eaten:eat awoke:awake bade:bid began:begin '
   + 'begun:begin bent:bend bit:bite bitten:bite blew:blow blown:blow bore:bear '
   + 'born:bear borne:bear bought:buy bound:bind bred:breed brought:bring '
   + 'broke:break broken:break built:build burnt:burn came:come caught:catch '
   + 'chose:choose chosen:choose clung:cling crept:creep dealt:deal did:do '
   + 'done:do drank:drink drunk:drink drew:draw drawn:draw drove:drive '
   + 'driven:drive dug:dig dwelt:dwell fed:feed fell:fall fallen:fall felt:feel '
   + 'fled:flee flew:fly flown:fly fought:fight found:find forbade:forbid '
   + 'forgave:forgive forgot:forget forgotten:forget froze:freeze frozen:freeze '
   + 'gave:give given:give went:go gone:go got:get gotten:get grew:grow '
   + 'grown:grow ground:grind hung:hang heard:hear held:hold hid:hide '
   + 'hidden:hide kept:keep knelt:kneel knew:know known:know laid:lay led:lead '
   + 'leapt:leap learnt:learn left:leave lent:lend lay:lie lain:lie lit:light '
   + 'lost:lose made:make meant:mean met:meet mistook:mistake paid:pay '
   + 'rode:ride ridden:ride rang:ring rung:ring rose:rise risen:rise ran:run '
   + 'said:say saw:see seen:see sought:seek sold:sell sent:send shook:shake '
   + 'shaken:shake shone:shine shot:shoot showed:show shown:show shrank:shrink '
   + 'sang:sing sung:sing sank:sink sunk:sink sat:sit slept:sleep slid:slide '
   + 'slung:sling spoke:speak spoken:speak spent:spend spun:spin spat:spit '
   + 'sprang:spring stood:stand stole:steal stolen:steal stuck:stick '
   + 'stung:sting strode:stride struck:strike strove:strive swore:swear '
   + 'sworn:swear swept:sweep swam:swim swum:swim swung:swing took:take '
   + 'taken:take taught:teach tore:tear torn:tear told:tell thought:think '
   + 'threw:throw thrown:throw trod:tread understood:understand woke:wake '
   + 'woken:wake wore:wear worn:wear wove:weave woven:weave wept:weep won:win '
   + 'wound:wind wrote:write written:write men:man women:woman children:child '
   + 'feet:foot teeth:tooth mice:mouse geese:goose grey:gray').split(' ').forEach(function (pair) {
    var p = pair.split(':');
    IRREGULAR[p[0]] = p[1];
  });

  /* ONE WORD, HOWEVER THE SENTENCE INFLECTED IT: the dictionary says "to
     fall", the translation "was not fallen"; "burn" and "burned", "city"
     and "cities", "make" and "making", "dark" and "darkness", "goal" and
     "goalless" (目标 in 没有目标的, which the translation made one word).  Both sides
     are cut the same way, so what matters is only that they meet.  English
     only -- the one language the models translate into here -- and in any
     other the word as it is. */
  function stem(w, en) {
    w = String(w || '').toLowerCase().replace(/['’]s$/, '').replace(/['’]/g, '');
    if (!en || w.length < 3) return w;
    if (IRREGULAR[w]) w = IRREGULAR[w];
    // one spelling for both sides of the Atlantic: رنگ is "colour" in the
    // dictionary and "color" in the translation; centre/center, realise/realize
    w = w.replace(/our(?=(s|ed|ing|ful|less)?$)/, 'or')
         .replace(/([^aeiou])tre(?=s?$)/, '$1ter')
         .replace(/is(?=(e|es|ed|ing|ation|ations)$)/, 'iz');
    var s = w;
    if (/(ness|less)$/.test(s) && s.length > 6) s = s.slice(0, -4);
    else if (/ful$/.test(s) && s.length > 5) s = s.slice(0, -3);
    else if (/ies$/.test(s) && s.length > 4) s = s.slice(0, -3) + 'y';
    else if (/ied$/.test(s) && s.length > 4) s = s.slice(0, -3) + 'y';
    else if (/ing$/.test(s) && s.length > 5) s = s.slice(0, -3);
    else if (/ed$/.test(s) && s.length > 4) s = s.slice(0, -2);
    else if (/(ss|sh|ch|x|z)es$/.test(s) && s.length > 4) s = s.slice(0, -2);
    else if (/[^s]s$/.test(s) && s.length > 3) s = s.slice(0, -1);
    // stopp(ed) -> stop, runn(ing) -> run; but fall, pass, buzz keep theirs
    if (s !== w && /([^aeiouls])\1$/.test(s)) s = s.slice(0, -1);
    if (/y$/.test(s) && s.length > 3) s = s.slice(0, -1) + 'i';
    if (/e$/.test(s) && s.length > 3) s = s.slice(0, -1);
    return s;
  }

  function keyOf(w) {
    return String(w || '').toLowerCase().replace(/^[^\w'’]+|[^\w'’]+$/g, '');
  }

  function words(s, en) {
    // keep the offsets: the panel marks inside the sentence it shows
    var out = [], re = /[^\s]+/g, m;
    while ((m = re.exec(String(s || '')))) {
      var key = keyOf(m[0]);
      // "red-clad" is red and clad: a gloss says "red"
      var parts = key.indexOf('-') > 0 ? key.split('-').filter(Boolean) : [];
      out.push({ raw: m[0], at: m.index, end: m.index + m[0].length, key: key,
                 st: stem(key, en), kind: key ? kind(key) : 'fn',
                 parts: parts.map(function (x) { return stem(x, en); }) });
    }
    return out;
  }

  // one letter apart, from six letters up: moustache/mustache, travelled/traveled
  function oneApart(a, b) {
    if (a.length < 6 || b.length < 6 || Math.abs(a.length - b.length) > 1) return false;
    var i = 0, j = 0, d = 0;
    while (i < a.length && j < b.length) {
      if (a[i] === b[j]) { i++; j++; continue; }
      if (++d > 1) return false;
      if (a.length > b.length) i++;
      else if (b.length > a.length) j++;
      else { i++; j++; }
    }
    return d + (a.length - i) + (b.length - j) <= 1;
  }

  var EMPTY = [];          // nothing to look a word up in, when SYN has no entry for it

  /* Two content words meet when they are the same once stemmed; more weakly
     when one begins the other (business/businessman, Iran/Iranian,
     Labad/Labadde) or ends it after a prefix of two letters or more
     (build/rebuild), from four letters up and most of the longer one; or
     when they are one letter apart (moustache/mustache).  Not `hand` in
     `handsome`, and not `ring` in `bring`: 帶回, "to bring back", put its
     mark on the translation's "stone ring". */
  function meet(a, b) {
    if (!a || !b) return 0;
    if (a === b) return 1;
    var s = a.length < b.length ? a : b, l = a.length < b.length ? b : a;
    if (s.length >= 4) {
      var r = s.length / l.length;
      if (l.indexOf(s) === 0 && r >= 0.55) return 0.8;
      if (l.lastIndexOf(s) === l.length - s.length && l.length - s.length >= 2
          && r >= 0.6) return 0.8;
    }
    if (oneApart(a, b)) return 0.75;
    // A SYNONYM IS REAL EVIDENCE, WEAKER THAN THE WORD ITSELF: begin/start,
    // help/aid.  lib/getsyn.py's table, both directions (its groups are
    // built symmetric, but a table fetched mid-build, or hand-edited, is not
    // trusted to stay that way).  Below every match above -- an exact word
    // always outscores a synonym of it, a mountain of paperwork is not a
    // hill -- and used at all only where the table has loaded (SYN is null
    // until synLoad's fetch resolves; see the module docstring).
    if (SYN && ((SYN[a] || EMPTY).indexOf(b) >= 0
             || (SYN[b] || EMPTY).indexOf(a) >= 0))
      return SYN_Q;
    return 0;
  }

  /* The chunk's words, each with what the dictionary says it means, as the
     lookup answered: [{word, hits: [{headword, senses: [...]}, ...]}, ...].
     Each equivalent is kept with how far down the answer it was -- the
     first hit's first sense counts most, a homograph's third sense least --
     so a stray homograph can lend weight but not outweigh the word.

     A WORD WHOSE FIRST MEANING IS A FUNCTION WORD IS ONE.  آن is first of
     all "that", به "to", که "that": their other hits are homographs --
     آن "moment", به "quince", که "small" -- and matched, they put a mark on
     "comes", "good", "small" wherever the sentence has them.  So where the
     first sense of the first hit gives function words only, the word has
     no content meanings at all, and its light ones start nothing; its
     function words still extend a mark.  A LIGHT first meaning does not
     make a word functional: luego is first "then", and then "later" --
     which is exactly the word "see you later" has.

     A GRAMMATICAL READING IN THE FIRST TWO ANSWERS makes one too.  The
     dictionary ranks 的 "bright; clear" first and its "genitive case
     marker" second; 到's second answer is "used as a verbal complement…".
     In running text those are particles, and their other readings marked
     the translation's "clear" and "go".  The cost, where one of them IS the
     verb, is a word left unmarked -- never a wrong mark.

     A WORD FROM A ONE-WORD EQUIVALENT COUNTS MOST.  "hat" is what کلاه
     means; "made" in 笄's "hairpin of women, perhaps made of bamboo" is a
     word of a description, and it put a mark on "made" for 雞 (chicken).

     AND ONLY AN EQUIVALENT THAT IS NOTHING BUT FUNCTION WORDS makes one a
     meaning: از is "of, from", و "and".  The "to" of "to wear" or the
     "the" of "the rest" says nothing about the chunk -- counted, every verb
     made "to" part of the chunk, and marks trailed off into "…sun to the". */
  var HIT_W = [1, 0.85, 0.7, 0.6], SENSE_W = [1, 0.9, 0.8];
  // a light word starts a mark only as the first meaning of a word that is
  // not a function word itself: 下 is first "under"; که is "that" first and
  // "when" only after, and "When" at the head of a sentence was marked for it
  var LIGHT_Q = 0.95;
  // how much a SYNONYM (lib/getsyn.py's table -- `meet`, below) is worth,
  // against an inflected match (0.8) or the word itself (1): below both,
  // always -- begin found for start is real, but weaker evidence than start
  // itself would be, and a wrong synonym costs less marked at this quality
  var SYN_Q = 0.62;

  // a sense's equivalents, and whether it OPENS with a grammar description
  function equivalents(sense) {
    var out = [], lead = null;
    String(sense || '').replace(/\([^()]*\)|\[[^\]]*\]|“[^”]*”|"[^"]*"/g, ' ')
      .split(/[;,:|.]/).forEach(function (eq) {
        eq = eq.trim();
        if (!eq) return;
        var ws = eq.split(/\s+/).map(keyOf).filter(Boolean);
        if (!ws.length) return;
        var grammar = GRAMMAR.test(eq);
        if (lead === null) lead = grammar;
        if (grammar || ws.length > 5 || META.test(eq)) return;
        out.push(ws);
      });
    out.grammar = !!lead;
    return out;
  }

  function meaningsOf(words_, en) {
    var out = [];
    (words_ || []).forEach(function (w) {
      var content = {}, light = {}, fn = {};
      var hits = (w && w.hits) || [];
      var functional = hits.slice(0, 2).some(function (h) {
        var eqs = equivalents(((h || {}).senses || [])[0]);
        // a first sense that opens by describing grammar ("genitive case
        // marker", "used as a verbal complement…") is a grammatical reading,
        // and one of function words only ("that; the", "of, from") is one
        // too; "synonym of abete rosso" (pezzo's second answer) is neither
        return eqs.grammar || (eqs.length > 0 && eqs.every(function (ws) {
          return ws.every(function (k) { return kind(k) === 'fn'; });
        }));
      });
      // THE WORD'S OWN FIRST SENSE, alone -- the one reading a synonym is
      // allowed to stand in for with nothing else corroborating it (see the
      // cluster filter below).  "started" for "begin" is real evidence on
      // its own; "started" for a fourth hit's obscure third sense is not,
      // and this list has only ever the first.
      var eq0 = equivalents(((hits[0] || {}).senses || [])[0]), firstContent = [];
      if (!eq0.grammar) {
        eq0.forEach(function (ws) {
          ws.forEach(function (k) {
            if (kind(k) === 'content') {
              var sk = stem(k, en);
              if (firstContent.indexOf(sk) < 0) firstContent.push(sk);
            }
          });
        });
      }
      function keep(bag, k, q) { if (!(k in bag) || bag[k] < q) bag[k] = q; }
      hits.forEach(function (h, hi) {
        (h.senses || []).forEach(function (sense, si) {
          var q = (HIT_W[hi] || 0.5) * (SENSE_W[si] || 0.7);
          equivalents(sense).forEach(function (ws) {
            var bare = ws.every(function (k) { return kind(k) !== 'content'; });
            var nContent = ws.filter(function (k) { return kind(k) === 'content'; }).length;
            var qc = q * (nContent <= 1 ? 1 : nContent === 2 ? 0.85 : 0.7);
            ws.forEach(function (k) {
              if (/^\d{5,}$/.test(k)) return;
              var kd = kind(k);
              if (kd === 'content') { if (!functional) keep(content, stem(k, en), qc); }
              else if (bare) keep(kd === 'light' ? light : fn, fnKey(k), q);
            });
          });
        });
      });
      out.push({ word: (w && w.word) || '', content: content, light: light, fn: fn,
                 functional: functional, firstContent: firstContent,
                 has: Object.keys(content).length > 0
                      || (!functional && Object.keys(light).some(function (k) {
                        return light[k] >= LIGHT_Q;
                      })) });
    });
    return out;
  }

  // how well one content token meets a bag of stems: its best
  function inContent(tok, bag) {
    var best = bag[tok.st] || 0;
    if (best >= 1) return best;
    for (var k in bag) {
      var m = meet(tok.st, k);
      tok.parts.forEach(function (p) { m = Math.max(m, 0.9 * meet(p, k)); });
      if (m * bag[k] > best) best = m * bag[k];
    }
    return best;
  }

  /* align(target, probe, words[, lang]) -> {ranges, from, to, text, sure,
     pairs, by} or null.  `words` is the lookup's answer for the chunk (its
     `words`), `probe` the chunk translated alone, `lang` what `target` is in
     ('en' unless said).  A number where `words` goes is the old caller's
     place in the sentence, and is ignored: see above. */
  function align(target, probe, words_, lang) {
    var en = !lang || lang === 'en';
    var T = words(target, en);
    if (!T.length) return null;
    var M = meaningsOf(Array.isArray(words_) ? words_ : [], en);
    // the chunk's own translation: its content words may start a mark; its
    // function words only say which of two equal marks is the chunk's
    var P = {}, Pfn = {};
    words(probe, en).forEach(function (w) {
      if (!w.key) return;
      if (w.kind === 'content') P[w.st] = 0.75; else Pfn[fnKey(w.key)] = 1;
    });

    var hot = T.map(function (tok) {
      var by = {}, best = 0, pr = 0, touched = {}, touch = false;
      M.forEach(function (m, k) {
        var q = 0;
        if (tok.kind === 'content') q = inContent(tok, m.content);
        else if (tok.kind === 'light') q = m.light[tok.key] || 0;
        else if (m.fn[fnKey(tok.key)]) { touch = true; touched[k] = 1; }
        if (tok.kind === 'light' && q > 0) { touch = true; touched[k] = 1; }
        if (tok.kind === 'light' && (q < LIGHT_Q || m.functional)) q = 0;
        if (q > 0) { by[k] = q; best = Math.max(best, q); }
      });
      if (tok.kind === 'content') pr = inContent(tok, P);
      return { by: by, best: best, probe: pr, touch: touch, touched: touched,
               anchor: best > 0 || pr > 0,
               hint: tok.kind !== 'content' && !!Pfn[fnKey(tok.key)] };
    });

    /* CLUSTERS: anchors that stand together, with nothing but at most two
       function or light words between them -- "parable of Iran", "Baku and
       Rasht".  A content word nobody matched ends a cluster: "the short hat
       of Baku" is two things, not one.  So does the end of a sentence: 是我
       发现她的 was marked "found her. She", its 她 reaching into the next.

       ONLY A STRONG ANCHOR (quality >= 0.7: the word itself, or an
       inflection of it) JOINS ONE.  A synonym-quality anchor (SYN_Q, below
       0.7) never extends a cluster, because "of the" between two repeats of
       it joins them just as readily as it joins two different words -- a
       garbled reading that says "Lord of the Lord, the Lord of the Lord"
       chained every repeat of صاحب's synonym "Lord" into one span covering
       the whole sentence, measured.  A weak anchor still gets its own
       single-token cluster and is judged on its own below (a lone synonym
       survives only from the word's OWN first sense, not a neighbour's). */
    var ENDS = /[.!?;:。！？；：…]["'”’)\]]*$/;
    var clusters = [], cur = null;
    for (var i = 0; i < T.length; i++) {
      if (!hot[i].anchor) continue;
      var strongNow = hot[i].best >= 0.7;
      // BOTH SIDES MUST BE STRONG: a strong anchor joining a cluster that
      // is only there because of an earlier WEAK one would give the weak
      // one a free ride on the strong one's admission -- "pueblo" (village)
      // reached "living" only through poblar, its unrelated second hit's
      // "to populate", at quality 0.53; "small" and "town" are its real,
      // strong matches two words later, and joining across "living" would
      // have marked "living in a small town" as if all three were the
      // chunk's, measured.
      if (cur && cur.strong && strongNow && i - cur.j <= 2 && !ENDS.test(T[cur.j - 1].raw)) {
        var ok = true;
        for (var g = cur.j; g < i; g++)
          if (T[g].kind === 'content' || ENDS.test(T[g].raw)) { ok = false; break; }
        if (ok) { cur.j = i + 1; continue; }
      }
      cur = { i: i, j: i + 1, strong: strongNow };
      clusters.push(cur);
    }
    // a function word the chunk's own meanings use, right at a cluster's
    // edge, is part of it: "from the bottom", "Baku and Rasht" -- but a
    // mark does not end on "and" or "the": those open what comes next
    var TAIL = { and: 1, or: 1, but: 1, the: 1, a: 1, an: 1 };
    clusters.forEach(function (c) {
      while (c.i > 0 && hot[c.i - 1].touch && !ENDS.test(T[c.i - 1].raw)) c.i--;
      while (c.j < T.length && hot[c.j].touch && !ENDS.test(T[c.j - 1].raw)) c.j++;
      while (c.j - 1 > c.i && !hot[c.j - 1].anchor && TAIL[T[c.j - 1].key]) c.j--;
    });

    // what a cluster accounts for: the chunk's words it covers, best quality
    // each, and the words of the chunk's own translation it shares
    function account(c) {
      var cov = {}, pr = {}, tcov = {}, score = 0, anchors = 0, top = 0;
      for (var x = c.i; x < c.j; x++) {
        if (hot[x].anchor) anchors++;
        for (var t in hot[x].touched) tcov[t] = 1;
        for (var k in hot[x].by) {
          if (!(k in cov) || cov[k] < hot[x].by[k]) cov[k] = hot[x].by[k];
          top = Math.max(top, hot[x].by[k]);
        }
        if (hot[x].probe) { pr[T[x].st] = hot[x].probe; top = Math.max(top, hot[x].probe); }
        if (hot[x].touch) score += 0.1;
      }
      for (var k2 in cov) score += cov[k2];
      for (var p in pr) score += 0.5 * pr[p];
      // the chunk's own translation puts "my" before "soul": of two clusters
      // on the same word, the one standing where that translation stands it
      for (var y = Math.max(0, c.i - 1); y < Math.min(T.length, c.j + 1); y++)
        if (hot[y].hint) score += 0.05;
      return { cov: cov, pr: pr, tcov: tcov, score: score, anchors: anchors, top: top };
    }
    clusters.forEach(function (c) { c.acc = account(c); });
    // A LONE WEAK MATCH IS NOT A MARK: a homograph's third sense, or a
    // spelling one letter off, standing by itself.  A LONE SYNONYM IS,
    // where the word it stands for is the ONE it is a synonym of: "started"
    // survives alone for "begin" (begin's own first sense), not for a
    // fourth hit's stray third sense that happens to share a synonym too.
    clusters = clusters.filter(function (c) {
      if (c.acc.top >= 0.7 || c.acc.anchors >= 2) return true;
      for (var x = c.i; x < c.j; x++) {
        if (T[x].kind !== 'content') continue;
        for (var k in c.acc.cov) {
          if ((M[k].firstContent || EMPTY).some(function (fc) {
            return meet(T[x].st, fc) >= SYN_Q && meet(T[x].st, fc) < 0.75;
          })) return true;
        }
      }
      return false;
    });
    if (!clusters.length) return null;
    var order = clusters.slice().sort(function (a, b) {
      return b.acc.score - a.acc.score || (a.j - a.i) - (b.j - b.i);
    });

    /* THE BEST, AND WHAT ELSE THE CHUNK'S MEANING NEEDS.  A chunk whose
       words land apart in English -- a German verb and its prefix, a Persian
       object and its verb -- is marked in as many places as it lands in, but
       only where a place adds a word of the chunk the others do not cover.
       A word the translation says twice, with nothing to tell the two apart,
       is marked twice: which of them is this chunk's the words cannot say,
       and the place is no guide.  A word already in a mark by its function
       word is in it: در is "in" there, and its homograph "door" further on
       is not a second place the chunk landed. */
    var chosen = [order[0]], covered = {}, present = {}, probed = {};
    for (var k3 in order[0].acc.cov) covered[k3] = present[k3] = 1;
    for (var t3 in order[0].acc.tcov) present[t3] = 1;
    for (var p3 in order[0].acc.pr) probed[p3] = 1;
    var sig0 = Object.keys(order[0].acc.cov).sort().join(',');
    for (var c2 = 1; c2 < order.length && chosen.length < 3; c2++) {
      var o = order[c2], adds = false;
      for (var k4 in o.acc.cov) if (!present[k4] && o.acc.cov[k4] >= 0.6) adds = true;
      // the chunk's own translation's content words are all the chunk's:
      // "John Ba Azrael" landed as "And John" and "the Azrael"; رؤیاهایش را
      // پیدا کرد, "He found his dreams", as "found" and "dreams" -- and the
      // dictionary, which has پیدا only as "evident", could say only one.
      // ONLY A STRONG probe match adds on its own: a synonym of the probe
      // (aid, for a probe "help") is not enough by itself, or "aid" joined
      // "helped" in a sentence where the dictionary's own word already won.
      for (var p4 in o.acc.pr) if (!probed[p4] && o.acc.pr[p4] >= 0.7) adds = true;
      var tie = Math.abs(o.acc.score - order[0].acc.score) < 1e-9
                && Object.keys(o.acc.cov).sort().join(',') === sig0;
      if (adds || tie) {
        chosen.push(o);
        for (var k5 in o.acc.cov) covered[k5] = present[k5] = 1;
        for (var t5 in o.acc.tcov) present[t5] = 1;
        for (var p5 in o.acc.pr) probed[p5] = 1;
      }
    }
    chosen.sort(function (a, b) { return a.i - b.i; });

    var meaningful = M.filter(function (m) { return m.has; }).length;
    var got = Object.keys(covered).filter(function (k) { return M[k].has; }).length;
    var byDict = Object.keys(covered).length > 0;
    var byProbe = chosen.some(function (c) { return Object.keys(c.acc.pr).length > 0; });
    // SURE where the dictionary accounts for half the chunk's words that have
    // a meaning -- or, with no dictionary, the chunk's own translation for
    // half its words; otherwise marked, and said to be partial
    var probeWords = Object.keys(P).length;
    var sure = meaningful ? got / meaningful >= 0.5
                          : probeWords > 0 && chosen.reduce(function (n, c) {
                              return n + Object.keys(c.acc.pr).length;
                            }, 0) / probeWords >= 0.5;

    // which word of the chunk each marked word stands for, for the line under it
    var pairs = [], seen = {};
    chosen.forEach(function (c) {
      for (var x = c.i; x < c.j; x++) {
        var bestK = null, bestQ = 0;
        for (var k in hot[x].by) if (hot[x].by[k] > bestQ) { bestQ = hot[x].by[k]; bestK = k; }
        if (bestK !== null && !seen[bestK + '|' + T[x].st]) {
          seen[bestK + '|' + T[x].st] = 1;
          pairs.push({ word: M[bestK].word, as: T[x].raw });   // as written: "Iran"
        }
      }
    });

    var ranges = chosen.map(function (c) {
      return { from: T[c.i].at, to: T[c.j - 1].end };
    });
    return {
      ranges: ranges,
      from: ranges[0].from, to: ranges[ranges.length - 1].to,
      text: ranges.map(function (r) { return String(target).slice(r.from, r.to); })
                  .join(' … '),
      sure: sure, pairs: pairs,
      by: byDict && byProbe ? 'both' : byDict ? 'dictionary' : 'translation'
    };
  }

  /* The sentence cut at the marks, for a reader to draw: [{text, here}]. */
  function marked(target, span) {
    var out = [], at = 0, t = String(target || '');
    ((span && span.ranges) || []).forEach(function (r) {
      if (r.from > at) out.push({ text: t.slice(at, r.from), here: false });
      out.push({ text: t.slice(r.from, r.to), here: true });
      at = r.to;
    });
    if (at < t.length) out.push({ text: t.slice(at), here: false });
    return out;
  }

  /* What the line under the reading says the mark rests on: which of the
     chunk's words the dictionary found where -- "مثل → parable · ایران →
     Iran" -- with the punctuation the chunk's words carry ("Vale,", "جان،")
     taken off. */
  var EDGE = /^[\s.,;:!?¿¡«»"“”'‘’()\[\]،؛؟…。，、；：！？（）]+|[\s.,;:!?¿¡«»"“”'‘’()\[\]،؛؟…。，、；：！？（）]+$/g;
  function why(span) {
    var seen = {};
    return ((span && span.pairs) || []).map(function (p) {
      return String(p.word).replace(EDGE, '') + ' \u2192 ' + String(p.as).replace(EDGE, '');
    }).filter(function (x) {
      if (seen[x]) return false;
      seen[x] = 1;
      return true;
    }).join(' \u00b7 ');
  }

  root.ParsehMT = { has: has, translate: translate, load: load, align: align,
                    marked: marked, why: why,
                    // _stem and _syn are for tests only (lib/getsyn.py ports
                    // `stem` by hand, and tests/smoke.py's test_getsyn checks
                    // the two agree on the same word list; mtcheck checks the
                    // synonym file loads). Not part of the public API.
                    _stem: stem, get _syn() { return SYN; },
                    get failed() { return MT.failed; } };
})(this);

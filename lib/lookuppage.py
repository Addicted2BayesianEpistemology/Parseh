#!/usr/bin/env python3
"""The page that sets up reading a book nobody has glossed, at /lookup/.

  THE DICTIONARIES.  One button per language: fetch it, watch it build, see
  how big it is and where it came from, throw it away.  What used to be
  `python3 lib/getdict.py fa` and a person who never found out that command
  existed.

  THE CORPORA.  The same row again, for the half a dictionary cannot do:
  a dictionary lists every sense a word can carry and cannot say which one
  this sentence means, so the panel can also show a whole sentence somebody
  translated that shares the chunk's rare words.  A corpus is a PAIR of
  languages, so each row carries what it already has and a picker for what
  to add.

Nothing here is required: Parseh gains no dependency and sends nothing
anywhere.  The download is Wiktionary's own extract, it happens on this
machine, and what it leaves behind is one file per language under `dict/`.

THE PAGE IS LINKED FROM THE HUB AND FROM BOTH READERS, which is the whole
difference between a feature and a feature somebody can use.  It was neither
for a while, and might as well not have existed.
"""
import io
import json
import os
import sys

LIB = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(LIB)
sys.path.insert(0, LIB)
import languages                                               # noqa: E402
import decomposition
import corpus                                                  # noqa: E402
import getmt                                                   # noqa: E402
import getsyn                                                  # noqa: E402
import lookup                                                  # noqa: E402


def dictionaries():
    """Every language the toolbox teaches, and what it has to read it with."""
    out = []
    for L in languages.LANGS.values():
        m = lookup.about(L.code) or {}
        row = {"code": L.code, "name": L.name, "native": L.native,
               "have": bool(m), "entries": m.get("entries", ""),
               "source": m.get("source", ""), "licence": m.get("licence", ""),
               "built": m.get("built", ""), "size": 0}
        if m:
            try:
                row["size"] = os.path.getsize(lookup.path_for(L.code))
            except OSError:
                row["size"] = 0
        out.append(row)
    return out


def corpora():
    """Every language, and which of its parallel corpora are installed.

    One row per language, carrying the pairs it already has -- Persian
    glossed in English and Persian glossed in Italian are two files, because
    a corpus is a pair of languages and not one.
    """
    out = []
    have = {}
    for a, b in corpus.installed():
        have.setdefault(a, []).append(b)
    for L in languages.LANGS.values():
        rows = []
        for g in sorted(have.get(L.code, [])):
            m = corpus.about(L.code, g) or {}
            size = 0
            try:
                size = os.path.getsize(corpus.path_for(L.code, g))
            except OSError:
                pass
            G = languages.get_or_default(g)
            rows.append({"gloss": g, "gloss_name": G.name,
                         "pairs": m.get("pairs", ""), "source": m.get("source", ""),
                         "licence": m.get("licence", ""), "built": m.get("built", ""),
                         "size": size})
        # A LANGUAGE WITH NO WORD SEPARATOR CANNOT BE INDEXED UNTIL ITS
        # DICTIONARY IS HERE.  The corpus index is per word, and finding the
        # words of 我喜欢喝茶 means cutting it, which only the dictionary's
        # own word list can do.  Offering the button first builds a corpus
        # that reports itself built and can never match anything.
        out.append({"code": L.code, "name": L.name, "native": L.native,
                    "have": rows,
                    "needs_dict": bool(not L.spaced
                                       and not lookup.available(L.code))})
    return out


def models():
    """Every language, and which translation models are installed for it."""
    out = []
    have = {}
    for a, b in getmt.installed():
        have.setdefault(a, []).append(b)
    for L in languages.LANGS.values():
        rows = []
        for g in sorted(have.get(L.code, [])):
            m = getmt.about(L.code, g) or {}
            d = getmt.path_for(L.code, g)
            size = 0
            try:
                size = sum(os.path.getsize(os.path.join(d, n))
                           for n in os.listdir(d))
            except OSError:
                pass
            G = languages.get_or_default(g)
            rows.append({"gloss": g, "gloss_name": G.name, "size": size,
                         "source": m.get("source", ""),
                         "licence": m.get("licence", ""),
                         "built": m.get("built", "")})
        out.append({"code": L.code, "name": L.name, "native": L.native,
                    "have": rows,
                    # only the glosses a model could exist for: Mozilla trains
                    # against English and not against other languages, so
                    # offering Italian beside Persian is offering a download
                    # that is not there
                    "can": [g.code for g in languages.LANGS.values()
                            if getmt.trainable(L.code, g.code)]})
    return out


def synonym_table():
    """Is the aligner's synonym table here, and what it is.

    ONE ROW, not one per language: unlike a dictionary or a corpus this is
    not about any one language, it is English words the machine's reading
    is already in, so there is exactly one file and exactly one thing to
    say about it.
    """
    if not getsyn.installed():
        return {"have": False}
    meta, size = {}, 0
    try:
        meta = json.load(io.open(getsyn.OUT, encoding="utf-8"))
    except (OSError, ValueError):
        pass
    try:
        size = os.path.getsize(getsyn.OUT)
    except OSError:
        pass
    return {"have": True, "size": size,
            "entries": len(meta.get("synonyms") or {}),
            "source": meta.get("source", ""), "licence": meta.get("licence", ""),
            "built": meta.get("built", "")}


def glosses():
    """What a corpus can be glossed in: every language the toolbox teaches."""
    return [{"code": L.code, "name": L.name} for L in languages.LANGS.values()]


def page(base=""):
    return TEMPLATE.replace("__DICTS__", json.dumps(dictionaries())) \
                   .replace("__CORPORA__", json.dumps(corpora())) \
                   .replace("__MODELS__", json.dumps(models())) \
                   .replace("__SYN__", json.dumps(synonym_table())) \
                   .replace("__DECOMPOSITIONS__", json.dumps(decomposition.packs())) \
                   .replace("__GLOSSES__", json.dumps(glosses()))


TEMPLATE = r"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Reading what nobody has glossed — Parseh</title>
<link rel="stylesheet" href="/lib/parseh.css">
<script src="/lib/parseh.js"></script>
<style>
main{max-width:760px;margin:0 auto;padding:22px 20px 80px}
h1{font-size:23px;margin:0 0 4px}
.sub{color:var(--dim);margin:0 0 22px}
button.go{font:inherit;font-size:13px;background:var(--accent);color:var(--accent-fg);
  border:1px solid var(--accent);border-radius:7px;padding:6px 14px;cursor:pointer}
button.go[disabled]{opacity:.5;cursor:default}
button.plain{font:inherit;font-size:13px;background:var(--bg);color:var(--dim);
  border:1px solid var(--rule);border-radius:7px;padding:6px 12px;cursor:pointer}
button.plain:hover{color:var(--accent);border-color:var(--accent)}
.foot{color:var(--faint);font-size:12.5px;line-height:1.6;margin-top:26px}
h2.part{font-size:16px;margin:30px 0 6px;padding-bottom:6px;
  border-bottom:1px solid var(--rule)}
.lead{color:var(--dim);font-size:13.5px;line-height:1.6;margin:6px 0 12px}
.dicts{border:1px solid var(--rule);border-radius:12px;background:var(--card);
  overflow:hidden}
.drow{display:flex;align-items:center;gap:12px;padding:10px 14px;
  border-top:1px solid var(--rule);font-size:13.5px}
.drow:first-child{border-top:none}
.drow .dnam{flex:none;width:150px;color:var(--ink)}
.drow .dnat{color:var(--faint);font-size:12px}
.drow .dabt{flex:1;color:var(--dim);font-size:12.5px;min-width:0}
.drow .dabt b{color:var(--ink);font-weight:600}
.drow .dbtns{flex:none;display:flex;gap:6px;align-items:center}
.drow .dabt button.plain{font-size:11.5px;padding:2px 8px;margin-inline-start:4px}
select.gsel,select.msel{font:inherit;font-size:12.5px;padding:5px 8px;border-radius:7px;
  border:1px solid var(--rule);background:var(--bg);color:var(--ink)}
@media(max-width:600px){.drow{flex-wrap:wrap}.drow .dnam{width:100%}.drow .dabt{flex-basis:55%}}
.drow.busy{background:var(--hl)}
.bar{height:3px;background:var(--rule);border-radius:2px;overflow:hidden;
  margin-top:5px}
.bar i{display:block;height:100%;background:var(--accent);width:30%;
  animation:slide 1.4s ease-in-out infinite}
@keyframes slide{0%{margin-left:-30%}100%{margin-left:100%}}
</style>
</head><body>
<header lang="en" dir="ltr"><div class="hrow">
  <a class="home glyph" href="/" title="Parseh — the hub">&#x67E;</a>
  <span class="sp"></span>
  <button id="theme" data-parseh-theme title="theme: light / dark / sepia">◐</button>
</div></header>
<main>
<h1>Reading a book nobody has glossed</h1>
<p class="sub">Between pasting a text in and finishing its glosses lie weeks,
and for those weeks every chunk is a phrase you cannot get past. A dictionary
helps, and it is set up here. It is optional, it is off until you turn it on,
and a reader without one is exactly the reader it has always been.</p>

<h2 class="part">A dictionary</h2>
<p class="lead">Look the words of an unglossed chunk up. Pick a language and
press <b>get it</b> &mdash; Parseh downloads Wiktionary's own extract for it
and builds a database, once. That download is 30&nbsp;MB for a small language
and half a gigabyte for a large one, and it happens on this machine: nothing
about what you read is sent anywhere, and nothing is kept but the file. Then
the <b>dictionary</b> switch appears in the header of every reader and player
of that language.</p>
<div id="dicts" class="dicts">loading…</div>
<p class="lead" style="margin-top:14px">A language with no dictionary is read
exactly as it is read today; it simply is not offered one. The files live in
<code>dict/</code> and are yours to delete at any time.</p>

<h2 class="part" id="character-components">Kanji &amp; Hanzi components</h2>
<p class="lead">Explore the parts of a character in books and videos. Install
<b>KanjiVG</b> for Japanese or <b>Make Me a Hanzi</b> for Chinese; optionally add
<b>CJKVI-IDS</b> for extended coverage when the preferred pack has no entry.
Then choose <b>Decompose Kanji</b> or <b>Decompose Hanzi</b> in a reader.
These packs contain component trees only. Meanings use your existing dictionary;
without one, the trees still work. Downloads happen once and inspection works offline.</p>
<div id="decompositions" class="dicts">loading…</div>
<p class="lead">KanjiVG is about 24 MB to download; the other sources about 3 MB each.
Each local pack keeps its own source attribution and licence. Removing a pack
leaves your books, videos and dictionaries unchanged.</p>

<h2 class="part">Sentences somebody has already translated</h2>
<p class="lead">A dictionary lists every sense a word can carry and cannot
say which one your sentence means &mdash; <span lang="fa" dir="rtl">شیر</span>
is lion, faucet, tiger and milk. So the panel can also show a <b>whole
sentence</b> that a person wrote and another person translated, picked
because it shares the rare words of the chunk you are looking at. It is not
a translation of your line and never pretends to be: both sides are shown,
with the words they share named under them. The sentences come from
<a href="https://tatoeba.org" target="_blank" rel="noopener">Tatoeba</a>,
whose contributors release them under CC&nbsp;BY&nbsp;2.0&nbsp;FR, and the
download happens on this machine like the dictionaries'.</p>
<div id="corpora" class="dicts">loading…</div>
<p class="lead" style="margin-top:14px">A corpus is a <b>pair</b> of
languages, so pick what your glosses are written in. Coverage is very
uneven, and so is the size: Italian&ndash;English is 719&nbsp;000 sentence
pairs and 182&nbsp;MB, Spanish&ndash;English 283&nbsp;123 and 83&nbsp;MB,
Persian&ndash;English 8&nbsp;454 and 3&nbsp;MB &mdash; two orders of
magnitude between the ends of that list, and a thin pair simply finds a
sentence to show you less often. The files live in
<code>corpus/</code>.</p>
<h2 class="part">A translation model, in the page</h2>
<p class="lead">Where the dictionary reads the words and the corpus finds a
sentence like yours, a <b>translation model</b> reads the sentence itself. It
is not a chat model and there is nothing to configure: one job, no prompt, no
address, no key, and the same answer every time. It runs as WebAssembly
<i>inside the reader</i>, so the line being translated never leaves this
machine and Parseh gains no dependency to run it. The engine is
<a href="https://github.com/browsermt/bergamot-translator" target="_blank"
rel="noopener">bergamot-translator</a>, the one Firefox's own translations
use, and the models are Mozilla's &mdash; about 20&nbsp;MB a pair against
gigabytes for a general model. What it reads is the <b>whole sentence</b>
and not the chunk: a chunk is a fragment by construction, and a fragment
translated alone comes back as one &mdash;
<span lang="fa" dir="rtl">مثل ایران با هم</span> on its own gave &ldquo;The
parable of Iran with Hem&rdquo;, three words each defensible and a sentence
about nothing, while the sentence holding
<span lang="fa" dir="rtl">دوباره می‌سازمت، وطن</span> came back &ldquo;I will
rebuild you, my country&hellip;&rdquo; &mdash; the near future and the
attached <i>you</i> that the fragment lost. So
the sentence is shown entire, with the words of it that look like your
chunk's marked inside it and named under it &mdash; a guess, since the
engine offers no word alignment, and drawn as one. Nothing is pressed: the
reading is already in the panel when it opens, because the sentences ahead
of you were translated while you read. It is drawn in the same panel as the
rest, labelled <i>a machine's reading</i>, and is never written into a
book.</p>
<div id="models" class="dicts">loading…</div>
<p class="lead" style="margin-top:14px">Mozilla trains its pairs
<b>against English</b> rather than against each other, so Persian glossed in
English has a model and the same book glossed in Italian has none &mdash; a
pair that cannot exist is never offered one. The engine is fetched once and
shared, and the files live in <code>mt/</code>.</p>

<h2 class="part">Which words of a reading are the chunk's</h2>
<p class="lead">The engine gives no word alignment, so the panel's guess at
which words of a machine's reading are this chunk's works from what the
<b>dictionary</b> says the chunk's words mean. Where the model chose a
different word for the same idea &mdash; <i>begin</i> where the dictionary
says <i>start</i> &mdash; nothing in the reading matches, and the guess used
to say nothing at all. This is the same idea again, one step further: a
table of which English words are <b>synonyms</b> of which, from
<a href="https://wordnet.princeton.edu/" target="_blank"
rel="noopener">WordNet</a> (Princeton University). A synonym is real
evidence and is used, but weaker than the word itself &mdash; an exact match
always wins over one &mdash; and it is admitted alone only from a word's own
first, most common sense, never a stray one three senses down. One file,
about a megabyte, and nothing about any one language: get it once.</p>
<div id="syn" class="dicts">loading…</div>


<p class="foot">
What the dictionary shows is every sense a word can carry, which is not the
same as the one this sentence wants: it is a reference to read past a chunk
with, never a gloss. It appears in its own panel, only where nobody has
written a vocabulary line. One switch in the header of every reader and
every player turns the help on &mdash; it is there as soon as any one of the
three above is installed for that language &mdash; and it can be turned off
there without coming back here.
</p>
</main>
<script>
let DICTS = __DICTS__, CORPORA = __CORPORA__, MODELS = __MODELS__, SYN = __SYN__;
let DECOMPOSITIONS = __DECOMPOSITIONS__;
let ENGINE = false;
const GLOSSES = __GLOSSES__;
const $ = s => document.querySelector(s);
const api = (what, body) => fetch('/lookup/api/' + what, {
  method: 'POST', headers: {'Content-Type': 'application/json'},
  body: JSON.stringify(body || {})}).then(r => r.json()).then(j => {
    // a download just started is a job the server lists (lib/activity.js
    // draws the list): ask for it now rather than at the next slow poll
    if (/^get/.test(what) && window.ParsehActivity) ParsehActivity.poke(200);
    return j;
  });


/* ---- the dictionaries ---------------------------------------------------
   One row per language the toolbox teaches, and one button that does the
   whole of what `python3 lib/getdict.py <code>` did -- which is the right
   comparison, because a command nobody finds is a feature nobody has. */
const MB = n => n >= 1e9 ? (n / 1e9).toFixed(1) + ' GB'
                         : Math.max(1, Math.round(n / 1e6)) + ' MB';
const esc = s => (s || '').replace(/[<>&"]/g, c =>
  ({'<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;'}[c]));

function drawDecompositions(jobs = {}) {
  $('#decompositions').innerHTML = DECOMPOSITIONS.map(d => {
    const job = jobs[d.source] || {}, busy = job.running;
    const detail = busy ? esc(job.say || 'Installing…') + '<div class="bar"><i></i></div>'
      : job.error ? '<span style="color:var(--danger)">' + esc(job.error) + '</span>'
      : d.have ? Number(d.entries).toLocaleString() + ' entries · ' + MB(d.size) + ' · ' + esc(d.licence)
      : (d.source === 'cjkvi' ? 'Optional fallback for both languages' : d.languages[0] === 'ja' ? 'Japanese component trees' : 'Chinese component trees') + ' · ' + esc(d.licence);
    const buttons = busy ? '' : '<button class="' + (d.have ? 'plain' : 'go') + '" data-component-get="' + d.source + '">' + (d.have ? 'rebuild' : 'get it') + '</button>' +
      (d.have ? '<button class="plain" data-component-drop="' + d.source + '">remove</button>' : '');
    return '<div class="drow' + (busy ? ' busy' : '') + '"><div class="dnam"><a href="' + esc(d.url) + '" target="_blank" rel="noopener">' + esc(d.name) + '</a></div><div class="dabt">' + detail + '</div><div class="dbtns">' + buttons + '</div></div>';
  }).join('');
}
let componentTimer;
function pollDecompositions() {
  clearTimeout(componentTimer);
  return api('decompositions').then(j => {
    if (!j.ok) throw Error(j.error);
    DECOMPOSITIONS = j.packs; drawDecompositions(j.jobs);
    if (Object.values(j.jobs || {}).some(x => x.running)) componentTimer = setTimeout(pollDecompositions, 1200);
  }).catch(e => { Parseh.toast('Could not check component installation: ' + e.message, true); });
}
drawDecompositions(); pollDecompositions();
document.addEventListener('click', async e => {
  const button = e.target.closest('[data-component-get],[data-component-drop]');
  if (!button) return;
  const removing = !!button.dataset.componentDrop;
  const source = button.dataset.componentDrop || button.dataset.componentGet;
  if (removing && !confirm('Remove this component pack? You can install it again at any time.')) return;
  button.disabled = true;
  try {
    const j = await api(removing ? 'dropdecomposition' : 'getdecomposition', {source});
    if (!j.ok) throw Error(j.error || 'Request failed');
    await pollDecompositions();
  } catch (err) { button.disabled = false; Parseh.toast(err.message, true); }
});


function drawDicts(jobs) {
  jobs = jobs || {};
  $('#dicts').innerHTML = DICTS.map(d => {
    const job = jobs[d.code];
    const busy = job && job.running;
    let about;
    if (busy) {
      about = '<div>' + esc(job.say || 'working…') + '</div><div class="bar"><i></i></div>';
    } else if (job && job.error) {
      about = '<span style="color:var(--danger)">' + esc(job.error) + '</span>';
    } else if (d.have) {
      about = '<b>' + Number(d.entries || 0).toLocaleString() + '</b> entries · ' +
              MB(d.size) + ' · ' + esc(d.source) +
              (d.licence ? ' · ' + esc(d.licence) : '') +
              (d.built ? ' · built ' + esc(d.built) : '');
    } else {
      // Turkish's extract is 431 MB and builds to 237 MB; Persian's whole
      // built file is 18 MB.  "Tens of megabytes" was true of the one I
      // happened to build first and of almost nothing else.
      about = 'no dictionary yet — a download of 30 MB for a small ' +
              'language to half a gigabyte for a large one, once';
    }
    const btns = busy ? ''
      : d.have
        ? '<button class="plain" data-drop="' + d.code + '">remove</button>' +
          '<button class="plain" data-get="' + d.code + '">rebuild</button>'
        : '<button class="go" data-get="' + d.code + '">get it</button>';
    return '<div class="drow' + (busy ? ' busy' : '') + '">' +
           '<div class="dnam">' + esc(d.name) +
           ' <span class="dnat" lang="' + d.code + '">' + esc(d.native) + '</span></div>' +
           '<div class="dabt">' + about + '</div>' +
           '<div class="dbtns">' + btns + '</div></div>';
  }).join('');
}
drawDicts();

let dictTimer = null;
function pollDicts() {
  api('dicts', {}).then(j => {
    if (!j || !j.ok) return;
    DICTS = j.dicts;
    drawDicts(j.jobs);
    const working = Object.values(j.jobs || {}).some(x => x.running);
    clearTimeout(dictTimer);
    if (working) dictTimer = setTimeout(pollDicts, 1200);
  }).catch(() => {});
}
pollDicts();

/* ---- 3: the translation model ------------------------------------------
   The same row again.  It says the size plainly, because 20 MB is a decision
   somebody should make on purpose, and it says whether the shared engine is
   here yet. */
function drawModels(jobs) {
  jobs = jobs || {};
  $('#models').innerHTML = MODELS.map(d => {
    const running = Object.entries(jobs).find(
      ([k, v]) => k.startsWith(d.code + '-') && v.running);
    const bad = Object.entries(jobs).find(
      ([k, v]) => k.startsWith(d.code + '-') && v.error);
    let about;
    if (running) {
      about = '<div>' + esc(running[1].say || 'working…') +
              '</div><div class="bar"><i></i></div>';
    } else if (bad) {
      about = '<span style="color:var(--danger)">' + esc(bad[1].error) + '</span>';
    } else if (d.have.length) {
      about = d.have.map(h =>
        '<div>into <b>' + esc(h.gloss_name) + '</b> · ' + MB(h.size) + ' · ' +
        esc(h.source) + (h.licence ? ' · ' + esc(h.licence) : '') +
        ' <button class="plain" data-dropm="' + d.code + '" data-gloss="' +
        h.gloss + '">remove</button></div>').join('');
    } else {
      about = 'nothing yet — about 20 MB a pair, plus a 5 MB engine once';
    }
    const has = new Set(d.have.map(h => h.gloss));
    const can = new Set(d.can || []);
    const opts = GLOSSES.filter(g => can.has(g.code) && !has.has(g.code))
      .map(g => '<option value="' + g.code + '"' +
                (g.code === 'en' ? ' selected' : '') + '>' +
                esc(g.name) + '</option>').join('');
    if (!can.size)
      about = 'no model exists for this language — Mozilla trains its pairs ' +
              'against English, and this one is not among them';
    const btns = running || !opts ? ''
      : '<select class="msel" data-for="' + d.code + '">' + opts + '</select>' +
        '<button class="go" data-getm="' + d.code + '">get it</button>';
    return '<div class="drow' + (running ? ' busy' : '') + '">' +
           '<div class="dnam">' + esc(d.name) +
           ' <span class="dnat" lang="' + d.code + '">' + esc(d.native) + '</span></div>' +
           '<div class="dabt">' + about + '</div>' +
           '<div class="dbtns">' + btns + '</div></div>';
  }).join('');
}
drawModels();

let mtTimer = null;
function pollModels() {
  api('models', {}).then(j => {
    if (!j || !j.ok) return;
    MODELS = j.models; ENGINE = !!j.engine;
    drawModels(j.jobs);
    const working = Object.values(j.jobs || {}).some(x => x.running);
    clearTimeout(mtTimer);
    if (working) mtTimer = setTimeout(pollModels, 1500);
  }).catch(() => {});
}
pollModels();

document.addEventListener('click', e => {
  const getm = e.target.closest && e.target.closest('[data-getm]');
  const dropm = e.target.closest && e.target.closest('[data-dropm]');
  if (getm) {
    const code = getm.dataset.getm;
    const sel = document.querySelector('.msel[data-for="' + code + '"]');
    api('getmodel', {code: code, gloss: sel ? sel.value : 'en'})
      .then(() => pollModels());
    getm.disabled = true;
    return;
  }
  if (dropm) {
    const code = dropm.dataset.dropm, gloss = dropm.dataset.gloss;
    const d = MODELS.find(x => x.code === code) || {};
    if (!confirm('Remove the ' + (d.name || '') + '-to-' + gloss + ' model?' +
                 '\n\nThe files are deleted. You can get them again whenever ' +
                 'you like.'))
      return;
    api('dropmodel', {code: code, gloss: gloss}).then(() => pollModels());
  }
});

/* ---- the synonym table --------------------------------------------------
   ONE ROW: there is one file, not one per language, so this is the
   dictionaries' row without the per-language loop or the gloss picker. */
function drawSyn(job) {
  let about;
  if (job && job.running) {
    about = '<div>' + esc(job.say || 'working…') + '</div><div class="bar"><i></i></div>';
  } else if (job && job.error) {
    about = '<span style="color:var(--danger)">' + esc(job.error) + '</span>';
  } else if (SYN.have) {
    about = '<b>' + Number(SYN.entries || 0).toLocaleString() + '</b> words · ' +
            MB(SYN.size) + ' · ' + esc(SYN.source) +
            (SYN.licence ? ' · ' + esc(SYN.licence) : '') +
            (SYN.built ? ' · built ' + esc(SYN.built) : '');
  } else {
    about = 'not fetched yet — about a megabyte, once';
  }
  const busy = job && job.running;
  const btns = busy ? ''
    : SYN.have
      ? '<button class="plain" data-dropsyn>remove</button>' +
        '<button class="plain" data-getsyn>rebuild</button>'
      : '<button class="go" data-getsyn>get it</button>';
  $('#syn').innerHTML = '<div class="drow' + (busy ? ' busy' : '') + '">' +
    '<div class="dnam">synonyms</div>' +
    '<div class="dabt">' + about + '</div>' +
    '<div class="dbtns">' + btns + '</div></div>';
}
drawSyn();

let synTimer = null;
function pollSyn() {
  api('syn', {}).then(j => {
    if (!j || !j.ok) return;
    SYN = j.syn;
    drawSyn(j.job);
    clearTimeout(synTimer);
    if (j.job && j.job.running) synTimer = setTimeout(pollSyn, 1200);
  }).catch(() => {});
}
pollSyn();

document.addEventListener('click', e => {
  if (e.target.closest && e.target.closest('[data-getsyn]')) {
    api('getsyn', {}).then(() => pollSyn());
    e.target.disabled = true;
    return;
  }
  if (e.target.closest && e.target.closest('[data-dropsyn]')) {
    if (!confirm('Remove the synonym table?\n\nThe file is deleted. You can '
                + 'get it again whenever you like.'))
      return;
    api('dropsyn', {}).then(() => pollSyn());
  }
});

/* ---- 2: the sentences somebody translated -------------------------------
   The same row and the same three buttons as a dictionary, with one more
   thing to say: a corpus is a PAIR of languages, so each row carries what it
   already has and a picker for what to add. */
function drawCorpora(jobs) {
  jobs = jobs || {};
  $('#corpora').innerHTML = CORPORA.map(d => {
    const job = jobs[d.code + '-' + (d.want || 'en')];
    const busy = Object.keys(jobs).some(k => k.startsWith(d.code + '-') && jobs[k].running);
    const running = Object.entries(jobs).find(
      ([k, v]) => k.startsWith(d.code + '-') && v.running);
    let about;
    if (running) {
      about = '<div>' + esc(running[1].say || 'working…') +
              '</div><div class="bar"><i></i></div>';
    } else {
      const bad = Object.entries(jobs).find(
        ([k, v]) => k.startsWith(d.code + '-') && v.error);
      if (bad) {
        about = '<span style="color:var(--danger)">' + esc(bad[1].error) + '</span>';
      } else if (d.have.length) {
        // REBUILD, like a dictionary and unlike a model.  Both are snapshots
        // of a source that moves -- Tatoeba gains sentences every week --
        // where a model is a pinned version that would come back identical.
        about = d.have.map(h =>
          '<div>glossed in <b>' + esc(h.gloss_name) + '</b> · ' +
          Number(h.pairs || 0).toLocaleString() + ' sentence pairs · ' +
          MB(h.size) + ' · ' + esc(h.source) +
          (h.licence ? ' · ' + esc(h.licence) : '') +
          (h.built ? ' · built ' + esc(h.built) : '') +
          ' <button class="plain" data-getc="' + d.code + '" data-gloss="' +
          h.gloss + '">rebuild</button>' +
          ' <button class="plain" data-dropc="' + d.code + '" data-gloss="' +
          h.gloss + '">remove</button></div>').join('');
      } else if (d.needs_dict) {
        about = 'its dictionary first — ' + esc(d.name) + ' is written ' +
                'without spaces between its words, so a corpus of it has to ' +
                'be cut into words before it can be indexed, and the ' +
                'dictionary\'s own word list is what cuts it';
      } else {
        about = 'nothing yet — a few megabytes for a small pair and a couple ' +
                'of hundred for a large one, and only where Tatoeba has ' +
                'this pair at all';
      }
    }
    const has = new Set(d.have.map(h => h.gloss));
    const opts = GLOSSES.filter(g => g.code !== d.code && !has.has(g.code))
      .map(g => '<option value="' + g.code + '"' +
                (g.code === 'en' ? ' selected' : '') + '>' +
                esc(g.name) + '</option>').join('');
    const btns = busy || !opts || d.needs_dict ? ''
      : '<select class="gsel" data-for="' + d.code + '">' + opts + '</select>' +
        '<button class="go" data-getc="' + d.code + '">get it</button>';
    return '<div class="drow' + (busy ? ' busy' : '') + '">' +
           '<div class="dnam">' + esc(d.name) +
           ' <span class="dnat" lang="' + d.code + '">' + esc(d.native) + '</span></div>' +
           '<div class="dabt">' + about + '</div>' +
           '<div class="dbtns">' + btns + '</div></div>';
  }).join('');
}
drawCorpora();

let corpTimer = null;
function pollCorpora() {
  api('corpora', {}).then(j => {
    if (!j || !j.ok) return;
    CORPORA = j.corpora;
    drawCorpora(j.jobs);
    const working = Object.values(j.jobs || {}).some(x => x.running);
    clearTimeout(corpTimer);
    if (working) corpTimer = setTimeout(pollCorpora, 1200);
  }).catch(() => {});
}
pollCorpora();

document.addEventListener('click', e => {
  const getc = e.target.closest && e.target.closest('[data-getc]');
  const dropc = e.target.closest && e.target.closest('[data-dropc]');
  if (getc) {
    const code = getc.dataset.getc;
    // a rebuild button carries the gloss it belongs to; the `get it` button
    // takes it from the picker beside it
    const sel = document.querySelector('.gsel[data-for="' + code + '"]');
    const gloss = getc.dataset.gloss || (sel ? sel.value : 'en');
    api('getcorpus', {code: code, gloss: gloss}).then(() => pollCorpora());
    getc.disabled = true;
    return;
  }
  if (dropc) {
    const code = dropc.dataset.dropc, gloss = dropc.dataset.gloss;
    const d = CORPORA.find(x => x.code === code) || {};
    if (!confirm('Remove the ' + (d.name || '') + ' sentences glossed in ' +
                 gloss + '?\n\nThe file is deleted. You can get it again ' +
                 'whenever you like.'))
      return;
    api('dropcorpus', {code: code, gloss: gloss}).then(() => pollCorpora());
  }
});

document.addEventListener('click', e => {
  const get = e.target.closest && e.target.closest('[data-get]');
  const drop = e.target.closest && e.target.closest('[data-drop]');
  if (get) {
    api('getdict', {code: get.dataset.get}).then(() => pollDicts());
    get.disabled = true;
    return;
  }
  if (drop) {
    const d = DICTS.find(x => x.code === drop.dataset.drop) || {};
    if (!confirm('Remove the ' + (d.name || '') + ' dictionary?\n\n' +
                 'The file is deleted. You can get it again whenever you like.'))
      return;
    api('dropdict', {code: drop.dataset.drop}).then(() => pollDicts());
  }
});
</script>
</body></html>
"""

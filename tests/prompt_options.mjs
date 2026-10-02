// SPDX-License-Identifier: GPL-3.0-or-later
import { chromium } from 'npm:playwright-core@1.52.0';
// Run: CHROME_BIN=/path/to/chrome PARSEH_PYTHON=/path/to/python3 deno run --allow-all tests/prompt_options.mjs
//      PROMPT_OPTIONS_SHOTS=<dir>   saves a screenshot of every place the options are drawn, at 1280 and 390 px,
//                                   in the light, dark and sepia themes
//      PROMPT_OPTIONS_ONLY=a,b      runs only those sections
//
// THE OPTIONS OF A PROMPT (lib/promptkit.py OPTIONS, drawn by lib/llmrow.js): the scheme of the transliteration -- the
// language's usual one, or IPA -- and, for a language whose record has `strip` (Persian, Arabic), the short vowels.
// On the REAL hub: serve.main() over a temporary tree holding copies of the fixture videos and books (Persian, Italian,
// Chinese), their readers built by this tex2html.py, no dictionary, no corpus and no model; nothing is stubbed but
// YouTube's iframe API.  Every action is the page's own: the panel and the sheet opened, a stretch picked, a select
// changed, the prompt copied and READ OFF THE CLIPBOARD; what a request carried is read off the request itself, and
// what was written off the file on disk.
//
//  a) the player's panel: Persian has the two options, in the language's own word ("transliteration") and the short
//     vowels; the defaults are the usual scheme and `no marks`, and the prompt's first line says so; IPA and "write
//     them" are carried by the request and end the line; the choice is remembered on this device (a reload, per
//     language / per surface); Italian has the scheme and no short vowels, Chinese neither (its record offers no IPA);
//     with the storage refused the panel works with the defaults.
//  b) the video's own record: a video that says IPA opens on IPA whatever the device remembers, choosing the usual
//     scheme for one prompt says that a video mixing two is harder to read and offers to make it the video's, which
//     writes video.json -- and the line above the prompt follows.
//  c) the book's sheet, the same (a reader built by this tex2html.py): the options, the request, the remembered choice,
//     the book's own record and "make it the book's setting" through the door the info sheet uses.
//  d) the add page: the options sit above the button that prepares the prompt, follow the language, are carried by
//     prepare, and a prompt prepared for other choices is forgotten.
//  e) at 1280 and 390 px, in the light, dark and sepia themes, the options are inside the window and wrap, and nothing is
//     wider than its box.
//  f) last: no page threw, logged an error or had a request refused; the hub printed no traceback; the owner's config/,
//     books/, youtube/videos/ and the fixtures are as they were.
const root = await Deno.realPath(new URL('..', import.meta.url));
Deno.chdir(root);
const PY = Deno.env.get('PARSEH_PYTHON') || 'python3';
const TMP = await Deno.makeTempDir({prefix: 'parseh-prompt-options-'});
const SHOTS = Deno.env.get('PROMPT_OPTIONS_SHOTS') || '';
const ONLY = (Deno.env.get('PROMPT_OPTIONS_ONLY') || '').split(',').filter(Boolean);
if (SHOTS) await Deno.mkdir(SHOTS, {recursive: true});
const td = new TextDecoder();
let passed = 0;
const assert = (v, m) => { if (!v) throw Error('FAIL: ' + m); passed++; console.log('  ok', m); };
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const eq = (got, want, m) => assert(same(got, want),
  m + (same(got, want) ? '' : ': got ' + JSON.stringify(got) + ' want ' + JSON.stringify(want)));
const sleep = ms => new Promise(r => setTimeout(r, ms));
async function until(fn, what, ms = 15000) {
  const t = Date.now();
  for (;;) {
    const v = await fn();
    if (v) return v;
    if (Date.now() - t > ms) throw Error('FAIL: timed out: ' + what);
    await sleep(60);
  }
}
async function run(cmd, args) {
  const o = await new Deno.Command(cmd, {args, cwd: root, stdout: 'piped', stderr: 'piped'}).output();
  return {code: o.code, out: td.decode(o.stdout), err: td.decode(o.stderr)};
}
async function py(code, ...args) {
  const r = await run(PY, ['-c', code, ...args]);
  if (r.code) throw Error(r.err || r.out);
  return r.out;
}
function freePort() {
  const l = Deno.listen({hostname: '127.0.0.1', port: 0});
  const p = l.addr.port;
  l.close();
  return p;
}
function drain(stream, sink) {
  (async () => {
    const r = stream.pipeThrough(new TextDecoderStream()).getReader();
    for (;;) { const {value, done} = await r.read(); if (done) break; sink.push(value); }
  })();
}

/* ---------------- the toolbox ---------------- */
// Copies of the fixtures under <tmp>/root, lib/ and youtube/lib/ linked into the tree, the books' readers built by this
// tex2html.py (tests/mobile_harness.built_reader).  The fixtures themselves are only ever read.
const BUILD = String.raw`
import json, os, shutil, sys
from pathlib import Path
REPO = Path(os.getcwd())
sys.path[:0] = ['tests', 'lib', 'youtube/lib']
import mobile_harness
tmp = Path(sys.argv[1])
root = tmp / 'root'
for d in (root / 'youtube' / 'videos', tmp / 'library', tmp / 'exercises', tmp / 'anki', tmp / 'tray', tmp / 'config',
          tmp / 'nodict', tmp / 'nocorpus', tmp / 'nomt'):
    d.mkdir(parents=True, exist_ok=True)
os.symlink(str(REPO / 'lib'), str(root / 'lib'))
os.symlink(str(REPO / 'youtube' / 'lib'), str(root / 'youtube' / 'lib'))
out = {}
import texwrite
# LINES OF REAL IPA, with the letters a transliteration's face often lacks (ʃ ʒ ɒ ɔ ɪ ʊ ɑ ʌ ɡ ɾ ʔ ʎ ɲ) and the length and
# stress marks: written over the first glossed chunks of the Persian and the Italian video and book, so that every page
# that draws a transliteration draws these
IPA = {'fa': ['sæˈlɒːm', 'tʃeˈtoɾi', 'ɡæɾm ʃoːd', 'ˈʒɒːle ʔɒːn', 'ɪn ʊ ɔ ʌ ɑː'],
       'it': ['ˈkwanto ˈkɔstano', 'le ˈmele ˈɔddʒi', 'ˈbwɔna dʒorˈnata', 'ˈfaʎʎa ˈɲɔkki', 'ˈpeʃe ʒ']}
for folder, vid, key in (('persian', 'fA6bK2mQ8sT', 'fa'), ('italian', 'kL9mN1oP3qR', 'it'), ('chinese', 'zH8cN2hA6nZ', 'zh')):
    vd = root / 'youtube' / 'videos' / folder / vid
    shutil.copytree(str(REPO / 'tests/fixtures/videos' / folder / vid), str(vd))
    out['v' + key] = vid
    if key in IPA:
        ann = json.loads((vd / 'annotations.json').read_text(encoding='utf-8'))
        n = 0
        for sg in ann['segments']:
            for ch in sg.get('chunks') or []:
                if ch.get('tr') and n < len(IPA[key]):
                    ch['tr'] = IPA[key][n]
                    n += 1
        (vd / 'annotations.json').write_text(json.dumps(ann, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
for folder, slug, key in (('persian', 'mini-fa', 'fa'), ('italian', 'mini-it', 'it'), ('chinese', 'mini-zh', 'zh')):
    d = root / 'books' / folder / slug
    shutil.copytree(str(REPO / 'tests/fixtures/books' / folder / slug), str(d),
                    ignore=shutil.ignore_patterns('reader', '.reader-key'))
    if key in IPA:
        recs = [r for r in texwrite.read_chunks(str(d / 'ch1.tex')) if r['macro'] != 'chp' and r['tr'].strip()]
        for r, line in zip(recs, IPA[key]):
            texwrite.edit_chunk(str(d / 'ch1.tex'), r['index'], {'tr': line})
    mobile_harness.built_reader(d)
    out['b' + key] = '/books/%s/%s' % (folder, slug)
    out['d' + key] = str(d)
out['transcript'] = (REPO / 'tests/fixtures/videos/persian/fA6bK2mQ8sT/transcript.txt').read_text(encoding='utf-8')
print(json.dumps(out, ensure_ascii=False))
`;
const SERVE = String.raw`
import sys
from pathlib import Path
sys.path[:0] = ['markdown/exlex', 'markdown/app', 'youtube/lib', 'lib', '.']
tmp, port = Path(sys.argv[1]), sys.argv[2]
import prefs, network, offline
prefs.STORE = str(tmp / 'config' / 'prefs.json')
network.STORE = str(tmp / 'config' / 'network.json')
import latexthemes, latexdraw, texpackages
latexthemes.STORE = str(tmp / 'config' / 'latex.json')
import prompts
prompts.STORE = str(tmp / 'config' / 'prompts.json')
latexdraw.DRAWN = str(tmp / 'latex-drawn')
texpackages.TREE = str(tmp / 'texmf')
offline.DIGESTS = str(tmp / 'config' / 'digests.json')
offline.WHERES = str(tmp / 'config' / 'wheres.json')
import lookup, corpus, getmt
lookup.DICT_DIR = str(tmp / 'nodict')
corpus.CORPUS_DIR = str(tmp / 'nocorpus')
getmt.MT_DIR = str(tmp / 'nomt')
getmt.ENGINE_DIR = str(tmp / 'nomt' / 'engine')
import clips, decks, store
clips.set_dir(tmp / 'tray')
import serve, ytpages
for st in {store, serve.studio.store}:
    st.LIB = tmp / 'library'
    st.set_clips_dir(tmp / 'tray')
decks.set_dir(tmp / 'exercises')
decks.set_clips_dir(tmp / 'tray')
serve.ROOT = str(tmp / 'root')
serve._AtRoot.directory = str(tmp / 'root')
ytpages.VIDEOS = str(tmp / 'root' / 'youtube' / 'videos')
ytpages.oembed = lambda vid: {}
serve.ANKI = ytpages.ANKI = str(tmp / 'anki')
ytpages.INBOX = str(tmp / 'anki' / 'inbox')
sys.argv = ['serve.py', '--http', '--local', port]
serve.main()
`;
// the owner's own files, which nothing here may touch
const OWN = String.raw`
import hashlib, json, os, sys
tmp = sys.argv[1]
out, leaks = {}, []
for top in ('config', 'books', 'youtube/videos', 'tests/fixtures/videos', 'tests/fixtures/books'):
    for d, _, files in os.walk(top):
        if '/reader' in d.replace(os.sep, '/') + '/' and top == 'tests/fixtures/books':
            continue
        for f in files:
            p = os.path.join(d, f)
            if p.replace(os.sep, '/') in ('config/digests.json', 'config/wheres.json'):
                try:
                    text = open(p, encoding='utf-8').read()
                except OSError:
                    continue
                if tmp in text:
                    leaks.append(p)
                continue
            out[p] = hashlib.md5(open(p, 'rb').read()).hexdigest()
print(json.dumps({'digests': out, 'leaks': leaks}, sort_keys=True))
`;
// what a record says of its scheme, read off the file; and set, as a hand would
const RECORD = String.raw`
import json, sys
path, scheme = sys.argv[1], sys.argv[2]
doc = json.load(open(path, encoding='utf-8'))
if scheme == '?':
    print(json.dumps(doc.get('translit')))
else:
    if scheme: doc['translit'] = scheme
    else: doc.pop('translit', None)
    json.dump(doc, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print('null')
`;
const ownBefore = JSON.parse(await py(OWN, TMP));
const FAKE_YT = `window.YT = {Player: function (el, o) {
  var t = 0, going = false, self = this;
  window.__yt = {seeks: []};
  this.getCurrentTime = function () { return t; };
  this.getDuration = function () { return 40; };
  this.seekTo = function (s) { t = +s || 0; window.__yt.seeks.push(t); };
  this.playVideo = function () { going = true; };
  this.pauseVideo = function () { going = false; };
  this.getPlayerState = function () { return going ? 1 : 2; };
  this.getPlaybackRate = function () { return 1; };
  this.setPlaybackRate = function () {};
  this.mute = function () {}; this.unMute = function () {};
  this.isMuted = function () { return false; };
  setTimeout(function () { if (o.events && o.events.onReady) o.events.onReady({target: self}); }, 20);
}};
if (window.onYouTubeIframeAPIReady) window.onYouTubeIframeAPIReady();`;

const errors = [];
let hub = null, browser = null;
const log = [];
try {
  const T = JSON.parse((await py(BUILD, TMP)).trim().split('\n').pop());
  const port = freePort();
  hub = new Deno.Command(PY, {args: ['-c', SERVE, TMP, String(port)], cwd: root, stdout: 'piped', stderr: 'piped'}).spawn();
  drain(hub.stdout, log); drain(hub.stderr, log);
  const B = `http://127.0.0.1:${port}`;
  {
    const t = Date.now();
    for (;;) {
      try { const r = await fetch(B + '/clips/api/status'); await r.body?.cancel(); if (r.ok) break; } catch (_) {}
      if (Date.now() - t > 60000) throw Error('the hub did not start:\n' + log.join(''));
      await sleep(250);
    }
  }
  browser = await chromium.launch({executablePath: Deno.env.get('CHROME_BIN'), headless: true});
  const context = await browser.newContext({viewport: {width: 1280, height: 900}});
  await context.grantPermissions(['clipboard-read', 'clipboard-write'], {origin: B});
  await context.route(/^https?:\/\/(?!127\.0\.0\.1[:/])/, route => {
    if (route.request().url() === 'https://www.youtube.com/iframe_api')
      return route.fulfill({contentType: 'text/javascript', body: FAKE_YT});
    return route.abort();
  });
  const record = (path, scheme) => py(RECORD, path, scheme).then(s => JSON.parse(s.trim()));
  const videoJson = vid => `${TMP}/root/youtube/videos/${vid === T.vfa ? 'persian' : vid === T.vit ? 'italian' : 'chinese'}/${vid}/video.json`;
  const bookJson = key => `${T['d' + key]}/book.json`;

  /* ---------------- helpers over a page ---------------- */
  const optional = (status, method, path) => status === 404 && method === 'GET' &&
    (/^\/mt\/[^/]+\/meta\.json$/.test(path) || /\/waveform\.json$/.test(path) || path === '/favicon.ico');
  const posted = [];                       // every region/prepare request the pages sent: {path, body}
  async function open(url, name, {refuseStorage = false} = {}) {
    const page = await context.newPage();
    if (refuseStorage) await page.addInitScript(() => {
      const boom = () => { throw new Error('storage refused'); };
      Object.defineProperty(window, 'localStorage', {get: boom});
    });
    page.on('pageerror', e => errors.push(name + ' pageerror: ' + e.message));
    page.on('response', r => {
      const u = new URL(r.url());
      if (u.host !== `127.0.0.1:${port}` || r.status() < 400) return;
      if (!optional(r.status(), r.request().method(), u.pathname)) errors.push(name + ' ' + r.status() + ' ' + r.request().method() + ' ' + u.pathname);
    });
    page.on('console', m => {
      if (m.type() !== 'error') return;
      const at = (m.location() || {}).url || '';
      if (/^Failed to load resource/.test(m.text()) && (at.startsWith(B) || !at.startsWith('http://127.0.0.1'))) return;
      errors.push(name + ' console: ' + m.text() + (at ? ' (' + at + ')' : ''));
    });
    page.on('request', r => {
      const u = new URL(r.url());
      if (r.method() === 'POST' && /\/(__region\/prompt|api\/region\/prompt|api\/prepare)$/.test(u.pathname))
        posted.push({path: u.pathname, body: JSON.parse(r.postData() || '{}')});
    });
    await page.goto(B + url);
    return page;
  }
  const clip = page => page.evaluate(() => navigator.clipboard.readText());
  const setClip = (page, s) => page.evaluate(s => navigator.clipboard.writeText(s), s);
  const store = (page, k) => page.evaluate(k => { try { return localStorage.getItem(k); } catch (e) { return 'refused'; } }, k);
  // what the row's options say, as a person reads them: [{name, label, value, choices}]
  const optionsOf = (page, scope) => page.evaluate(scope => [...document.querySelectorAll(scope + ' .llmrow-opt')].map(l => ({
    name: l.dataset.option, label: l.firstChild.textContent.trim(), value: l.querySelector('select').value,
    choices: [...l.querySelectorAll('option')].map(o => o.textContent), shown: l.getClientRects().length > 0})), scope);
  const choose = (page, scope, name, value) => page.selectOption(`${scope} .llmrow-opt[data-option="${name}"] select`, value);
  const noteOf = (page, scope) => page.evaluate(scope => {
    const n = document.querySelector(scope + ' .llmrow-optnote');
    return n && !n.hidden && n.getClientRects().length ? {text: n.firstChild.textContent, button: (n.querySelector('button') || {}).textContent || ''} : null;
  }, scope);
  const FIRST = /^Parseh prompt · (video|book)-region · (\w+) → en · a0\.\d+\.\d+/;
  // the prompt the row copies: its first line
  async function copyFirstLine(page, scope) {
    await setClip(page, 'SENTINEL — not written by the page');
    await page.click(scope + ' .llmrow-copy');
    await until(async () => (await clip(page)) !== 'SENTINEL — not written by the page', 'the prompt on the clipboard');
    return (await clip(page)).split('\n')[0];
  }
  const THEMES = [['light', 1280, 900], ['dark', 1280, 900], ['light', 390, 844], ['dark', 390, 844], ['sepia', 390, 844]];
  async function look(page, name, scope) {
    for (const [theme, w, h] of THEMES) {
      await page.setViewportSize({width: w, height: h});
      await page.evaluate(t => { document.documentElement.setAttribute('data-theme', t); if (document.body) document.body.setAttribute('data-theme', t); }, theme);
      await sleep(150);
      const r = await page.evaluate(scope => {
        const o = document.querySelector(scope + ' .llmrow-opts, ' + scope + '.llmrow-opts');
        o.scrollIntoView({block: 'center'});
        const rr = o.getBoundingClientRect();
        const sel = [...o.querySelectorAll('select')];
        const out = sel.filter(s => { const b = s.getBoundingClientRect(); return b.left < -0.5 || b.right > innerWidth + 0.5; }).length;
        const hit = sel.every(s => { const b = s.getBoundingClientRect(); const e = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2); return e === s || s.contains(e); });
        return {left: rr.left, right: rr.right, width: innerWidth, out, hit, selects: sel.length, page: document.documentElement.scrollWidth};
      }, scope);
      assert(r.left >= 0 && r.right <= r.width + 0.5 && r.out === 0 && r.hit && r.selects > 0 && r.page <= r.width + 1,
             `${name}: the options are inside the window, on top, and make the page no wider (${theme}, ${w} px)`);
      if (SHOTS) await page.screenshot({path: `${SHOTS}/${name}-${theme}-${w}.png`});
    }
    await page.setViewportSize({width: 1280, height: 900});
    await page.evaluate(() => { document.documentElement.setAttribute('data-theme', 'light'); if (document.body) document.body.setAttribute('data-theme', 'light'); });
  }
  const section = async (key, title, fn) => {
    if (ONLY.length && !ONLY.includes(key)) return;
    console.log(`\n${key}) ${title}`);
    await fn();
  };

  /* ---------------- the player ---------------- */
  const PANEL = '#rgrow';
  async function player(vid, name, more) {
    const page = await open(`/youtube/v/${vid}/`, name, more);
    await page.waitForSelector('#segs .seg .fa .w');
    await page.waitForFunction(() => window.__yt && document.querySelector('#novid').hidden);
    await page.click('#rgn');
    await page.waitForFunction(() => !document.querySelector('#rgpanel').hidden);
    return page;
  }
  async function pickCaption(page, i) {
    await page.click(`#segs .seg[data-i="${i}"] .lab`);
    await page.waitForFunction(() => document.querySelector('#rgfrom').classList.contains('set'));
  }
  await section('a', 'the player: the options, the request, what is remembered', async () => {
    let page = await player(T.vfa, 'player fa');
    await until(async () => (await optionsOf(page, PANEL)).length === 2, 'the options drawn');
    eq((await optionsOf(page, PANEL)).map(o => [o.name, o.label, o.value, o.choices]),
       [['translit', 'transliteration:', 'classic', ['usual scheme', 'IPA']],
        ['marks', 'short vowels:', 'nomarks', ['as they are', 'write them']]],
       'Persian: the two options, the first in the language\'s own word, both on their defaults');
    await pickCaption(page, 1);
    let first = await copyFirstLine(page, PANEL);
    assert(/^Parseh prompt · video-region · fa → en · a0\.\d+\.\d+ · no marks$/.test(first), 'the usual scheme and the text as it is: the line says only the second (' + first + ')');
    let body = posted.filter(p => /region\/prompt/.test(p.path)).pop().body;
    eq([body.translit, body.marks], ['classic', 'nomarks'], 'the request carries both, on their defaults');
    await choose(page, PANEL, 'translit', 'ipa');
    first = await copyFirstLine(page, PANEL);
    assert(/ · IPA · no marks$/.test(first), 'IPA: the prompt\'s first line ends "· IPA · no marks" (' + first + ')');
    body = posted.filter(p => /region\/prompt/.test(p.path)).pop().body;
    eq([body.translit, body.marks], ['ipa', 'nomarks'], 'and the request carries it');
    assert(/the IPA of the chunk/.test(await clip(page)), 'the prompt asks for IPA in the place where it asks for the transliteration');
    await choose(page, PANEL, 'marks', 'marks');
    first = await copyFirstLine(page, PANEL);
    assert(/ · IPA · marks$/.test(first), '"write them": the line ends "· IPA · marks" (' + first + ')');
    eq([await store(page, 'parseh_llmrow_translit_fa'), await store(page, 'parseh_llmrow_marks_video-region')], ['ipa', 'marks'],
       'both choices are kept on this device: the scheme for the language, the short vowels for the surface');
    await look(page, 'player-fa-options', PANEL);
    await page.reload();
    await page.waitForSelector('#segs .seg .fa .w');
    await page.waitForFunction(() => window.__yt && document.querySelector('#novid').hidden);
    await page.click('#rgn');
    await until(async () => (await optionsOf(page, PANEL)).length === 2, 'the options drawn after a reload');
    eq((await optionsOf(page, PANEL)).map(o => o.value), ['ipa', 'marks'], 'after a reload the choices are the ones kept');
    await pickCaption(page, 1);
    first = await copyFirstLine(page, PANEL);
    assert(/ · IPA · marks$/.test(first), 'and the first prompt of the page is already made that way (' + first + ')');
    await page.close();

    page = await player(T.vit, 'player it');
    await until(async () => (await optionsOf(page, PANEL)).length > 0, 'the options drawn');
    eq((await optionsOf(page, PANEL)).map(o => [o.name, o.label]), [['translit', 'pronunciation:']],
       'Italian: the scheme, called pronunciation, and no short vowels');
    await choose(page, PANEL, 'translit', 'ipa');
    await pickCaption(page, 1);
    first = await copyFirstLine(page, PANEL);
    assert(/ · IPA$/.test(first) && !/marks/.test(first), 'its prompt ends "· IPA" and says nothing of short vowels (' + first + ')');
    body = posted.filter(p => /region\/prompt/.test(p.path)).pop().body;
    eq(Object.keys(body).filter(k => k === 'marks'), [], 'the request does not carry the short vowels either');
    await look(page, 'player-it-options', PANEL);
    await page.close();

    page = await player(T.vzh, 'player zh');
    await sleep(600);
    eq([await optionsOf(page, PANEL), await page.evaluate(sel => document.querySelector(sel + ' .llmrow-opts').hidden, PANEL)],
       [[], true], 'Chinese: no option at all, its record offers no IPA and it has no short vowels');
    await pickCaption(page, 1);
    first = await copyFirstLine(page, PANEL);
    assert(!/IPA|marks/.test(first), 'and its prompt says neither (' + first + ')');
    await page.close();

    // the storage refused: the panel works, on the defaults
    page = await player(T.vfa, 'player fa, storage refused', {refuseStorage: true});
    await until(async () => (await optionsOf(page, PANEL)).length === 2, 'the options drawn with the storage refused');
    eq((await optionsOf(page, PANEL)).map(o => o.value), ['classic', 'nomarks'], 'with the storage refused: the defaults');
    await choose(page, PANEL, 'translit', 'ipa');
    await pickCaption(page, 1);
    first = await copyFirstLine(page, PANEL);
    assert(/ · IPA · no marks$/.test(first), 'and a choice still works for the page (' + first + ')');
    await page.close();
  });

  await section('b', 'the video\'s own record of the scheme', async () => {
    await record(videoJson(T.vfa), 'ipa');
    let page = await player(T.vfa, 'player fa, a video that says IPA');
    await page.evaluate(() => { try { localStorage.clear(); } catch (e) {} });
    await page.reload();
    await page.waitForSelector('#segs .seg .fa .w');
    await page.waitForFunction(() => window.__yt && document.querySelector('#novid').hidden);
    await page.click('#rgn');
    await until(async () => (await optionsOf(page, PANEL)).length === 2, 'the options drawn');
    eq((await optionsOf(page, PANEL)).map(o => o.value), ['ipa', 'nomarks'], 'a video that says IPA opens on IPA, with nothing remembered on this device');
    eq(await noteOf(page, PANEL), null, 'and has nothing to say about it');
    await pickCaption(page, 1);
    let first = await copyFirstLine(page, PANEL);
    assert(/ · IPA · no marks$/.test(first), 'its prompt asks for IPA (' + first + ')');
    await choose(page, PANEL, 'translit', 'classic');
    const note = await noteOf(page, PANEL);
    assert(note && /^this video's transliteration is IPA and this prompt asks for usual scheme: a video that mixes the two is harder to read\.$/.test(note.text) &&
           note.button === "make usual scheme the video's setting", 'choosing the usual scheme for one prompt says so, and offers to make it the video\'s (' + JSON.stringify(note) + ')');
    first = await copyFirstLine(page, PANEL);
    assert(!/ · IPA/.test(first), 'the prompt of that choice is in the usual scheme (' + first + ')');
    eq(await store(page, 'parseh_llmrow_translit_fa'), null, 'and a choice against the record is for this prompt: nothing is remembered');
    await look(page, 'player-fa-options-note', PANEL);
    await page.click(PANEL + ' .llmrow-optnote button');
    await until(async () => (await noteOf(page, PANEL)) === null, 'the note gone');
    eq(await record(videoJson(T.vfa), '?'), null, 'making it the video\'s writes video.json: the usual way is no key');
    first = await copyFirstLine(page, PANEL);
    assert(!/ · IPA/.test(first), 'and the next prompt is in the usual scheme (' + first + ')');
    await page.close();
  });

  /* ---------------- the book's reader ---------------- */
  const SHEET = '#rgrow';
  async function reader(key, name, more) {
    const page = await open(T['b' + key] + '/reader/', name, more);
    await page.waitForSelector('#rgn');
    await page.click('#rgn');
    await page.waitForFunction(() => rgShown);
    return page;
  }
  async function pickFirstSentence(page) {
    const ch = page.locator('#rgbox .oltree > li.ol-ch').first();
    if ((await ch.getAttribute('aria-expanded')) === 'false') await ch.locator(':scope > .olr > .oltw').click();
    for (let guard = 0; guard < 60; guard++) {
      const shut = ch.locator('li[aria-expanded="false"]');
      if (!(await shut.count())) break;
      await shut.first().locator(':scope > .olr > .oltw').click();
    }
    await ch.locator('li.ol-s').first().locator(':scope > .olr').click();
    await page.waitForFunction(() => rgPicker && rgPicker.get());
  }
  await section('c', 'the book\'s sheet: the options, the request, the record', async () => {
    await page_clear();
    let page = await reader('fa', 'reader fa');
    await until(async () => (await optionsOf(page, SHEET)).length === 2, 'the options drawn');
    eq((await optionsOf(page, SHEET)).map(o => [o.name, o.label, o.value]),
       [['translit', 'transliteration:', 'classic'], ['marks', 'short vowels:', 'nomarks']], 'Persian: the two options on their defaults');
    await pickFirstSentence(page);
    let first = await copyFirstLine(page, SHEET);
    assert(/^Parseh prompt · book-region · fa → en · a0\.\d+\.\d+ · no marks$/.test(first), 'the first line says the short vowels and not the scheme (' + first + ')');
    await choose(page, SHEET, 'translit', 'ipa');
    await choose(page, SHEET, 'marks', 'marks');
    first = await copyFirstLine(page, SHEET);
    assert(/ · IPA · marks$/.test(first), 'IPA and "write them": the line ends "· IPA · marks" (' + first + ')');
    const body = posted.filter(p => /__region\/prompt/.test(p.path)).pop().body;
    eq([body.translit, body.marks], ['ipa', 'marks'], 'and the request carries both');
    await look(page, 'reader-fa-options', SHEET);
    await page.reload();
    await page.waitForSelector('#rgn');
    await page.click('#rgn');
    await until(async () => (await optionsOf(page, SHEET)).length === 2, 'the options after a reload');
    eq((await optionsOf(page, SHEET)).map(o => o.value), ['ipa', 'marks'], 'a reload keeps the choices');
    await page.close();

    // the book's own record
    await record(bookJson('fa'), 'ipa');
    await page_clear();
    page = await reader('fa', 'reader fa, a book that says IPA');
    await until(async () => (await optionsOf(page, SHEET)).length === 2, 'the options drawn');
    eq((await optionsOf(page, SHEET)).map(o => o.value), ['ipa', 'nomarks'], 'a book that says IPA opens on IPA');
    await choose(page, SHEET, 'translit', 'classic');
    const note = await noteOf(page, SHEET);
    assert(note && /^this book's transliteration is IPA and this prompt asks for usual scheme/.test(note.text) && note.button === "make usual scheme the book's setting",
           'choosing against it says so and offers to make it the book\'s (' + JSON.stringify(note) + ')');
    await page.click(SHEET + ' .llmrow-optnote button');
    await until(async () => (await noteOf(page, SHEET)) === null, 'the note gone');
    eq(await record(bookJson('fa'), '?'), null, 'the book\'s record lost the key: the usual way is no key');
    await page.close();

    page = await reader('it', 'reader it');
    await until(async () => (await optionsOf(page, SHEET)).length > 0, 'the options drawn');
    eq((await optionsOf(page, SHEET)).map(o => o.name), ['translit'], 'Italian: the scheme, and no short vowels');
    await page.close();
    page = await reader('zh', 'reader zh');
    await sleep(600);
    eq(await optionsOf(page, SHEET), [], 'Chinese: none');
    await page.close();
  });
  async function page_clear() {
    const p = await context.newPage();
    await p.goto(B + '/clips/api/status');
    await p.evaluate(() => { try { localStorage.clear(); } catch (e) {} });
    await p.close();
  }

  /* ---------------- the add page ---------------- */
  await section('d', 'the add page: above the button that prepares the prompt', async () => {
    await page_clear();
    const page = await open('/youtube/add/', 'add');
    await page.waitForSelector('#prepare');
    await page.selectOption('#lang', 'fa');
    await until(async () => (await optionsOf(page, '#popts')).length === 2, 'the options drawn for Persian');
    eq((await optionsOf(page, '#popts')).map(o => [o.name, o.label, o.value, o.shown]),
       [['translit', 'transliteration:', 'classic', true], ['marks', 'short vowels:', 'nomarks', true]],
       'Persian: both, visible before any prompt is prepared');
    await page.selectOption('#lang', 'it');
    await until(async () => (await optionsOf(page, '#popts')).length === 1, 'the options for Italian');
    eq((await optionsOf(page, '#popts')).map(o => o.name), ['translit'], 'Italian: the scheme only');
    await page.selectOption('#lang', 'zh');
    await until(async () => (await optionsOf(page, '#popts')).length === 0, 'the options for Chinese');
    eq(await optionsOf(page, '#popts'), [], 'Chinese: none');
    await page.selectOption('#lang', 'fa');
    await until(async () => (await optionsOf(page, '#popts')).length === 2, 'the options back');
    await choose(page, '#popts', 'translit', 'ipa');
    await page.click('.path[data-src="yt"]');
    await page.click('.path[data-by="llm"]');
    await page.fill('#url', 'https://www.youtube.com/watch?v=' + T.vfa);
    await page.fill('#transcript', T.transcript);
    await page.click('#prepare');
    await until(() => page.evaluate(() => document.querySelector('#prompt').value.length > 1000), 'the prompt prepared');
    const prompt = await page.evaluate(() => document.querySelector('#prompt').value);
    assert(/^Parseh prompt · video-new · fa → en · a0\.\d+\.\d+ · IPA · no marks\n/.test(prompt), 'the prepared prompt asks for IPA (' + prompt.split('\n')[0] + ')');
    const body = posted.filter(p => /api\/prepare$/.test(p.path)).pop().body;
    eq([body.translit, body.marks], ['ipa', 'nomarks'], 'prepare carried both');
    await look(page, 'add-fa-options', '#popts');
    await choose(page, '#popts', 'marks', 'marks');
    await until(() => page.evaluate(() => document.querySelector('#prow').hidden), 'the prepared prompt forgotten');
    assert(true, 'choosing another setting forgets the prompt prepared for the first');
    await page.click('#prepare');
    await until(() => page.evaluate(() => document.querySelector('#prompt').value.length > 1000), 'the prompt prepared again');
    assert(/ · IPA · marks\n/.test(await page.evaluate(() => document.querySelector('#prompt').value)), 'and the next one says "· IPA · marks"');
    await page.close();
  });

  /* ---------------- IPA on the page ---------------- */
  // THE LETTERS ARE THERE, and the page is no wider for them: what the tree holds (IPA written over the first glossed
  // chunks of the Persian and the Italian book and video, by BUILD) is read off the element that draws it and compared
  // with what was written; the element is looked at in the three themes at 1280 and 390 px (screenshots when asked).
  // Whether a missing letter prints as a box is the face's, which a headless browser cannot say for another computer's
  // fonts: the PDF is held by tests/test_ipa_book_pdf.py, and the screenshots are for a person to look at.
  async function themed(page, name, locator) {
    for (const [theme, w, h] of THEMES) {
      await page.setViewportSize({width: w, height: h});
      await page.evaluate(t => { document.documentElement.setAttribute('data-theme', t); if (document.body) document.body.setAttribute('data-theme', t); }, theme);
      await sleep(150);
      const box = await locator.evaluate(el => { el.scrollIntoView({block: 'center'}); const r = el.getBoundingClientRect(); return {l: r.left, r: r.right, w: innerWidth, page: document.documentElement.scrollWidth}; });
      assert(box.l >= -0.5 && box.r <= box.w + 0.5 && box.page <= box.w + 1, `${name}: inside the window and the page no wider (${theme}, ${w} px)`);
      if (SHOTS) await page.screenshot({path: `${SHOTS}/${name}-${theme}-${w}.png`});
    }
    await page.setViewportSize({width: 1280, height: 900});
    await page.evaluate(() => { document.documentElement.setAttribute('data-theme', 'light'); if (document.body) document.body.setAttribute('data-theme', 'light'); });
  }
  const WROTE = {fa: ['sæˈlɒːm', 'tʃeˈtoɾi', 'ɡæɾm ʃoːd'], it: ['ˈkwanto ˈkɔstano', 'le ˈmele ˈɔddʒi', 'ˈbwɔna dʒorˈnata']};
  await section('g', 'IPA on the reader, the player and the studio', async () => {
    await page_clear();
    for (const key of ['fa', 'it']) {
      const page = await open(T['b' + key] + '/reader/', `reader ${key} IPA`);
      await page.waitForSelector('.pass.p2 .row .gl .tr');
      const said = await page.evaluate(() => [...document.querySelectorAll('.pass.p2 .row .gl .tr')].map(e => e.textContent.trim()).filter(Boolean));
      assert(WROTE[key].every(w => said.includes(w)), `${key} reader: the IPA written into the book is on the page, letter for letter (${said.slice(0, 3).join(' | ')})`);
      await themed(page, `reader-${key}-ipa`, page.locator('.pass.p2 .row .gl .tr', {hasText: WROTE[key][1]}).first());
      await page.close();
    }
    for (const key of ['fa', 'it']) {
      const page = await open(`/youtube/v/${T['v' + key]}/`, `player ${key} IPA`);
      await page.waitForSelector('#segs .seg .fa .w');
      await page.waitForFunction(() => window.__yt && document.querySelector('#novid').hidden);
      await page.hover('#segs .seg[data-i="0"] .fa .w[data-j="0"]');
      await page.waitForFunction(() => { const c = document.querySelector('#cloud'); return !c.hidden && c.querySelector('.tr'); });
      const tr = await page.evaluate(() => document.querySelector('#cloud .tr').textContent.trim());
      assert(IPA_OF[key].includes(tr), `${key} player: the cloud of a phrase says its IPA as written (${tr})`);
      await themed(page, `player-${key}-ipa-cloud`, page.locator('#cloud'));
      await page.close();
    }
    // the studio: a heading's transliteration is drawn on the sheet, and a mark's is carried for the reader to point at
    const page = await open('/studio/', 'studio IPA');
    const made = await page.evaluate(async () => {
      const md = '---\ntitle: Sounds\nlang: fa\ntarget: fa\n---\n\n## تند | tɒnd | an adjective | = *sharp, fast*\n\nThe word [تند]{translit:tɒnd} is said ˈtɒnd, and [آرام]{translit:ʔɒːˈɾɒːm} has a long vowel and a stress mark: ʃ ʒ ɒ ɔ ɪ ʊ ɑ ʌ ɡ ɾ ʔ.\n';
      const r = await fetch('/studio/api/docs', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({markdown: md})});
      return r.json();
    });
    assert(made && made.meta && made.meta.id, 'the studio made the document');
    await page.goto(B + '/studio/doc/' + made.meta.id);
    await page.waitForSelector('.voce, .entry, h2');
    const sheet = await page.evaluate(() => document.body.textContent);
    assert(/tɒnd/.test(sheet), 'the heading\'s IPA is on the sheet');
    assert(await page.evaluate(() => document.documentElement.innerHTML.includes('data-translit="tɒnd"')), 'and the mark carries it for the reader to point at');
    await themed(page, 'studio-ipa-sheet', page.locator('body').first());
    await page.close();
  });
  const IPA_OF = {fa: ['sæˈlɒːm', 'tʃeˈtoɾi', 'ɡæɾm ʃoːd', 'ˈʒɒːle ʔɒːn', 'ɪn ʊ ɔ ʌ ɑː'], it: ['ˈkwanto ˈkɔstano', 'le ˈmele ˈɔddʒi', 'ˈbwɔna dʒorˈnata', 'ˈfaʎʎa ˈɲɔkki', 'ˈpeʃe ʒ']};

  /* ---------------- last ---------------- */
  await section('f', 'what the pages and the hub said', async () => {
    eq(errors, [], 'no page threw, logged an error or had a request refused');
    const said = log.join('');
    assert(!/Traceback/.test(said), 'no traceback in the hub\'s log' + (/Traceback/.test(said) ? ':\n' + said.slice(said.indexOf('Traceback')).slice(0, 600) : ''));
    const ownAfter = JSON.parse(await py(OWN, TMP));
    eq(ownAfter.leaks, [], 'nothing of this run\'s tree was remembered in the owner\'s config/digests.json or wheres.json');
    eq(ownAfter.digests, ownBefore.digests, 'the owner\'s config/, books/, youtube/videos/ and the fixtures are untouched');
  });
  console.log(`\nprompt_options: ${passed} checks passed`);
} catch (e) {
  console.log(String(e && e.stack || e));
  console.log('\nhub log:\n' + log.join('').slice(-1500));
  console.log(`\nprompt_options: ${passed} checks passed, then a failure`);
  Deno.exitCode = 1;
} finally {
  if (browser) await browser.close().catch(() => {});
  if (hub) { try { hub.kill('SIGTERM'); } catch (_) {} await hub.status.catch(() => {}); }
  if (!Deno.env.get('PARSEH_KEEP')) await Deno.remove(TMP, {recursive: true}).catch(() => {});
}

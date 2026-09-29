// SPDX-License-Identifier: GPL-3.0-or-later
import { chromium } from 'npm:playwright-core@1.52.0';
// Run: CHROME_BIN=/path/to/chrome PARSEH_PYTHON=/path/to/python3 deno run --allow-all tests/llmrow.mjs
//      LLMROW_SHOTS=<dir>   saves a screenshot of every surface, at 1280 and 390 px, in the light, the dark and
//                           (where the page has it) the sepia theme
//      LLMROW_ONLY=a,b      runs only those sections (a development aid): size, row, studio, add, tidy, player,
//                           reader, ask, storage
//      LLMROW_KEEPGOING=1   goes on past a section that fails, and lists them at the end (to see which sections
//                           a tree that has no row fails)
//
// THE LLM ROW, lib/llmrow.js: the controls around a prompt, drawn once for every page that hands one out --
// driven where a person meets it.  The real hub (serve.main() over a temporary tree: a Persian video, Persian and
// Italian books built into readers, the studio mounted at /studio) and the studio run on its own
// (tests/studio_harness.py studio), a real Chromium, the clipboard read back off the browser.  Nothing is stubbed
// but YouTube's iframe API and the dictionary's answer.
//
//  size)    the one helper that counts: about 4 characters a token in Latin script and 2 in Arabic script, CJK and
//           Devanagari, worked out from the mix; the words said above the copy; past 8,000 tokens one sentence.
//  row)     the row on its own: the size said before any copy and worked out from the very text held; the press
//           copies exactly that text INSIDE the click (a held text) and after a wait only when it had to make it;
//           a text made for another state is never copied (invalidate, forget, `fresh`); a clipboard that refuses
//           gets the box to copy by hand, made only then, and the next press copies the held text; the last-used
//           button goes first; the menu and the skill button are not drawn until a caller supplies them; the
//           reason a button is off is its tooltip; localStorage throwing changes nothing.
//  studio)  the prompt page and the editor's dialog, mounted at /studio and run on their own: the size before the
//           copy, the clipboard equal to the box (and to the box with the question after it), the dialog's size
//           equal to what the route hands out.
//  add)     the video add page: "Prepare the prompt" copies nothing; the row appears with the size; the copy is
//           exactly the box; a changed transcript takes both away.
//  tidy)    the transcript editor's LLM panel: the size, the copy, and a word typed into a caption BEFORE the
//           press is in what is copied.
//  player)  the player's "gloss with an LLM" panel: the size appears once a stretch is picked, before any press;
//           a box changed makes another prompt and another size.
//  reader)  the reader's region sheet: the same, and the sheet shut lets the held prompt go.
//  ask)     Ask LLM in the sources sidebar of the reader and of the player: the size before the copy, and a first
//           line that names the prompt, the languages and the Parseh that wrote it, the number read from the
//           server (GET /__version) and equal to the VERSION file.
//  storage) the pages work with localStorage refused.
//  look)    at every surface, at 1280 and 390 px, in the light, dark and sepia themes: the row is inside the
//           window, does not overflow, and its button is on top (elementFromPoint); the screenshots are read by
//           whoever runs this with LLMROW_SHOTS.
//  last)    no page threw or logged an error or had a request refused; the hub printed no traceback; the owner's
//           config/, books/, youtube/videos/ and the fixtures are as they were.
const root = await Deno.realPath(new URL('..', import.meta.url));
Deno.chdir(root);
const PY = Deno.env.get('PARSEH_PYTHON') || 'python3';
const TMP = await Deno.makeTempDir({prefix: 'parseh-llmrow-'});
const SHOTS = Deno.env.get('LLMROW_SHOTS') || '';
const ONLY = (Deno.env.get('LLMROW_ONLY') || '').split(',').filter(Boolean);
const KEEP = !!Deno.env.get('LLMROW_KEEPGOING');
const failed = [];
if (SHOTS) await Deno.mkdir(SHOTS, {recursive: true});
const td = new TextDecoder();
let passed = 0;
const assert = (v, m) => { if (!v) throw Error('FAIL: ' + m); passed++; console.log('  ok', m); };
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const eq = (got, want, m) => assert(same(got, want),
  m + (same(got, want) ? '' : ': got ' + JSON.stringify(got) + ' want ' + JSON.stringify(want)));
const sleep = ms => new Promise(r => setTimeout(r, ms));
async function until(fn, what, ms = 20000) {
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
const VERSION = (await Deno.readTextFile(root + '/VERSION')).trim();

/* ---------------- the toolbox ---------------- */
// Copies of the fixture Persian video and of the Persian and Italian editions, the latter built into readers
// with their climb to lib/ written as the hub's own path (tests/mobile_harness.built_reader); lib/ and
// youtube/lib/ linked into the tree; a film that is a few bytes, for the add page (which asks only that the file
// exists and is called like a film).  The fixtures themselves are only ever read.
const BUILD = String.raw`
import json, os, shutil, sys
from pathlib import Path
REPO = Path(os.getcwd())
sys.path[:0] = ['tests', 'lib']
import mobile_harness
tmp = Path(sys.argv[1])
root = tmp / 'root'
for d in (root / 'youtube' / 'videos', tmp / 'library', tmp / 'exercises', tmp / 'anki', tmp / 'tray',
          tmp / 'config', tmp / 'films'):
    d.mkdir(parents=True, exist_ok=True)
os.symlink(str(REPO / 'lib'), str(root / 'lib'))
os.symlink(str(REPO / 'youtube' / 'lib'), str(root / 'youtube' / 'lib'))
(tmp / 'films' / 'lesson.mp4').write_bytes(b'not really a film')
vd = root / 'youtube' / 'videos' / 'persian' / 'fA6bK2mQ8sT'
shutil.copytree(str(REPO / 'tests/fixtures/videos/persian/fA6bK2mQ8sT'), str(vd))
out = {'video': str(vd)}
for key, folder, slug in (('fa', 'persian', 'mini-fa'), ('it', 'italian', 'mini-it')):
    d = root / 'books' / folder / slug
    shutil.copytree(str(REPO / 'tests/fixtures/books' / folder / slug), str(d),
                    ignore=shutil.ignore_patterns('reader', '.reader-key'))
    mobile_harness.built_reader(d)
    out[key] = str(d)
print(json.dumps(out))
`;
// serve.main() over the temporary tree: every store it reads or writes is in there (prefs and the network door,
// the offline door's two memories, the LaTeX themes, the studio library, the decks, the Anki store and the clip
// tray).  YouTube's oEmbed is answered by nobody, so the add page never waits for a network there is not
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
ytpages.oembed = lambda vid: {}
for st in {store, serve.studio.store}:
    st.LIB = tmp / 'library'
    st.set_clips_dir(tmp / 'tray')
decks.set_dir(tmp / 'exercises')
decks.set_clips_dir(tmp / 'tray')
serve.ROOT = str(tmp / 'root')
serve._AtRoot.directory = str(tmp / 'root')
ytpages.VIDEOS = str(tmp / 'root' / 'youtube' / 'videos')
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
            continue                    # build output, gitignored
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
const ownBefore = JSON.parse(await py(OWN, TMP));

// THE YOUTUBE PLAYER, as the page loads it from https://www.youtube.com/iframe_api: a player that plays nothing
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
  this.destroy = function () {};
  setTimeout(function () { if (o.events && o.events.onReady) o.events.onReady({target: self}); }, 20);
}};
if (window.onYouTubeIframeAPIReady) window.onYouTubeIframeAPIReady();`;
// what the dictionary and the corpus would say of any chunk: one word, one sentence somebody translated
const LOOKUP = {ok: true, words: [{word: 'x', hits: [{headword: 'x', translit: 'ex', pos: 'noun', senses: ['a letter']}]}],
                pairs: [{src: 'یک مثال', dst: 'An example.', matched: []}], pairs_more: false, pairs_offset: 0,
                corpus: {source: 'Tatoeba'}};

const errors = [];
const log = [];
let hub = null, studio = null, browser = null;
try {
  const B0 = JSON.parse((await py(BUILD, TMP)).trim().split('\n').pop());
  const port = freePort();
  hub = new Deno.Command(PY, {args: ['-c', SERVE, TMP, String(port)], cwd: root, stdout: 'piped', stderr: 'piped'}).spawn();
  drain(hub.stdout, log); drain(hub.stderr, log);
  const B = `http://127.0.0.1:${port}`;
  for (const t = Date.now();;) {
    try { const r = await fetch(B + '/clips/api/status'); await r.body?.cancel(); if (r.ok) break; } catch (_) {}
    if (Date.now() - t > 60000) throw Error('the hub did not start:\n' + log.join(''));
    await sleep(250);
  }
  // the studio on its own: its own process, its own library, plain http
  studio = new Deno.Command(PY, {args: ['tests/studio_harness.py', 'studio'], cwd: root, stdout: 'piped', stderr: 'piped'}).spawn();
  const slog = [];
  drain(studio.stderr, slog);
  const sreader = studio.stdout.pipeThrough(new TextDecoderStream()).getReader();
  let sbuf = '', S0 = null;
  while (!S0) {
    const {value, done} = await sreader.read();
    if (done) throw Error('the studio harness ended: ' + sbuf + slog.join(''));
    sbuf += value;
    const m = /READY (\{.*\})/.exec(sbuf);
    if (m) S0 = JSON.parse(m[1]);
  }
  (async () => { for (;;) { const {done} = await sreader.read(); if (done) break; } })();
  const SB = `http://127.0.0.1:${S0.port}`;

  browser = await chromium.launch({executablePath: Deno.env.get('CHROME_BIN'), headless: true});
  const SENTINEL = 'SENTINEL — not written by the page';

  /* ---------------- helpers over a page ---------------- */
  // WHAT A PAGE MAY BE REFUSED, and nothing else: the pages ask for a translation model, a waveform, a book's
  // timings and the browser's own icon on load and do without them; a studio run on its own has no /lib/activity.js
  const optional = (status, method, path) => status === 404 && method === 'GET' &&
    (/^\/mt\/[^/]+\/meta\.json$/.test(path) || /^\/youtube\/videos\/[^/]+\/[^/]+\/waveform\.json$/.test(path) ||
     /^\/books\/[^/]+\/[^/]+\/timings\.json$/.test(path) || path === '/favicon.ico' || path === '/lib/activity.js');
  async function context({w = 1280, h = 900, scheme = 'light', storage = true} = {}) {
    const ctx = await browser.newContext({viewport: {width: w, height: h}, colorScheme: scheme});
    await ctx.grantPermissions(['clipboard-read', 'clipboard-write'], {origin: B});
    await ctx.grantPermissions(['clipboard-read', 'clipboard-write'], {origin: SB});
    // nothing leaves this machine but YouTube's API, which is this test's
    await ctx.route(/^https?:\/\/(?!127\.0\.0\.1[:/])/, route => {
      if (route.request().url() === 'https://www.youtube.com/iframe_api')
        return route.fulfill({contentType: 'text/javascript', body: FAKE_YT});
      return route.abort();
    });
    // what the dictionary and the corpus would say, so that the sources sidebar has something to draw
    await ctx.route(/\/(__lookup|youtube\/api\/lookup)$/, route => route.fulfill({json: LOOKUP}));
    if (!storage) await ctx.addInitScript(() => {
      Object.defineProperty(window, 'localStorage', {configurable: true, get() { throw new DOMException('denied', 'SecurityError'); }});
    });
    return ctx;
  }
  async function open(ctx, url, name, ready) {
    const page = await ctx.newPage();
    page.on('pageerror', e => errors.push(name + ' pageerror: ' + e.message));
    page.on('response', r => {
      if (r.status() < 400) return;
      const u = new URL(r.url());
      if (!r.url().startsWith(B) && !r.url().startsWith(SB)) return;
      if (optional(r.status(), r.request().method(), u.pathname)) return;
      errors.push(name + ' ' + r.status() + ' ' + r.request().method() + ' ' + u.pathname);
    });
    page.on('console', m => {
      if (m.type() !== 'error') return;
      const at = (m.location() || {}).url || '';
      // a refusal is counted by its response above; YouTube's, aborted here, is the offline world the test lives in
      if (/^Failed to load resource/.test(m.text())) return;
      errors.push(name + ' console: ' + m.text() + (at ? ' (' + at + ')' : ''));
    });
    page.on('requestfailed', r => {
      if (!r.url().startsWith(B) && !r.url().startsWith(SB)) return;
      // the studio on its own has no /lib/activity.js (its page says so), and the page leaving abandons the ask
      if (new URL(r.url()).pathname === '/lib/activity.js') return;
      errors.push(name + ' request failed: ' + r.method() + ' ' + new URL(r.url()).pathname + ' (' + (r.failure() || {}).errorText + ')');
    });
    await page.goto(url);
    if (ready) await ready(page);
    return page;
  }
  const clip = page => page.evaluate(() => navigator.clipboard.readText());
  const setClip = (page, s) => page.evaluate(s => navigator.clipboard.writeText(s), s);
  const text = (page, sel) => page.evaluate(sel => { const e = document.querySelector(sel); return e ? e.textContent : null; }, sel);
  const attr = (page, sel, a) => page.evaluate(([sel, a]) => { const e = document.querySelector(sel); return e ? e.getAttribute(a) : null; }, [sel, a]);
  // the row inside `scope`: what it says, as a person reads it
  const rowOf = (page, scope = '') => page.evaluate(scope => {
    const r = document.querySelector((scope + ' .llmrow').trim());
    if (!r) return null;
    const t = s => { const e = r.querySelector(s); return e ? e.textContent : null; };
    const on = s => { const e = r.querySelector(s); return !!e && !e.hidden && e.getClientRects().length > 0; };
    const sz = r.querySelector('.llmrow-size');
    return {size: t('.llmrow-size'), chars: sz.getAttribute('data-chars'), tokens: sz.getAttribute('data-tokens'),
            warn: on('.llmrow-warn'), note: t('.llmrow-note'), say: t('.llmrow-say'),
            copy: t('.llmrow-copy'), copyOff: r.querySelector('.llmrow-copy').disabled,
            skill: on('.llmrow-skill'), menu: on('.llmrow-menu'), hand: !!r.querySelector('.llmrow-hand') && on('.llmrow-hand')};
  }, scope);
  // the size line has a number in it, and it is no longer "measuring…"
  const sized = async (page, scope = '') => {
    try {
      return await until(async () => {
        const r = await rowOf(page, scope);
        return r && r.chars ? r : null;
      }, `the row in ${scope || 'the page'} says how long the prompt is`);
    } catch (e) {
      throw Error(e.message + ' -- the row says ' + JSON.stringify(await rowOf(page, scope)));
    }
  };
  // a line of a prompt's size, as the row words it: "about 12,500 characters (about 3,100 tokens)"
  const sizeWords = (chars, tokens) => {
    const round = n => n < 100 ? n : n < 1000 ? Math.round(n / 10) * 10 : Math.round(n / 100) * 100;
    const fmt = n => String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    return `about ${fmt(round(chars))} characters (about ${fmt(round(tokens))} tokens)`;
  };
  const codePoints = s => [...s].length;

  /* ---------------- how it looks, and where ---------------- */
  // every surface, in the windows and themes a person meets it in.  The row must be inside the window and not
  // wider than its own box, its button must be what the browser finds at its centre (nothing over it), and the
  // page must not be made wider by it.  Screenshots, if asked for, are of the whole window.
  const THEMES = [['light', 1280, 900], ['dark', 1280, 900], ['light', 390, 844], ['dark', 390, 844], ['sepia', 390, 844]];
  async function look(page, name, {scope = '', studio: isStudio = false, themes = THEMES} = {}) {
    for (const [theme, w, h] of themes) {
      if (isStudio && theme === 'sepia') { /* the studio has it too, on <body> */ }
      await page.setViewportSize({width: w, height: h});
      await page.evaluate(([t, studio]) => {
        document.documentElement.setAttribute('data-theme', t);
        if (document.body) document.body.setAttribute('data-theme', t);
        if (studio && document.body) document.body.dataset.theme = t;
      }, [theme, isStudio]);
      await sleep(150);
      const r = await page.evaluate(scope => {
        const row = document.querySelector((scope + ' .llmrow').trim());
        const btn = row.querySelector('.llmrow-copy');
        btn.scrollIntoView({block: 'center'});
        const rr = row.getBoundingClientRect(), br = btn.getBoundingClientRect();
        const hit = document.elementFromPoint(br.left + br.width / 2, br.top + br.height / 2);
        const wide = [...row.querySelectorAll('*')].filter(e => e.getBoundingClientRect().right > rr.right + 1 && getComputedStyle(e).display !== 'none').length;
        return {left: rr.left, right: rr.right, width: innerWidth, hit: !!hit && (btn === hit || btn.contains(hit)),
                over: row.scrollWidth > row.clientWidth + 1, wide, page: document.documentElement.scrollWidth,
                size: !!row.querySelector('.llmrow-size') && row.querySelector('.llmrow-size').getClientRects().length > 0};
      }, scope);
      assert(r.left >= 0 && r.right <= r.width + 0.5 && r.hit && !r.over && r.wide === 0,
             `${name}: the row is inside the window, its button on top and nothing wider than its box (${theme}, ${w} px)`);
      if (SHOTS) await page.screenshot({path: `${SHOTS}/${name}-${theme}-${w}.png`});
    }
    await page.setViewportSize({width: 1280, height: 900});
    await page.evaluate(() => { document.documentElement.setAttribute('data-theme', 'light'); if (document.body) document.body.setAttribute('data-theme', 'light'); });
  }
  const section = async (key, title, fn) => {
    if (ONLY.length && !ONLY.includes(key)) return;
    console.log(`\n${key}) ${title}`);
    try {
      await fn();
    } catch (e) {
      if (!KEEP) throw e;
      failed.push(key);
      console.log(`  FAILED: ${String(e.message).split('\n')[0].slice(0, 220)}`);
    }
  };

  /* ---------------- size) the one helper that counts ---------------- */
  await section('size', 'the size of a prompt: 4 characters a token in Latin script, 2 in Arabic script, CJK and Devanagari', async () => {
    const ctx = await context();
    const page = await open(ctx, `${B}/studio/prompt`, 'size', p => p.waitForFunction(() => window.ParsehLLMRow));
    const size = t => page.evaluate(t => ParsehLLMRow.promptSize(t), t);
    const at = async (label, t, chars, tokens) => {
      const s = await size(t);
      eq([s.chars, s.tokens], [chars, tokens], `${label}: ${chars} characters are about ${tokens} tokens`);
      return s;
    };
    await at('Latin', 'abcd'.repeat(1000), 4000, 1000);
    await at('Persian (Arabic script)', 'س'.repeat(4000), 4000, 2000);
    await at('Persian with its short vowels', 'سَلامٌ'.repeat(500), 3000, 1500);
    await at('Japanese', '漢あア'.repeat(1000), 3000, 1500);
    await at('Chinese beyond the first plane', '𠀀'.repeat(1000), 1000, 500);
    await at('Hindi (Devanagari)', 'क'.repeat(4000), 4000, 2000);
    await at('Korean', '한'.repeat(1000), 1000, 500);
    await at('half Latin, half Arabic script', 'abcd'.repeat(500) + 'س'.repeat(2000), 4000, 1500);
    await at('an emoji is one character, in the Latin rate', '😀'.repeat(1000), 1000, 250);
    await at('nothing', '', 0, 0);
    eq((await size('x'.repeat(12483))).line, 'about 12,500 characters (about 3,100 tokens)', 'the words said above the copy');
    eq((await size('x'.repeat(57))).line, 'about 57 characters (about 15 tokens)', 'below a hundred it is exact');
    eq((await size('x'.repeat(457))).line, 'about 460 characters (about 120 tokens)', 'below a thousand it is to ten');
    eq((await size('')).line, '', 'nothing is said of nothing');
    eq([(await size('x'.repeat(32000))).over, (await size('x'.repeat(32001))).over], [false, true],
       'past 8,000 tokens (32,001 Latin characters), and not before');
    eq((await size('س'.repeat(16001))).over, true, 'the same in Arabic script: 16,001 characters');
    eq(await page.evaluate(() => ParsehLLMRow.TOO_MUCH),
       'some chatbots take less at once — ask for less, or send the rules and the data in two messages.',
       'the sentence past 8,000 tokens');
    await ctx.close();
  });

  /* ---------------- row) the row on its own ---------------- */
  await section('row', 'the row: size before the copy, the held text, the box by hand, the two slots', async () => {
    const ctx = await context();
    // any page that has parseh.css and the script will do: the licences page is the smallest
    const page = await open(ctx, `${B}/licences/`, 'row', async p => {
      await p.addStyleTag({url: `${B}/lib/parseh.css`});
      await p.addScriptTag({url: `${B}/lib/llmrow.js`});
      await p.waitForFunction(() => window.ParsehLLMRow);
    });
    await page.evaluate(() => {
      window.made = [];
      // where a copy is made: in the click itself, or after something was waited for
      window.writes = [];
      const real = navigator.clipboard.writeText.bind(navigator.clipboard);
      window.refuse = false;
      navigator.clipboard.writeText = t => {
        window.writes.push({text: t, inClick: !!window.__click});
        return window.refuse ? Promise.reject(new DOMException('denied', 'NotAllowedError')) : real(t);
      };
      document.addEventListener('click', () => { window.__click = true; setTimeout(() => { window.__click = false; }, 0); }, true);
      window.slot = document.createElement('div');
      window.slot.id = 'slot';
      document.body.appendChild(window.slot);
    });
    const fresh = () => page.evaluate(() => {
      document.getElementById('slot').remove();
      const s = document.createElement('div');
      s.id = 'slot';
      document.body.appendChild(s);
      window.writes = [];
      window.made = [];
      window.refuse = false;
    });
    const TEXT = 'A prompt\nwith two lines, and a last one that ends the text\n';

    // 1) nothing said until there is something to say; the slots are not drawn
    await page.evaluate(() => {
      window.row = ParsehLLMRow.mount(document.getElementById('slot'), {
        surface: 'lab', getText: async ctx => { window.made.push(ctx.press); await new Promise(r => setTimeout(r, 40)); return window.__next; }});
    });
    let r = await rowOf(page, '#slot');
    eq([r.size, r.chars, r.copy, r.copyOff, r.menu, r.skill, r.hand],
       ['', null, 'copy the prompt', false, false, false, false],
       'a fresh row: no size yet, the button is there, and no menu, no skill button, no box for a copy by hand');
    eq(await page.evaluate(() => document.querySelector('#slot .llmrow-note').textContent),
       'paste it into a chatbot, then bring its answer back here.', 'and one line of reminder, a plain generic one');
    eq(await page.evaluate(() => document.querySelectorAll('#slot textarea').length), 0,
       'nothing in it a page could take for its own textarea');

    // 2) update: the size is worked out from the very text, and said before any copy
    await setClip(page, SENTINEL);
    await page.evaluate(t => window.row.update(t), TEXT);
    r = await rowOf(page, '#slot');
    eq([r.chars, r.tokens, r.size, r.warn], [String(TEXT.length), String(Math.ceil(TEXT.length / 4)), sizeWords(TEXT.length, Math.ceil(TEXT.length / 4)), false],
       'update(text): the size line is that text\'s, its numbers are in the row');
    eq(await clip(page), SENTINEL, 'and nothing was copied by saying it');
    await page.evaluate(() => window.row.update('x'.repeat(40000)));
    r = await rowOf(page, '#slot');
    eq([r.warn, r.tokens], [true, '10000'], 'past 8,000 tokens the row adds its sentence');
    eq(await text(page, '#slot .llmrow-warn'), 'some chatbots take less at once — ask for less, or send the rules and the data in two messages.',
       'the owner\'s sentence, as written');
    await page.evaluate(t => window.row.update(t), TEXT);

    // 3) the press copies the held text INSIDE the click, exactly
    await fresh();
    await page.evaluate(t => { window.row = ParsehLLMRow.mount(document.getElementById('slot'), {surface: 'lab', getText: async () => 'never'}); window.row.update(t); }, TEXT);
    await page.click('#slot .llmrow-copy');
    await page.waitForFunction(() => /^copied/.test(document.querySelector('#slot .llmrow-say').textContent));
    eq(await clip(page), TEXT, 'the clipboard holds exactly the text held, its line breaks and its last newline included');
    eq(await page.evaluate(() => window.writes.map(w => w.inClick)), [true], 'and it was written inside the click itself, before anything was awaited');
    eq(await text(page, '#slot .llmrow-say'), 'copied ✓', 'the row says it, and only then');
    // a change of text: "copied" was about the text before
    await page.evaluate(() => window.row.update('another text'));
    eq(await text(page, '#slot .llmrow-say'), '', 'a new text takes "copied" away');

    // 4) a text that has to be made is made at the press, and copied after the wait
    await fresh();
    await page.evaluate(() => {
      window.__next = 'made at the press';
      window.row = ParsehLLMRow.mount(document.getElementById('slot'), {surface: 'lab',
        getText: async ctx => { window.made.push(ctx.press); await new Promise(r => setTimeout(r, 40)); return window.__next; }});
    });
    await page.click('#slot .llmrow-copy');
    await page.waitForFunction(() => /^copied/.test(document.querySelector('#slot .llmrow-say').textContent));
    eq(await page.evaluate(() => [window.made, window.writes.map(w => [w.text, w.inClick])]),
       [[true], [['made at the press', false]]], 'no text held: getText({press: true}) once, the copy after the wait');
    eq((await rowOf(page, '#slot')).chars, String('made at the press'.length), 'and its size is said');
    // a second press has it held: nothing is made again, the copy is in the click
    await page.click('#slot .llmrow-copy');
    await page.waitForFunction(() => window.writes.length === 2);
    eq(await page.evaluate(() => [window.made.length, window.writes[1].inClick]), [1, true], 'a second press copies the held text in the click, and makes nothing');

    // 5) refresh measures (press: false); invalidate drops what is held and measures again soon, if it should
    await fresh();
    await page.evaluate(() => {
      window.__next = 'measured';
      window.__measure = true;
      window.row = ParsehLLMRow.mount(document.getElementById('slot'), {surface: 'lab', measure: () => window.__measure,
        getText: async ctx => { window.made.push(ctx.press); return window.__next; }});
      window.row.refresh();
    });
    await sized(page, '#slot');
    eq(await page.evaluate(() => [window.made, window.row.text()]), [[false], 'measured'], 'refresh(): asked with press false, and held');
    await page.evaluate(() => { window.__next = 'measured again, longer'; window.row.invalidate(); });
    eq(await page.evaluate(() => [window.row.text(), document.querySelector('#slot .llmrow-size').textContent]), [null, ''],
       'invalidate(): nothing held and no size at once -- a stale size is worse than none');
    await until(async () => (await rowOf(page, '#slot')).chars === String('measured again, longer'.length), 'measured again after a moment');
    await page.evaluate(() => { window.__measure = false; window.row.invalidate(); });
    await sleep(600);
    eq(await page.evaluate(() => [window.row.text(), window.made.length]), [null, 2], 'and not measured again where measure() says there is nothing to measure');

    // 6) an answer for a state that has gone is dropped
    await page.evaluate(() => {
      window.row.forget();
      window.__next = 'for the old state';
      const p = window.row.refresh();
      window.row.forget();
      return p;
    });
    await sleep(300);
    eq(await page.evaluate(() => window.row.text()), null, 'forget() while a text is being made: the answer is dropped when it arrives');

    // 7) `fresh`: a held text the page says is stale is made again before it is copied
    await fresh();
    await page.evaluate(() => {
      window.__next = 'the new text';
      window.__stale = false;
      window.row = ParsehLLMRow.mount(document.getElementById('slot'), {surface: 'lab', fresh: () => !window.__stale,
        getText: async ctx => { window.made.push(ctx.press); return window.__next; }});
      window.row.update('the old text');
    });
    await page.evaluate(() => { window.__stale = true; });
    await page.click('#slot .llmrow-copy');
    await page.waitForFunction(() => window.writes.length === 1);
    eq(await page.evaluate(() => [window.writes[0].text, window.made]), ['the new text', [true]], 'fresh() false: the text is made again, and that is what is copied');

    // 8) a clipboard that refuses: the box to copy by hand, made only now; the second press copies the held text
    await fresh();
    await page.evaluate(t => {
      window.oncopied = [];
      window.row = ParsehLLMRow.mount(document.getElementById('slot'), {surface: 'lab', ids: {copy: 'labcopy', hand: 'labhand', handRow: 'labhandrow'},
        getText: async () => 'never', onCopied: (ok, text, which) => window.oncopied.push([ok, text, which])});
      window.row.update(t);
      window.refuse = true;
      document.execCommand = () => false;
    }, TEXT);
    await page.click('#labcopy');
    await page.waitForSelector('#labhandrow:not([hidden])');
    eq(await page.evaluate(() => [document.getElementById('labhand').value, document.activeElement === document.getElementById('labhand'),
                                   document.getElementById('labhand').selectionStart === 0 &&
                                   document.getElementById('labhand').selectionEnd === document.getElementById('labhand').value.length,
                                   document.getElementById('labhand').readOnly, document.getElementById('labhand').dir]),
       [TEXT, true, true, true, 'ltr'], 'the prompt is in the box, selected, read only, left to right');
    eq(await text(page, '#slot .llmrow-say'), 'the browser would not put it on the clipboard', 'the row says why');
    eq(await page.evaluate(() => window.oncopied), [[false, TEXT, 'prompt']], 'and tells the page that it did not reach the clipboard');
    await page.evaluate(() => { window.refuse = false; });
    await page.click('#labcopy');
    await page.waitForFunction(() => window.oncopied.length === 2);
    eq(await clip(page), TEXT, 'the second press copies the held text');
    eq(await page.evaluate(() => [document.getElementById('labhandrow').hidden, document.getElementById('labhand').value]), [true, ''],
       'and puts the box away');

    // 9) or the page's own box, where it has one: selected there, none drawn
    await fresh();
    await page.evaluate(t => {
      const own = document.createElement('textarea');
      own.id = 'own';
      own.value = t;
      document.getElementById('slot').before(own);
      window.row = ParsehLLMRow.mount(document.getElementById('slot'), {surface: 'lab', box: () => own, getText: async () => 'never'});
      window.row.update(t);
      window.refuse = true;
      document.execCommand = () => false;
    }, TEXT);
    await page.click('#slot .llmrow-copy');
    await page.waitForFunction(() => /would not put/.test(document.querySelector('#slot .llmrow-say').textContent));
    eq(await page.evaluate(() => [document.activeElement === document.getElementById('own'), document.getElementById('own').selectionEnd,
                                   document.querySelector('#slot .llmrow-hand')]),
       [true, TEXT.length, null], 'the page\'s own box is selected, and the row draws none of its own');
    await page.evaluate(() => document.getElementById('own').remove());

    // 10) the menu and the skill button are for later lanes: nothing is drawn until a caller supplies them
    await fresh();
    await page.evaluate(() => {
      window.picked = [];
      window.row = ParsehLLMRow.mount(document.getElementById('slot'), {surface: 'lab-slots', getText: async () => 'never'});
      window.row.update('the prompt');
    });
    eq(await page.evaluate(() => [window.row.menuSlot.hidden, getComputedStyle(window.row.menuSlot).display,
                                   getComputedStyle(document.querySelector('#slot .llmrow-skill')).display]),
       [true, 'none', 'none'], 'the menu and the skill button are hidden until supplied');
    await page.evaluate(() => window.row.setMenu({items: [{id: 'p', label: "Parseh's"}, {id: 'm', label: 'my own'}], value: 'p',
                                                   onChange: (id, item) => window.picked.push([id, item.label])}));
    eq(await page.evaluate(() => [window.row.menuSlot.hidden, window.row.menuSlot.querySelector('label').firstChild.textContent,
                                   [...window.row.menuSlot.querySelectorAll('option')].map(o => o.textContent)]),
       [false, 'prompt: ', ["Parseh's", 'my own']], 'the menu, once items are supplied: "prompt:" and its choices');
    await page.selectOption('#slot .llmrow-menu select', 'm');
    eq(await page.evaluate(() => window.picked), [['m', 'my own']], 'a choice tells its caller');
    await page.evaluate(() => window.row.setMenu(null));
    eq(await page.evaluate(() => window.row.menuSlot.hidden), true, 'and setMenu(null) takes it away');
    await page.evaluate(() => window.row.setSkill({getText: async () => 'Parseh request · parseh-gloss · a0.4.2', note: 'in a chat where the skill is installed, paste this.',
                                                    link: {text: 'how to install it', href: '/guide/'}}));
    r = await rowOf(page, '#slot');
    eq([r.skill, await text(page, '#slot .llmrow-skillnote'), await attr(page, '#slot .llmrow-skillnote a', 'href')],
       [true, 'in a chat where the skill is installed, paste this. how to install it', '/guide/'], 'the skill button, its note and its link, once supplied');
    eq(await page.evaluate(() => [...document.querySelectorAll('#slot .llmrow-bar > button')].map(b => b.className.replace(/\s.*/, ''))),
       ['llmrow-copy', 'llmrow-skill'], 'the prompt first, when nothing has been remembered');

    // 11) which of the two was used last is remembered, per surface, and goes first -- and neither is hidden
    await setClip(page, SENTINEL);
    await page.click('#slot .llmrow-skill');
    await page.waitForFunction(() => /^copied/.test(document.querySelector('#slot .llmrow-say').textContent));
    eq(await clip(page), 'Parseh request · parseh-gloss · a0.4.2', 'the skill button copies its own text');
    eq(await page.evaluate(() => localStorage.getItem('parseh_llmrow_lab-slots')), 'skill', 'and it is remembered on this device');
    await fresh();
    await page.evaluate(() => {
      window.row = ParsehLLMRow.mount(document.getElementById('slot'), {surface: 'lab-slots', getText: async () => 'never'});
      window.row.update('the prompt');
      window.row.setSkill({getText: async () => 'the request'});
    });
    eq(await page.evaluate(() => [...document.querySelectorAll('#slot .llmrow-bar > button')].map(b => [b.className.replace(/\s.*/, ''), b.getClientRects().length > 0])),
       [['llmrow-skill', true], ['llmrow-copy', true]], 'next time the skill button is first, and the other is still there');
    eq(await page.evaluate(() => localStorage.getItem('parseh_llmrow_another-surface')), null, 'and another surface remembers nothing of it');
    await page.click('#slot .llmrow-copy');
    eq(await page.evaluate(() => localStorage.getItem('parseh_llmrow_lab-slots')), 'prompt', 'pressing the other button is remembered in its turn');

    // 12) the button's reason, and the error a page does not say itself
    await fresh();
    await page.evaluate(() => {
      window.row = ParsehLLMRow.mount(document.getElementById('slot'), {surface: 'lab', getText: async () => { throw new Error('the server refused: no chunk'); }});
      window.row.disable('click a caption first');
    });
    eq(await page.evaluate(() => { const b = document.querySelector('#slot .llmrow-copy'); return [b.disabled, b.title]; }),
       [true, 'click a caption first'], 'disable(why): the button is off, and the reason is its tooltip');
    await page.evaluate(() => window.row.enable('copy the prompt for captions 1–3'));
    eq(await page.evaluate(() => { const b = document.querySelector('#slot .llmrow-copy'); return [b.disabled, b.title]; }),
       [false, 'copy the prompt for captions 1–3'], 'enable(title): on again, with its own tooltip');
    await page.click('#slot .llmrow-copy');
    await page.waitForFunction(() => /refused/.test(document.querySelector('#slot .llmrow-say').textContent));
    eq(await page.evaluate(() => [document.querySelector('#slot .llmrow-say').classList.contains('bad'), window.writes.length]), [true, 0],
       'getText failing: the row says it, in the error colour, and copies nothing');

    // 13) a page's own callback that throws is the page's fault, said on the console: the row goes on
    await fresh();
    await page.evaluate(() => {
      window.faults = [];
      const real = console.error;
      console.error = e => window.faults.push(e && e.message);
      window.__real = real;
      window.row = ParsehLLMRow.mount(document.getElementById('slot'), {surface: 'lab', getText: async () => 'made',
        onPress: () => { throw new Error('a bug in onPress'); }, onCopied: () => { throw new Error('a bug in onCopied'); }});
    });
    await page.click('#slot .llmrow-copy');
    await page.waitForFunction(() => window.writes.length === 1);
    await page.click('#slot .llmrow-copy');
    await page.waitForFunction(() => window.writes.length === 2);
    eq(await page.evaluate(() => [window.faults, document.querySelector('#slot .llmrow-copy').hasAttribute('aria-busy'),
                                   window.writes.map(w => w.text)]),
       [['a bug in onPress', 'a bug in onCopied', 'a bug in onPress', 'a bug in onCopied'], false, ['made', 'made']],
       'the row is not left busy, both presses copy, and each fault is on the console');
    await page.evaluate(() => { console.error = window.__real; });

    // 14) a page that reads right to left: the row starts where the page does, and its English lines read as English
    await fresh();
    const rtl = await page.evaluate(() => {
      const box = document.createElement('div');
      box.id = 'rtl';
      box.dir = 'rtl';
      box.style.cssText = 'width:420px;border:1px solid #999;padding:8px';
      document.getElementById('slot').before(box);
      const row = ParsehLLMRow.mount(box, {surface: 'lab-rtl', getText: async () => 'never'});
      // past 8,000 tokens, so that the warning is drawn too: 12,000 Arabic-script characters and 12,000 Latin ones
      row.update('س'.repeat(12000) + 'abcd'.repeat(3000));
      const q = s => box.querySelector(s), r = e => e.getBoundingClientRect(), b = r(box);
      const bidi = ['.llmrow-size', '.llmrow-warn', '.llmrow-note'].map(s => getComputedStyle(q(s)).unicodeBidi);
      return {bidi, btn: r(q('.llmrow-copy')).right, left: b.left, right: b.right, over: box.scrollWidth > box.clientWidth,
              warn: q('.llmrow-warn').getClientRects().length > 0};
    });
    eq(rtl.bidi, ['plaintext', 'plaintext', 'plaintext'], 'in a right-to-left page each line of its words takes its direction from what it says');
    assert(rtl.btn > (rtl.left + rtl.right) / 2 && !rtl.over && rtl.warn, 'the button starts at the right, as the page does, and nothing is wider than the page\'s box');
    await page.evaluate(() => document.getElementById('rtl').remove());

    // 15) storage refused: nothing changes for a person
    await fresh();
    await page.evaluate(() => {
      Object.defineProperty(window, 'localStorage', {configurable: true, get() { throw new DOMException('denied', 'SecurityError'); }});
      window.row = ParsehLLMRow.mount(document.getElementById('slot'), {surface: 'lab-refused', getText: async () => 'never'});
      window.row.update('the prompt');
      window.row.setSkill({getText: async () => 'the request'});
    });
    await page.click('#slot .llmrow-copy');
    await page.waitForFunction(() => /^copied/.test(document.querySelector('#slot .llmrow-say').textContent));
    eq(await clip(page), 'the prompt', 'localStorage throwing: the row is drawn, the two buttons are there, and it copies');

    // 16) which button was used last is remembered ACROSS A RELOAD of the page: the skill button pressed, the page
    // loaded again, the row drawn afresh
    const draw = async () => {
      await page.addScriptTag({url: `${B}/lib/llmrow.js`});
      await page.waitForFunction(() => window.ParsehLLMRow);
      return page.evaluate(() => {
        const s = document.createElement('div');
        s.id = 'slot';
        document.body.appendChild(s);
        window.row = ParsehLLMRow.mount(s, {surface: 'lab-reload', getText: async () => 'never'});
        window.row.update('the prompt');
        window.row.setSkill({getText: async () => 'the request'});
        return [...document.querySelectorAll('#slot .llmrow-bar > button')].map(b => b.className.replace(/\s.*/, ''));
      });
    };
    await page.reload();
    eq(await draw(), ['llmrow-copy', 'llmrow-skill'], 'a page that has remembered nothing puts the prompt first');
    await page.click('#slot .llmrow-skill');
    await page.waitForFunction(() => /^copied/.test(document.querySelector('#slot .llmrow-say').textContent));
    await page.reload();
    eq(await draw(), ['llmrow-skill', 'llmrow-copy'], 'after a reload of the page the skill button, used last, is first, and the other is still there');
    await ctx.close();
  });

  /* ---------------- studio) the prompt page and the editor's dialog, mounted and on their own ---------------- */
  await section('studio', 'the studio: the prompt page and the exercise dialog, in the hub and on their own', async () => {
    const where = [['mounted at /studio', B, '/studio'], ['on its own', SB, '']];
    for (const [what, origin, base] of where) {
      const ctx = await context();
      const page = await open(ctx, `${origin}${base}/prompt`, `studio ${what}`, p => p.waitForSelector('#llm-row .llmrow'));
      const r = await sized(page, '#llm-row');
      const box = await page.inputValue('#prompt-text');
      eq([r.copy, r.skill, r.menu], ['copy the prompt', false, false], `${what}: the prompt page has the row, and no menu or skill button before they are supplied`);
      eq(await page.evaluate(() => ['btn-copy-prompt', 'copy-info'].map(i => !!document.getElementById(i))), [false, false],
         `${what}: and the two buttons it replaces are gone`);
      eq([r.chars, r.size], [String(codePoints(box)), sizeWords(codePoints(box), Number(r.tokens))],
         `${what}: the size said is the size of what the box shows (${r.chars} characters)`);
      assert(/^Parseh prompt · studio-doc · fa · a0\.\d+\.\d+\n\n/.test(box) && box.includes('target: fa — this document is about Persian'),
             `${what}: the box opens with the version line and shows the target line the copy always had`);
      await setClip(page, SENTINEL);
      assert((await clip(page)) === SENTINEL && !!(await rowOf(page, '#llm-row')).chars, `${what}: the size is said, and nothing has been copied`);
      await page.click('#llm-row .llmrow-copy');
      await page.waitForFunction(() => /^copied/.test(document.querySelector('#llm-row .llmrow-say').textContent));
      eq(await clip(page), box, `${what}: "copy the prompt" puts on the clipboard exactly what the box shows`);
      // a question written: the size moves, and the copy is the prompt with the question after it
      const q = 'The Persian words for hot and cold: uses, registers, opposites.';
      await page.fill('#question', q);
      const r2 = await until(async () => { const x = await rowOf(page, '#llm-row'); return x.chars !== r.chars ? x : null; }, 'the size follows the question');
      eq(r2.chars, String(codePoints(box) + codePoints('\n' + q + '\n') + (box.endsWith('\n') ? 0 : 1)), `${what}: the size follows the question as it is typed`);
      eq(r2.copy, 'copy the prompt and your question', `${what}: and the button says that the question goes with it`);
      eq(r2.say, '', `${what}: "copied" was about the text before`);
      await page.click('#llm-row .llmrow-copy');
      await page.waitForFunction(() => /^copied/.test(document.querySelector('#llm-row .llmrow-say').textContent));
      eq(await clip(page), box.replace(/\n*$/, '\n') + '\n' + q + '\n', `${what}: with a question the copy is the prompt, a blank line, and the question`);
      await page.fill('#question', '');
      eq((await until(async () => { const x = await rowOf(page, '#llm-row'); return x.copy === 'copy the prompt' ? x : null; }, 'the button goes back to its plain words')).chars,
         r.chars, `${what}: the question taken away, the button is "copy the prompt" again, and the size is the box's`);
      await page.fill('#question', q);
      await until(async () => (await rowOf(page, '#llm-row')).copy === 'copy the prompt and your question', 'the question is back');
      // another language: another prompt, and its own size
      await page.selectOption('#prompt-target', 'it');
      const r3 = await until(async () => { const x = await rowOf(page, '#llm-row'); return x.chars !== r2.chars ? x : null; }, 'the size follows the language');
      const boxIt = await page.inputValue('#prompt-text');
      assert(/^Parseh prompt · studio-doc · it · /.test(boxIt) && boxIt.includes('target: it — this document is about Italian'), `${what}: Italian is another prompt`);
      eq(r3.chars, String(codePoints(await page.inputValue('#prompt-text')) + codePoints('\n' + q + '\n') + ((await page.inputValue('#prompt-text')).endsWith('\n') ? 0 : 1)),
         `${what}: and the size is its own`);
      await look(page, `studio-prompt-${what.startsWith('mounted') ? 'mounted' : 'alone'}`, {scope: '#llm-row', studio: true});
      await ctx.close();

      // the editor's dialog: made by the server from this page, sized, and copied exactly
      const c2 = await context();
      const made = await (await c2.request.post(`${origin}${base}/api/docs`, {data: {markdown: '---\ntitle: A page\ntarget: fa\n---\n\n## A word\n\nHello.\n'}})).json();
      const id = made.id || (made.doc && made.doc.id) || made.meta && made.meta.id;
      assert(id, `${what}: a document to open the editor on`);
      const ed = await open(c2, `${origin}${base}/doc/${id}/edit`, `dialog ${what}`, p => p.waitForSelector('#btn-exercise-prompt', {state: 'attached'}));
      await ed.click('summary:has-text("Exercises")');
      await ed.click('#btn-exercise-prompt');
      await ed.waitForSelector('.ex-prompt-modal .llmrow');
      const rd = await sized(ed, '.ex-prompt-modal');
      const route = await (await c2.request.post(`${origin}${base}/api/exercise-prompt`, {data: {markdown: await ed.inputValue('#src'), decks: []}})).json();
      eq(rd.chars, String(codePoints(route.prompt)), `${what}: the dialog says the size of what the route hands out, before the copy (${rd.chars} characters)`);
      await setClip(ed, SENTINEL);
      await ed.click('.ex-prompt-modal .llmrow-copy');
      await ed.waitForFunction(() => /^copied/.test(document.querySelector('.ex-prompt-modal .llmrow-say').textContent));
      eq(await clip(ed), route.prompt, `${what}: the dialog's copy is that prompt exactly`);
      eq(await text(ed, '.ex-copy-status'), '', `${what}: no deck ticked, so nothing is said of known items`);
      await look(ed, `studio-dialog-${what.startsWith('mounted') ? 'mounted' : 'alone'}`, {scope: '.ex-prompt-modal', studio: true});
      await ed.click('[data-x="cancel"]');
      eq(await ed.evaluate(() => document.querySelectorAll('.ex-prompt-modal, .llmrow').length), 0, `${what}: "Close" takes the dialog and its row away`);
      await c2.close();
    }
  });

  /* ---------------- add) the video add page ---------------- */
  const CAPTIONS = '0:01\nسلام، حال شما چطور است؟\n0:05\nمن خوبم، ممنون از شما\n0:09\nامروز هوا خیلی خوب است\n';
  async function addPage(ctx, name) {
    const page = await open(ctx, `${B}/youtube/add/?src=film&by=llm`, name, p => p.waitForSelector('#transcript', {state: 'visible'}));
    await page.fill('#path', `${TMP}/films/lesson.mp4`);
    await page.selectOption('#lang', 'fa');
    await page.fill('#transcript', CAPTIONS);
    return page;
  }
  await section('add', 'the video add page: prepare copies nothing, the row says the size, the copy is the box', async () => {
    const ctx = await context();
    const page = await addPage(ctx, 'add');
    eq(await page.evaluate(() => Parseh.llmRow === ParsehLLMRow.mount), true, 'a page that has Parseh has the row as Parseh.llmRow, the same function');
    eq(await page.evaluate(() => document.getElementById('prow').hidden), true, 'before anything is prepared there is no row');
    eq(await page.evaluate(() => document.getElementById('prepare').textContent), 'Prepare the prompt', 'the button prepares');
    await setClip(page, SENTINEL);
    await page.click('#prepare');
    await until(async () => /captions/.test(await text(page, '#pinfo')), 'the prompt is prepared');
    const r = await sized(page, '#prow');
    eq(await clip(page), SENTINEL, 'preparing copied nothing: the size is said first');
    assert(!/Prompt: \d+ characters/.test(await text(page, '#pinfo')), 'and what was found no longer counts characters after the fact: the row does, before');
    const box = await page.inputValue('#prompt');
    eq([r.chars, r.size], [String(codePoints(box)), sizeWords(codePoints(box), Number(r.tokens))], `the size is the size of the box "The prompt, as it will be copied" (${r.chars} characters)`);
    assert(r.warn === (Number(r.tokens) > 8000), 'and the sentence for a long prompt is there exactly when it is over 8,000 tokens');
    assert(await page.evaluate(() => !document.getElementById('prow').hidden && document.getElementById('prow').getClientRects().length > 0),
           'the row is drawn under what was found');
    await page.click('#prow .llmrow-copy');
    await page.waitForFunction(() => /^copied/.test(document.querySelector('#prow .llmrow-say').textContent));
    eq(await clip(page), box, 'the copy is exactly the box');
    assert(/^Parseh prompt · video-new|^# /.test(box.split('\n')[0]) || box.length > 1000, 'and it is the prompt');
    eq(await page.evaluate(() => ['copyagain'].map(i => !!document.getElementById(i))), [false], 'copy again is the row\'s button now');
    await look(page, 'add', {scope: '#prow'});
    // the prompt is built from the transcript, so a changed transcript takes prompt and row away
    await page.fill('#transcript', CAPTIONS + '0:13\nخداحافظ\n');
    eq(await page.evaluate(() => [document.getElementById('prow').hidden, document.getElementById('pshow').hidden]), [true, true], 'a changed transcript: the row and the prompt are gone');
    await page.click('#prepare');
    await until(async () => /captions/.test(await text(page, '#pinfo')), 'prepared again');
    const r2 = await sized(page, '#prow');
    assert(Number(r2.chars) > Number(r.chars), 'prepared again: a longer transcript, a longer prompt, and the new size');
    await ctx.close();
  });

  /* ---------------- tidy) the transcript editor's LLM panel ---------------- */
  await section('tidy', 'the transcript tidy: size, copy, and a word typed before the press is what is copied', async () => {
    const ctx = await context();
    const page = await addPage(ctx, 'tidy');
    await page.click('#subedit');
    await page.waitForSelector('.se-row');
    await page.click('.se-btn:has-text("or with an LLM")');
    await page.waitForSelector('.se-llm .llmrow');
    const r = await sized(page, '.se-llm');
    const caps = () => page.evaluate(() => [...document.querySelectorAll('.se-row')].map(r => ({start: r.querySelector('.se-at').value, text: r.querySelector('.se-text').value})));
    const asked = async () => {
      const c = await caps();
      const secs = t => { const m = /^(\d+):(\d+)/.exec(t); return +m[1] * 60 + +m[2]; };
      return (await (await ctx.request.post(`${B}/youtube/api/transcript`, {data: {lang: 'fa', prompt: true,
        captions: c.map(x => ({start: secs(x.start), text: x.text, chapter: null}))}})).json()).prompt;
    };
    const first = await asked();
    eq(r.chars, String(codePoints(first)), `the size is the size of the prompt the route makes (${r.chars} characters)`);
    await setClip(page, SENTINEL);
    assert((await clip(page)) === SENTINEL, 'opening the panel copied nothing');
    await page.click('.se-llm .llmrow-copy');
    await page.waitForFunction(() => /^copied/.test(document.querySelector('.se-llm .llmrow-say').textContent));
    eq(await clip(page), first, 'the copy is that prompt exactly');
    // a word typed into a caption, and the button pressed at once, before any measuring could have happened
    await page.fill('.se-row >> nth=0 >> .se-text', 'سلام دوست عزیز، حال شما چطور است؟');
    await page.click('.se-llm .llmrow-copy');
    await page.waitForFunction(() => /^copied/.test(document.querySelector('.se-llm .llmrow-say').textContent));
    const second = await clip(page);
    assert(second !== first && second.includes('دوست عزیز'), 'a word typed into a caption is in what the next press copies');
    eq(second, await asked(), 'and that is exactly what the route makes of the captions as they are now');
    const r2 = await until(async () => { const x = await rowOf(page, '.se-llm'); return x.chars === String(codePoints(second)) ? x : null; }, 'the size follows the caption');
    assert(!!r2, 'the size line has followed too');
    // the words around it are the panel's own
    assert(/^Copy the prompt into any model/.test(await text(page, '.se-llmnote')), 'the panel\'s own note stays');
    eq(await text(page, '.se-llm .llmrow-note'), '', 'the row adds no reminder of its own here');
    await look(page, 'tidy', {scope: '.se-llm'});
    await page.keyboard.press('Escape');
    await ctx.close();
  });

  /* ---------------- player) gloss with an LLM, in the video player ---------------- */
  async function player(ctx, name) {
    const page = await open(ctx, `${B}/youtube/v/fA6bK2mQ8sT/`, name, async p => {
      await p.waitForSelector('#segs .seg .fa .w');
      await p.waitForFunction(() => window.__yt && document.querySelector('#novid').hidden);
    });
    return page;
  }
  // a caption picked by a click on its time, once the page has stopped scrolling to it
  const clickCaption = async (page, i) => {
    await page.mouse.move(1, 1);
    await page.evaluate(i => document.querySelector(`#segs .seg[data-i="${i}"]`).scrollIntoView({block: 'center', behavior: 'instant'}), i);
    await sleep(250);
    const p = await page.evaluate(i => {
      const r = document.querySelector(`#segs .seg[data-i="${i}"] .lab`).getBoundingClientRect();
      return {x: r.left + r.width / 2, y: r.top + r.height / 2};
    }, i);
    await page.mouse.click(p.x, p.y);
  };
  await section('player', 'the player\'s "gloss with an LLM" panel: the size once a stretch is picked, before any press', async () => {
    const ctx = await context();
    const page = await player(ctx, 'player');
    await page.click('#rgn');
    await page.waitForFunction(() => !document.querySelector('#rgpanel').hidden);
    let r = await rowOf(page, '#rgpanel');
    eq([r.copy, r.copyOff, r.size, r.skill, r.menu], ['copy the prompt', true, '', false, false], 'with nothing picked the button is off and says nothing of a size');
    eq(await attr(page, '#rgcopy', 'title'), 'click a caption first: the stretch starts there', 'and its tooltip says what to do');
    await setClip(page, SENTINEL);
    await clickCaption(page, 1);
    await clickCaption(page, 3);
    eq(await page.evaluate(() => [document.querySelector('#rgfrom').textContent, document.querySelector('#rgto').textContent].map(s => s.replace(/,.*/, ''))),
       ['caption 1', 'caption 3'], 'two captions picked on the transcript');
    // every chunk of the stretch is glossed already: there is nothing to ask a chatbot for, so no size, and
    // no copy -- the server's own words say so
    await sleep(700);
    r = await rowOf(page, '#rgpanel');
    eq([r.chars, r.copyOff], [null, false], 'a stretch with nothing to gloss: no size is said, and the button is on');
    await page.click('#rgcopy');
    await until(async () => /nothing was copied/.test(await text(page, '#rgsum')), 'the panel says nothing was copied');
    eq(await clip(page), SENTINEL, 'and nothing was copied');
    // re-gloss ticked: every chunk is asked for, and its size is said BEFORE any press
    await page.check('#rgregloss');
    r = await sized(page, '#rgpanel');
    eq(await clip(page), SENTINEL, 're-gloss ticked: the size is said, and nothing was copied');
    await page.click('#rgcopy');
    await page.waitForFunction(() => /^copied/.test(document.querySelector('#rgcopysay').textContent));
    const prompt = await clip(page);
    assert(/^Parseh prompt|^# Gloss part of/.test(prompt.split('\n')[0]), 'the prompt is on the clipboard');
    eq(String(codePoints(prompt)), r.chars, `and the size said before is the size copied (${r.chars} characters)`);
    assert(/chunks?, \d+ to gloss/.test(await text(page, '#rgsum')), 'the panel still says what was made: its chunks and how many to gloss');
    // a box changed again: another prompt, and its own size
    await page.check('#rgperfield');
    await page.uncheck('#rgregloss');
    await sleep(700);
    eq((await rowOf(page, '#rgpanel')).chars, null, 'both boxes changed: everything is glossed and re-gloss is off, so nothing to ask for again');
    await page.check('#rgregloss');
    const r2 = await sized(page, '#rgpanel');
    eq(r2.say, '', 'a prompt made again: "copied" is not said of it');
    assert(r2.chars !== null, `the size is said again (${r2.chars} characters)`);
    // the panel shut: nothing is kept, and the size is gone until it is opened again
    await page.click('#rgclose');
    await page.click('#rgn');
    await page.waitForFunction(() => !document.querySelector('#rgpanel').hidden);
    await sized(page, '#rgpanel');
    await look(page, 'player-panel', {scope: '#rgpanel'});
    await ctx.close();
  });

  /* ---------------- reader) gloss with an LLM, in the book reader ---------------- */
  async function reader(ctx, folder, slug, name) {
    return open(ctx, `${B}/books/${folder}/${slug}/reader/`, name, async p => {
      await p.waitForFunction(() => typeof SRC !== 'undefined' && window.Parseh && document.querySelector('.sub'));
    });
  }
  await section('reader', 'the reader\'s region sheet: the size once a stretch is picked, before any press', async () => {
    const ctx = await context();
    const page = await reader(ctx, 'persian', 'mini-fa', 'reader');
    await page.click('#rgn');
    await page.waitForFunction(() => !document.querySelector('#rgbox').hidden);
    // the sheet's own way of starting on a sentence (rgOpen): picked, then the sheet told
    await page.evaluate(() => { const p = rgPick(); if (!p.get()) { p.set(0, 0); rgState(); } });
    await setClip(page, SENTINEL);
    // every chunk of the sentence is glossed already: nothing to ask for, so no size and no copy
    await sleep(700);
    let r = await rowOf(page, '#rgbox');
    eq([r.copy, r.copyOff, r.chars], ['copy the prompt', false, null], 'a sentence picked, all glossed: the button is on and no size is said');
    await page.click('#rgcopy');
    await until(async () => /nothing was copied/.test(await text(page, '#rgsum')), 'the sheet says nothing was copied');
    eq(await clip(page), SENTINEL, 'and nothing was copied');
    // re-gloss ticked: every chunk is asked for, and the size is said BEFORE any press
    await page.check('#rgregloss');
    r = await sized(page, '#rgbox');
    eq(await clip(page), SENTINEL, 're-gloss ticked: the size is said, and nothing was copied');
    await page.click('#rgcopy');
    await page.waitForFunction(() => /^copied/.test(document.querySelector('#rgcopysay').textContent));
    const prompt = await clip(page);
    eq(String(codePoints(prompt)), r.chars, `the size said before is the size copied (${r.chars} characters)`);
    assert(/chunks?, \d+ to gloss/.test(await text(page, '#rgsum')), 'the sheet still says what was made');
    // a box changed: another prompt
    await page.uncheck('#rgregloss');
    await sleep(700);
    eq((await rowOf(page, '#rgbox')).chars, null, 'a box changed: the size of the old prompt is gone, and the new one has nothing to ask for');
    await page.check('#rgregloss');
    const r2 = await sized(page, '#rgbox');
    assert(!!r2, `and the size is said again (${r2.chars} characters)`);
    // the sheet shut and opened: what was held is gone, and measured again
    await page.click('#rgclose');
    eq(await page.evaluate(() => [rgMade, document.querySelector('.llmrow-size').getAttribute('data-chars')]), [[], null], 'the sheet shut: nothing held');
    await page.click('#rgn');
    await sized(page, '#rgbox');
    await look(page, 'reader-sheet', {scope: '#rgbox'});
    await ctx.close();
  });

  /* ---------------- ask) Ask LLM in the sources sidebar ---------------- */
  const askLine = new RegExp(`^Parseh prompt · ask · (fa|it) → en · ${VERSION.replace(/\./g, '\\.')}\\n\\nTranslate the TARGET SENTENCE from \\w+ into English\\.\\n`);
  await section('ask', 'Ask LLM: the size before the copy, and a first line naming the prompt, the languages and the Parseh', async () => {
    eq(await (await fetch(`${B}/__version`)).json(), {version: VERSION}, 'the server tells a page which Parseh it is (GET /__version): what VERSION says');
    // in the reader
    let ctx = await context();
    let page = await reader(ctx, 'persian', 'mini-fa', 'ask reader');
    await page.evaluate(() => {
      const rows = [...document.querySelectorAll('.pass.p2 .row[data-c]')];
      openChunk(+rows[1].dataset.c, rows[1]);
      sideShow(true);
    });
    // THE THREE PARTS, in the shape the server-built prompts have, and word for word what it was but for the first line
    const OLD = ['Translate the TARGET SENTENCE from Persian into English.',
      'Return ONLY the translation. Do not include an explanation, notes, alternatives, labels, quotation marks, or Markdown formatting.',
      'Translate only the target sentence. Use the surrounding sentences, dictionary results, and Tatoeba examples only as context.',
      '', 'SENTENCES BEFORE:', '(none available)', '', 'TARGET SENTENCE:', 'x', '', 'SENTENCES AFTER:', '(none available)', '',
      'DICTIONARY RESULTS FOR THE CURRENT CHUNK:', '(none)', '', 'RELEVANT TATOEBA EXAMPLES:', '(none)'].join('\n');
    const shape = await page.evaluate(() => {
      const o = {sourceName: 'Persian', targetName: 'English', sentence: 'x', before: [], after: [], words: [], pairs: []};
      return {plain: ParsehLLM.prompt(o),
              numbered: ParsehLLM.prompt(Object.assign({}, o, {sourceCode: 'fa', targetCode: 'en', version: 'a9.9.9'})),
              added: ParsehLLM.parts(Object.assign({}, o, {instructions: 'Never gloss proper names.', instructionsKind: 'added'})),
              replaced: ParsehLLM.parts(Object.assign({}, o, {instructions: 'Just translate.', instructionsKind: 'replace', custom: 'mine'}))};
    });
    eq(shape.plain, 'Parseh prompt · ask · Persian → English\n\n' + OLD,
       'a caller that gives no codes and no number (a reader built before a0.4.2) still gets the prompt word for word as before, under its first line');
    eq(shape.numbered, 'Parseh prompt · ask · fa → en · a9.9.9\n\n' + OLD, 'with the codes and the number, the first line says which prompt, which languages and which Parseh');
    eq([shape.added.instructions, shape.added.contract, shape.added.data.split('\n')[0]],
       [OLD.split('\n').slice(0, 3).join('\n') + '\n\nNever gloss proper names.', '', 'SENTENCES BEFORE:'],
       'a person\'s instructions "added" go after Parseh\'s; nothing of Ask LLM\'s answer is read back, so there is no contract; the data is Parseh\'s');
    eq([shape.replaced.instructions, shape.replaced.version, shape.replaced.data.split('\n')[0]],
       ['Just translate.', 'Parseh prompt · ask · Persian → English · custom: mine', 'SENTENCES BEFORE:'],
       'and "in place of" stand alone, named on the first line, the data still Parseh\'s');
    let r = await sized(page, '#chside');
    eq([r.copy, r.skill, r.menu], ['Ask LLM', false, false], 'the reader\'s sidebar: the button is still called Ask LLM');
    eq(await text(page, '#chside .llmrow-note'), 'paste it into a chatbot, then paste its translation below.', 'and says where the answer goes');
    await setClip(page, SENTINEL);
    await page.click('#chside .llmrow-copy');
    await page.waitForFunction(() => /^copied/.test(document.querySelector('#chside .llmrow-say').textContent));
    let prompt = await clip(page);
    assert(askLine.test(prompt), `its first line names the prompt, the languages and this Parseh: ${JSON.stringify(prompt.split('\n')[0])}`);
    eq(String(codePoints(prompt)), r.chars, `the size said before is the size copied (${r.chars} characters)`);
    assert(prompt.includes('SENTENCES BEFORE:') && prompt.includes('TARGET SENTENCE:') && prompt.includes('RELEVANT TATOEBA EXAMPLES:') &&
           prompt.includes('An example.'), 'the instructions, then the data: the sentences, the dictionary rows and the corpus rows');
    assert(!/Parseh prompt.*\n\n[\s\S]*Parseh prompt/.test(prompt), 'the first line is there once');
    await look(page, 'ask-reader', {scope: '#chside'});
    await ctx.close();
    // in the player
    ctx = await context();
    page = await player(ctx, 'ask player');
    // a phrase hovered, its cloud's pencil pressed, the sources opened: as a person does
    await page.hover('#segs .seg[data-i="2"] .fa .w[data-j="0"]');
    await page.waitForFunction(() => !document.querySelector('#cloud').hidden);
    await page.click('#cloud .mkedit');
    await page.waitForSelector('#cloud .esrc');
    await page.click('#cloud .esrc');
    r = await sized(page, '#cloud .eside');
    eq(r.copy, 'Ask LLM', 'the player\'s sidebar: the same button');
    await setClip(page, SENTINEL);
    await page.click('#cloud .eside .llmrow-copy');
    await page.waitForFunction(() => /^copied/.test(document.querySelector('#cloud .eside .llmrow-say').textContent));
    prompt = await clip(page);
    assert(askLine.test(prompt), `the player's prompt: ${JSON.stringify(prompt.split('\n')[0])}`);
    eq(String(codePoints(prompt)), r.chars, `and its size said before is the size copied (${r.chars} characters)`);
    await look(page, 'ask-player', {scope: '#cloud .eside'});
    await ctx.close();
  });

  /* ---------------- storage) the pages work with localStorage refused ---------------- */
  await section('storage', 'localStorage refused: the pages draw the row and copy', async () => {
    const ctx = await context({storage: false});
    let page = await open(ctx, `${B}/studio/prompt`, 'storage studio', p => p.waitForSelector('#llm-row .llmrow'));
    await sized(page, '#llm-row');
    const box = await page.inputValue('#prompt-text');
    await page.click('#llm-row .llmrow-copy');
    await page.waitForFunction(() => /^copied/.test(document.querySelector('#llm-row .llmrow-say').textContent));
    eq(await clip(page), box, 'the studio\'s prompt page copies exactly its box');
    page = await addPage(ctx, 'storage add');
    await page.click('#prepare');
    await until(async () => /captions/.test(await text(page, '#pinfo')), 'prepared');
    await sized(page, '#prow');
    await page.click('#prow .llmrow-copy');
    await page.waitForFunction(() => /^copied/.test(document.querySelector('#prow .llmrow-say').textContent));
    eq(await clip(page), await page.inputValue('#prompt'), 'and so does the add page');
    await ctx.close();
  });

  /* ---------------- last) ---------------- */
  console.log('\nlast) what the pages and the hub said');
  eq(errors, [], 'no page threw, logged an error or had a request refused');
  const said = log.join('') + slog.join('');
  assert(!/Traceback/.test(said), 'no traceback in the hub\'s or the studio\'s log');
  const after = JSON.parse(await py(OWN, TMP));
  eq(after.leaks, [], 'nothing of this run\'s tree was remembered in the owner\'s config/digests.json or wheres.json');
  eq(after.digests, ownBefore.digests, 'the owner\'s config/, books/, youtube/videos/ and the fixtures are untouched');
} finally {
  if (browser) await browser.close();
  for (const p of [hub, studio]) { try { p && p.kill('SIGTERM'); } catch (_) {} }
  if (!Deno.env.get('PARSEH_KEEP')) await Deno.remove(TMP, {recursive: true}).catch(() => {});
}
console.log(`\nllmrow: ${passed} checks passed` + (failed.length ? `; sections that failed: ${failed.join(', ')}` : ''));
if (failed.length) Deno.exit(1);

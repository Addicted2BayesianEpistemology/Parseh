// SPDX-License-Identifier: GPL-3.0-or-later
import { chromium } from 'npm:playwright-core@1.52.0';
// Run: CHROME_BIN=/path/to/chrome PARSEH_PYTHON=/path/to/python3 deno run --allow-all tests/vocline_video.mjs
//      PARSEH_KEEP=1 keeps the temporary tree, to read what was written
//      VOCLINE_SHOTS=<dir> saves the clouds, the form and the phone's, per language
//
// A VIDEO'S VOCABULARY LINE IN THE BOOKS' MACROS, in the video player
// (youtube/lib/player.js, player.html, style.css) on the REAL hub: serve.main()
// over a temporary tree holding temporary copies of the fixture videos --
// Persian, Arabic, Japanese, Italian and Chinese -- each with a chunk whose
// vocabulary is a line in \dw \vb \bw \pw, set up through annwrite's own writer
// and the checker.  Nothing is stubbed but YouTube's iframe API and, for the
// sidebar (e), the dictionary's answer -- whose \vb is built by lib/verbs
// itself, so the page is handed the shape the server hands it.  Every action is
// the page's own: a phrase hovered, the ✎ in its cloud, the four buttons, the
// keys.
//
//  a) the cloud draws a macro line as the READER draws it: the same HTML
//     lib/tex2html.py's render_voc makes of the same line, byte for byte, in
//     five languages, two of them right to left; a line of plain text, in the
//     same videos, is byte for byte what the player as it was committed draws
//     (tests/fixtures/player_base/, the page as a whole).
//  b) the ✎ form's vocabulary row: the four buttons, each the kind of entry
//     with its skeleton small under it; pointing at one, or tabbing to it,
//     shows a line under the buttons -- on screen, and what the pointer would
//     hit -- saying what it is, the braces (a verb's the language's own three
//     forms) and an example drawn by the same renderer, and the same words are
//     its title; a press writes the skeleton at the cursor; the row reads as
//     what is typed, and says what is short of a line not finished.
//  c) save: another macro is refused in the checker's words and nothing is
//     written; a good line is written as typed, drawn in the cloud, and there
//     again when the form is reopened; a plain line is written as it always was.
//  d) a card made of the chunk carries the line as plain text in its notes,
//     never its source.
//  e) the sources sidebar's → vocabulary puts the books' entries: a \dw for a
//     word, the recipe's \vb (the video's colloquial present inside its
//     parenthesis, the chunk's own form named after it) for a verb, the whole
//     compound as one entry, parted from what is there by "; ".
//  f) the divide sheet cuts a chunk whose line holds macros entry by entry and
//     joins it back: the file is the file it was, byte for byte.
//  g) on a phone, in the mobile interface, the cloud draws the same line, inside
//     the screen.
//  h) last: no page threw, logged an error or had a request refused; the hub
//     printed no traceback; the owner's config/, books/ and youtube/videos/ and
//     the fixtures are as they were.
const root = await Deno.realPath(new URL('..', import.meta.url));
Deno.chdir(root);
const PY = Deno.env.get('PARSEH_PYTHON') || 'python3';
const TMP = await Deno.makeTempDir({prefix: 'parseh-vocline-video-'});
const SHOTS = Deno.env.get('VOCLINE_SHOTS') || '';
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
// What each language's chunk holds.  `line` is a line as a person or a model
// writes one; `plain` is one of the same video's chunks that keeps its plain
// text.  Every one passes the checker (it is written through annwrite).
const LINES = {
  fa: {folder: 'persian', vid: 'fA6bK2mQ8sT',
       line: '\\vb{دیدن}{didan}{بین}{bin}{دید}{did}{to see}; \\dw{سیب}{sib} apple, pl. \\pw{سیب‌ها}'},
  ar: {folder: 'arabic', vid: 'aR5nJ3xW7yZ',
       line: '\\vb{كتب}{kataba (I)}{يكتب}{yaktubu}{كتابة}{kitāba}{to write}; \\dw{كتاب}{kitāb} book, pl. \\pw{كتب}'},
  ja: {folder: 'japanese', vid: 'aB3dE5fG7hI',
       line: '\\vb{書く}{kaku}{書き}{kaki}{書いて}{kaite}{to write}; \\dw{今日}{kyō} today'},
  it: {folder: 'italian', vid: 'kL9mN1oP3qR',
       line: "\\vb{andare}{}{vado}{}{andato}{}{to go (aux. \\pw{essere}/\\pw{avere})}; \\dw{casa}{} house, \\textit{la casa}"},
  zh: {folder: 'chinese', vid: 'zH8cN2hA6nZ',
       line: '\\vb{睡觉}{shuìjiào}{睡了觉}{shuìle jiào}{}{}{to sleep}; \\dw{茶}{chá} tea'},
};
const BUILD = String.raw`
import json, os, shutil, sys
from pathlib import Path
REPO = Path(os.getcwd())
sys.path[:0] = ['youtube/lib', 'lib']
import annwrite, check_annotations as CA, languages, tex2html, texparse
import verbs as V
tmp = Path(sys.argv[1])
LINES = json.loads(sys.argv[2])
root = tmp / 'root'
for d in (root / 'youtube' / 'videos', tmp / 'library', tmp / 'exercises', tmp / 'anki',
          tmp / 'tray', tmp / 'config', tmp / 'nodict', tmp / 'nocorpus', tmp / 'nomt'):
    d.mkdir(parents=True, exist_ok=True)
os.symlink(str(REPO / 'lib'), str(root / 'lib'))
os.symlink(str(REPO / 'youtube' / 'lib'), str(root / 'youtube' / 'lib'))
out = {}
for key, spec in LINES.items():
    d = root / 'youtube' / 'videos' / spec['folder'] / spec['vid']
    shutil.copytree(str(REPO / 'tests/fixtures/videos' / spec['folder'] / spec['vid']), str(d))
    ann = annwrite.read(str(d))
    L = CA.video_language(str(d), annwrite._meta(str(d)), ann)
    # the first chunk of a caption after the first that holds a vocabulary line
    # is the one that gets the macro line; the next such chunk of ANOTHER
    # caption stays plain, to be compared with the player as it was
    picks = [(i, j) for i, sg in enumerate(ann['segments']) if i > 0
             for j, ch in enumerate(sg.get('chunks') or []) if ch.get('voc')]
    (si, ci), (pi, pj) = picks[0], next(p for p in picks if p[0] != picks[0][0])
    ann['segments'][si]['chunks'][ci]['voc'] = spec['line']
    annwrite.write(str(d), ann)
    errs, _w, _n = CA.check(str(d))
    tex2html.set_lang(L); texparse.set_lang(L)
    out[key] = {'dir': str(d), 'lang': L.as_json(), 'errors': errs, 'seg': si, 'chunk': ci,
                'plain': [pi, pj], 'line': spec['line'],
                'html': tex2html.render_voc(spec['line']), 'text': texparse.voc_text(spec['line'], L)}
# the two-word chunk of the Persian and the Italian video whose line is two entries, cut and joined in f)
for key, entries in (('fa', '\\dw{%s}{a} x; \\dw{%s}{b} y'), ('it', '\\dw{%s}{a} x; \\dw{%s}{b} y')):
    d = Path(out[key]['dir'])
    ann = annwrite.read(str(d))
    L = languages.get(out[key]['lang']['code'])
    at = next((i, j) for i, sg in enumerate(ann['segments']) if i != out[key]['seg']
              for j, ch in enumerate(sg.get('chunks') or [])
              if len(L.split_words(ch['fa'])) == 2 and [i, j] != out[key]['plain'])
    words = L.split_words(ann['segments'][at[0]]['chunks'][at[1]]['fa'])
    ann['segments'][at[0]]['chunks'][at[1]]['voc'] = entries % tuple(w.strip('.,?!') for w in words)
    annwrite.write(str(d), ann)
    out[key]['two'] = list(at)
    out[key]['two_line'] = ann['segments'][at[0]]['chunks'][at[1]]['voc']
    errs, _w, _n = CA.check(str(d))
    out[key]['errors'] += errs
# two books of the same fixtures, their readers built as every book's is built: nothing of this work is baked in
import subprocess
import books as booklib, texwrite
out['books'] = {}
for key, rel in (('fa', 'persian/mini-fa'), ('it', 'italian/mini-it')):
    d = root / 'books' / rel
    shutil.copytree(str(REPO / 'tests/fixtures/books' / rel), str(d), ignore=shutil.ignore_patterns('reader', '.reader-key'))
    r = subprocess.run([sys.executable, 'lib/tex2html.py', '--book', str(d)], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(r.stderr or r.stdout)
    rdr = d / 'reader'
    climb = os.path.relpath(str(REPO), str(rdr)).replace(os.sep, '/') + '/'
    for name in os.listdir(str(rdr)):
        if name.endswith('.html'):
            pth = rdr / name
            pth.write_text(pth.read_text(encoding='utf-8').replace(climb, '/'), encoding='utf-8')
    BL = booklib.Book(str(d)).lang
    cs = texwrite.read_chunks(str(d / 'ch1.tex'))
    n = next(i for i, c in enumerate(cs) if c['glossed'] and '\\vb{' in c['voc'] and '~' not in c['voc']
             and '--' not in c['voc'] and '\\%' not in c['voc'])
    tex2html.set_lang(BL); texparse.set_lang(BL)
    out['books'][key] = {'rel': rel, 'n': n, 'voc': cs[n]['voc'], 'text': texparse.voc_text(cs[n]['voc'], BL),
                         'lang': BL.as_json()}
# for the eye only: a book per language whose chunk holds the same line, to be drawn beside the video's cloud
out['shots'] = {}
if len(sys.argv) > 3 and sys.argv[3] == 'shots':
    rels = {'fa': 'persian/mini-fa', 'ar': 'arabic/mini-ar', 'ja': 'japanese/mini-ja', 'it': 'italian/mini-it', 'zh': 'chinese/mini-zh'}
    for key, rel in rels.items():
        folder, slug = rel.split('/')
        d = root / 'books' / folder / (slug + '-vl')
        shutil.copytree(str(REPO / 'tests/fixtures/books' / rel), str(d), ignore=shutil.ignore_patterns('reader', '.reader-key'))
        meta = json.loads((d / 'book.json').read_text(encoding='utf-8'))
        meta['slug'] = slug + '-vl'
        (d / 'book.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
        cs = texwrite.read_chunks(str(d / 'ch1.tex'))
        n = next(i for i, c in enumerate(cs) if i > 0 and c['glossed'] and c['voc'].strip())
        texwrite.edit_chunk(str(d / 'ch1.tex'), n, {'voc': LINES[key]['line']})
        r = subprocess.run([sys.executable, 'lib/tex2html.py', '--book', str(d)], capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(r.stderr or r.stdout)
        rdr = d / 'reader'
        climb = os.path.relpath(str(REPO), str(rdr)).replace(os.sep, '/') + '/'
        for name in os.listdir(str(rdr)):
            if name.endswith('.html'):
                pth = rdr / name
                pth.write_text(pth.read_text(encoding='utf-8').replace(climb, '/'), encoding='utf-8')
        out['shots'][key] = {'rel': folder + '/' + slug + '-vl', 'n': n}
# a line typed into the form and saved, and how the reader draws it
fa_L = languages.get('fa')
tex2html.set_lang(fa_L); texparse.set_lang(fa_L)
new = '\\vb{خواندن}{xāndan}{خوان}{xān}{خواند}{xānd}{to read}'
out['new'] = {'line': new, 'html': tex2html.render_voc(new), 'text': texparse.voc_text(new, fa_L)}
# what the sidebar is answered with: the \vb lib/verbs builds for a Persian verb the chunk holds a form of
fa = languages.get('fa')
vb = V.compose('fa', V.Parts(parts=[('گفتن', 'goftan'), ('گو', 'gu'), ('گفت', 'goft')], meaning='',
                             extras_video=['coll. ' + V.tl('می‌گم', 'mi-gam')]),
               word='گفتم', of_form='goftam', gloss='en', meaning='to say')
cp = V.compose('fa', V.Parts(parts=[('کردن', 'kardan'), ('کن', 'kon'), ('کرد', 'kard')], meaning='',
                             compound={'name': 'compound verb', 'whole': 'فکر کردن', 'whole_sound': 'fekr kardan',
                                       'mean': 'to think', 'word': 'فکر', 'word_sound': 'fekr'}),
               word='کردن', gloss='en')
out['hits'] = {'verb': vb, 'compound': cp}
print(json.dumps(out, ensure_ascii=False))
`;
// serve.main() over the temporary tree, every store in there (see
// tests/gloss_llm_video.mjs, whose harness this is)
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

// THE YOUTUBE PLAYER, as the page loads it from https://www.youtube.com/iframe_api
const FAKE_YT = `window.YT = {Player: function (el, o) {
  var t = 0, going = false, self = this;
  window.__yt = {seeks: [], t: function () { return t; }, going: function () { return going; }};
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
  setInterval(function () { if (going) t += 0.05; }, 50);
  setTimeout(function () { if (o.events && o.events.onReady) o.events.onReady({target: self}); }, 20);
}};
if (window.onYouTubeIframeAPIReady) window.onYouTubeIframeAPIReady();`;

const errors = [];
let hub = null, browser = null;
const log = [];
try {
  const B0 = JSON.parse((await py(BUILD, TMP, JSON.stringify(LINES), SHOTS ? 'shots' : '')).trim().split('\n').pop());
  for (const k of Object.keys(LINES))
    eq(B0[k].errors, [], `${k}: the copy as set up is one the checker has nothing against`);
  const port = freePort();
  hub = new Deno.Command(PY, {args: ['-c', SERVE, TMP, String(port)], cwd: root,
                              stdout: 'piped', stderr: 'piped'}).spawn();
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
  const newContext = async (opts = {}, mode = '') => {
    const ctx = await browser.newContext(Object.assign({viewport: {width: 1280, height: 900}, serviceWorkers: 'block'}, opts));
    await ctx.route(/^https?:\/\/(?!127\.0\.0\.1[:/])/, route => {
      if (route.request().url() === 'https://www.youtube.com/iframe_api')
        return route.fulfill({contentType: 'text/javascript', body: FAKE_YT});
      return route.abort();
    });
    if (mode) await ctx.addCookies([{name: 'parseh_mode', value: mode, url: B}]);
    return ctx;
  };
  const context = await newContext();
  await context.grantPermissions(['clipboard-read', 'clipboard-write'], {origin: B});

  /* ---------------- helpers over a page ---------------- */
  const optional = (status, method, path) => status === 404 && method === 'GET' &&
    (/^\/mt\/[^/]+\/meta\.json$/.test(path) || /^\/youtube\/videos\/[^/]+\/[^/]+\/waveform\.json$/.test(path) ||
     // a book with no narration has no times, and its reader asks all the same
     /^\/books\/[^/]+\/[^/]+\/timings\.json$/.test(path) ||
     path === '/favicon.ico');
  const allowed = new Set();
  const refused = [];
  let refusing = null;
  async function player(id, name, ctx = context, without = false) {
    const page = await ctx.newPage();
    page.on('pageerror', e => errors.push(name + ' pageerror: ' + e.message));
    page.on('response', r => {
      const u = new URL(r.url());
      if (u.host !== `127.0.0.1:${port}` || r.status() < 400) return;
      if (optional(r.status(), r.request().method(), u.pathname)) allowed.add(u.pathname.replace(/\/[^/]+\/[^/]+\/waveform/, '/…/waveform'));
      else if (refusing && refusing(r.status(), r.request().method(), u.pathname)) refused.push(name + ' ' + r.status() + ' ' + u.pathname);
      else errors.push(name + ' ' + r.status() + ' ' + r.request().method() + ' ' + u.pathname);
    });
    page.on('console', m => {
      if (m.type() !== 'error') return;
      const at = (m.location() || {}).url || '';
      if (/^Failed to load resource/.test(m.text()) && (at.startsWith(B) || !at.startsWith('http://127.0.0.1'))) return;
      errors.push(name + ' console: ' + m.text() + (at ? ' (' + at + ')' : ''));
    });
    page.on('requestfailed', r => {
      const u = new URL(r.url());
      if (without && /^\/lib\/voc(line|buttons)\.js$/.test(u.pathname)) return;   // refused on purpose, above
      if (u.host === `127.0.0.1:${port}`)
        errors.push(name + ' request failed: ' + r.method() + ' ' + u.pathname + ' (' + (r.failure() || {}).errorText + ')');
    });
    // a page from before the macros: the two scripts never arrive, and the player goes on without them
    if (without) for (const f of ['vocline.js', 'vocbuttons.js']) await page.route(`**/lib/${f}`, route => route.abort());
    await page.goto(`${B}/youtube/v/${id}/`);
    await page.waitForSelector('#segs .seg .fa .w');
    await page.waitForFunction(() => window.__yt && document.querySelector('#novid').hidden);
    return page;
  }
  const text = (page, sel) => page.evaluate(sel => { const e = document.querySelector(sel); return e ? e.textContent : null; }, sel);
  const W = (i, j) => `#segs .seg[data-i="${i}"] .fa .w[data-j="${j}"]`;
  const away = async page => {
    await page.mouse.move(1, 1);
    await page.waitForFunction(() => document.querySelector('#cloud').hidden ||
                                     document.querySelector('#cloud').classList.contains('editing'));
  };
  // a point a hand can reach on a phrase: the element the browser finds there is asked, not assumed
  async function point(page, i, j) {
    await page.evaluate(i => {
      const seg = document.querySelector(`#segs .seg[data-i="${i}"]`), r = seg.getBoundingClientRect();
      const top = document.querySelector('#playerwrap').getBoundingClientRect().bottom;
      scrollBy({top: r.top + r.height / 2 - (top + innerHeight) / 2, behavior: 'instant'});
    }, i);
    await sleep(120);
    const p = await page.evaluate(([i, j]) => {
      const seg = document.querySelector(`#segs .seg[data-i="${i}"]`), el = seg.querySelector(`.fa .w[data-j="${j}"]`);
      for (const r of el.getClientRects()) {
        const xs = [];
        for (let d = 0; d < r.width / 2; d += 3) xs.push(r.left + r.width / 2 + d, r.left + r.width / 2 - d);
        for (const y of [r.top + r.height / 2, r.top + 4, r.bottom - 4]) for (const x of xs) {
          if (x < 0 || y < 0 || x > innerWidth || y > innerHeight) continue;
          const hit = document.elementFromPoint(x, y);
          if (hit && hit.closest('.w') === el) return {x, y};
        }
      }
      return null;
    }, [i, j]);
    if (!p) throw Error(`FAIL: no reachable point on caption ${i} phrase ${j}`);
    return p;
  }
  async function hover(page, i, j) {
    for (let tries = 0; ; tries++) {
      await away(page);
      const p = await point(page, i, j);
      await page.mouse.move(p.x, p.y);
      try {
        await page.waitForFunction(sel => {
          const c = document.querySelector('#cloud'), w = document.querySelector(sel);
          return !c.hidden && w && w.classList.contains('hot');
        }, W(i, j), {timeout: 3000});
        return;
      } catch (e) { if (tries >= 2) throw e; }
    }
  }
  async function openEdit(page, i, j) {
    await hover(page, i, j);
    await page.click('#cloud .mkedit');
    await page.waitForFunction(w => {
      const c = document.querySelector('#cloud');
      return c.classList.contains('editing') && (c.querySelector('.ewhere') || {}).textContent === w;
    }, `segment ${i} chunk ${j}`);
  }
  async function closeEdit(page) {
    await page.keyboard.press('Escape');
    await page.waitForFunction(() => !document.querySelector('#cloud').classList.contains('editing'));
  }
  const cloudHTML = page => page.evaluate(() => document.querySelector('#cloud').innerHTML.replace(/<div class="arrow"[^>]*><\/div>/, ''));
  const vocOfCloud = page => page.evaluate(() => (document.querySelector('#cloud .voc') || {}).innerHTML);
  async function type(page, f, value) {
    await page.click(`#cloud .ef[data-f="${f}"]`);
    await page.keyboard.press('Control+A');
    await page.keyboard.press('Delete');
    if (value) await page.keyboard.insertText(value);
  }
  const annOf = async key => JSON.parse(await Deno.readTextFile(B0[key].dir + '/annotations.json'));
  const bytesOf = key => Deno.readFile(B0[key].dir + '/annotations.json');
  const shot = async (page, name, sel) => {
    if (!SHOTS) return;
    if (sel) await page.locator(sel).first().screenshot({path: `${SHOTS}/${name}.png`});
    else await page.screenshot({path: `${SHOTS}/${name}.png`});
  };
  const within = (box, w, h) => box && box.x >= 0 && box.y >= 0 && box.x + box.width <= w + 0.5 && box.y + box.height <= h + 0.5;

  /* ---------------- a) ---------------- */
  console.log('\na) the cloud draws a macro line as the reader does; a plain line as it always was');
  const pages = {};
  for (const [k, spec] of Object.entries(LINES)) {
    const page = pages[k] = await player(spec.vid, k);
    const b = B0[k];
    await hover(page, b.seg, b.chunk);
    const voc = await vocOfCloud(page);
    eq(voc, b.html, `${k}: the cloud's vocabulary is the reader's own HTML of the same line, byte for byte`);
    const txt = (await page.evaluate(() => document.querySelector('#cloud .voc').textContent)).replace(/\s+/g, ' ').trim();
    eq(txt, b.text, `${k}: and reads as the line's plain text, no backslash and no brace left`);
    eq(await page.evaluate(() => [...document.querySelectorAll('#cloud .voc bdi.v')].every(
         e => e.lang === document.documentElement.dataset.lang && e.getAttribute('dir') === (document.documentElement.dataset.dir === 'rtl' ? 'rtl' : 'ltr'))),
       true, `${k}: every word of the language isolated with its own lang and dir`);
    await shot(page, `cloud-${k}-1280`, '#cloud');
    await away(page);
  }
  // a chunk of the same videos whose line is plain text: its cloud is byte for byte what it is on a page
  // that never received the two scripts -- what draws a plain line is the code that always drew it
  // (tests/player_words.mjs holds it to the committed player as well)
  for (const k of Object.keys(LINES)) {
    const b = B0[k], now = pages[k];
    const was = await player(LINES[k].vid, k + ' (without the scripts)', context, true);
    await hover(now, b.plain[0], b.plain[1]);
    await hover(was, b.plain[0], b.plain[1]);
    const a = await cloudHTML(now), c = await cloudHTML(was);
    assert(/class="voc"/.test(a) && !/\\/.test(a), `${k}: the plain chunk has a vocabulary line`);
    eq(a, c, `${k}: a plain line's cloud is byte for byte what it is without the new scripts`);
    // and where they are missing a macro line is shown as it stands, no cloud fails to open
    await hover(was, b.seg, b.chunk);
    eq(await was.evaluate(() => document.querySelector('#cloud .voc').textContent.trim()), b.line,
       `${k}: a page without the scripts shows a macro line as its source, as an older Parseh does`);
    await was.close();
  }
  console.log(`\nvocline_video: ${passed} checks passed (so far)`);
  for (const p of Object.values(pages)) await p.close();

  /* ---------------- b) ---------------- */
  console.log('\nb) the ✎ form: four buttons that say what they write');
  // the row's buttons, and the line under them for one pointed at
  const helpOf = async (page, kind) => {
    await page.hover(`#cloud .evbtns [data-ins="${kind}"]`);
    await page.waitForFunction(k => {
      const h = document.querySelector('#vk-help'), b = document.querySelector(`#cloud .evbtns [data-ins="${k}"]`);
      return h && !h.hidden && b.classList.contains('vk-on');
    }, kind);
    return readHelp(page, kind);
  };
  const readHelp = (page, kind) => page.evaluate(k => {
    const h = document.querySelector('#vk-help'), r = h.getBoundingClientRect();
    const btn = document.querySelector(`#cloud .evbtns [data-ins="${k}"]`), br = btn.getBoundingClientRect();
    const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
    const drawn = h.querySelector('.vk-drawn');
    return {name: h.children[0].textContent, braces: h.children[1].textContent, hidden: h.hidden,
            look: drawn ? drawn.textContent.replace(/\s+/g, ' ').trim() : '', drawn: drawn ? drawn.innerHTML : '',
            src: (h.querySelector('.vk-src code') || {}).textContent || '',
            box: {x: r.x, y: r.y, width: r.width, height: r.height}, hit: !!hit && h.contains(hit),
            under: r.top >= br.bottom - 1, vw: innerWidth, vh: innerHeight, title: btn.title,
            lit: [...document.querySelectorAll('#cloud .evbtns [data-ins]')].filter(x => x.classList.contains('vk-on')).map(x => x.dataset.ins)};
  }, kind);
  const KINDS = [['dw', 'word', '\\dw{}{}'], ['vb', 'verb', '\\vb{…}'], ['bw', 'compound', '\\bw{}{}{}'], ['pw', 'word in a meaning', '\\pw{}']];
  {
    const k = 'fa', b = B0[k];
    const page = await player(LINES[k].vid, k + ' form');
    await openEdit(page, b.seg, b.chunk);
    eq(await page.evaluate(() => [...document.querySelectorAll('#cloud .evbtns [data-ins]')].map(
         x => [x.dataset.ins, x.querySelector('.vk-kind').textContent, x.querySelector('.vk-skel').textContent])),
       KINDS, `${k}: four buttons, each the kind of entry with its skeleton small under it`);
    eq(await page.evaluate(() => [document.querySelector('#cloud .evcap').textContent, document.querySelector('#cloud .evnow').innerHTML]),
       ['reads as', b.html], `${k}: the row reads as the line, drawn as the reader draws it`);
    eq(await page.evaluate(() => document.querySelector('#vk-help').hidden), true, `${k}: nothing under the buttons until one is pointed at`);
    const ex = await page.evaluate(() => ({ex: ParsehVocButtons.EXAMPLES, lang: window.YTFRANK.lang}));
    for (const [kind, name] of KINDS) {
      const h = await helpOf(page, kind);
      assert(h.name.startsWith(name + ' — '), `${k}: pointing at ${name} says which kind it is and what it is for: ${h.name}`);
      assert(/^in the braces/.test(h.braces), `${k}: ${name}: and what goes in the braces: ${h.braces}`);
      eq(h.src, ex.ex[k][kind], `${k}: ${name}: the example, in the language's own words`);
      eq(h.drawn, await page.evaluate(([e, l]) => ParsehVocline.render(e, l), [ex.ex[k][kind], ex.lang]),
         `${k}: ${name}: drawn by the renderer the cloud draws with`);
      eq(h.title.split('\n')[0], h.name, `${k}: ${name}: the button's title says the same, first line`);
      eq(h.title.split('\n')[1], h.braces, `${k}: ${name}: second line`);
      eq(h.title.split('\n')[2], 'looks like: ' + h.look, `${k}: ${name}: and the example as plain text`);
      assert(h.under && h.hit && !h.hidden && within(h.box, h.vw, h.vh), `${k}: ${name}: the line is under the buttons, on screen, and what a pointer there hits`);
      eq(h.lit, [kind], `${k}: ${name}: the button it is about is lit`);
    }
    const vb = await helpOf(page, 'vb');
    assert(vb.braces.includes('infinitive · present stem · past stem') && vb.braces.includes('‘pres.’ and ‘past’'),
           `${k}: a verb's says the language's own three forms and its two labels: ${vb.braces}`);
    await shot(page, `form-${k}-verb-1280`, '#cloud');
    // the line goes when the pointer has left, and the form has not grown
    await page.mouse.move(2, 2);
    await page.waitForFunction(() => document.querySelector('#vk-help').hidden);
    // the keyboard reaches them, and shows the same
    await page.focus('#cloud .ef[data-f="voc"]');
    const order = [];
    for (let n = 0; n < 4; n++) {
      await page.keyboard.press('Tab');
      order.push(await page.evaluate(() => document.activeElement.dataset.ins));
      const h = await readHelp(page, order[n]);
      assert(!h.hidden && h.name.startsWith(KINDS[n][1] + ' — ') && h.lit[0] === order[n], `${k}: Tab to ${KINDS[n][1]} shows its line`);
    }
    eq(order, ['dw', 'vb', 'bw', 'pw'], `${k}: Tab goes through the four buttons in order`);
    await page.keyboard.press('Shift+Tab');
    eq(await page.evaluate(() => document.activeElement.dataset.ins), 'bw', `${k}: and back`);
    // a press writes the skeleton at the cursor, the caret inside its first braces
    await type(page, 'voc', '');
    await page.click('#cloud .evbtns [data-ins="vb"]');
    eq(await page.evaluate(() => { const t = document.querySelector('#cloud .ef[data-f="voc"]'); return [t.value, t.selectionStart, t.selectionEnd, document.activeElement === t]; }),
       ['\\vb{}{}{}{}{}{}{}', 4, 4, true], `${k}: a press writes ${'\\vb{}{}{}{}{}{}{}'}, the caret in the first braces, the focus in the box`);
    eq(await text(page, '#cloud .evnow'), 'an entry with nothing in it yet', `${k}: and reads as an empty entry`);
    await page.keyboard.type('دیدن');
    eq(await page.evaluate(() => document.querySelector('#cloud .evnow bdi.v').textContent), 'دیدن', `${k}: typed into, the row reads as what is typed`);
    await type(page, 'voc', '\\dw{a}{');
    assert(/never closed/.test(await text(page, '#cloud .evnow .bad')), `${k}: a line not finished says so: ${await text(page, '#cloud .evnow .bad')}`);
    await type(page, 'voc', '\\dw{a}');
    assert(/needs 2 groups in braces .* and has 1/.test(await text(page, '#cloud .evnow .bad')), `${k}: and what it is short of: ${await text(page, '#cloud .evnow .bad')}`);
    await type(page, 'voc', B0.new.line);
    eq(await page.evaluate(() => document.querySelector('#cloud .evnow').innerHTML), B0.new.html, `${k}: a finished line is drawn as the reader draws it`);
    await type(page, 'voc', 'سلام salām hello (peace)');
    eq(await page.evaluate(() => document.querySelector('#cloud .evnow i')), null, `${k}: a plain line is drawn as the cloud draws a plain line, no italics of a romanisation`);
    await type(page, 'voc', '');
    eq(await text(page, '#cloud .evnow'), 'no vocabulary line yet', `${k}: nothing typed: nothing yet`);

    /* ---- c) ---- */
    console.log('\nc) saving');
    const before = await bytesOf(k);
    await type(page, 'voc', '\\dw{a}{b} \\foo{x}');
    refusing = (s, m, p) => p === '/youtube/api/edit';
    await page.click('#cloud .esave');
    await page.waitForFunction(() => /vocabulary macros/.test((document.querySelector('#cloud .cstat') || {}).textContent || ''));
    refusing = null;
    const said = await text(page, '#cloud .cstat');
    assert(/voc uses \\foo, which is not one of the books' vocabulary macros/.test(said) && /segment \d+ \(start [\d.:]+\) chunk \d+/.test(said),
           `${k}: another macro is refused in the checker's words, naming the phrase: ${said}`);
    assert(await page.evaluate(() => document.querySelector('#cloud .cstat').classList.contains('bad')), `${k}: as a refusal`);
    assert((await bytesOf(k)).every((x, i) => x === before[i]) && (await bytesOf(k)).length === before.length, `${k}: and nothing was written`);
    await type(page, 'voc', B0.new.line);
    await page.click('#cloud .esave');
    await page.waitForFunction(() => /saved/.test((document.querySelector('#cloud .cstat') || {}).textContent || ''));
    eq((await annOf(k)).segments[b.seg].chunks[b.chunk].voc, B0.new.line, `${k}: a good line is written as typed`);
    await closeEdit(page);
    await hover(page, b.seg, b.chunk);
    eq(await vocOfCloud(page), B0.new.html, `${k}: and the cloud draws it at once, as the reader would`);
    await away(page);
    await openEdit(page, b.seg, b.chunk);
    eq(await page.evaluate(() => [document.querySelector('#cloud .ef[data-f="voc"]').value, document.querySelector('#cloud .evnow').innerHTML]),
       [B0.new.line, B0.new.html], `${k}: reopened, the box holds it and the row reads it`);
    await type(page, 'voc', 'سیب sib apple · چند čand how much');
    await page.click('#cloud .esave');
    await page.waitForFunction(() => /saved/.test((document.querySelector('#cloud .cstat') || {}).textContent || ''));
    eq((await annOf(k)).segments[b.seg].chunks[b.chunk].voc, 'سیب sib apple · چند čand how much', `${k}: a plain line is written as it always was`);
    await closeEdit(page);
    await page.close();
  }
  // the four buttons in every other language: its own three forms, its own example, drawn
  for (const k of ['ar', 'ja', 'it', 'zh']) {
    const b = B0[k];
    const page = await player(LINES[k].vid, k + ' form');
    await openEdit(page, b.seg, b.chunk);
    eq(await page.evaluate(() => document.querySelector('#cloud .evnow').innerHTML), b.html, `${k}: the row reads as the line, as the reader draws it`);
    const ex = await page.evaluate(() => ({ex: ParsehVocButtons.EXAMPLES, lang: window.YTFRANK.lang}));
    for (const [kind, name] of KINDS) {
      const h = await helpOf(page, kind);
      eq(h.drawn, await page.evaluate(([e, l]) => ParsehVocline.render(e, l), [ex.ex[k][kind], ex.lang]), `${k}: ${name}: its example, drawn`);
      assert(h.hit && h.under && within(h.box, h.vw, h.vh), `${k}: ${name}: the line is under the buttons and on screen: ` + JSON.stringify({hit: h.hit, under: h.under, box: h.box, vw: h.vw, vh: h.vh}));
    }
    const vb = await helpOf(page, 'vb');
    assert(vb.braces.includes(b.lang.vb_forms.slice(0, 3).join(' · ')) && vb.braces.includes(`‘${b.lang.vb_labels[0]}’ and ‘${b.lang.vb_labels[1]}’`),
           `${k}: a verb's says this language's three forms (${b.lang.vb_forms.slice(0, 3).join(' · ')}) and its labels`);
    await shot(page, `form-${k}-verb-1280`, '#cloud');
    await closeEdit(page);
    await page.close();
  }

  /* ---------------- d) ---------------- */
  console.log('\nd) a card takes the line as plain text');
  {
    const k = 'ja', b = B0[k];
    const page = await player(LINES[k].vid, k + ' card');
    await hover(page, b.seg, b.chunk);
    await page.click('#cloud .mkcard');
    await page.waitForFunction(() => !document.querySelector('#anki').hidden);
    eq(await page.inputValue('#anotes'), b.text, `${k}: the card's notes are the line as text, never its source`);
    assert(!/[\\{}]/.test(await page.inputValue('#anotes')), `${k}: no backslash and no brace in them`);
    await page.click('#acancel');
    await hover(page, b.plain[0], b.plain[1]);
    const plain = (await annOf(k)).segments[b.plain[0]].chunks[b.plain[1]].voc;
    await page.click('#cloud .mkcard');
    await page.waitForFunction(() => !document.querySelector('#anki').hidden);
    eq(await page.inputValue('#anotes'), plain, `${k}: a plain line goes into the notes as it is`);
    await page.click('#acancel');
    await page.close();
  }

  /* ---------------- e) ---------------- */
  console.log('\ne) the sources sidebar puts the books\' entries');
  {
    const k = 'fa', b = B0[k], hits = B0.hits;
    const page = await player(LINES[k].vid, k + ' sidebar');
    const hit = (headword, translit, senses, vb) => Object.assign({headword, translit, pos: 'noun', senses}, vb ? {pos: 'verb', vb} : {});
    await page.route('**/youtube/api/lookup', route => {
      const q = route.request().postDataJSON();
      if (q.about) return route.fulfill({json: {ok: true, help: true, available: true, corpus_available: false, source: {source: 'a test dictionary'}}});
      return route.fulfill({json: {ok: true, pairs: [], pairs_more: false, pairs_offset: 0, words: [
        {word: q.text || 'x', tried: [q.text || 'x'], hits: [hit('گفتن', 'goftan', ['to say'], hits.verb),
                                                              hit('سیب', 'sib', ['apple']),
                                                              hit('کردن', 'kardan', ['to do'], hits.compound)]}]}});
    });
    await openEdit(page, b.plain[0], b.plain[1]);
    await page.click('#cloud .esrc');
    await page.waitForFunction(() => document.querySelectorAll('#cloud .esrcbody .srow').length >= 3);
    const rows = () => page.locator('#cloud .esrcbody .srow');
    const press = async (row, label) => { await rows().nth(row).locator('button', {hasText: label}).evaluate(x => x.click()); };
    const voc = () => page.inputValue('#cloud .ef[data-f="voc"]');
    await type(page, 'voc', '');
    await press(0, '→ vocabulary');
    eq(await voc(), hits.verb.tex_video, `${k}: a verb's → vocabulary puts the recipe's \\vb, the video's colloquial present inside its parenthesis and the chunk's own form after it`);
    assert(/\(coll\. \\pw\{می‌گم\} \\textit\{mi-gam\}\)\}; here \\pw\{گفتم\} \\textit\{goftam\}$/.test(await voc()), `${k}: which is ${await voc()}`);
    await press(1, '→ vocabulary');
    eq(await voc(), hits.verb.tex_video + '; \\dw{سیب}{sib} apple', `${k}: a word's puts a \\dw with its sound and sense, parted from the entry before by "; "`);
    eq(await page.evaluate(() => document.querySelector('#cloud .evnow').innerHTML.includes('<i>sib</i>')), true, `${k}: and the row reads it at once`);
    await type(page, 'voc', '');
    await press(2, 'compound verb');
    eq(await voc(), hits.compound.compound.tex_video, `${k}: a compound goes in as one entry, \\vb and \\bw run together`);
    assert(!(await voc()).includes('; ') && (await voc()).includes('}\\bw{'), `${k}: with nothing between them`);
    await type(page, 'voc', '');
    await page.click('#cloud .esave');
    await page.waitForFunction(() => /saved/.test((document.querySelector('#cloud .cstat') || {}).textContent || ''));
    await closeEdit(page);
    await page.close();
  }

  /* ---------------- f) ---------------- */
  console.log('\nf) cutting and joining a chunk whose line holds macros');
  // the sheet's button writes, says done, and becomes "close"
  const commit = async (page, k) => {
    await page.click('#dvdo');
    await page.waitForFunction(() => /^done/.test(document.querySelector('#dvstat').textContent), null, {timeout: 8000})
      .catch(async () => { throw Error(`${k}: the division was not written: ` + await text(page, '#dvstat')); });
    await page.click('#dvdo');
    await page.waitForFunction(() => document.querySelector('#dvbox').hidden);
  };
  for (const k of ['fa', 'it']) {
    const b = B0[k];
    const page = await player(LINES[k].vid, k + ' divide');
    const at = b.two, whole = await bytesOf(k);
    const line = (await annOf(k)).segments[at[0]].chunks[at[1]].voc;
    assert(/^\\dw\{[^}]+\}\{a\} x; \\dw\{[^}]+\}\{b\} y$/.test(line), `${k}: the chunk holds two entries, ${line}`);
    await openEdit(page, at[0], at[1]);
    await page.click('#cloud .edv[data-dv="split"]');
    await page.waitForFunction(() => !document.querySelector('#dvbox').hidden && !document.querySelector('#dvdo').disabled);
    const [e1, e2] = line.split('; ');
    eq(await page.evaluate(() => [...document.querySelectorAll('#dvpair .dvcol textarea[data-k="voc"]')].map(t => t.value)), [e1, e2],
       `${k}: the sheet proposes one entry to each half`);
    eq(await page.evaluate(() => [...document.querySelectorAll('#dvpair .dvchip .dvtxt')].map(t => t.textContent)), [e1, e2],
       `${k}: as two chips, the entries as they are written`);
    await page.click('#dvbox .dvchip button');            // the first entry crosses to the second half
    eq(await page.evaluate(() => [...document.querySelectorAll('#dvpair .dvcol textarea[data-k="voc"]')].map(t => t.value)), ['', e1 + '; ' + e2],
       `${k}: an entry sent across joins the other with "; ", as a book's line does`);
    await page.click('#dvbox .dvchip button');            // ...and back
    await commit(page, k);
    const cut = (await annOf(k)).segments[at[0]].chunks;
    eq([cut[at[1]].voc, cut[at[1] + 1].voc], [e1, e2], `${k}: cut: one entry to each chunk, on disk`);
    await hover(page, at[0], at[1] + 1);
    assert(/<i>b<\/i>/.test(await vocOfCloud(page)), `${k}: and the second is drawn`);
    await away(page);
    await openEdit(page, at[0], at[1]);
    await page.click('#cloud .edv[data-dv="next"]');
    await page.waitForFunction(() => !document.querySelector('#dvbox').hidden && !document.querySelector('#dvdo').disabled);
    await commit(page, k);
    const now = await bytesOf(k);
    assert(now.length === whole.length && now.every((x, i) => x === whole[i]), `${k}: joined again, annotations.json is the file it was, byte for byte`);
    await page.close();
  }

  /* ---------------- g) ---------------- */
  console.log('\ng) on a phone');
  {
    const ctx = await newContext({viewport: {width: 390, height: 844}, isMobile: true, hasTouch: true, deviceScaleFactor: 2}, 'mobile');
    for (const k of ['ar', 'ja']) {
      const b = B0[k];
      const page = await player(LINES[k].vid, k + ' phone', ctx);
      assert(await page.evaluate(() => document.documentElement.getAttribute('data-mode') === 'mobile'), `${k}: the mobile interface`);
      await page.tap(W(b.seg, b.chunk));
      await page.waitForFunction(() => !document.querySelector('#cloud').hidden);
      eq(await vocOfCloud(page), b.html, `${k}: the cloud a finger opens draws the same line, as the reader does`);
      assert(within(await page.evaluate(() => { const r = document.querySelector('#cloud').getBoundingClientRect(); return {x: r.x, y: r.y, width: r.width, height: r.height}; }), 390, 844),
             `${k}: and it is inside the screen`);
      await shot(page, `cloud-${k}-390`, '#cloud');
      await page.close();
    }
    await ctx.close();
  }

  /* ---------------- i) ---------------- */
  console.log('\ni) the book\'s chunk sheet, in a reader built as every book\'s is: no rebuild');
  for (const key of ['fa', 'it']) {
    const bk = B0.books[key];
    const url = `${B}/books/${bk.rel}/reader/`;
    const raw = await (await fetch(url)).text();
    assert(raw.includes('data-ins="dw"') && raw.includes('>\\dw{}{}</button>') && raw.includes('>\\vb{}{}{}{}{}{}{}</button>'),
           `${key}: the page as built holds the buttons it always did, each with its raw skeleton`);
    assert(!/vocbuttons|vocline/.test(raw), `${key}: and names neither new script: parseh.js brings them`);
    const page = await context.newPage();
    page.on('pageerror', e => errors.push(key + ' reader pageerror: ' + e.message));
    page.on('response', r => {
      const u = new URL(r.url());
      if (u.host === `127.0.0.1:${port}` && r.status() >= 400 && !optional(r.status(), r.request().method(), u.pathname))
        errors.push(key + ' reader ' + r.status() + ' ' + u.pathname);
    });
    page.on('console', m => { if (m.type() === 'error' && !/^Failed to load resource/.test(m.text())) errors.push(key + ' reader console: ' + m.text()); });
    await page.goto(url);
    await page.waitForSelector('#chins.vk-row', {state: 'attached'});
    assert(await page.evaluate(() => !!document.querySelector('script[src$="/vocline.js"]') && !!document.querySelector('script[src$="/vocbuttons.js"]')),
           `${key}: the two scripts were loaded by parseh.js from beside it`);
    await page.evaluate(n => openChunk(n, rowOf(n)), bk.n);
    await page.waitForFunction(() => !document.querySelector('#chbox').hidden);
    eq(await page.evaluate(() => [...document.querySelectorAll('#chins [data-ins]')].map(
         x => [x.dataset.ins, x.querySelector('.vk-kind').textContent, x.querySelector('.vk-skel').textContent])),
       KINDS, `${key}: four buttons in the order of the kinds, each the kind with its skeleton small under it`);
    const lang = bk.lang;
    for (const [kind, name] of KINDS) {
      await page.hover(`#chins [data-ins="${kind}"]`);
      await page.waitForFunction(k => { const h = document.querySelector('#vk-help'); return h && !h.hidden && document.querySelector(`#chins [data-ins="${k}"]`).classList.contains('vk-on'); }, kind);
      const h = await page.evaluate(k => {
        const el = document.querySelector('#vk-help'), r = el.getBoundingClientRect(), btn = document.querySelector(`#chins [data-ins="${k}"]`), br = btn.getBoundingClientRect();
        const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
        const drawn = el.querySelector('.vk-drawn');
        return {name: el.children[0].textContent, braces: el.children[1].textContent, drawn: drawn ? drawn.innerHTML : '',
                src: (el.querySelector('.vk-src code') || {}).textContent || '', title: btn.title,
                ok: !!hit && el.contains(hit) && r.top >= br.bottom - 1 && r.left >= 0 && r.bottom <= innerHeight && r.right <= innerWidth};
      }, kind);
      const ex = await page.evaluate(([k, c]) => ParsehVocButtons.EXAMPLES[c][k], [kind, lang.code]);
      eq(h.src, ex, `${key}: ${name}: the book's language's example`);
      eq(h.drawn, await page.evaluate(([e, l]) => ParsehVocline.render(e, l), [ex, lang]), `${key}: ${name}: drawn by the renderer the reader's own HTML is held to`);
      assert(h.name.startsWith(name + ' — ') && h.title.split('\n')[0] === h.name && h.title.split('\n')[1] === h.braces,
             `${key}: ${name}: the title says what the line says`);
      assert(h.ok, `${key}: ${name}: the line is under the buttons, on screen, and what a pointer there hits`);
      if (kind === 'vb')
        assert(h.braces.includes(lang.vb_forms.slice(0, 3).join(' · ')), `${key}: a verb's names ${lang.name}'s three forms: ${h.braces}`);
    }
    await shot(page, `sheet-${key}-verb-1280`, '#chbox');
    // the baked press still writes the skeleton, as it always did
    await page.click('#chvoc');
    await page.keyboard.press('Control+A');
    await page.keyboard.press('Delete');
    await page.click('#chins [data-ins="vb"]');
    eq(await page.evaluate(() => { const t = document.querySelector('#chvoc'); return [t.value, t.selectionStart]; }),
       ['\\vb{}{}{}{}{}{}{}', 4], `${key}: a press still writes the \\vb with its seven groups, the caret in the first`);
    // Tab reaches them
    await page.focus('#chvoc');
    await page.keyboard.press('Tab');
    eq(await page.evaluate(() => [document.activeElement.dataset.ins, document.querySelector('#vk-help').hidden]), ['dw', false], `${key}: Tab reaches the first, and its line opens`);
    await page.keyboard.press('Escape');
    // a card made from a chunk carries the rendered line as text, never its source
    await page.evaluate(() => closeChunk());
    const notes = await page.evaluate(n => {
      const w = document.querySelector(`.row[data-c="${n}"] .fa .wd, [data-c="${n}"] .wd`);
      w.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, altKey: true}));
      return null;
    }, bk.n);
    await page.waitForFunction(() => !document.querySelector('#anki').hidden);
    eq(await page.inputValue('#anotes'), bk.text, `${key}: the reader's card carries the line as text: ${bk.text}`);
    assert(!/[\\{}]/.test(await page.inputValue('#anotes')), `${key}: no backslash and no brace in it`);
    await page.close();
  }

  /* ---------------- shots ---------------- */
  if (SHOTS) {
    console.log('\nscreenshots for the eye, into ' + SHOTS);
    const theme = (page, t) => page.evaluate(t => Parseh.theme.set(t), t);
    const png = async loc => (await loc.screenshot()).toString('base64');
    // two element pictures side by side, captioned: the player's and the reader's rendering of the same line
    const sideBySide = async (name, left, right, note) => {
      const p = await context.newPage();
      await p.setContent(`<body style="margin:0;padding:14px;background:#888;font:13px sans-serif;color:#fff">
        <div style="display:flex;gap:18px;align-items:flex-start">
          <div><div style="margin-bottom:5px">the video player's cloud</div><img src="data:image/png;base64,${left}"></div>
          <div><div style="margin-bottom:5px">the book reader's chunk, same line</div><img src="data:image/png;base64,${right}"></div>
        </div><div style="margin-top:8px">${note}</div></body>`);
      await p.screenshot({path: `${SHOTS}/${name}.png`, fullPage: true});
      await p.close();
    };
    for (const key of Object.keys(LINES)) {
      const b = B0[key], sb = B0.shots[key];
      const rd = await context.newPage();
      await rd.goto(`${B}/books/${sb.rel}/reader/`);
      await rd.waitForSelector('.row[data-c] .gl .voc');
      const rowVoc = rd.locator(`.row[data-c="${sb.n}"] .gl .voc`);
      const rhtml = await rowVoc.evaluate(e => e.innerHTML);
      eq(rhtml, b.html, `${key}: the reader's own row holds the very HTML the video's cloud is byte for byte`);
      for (const t of ['light', 'dark']) {
        const page = await player(LINES[key].vid, key + ' shots');
        await theme(page, t); await theme(rd, t);
        await hover(page, b.seg, b.chunk);
        const left = await png(page.locator('#cloud'));
        await shot(page, `cloud-${key}-1280-${t}`, '#cloud');
        const right = await png(rowVoc);
        await sideBySide(`side-by-side-${key}-${t}`, left, right, `${key}: ${b.line.replace(/</g, '&lt;')}`);
        await page.close();
      }
      await rd.close();
    }
    // the ✎ form and the book's sheet, buttons pointed at, at 1280 and in a window 390 wide, light and dark
    for (const [w, h] of [[1280, 900], [390, 844]]) {
      const ctx = await newContext({viewport: {width: w, height: h}});
      for (const t of ['light', 'dark']) {
        for (const key of ['fa', 'it']) {
          const b = B0[key];
          const page = await player(LINES[key].vid, key + ' form shots', ctx);
          await theme(page, t);
          await openEdit(page, b.seg, b.chunk);
          for (const kind of ['vb', 'bw']) {
            await page.hover(`#cloud .evbtns [data-ins="${kind}"]`);
            await page.waitForFunction(() => !document.querySelector('#vk-help').hidden);
            await sleep(150);
            await page.screenshot({path: `${SHOTS}/form-${key}-${kind}-${w}-${t}.png`});
          }
          await page.close();
          const rd = await ctx.newPage();
          await rd.goto(`${B}/books/${B0.books[key].rel}/reader/`);
          await rd.waitForSelector('#chins.vk-row', {state: 'attached'});
          await theme(rd, t);
          await rd.evaluate(n => openChunk(n, rowOf(n)), B0.books[key].n);
          await rd.waitForFunction(() => !document.querySelector('#chbox').hidden);
          await rd.hover('#chins [data-ins="vb"]');
          await rd.waitForFunction(() => !document.querySelector('#vk-help').hidden);
          await sleep(150);
          await rd.screenshot({path: `${SHOTS}/sheet-${key}-vb-${w}-${t}.png`});
          await rd.close();
        }
      }
      await ctx.close();
    }
  }

  /* ---------------- h) ---------------- */
  console.log('\nh) what the pages and the hub said');
  console.log('  (refused as expected: ' + [...allowed].join(', ') + ')');
  assert(!errors.length, 'no page threw, logged an error or had a request refused: ' + errors.join('; '));
  assert(!/Traceback/.test(log.join('')), 'no traceback in the hub\'s log');
  const ownAfter = JSON.parse(await py(OWN, TMP));
  eq(ownAfter.leaks, [], 'nothing of this run\'s tree was remembered in the owner\'s config/digests.json or wheres.json');
  eq(ownAfter.digests, ownBefore.digests, 'the owner\'s config/, books/, youtube/videos/ and the fixtures are untouched');
  console.log(`\nvocline_video: ${passed} checks passed`);
} finally {
  if (errors.length) console.log('what the pages said:\n  ' + errors.join('\n  '));
  if (browser) await browser.close();
  if (hub) { try { hub.kill('SIGTERM'); await hub.status; } catch (_) {} }
  if (!Deno.env.get('PARSEH_KEEP')) await Deno.remove(TMP, {recursive: true}).catch(() => {});
  else console.log('kept ' + TMP);
}

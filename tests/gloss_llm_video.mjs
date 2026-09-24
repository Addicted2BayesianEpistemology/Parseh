// SPDX-License-Identifier: GPL-3.0-or-later
import { chromium } from 'npm:playwright-core@1.52.0';
// Run: CHROME_BIN=/path/to/chrome PARSEH_PYTHON=/path/to/python3 deno run --allow-all tests/gloss_llm_video.mjs
//      PARSEH_KEEP=1 keeps the temporary tree, to read what was written
//      GLOSS_LLM_PROMPTS=<dir> keeps every prompt the page put on the clipboard
//      GLOSS_LLM_SHOTS=<dir> saves the player with the panel open, per language
//
// DELETING A GLOSS, AND GLOSSING A STRETCH OF A VIDEO WITH AN LLM, in the
// video player (youtube/lib/player.js, player.html, style.css) on the REAL
// hub: serve.main() over a temporary tree holding temporary copies of the
// fixture videos -- Persian, Japanese and Italian -- with no dictionary, no
// corpus and no model installed (their three folders pointed at empty ones).
// Nothing is stubbed but YouTube, whose iframe API is answered by a script of
// this test: a player that plays nothing and writes down every seekTo it is
// asked, which is how "the video does not seek" is seen.  Every action is the
// page's own: a phrase hovered, the ✎ in its cloud, the form's buttons, the
// captions clicked where a hand can reach them, the panel's boxes and
// buttons; the prompt is READ OFF THE CLIPBOARD the page wrote it to, the
// answer is written here out of what the clipboard held and PASTED into the
// answer box with Ctrl+V; what lands is read back off annotations.json on
// disk, and off the page.
//
//  a) a chunk nobody has glossed, in a video with no dictionary installed and
//     no draft flag (and the Italian one with a "draft": true left in its
//     video.json, which changes nothing): a phrase all the same -- every
//     chunk of the target's text is one -- hoverable, its cloud saying
//     "nothing glossed yet" and offering ✎; the form opens with its boxes
//     empty and "delete gloss" greyed; one box filled alone is saved (half
//     glossed is legal by hand) and "delete gloss" takes it off again.
//  b) "delete gloss" in the ✎ form: one complete box emptied alone is refused
//     in the rule's words; "delete gloss" takes the gloss off the phrase (its
//     cloud, its boxes, the reading drawn over it), annotations.json loses
//     tr/voc/en/kana and keeps fa, col, free, words and note; the form,
//     closed and opened again, still offers "undo delete", which writes the
//     file back byte for byte.
//  c) the panel: "gloss with an LLM" pauses a playing video; a caption is
//     picked by a click on its line, another by a click on a phrase of it
//     (the later one first: the two are swapped); the video does NOT seek
//     while picking (a click with the panel shut does); the run is lit, and
//     the slots name each end by its number and m:ss; no caption line is
//     under the panel -- the transcript's column steps aside for it, at
//     1280, 900 and 1920 wide and beside the video (it covered the head of
//     every Persian caption); "copy the prompt" puts on the clipboard the
//     run's captions, the deleted chunk marked todo and every other chunk with
//     its gloss as the file has it.
//  d) delete, copy, answer with exactly the deleted gloss, paste, "fill from
//     the answer": the report says filled 1; the caption is drawn again where
//     it stands (a new line in its place, every other line the same element,
//     no reload, no scroll); annotations.json is byte for byte what it was
//     before the delete.
//  e) a HOSTILE answer, rewriting every chunk of the run (a note and a colour
//     too) and adding a caption from outside it: nothing glossed moves on the
//     page or on disk, the report lists every chunk as kept and the stray
//     caption as dropped.
//  f) a phrase marked free with its text changed in the ✎ form: the page's
//     own copy of the caption follows (a shift-click beside the phrases
//     copies the new text); a browser that refuses the clipboard is shown the
//     prompt to copy by hand; the prompt carries the changed text, never
//     transcript.txt's; and an answer to it lands.
//  g) re-gloss: the box as it stands when the answer is filled decides
//     (unticked by then, every gloss is kept); the first press writes nothing
//     and becomes "replace N glosses — press again"; left alone it disarms
//     after four seconds, and a change to the answer disarms it; the second
//     press replaces them (a blank chunk inside counts as filled).
// g2) per field: a chunk half glossed by hand is left whole per chunk, and
//     with "also fill the empty boxes…" ticked is asked for exactly its empty
//     boxes; the answer fills them and its change to the meaning is kept out.
//     The caption is picked by clicks on its time, which play nothing either;
//     the panel shut (Esc, or its ✕), a click on a caption plays again.
//  h) the divide sheet cuts a phrase that carries a note, and joins it back:
//     neither is refused (the page no longer sends the note), and the note
//     survives on disk and in the cloud.
//  i) last: no page threw, logged an error or had a request refused; the hub
//     printed no traceback; the Italian video.json's leftover flag is still
//     there untouched; the owner's config/, books/, youtube/videos/ and the
//     fixtures are as they were.
const root = await Deno.realPath(new URL('..', import.meta.url));
Deno.chdir(root);
const PY = Deno.env.get('PARSEH_PYTHON') || 'python3';
const TMP = await Deno.makeTempDir({prefix: 'parseh-gloss-llm-video-'});
const PROMPTS = Deno.env.get('GLOSS_LLM_PROMPTS') || '';
const SHOTS = Deno.env.get('GLOSS_LLM_SHOTS') || '';
let promptNo = 0;
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
const bytesEqual = (a, b) => a.length === b.length && a.every((x, i) => x === b[i]);
const GLOSS = ['kana', 'tr', 'voc', 'en'];

/* ---------------- the toolbox ---------------- */
// Copies of the fixture videos under <tmp>/root/youtube/videos, lib/ and
// youtube/lib/ linked into the tree.  Each copy is set up through annwrite's
// own reader and writer, so the file keeps the style annwrite writes it in
// and a chunk's keys stand in the order annwrite keeps them -- which is what
// lets "byte for byte" below mean what it says.  The fixtures themselves are
// only ever read.
const BUILD = String.raw`
import json, os, shutil, sys
from pathlib import Path
REPO = Path(os.getcwd())
sys.path[:0] = ['youtube/lib', 'lib']
import annwrite, check_annotations as CA
tmp = Path(sys.argv[1])
root = tmp / 'root'
for d in (root / 'youtube' / 'videos', tmp / 'library', tmp / 'exercises', tmp / 'anki',
          tmp / 'tray', tmp / 'config', tmp / 'nodict', tmp / 'nocorpus', tmp / 'nomt'):
    d.mkdir(parents=True, exist_ok=True)
os.symlink(str(REPO / 'lib'), str(root / 'lib'))
os.symlink(str(REPO / 'youtube' / 'lib'), str(root / 'youtube' / 'lib'))

def copy(folder, vid):
    d = root / 'youtube' / 'videos' / folder / vid
    shutil.copytree(str(REPO / 'tests/fixtures/videos' / folder / vid), str(d))
    return d

def edit(d, fn):
    ann = annwrite.read(str(d))
    fn(ann['segments'])
    # a caption given the transcript mark takes its text from its chunks,
    # as it does when the mark is ticked in the player (annwrite._retext)
    L = CA.video_language(str(d), annwrite._meta(str(d)), ann)
    for sg in ann['segments']:
        if sg.get('chunks'):
            annwrite._retext(sg, L)
    annwrite.write(str(d), ann)

def blank(ch):                      # a chunk nobody has glossed yet
    for f in ('kana', 'tr', 'voc', 'en'):
        ch.pop(f, None)

def put(ch, **kv):                  # fields added where annwrite keeps them
    o = annwrite._order(dict(ch, **kv))
    ch.clear()
    ch.update(o)

fa = copy('persian', 'fA6bK2mQ8sT')
def fa_(segs):
    blank(segs[4]['chunks'][1])                                   # a) چیز دیگری
    put(segs[2]['chunks'][1], note='just arrived, as fruit does', col='green', free=True)  # b) تازه آمده
    put(segs[1]['chunks'][2], note='the price question')          # h) سیب چند است
edit(fa, fa_)

ja = copy('japanese', 'aB3dE5fG7hI')
def ja_(segs):
    blank(segs[6]['chunks'][0])                                   # a) 少し
    put(segs[2]['chunks'][1], words='天気(てんき) が', note='weather talk', col='blue',
        free=True)                                                # b) 天気が
edit(ja, ja_)

it = copy('italian', 'kL9mN1oP3qR')
def it_(segs):
    blank(segs[6]['chunks'][1])                                   # a) e buona giornata
    put(segs[2]['chunks'][0], note='the price, again', col='orange', free=True)  # b) Quanto costano
edit(it, it_)
# a flag a draft once left behind: never read, never stripped
meta = json.loads((it / 'video.json').read_text(encoding='utf-8'))
meta['draft'] = True
(it / 'video.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

out = {}
for key, d in (('fa', fa), ('ja', ja), ('it', it)):
    # the checker's own verdict: an error, or a half-glossed chunk, is one
    # the test would be building on sand
    errs, _warns, _n = CA.check(str(d))
    ann = annwrite.read(str(d))
    L = CA.video_language(str(d), annwrite._meta(str(d)), ann)
    out[key] = {'dir': str(d), 'lang': L.as_json(), 'errors': errs}
print(json.dumps(out, ensure_ascii=False))
`;
// serve.main() over the temporary tree: every store it reads or writes is in
// there -- prefs and the network door (a suite once turned the owner's theme
// dark in the real config/), the offline door's two memories, the studio
// library, the decks, the Anki store and the clip tray -- and the three
// things that could answer for an unglossed phrase (a dictionary, a corpus,
// a model) are looked for in empty folders, so none of them is installed
const SERVE = String.raw`
import sys
from pathlib import Path
sys.path[:0] = ['markdown/exlex', 'markdown/app', 'youtube/lib', 'lib', '.']
tmp, port = Path(sys.argv[1]), sys.argv[2]
import prefs, network, offline
prefs.STORE = str(tmp / 'config' / 'prefs.json')
network.STORE = str(tmp / 'config' / 'network.json')
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
// the owner's own files, which nothing here may touch: their digests now,
// compared at the end -- all but the offline door's two memories in config/,
// which his own running hub may write to meanwhile, and which are searched
// for this run's tree instead
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

// THE YOUTUBE PLAYER, as the page loads it from https://www.youtube.com/iframe_api:
// the calls the page may make of it, a clock that runs while it "plays", and
// every seekTo written down in window.__yt.seeks
const FAKE_YT = `window.YT = {Player: function (el, o) {
  var t = 0, going = false, self = this;
  window.__yt = {seeks: [], t: function () { return t; }, going: function () { return going; },
                 pause: function () { going = false; }};
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
let hub = null, browser = null, current = null;
const log = [];
try {
  const B0 = JSON.parse((await py(BUILD, TMP)).trim().split('\n').pop());
  for (const k of Object.keys(B0))
    eq(B0[k].errors, [], `${k}: the copy as set up is one the checker has nothing against (no half-glossed chunk)`);
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
  const context = await browser.newContext({viewport: {width: 1280, height: 900}});
  // the clipboard, both ways: the page writes the prompt, the test reads it;
  // the test writes the answer, and Ctrl+V pastes it into the answer box
  await context.grantPermissions(['clipboard-read', 'clipboard-write'], {origin: B});
  // nothing leaves this machine but YouTube's API, which is this test's
  await context.route(/^https?:\/\/(?!127\.0\.0\.1[:/])/, route => {
    if (route.request().url() === 'https://www.youtube.com/iframe_api')
      return route.fulfill({contentType: 'text/javascript', body: FAKE_YT});
    return route.abort();
  });

  /* ---------------- helpers over a page ---------------- */
  // WHAT A PAGE MAY BE REFUSED, and nothing else.  A machine with no
  // translation model has no /mt/<pair>/meta.json nor /mt/engine/meta.json,
  // and a video whose sound was never drawn has no waveform.json: the player
  // asks for all three on load and does without them.  /favicon.ico is the
  // browser's own question, which the hub has never answered.
  const optional = (status, method, path) => status === 404 && method === 'GET' &&
    (/^\/mt\/[^/]+\/meta\.json$/.test(path) || /^\/youtube\/videos\/[^/]+\/[^/]+\/waveform\.json$/.test(path) ||
     path === '/favicon.ico');
  const allowed = new Set();
  // the one refusal asked for on purpose (b), let through by name while it is
  // being asked for, and counted
  let refusing = null;
  const refused = [];
  async function player(id, name) {
    const page = await context.newPage();
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
      // a refusal of ours is already counted by its response above; one of
      // YouTube's, aborted here, is the offline world the test lives in
      if (/^Failed to load resource/.test(m.text()) && (at.startsWith(B) || !at.startsWith('http://127.0.0.1'))) return;
      errors.push(name + ' console: ' + m.text() + (at ? ' (' + at + ')' : ''));
    });
    page.on('requestfailed', r => {
      const u = new URL(r.url());
      if (u.host === `127.0.0.1:${port}`)
        errors.push(name + ' request failed: ' + r.method() + ' ' + u.pathname + ' (' + (r.failure() || {}).errorText + ')');
    });
    await page.goto(`${B}/youtube/v/${id}/`);
    await page.waitForSelector('#segs .seg .fa .w');
    await page.waitForFunction(() => window.__yt && document.querySelector('#novid').hidden);
    // a mark on the page itself: a reload would take it away
    await page.evaluate(() => { window.__stay = 'never reloaded'; });
    return page;
  }
  const stayed = page => page.evaluate(() => window.__stay === 'never reloaded');
  const text = (page, sel) => page.evaluate(sel => { const e = document.querySelector(sel); return e ? e.textContent : null; }, sel);
  const clip = page => page.evaluate(() => navigator.clipboard.readText());
  const setClip = (page, s) => page.evaluate(s => navigator.clipboard.writeText(s), s);
  const SENTINEL = 'SENTINEL — not written by the page';
  const W = (i, j) => `#segs .seg[data-i="${i}"] .fa .w[data-j="${j}"]`;
  const away = async page => {
    await page.mouse.move(1, 1);
    await page.waitForFunction(() => document.querySelector('#cloud').hidden ||
                                     document.querySelector('#cloud').classList.contains('editing'));
  };
  // A POINT A HAND CAN REACH: inside the caption (on one of its phrases, or
  // on its line beside them), on screen, and not under the panel -- the
  // element the browser finds there is asked, not assumed
  async function point(page, i, what, j) {
    // scrolled to the middle of what the pinned video leaves of the window
    await page.evaluate(i => {
      const seg = document.querySelector(`#segs .seg[data-i="${i}"]`), r = seg.getBoundingClientRect();
      const top = document.querySelector('#playerwrap').getBoundingClientRect().bottom;
      scrollBy({top: r.top + r.height / 2 - (top + innerHeight) / 2, behavior: 'instant'});
    }, i);
    await sleep(120);
    const p = await page.evaluate(([i, what, j]) => {
      const seg = document.querySelector(`#segs .seg[data-i="${i}"]`);
      const panel = document.querySelector('#rgpanel');
      const pr = panel.hidden ? null : panel.getBoundingClientRect();
      const under = (x, y) => pr && x >= pr.left - 2 && x <= pr.right + 2 && y >= pr.top - 2 && y <= pr.bottom + 2;
      const els = what === 'phrase' ? [seg.querySelector(`.fa .w[data-j="${j}"]`)]
                : what === 'line' ? [seg.querySelector('.fa, .en-line')]
                : what === 'time' ? [seg.querySelector('.lab')] : [seg];
      for (const el of els) for (const r of el.getClientRects()) {
        const ys = [r.top + r.height / 2, r.top + 4, r.bottom - 4];
        // from the middle of the box outwards, three pixels at a time
        const xs = [];
        for (let d = 0; d < r.width / 2; d += 3) xs.push(r.left + r.width / 2 + d, r.left + r.width / 2 - d);
        for (const y of ys) for (const x of xs) {
          if (under(x, y) || x < 0 || y < 0 || x > innerWidth || y > innerHeight) continue;
          const hit = document.elementFromPoint(x, y);
          if (!hit || !seg.contains(hit)) continue;
          // a phrase: that very phrase; the line: its text, beside every phrase
          if (what === 'phrase' ? hit.closest('.w') !== els[0]
              : what === 'line' ? (hit.closest('.w') || !hit.closest('.fa, .en-line'))
              : what === 'time' ? hit.closest('.lab') !== els[0] : false) continue;
          return {x, y};
        }
      }
      return null;
    }, [i, what, j]);
    if (!p) throw Error(`FAIL: no reachable point on caption ${i} (${what})`);
    return p;
  }
  // a phrase hovered: the cloud open on it
  async function hover(page, i, j) {
    for (let tries = 0; ; tries++) {
      await away(page);
      const p = await point(page, i, 'phrase', j);
      await page.mouse.move(p.x, p.y);
      try {
        await page.waitForFunction(sel => {
          const c = document.querySelector('#cloud'), w = document.querySelector(sel);
          return !c.hidden && w && w.classList.contains('hot');
        }, W(i, j), {timeout: 3000});
        return;
      } catch (e) {
        if (tries >= 2) throw e;
      }
    }
  }
  // what the hover cloud says, as read
  const cloudSays = page => page.evaluate(() => {
    const c = document.querySelector('#cloud'), t = s => { const e = c.querySelector(s); return e ? e.textContent.trim() : null; };
    return {unwritten: t('.unwritten'), kana: t('.kana'), tr: t('.tr'), voc: t('.voc'), en: t('.en'), note: t('.note'),
            edit: !!c.querySelector('.mkedit')};
  });
  // the ✎ form open on a phrase, by its own button in the phrase's cloud
  async function openEdit(page, i, j) {
    await hover(page, i, j);
    await page.click('#cloud .mkedit');
    await page.waitForFunction(w => {
      const c = document.querySelector('#cloud');
      return c.classList.contains('editing') && (c.querySelector('.ewhere') || {}).textContent === w;
    }, `segment ${i} chunk ${j}`);
  }
  const boxes = page => page.evaluate(() => Object.fromEntries(
    [...document.querySelectorAll('#cloud .ef')].map(el => [el.dataset.f, el.value])));
  const delState = page => page.evaluate(() => {
    const d = document.querySelector('#cloud .edel'), u = document.querySelector('#cloud .eundo');
    const drawn = el => !!el && !el.hidden && el.getClientRects().length > 0;
    return {del: drawn(d), delOff: !!d && d.disabled, undo: drawn(u)};
  });
  const waitStat = (page, re) => page.waitForFunction(
    re => new RegExp(re).test((document.querySelector('#cloud .cstat') || {}).textContent || ''), re.source, {timeout: 20000});
  const stat = page => text(page, '#cloud .cstat');
  async function closeEdit(page) {
    await page.keyboard.press('Escape');
    await page.waitForFunction(() => !document.querySelector('#cloud').classList.contains('editing'));
  }
  // a box typed into as a hand does: everything in it selected, then typed over
  async function type(page, f, value) {
    await page.click(`#cloud .ef[data-f="${f}"]`);
    await page.keyboard.press('Control+A');
    await page.keyboard.press('Delete');
    if (value) await page.keyboard.insertText(value);
  }
  const annOf = async key => JSON.parse(await Deno.readTextFile(B0[key].dir + '/annotations.json'));
  const bytesOf = key => Deno.readFile(B0[key].dir + '/annotations.json');
  const unwritten = (ch, L) => !['tr', 'voc', 'en'].concat(L.reading ? ['kana'] : []).some(f => (ch[f] || '').trim());
  const glossOf = ch => Object.fromEntries(GLOSS.filter(f => ch[f]).map(f => [f, ch[f]]));
  // the ```json block the prompt ends with: the data, as the LLM receives it
  function dataOf(prompt) {
    const at = prompt.lastIndexOf('```json\n');
    if (at < 0) throw Error('the prompt has no ```json block');
    const body = prompt.slice(at + 8);
    return JSON.parse(body.slice(0, body.indexOf('\n```')));
  }
  const fence = doc => '```json\n' + JSON.stringify(doc, null, 2) + '\n```\n';
  // THE PANEL
  const slots = page => page.evaluate(() => [document.querySelector('#rgfrom').textContent,
                                             document.querySelector('#rgto').textContent]);
  // the captions lit, as drawn: the class, and the rail its style puts down the edge
  const lit = page => page.evaluate(() => [...document.querySelectorAll('#segs .seg')]
    .filter(el => el.classList.contains('rgpick') && /inset/.test(getComputedStyle(el).boxShadow))
    .map(el => +el.dataset.i));
  const litClass = page => page.evaluate(() => [...document.querySelectorAll('#segs .seg.rgpick')].map(el => +el.dataset.i));
  async function openPanel(page) {
    await away(page);
    await page.click('#rgn');
    await page.waitForFunction(() => !document.querySelector('#rgpanel').hidden);
  }
  async function pickAt(page, i, what, j) {
    await away(page);
    const p = await point(page, i, what, j);
    await page.mouse.click(p.x, p.y);
  }
  // a run a..b picked afresh: a "from" waiting for its "to" is given one
  // first, so that the next click starts again (the panel's own rule)
  async function pickRun(page, a, b, what = 'line') {
    const s = await slots(page);
    if (s[0] !== 'click a caption' && s[1] === 'click a caption') await pickAt(page, a, what);
    await pickAt(page, a, what);
    await pickAt(page, b, what);
  }
  async function copyPrompt(page) {
    await setClip(page, SENTINEL);
    await page.click('#rgcopy');
    await page.waitForFunction(() => {
      const t = document.querySelector('#rgsum').textContent;
      return t && !/^making the prompt…/.test(t) && !document.querySelector('#rgcopy').disabled;
    }, null, {timeout: 20000});
    const prompt = await clip(page);
    if (PROMPTS && prompt !== SENTINEL)
      await Deno.writeTextFile(`${PROMPTS}/${String(++promptNo).padStart(2, '0')}.md`, prompt);
    return {prompt, sum: await text(page, '#rgsum')};
  }
  // an answer PASTED: onto the clipboard, then Ctrl+V into the emptied box
  async function paste(page, answer) {
    await setClip(page, answer);
    await page.click('#rgans');
    await page.keyboard.press('Control+A');
    await page.keyboard.press('Delete');
    await page.keyboard.press('Control+V');
    await page.waitForFunction(a => document.querySelector('#rgans').value === a, answer, {timeout: 5000});
  }
  async function fill(page) {
    await page.click('#rgfill');
    await page.waitForFunction(() => {
      const t = document.querySelector('#rgreport').textContent;
      return t && !/^(reading the answer|replacing)…/.test(t) && !document.querySelector('#rgfill').disabled;
    }, null, {timeout: 30000});
    return report(page);
  }
  // the report as read: its tally, and each list under its heading
  const report = page => page.evaluate(() => {
    const box = document.querySelector('#rgreport'), out = {tally: '', lists: {}};
    const t = box.querySelector('.rgtally');
    out.tally = t ? t.textContent : box.textContent;
    let head = null;
    for (const el of box.children) {
      if (el.tagName === 'H5') head = el.textContent.replace(/ \(\d+\)$/, '').split(' — ')[0];
      else if (el.tagName === 'UL' && head) out.lists[head] = [...el.children].map(li => li.textContent);
    }
    return out;
  });
  const counts = rep => (rep.tally.match(/filled \d+ · completed \d+ · replaced \d+/) || [rep.tally.slice(0, 120)])[0];
  // every caption line marked, to tell afterwards which were drawn again
  const markLines = page => page.evaluate(() => {
    [...document.querySelectorAll('#segs .seg')].forEach(el => { el.__mark = 'line ' + el.dataset.i; });
    return scrollY;
  });
  const redrawn = page => page.evaluate(() => {
    const all = [...document.querySelectorAll('#segs .seg')];
    return {fresh: all.filter(el => !el.__mark).map(el => +el.dataset.i),
            order: all.every((el, k) => +el.dataset.i === k), y: scrollY};
  });
  // the caption lines the panel is drawn over -- and how many lines stand in
  // the panel's own band of the window at all, or "none" would prove nothing
  const underPanel = page => page.evaluate(() => {
    const p = document.querySelector('#rgpanel').getBoundingClientRect(), out = {under: [], band: 0};
    for (const el of document.querySelectorAll('#segs .seg')) {
      const r = el.querySelector('.fa, .en-line').getBoundingClientRect();
      if (r.bottom <= p.top || r.top >= p.bottom || r.bottom < 0 || r.top > innerHeight) continue;
      out.band++;
      if (r.right > p.left && r.left < p.right) out.under.push(+el.dataset.i);
    }
    return out;
  });
  async function shot(page, name) {
    if (!SHOTS) return;
    await Deno.mkdir(SHOTS, {recursive: true});
    await page.screenshot({path: `${SHOTS}/${name}.png`});
  }

  /* ---------------- the three videos ---------------- */
  // blank: a chunk the copy was given with no gloss (a); del: a complete
  // chunk with a note, a colour and the transcript mark, whose gloss is
  // deleted (b-d); one: a complete chunk whose `field` alone is emptied;
  // region: the run of captions for c-e; free: a chunk whose text is changed
  // (f); regloss: the run re-glossed (g); perfield: a complete chunk made half
  // glossed by hand, then completed per field (g2); divide: a chunk with a
  // note (h); widths: the panel's room looked at in other windows too
  const VIDS = [
    {key: 'fa', id: 'fA6bK2mQ8sT', name: 'Persian', blank: [4, 1], del: [2, 1], one: [3, 1, 'tr'],
     region: [1, 3], free: {at: [5, 0], to: 'نه مرسی،'}, regloss: [4, 5], perfield: [3, 0], divide: [1, 2],
     widths: true},
    {key: 'ja', id: 'aB3dE5fG7hI', name: 'Japanese', blank: [6, 0], del: [2, 1], one: [3, 1, 'kana'],
     region: [2, 4], free: {at: [5, 0], to: 'その本は'}, regloss: [5, 6], perfield: [7, 0], divide: [4, 2]},
    {key: 'it', id: 'kL9mN1oP3qR', name: 'Italian', blank: [6, 1], del: [2, 0], one: [3, 1, 'en'],
     region: [0, 2], free: {at: [5, 1], to: 'ciao'}, regloss: [3, 4], perfield: [5, 0], divide: [2, 0],
     flagLeft: true, shutBy: '✕'},
  ];
  const itMetaBefore = await Deno.readFile(B0.it.dir + '/video.json');

  for (const V of VIDS) {
    const L = B0[V.key].lang, key = V.key;
    console.log(`\n${V.name} (${key}): ${V.flagLeft ? 'a "draft": true left in its video.json' : 'no draft flag'}`);
    const page = current = await player(V.id, key);
    let ann = await annOf(key);

    /* ---------------- a) ---------------- */
    console.log(' a) a chunk nobody has glossed');
    eq(await page.evaluate(() => [!!window.YTFRANK.help, !!document.querySelector('#draft'),
                                  [...document.querySelectorAll('header *')].some(e => /^draft$/i.test(e.textContent.trim()))]),
       [false, false, false], `${key}: no dictionary, corpus or model is installed (and the page is told nothing about them), and no draft badge anywhere on the page`);
    if (V.flagLeft)
      assert(JSON.parse(await Deno.readTextFile(B0.it.dir + '/video.json')).draft === true,
             `${key}: (its video.json does carry "draft": true, which the page must ignore)`);
    // every chunk of the target's text is a phrase; only a chunk marked
    // plain, or a run holding none of a script language's script, is bare
    const want = ann.segments.map(sg => sg.plain ? null : sg.chunks.map(ch =>
      !(ch.plain || (L.chars && !new RegExp('[' + L.chars + ']').test(ch.fa)))));
    const drawn = await page.evaluate(() => [...document.querySelectorAll('#segs .seg')].map(el => {
      const fa = el.querySelector('.fa');
      return fa ? [...fa.children].map(c => c.classList.contains('w')) : null;
    }));
    eq(drawn, want, `${key}: every chunk not marked plain is drawn as a phrase, glossed or not (${want.flat().filter(Boolean).length} phrases)`);
    const [bi, bj] = V.blank, blankFa = ann.segments[bi].chunks[bj].fa;
    assert(unwritten(ann.segments[bi].chunks[bj], L), `${key}: segment ${bi} chunk ${bj} «${blankFa}» has no gloss in the file`);
    const setUp = await bytesOf(key);
    await hover(page, bi, bj);
    const c0 = await cloudSays(page);
    eq([c0.unwritten, c0.en, c0.edit], ['nothing glossed yet', null, true],
       `${key}: hovered, its cloud opens saying "nothing glossed yet", and offers ✎`);
    await page.click('#cloud .mkedit');
    await page.waitForFunction(() => document.querySelector('#cloud').classList.contains('editing'));
    eq(await text(page, '#cloud .ewhere'), `segment ${bi} chunk ${bj}`, `${key}: ✎ opens the form on it`);
    const b0 = await boxes(page);
    eq([b0.fa, ...GLOSS.filter(f => f in b0).map(f => b0[f])], [blankFa, ...GLOSS.filter(f => f in b0).map(() => '')],
       `${key}: its text in the first box, every gloss box empty`);
    eq(await delState(page), {del: true, delOff: true, undo: false}, `${key}: "delete gloss" is there, greyed: there is nothing to delete`);
    await type(page, 'en', 'a meaning typed alone');
    await page.click('#cloud .esave');
    await waitStat(page, /^saved ✓/);
    const halfCh = (await annOf(key)).segments[bi].chunks[bj];
    eq(glossOf(halfCh), {en: 'a meaning typed alone'}, `${key}: one box filled alone is saved -- half glossed, by hand, is legal`);
    eq(await delState(page), {del: true, delOff: false, undo: false}, `${key}: "delete gloss" is live now`);
    await page.click('#cloud .edel');
    await waitStat(page, /^gloss deleted/);
    assert(bytesEqual(await bytesOf(key), setUp), `${key}: "delete gloss" takes it off: annotations.json is byte for byte as set up`);
    await closeEdit(page);

    /* ---------------- b) ---------------- */
    console.log(' b) delete gloss, and undo');
    {
      const [oi, oj, of] = V.one, before1 = await bytesOf(key), was = refused.length;
      await openEdit(page, oi, oj);
      await type(page, of, '');
      refusing = (st, m, p) => st === 400 && m === 'POST' && p === '/youtube/api/edit';
      await page.click('#cloud .esave');
      await page.waitForFunction(() => (document.querySelector('#cloud .cstat') || {}).className === 'cstat bad', null, {timeout: 20000});
      refusing = null;
      eq(refused.length - was, 1, `${key}: the server refused that one save (400)`);
      const why = await stat(page);
      assert(/delete gloss/.test(why) && new RegExp(`\\b${of}\\b`).test(why),
             `${key}: emptying ${of} alone of a complete chunk is refused in the rule's words: ${JSON.stringify(why.slice(0, 110))}…`);
      assert(bytesEqual(await bytesOf(key), before1), `${key}: and nothing was written`);
      await closeEdit(page);
    }
    const [di, dj] = V.del, orig = ann.segments[di].chunks[dj], before = await bytesOf(key);
    assert(orig.note && orig.col && orig.free && orig.en && (!L.words || orig.words),
           `${key}: segment ${di} chunk ${dj} «${orig.fa}» is complete and carries a note, a colour, the transcript mark${L.words ? ' and a word line' : ''}`);
    const rtBefore = await page.evaluate(sel => document.querySelector(sel).querySelectorAll('rt').length, W(di, dj));
    await hover(page, di, dj);
    eq((await cloudSays(page)).en, orig.en, `${key}: its cloud shows its meaning, «${orig.en}»`);
    await page.click('#cloud .mkedit');
    await page.waitForFunction(() => document.querySelector('#cloud').classList.contains('editing'));
    const bx = await boxes(page);
    eq(Object.fromEntries(GLOSS.filter(f => f in bx).map(f => [f, bx[f]])),
       Object.fromEntries(GLOSS.filter(f => f in bx).map(f => [f, orig[f] || ''])), `${key}: the form's boxes hold its gloss`);
    eq(await delState(page), {del: true, delOff: false, undo: false}, `${key}: "delete gloss" is offered beside save, and no undo yet`);
    eq(await page.evaluate(() => [...document.querySelectorAll('#cloud .mkrow button')].slice(0, 3).map(b => b.className)),
       ['esave', 'edel', 'eundo'], `${key}: in the row, right after save`);
    eq(await page.evaluate(() => document.querySelector('#cloud .edel').title),
       "empty this chunk's transliteration, vocabulary and meaning (and its reading) — the text, the colour and the word line stay; undo delete puts the gloss back",
       `${key}: its title says what it does`);
    await page.click('#cloud .edel');
    await waitStat(page, /^gloss deleted/);
    const b1 = await boxes(page);
    eq(GLOSS.filter(f => f in b1).map(f => b1[f]), GLOSS.filter(f => f in b1).map(() => ''), `${key}: one click and the gloss boxes are empty`);
    eq(b1.fa, orig.fa, `${key}: the text box keeps the text`);
    eq(await delState(page), {del: true, delOff: true, undo: true}, `${key}: "delete gloss" greyed now, "undo delete" offered`);
    eq(await page.evaluate(() => document.querySelector('#cloud .eundo').title), 'write the deleted gloss back', `${key}: its title`);
    const now1 = (await annOf(key)).segments[di].chunks[dj];
    const expectDel = Object.fromEntries(Object.entries(orig).filter(([k]) => !GLOSS.includes(k)));
    eq(now1, expectDel, `${key}: annotations.json lost tr/voc/en/kana and kept ${Object.keys(expectDel).join(', ')} as they were`);
    {
      const a1 = await annOf(key), a0 = JSON.parse(td.decode(before));
      a0.segments[di].chunks[dj] = expectDel;
      eq(a1, a0, `${key}: and nothing else in the file changed`);
    }
    assert(await stayed(page), `${key}: without a reload`);
    await closeEdit(page);
    await hover(page, di, dj);
    const c1 = await cloudSays(page);
    eq([c1.unwritten, c1.en, c1.tr, c1.voc, c1.note], ['nothing glossed yet', null, null, null, orig.note],
       `${key}: hovered again, the phrase's cloud has no gloss left -- only its note`);
    // the readings over the text: a word line's are the line's own and stay
    // with it; a reading drawn from the kana goes with the gloss
    if (rtBefore)
      eq(await page.evaluate(sel => document.querySelector(sel).querySelectorAll('rt').length, W(di, dj)),
         orig.words ? rtBefore : 0,
         orig.words ? `${key}: the word line's readings stay drawn over its text (the line is no gloss)`
                    : `${key}: and the reading drawn over its text is gone with it`);
    await page.click('#cloud .mkedit');
    await page.waitForFunction(() => document.querySelector('#cloud').classList.contains('editing'));
    eq(await delState(page), {del: true, delOff: true, undo: true}, `${key}: the form closed and opened again still offers "undo delete" (kept in the page)`);
    await page.click('#cloud .eundo');
    await waitStat(page, /^gloss written back ✓/);
    assert(bytesEqual(await bytesOf(key), before), `${key}: "undo delete" writes it back: annotations.json byte for byte what it was`);
    const b2 = await boxes(page);
    eq(Object.fromEntries(GLOSS.filter(f => f in b2).map(f => [f, b2[f]])),
       Object.fromEntries(GLOSS.filter(f => f in b2).map(f => [f, orig[f] || ''])), `${key}: the boxes hold the gloss again`);
    eq(await delState(page), {del: true, delOff: false, undo: false}, `${key}: undo is spent, delete is live again`);
    await closeEdit(page);
    await hover(page, di, dj);
    eq((await cloudSays(page)).en, orig.en, `${key}: and the cloud shows the meaning again`);
    if (rtBefore)
      eq(await page.evaluate(sel => document.querySelector(sel).querySelectorAll('rt').length, W(di, dj)), rtBefore,
         `${key}: the reading over the text is back`);

    /* ---------------- c) ---------------- */
    console.log(' c) the panel: a run picked on the transcript, the prompt on the clipboard');
    // deleted again, for the prompt to ask for it
    await openEdit(page, di, dj);
    await page.click('#cloud .edel');
    await waitStat(page, /^gloss deleted/);
    await closeEdit(page);
    ann = await annOf(key);
    const [r0, r1] = V.region;
    // a click on a caption with the panel shut plays it from its start
    await pickAt(page, r0, 'line');
    await until(() => page.evaluate(() => window.__yt.seeks.length === 1 && window.__yt.going()), 'the click seeks');
    eq(await page.evaluate(() => window.__yt.seeks), [ann.segments[r0].start],
       `${key}: (with the panel shut, a click on caption ${r0} seeks to its start, ${ann.segments[r0].start} s, and plays)`);
    await openPanel(page);
    assert(await page.evaluate(() => !window.__yt.going()), `${key}: "gloss with an LLM" opens the panel, and the playing video pauses under it`);
    eq(await page.evaluate(() => [document.querySelector('#rgn').getAttribute('aria-expanded'),
                                  document.querySelector('#rghead').textContent]),
       ['true', 'gloss a stretch with an LLM'], `${key}: the panel, headed "gloss a stretch with an LLM"`);
    eq(await slots(page), ['click a caption', 'click a caption'], `${key}: its two slots wait for a caption`);
    const t0 = await page.evaluate(() => window.__yt.t());
    // the later caption first, by a click on one of its phrases
    const lastJ = ann.segments[r1].chunks ? ann.segments[r1].chunks.findIndex((ch, j) => want[r1] && want[r1][j]) : -1;
    if (lastJ >= 0) await pickAt(page, r1, 'phrase', lastJ); else await pickAt(page, r1, 'line');
    const clock = s => Math.floor(s / 60) + ':' + String(Math.floor(s % 60)).padStart(2, '0');
    const name = i => `caption ${i}, ${clock(ann.segments[i].start)}`;
    eq(await slots(page), [name(r1), 'click a caption'], `${key}: a click on ${lastJ >= 0 ? 'a phrase of ' : ''}caption ${r1} sets "from": ${JSON.stringify(name(r1))}`);
    eq(await litClass(page), [r1], `${key}: and lights that one caption`);
    await pickAt(page, r0, 'line');
    eq(await slots(page), [name(r0), name(r1)], `${key}: a click on caption ${r0}'s line, the earlier, and the two swap: from ${JSON.stringify(name(r0))}, to ${JSON.stringify(name(r1))}`);
    const run = Array.from({length: r1 - r0 + 1}, (_, k) => r0 + k);
    eq(await lit(page), run, `${key}: the run ${r0}–${r1} is lit on the transcript (the class, and the rail its style draws), nothing else`);
    eq(await page.evaluate(() => [window.__yt.seeks.length, window.__yt.going()]), [1, false],
       `${key}: the video did NOT seek while picking (no seekTo asked), and does not play`);
    eq(await page.evaluate(() => window.__yt.t()), t0, `${key}: it stands where it stood`);
    await shot(page, key + '-panel');
    eq(await page.evaluate(() => [
      document.querySelector('label.rgchk:has(#rgregloss)').textContent.trim(),
      document.querySelector('label.rgchk:has(#rgregloss) + .anote').textContent.trim(),
      document.querySelector('label.rgchk:has(#rgperfield)').textContent.trim(),
      document.querySelector('label.rgchk:has(#rgperfield) + .anote').textContent.trim(),
      document.querySelector('#rgcopy').textContent, document.querySelector('label[for="rgans"]').textContent,
      document.querySelector('#rgfill').textContent,
      document.querySelector('#rgregloss').checked, document.querySelector('#rgperfield').checked]),
      ['re-gloss what is already glossed', 'its glosses are not sent, and the answer replaces them',
       'also fill the empty boxes of partly glossed chunks', 'otherwise a chunk with any gloss is left exactly as it is',
       'copy the prompt', "the LLM's answer", 'fill from the answer', false, false],
      `${key}: the panel's two boxes (unticked), their notes and its buttons, in the words the guide uses`);
    // THE CAPTIONS STAY WHERE A HAND CAN REACH THEM: none under the panel
    {
      const u = await underPanel(page);
      assert(u.band >= 2 && !u.under.length,
             `${key}: no caption line is under the panel (${u.band} lines stand in its band of the window, none under it)`);
      if (V.widths) {
        for (const [w, h] of [[900, 800], [1920, 1000]]) {
          await page.setViewportSize({width: w, height: h});
          await sleep(200);
          const v = await underPanel(page);
          const m = await page.evaluate(() => { const r = document.querySelector('main').getBoundingClientRect();
                                                return [Math.round(r.left), Math.round(document.documentElement.clientWidth - r.right)]; });
          assert(v.band >= 1 && !v.under.length, `${key}: at ${w}x${h} too (${v.band} lines in its band, none under it)`);
          if (w === 1920) assert(Math.abs(m[0] - m[1]) <= 2, `${key}: where there is room the column stays centred (${m[0]}px | ${m[1]}px)`);
        }
        await page.setViewportSize({width: 1280, height: 900});
        await page.click('#sbs');
        await page.waitForFunction(() => document.body.classList.contains('sbs'));
        await sleep(200);
        const v = await underPanel(page);
        assert(v.band >= 1 && !v.under.length, `${key}: and with the video beside the transcript (${v.band} lines in its band, none under it)`);
        await page.click('#sbs');
        await page.waitForFunction(() => !document.body.classList.contains('sbs'));
        eq(await slots(page), [name(r0), name(r1)], `${key}: (the picks are as they were through all that)`);
      }
    }
    let {prompt, sum} = await copyPrompt(page);
    assert(prompt !== SENTINEL && prompt.length > 1000, `${key}: "copy the prompt" put the prompt on the clipboard (${prompt.length} characters)`);
    assert(new RegExp(`^# Gloss part of an? ${V.name} video, in English, for Parseh`).test(prompt),
           `${key}: the prompt is for ${/^[AEIOU]/.test(V.name) ? 'an' : 'a'} ${V.name} video glossed in English: ${JSON.stringify(prompt.split('\n')[0])}`);
    let data = dataOf(prompt);
    eq(data.captions.map(c => c.i), run, `${key}: the clipboard's data holds the captions of the run, ${r0} to ${r1}`);
    eq(data.captions.map(c => c.start), run.map(i => ann.segments[i].start), `${key}: each with its start`);
    const sentFa = data.captions.map(c => c.plain ? {plain: c.text} : c.chunks.map(ch => ch.fa));
    eq(sentFa, run.map(i => ann.segments[i].plain ? {plain: ann.segments[i].text} : ann.segments[i].chunks.map(ch => ch.fa)),
       `${key}: every chunk of them, divided as annotations.json divides them`);
    const todos = data.captions.flatMap(c => (c.chunks || []).map((ch, j) => [c.i, j, ch]).filter(x => x[2].todo));
    eq(todos.map(x => [x[0], x[1], x[2].todo]), [[di, dj, true]], `${key}: the deleted chunk, and it alone, is marked "todo": true`);
    eq(Object.keys(todos[0][2]).filter(k => GLOSS.includes(k)), [], `${key}: carrying no gloss`);
    if (orig.words) eq(todos[0][2].words, orig.words, `${key}: with its word line, read-only`);
    let glossedSent = 0, plainSent = 0;
    const others = data.captions.every(c => (c.chunks || []).every((ch, j) => {
      if (c.i === di && j === dj) return true;
      const f = ann.segments[c.i].chunks[j];
      if (f.plain) { plainSent++; return ch.plain === true && !GLOSS.some(g => g in ch); }
      glossedSent++;
      return !ch.todo && GLOSS.every(g => (ch[g] || '') === ((g !== 'kana' || L.reading) ? (f[g] || '') : ''));
    }));
    assert(others, `${key}: the ${glossedSent} other chunks are sent with their gloss exactly as the file has it, not todo${plainSent ? `; the ${plainSent} plain one marked plain, with none` : ''}`);
    const nChunks = data.captions.reduce((n, c) => n + (c.chunks || []).length, 0);
    assert(sum.includes(nChunks + ' chunks, 1 to gloss, ' + glossedSent + ' glossed sent as context') && /on the clipboard/.test(sum),
           `${key}: the panel says what it made: ${JSON.stringify(sum.split('\n').slice(0, 2).join(' | '))}`);

    /* ---------------- d) ---------------- */
    console.log(' d) the deleted gloss, answered and filled');
    const answer = structuredClone(data);
    const mine = answer.captions.find(c => c.i === di).chunks[dj];
    delete mine.todo;
    Object.assign(mine, glossOf(orig));
    await paste(page, 'Here it is:\n\n' + fence(answer));
    assert(true, `${key}: the answer is pasted into "the LLM's answer" with Ctrl+V`);
    const y0 = await markLines(page);
    let rep = await fill(page);
    eq(counts(rep), 'filled 1 · completed 0 · replaced 0', `${key}: "fill from the answer" reports filled 1`);
    eq(rep.lists, {}, `${key}: nothing kept, dropped or unanswered`);
    assert(bytesEqual(await bytesOf(key), before), `${key}: annotations.json is byte for byte what it was before the delete`);
    const rd = await redrawn(page);
    eq([rd.fresh, rd.order, rd.y], [[di], true, y0], `${key}: caption ${di} is drawn again in its place -- a new line where it stood, every other line the very same element, the page not scrolled`);
    assert(await stayed(page), `${key}: with no reload`);
    eq(await lit(page), run, `${key}: the run still lit on the new line as on the others`);
    await hover(page, di, dj);
    eq((await cloudSays(page)).en, orig.en, `${key}: its phrase's cloud shows the meaning again`);
    if (rtBefore)
      eq(await page.evaluate(sel => document.querySelector(sel).querySelectorAll('rt').length, W(di, dj)), rtBefore,
         `${key}: and the reading drawn over its text`);

    /* ---------------- e) ---------------- */
    console.log(' e) a hostile answer');
    const beforeHostile = await bytesOf(key);
    ann = await annOf(key);
    ({prompt, sum} = await copyPrompt(page));
    eq(prompt, SENTINEL, `${key}: with nothing left to gloss, "copy the prompt" copies nothing`);
    assert(/0 to gloss/.test(sum) && /nothing was copied/.test(sum), `${key}: and says so: ${JSON.stringify(sum.split('\n').slice(0, 3).join(' | '))}`);
    const hostile = structuredClone(data);
    let rewritten = 0;
    for (const c of hostile.captions) for (const ch of c.chunks || []) {
      delete ch.todo;
      ch.en = 'REWRITTEN ' + (ch.en || ch.fa);
      if (!ch.plain) {
        ch.tr = 'rewritten'; ch.voc = 'rewritten vocabulary';
        if (L.reading) ch.kana = 'かきかえ';
        ch.note = 'a note an LLM wrote'; ch.col = 'red';
      }
      rewritten++;
    }
    // and a caption from outside the run
    const outside = r1 + 1 < ann.segments.length ? r1 + 1 : r0 - 1;
    hostile.captions.push({i: outside, start: ann.segments[outside].start,
                           chunks: ann.segments[outside].chunks.map(ch => ({fa: ch.fa, en: 'STRAY'}))});
    await paste(page, fence(hostile));
    await markLines(page);
    rep = await fill(page);
    eq(counts(rep), 'filled 0 · completed 0 · replaced 0', `${key}: the hostile answer writes nothing`);
    assert(/nothing was written/.test(rep.tally), `${key}: and the report says so`);
    const kept = rep.lists['kept'] || [];
    eq(kept.length, rewritten, `${key}: the report lists every one of the ${rewritten} chunks it rewrote as kept`);
    assert(kept.every(t => /already glossed -- left as it is|plain text, never glossed/.test(t)),
           `${key}: each saying why: ${JSON.stringify(kept[0])}`);
    const dropped = rep.lists['dropped'] || [];
    assert(dropped.length === 1 && dropped[0].startsWith(`caption ${outside} `),
           `${key}: and the caption from outside the run as dropped: ${JSON.stringify(dropped[0])}`);
    assert(bytesEqual(await bytesOf(key), beforeHostile), `${key}: on disk nothing moved -- annotations.json byte for byte`);
    eq((await redrawn(page)).fresh, [], `${key}: on the page no caption was drawn again`);
    const shownNow = [];
    for (const i of run) for (const [j, ch] of (ann.segments[i].chunks || []).entries())
      if (want[i] && want[i][j]) { await hover(page, i, j); shownNow.push((await cloudSays(page)).en === ch.en); }
    assert(shownNow.length && shownNow.every(Boolean), `${key}: every phrase of the run still shows the meaning it had (${shownNow.length} hovered)`);
    await away(page);

    /* ---------------- f) ---------------- */
    console.log(' f) a phrase marked free, its text changed');
    {
      const [fi, fj] = V.free.at;
      ann = await annOf(key);
      const was = ann.segments[fi].chunks[fj], wasText = ann.segments[fi].text;
      const transcript = await Deno.readTextFile(B0[key].dir + '/transcript.txt');
      assert(transcript.includes(wasText), `${key}: caption ${fi} is «${wasText}», as transcript.txt has it`);
      await openEdit(page, fi, fj);
      await type(page, 'fa', V.free.to);
      await page.click('#cloud .efree');
      await page.click('#cloud .esave');
      await waitStat(page, /^saved ✓/);
      ann = await annOf(key);
      const newText = ann.segments[fi].chunks.map(ch => ch.fa).join(L.word_sep);
      eq([ann.segments[fi].chunks[fj].fa, ann.segments[fi].chunks[fj].free, ann.segments[fi].text],
         [V.free.to, true, newText], `${key}: the phrase is marked free, its text «${V.free.to}», its caption's text «${newText}» on disk`);
      await closeEdit(page);
      // a shift-click on the caption's line beside its phrases copies the caption
      await away(page);
      await setClip(page, SENTINEL);
      const p = await point(page, fi, 'line');
      await page.keyboard.down('Shift');
      await page.mouse.click(p.x, p.y);
      await page.keyboard.up('Shift');
      await until(async () => (await clip(page)) !== SENTINEL, 'the shift-click copies');
      eq(await clip(page), newText.replace(/\s+/g, ' ').trim(),
         `${key}: a shift-click beside the phrases copies the caption as it is now, not as it was loaded`);
      // the prompt: its gloss deleted, the caption picked alone
      await openEdit(page, fi, fj);
      await page.click('#cloud .edel');
      await waitStat(page, /^gloss deleted/);
      await closeEdit(page);
      await pickAt(page, fi, 'line');
      eq(await slots(page), [name(fi), 'click a caption'], `${key}: a third click starts again: caption ${fi} alone`);
      eq(await lit(page), [fi], `${key}: lit alone`);
      // a browser that will not put it on the clipboard: the prompt is shown
      await setClip(page, SENTINEL);
      await page.evaluate(() => {
        window.__write = navigator.clipboard.writeText;
        navigator.clipboard.writeText = () => Promise.reject(new DOMException('denied', 'NotAllowedError'));
        window.__exec = document.execCommand;
        document.execCommand = () => false;
      });
      await page.click('#rgcopy');
      await page.waitForFunction(() => !document.querySelector('#rgpromptrow').hidden, null, {timeout: 20000});
      const byHand = await page.evaluate(() => document.querySelector('#rgprompt').value);
      assert(/^# Gloss part of/.test(byHand) && /the prompt is below/.test(await text(page, '#rgsum')) && (await clip(page)) === SENTINEL,
             `${key}: a browser that refuses the clipboard: the prompt is shown in the panel to copy by hand, and the panel says so`);
      await page.evaluate(() => { navigator.clipboard.writeText = window.__write; document.execCommand = window.__exec; });
      ({prompt, sum} = await copyPrompt(page));
      eq(prompt, byHand, `${key}: the next press copies it, the same prompt`);
      eq(await page.evaluate(() => document.querySelector('#rgpromptrow').hidden), true, `${key}: and the hand-copy box is put away`);
      data = dataOf(prompt);
      eq(data.captions.map(c => c.i), [fi], `${key}: the prompt holds that one caption`);
      eq([data.captions[0].chunks[fj].fa, data.captions[0].chunks[fj].todo], [V.free.to, true],
         `${key}: its chunk as annotations.json has it now, «${V.free.to}», todo`);
      assert(!prompt.includes(wasText) && !JSON.stringify(data).includes(was.fa),
             `${key}: transcript.txt's «${wasText}» is nowhere in the prompt`);
      const ans = structuredClone(data);
      const c = ans.captions[0].chunks[fj];
      delete c.todo;
      Object.assign(c, {en: 'the meaning of the new text', tr: 'new text'}, L.reading ? {kana: 'そのほんは'} : {});
      await paste(page, fence(ans));
      rep = await fill(page);
      eq(counts(rep), 'filled 1 · completed 0 · replaced 0', `${key}: an answer to it lands`);
      const landed = (await annOf(key)).segments[fi].chunks[fj];
      eq([landed.fa, landed.free, landed.en], [V.free.to, true, 'the meaning of the new text'],
         `${key}: the gloss written beside the new text, the text and its mark untouched`);
    }

    /* ---------------- g) ---------------- */
    console.log(' g) re-gloss, and its confirm arm');
    {
      const [g0, g1] = V.regloss;
      ann = await annOf(key);
      await pickRun(page, g0, g1);
      eq(await slots(page), [name(g0), name(g1)], `${key}: captions ${g0}–${g1} picked`);
      await page.click('#rgregloss');
      ({prompt, sum} = await copyPrompt(page));
      data = dataOf(prompt);
      const flat = data.captions.flatMap(c => c.chunks || []);
      const glossable = flat.filter(ch => !ch.plain);
      assert(glossable.length && glossable.every(ch => ch.todo === true && !GLOSS.some(g => g in ch)),
             `${key}: re-gloss ticked, every one of the ${glossable.length} chunks is todo and no gloss is sent`);
      const seg = run => run.flatMap(i => (ann.segments[i].chunks || []).map((ch, j) => [i, j, ch]));
      const inRun = seg([g0, g1].length && Array.from({length: g1 - g0 + 1}, (_, k) => g0 + k)).filter(x => !x[2].plain);
      const nWritten = inRun.filter(x => !unwritten(x[2], L)).length, nBlank = inRun.length - nWritten;
      assert(sum.includes(`${glossable.length} to gloss, 0 glossed sent as context`), `${key}: the panel says so: ${JSON.stringify(sum.split('\n')[1])}`);
      const fresh = structuredClone(data);
      for (const c of fresh.captions) for (const ch of c.chunks || []) {
        if (ch.plain) continue;
        delete ch.todo;
        ch.en = 'afresh: ' + ch.fa;
        ch.voc = 'afresh vocabulary';
        if (L.require_tr) ch.tr = 'afresh';
        if (L.reading) ch.kana = 'あらた';
      }
      await paste(page, fence(fresh));
      const beforeG = await bytesOf(key);
      // unticked by the time the answer is filled: every gloss is kept
      await page.click('#rgregloss');
      rep = await fill(page);
      eq(counts(rep), `filled ${nBlank} · completed 0 · replaced 0`, `${key}: the box unticked when the answer is filled decides: nothing glossed is replaced`);
      eq((rep.lists['kept'] || []).length, nWritten, `${key}: all ${nWritten} glossed chunks listed as kept`);
      if (nBlank) {
        // the blank one was filled: the next press would find nothing blank
        const b = await bytesOf(key);
        assert(!bytesEqual(b, beforeG), `${key}: (the ${nBlank} blank chunk of the run took the answer)`);
      } else assert(bytesEqual(await bytesOf(key), beforeG), `${key}: annotations.json untouched`);
      const beforeArm = await bytesOf(key);
      ann = await annOf(key);
      // what the second answer would REPLACE: a glossed chunk whose gloss is
      // not already the answer's (the blank one just filled from this very
      // answer would change nothing, and is not counted)
      const slotsL = ['tr', 'voc', 'en'].concat(L.reading ? ['kana'] : []);
      const answered = (i, j) => fresh.captions.find(c => c.i === i).chunks[j];
      const nNow = inRun.filter(x => {
        const ch = ann.segments[x[0]].chunks[x[1]], a = answered(x[0], x[1]);
        return !unwritten(ch, L) && slotsL.some(f => (ch[f] || '').trim() !== (a[f] || '').trim());
      }).length;
      await page.click('#rgregloss');
      rep = await fill(page);
      const armed = () => page.evaluate(() => {
        const b = document.querySelector('#rgfill');
        return {text: b.textContent, armed: b.classList.contains('armed')};
      });
      const R = n => `replace ${n} ${n === 1 ? 'gloss' : 'glosses'} — press again`;
      eq(await armed(), {text: R(nNow), armed: true}, `${key}: re-gloss ticked, the first press writes nothing and arms: ${JSON.stringify(R(nNow))}`);
      assert(new RegExp(`^${nNow} existing gloss(es)? will be replaced`).test(rep.tally), `${key}: the report says ${JSON.stringify(rep.tally.split('.')[0])}`);
      assert(bytesEqual(await bytesOf(key), beforeArm), `${key}: annotations.json untouched while armed`);
      await sleep(4500);
      eq(await armed(), {text: 'fill from the answer', armed: false}, `${key}: left alone for four seconds it disarms`);
      await page.click('#rgfill');
      await page.waitForFunction(() => document.querySelector('#rgfill').classList.contains('armed'));
      await page.click('#rgans');
      await page.keyboard.press('Control+End');
      await page.keyboard.type(' ');
      eq(await armed(), {text: 'fill from the answer', armed: false}, `${key}: armed again, a change to the answer disarms it`);
      assert(bytesEqual(await bytesOf(key), beforeArm), `${key}: still nothing written`);
      await page.click('#rgfill');
      await page.waitForFunction(() => document.querySelector('#rgfill').classList.contains('armed'));
      await markLines(page);
      rep = await fill(page);
      eq(counts(rep), `filled 0 · completed 0 · replaced ${nNow}`, `${key}: the second press replaces them`);
      ann = await annOf(key);
      const got = inRun.map(x => ann.segments[x[0]].chunks[x[1]]);
      assert(got.every(ch => ch.en === 'afresh: ' + ch.fa && ch.voc === 'afresh vocabulary' &&
                             (!L.reading || ch.kana === 'あらた') && (!L.require_tr || ch.tr === 'afresh') &&
                             (L.require_tr || !ch.tr)),
             `${key}: on disk every chunk of the run carries the answer's gloss`);
      eq((await redrawn(page)).fresh, [...new Set(inRun.map(x => x[0]))], `${key}: and exactly those captions are drawn again`);
      await hover(page, inRun[0][0], inRun[0][1]);
      eq((await cloudSays(page)).en, 'afresh: ' + inRun[0][2].fa, `${key}: the page shows the new meaning`);
      await away(page);
    }

    /* ---------------- g2) ---------------- */
    console.log(' g2) per field: a chunk half glossed by hand');
    {
      const [pi, pj] = V.perfield;
      await openEdit(page, pi, pj);
      await page.click('#cloud .edel');
      await waitStat(page, /^gloss deleted/);
      await type(page, 'en', 'a meaning somebody wrote');
      await page.click('#cloud .esave');
      await waitStat(page, /^saved ✓/);
      await closeEdit(page);
      ann = await annOf(key);
      eq(glossOf(ann.segments[pi].chunks[pj]), {en: 'a meaning somebody wrote'}, `${key}: segment ${pi} chunk ${pj} half glossed by hand: its meaning alone`);
      if (await page.evaluate(() => document.querySelector('#rgregloss').checked)) await page.click('#rgregloss');
      const seeks = await page.evaluate(() => window.__yt.seeks.length);
      await pickRun(page, pi, pi, 'time');
      eq(await slots(page), [name(pi), name(pi)], `${key}: caption ${pi} picked by clicks on its time`);
      eq(await page.evaluate(() => [window.__yt.seeks.length, window.__yt.going()]), [seeks, false],
         `${key}: which, while picking, plays nothing either`);
      ({prompt, sum} = await copyPrompt(page));
      eq(prompt, SENTINEL, `${key}: per chunk, a chunk with any gloss is left as it is: nothing to copy`);
      await page.click('#rgperfield');
      ({prompt, sum} = await copyPrompt(page));
      data = dataOf(prompt);
      const slotsL = ['kana', 'tr', 'voc', 'en'].filter(f => f !== 'kana' || L.reading);
      const wantTodo = ann.segments[pi].chunks.map(ch => unwritten(ch, L) ? true : (slotsL.filter(f => !(ch[f] || '').trim()).length ? slotsL.filter(f => !(ch[f] || '').trim()) : undefined));
      eq(data.captions[0].chunks.map(ch => ch.todo), wantTodo, `${key}: "also fill the empty boxes of partly glossed chunks" ticked, each chunk is asked for exactly its empty boxes: ${JSON.stringify(wantTodo[pj])}`);
      eq(data.captions[0].chunks[pj].en, 'a meaning somebody wrote', `${key}: sent with the meaning somebody wrote`);
      const ans = structuredClone(data);
      let asked = 0;
      for (const ch of ans.captions[0].chunks) {
        if (!Array.isArray(ch.todo)) continue;
        asked++;
        for (const f of ch.todo) ch[f] = f === 'kana' ? 'ありがとう' : 'filled ' + f;
        delete ch.todo;
      }
      ans.captions[0].chunks[pj].en = 'CHANGED by the answer';
      await paste(page, fence(ans));
      rep = await fill(page);
      eq(counts(rep), `filled 0 · completed ${asked} · replaced 0`, `${key}: the answer completes ${asked === 1 ? 'it' : 'the ' + asked}`);
      assert((rep.lists['kept'] || []).length === 1 && /already glossed -- left as it is \(the answer changed `en`\)/.test(rep.lists['kept'][0]),
             `${key}: its change to the meaning somebody wrote is kept out, and listed: ${JSON.stringify((rep.lists['kept'] || [])[0])}`);
      const done = (await annOf(key)).segments[pi].chunks[pj];
      eq(done.en, 'a meaning somebody wrote', `${key}: on disk the meaning is the one somebody wrote`);
      assert(wantTodo[pj].every(f => done[f] === (f === 'kana' ? 'ありがとう' : 'filled ' + f)), `${key}: and its empty boxes are filled`);
      await page.click('#rgperfield');
    }

    if (V.shutBy === '✕') await page.click('#rgclose');
    else {
      await page.click('#rghead');                    // the focus in the panel, on nothing that takes a key
      await page.keyboard.press('Escape');
    }
    await page.waitForFunction(() => document.querySelector('#rgpanel').hidden);
    assert(true, `${key}: ${V.shutBy === '✕' ? 'its ✕' : 'Esc'} closes the panel`);
    eq([await litClass(page), await page.evaluate(() => document.body.classList.contains('rgpicking'))], [[], false],
       `${key}: closed, the run is unlit`);
    {
      const n = await page.evaluate(() => window.__yt.seeks.length);
      await pickAt(page, V.region[1], 'line');
      await until(() => page.evaluate(n => window.__yt.seeks.length === n + 1 && window.__yt.going(), n), 'the click seeks again');
      eq(await page.evaluate(() => window.__yt.seeks.slice(-1)[0]), (await annOf(key)).segments[V.region[1]].start,
         `${key}: and a click on a caption plays it again from its start`);
      await page.evaluate(() => window.__yt.pause());   // the pause in YouTube's own frame
    }

    /* ---------------- h) ---------------- */
    console.log(' h) the divide sheet, on a phrase with a note');
    {
      const [hi, hj] = V.divide;
      ann = await annOf(key);
      const ch = ann.segments[hi].chunks[hj], n0 = ann.segments[hi].chunks.length;
      assert(ch.note, `${key}: segment ${hi} chunk ${hj} «${ch.fa}» carries a note: «${ch.note}»`);
      await openEdit(page, hi, hj);
      await page.click('#cloud .edv[data-dv="split"]');
      await page.waitForFunction(() => !document.querySelector('#dvbox').hidden &&
                                       document.querySelectorAll('#dvwhere .dvcut').length > 0);
      if (!(await page.evaluate(() => document.querySelectorAll('#dvpair .dvcol').length === 2)))
        await page.click('#dvwhere .dvcut >> nth=0');
      const halves = await page.evaluate(() => [...document.querySelectorAll('#dvpair .dvcol')].map(c => c.dataset.fa));
      await page.click('#dvdo');
      await page.waitForFunction(() => /done ✓|\S/.test(document.querySelector('#dvstat').textContent) &&
                                       !/writing…/.test(document.querySelector('#dvstat').textContent), null, {timeout: 20000});
      eq(await text(page, '#dvstat'), 'done ✓', `${key}: "✂ cut in two" divides it into «${halves.join('» + «')}», not refused`);
      ann = await annOf(key);
      const cut = ann.segments[hi].chunks;
      eq([cut.length, cut[hj].fa, cut[hj + 1].fa], [n0 + 1, halves[0], halves[1]], `${key}: on disk the two phrases`);
      eq([cut[hj].note, cut[hj + 1].note], [ch.note, undefined], `${key}: the note stays with the first`);
      const said = await text(page, '#dvnotes');
      assert(/annotations\.json is what was written/.test(said) && !/parts\//.test(said),
             `${key}: and the sheet says what was written, with no word of a parts/ that is gone: ${JSON.stringify(said.slice(-90))}`);
      await page.click('#dvdo');
      await page.waitForFunction(() => document.querySelector('#dvbox').hidden);
      await openEdit(page, hi, hj);
      await page.click('#cloud .edv[data-dv="next"]');
      await page.waitForFunction(() => !document.querySelector('#dvbox').hidden && !document.querySelector('#dvdo').disabled &&
                                       document.querySelector('#dvdo').textContent === 'join');
      await page.click('#dvdo');
      await page.waitForFunction(() => !/writing…/.test(document.querySelector('#dvstat').textContent) &&
                                       document.querySelector('#dvstat').textContent, null, {timeout: 20000});
      eq(await text(page, '#dvstat'), 'done ✓', `${key}: "join next" joins them back, not refused`);
      ann = await annOf(key);
      const one = ann.segments[hi].chunks;
      eq([one.length, one[hj].fa, one[hj].note], [n0, ch.fa, ch.note], `${key}: on disk one phrase again, «${ch.fa}», its note «${ch.note}» kept`);
      if (ch.col) eq(one[hj].col, ch.col, `${key}: and its colour`);
      await page.click('#dvdo');
      await page.waitForFunction(() => document.querySelector('#dvbox').hidden);
      await hover(page, hi, hj);
      eq((await cloudSays(page)).note, ch.note, `${key}: the phrase's cloud shows the note`);
      await away(page);
    }
    await page.close();
  }

  /* ---------------- i) ---------------- */
  console.log('\ni) what the pages and the hub said');
  console.log('  (refused as expected: ' + [...allowed].join(', ') + ')');
  assert(!errors.length, 'no page threw, logged an error or had a request refused: ' + errors.join('; '));
  const tb = log.join('');
  assert(!/Traceback/.test(tb), 'no traceback in the hub\'s log');
  assert(bytesEqual(await Deno.readFile(B0.it.dir + '/video.json'), itMetaBefore),
         'the Italian video.json still carries the "draft": true it was given, untouched (never read, never stripped)');
  for (const k of ['fa', 'ja']) {
    const m = JSON.parse(await Deno.readTextFile(B0[k].dir + '/video.json'));
    assert(!('draft' in m), `${k}: its video.json was given no draft flag`);
  }
  const ownAfter = JSON.parse(await py(OWN, TMP));
  eq(ownAfter.leaks, [], 'nothing of this run\'s tree was remembered in the owner\'s config/digests.json or wheres.json');
  eq(ownAfter.digests, ownBefore.digests, 'the owner\'s config/, books/, youtube/videos/ and the fixtures are untouched');
  console.log(`\ngloss_llm_video: ${passed} checks passed`);
} finally {
  // a failure part way says what the pages said up to it
  if (errors.length) console.log('what the pages said:\n  ' + errors.join('\n  '));
  if (SHOTS && current && !current.isClosed())
    await current.screenshot({path: `${SHOTS}/at-the-end.png`}).catch(() => {});
  if (browser) await browser.close();
  if (hub) { try { hub.kill('SIGTERM'); await hub.status; } catch (_) {} }
  if (!Deno.env.get('PARSEH_KEEP')) await Deno.remove(TMP, {recursive: true}).catch(() => {});
  else console.log('kept ' + TMP);
}

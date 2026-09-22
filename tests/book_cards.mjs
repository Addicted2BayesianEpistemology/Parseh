// SPDX-License-Identifier: GPL-3.0-or-later
import { chromium } from 'npm:playwright-core@1.52.0';
// Run: CHROME_BIN=/path/to/chrome PARSEH_PYTHON=/path/to/python3 deno run --allow-all tests/book_cards.mjs
//      BOOK_CARDS_SHOTS=<dir> also saves the card sheet in each destination, at
//      desktop and at phone width
//
// The book reader's card sheet (lib/tex2html.py) on the REAL hub: serve.main()
// on a temporary toolbox holding four books -- mini-en narrated (a steady
// tone, every subparagraph timed but the last), mini-ja read in two
// recordings with a word line in one chunk, mini-fr with no narration at
// all, and mini-jb read in three recordings of which one file is missing and
// one covers too little -- and the studio library, the exercise decks, the
// Anki store and the clip tray, all inside the temporary folder.  Every
// action is the page's own: a modifier-click on a word, the sheet's buttons,
// the cut editor's buttons.
//
//  a) An alt-click on a word in the middle of a subparagraph opens the sheet,
//     over the narration, which it pauses.  "exercise deck" is picked and
//     remembered, and each destination keeps the new deck's name typed for
//     it; "cut the audio…" opens the cut editor with its edges where
//     the word's share of the sentence puts them (worked out here, apart from
//     the page); a nudge and "save clip" cut it into the tray, "use this clip"
//     puts it on the card, where it plays.  "add to deck" makes the deck and
//     the exercise: on disk with front-audio and the recording in the deck's
//     audio/; the sheet stays open, saying what went in, and its "open the
//     deck" link opens the deck; the deck's page links back to the book, and
//     the link opens it.  A duplicate is asked about on the sheet ("add it
//     again"), a change to the card asks again, and the second press adds
//     it.  Escape the moment after "add to deck": the card goes in as
//     pressed, recording and all, the clip stays in the tray, a toast says
//     so, and a sheet opened since is left alone; an Anki save answered while
//     the cut editor is open does not close the sheet under it.
//  b) The same card to Anki a second time: the preview plays the clip; the
//     card on disk names its sound and the sound is in the deck's media/.
//  c) Markdown: the clipboard holds one flashcard block the real parser reads
//     without an error, with back-audio; the preview draws it.  Jolly: the
//     four fields filled from the card, the clip inserted where the caret was;
//     a clip cut again goes into the box the cursor was last in and the one it
//     replaces leaves the card; a line taken out by hand stays out of the copy
//     and of a return to jolly, and the sheet says so; a browser that will not
//     put the markdown on the clipboard: the markdown is shown in the sheet,
//     selected, and the clip it names stays in the tray; a clip cut before
//     jolly was picked is put into back-primary.
//  d) A word-line (Japanese) chunk: the edges from the word's surfaces; a
//     whole chunk; Escape leaves no clip; a subparagraph of the second
//     recording is cut from that file.  No narration, a subparagraph with no
//     times, one in no recording, one timed in a recording whose file is
//     gone: "cut the audio…" is disabled and says which.
//  e) The card kit did not load: "cut the audio…", an exercise deck and
//     markdown each say so, in the video player's words.
// The sheet's head names the card each destination makes, and its rows are
// looked at as drawn.
const root = await Deno.realPath(new URL('..', import.meta.url));
Deno.chdir(root);
const PY = Deno.env.get('PARSEH_PYTHON') || 'python3';
const SHOTS = Deno.env.get('BOOK_CARDS_SHOTS') || '';
const TMP = await Deno.makeTempDir({prefix: 'parseh-book-cards-'});
const td = new TextDecoder();
let passed = 0;
const assert = (v, m) => { if (!v) throw Error('FAIL: ' + m); passed++; console.log('  ok', m); };
const near = (a, b, tol) => Math.abs(a - b) <= tol;
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function run(cmd, args) {
  const o = await new Deno.Command(cmd, {args, cwd: root, stdout: 'piped', stderr: 'piped'}).output();
  return {code: o.code, out: td.decode(o.stdout), err: td.decode(o.stderr)};
}
async function py(code, ...args) {
  const r = await run(PY, ['-c', code, ...args]);
  if (r.code) throw Error(r.err || r.out);
  return r.out;
}
async function duration(path) {
  const r = await run('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path]);
  if (r.code) throw Error('ffprobe: ' + r.err);
  return parseFloat(r.out);
}
async function files(dir, re = /./) {
  const out = [];
  try {
    for await (const e of Deno.readDir(dir))
      if (e.isFile && re.test(e.name)) out.push(e.name);
  } catch (_) {}
  return out.sort();
}
async function dirs(dir) {
  const out = [];
  try { for await (const e of Deno.readDir(dir)) if (e.isDirectory) out.push(e.name); } catch (_) {}
  return out.sort();
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
// Four books under <tmp>/root/books, each built by this tex2html.py.  The
// reader links lib/ relatively, from where it was built to where the toolbox
// is; served from the temporary root that path climbs out of the site, so it
// is written as the hub's own absolute one, and lib/ is linked in.
const BUILD = String.raw`
import json, os, shutil, subprocess, sys
REPO = os.getcwd()
sys.path[:0] = ['lib']
import books, texparse, texwrite, timestamp as ts
tmp = sys.argv[1]
root = os.path.join(tmp, 'root')

def ff(*args):
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error'] + [str(a) for a in args], check=True)

def copy(rel, dest=None):
    d = os.path.join(root, 'books', dest or rel)
    shutil.copytree(os.path.join('tests/fixtures/books', rel), d,
                    ignore=shutil.ignore_patterns('reader', '.reader-key'))
    return d

def narrate(d, times, parts=1):
    """Recordings of 8 s of a steady tone -- one, or PARTS sharing the
    subparagraphs out in order, each its own file -- and [t0, t1] for each
    subparagraph, seconds into its own recording: times(k) for the k-th of
    its recording (None: no time)."""
    os.makedirs(os.path.join(d, 'audio'))
    b = books.Book(d)
    ts._bind(b)
    subs = [x for ch in texparse.parse_book(b.main, b.lang) for pp in ch.paragraphs for x in pp.subs]
    labels = [x.num for x in subs]
    per = -(-len(subs) // parts)
    narrations = []
    for p in range(parts):
        ff('-f', 'lavfi', '-i', 'sine=frequency=%d:duration=8' % (440 + 220 * p), '-ac', '1',
           '-c:a', 'libmp3lame', '-q:a', '4', os.path.join(d, 'audio', 'part%d.mp3' % (p + 1)))
        stretch = labels[p * per:(p + 1) * per]
        narrations.append({'id': 'n%d' % (p + 1), 'audio': 'audio/part%d.mp3' % (p + 1), 'transcript': '',
                           'from': stretch[0], 'to': stretch[-1]})
    meta = json.load(open(os.path.join(d, 'book.json'), encoding='utf-8'))
    meta['audio'] = 'audio/part1.mp3'
    if parts > 1:
        meta['narrations'] = narrations
    json.dump(meta, open(os.path.join(d, 'book.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    recs = {}
    for k, x in enumerate(subs):
        t = times(k % per)
        if t:
            recs[ts.subkey(x)] = {'t0': t[0], 't1': t[1], 'conf': 1.0, 'src': 'manual', 'label': x.num}
            if parts > 1:
                recs[ts.subkey(x)]['n'] = 'n%d' % (k // per + 1)
    sidecar = {'audio': 'audio/part1.mp3', 'book': b.slug, 'generated_by': 'book_cards', 'subs': recs}
    if parts > 1:
        sidecar['narrations'] = narrations
    json.dump(sidecar, open(os.path.join(d, 'timings.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    r = subprocess.run([sys.executable, 'lib/timestamp.py', '--book', d, '--from-sidecar'],
                       capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(r.stderr or r.stdout)
    return labels

def build(d):
    r = subprocess.run([sys.executable, 'lib/tex2html.py', '--book', d], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(r.stderr or r.stdout)
    out = os.path.join(d, 'reader')
    climb = os.path.relpath(REPO, out).replace(os.sep, '/') + '/'
    for name in os.listdir(out):
        if name.endswith('.html'):
            p = os.path.join(out, name)
            text = open(p, encoding='utf-8').read()
            open(p, 'w', encoding='utf-8').write(text.replace(climb, '/'))

en = copy('english/mini-en')
en_labels = narrate(en, lambda k: [[0.8, 3.9], [3.9, 6.2], [6.2, 7.6], None][k])
ja = copy('japanese/mini-ja')
texwrite.edit_chunk(os.path.join(ja, 'ch1.tex'), 6, {'words': '山(やま) へ 柴刈り(しばかり) に 、'})
# read in two recordings, 1.1-1.3 and 2.1-2.3
ja_labels = narrate(ja, lambda k: [round(0.3 + 1.2 * k, 2), round(1.5 + 1.2 * k, 2)], parts=2)
fr = copy('french/mini-fr')
# mini-jb: mini-ja read in three recordings, 1.1-1.2, 1.3-2.1 and 2.2-2.3 -- but
# the second's file is not on this machine, and the third was cut back to 2.2,
# which leaves 2.3 in no recording and with no times
jb = copy('japanese/mini-ja', 'japanese/mini-jb')
narrate(jb, lambda k: [[0.3, 1.5], [1.5, 2.7]][k], parts=3)
for name in ('book.json', 'timings.json'):
    p = os.path.join(jb, name)
    j = json.load(open(p, encoding='utf-8'))
    j['narrations'][2]['to'] = '2.2'
    if name == 'book.json':
        j['slug'] = 'mini-jb'
    else:
        j['subs'] = {k: v for k, v in j['subs'].items() if v['label'] != '2.3'}
    json.dump(j, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
p = os.path.join(jb, 'ch1.tex')
kept = ''.join(line for line in open(p, encoding='utf-8') if not line.startswith('% @par 2.3 '))
open(p, 'w', encoding='utf-8').write(kept)
os.remove(os.path.join(jb, 'audio', 'part2.mp3'))
for d in (en, ja, fr, jb):
    build(d)
os.symlink(os.path.join(REPO, 'lib'), os.path.join(root, 'lib'))
os.makedirs(os.path.join(root, 'youtube'))
os.symlink(os.path.join(REPO, 'youtube', 'lib'), os.path.join(root, 'youtube', 'lib'))
for name in ('library', 'exercises', 'anki', 'tray'):
    os.makedirs(os.path.join(tmp, name))
print(json.dumps({'en': en_labels, 'ja': ja_labels}))
`;
// serve.main() over the temporary tree: every store it writes is in there
const SERVE = String.raw`
import sys
from pathlib import Path
sys.path[:0] = ['markdown/exlex', 'markdown/app', 'youtube/lib', 'lib', '.']
tmp, port = Path(sys.argv[1]), sys.argv[2]
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
// what the real parser, the deck store and the renderer make of a card
const READ = String.raw`
import json, sys
sys.path[:0] = ['markdown/exlex', 'markdown/app', 'lib']
import mdparser, htmlgen, decks
md = sys.argv[1]
doc = '---\ntarget: ' + sys.argv[2] + '\n---\n\n' + md
fm, blocks = mdparser.parse(doc)
b = blocks[0] if blocks else {}
try:
    decks.validate_markdown(md, sys.argv[2]); deck = True
except Exception as e:
    deck = str(e)
html = htmlgen.render_document(doc, asset_base='/clips/media/')['html']
print(json.dumps({'types': [x['type'] for x in blocks], 'subtype': b.get('subtype'), 'errors': b.get('errors'),
                  'fields': b.get('fields'), 'raw': b.get('raw_fields'), 'deck': deck, 'html': html}))
`;

const errors = [];
let hub = null, browser = null;
const log = [];
try {
  await py(BUILD, TMP);
  const port = freePort();
  hub = new Deno.Command(PY, {args: ['-c', SERVE, TMP, String(port)], cwd: root, stdout: 'piped', stderr: 'piped'}).spawn();
  drain(hub.stdout, log); drain(hub.stderr, log);
  const B = `http://127.0.0.1:${port}`;
  const until = Date.now() + 60000;
  for (;;) {
    try { const r = await fetch(B + '/clips/api/status'); await r.body?.cancel(); if (r.ok) break; } catch (_) {}
    if (Date.now() > until) throw Error('the hub did not start:\n' + log.join(''));
    await sleep(250);
  }
  const TRAY = TMP + '/tray';
  browser = await chromium.launch({executablePath: Deno.env.get('CHROME_BIN'), headless: true});
  const page = await browser.newPage({viewport: {width: 1280, height: 860}});
  page.on('pageerror', e => errors.push('pageerror: ' + e.message));
  page.on('response', r => {
    const u = new URL(r.url());
    // the one refusal asked for on purpose is the duplicate (409); the reader
    // asks for a few optional files a temporary book does not have
    if (r.status() >= 400 && !(r.status() === 409 && /\/items$/.test(u.pathname))
        && /\/(clips\/|__clip\/|anki\/|exercises\/|lib\/cardkit|studio\/static\/)/.test(u.pathname))
      errors.push(r.status() + ' ' + r.request().method() + ' ' + u.pathname);
  });

  // ---- helpers over the page
  const READER = B + '/books/english/mini-en/reader/';
  const shown = sel => page.evaluate(sel => {
    const el = document.querySelector(sel);
    return !!el && el.getClientRects().length > 0 && getComputedStyle(el).visibility === 'visible';
  }, sel);
  async function onScreen(sel, what) {
    const r = await page.evaluate(sel => {
      const b = document.querySelector(sel), rc = b.getBoundingClientRect();
      const hit = document.elementFromPoint(rc.left + rc.width / 2, rc.top + Math.min(rc.height / 2, 12));
      return {l: rc.left, t: rc.top, r: rc.right, b: rc.bottom, w: innerWidth, h: innerHeight,
              hit: !!hit && (b === hit || b.contains(hit))};
    }, sel);
    assert(r.l >= 0 && r.t >= 0 && r.r <= r.w + 0.5 && r.b <= r.h + 0.5 && r.r - r.l > 10 && r.hit,
           `${what} is on screen and on top (${Math.round(r.l)},${Math.round(r.t)}–${Math.round(r.r)},${Math.round(r.b)} in ${r.w}x${r.h})`);
  }
  // an alt-click on the k-th word of chunk n in pass 1
  async function altWord(n, k, what) {
    await page.locator(`.p1 [data-c="${n}"] .wd`).nth(k).click({modifiers: ['Alt']});
    await page.waitForFunction(() => !document.getElementById('anki').hidden && ankiOpen);
    if (what) await onScreen('#anki', what);
  }
  // THE EDGES, WORKED OUT HERE: the subparagraph's times, the text's
  // stripped length (the marks off, no whitespace, a code point a unit),
  // the chunk's place in it and the word's in the chunk -- the spaced words
  // of SRC, or the surfaces of a word line -- and the guess as the contract
  // writes it, rounded as the editor shows it
  const expected = (n, k, line) => page.evaluate(([n, k, line]) => {
    const sub = document.querySelector(`.p1 [data-c="${n}"]`).closest('.sub');
    const i = +sub.dataset.s, from = +sub.dataset.from, to = +sub.dataset.to;
    const marks = LANG.strip ? new RegExp('[' + LANG.strip + ']', 'g') : null;
    const len = s => [...(marks ? s.replace(marks, '') : s).replace(/\s/g, '')].length;
    const t0 = SUBS[i][0], t1 = SUBS[i][1];
    let units = 0, pre = 0;
    for (let c = from; c <= to; c++) { units += len(SRC[c][1]); if (c < n) pre += len(SRC[c][1]); }
    let a = pre, b = pre + len(SRC[n][1]);
    if (k !== null) {
      const words = line ? SRC[n][6].split(' ').map(w => w.replace(/\(.*\)$/, ''))
                         : SRC[n][1].trim().split(/\s+/);
      a = pre + words.slice(0, k).reduce((x, w) => x + len(w), 0);
      b = a + len(words[k]);
    }
    let s = t0 + (t1 - t0) * a / units - 0.12, e = t0 + (t1 - t0) * b / units + 0.12;
    const lo = Math.max(0, t0 - 0.3), hi = t1 + 0.3;
    s = Math.min(Math.max(s, lo), hi); e = Math.min(Math.max(e, lo), hi);
    if (e < s + 0.2) { e = Math.min(hi, s + 0.2); s = Math.max(lo, Math.min(s, e - 0.2)); }
    const rec = NARR.find(r => r.id === SUBS[i][3]) || NARR[0];
    return {s, e, t0, t1, units, a, b, file: new URL(rec.src, location.href).pathname, narration: rec.id};
  }, [n, k, line]);
  const edges = () => page.evaluate(() => ({s: +document.querySelector('.pc-cut .e0').value,
                                            e: +document.querySelector('.pc-cut .e1').value}));
  async function openCutter(what) {
    assert(await page.evaluate(() => !document.getElementById('asnd').disabled), what + ': "cut the audio…" can be pressed');
    await page.click('#asnd');
    await page.waitForSelector('.pc-root .pc-cut');
    await page.waitForFunction(() => document.querySelector('.pc-root .pc-play').readyState >= 1, null, {timeout: 10000});
  }
  // save, then use: the clip goes onto the card
  async function useClip() {
    await page.click('.pc-cut .pc-save');
    await page.waitForFunction(() => {
      const s = document.querySelector('.pc-saved');
      return s && !s.hidden && /saved to the clip tray/.test(document.querySelector('.pc-stat').textContent);
    }, null, {timeout: 20000});
    await page.click('.pc-cut .pc-use');
    await page.waitForFunction(() => !document.querySelector('.pc-root'));
    await page.waitForFunction(() => !document.getElementById('asndprev').hidden);
    return page.evaluate(() => ({name: document.getElementById('asndname').textContent.split(' ')[0],
                                 src: document.getElementById('asndaudio').getAttribute('src')}));
  }
  const status = () => page.evaluate(() => document.getElementById('astat').textContent);
  async function shot(name) {
    if (!SHOTS) return;
    await Deno.mkdir(SHOTS, {recursive: true});
    await page.screenshot({path: `${SHOTS}/${name}.png`});
  }

  /* ---------------- a) an exercise deck ---------------- */
  console.log('a) a word to an exercise deck, with its recording');
  await page.goto(READER);
  await page.waitForFunction(() => typeof SUBS !== 'undefined' && document.querySelector('.sub'));
  assert(await page.evaluate(() => typeof ParsehCards === 'object' && typeof ParsehCards.cut === 'function'
                                   && [...document.styleSheets].some(s => /\/lib\/cardkit\.css$/.test(s.href || ''))),
         'the reader links the card kit: window.ParsehCards and cardkit.css');
  // the narration plays: a click on the subparagraph
  await page.click('.sub[data-s="1"] .lab');
  await page.waitForFunction(() => !document.getElementById('audio').paused && document.getElementById('audio').currentTime > 0,
                             null, {timeout: 10000});
  // "wind", the third word of the second chunk of 1.2: the middle of it
  await altWord(4, 2, 'the card sheet');
  assert(await page.evaluate(() => document.getElementById('audio').paused), 'the narration is paused under the sheet');
  assert(await page.evaluate(() => [document.getElementById('afa').value, document.getElementById('aref').textContent,
                                    document.getElementById('atanki').classList.contains('on')].join('|')) === 'wind|1.2|true',
         'it is the word\'s card, for 1.2, and Anki is where a card goes first');
  await shot('sheet-anki-desktop');
  // a name for a new Anki deck, typed before another destination is picked
  await page.waitForFunction(() => document.getElementById('adeck').dataset.of === 'anki');
  assert(await page.evaluate(() => document.getElementById('ahtitle').textContent) === 'anki card' && await shown('#adecknew'),
         'Anki: the head says "anki card"; no Anki deck yet, so a name box');
  await page.fill('#adecknew', 'English::Words');
  await page.click('#atdeck');
  assert(await page.evaluate(() => localStorage.getItem('bk_card_target')) === 'deck'
         && await page.evaluate(() => document.getElementById('atdeck').getAttribute('aria-pressed')) === 'true',
         'exercise deck is picked, and remembered');
  assert(await shown('#akjolly') && !(await shown('#abuild')) && !(await shown('#atagsrow'))
         && await page.evaluate(() => document.getElementById('asavelab').textContent) === 'add to deck',
         'the sheet offers jolly, hides build and tags, and its button reads "add to deck"');
  await page.waitForFunction(() => document.getElementById('adeck').dataset.of === 'deck');
  assert(await page.evaluate(() => [...document.querySelectorAll('#adeck option')].map(o => o.textContent).join()) === '+ new deck…'
         && await shown('#adecknew') && await page.evaluate(() => [document.getElementById('adecknew').value, document.getElementById('ahtitle').textContent].join('|')) === '|exercise card',
         'no exercise deck yet: "+ new deck…" and an empty name box (the Anki name stays Anki\'s); the head says "exercise card"');
  await page.fill('#adecknew', 'Book cards');
  // each destination keeps the name typed for it
  await page.click('#atanki');
  await page.waitForFunction(() => document.getElementById('adeck').dataset.of === 'anki');
  assert(await page.evaluate(() => document.getElementById('adecknew').value) === 'English::Words', 'back on Anki: the name typed for Anki');
  await page.click('#atdeck');
  await page.waitForFunction(() => document.getElementById('adeck').dataset.of === 'deck');
  assert(await page.evaluate(() => document.getElementById('adecknew').value) === 'Book cards', 'and on the exercise deck, the one typed for it');
  await shot('sheet-deck-desktop');

  // the cut editor, with the word's stretch of the sentence
  const want = await expected(4, 2, false);
  await openCutter('the word "wind"');
  await onScreen('.pc-cut', 'the cut editor');
  assert(await page.evaluate(() => document.getElementById('audio').paused), 'the narration stays paused under the cut editor');
  let got = await edges();
  assert(near(got.s, want.s, 0.01) && near(got.e, want.e, 0.01),
         `the edges are the word's share of 1.2: ${got.s}–${got.e} (worked out ${want.s.toFixed(3)}–${want.e.toFixed(3)} from ${want.a}–${want.b} of ${want.units} in [${want.t0}, ${want.t1}])`);
  // and by hand, for this sentence: "wind" is letters 20-24 of 53 in 3.9-6.2
  assert(near(got.s, 4.65, 0.01) && near(got.e, 5.06, 0.01), `…which is 4.65–5.06 (${got.s}–${got.e})`);
  assert(await page.evaluate(() => new URL(document.querySelector('.pc-root .pc-play').src).pathname) === want.file
         && await page.evaluate(() => document.querySelector('.pc-cut .who').textContent) === '1.2',
         'it plays the book\'s own recording, and names the subparagraph');
  await page.click('.pc-cut [data-e="s-"]');
  await page.click('.pc-cut [data-e="e+"]');
  got = await edges();
  assert(near(got.s, want.s - 0.1, 0.011) && near(got.e, want.e + 0.1, 0.011), `nudged: ${got.s}–${got.e}`);
  const trayBefore = await files(TRAY, /\.mp3$/);
  const clipA = await useClip();
  assert(clipA.src === '/clips/media/' + clipA.name && (await files(TRAY, /\.mp3$/)).length === trayBefore.length + 1
         && (await files(TRAY)).includes(clipA.name), `the clip is in the tray and on the card: ${clipA.name}`);
  const lenA = await duration(`${TRAY}/${clipA.name}`);
  assert(near(lenA, got.e - got.s, 0.06), `the clip is as long as the edges say (${lenA.toFixed(3)} s for ${(got.e - got.s).toFixed(2)})`);
  await onScreen('#asndaudio', 'the clip\'s player');
  await page.evaluate(() => document.getElementById('asndaudio').play());
  await page.waitForFunction(() => { const a = document.getElementById('asndaudio'); return a.readyState >= 1 && a.currentTime > 0.1; },
                             null, {timeout: 8000});
  assert(await page.evaluate(d => Math.abs(document.getElementById('asndaudio').duration - d) < 0.08, lenA),
         'the clip plays in the sheet');
  assert(await page.evaluate(() => document.querySelector('input[name=asndside][value=front]').checked) && await shown('#asndsides'),
         'on the front: the side of the language');
  await shot('sheet-deck-clip-desktop');

  await page.click('#asave');
  await page.waitForFunction(() => /added ✓/.test(document.getElementById('astat').textContent), null, {timeout: 10000});
  const said = await status();
  assert(said === 'added ✓ — a vocabulary card for “wind”, with its recording, to “Book cards” — open the deck',
         'it says what went in, and where: ' + said);
  const slugs = await dirs(TMP + '/exercises/english');
  assert(slugs.length === 1, 'one deck made: ' + slugs.join());
  const DECK = `${TMP}/exercises/english/${slugs[0]}`;
  let items = await files(DECK + '/items', /\.json$/);
  const item = JSON.parse(await Deno.readTextFile(`${DECK}/items/${items[0]}`));
  assert(items.length === 1 && item.markdown.includes('\nfront-audio: audio/' + clipA.name + '\n')
         && item.markdown.includes('\ntarget: [wind]{tl}\n'), 'the exercise is on disk, with front-audio: audio/' + clipA.name);
  const deckClip = await Deno.stat(`${DECK}/audio/${clipA.name}`), trayClip = await Deno.stat(`${TRAY}/${clipA.name}`);
  assert(deckClip.size === trayClip.size && deckClip.size > 500, `the recording is in the deck's audio/ (${deckClip.size} bytes)`);
  const para = await page.evaluate(() => document.querySelector('.p1 [data-c="4"]').closest('.para[id]').id);
  assert(JSON.stringify(item.origin) === JSON.stringify({title: 'The Clock and the Wind', book: '/books/english/mini-en',
                                                          label: '1.2', url: '/books/english/mini-en/reader/#' + para}),
         'its origin: the book, the subparagraph, the page at its paragraph ' + JSON.stringify(item.origin));
  await sleep(1300);
  assert(await page.evaluate(() => ankiOpen) && await shown('#anki')
         && await page.evaluate(() => document.querySelector('#adeck option:checked').textContent) === 'Book cards (1 exercise)',
         'the sheet stays open after "added", the deck picked with its count');
  assert(await page.evaluate(() => document.querySelector('#astat a').getAttribute('href')) === `/exercises/deck/english/${slugs[0]}/`,
         'its "open the deck" link is the deck\'s page');
  await shot('sheet-deck-added-desktop');
  {
    const [tab] = await Promise.all([page.context().waitForEvent('page'), page.click('#astat a')]);
    await tab.waitForLoadState();
    await tab.waitForSelector('a.dk-made');
    assert(new URL(tab.url()).pathname === `/exercises/deck/english/${slugs[0]}/` && await tab.locator('a.dk-made').count() === 1,
           'following it opens the deck, in a tab of its own, with the exercise in it');
    await tab.close();
  }
  await page.keyboard.press('Escape');
  await page.waitForFunction(() => document.getElementById('anki').hidden && !ankiOpen, null, {timeout: 5000});
  assert(await page.evaluate(() => document.getElementById('audio').paused === false), 'closed: the narration plays on');
  await page.click('#play');

  // twice more without a recording: the second is a duplicate, asked about
  await altWord(4, 2);
  assert(await page.evaluate(() => document.getElementById('atdeck').classList.contains('on')), 'the sheet opens on the exercise deck again');
  await page.waitForFunction(() => document.getElementById('adeck').dataset.of === 'deck' && document.getElementById('adeck').value !== '');
  assert(await page.evaluate(() => document.querySelector('#adeck option:checked').textContent) === 'Book cards (1 exercise)'
         && !(await shown('#asndprev')), 'on the deck it went to, and with no clip on the new card');
  await page.click('#asave');
  await page.waitForFunction(() => /added ✓/.test(document.getElementById('astat').textContent), null, {timeout: 10000});
  await page.click('#acancel');
  await altWord(4, 2);
  await page.waitForFunction(() => document.getElementById('adeck').dataset.of === 'deck' && document.getElementById('adeck').value !== '');
  await page.click('#asave');
  await page.waitForFunction(() => document.getElementById('asavelab').textContent === 'add it again', null, {timeout: 10000});
  await shot('sheet-deck-duplicate-desktop');
  assert(await status() === 'this exercise is already in "Book cards" — press “add it again” to add a second one'
         && (await files(DECK + '/items', /\.json$/)).length === 2,
         'the same card again: the deck says it has it, nothing is added, the button reads "add it again"');
  // a change to the card asks again
  await page.click('#akvocab');
  assert(await page.evaluate(() => document.getElementById('asavelab').textContent) === 'add to deck',
         'a click on the card\'s type puts the button back to "add to deck"');
  await page.click('#asave');
  await page.waitForFunction(() => document.getElementById('asavelab').textContent === 'add it again', null, {timeout: 10000});
  await page.click('#asave');
  await page.waitForFunction(() => /added ✓/.test(document.getElementById('astat').textContent), null, {timeout: 10000})
    .catch(() => {});
  assert((await files(DECK + '/items', /\.json$/)).length === 3
         && await page.evaluate(() => document.getElementById('asavelab').textContent) === 'add to deck',
         'pressed again, it is added, and the button is "add to deck" again: ' + await status());
  await page.click('#acancel');

  // the deck's page links back to the book
  const deckPage = await browser.newPage({viewport: {width: 1280, height: 860}});
  deckPage.on('pageerror', e => errors.push('deck pageerror: ' + e.message));
  await deckPage.goto(`${B}/exercises/deck/english/${slugs[0]}/`);
  await deckPage.waitForSelector('a.dk-made');
  const back = await deckPage.evaluate(() => [...document.querySelectorAll('a.dk-made')].map(a => [a.getAttribute('href'), a.textContent]));
  assert(back.length === 3 && back.every(x => x[0] === '/books/english/mini-en/reader/#' + para && x[1] === 'The Clock and the Wind · 1.2'),
         'the deck page links each card back to the book: ' + JSON.stringify(back[0]));
  await deckPage.locator('a.dk-made').first().click();
  await deckPage.waitForFunction(p => location.pathname === '/books/english/mini-en/reader/' && location.hash === '#' + p
                                      && document.querySelector('.sub') && typeof SUBS !== 'undefined', para);
  assert(true, 'and the link opens the reader at the paragraph');
  await deckPage.close();

  // a clip gone from the tray before the card is added: the deck says so,
  // the sheet says it, and stays open for it to be read
  await altWord(4, 2);
  await page.waitForFunction(() => document.getElementById('adeck').dataset.of === 'deck' && document.getElementById('adeck').value !== '');
  await openCutter('a clip that goes missing');
  const gone = await useClip();
  await (await fetch(`${B}/clips/api/${gone.name}`, {method: 'DELETE'})).body?.cancel();
  await page.click('#asave');
  await page.waitForFunction(() => /added ✓/.test(document.getElementById('astat').textContent), null, {timeout: 10000});
  await sleep(1500);
  const warned = await status();
  assert(warned.includes(`front-audio: audio/${gone.name} is not among this deck's recordings`) && !(await page.evaluate(() => document.getElementById('anki').hidden)),
         'added with the deck\'s warning, and the sheet stays to show it: ' + warned.replace(/\n/g, ' | '));
  await onScreen('#astat', 'the warning');
  await shot('sheet-deck-warning-desktop');
  await page.click('#acancel');

  // "add to deck", and Escape the moment after, while the new deck is still
  // being made (the hub is held back a little, so the press is surely still
  // out): the card goes in as it was pressed, recording and all, the clip
  // stays in the tray, and -- the sheet being gone, and another open for
  // another word -- a toast over the page says so, and that other sheet is
  // neither told nor closed by the answer
  const slow = u => /^\/exercises\/api\/decks(\/[^\/]+\/[^\/]+\/items)?$/.test(new URL(u).pathname);
  const held = [];
  const hold = async route => {
    if (route.request().method() === 'POST') { held.push(new URL(route.request().url()).pathname); await sleep(400); }
    await route.continue();
  };
  await page.route(slow, hold);
  await altWord(4, 3);
  await page.waitForFunction(() => document.getElementById('adeck').dataset.of === 'deck' && document.getElementById('adeck').value !== '');
  await page.selectOption('#adeck', '');
  await page.fill('#adecknew', 'Closed early');
  // a list of the decks that comes back after the pick (asked again because a
  // count changed, or a first answer slower than the hand) must not undo it:
  // "+ new deck…" stays picked, with its name, or the card would go to the
  // deck used last
  await page.evaluate(() => ParsehCards.decks(LANG.code).then(list => exDeckOptions(list)));
  assert(await page.evaluate(() => document.getElementById('adeck').value === ''
                                   && document.getElementById('adecknew').value === 'Closed early'
                                   && !document.getElementById('adecknew').hidden),
         'a list of the decks that comes back after "+ new deck…" was picked keeps the pick and its name');
  await openCutter('a card whose sheet is closed before its deck is made');
  const early = await useClip();
  await page.click('#asave');
  await page.keyboard.press('Escape');
  assert(await page.evaluate(() => !ankiOpen && document.getElementById('anki').hidden)
         && await page.evaluate(() => document.getElementById('astat').textContent) === 'making the deck…',
         'Escape closes the sheet while its deck is still being made');
  await altWord(4, 0);
  await page.waitForFunction(() => {
    const t = document.getElementById('parseh-toast');
    return t && t.classList.contains('show') && /added ✓/.test(t.textContent);
  }, null, {timeout: 10000});
  const toast = await page.evaluate(() => document.getElementById('parseh-toast').textContent);
  // (a toast lets clicks through, so elementFromPoint cannot find it: it is
  // looked at by its box, its opacity and its layer over the sheet)
  await page.waitForFunction(() => getComputedStyle(document.getElementById('parseh-toast')).opacity === '1');
  const toastBox = await page.evaluate(() => {
    const t = document.getElementById('parseh-toast'), r = t.getBoundingClientRect();
    return {in: r.left >= 0 && r.top >= 0 && r.right <= innerWidth && r.bottom <= innerHeight && r.width > 10,
            over: +getComputedStyle(t).zIndex > +getComputedStyle(document.getElementById('anki')).zIndex};
  });
  assert(toastBox.in && toastBox.over, 'the toast is on screen, over the sheet: ' + JSON.stringify(toastBox));
  await shot('closed-early-toast-desktop');
  assert(toast === 'added ✓ — a vocabulary card for “outside”, with its recording, to “Closed early”'
         && await page.evaluate(() => ankiOpen && document.getElementById('afa').value === 'and'
                                      && !/added/.test(document.getElementById('astat').textContent)),
         'the answer is a toast over the page, not a word on the sheet opened since: ' + toast);
  const early_slug = (await dirs(TMP + '/exercises/english')).find(s => s !== slugs[0]);
  const EARLY = `${TMP}/exercises/english/${early_slug}`;
  const earlyItems = await files(EARLY + '/items', /\.json$/);
  const earlyMd = earlyItems.length === 1 ? JSON.parse(await Deno.readTextFile(`${EARLY}/items/${earlyItems[0]}`)).markdown : '';
  assert(early_slug === 'closed-early' && earlyMd.includes('\ntarget: [outside]{tl}\n') && earlyMd.includes('\nfront-audio: audio/' + early.name + '\n')
         && (await files(EARLY + '/audio')).includes(early.name),
         'the card went in as it was pressed: front-audio: audio/' + early.name + ', and the recording in the deck\'s audio/');
  await sleep(1300);
  assert((await files(TRAY)).includes(early.name) && await page.evaluate(() => ankiOpen),
         'the clip is still in the tray, and the sheet opened since is still open');

  // the sheet closes itself a moment after an Anki save -- but not from under
  // the cut editor opened while the save was out
  const slowAnki = u => new URL(u).pathname === '/anki/cards';
  await page.route(slowAnki, hold);
  await page.waitForFunction(() => document.getElementById('adeck').dataset.of === 'deck' && document.getElementById('adeck').value !== '');
  await page.click('#atanki');
  await page.waitForFunction(() => document.getElementById('adeck').dataset.of === 'anki');
  await page.selectOption('#adeck', '');
  await page.fill('#adecknew', 'English::Early');
  await page.click('#asave');
  await page.click('#asnd');
  await page.waitForSelector('.pc-root .pc-cut');
  await page.waitForFunction(() => /saved ✓/.test(document.getElementById('astat').textContent), null, {timeout: 10000});
  await sleep(1300);
  assert(await page.evaluate(() => ankiOpen && !document.getElementById('anki').hidden && !!document.querySelector('.pc-root')),
         'saved to Anki while the cut editor is open: the sheet stays under it');
  await page.waitForFunction(() => document.querySelector('.pc-root .pc-play').readyState >= 1, null, {timeout: 10000});
  const kept = await useClip();
  assert(await page.evaluate(() => ankiOpen) && await shown('#asndprev') && (await files(TRAY)).includes(kept.name),
         'and the clip it cut is on the card: ' + kept.name);
  assert(held.join() === '/exercises/api/decks,/exercises/api/decks/english/closed-early/items,/anki/cards',
         'the hub was held back on each of those presses: ' + held.join());
  await page.unroute(slow, hold);
  await page.unroute(slowAnki, hold);
  await page.click('#acancel');

  /* ---------------------- b) Anki, a second card ---------------------- */
  console.log('b) the same card to Anki again, a new deck');
  await page.click('#play');
  await altWord(4, 2);
  await page.click('#atanki');
  assert(await shown('#abuild') && await shown('#atagsrow') && !(await shown('#akjolly'))
         && await page.evaluate(() => document.getElementById('asavelab').textContent) === 'save card',
         'Anki: build and tags back, no jolly, "save card"');
  await page.waitForFunction(() => document.getElementById('adeck').dataset.of === 'anki');
  // a) saved a card to English::Early, the deck picked now: a new one instead
  await page.selectOption('#adeck', '');
  await page.fill('#adecknew', 'English::Book cards');
  await openCutter('Anki');
  got = await edges();
  assert(near(got.s, want.s, 0.01) && near(got.e, want.e, 0.01),
         `the edges are the same as before: ${got.s}–${got.e}`);
  await page.click('.pc-cut [data-e="e+5"]');
  const clipB = await useClip();
  assert(clipB.name !== clipA.name, 'a clip of its own: ' + clipB.name);
  await page.click('#apreview');
  await page.waitForFunction(() => !document.getElementById('apvrow').hidden, null, {timeout: 10000});
  const pv = await page.evaluate(() => ({doc: document.getElementById('apvframe').srcdoc,
                                        box: document.getElementById('apvframe').getAttribute('sandbox')}));
  assert(pv.doc.includes(`<audio controls src="/clips/media/${clipB.name}"`) && pv.box === 'allow-same-origin',
         'the Anki preview plays the clip, in a frame with no scripts');
  await page.click('#asave');
  await page.waitForFunction(() => /saved ✓/.test(document.getElementById('astat').textContent), null, {timeout: 10000});
  const ankiDecks = (await dirs(TMP + '/anki')).flatMap(f => [f]);
  let cardFile = null, cardDir = null;
  // the card for "wind" (a) saved one for "and" to a deck of its own)
  for (const f of ankiDecks) for (const s of await dirs(`${TMP}/anki/${f}`)) {
    for (const c of await files(`${TMP}/anki/${f}/${s}/cards`, /\.json$/))
      if (JSON.parse(await Deno.readTextFile(`${TMP}/anki/${f}/${s}/cards/${c}`)).fa === 'wind') {
        cardFile = `${TMP}/anki/${f}/${s}/cards/${c}`; cardDir = `${TMP}/anki/${f}/${s}`;
      }
  }
  const card = JSON.parse(await Deno.readTextFile(cardFile));
  const media = card.snd_front && await Deno.stat(`${cardDir}/media/${card.snd_front}`).catch(() => null);
  assert(card.fa === 'wind' && card.snd_front === card.id + '-front-audio.mp3' && card.snd_back == null
         && media && media.size === (await Deno.stat(`${TRAY}/${clipB.name}`)).size,
         `the Anki card names its sound (${card.snd_front}) and the sound is in the deck's media/`);
  await page.waitForFunction(() => document.getElementById('anki').hidden, null, {timeout: 5000});
  await page.click('#play');

  /* ---------------- c) markdown, and jolly ---------------- */
  console.log('c) markdown on the clipboard, and a jolly card');
  await page.evaluate(() => {
    window.__copied = [];
    window.__realCopy = Parseh.copy;
    Parseh.copy = (text, raw) => { window.__copied.push([text, raw]); return true; };
  });
  // the gloss cloud's button (hover mode, from the header) makes a card of
  // the whole chunk, for whichever destination: it is "+ card"
  await page.click('#hovermode');
  await page.mouse.move(1, 1);
  await page.locator('.p1 [data-c="4"]').hover();
  await page.waitForFunction(() => cloudC === 4 && !document.querySelector('#cloud').hidden);
  assert(await page.evaluate(() => document.querySelector('#cloud .mkcard').textContent) === '+ card', 'the gloss cloud\'s button reads "+ card"');
  await page.click('#cloud .mkcard');
  await page.waitForFunction(() => ankiOpen && !document.getElementById('anki').hidden);
  assert(await page.evaluate(() => document.getElementById('afa').value) === 'and the wind outside', 'and it opens the sheet on the whole chunk');
  await page.click('#acancel');
  await page.click('#hovermode');
  await altWord(4, 2);
  await page.click('#atmd');
  assert(!(await shown('#adeckrow')) && !(await shown('#abuild'))
         && await page.evaluate(() => [document.getElementById('asavelab').textContent, document.getElementById('ahtitle').textContent].join('|')) === 'copy markdown|card markdown',
         'markdown: no deck row, no build, "copy markdown", the head says "card markdown"');
  await shot('sheet-markdown-desktop');
  await openCutter('markdown');
  const clipC = await useClip();
  await page.check('input[name=asndside][value=back]');
  await page.click('#asave');
  await page.waitForFunction(() => window.__copied.length === 1);
  const [copied, raw] = await page.evaluate(() => window.__copied[0]);
  const cs = await status();
  assert(raw === true && cs === 'copied ✓ — a vocabulary card for “wind”. Paste it into a studio document or a deck’s “Add exercise”: ' +
                                'the recording comes along from the clip tray when it is pasted there',
         'copied, and it says where to paste it and that the clip comes along: ' + cs);
  let rd = JSON.parse(await py(READ, copied, 'en'));
  assert(rd.types.join() === 'exercise' && rd.subtype === 'flashcard' && rd.errors.length === 0 && rd.deck === true
         && rd.fields['back-audio'] === 'audio/' + clipC.name && !('front-audio' in rd.fields)
         && rd.fields.target === '[wind]{tl}' && rd.html.includes(`src="/clips/media/audio/${clipC.name}"`),
         'the real parser reads one flashcard with no error, back-audio: audio/' + clipC.name);
  await page.click('#apreview');
  await page.waitForFunction(() => !document.getElementById('apvrow').hidden, null, {timeout: 15000});
  await page.waitForFunction(n => {
    const d = document.getElementById('apvframe').contentDocument, a = d && d.querySelector('.ex-flashcard .ex-card-audio audio');
    return a && a.getAttribute('src') === '/clips/media/audio/' + n && a.readyState >= 1;
  }, clipC.name, {timeout: 15000});
  assert(true, 'the preview draws the card as the studio does, and its recording loads');
  await shot('sheet-markdown-preview-desktop');

  // jolly: filled from the card; the clip goes where the caret was
  await page.click('#akjolly');
  const jolly = () => page.evaluate(() => ['#ajfp', '#ajfs', '#ajbp', '#ajbs'].map(s => document.querySelector(s).value));
  let j = await jolly();
  const en = await page.evaluate(() => [document.getElementById('aen').value, document.getElementById('actx').value,
                                         document.getElementById('atr').value]);
  assert(await shown('#ajollyrow') && !(await shown('#afarow')) && !(await shown('#adirrow')) && !(await shown('#asndsides'))
         && !(await shown('#apvrow')) && await shown('#asndprev .ajollyinto')
         && await page.evaluate(() => document.querySelector('#asndprev .ajollyinto').textContent) === 'in the jolly box the cursor was last in (the back\'s main text until one has been)',
         'jolly: its four fields, the word\'s rows put aside, no side to pick but where the clip went, and the vocabulary card\'s preview gone');
  assert(j[0] === '[wind]{tl}' && j[1] === en[2] && en[2] && j[2] === en[0] + '\n![](audio/' + clipC.name + ')' && j[3] === en[1],
         'filled from the card: [wind]{tl} and its transliteration on the front, the meaning and the recording on the back (its side), the sentence under it');
  await page.click('#asnddel');
  j = await jolly();
  assert(j[2] === en[0] && !(await shown('#asndprev')) && (await files(TRAY)).includes(clipC.name),
         'remove takes the recording off the card and out of its field; a copied clip stays in the tray');
  // two lines in the front's smaller field, and the caret left on the first
  await page.click('#ajfs');
  await page.keyboard.press('End');
  await page.keyboard.type(' (a noun)');
  await page.keyboard.press('Enter');
  await page.keyboard.type('said once');
  await page.keyboard.press('ArrowUp');
  await openCutter('jolly');
  const clipD = await useClip();
  j = await jolly();
  const fs = en[2] + ' (a noun)\n![](audio/' + clipD.name + ')\nsaid once';
  assert(j[1] === fs && !j[2].includes('audio/'),
         'the new clip goes into the field the caret was last in, on a line of its own after the caret\'s: ' + JSON.stringify(j[1]));
  await shot('sheet-jolly-desktop');
  await page.click('#asave');
  await page.waitForFunction(() => window.__copied.length === 2);
  rd = JSON.parse(await py(READ, (await page.evaluate(() => window.__copied[1]))[0], 'en'));
  assert(rd.errors.length === 0 && rd.deck === true && rd.fields['card-type'] === 'jolly'
         && rd.raw['front-secondary'] === fs
         && rd.html.includes(`src="/clips/media/audio/${clipD.name}"`),
         'the jolly card reads with no error, its recording in front-secondary');
  // the cursor put in the back's smaller box, nothing typed there, and a
  // clip cut again: it goes there, and the one it replaces leaves the card
  await page.click('#ajbs');
  await page.keyboard.press('End');
  await openCutter('jolly, a clip cut again');
  const clipD2 = await useClip();
  j = await jolly();
  assert(j[1] === en[2] + ' (a noun)\nsaid once' && j[3] === en[1] + '\n![](audio/' + clipD2.name + ')' && !j[0].includes('audio/') && !j[2].includes('audio/'),
         'a clip cut again goes into the box the cursor was last in, typed in or not, and the old one\'s line goes: ' + JSON.stringify(j));
  // its line taken out by hand: the copy goes without it and says so, and
  // picking vocabulary and jolly again does not put it back
  await page.fill('#ajbs', en[1]);
  await page.click('#asave');
  await page.waitForFunction(() => window.__copied.length === 3);
  assert(!(await page.evaluate(() => window.__copied[2][0])).includes('audio/')
         && await status() === 'copied ✓ — a jolly card. Paste it into a studio document or a deck’s “Add exercise” — ' +
                               'the recording is not on the card: its line was taken out of the fields',
         'a line taken out by hand: the copy names no recording, and the sheet says so: ' + await status());
  await page.click('#akvocab');
  await page.click('#akjolly');
  j = await jolly();
  assert(!j.join('\n').includes('audio/'), 'nor does picking vocabulary and jolly again put it back: ' + JSON.stringify(j));
  // a browser that will not put the markdown on the clipboard (the API
  // refuses, and so does the old copy command): shown in the sheet, selected,
  // to copy by hand -- and the clip it names stays in the tray
  await openCutter('a copy the browser refuses');
  const clipF = await useClip();
  for (let i = 0; i < 40 && (await files(TRAY)).includes(clipD2.name); i++) await sleep(100);
  assert(!(await files(TRAY)).includes(clipD2.name), 'the clip it replaced, on no card, has left the tray');
  await page.evaluate(() => {
    Parseh.copy = window.__realCopy;
    navigator.clipboard.writeText = () => Promise.reject(new DOMException('not allowed', 'NotAllowedError'));
    document.execCommand = () => false;
  });
  await page.click('#asave');
  // (whatever the sheet says of it: the assertion below reads it)
  await page.waitForFunction(() => /not copied|would not/.test(document.getElementById('astat').textContent), null, {timeout: 10000});
  const byHand = await page.evaluate(() => { const o = document.getElementById('amdout');
    return {md: o.value, focused: document.activeElement === o, selected: o.selectionStart === 0 && o.selectionEnd === o.value.length}; });
  assert(await shown('#amdrow') && byHand.focused && byHand.selected && byHand.md.includes('![](audio/' + clipF.name + ')')
         && await status() === 'not copied — the browser would not put it on the clipboard: the markdown is below, to copy by hand',
         'refused: the markdown is in the sheet, focused and selected, naming its clip, and the sheet says so: ' + await status());
  rd = JSON.parse(await py(READ, byHand.md, 'en'));
  assert(rd.errors.length === 0 && rd.deck === true && rd.fields['card-type'] === 'jolly', 'the markdown shown reads with no error');
  await page.locator('#amdrow').scrollIntoViewIfNeeded();
  await shot('sheet-markdown-by-hand-desktop');
  // a clip cut and left unused goes out of the tray when the sheet closes
  await page.click('#acancel');
  await page.waitForFunction(() => document.getElementById('anki').hidden);
  await sleep(800);
  assert((await files(TRAY)).includes(clipD.name) && (await files(TRAY)).includes(clipF.name),
         'closed: the copied clip stays, and so does the one of the markdown to copy by hand');
  await altWord(4, 2);
  assert(!(await shown('#amdrow')), 'opened again: no markdown row');
  await openCutter('a clip nobody uses');
  const clipE = await useClip();
  // cut on the vocabulary card with its side left as it was, then jolly
  // picked: no field has had the caret, so the clip goes to the back's first
  assert(await page.evaluate(() => document.querySelector('input[name=asndside]:checked').value) === 'front',
         'the side is left at its default, the front');
  await page.click('#akjolly');
  j = await jolly();
  assert(j[2] === en[0] + '\n![](audio/' + clipE.name + ')' && !j[0].includes('audio/') && !j[1].includes('audio/') && !j[3].includes('audio/'),
         'jolly picked after the clip was cut: it goes into back-primary, as a clip cut now would: ' + JSON.stringify(j));
  await page.keyboard.press('Escape');
  await page.waitForFunction(() => document.getElementById('anki').hidden);
  for (let i = 0; i < 40 && (await files(TRAY)).includes(clipE.name); i++) await sleep(100);
  assert(!(await files(TRAY)).includes(clipE.name), 'a clip put on a card and never used leaves the tray when the sheet closes');

  /* ---------------- phone width ---------------- */
  if (SHOTS) {
    await page.setViewportSize({width: 400, height: 860});
    for (const [t, name] of [['#atanki', 'anki'], ['#atdeck', 'deck'], ['#atmd', 'markdown']]) {
      await altWord(4, 2);
      await page.click(t);
      await sleep(300);
      await shot(`sheet-${name}-phone`);
      await page.locator('#asave').scrollIntoViewIfNeeded();
      await onScreen('#asave', `the sheet's button at 400 px (${name})`);
      await shot(`sheet-${name}-phone-foot`);
      if (name === 'markdown') {
        await page.click('#akjolly');
        await page.locator('#ajollyrow').scrollIntoViewIfNeeded();
        await sleep(100);
        await shot('sheet-jolly-phone');
      }
      await page.click('#acancel');
    }
    await altWord(4, 2);
    await openCutter('phone');
    await shot('cutter-phone');
    await page.keyboard.press('Escape');
    await page.click('#acancel');
    await page.setViewportSize({width: 1280, height: 860});
  }

  /* ---------------- d) a word line; no narration; no times ---------------- */
  console.log('d) a word-line chunk, a whole chunk, and nothing to cut');
  await page.goto(B + '/books/japanese/mini-ja/reader/');
  await page.waitForFunction(() => typeof SUBS !== 'undefined' && document.querySelector('.sub'));
  // 柴刈り, the third word of the line of chunk 6
  await page.locator('.p1 [data-c="6"] .wd[data-k="2"]').click({modifiers: ['Alt']});
  await page.waitForFunction(() => ankiOpen);
  assert(await page.evaluate(() => document.getElementById('afa').value) === '柴刈り', 'the word of the line: 柴刈り');
  const wantJa = await expected(6, 2, true);
  await openCutter('a word of a word line');
  got = await edges();
  assert(near(got.s, wantJa.s, 0.01) && near(got.e, wantJa.e, 0.01),
         `its edges from the line's surfaces: ${got.s}–${got.e} (${wantJa.a}–${wantJa.b} of ${wantJa.units})`);
  const trayJa = await files(TRAY);
  await page.keyboard.press('Escape');
  await page.waitForFunction(() => !document.querySelector('.pc-root'));
  assert(await page.evaluate(() => document.getElementById('asndprev').hidden && ankiOpen) && (await files(TRAY)).join() === trayJa.join(),
         'Escape: the editor closes, the sheet stays, no clip');
  await page.click('#acancel');
  await page.locator('.p1 [data-c="4"] .wd').first().click({modifiers: ['Alt']});
  await page.waitForFunction(() => ankiOpen);
  const wantChunk = await expected(4, null, false);
  await openCutter('a whole chunk');
  got = await edges();
  assert(near(got.s, wantChunk.s, 0.01) && near(got.e, wantChunk.e, 0.01) && wantChunk.a > 0,
         `a chunk of a language without spaces is its whole share: ${got.s}–${got.e} (${wantChunk.a}–${wantChunk.b} of ${wantChunk.units})`);
  await page.keyboard.press('Escape');
  await page.click('#acancel');
  // the second recording: 2.3 is in part2.mp3, and cut from it
  const late = await page.evaluate(() => +document.querySelector('.sub[data-s="5"]').dataset.from);
  await page.locator(`.p1 [data-c="${late}"] .wd`).first().click({modifiers: ['Alt']});
  await page.waitForFunction(() => ankiOpen);
  const wantN2 = await expected(late, null, false);
  await openCutter('a chunk of the second recording');
  got = await edges();
  const playsN2 = await page.evaluate(() => new URL(document.querySelector('.pc-root .pc-play').src).pathname);
  assert(wantN2.narration === 'n2' && playsN2 === '/books/japanese/mini-ja/audio/part2.mp3' && playsN2 === wantN2.file
         && near(got.s, wantN2.s, 0.01) && near(got.e, wantN2.e, 0.01),
         `a subparagraph of the second recording plays that file, and its edges are seconds into it: ${got.s}–${got.e}`);
  await page.click('.pc-cut .pc-save');
  await page.waitForFunction(() => /saved to the clip tray/.test(document.querySelector('.pc-stat').textContent), null, {timeout: 20000});
  const n2name = await page.evaluate(() => document.querySelector('.pc-saved .pc-name').textContent.split(' ')[0]);
  const n2rec = JSON.parse(await Deno.readTextFile(`${TRAY}/${n2name}.json`));
  assert(n2rec.source.narration === 'n2' && n2rec.source.book === '/books/japanese/mini-ja'
         && near(n2rec.source.start, got.s, 0.001) && near(await duration(`${TRAY}/${n2name}`), got.e - got.s, 0.06),
         'the clip is cut from n2, at those seconds: ' + JSON.stringify(n2rec.source));
  await page.keyboard.press('Escape');
  await page.click('#acancel');

  const disabled = async what => {
    const r = await page.evaluate(() => ({d: document.getElementById('asnd').disabled, t: document.getElementById('asnd').title,
                                          why: document.getElementById('asndwhy').textContent}));
    await page.waitForFunction(() => !document.getElementById('asndwhy').hidden);
    return r;
  };
  await page.goto(B + '/books/french/mini-fr/reader/');
  await page.waitForFunction(() => typeof SUBS !== 'undefined' && document.querySelector('.sub'));
  await page.locator('.p1 [data-c="1"] .wd').first().click({modifiers: ['Alt']});
  await page.waitForFunction(() => ankiOpen);
  let dis = await disabled();
  assert(dis.d && /no narration file/.test(dis.t) && dis.why === dis.t,
         'a book with no narration: "cut the audio…" is disabled, and says why: ' + dis.t);
  await page.click('#asnd', {force: true});
  assert(!(await page.evaluate(() => !!document.querySelector('.pc-root'))), '…and pressing it opens nothing');
  await page.click('#acancel');
  // a book with recordings, and a subparagraph none of them covers, or one
  // timed in a recording whose file is not here: each says its own reason
  await page.goto(B + '/books/japanese/mini-jb/reader/');
  await page.waitForFunction(() => typeof SUBS !== 'undefined' && document.querySelector('.sub'));
  assert(await page.evaluate(() => NARR.map(n => n.id).join()) === 'n1,n3', 'mini-jb: two recordings on this machine, n1 and n3');
  const altSub = async label => {
    const c = await page.evaluate(l => +[...document.querySelectorAll('.sub')]
      .find(s => s.querySelector('.lab').textContent.trim() === l).dataset.from, label);
    await page.locator(`.p1 [data-c="${c}"] .wd`).first().click({modifiers: ['Alt']});
    await page.waitForFunction(l => ankiOpen && document.getElementById('aref').textContent === l, label);
  };
  await altSub('2.3');
  dis = await disabled();
  assert(dis.d && dis.t === 'none of this book’s recordings covers 2.3 yet: add one for it, or widen what one covers, under narration'
         && dis.why === dis.t, 'a subparagraph in no recording: disabled, and it is not "no narration file": ' + dis.t);
  await page.locator('#asndrow').scrollIntoViewIfNeeded();
  await shot('sheet-uncovered-desktop');
  await page.click('#acancel');
  await altSub('1.3');
  dis = await disabled();
  assert(dis.d && dis.t === '1.3 was timed in the recording n2, whose file is not on this machine',
         'a subparagraph timed in a recording whose file is gone: disabled, and says so: ' + dis.t);
  await page.click('#acancel');
  await altSub('2.2');
  assert(await page.evaluate(() => !document.getElementById('asnd').disabled && document.getElementById('asndwhy').hidden),
         '…while 2.2, in n3, can be cut');
  await page.click('#acancel');
  await page.goto(READER);
  await page.waitForFunction(() => typeof SUBS !== 'undefined' && document.querySelector('.sub'));
  const last = await page.evaluate(() => { const s = [...document.querySelectorAll('.sub')].pop(); return +s.dataset.from; });
  await page.locator(`.p1 [data-c="${last}"] .wd`).first().click({modifiers: ['Alt']});
  await page.waitForFunction(() => ankiOpen);
  dis = await disabled();
  assert(dis.d && /no times yet/.test(dis.t), 'a subparagraph with no times: disabled, and says why: ' + dis.t);
  await page.click('#acancel');

  /* ---------------- e) no card kit ---------------- */
  console.log('e) the card kit did not load');
  {
    const KIT_GONE = 'the card kit (lib/cardkit.js) did not load: reload the page';
    const kp = await browser.newPage({viewport: {width: 1280, height: 860}});
    kp.on('pageerror', e => errors.push('no-kit pageerror: ' + e.message));
    await kp.route(/\/lib\/cardkit\.js$/, route => route.abort());
    await kp.goto(READER);
    await kp.waitForFunction(() => typeof SUBS !== 'undefined' && document.querySelector('.sub'));
    await kp.locator('.p1 [data-c="4"] .wd').nth(2).click({modifiers: ['Alt']});
    await kp.waitForFunction(() => ankiOpen);
    const cut = await kp.evaluate(() => [typeof window.ParsehCards, document.getElementById('asnd').disabled, document.getElementById('asnd').title,
                                         document.getElementById('asndwhy').getClientRects().length > 0, document.getElementById('asndwhy').textContent]);
    assert(JSON.stringify(cut) === JSON.stringify(['undefined', true, KIT_GONE, true, KIT_GONE]),
           'no card kit: "cut the audio…" is disabled, and says why under it: ' + JSON.stringify(cut));
    const said = [];
    const stat = () => kp.evaluate(() => document.getElementById('astat').textContent);
    for (const t of ['#atdeck', '#atmd']) {
      await kp.click(t);
      said.push(await stat());
      await kp.click('#asave');
      said.push(await stat());
    }
    await kp.click('#atanki');
    said.push(await stat());
    assert(JSON.stringify(said) === JSON.stringify([KIT_GONE, KIT_GONE, KIT_GONE, KIT_GONE, '']),
           'an exercise deck and markdown say so when picked and when pressed; Anki does not: ' + JSON.stringify(said));
    await kp.close();
  }

  assert(!errors.length, 'the pages threw nothing and every request of the sheet was answered: ' + errors.join('; '));
  const tb = log.join('');
  assert(!/Traceback/.test(tb), 'no traceback in the hub\'s log');
  console.log(`\nbook_cards: ${passed} checks passed`);
} finally {
  if (browser) await browser.close();
  if (hub) { try { hub.kill('SIGTERM'); await hub.status; } catch (_) {} }
  if (!Deno.env.get('PARSEH_KEEP')) await Deno.remove(TMP, {recursive: true}).catch(() => {});
  else console.log('kept ' + TMP);
}

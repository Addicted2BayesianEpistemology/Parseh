// SPDX-License-Identifier: GPL-3.0-or-later
import { chromium } from 'npm:playwright-core@1.52.0';
// Run: CHROME_BIN=/path/to/chrome PARSEH_PYTHON=/path/to/python3 deno run --allow-all tests/gloss_llm_book.mjs
//      PARSEH_KEEP=1 keeps the temporary tree, to read what was written
//      GLOSS_LLM_PROMPTS=<dir> keeps every prompt the page put on the clipboard
//
// DELETING A GLOSS, AND GLOSSING A STRETCH OF A BOOK WITH AN LLM, in the book
// reader (lib/tex2html.py) on the REAL hub: serve.main() over a temporary
// tree holding temporary copies of the fixture editions -- Persian, Japanese
// (one chunk given a word line first, so it is a \chrw), Italian, Chinese
// (glossed in Italian, so the gloss language is not always English) and the
// three-chapter English book tests/outline_harness.py makes, with the second
// paragraph of chapter 1 folded away.  Every action is the page's own: the
// pencil over a row, the chunk sheet's buttons, the region sheet's outline,
// its boxes and its buttons; the prompt is READ OFF THE CLIPBOARD the page
// wrote it to, the answer is written here out of what the clipboard held and
// PASTED into the answer box with Ctrl+V; what lands is read back off the
// .tex on disk, and off the page.
//
//  a) "delete gloss": the chunk's gloss goes from under its text, the sheet's
//     boxes empty, and the .tex holds the SAME macro with its gloss slots
//     emptied and nothing else changed (a \chrw keeps its word line); the
//     paragraph still reproduces source/paras/ (verify_book); "undo delete"
//     writes it back, byte for byte.
//  b) the region sheet opens from the chunk sheet's "gloss around here with
//     an LLM…" on the chunk's own sentence, and from the header's "gloss with
//     an LLM"; a stretch is picked in its outline with a click and a
//     shift-click; "copy the prompt" puts on the clipboard the region's
//     sentences, the deleted chunk marked todo and the others with their
//     glosses, in the book's language and its gloss language.
//  c) delete, copy, answer with exactly the deleted gloss, paste, "fill from
//     the answer": the report says filled 1; the page shows the chunk again
//     where it stands, with no reload; the .tex is what it was before the
//     delete, byte for byte.
//  d) a HOSTILE answer, rewriting every glossed chunk of a two-sentence
//     stretch: on the page and on disk nothing glossed moves, and the report
//     lists every one of them as kept.
//  e) a paragraph marked free ("this paragraph need not reproduce
//     source/paras/") with a chunk's text changed through the sheet: the
//     prompt carries the text as the .tex has it now, never the source's,
//     and an answer to it lands.
//  f) a folded paragraph inside the stretch is not in the prompt, and the
//     sheet says one was left out; an answer naming it is dropped, not
//     written; a stretch of nothing else is refused, in the server's words.
//  g) re-gloss: the box as it stands when the answer is filled decides
//     (unticked by then, a re-gloss answer writes nothing and every gloss is
//     kept); the first press of "fill from the answer" writes nothing and
//     becomes "replace N glosses — press again"; left alone, or with the
//     answer changed, it disarms; the second press replaces them.
//  i) per field: a chunk half glossed by hand (its meaning typed into an
//     empty sheet, which is saved) is kept whole by a plain fill -- nothing
//     to copy -- and, with "also fill the empty boxes of partly glossed
//     chunks" ticked, is asked for exactly its empty boxes; the answer fills
//     them and its change to the meaning somebody wrote is kept out.
//  j) the same loop on a phone, by taps.
//  k) a browser that will not put the prompt on the clipboard: the prompt is
//     shown, selected, to copy by hand, and the next press copies it.
//  l) a chunk as a draft leaves it -- a word line and the reading proposed
//     from it, nothing else -- has no gloss to delete, is asked for with its
//     proposal, and once answered is a glossed chunk like any other.
//  h) last: no page threw, logged an error, or had a request refused beyond
//     the few a temporary book is always refused (and the two refusals asked
//     for on purpose); the hub printed no traceback; the owner's config/,
//     books/, youtube/videos/ and the fixtures are as they were.
const root = await Deno.realPath(new URL('..', import.meta.url));
Deno.chdir(root);
const PY = Deno.env.get('PARSEH_PYTHON') || 'python3';
const TMP = await Deno.makeTempDir({prefix: 'parseh-gloss-llm-book-'});
// GLOSS_LLM_PROMPTS=<dir> keeps every prompt the page copied, to read
const PROMPTS = Deno.env.get('GLOSS_LLM_PROMPTS') || '';
let promptNo = 0;
const td = new TextDecoder();
let passed = 0;
const assert = (v, m) => { if (!v) throw Error('FAIL: ' + m); passed++; console.log('  ok', m); };
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const eq = (got, want, m) => assert(same(got, want),
  m + (same(got, want) ? '' : ': got ' + JSON.stringify(got) + ' want ' + JSON.stringify(want)));
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

/* ---------------- the toolbox ---------------- */
// Copies of the fixture editions under <tmp>/root/books, each built by this
// tex2html.py with its climb to lib/ written as the hub's own path
// (tests/mobile_harness.built_reader), and lib/ linked into the tree.  The
// fixtures themselves are only ever read.
const BUILD = String.raw`
import json, os, shutil, sys
from pathlib import Path
REPO = Path(os.getcwd())
sys.path[:0] = ['tests', 'lib']
import mobile_harness, outline_harness, reading, texwrite
tmp = Path(sys.argv[1])
root = tmp / 'root'
for d in (root / 'youtube' / 'videos', tmp / 'library', tmp / 'exercises', tmp / 'anki',
          tmp / 'tray', tmp / 'config'):
    d.mkdir(parents=True, exist_ok=True)
os.symlink(str(REPO / 'lib'), str(root / 'lib'))
os.symlink(str(REPO / 'youtube' / 'lib'), str(root / 'youtube' / 'lib'))

def copy(folder, slug):
    d = root / 'books' / folder / slug
    shutil.copytree(str(REPO / 'tests/fixtures/books' / folder / slug), str(d),
                    ignore=shutil.ignore_patterns('reader', '.reader-key'))
    return d

fa = copy('persian', 'mini-fa')
ja = copy('japanese', 'mini-ja')
# a word line on 山へ柴刈りに、: the chunk becomes a \chrw, which a delete must keep
texwrite.edit_chunk(str(ja / 'ch1.tex'), 6, {'words': '山(やま) へ 柴刈り(しばかり) に 、'})
it = copy('italian', 'mini-it')
zh = copy('chinese', 'mini-zh')
meta = json.loads((zh / 'book.json').read_text(encoding='utf-8'))
meta['gloss'] = 'it'                        # a Chinese book glossed in Italian
(zh / 'book.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
# and 看书， as a draft leaves a chunk: its word line, and the reading proposed
# from it (wordline.seed) as all it holds -- nobody's writing, so no gloss
import languages, wordline
line = '看(kàn) 书(shū) ，'
field, proposal = wordline.seed({'words': line}, languages.get('zh'))
texwrite.edit_chunk(str(zh / 'ch1.tex'), 12, {'words': line, field: proposal, 'voc': '', 'en': ''})
en = outline_harness.make_book(outline_harness.book_dir(tmp))
reading.collapse(str(en), '1:2', '1:2', True)   # chapter 1's second paragraph folded
for d in (fa, ja, it, zh, en):
    mobile_harness.built_reader(d)
print(json.dumps({k: str(v) for k, v in (('fa', fa), ('ja', ja), ('it', it), ('zh', zh),
                                         ('en', en))}))
`;
// serve.main() over the temporary tree: every store it reads or writes is in
// there -- prefs and the network door (a suite once turned the owner's theme
// dark in the real config/), the offline door's two memories, the studio
// library, the decks, the Anki store and the clip tray
const SERVE = String.raw`
import sys
from pathlib import Path
sys.path[:0] = ['markdown/exlex', 'markdown/app', 'youtube/lib', 'lib', '.']
tmp, port = Path(sys.argv[1]), sys.argv[2]
import prefs, network, offline
prefs.STORE = str(tmp / 'config' / 'prefs.json')
network.STORE = str(tmp / 'config' / 'network.json')
# and the LaTeX drawings' themes, their drawings and their packages
import latexthemes, latexdraw, texpackages
latexthemes.STORE = str(tmp / 'config' / 'latex.json')
latexdraw.DRAWN = str(tmp / 'latex-drawn')
texpackages.TREE = str(tmp / 'texmf')
offline.DIGESTS = str(tmp / 'config' / 'digests.json')
offline.WHERES = str(tmp / 'config' / 'wheres.json')
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
// every chunk of a chapter file as texwrite reads it
const CHUNKS = String.raw`
import json, sys
sys.path.insert(0, 'lib')
import texwrite
print(json.dumps(texwrite.read_chunks(sys.argv[1]), ensure_ascii=False))
`;
// the file as it must stand once chunk n of `before` has its gloss deleted:
// the same call, the same macro, its colour, text and word line as written,
// and every gloss slot it has emptied -- nothing else in the file moved
const DELETED = String.raw`
import io, sys
sys.path.insert(0, 'lib')
import texwrite
before, n = sys.argv[1], int(sys.argv[2])
text = io.open(before, encoding='utf-8', newline='').read()
r = texwrite.read_chunks(before)[n]
a, b = r['span']
call = '\\' + r['macro'] + ''.join(
    '{%s}' % (r['col_tex'] if f == 'col' else '' if f in ('kana', 'tr', 'voc', 'en') else r[f])
    for f in texwrite.SLOTS[r['macro']])
sys.stdout.buffer.write((text[:a] + call + text[b:]).encode('utf-8'))
`;
const chunksOf = async path => JSON.parse(await py(CHUNKS, path));
// A reader the hub has rebuilt after a write links lib/ by the climb from
// where it stands to the checkout, which a page served from the temporary
// root cannot follow: built again here, the climb written as the hub's own
// path, before the book is opened in a new page (tests/outline_harness.py's
// relink).  A page already open never reloads, and needs none.
const RELINK = String.raw`
import sys
from pathlib import Path
sys.path[:0] = ['tests', 'lib']
import mobile_harness
mobile_harness.built_reader(Path(sys.argv[1]))
`;
async function deletedText(bytes, n) {
  const f = TMP + '/before.tex';
  await Deno.writeFile(f, bytes);
  const r = await new Deno.Command(PY, {args: ['-c', DELETED, f, String(n)], cwd: root,
                                        stdout: 'piped', stderr: 'piped'}).output();
  if (!r.success) throw Error(td.decode(r.stderr));
  return r.stdout;
}
async function verifyBook(dir) {
  const r = await run(PY, ['lib/verify_book.py', '--book', dir]);
  return {code: r.code, out: (r.out + r.err).trim()};
}
// the ```json block the prompt ends with: the data, as the LLM receives it
function dataOf(prompt) {
  const at = prompt.lastIndexOf('```json\n');
  if (at < 0) throw Error('the prompt has no ```json block');
  const body = prompt.slice(at + 8);
  return JSON.parse(body.slice(0, body.indexOf('\n```')));
}
const fence = doc => '```json\n' + JSON.stringify(doc, null, 2) + '\n```\n';
// the report's counts, as the sheet words them
const counts = rep => (rep.match(/filled \d+ · completed \d+ · replaced \d+/) || [rep.slice(0, 120)])[0];
const GLOSS = ['kana', 'tr', 'voc', 'en'];
// a chunk as written, without where it sits in the file (which an edit to an
// earlier chunk of the same file moves)
const fields = x => [x.macro, x.col, x.fa, x.kana, x.tr, x.voc, x.en, x.words, x.label];

// the owner's own files, which nothing here may touch: their digests now,
// compared at the end -- all but the offline door's two memories in config/,
// which his own running hub may write to meanwhile, and which are searched
// for this run's tree instead
const OWN = String.raw`
import hashlib, json, os, sys
tmp = sys.argv[1]
out, leaks = {}, []
for top in ('config', 'books', 'youtube/videos', 'tests/fixtures/books'):
    for d, _, files in os.walk(top):
        if '/reader' in d.replace(os.sep, '/') + '/' and top == 'tests/fixtures/books':
            continue                    # build output, gitignored
        for f in files:
            p = os.path.join(d, f)
            if p.replace(os.sep, '/') in ('config/digests.json', 'config/wheres.json'):
                # the offline door's memories, which the owner's own hub
                # writes as he reads: never compared, only searched for a
                # path of this run's tree
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

const errors = [];
let hub = null, browser = null;
const log = [];
try {
  const B0 = JSON.parse((await py(BUILD, TMP)).trim().split('\n').pop());
  const port = freePort();
  hub = new Deno.Command(PY, {args: ['-c', SERVE, TMP, String(port)], cwd: root,
                              stdout: 'piped', stderr: 'piped'}).spawn();
  drain(hub.stdout, log); drain(hub.stderr, log);
  const B = `http://127.0.0.1:${port}`;
  const until = Date.now() + 60000;
  for (;;) {
    try { const r = await fetch(B + '/clips/api/status'); await r.body?.cancel(); if (r.ok) break; } catch (_) {}
    if (Date.now() > until) throw Error('the hub did not start:\n' + log.join(''));
    await sleep(250);
  }
  browser = await chromium.launch({executablePath: Deno.env.get('CHROME_BIN'), headless: true});
  let context = await browser.newContext({viewport: {width: 1280, height: 900}});
  // the clipboard, both ways: the page writes the prompt, the test reads it;
  // the test writes the answer, and Ctrl+V pastes it into the answer box
  await context.grantPermissions(['clipboard-read', 'clipboard-write'], {origin: B});

  /* ---------------- helpers over a page ---------------- */
  // WHAT A PAGE MAY BE REFUSED, and nothing else.  A book with no recording
  // has no timings.json, and a machine with no translation model installed
  // has no /mt/<pair>/meta.json: the reader asks for both on load and does
  // without them.  /favicon.ico is the browser's own question, which the hub
  // has never answered.  The one refusal asked for on purpose (e) is let
  // through by name, while it is being asked for, and counted.
  const optional = (status, method, path) => status === 404 && method === 'GET' &&
    (/^\/books\/[^/]+\/[^/]+\/timings\.json$/.test(path) || /^\/mt\/[^/]+\/meta\.json$/.test(path) ||
     path === '/favicon.ico');
  const allowed = [];                         // what was refused as expected
  let refusing = null;                        // the refusal asked for now
  const letThrough = (status, method, path) =>
    optional(status, method, path) || (refusing && refusing(status, method, path));
  async function reader(url, name, init) {
    const page = await context.newPage();
    if (init) await page.addInitScript(init);
    page.on('pageerror', e => errors.push(name + ' pageerror: ' + e.message));
    const said = new Map();                   // a failed load's URL -> status
    page.on('response', r => {
      const u = new URL(r.url()), m = r.request().method();
      if (r.status() < 400) return;
      said.set(r.url(), r.status());
      if (letThrough(r.status(), m, u.pathname)) allowed.push(name + ' ' + r.status() + ' ' + m + ' ' + u.pathname);
      else errors.push(name + ' ' + r.status() + ' ' + m + ' ' + u.pathname);
    });
    // the console's "Failed to load resource" for a refusal let through above
    // says nothing new; any other error it logs is one
    page.on('console', m => {
      if (m.type() !== 'error') return;
      const at = (m.location() || {}).url || '';
      if (/^Failed to load resource/.test(m.text()) && at) {
        let path = '';
        try { path = new URL(at).pathname; } catch (_) {}
        if (optional(404, 'GET', path) || (said.has(at) && !errors.some(e => e.endsWith(' ' + path)))) return;
      }
      errors.push(name + ' console: ' + m.text() + (at ? ' (' + at + ')' : ''));
    });
    page.on('requestfailed', r => errors.push(name + ' request failed: ' + r.method() + ' ' + new URL(r.url()).pathname +
                                                ' (' + (r.failure() || {}).errorText + ')'));
    await page.goto(B + url);
    await page.waitForFunction(() => typeof SRC !== 'undefined' && window.Parseh && document.querySelector('.sub'));
    // a mark on the page itself: a reload would take it away
    await page.evaluate(() => { window.__stay = 'never reloaded'; });
    return page;
  }
  const stayed = page => page.evaluate(() => window.__stay === 'never reloaded');
  const row = n => '.pass.p2 .row[data-c="' + n + '"]';
  // what the page shows under a chunk's text, as a person reads it
  const glOf = (page, n) => page.evaluate(sel => {
    const g = document.querySelector(sel + ' .gl');
    return g ? g.textContent.replace(/\s+/g, ' ').trim() : null;
  }, row(n));
  const allGl = page => page.evaluate(() => Object.fromEntries(
    [...document.querySelectorAll('.pass.p2 .row[data-c]')].map(r => {
      const g = r.querySelector('.gl');
      return [r.dataset.c, g ? g.textContent.replace(/\s+/g, ' ').trim() : null];
    })));
  const boxes = page => page.evaluate(() => Object.fromEntries(
    ['kana', 'tr', 'voc', 'en'].map(f => [f, document.getElementById('ch' + f).value])));
  const text = (page, sel) => page.evaluate(sel => document.querySelector(sel).textContent, sel);
  const shown = (page, sel) => page.evaluate(sel => {
    const el = document.querySelector(sel);
    return !!el && !el.hidden && el.getClientRects().length > 0 && getComputedStyle(el).visibility === 'visible';
  }, sel);
  // really on screen and on top: a rect inside the window, and the element
  // the browser finds at its own centre
  async function onScreen(page, sel, what) {
    const r = await page.evaluate(sel => {
      const b = document.querySelector(sel), rc = b.getBoundingClientRect();
      const hit = document.elementFromPoint(rc.left + rc.width / 2, rc.top + Math.min(rc.height / 2, 12));
      return {l: rc.left, t: rc.top, r: rc.right, b: rc.bottom, w: innerWidth, h: innerHeight,
              hit: !!hit && (b === hit || b.contains(hit))};
    }, sel);
    assert(r.l >= 0 && r.t >= 0 && r.r <= r.w + 0.5 && r.r - r.l > 10 && r.hit,
           `${what} is on screen and on top (${Math.round(r.l)},${Math.round(r.t)}–${Math.round(r.r)},${Math.round(r.b)} in ${r.w}x${r.h})`);
  }
  // the pencil over the row under the pointer, pressed: the chunk sheet
  async function openChunk(page, n) {
    await page.mouse.move(1, 1);
    await page.evaluate(async sel => {
      document.querySelector(sel).scrollIntoView({block: 'center'});
      await new Promise(r => setTimeout(r, 250));
    }, row(n));
    await page.hover(row(n));
    await page.waitForFunction(n => !document.querySelector('#chpen').hidden && penFor && +penFor.dataset.c === n, n);
    await page.click('#chpen');
    await page.waitForFunction(n => chOpen && chN === n, n);
  }
  const waitStat = (page, re) => page.waitForFunction(
    re => new RegExp(re).test(document.querySelector('#chstat').textContent), re.source, {timeout: 20000});
  // the clipboard as the page left it
  const clip = page => page.evaluate(() => navigator.clipboard.readText());
  // (by the browser's own call, where a page of k) has stood in front of it)
  const setClip = (page, s) => page.evaluate(s => (window.__realWrite ||
    navigator.clipboard.writeText.bind(navigator.clipboard))(s), s);
  // an answer PASTED: onto the clipboard, then Ctrl+V into the empty box
  async function paste(page, answer) {
    await setClip(page, answer);
    await page.click('#rgans');
    await page.keyboard.press('Control+A');
    await page.keyboard.press('Delete');
    await page.keyboard.press('Control+V');
    await page.waitForFunction(a => document.querySelector('#rgans').value === a, answer, {timeout: 5000});
  }
  // the SUBS index and label of the subparagraph a chunk stands in
  const subOf = (page, n) => page.evaluate(sel => {
    const s = document.querySelector(sel).closest('.sub');
    return {s: +s.dataset.s, label: String(SUBS[+s.dataset.s][5])};
  }, row(n));
  // the region sheet's outline: a chapter opened all the way down, then a
  // sentence of it clicked (with Shift: the stretch to it)
  async function openOutline(page, ci) {
    const ch = page.locator('#rgbox .oltree > li.ol-ch').nth(ci);
    if ((await ch.getAttribute('aria-expanded')) === 'false') await ch.locator(':scope > .olr > .oltw').click();
    for (let guard = 0; guard < 60; guard++) {
      const shut = ch.locator('li[aria-expanded="false"]');
      if (!(await shut.count())) return ch;
      await shut.first().locator(':scope > .olr > .oltw').click();
    }
    throw Error('the outline would not open');
  }
  async function clickSentence(page, ci, label, shift) {
    const ch = await openOutline(page, ci);
    const esc = label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const li = ch.locator('li.ol-s').filter({has: page.locator(':scope > .olr > .olk', {hasText: new RegExp('^' + esc + '$')})});
    eq(await li.count(), 1, `the outline has sentence ${label} in chapter ${ci + 1} once`);
    await li.locator(':scope > .olr').click(shift ? {modifiers: ['Shift']} : {});
  }
  const pick = page => page.evaluate(() => {
    const p = rgPicker && rgPicker.get();
    return p ? {lo: p.lo, hi: p.hi} : null;
  });
  // "copy the prompt", pressed with a sentinel on the clipboard -> what the
  // clipboard then holds, and the summary line under the button
  async function copyPrompt(page) {
    await setClip(page, 'SENTINEL — not written by the page');
    await page.click('#rgcopy');
    // "writing the prompt…" is said the moment it is pressed; whatever comes
    // after it is the answer
    await page.waitForFunction(() => {
      const t = document.querySelector('#rgsum').textContent;
      return t && !/^writing the prompt…/.test(t);
    }, null, {timeout: 20000});
    const prompt = await clip(page);
    if (PROMPTS && prompt !== 'SENTINEL — not written by the page')
      await Deno.writeTextFile(`${PROMPTS}/${String(++promptNo).padStart(2, '0')}.md`, prompt);
    return {prompt, sum: await text(page, '#rgsum')};
  }
  async function fill(page) {
    await page.click('#rgfill');
    await page.waitForFunction(() => {
      const t = document.querySelector('#rgreport').textContent;
      return !document.querySelector('#rgreprow').hidden && t && !/^(reading the answer|replacing)…/.test(t);
    }, null, {timeout: 30000});
    return text(page, '#rgreport');
  }

  /* ---------------- a) to d), book by book ---------------- */
  // n: the chunk whose gloss is deleted; next: the sentence after its own,
  // which the header's pick stretches to
  const BOOKS = [
    {key: 'fa', name: 'Persian', code: 'fa', gloss: 'English', gcode: 'en', n: 1,
     reader: '/books/persian/mini-fa/reader/'},
    {key: 'ja', name: 'Japanese', code: 'ja', gloss: 'English', gcode: 'en', n: 6, words: true,
     reader: '/books/japanese/mini-ja/reader/'},
    {key: 'it', name: 'Italian', code: 'it', gloss: 'English', gcode: 'en', n: 1,
     reader: '/books/italian/mini-it/reader/'},
    {key: 'zh', name: 'Chinese', code: 'zh', gloss: 'Italian', gcode: 'it', n: 4,
     reader: '/books/chinese/mini-zh/reader/'},
  ];
  for (const bk of BOOKS) {
    console.log(`\n${bk.name} (${bk.code}), glossed in ${bk.gloss}: chunk ${bk.n}`);
    const dir = B0[bk.key], path = dir + '/ch1.tex';
    const page = await reader(bk.reader, bk.code);
    const original = await Deno.readFile(path);
    const recs = await chunksOf(path);
    const r = recs[bk.n];
    const glAll = await allGl(page);
    const glN = glAll[bk.n];
    assert(glN && glN.includes(r.en), `${bk.code}: chunk ${bk.n} shows its gloss under its text to begin with («${r.en}»)`);
    if (bk.words) eq(r.macro, 'chrw', `${bk.code}: chunk ${bk.n} is a \\chrw, with its word line`);

    /* a) delete, and undo */
    await openChunk(page, bk.n);
    eq(await page.evaluate(() => {
      const d = document.querySelector('#chdel'), u = document.querySelector('#chundo');
      return [!d.hidden, d.disabled, u.hidden, d.textContent];
    }), [true, false, true, 'delete gloss'], `${bk.code}: the chunk sheet offers "delete gloss", and no undo yet`);
    await page.click('#chdel');
    await waitStat(page, /^gloss deleted/);
    await page.waitForFunction(() => !document.querySelector('#chundo').hidden);
    eq(await boxes(page), {kana: '', tr: '', voc: '', en: ''}, `${bk.code}: after "delete gloss" the sheet's gloss boxes are empty`);
    eq(await page.evaluate(() => [document.querySelector('#chdel').disabled, document.querySelector('#chundo').textContent]),
       [true, 'undo delete'], `${bk.code}: delete is greyed out on a chunk with nothing to delete, and "undo delete" is offered`);
    eq(await glOf(page, bk.n), '', `${bk.code}: the gloss is gone from under the chunk's text on the page`);
    assert(await stayed(page), `${bk.code}: without a reload`);
    const afterDel = await Deno.readFile(path);
    assert(bytesEqual(afterDel, await deletedText(original, bk.n)),
           `${bk.code}: the .tex holds the same \\${r.macro} with its gloss slots emptied, and nothing else changed`);
    const nowRecs = await chunksOf(path);
    eq([nowRecs[bk.n].macro, nowRecs[bk.n].fa, nowRecs[bk.n].words, nowRecs[bk.n].col],
       [r.macro, r.fa, r.words, r.col], `${bk.code}: macro, text, word line and colour are all still there`);
    if (bk.words) assert(nowRecs[bk.n].words.includes('柴刈り(しばかり)'), `${bk.code}: the \\chrw keeps its word line`);
    let v = await verifyBook(dir);
    assert(v.code === 0 && / 0 mismatched/.test(v.out), `${bk.code}: the paragraph still reproduces source/paras/ (verify_book: ${v.out.split('\n').pop().replace(/^.*\]: /, '')})`);
    await page.click('#chundo');
    await waitStat(page, /^the deleted gloss is written back/);
    assert(bytesEqual(await Deno.readFile(path), original), `${bk.code}: "undo delete" writes the gloss back, the .tex byte for byte what it was`);
    eq(await glOf(page, bk.n), glN, `${bk.code}: and the page shows it under the text again`);
    eq(await page.evaluate(() => [document.querySelector('#chundo').hidden, document.querySelector('#chdel').disabled]),
       [true, false], `${bk.code}: undo is spent, and delete is offered again`);
    eq(await boxes(page), {kana: r.kana, tr: r.tr, voc: r.voc, en: r.en}, `${bk.code}: the boxes hold the gloss again`);

    /* b) + c) delete, the region sheet from the chunk sheet, copy, answer, paste, fill */
    await page.click('#chdel');
    await waitStat(page, /^gloss deleted/);
    const {s, label} = await subOf(page, bk.n);
    await page.click('#chrgn');
    await page.waitForFunction(() => rgShown && !chOpen);
    await onScreen(page, '#rgbox', `${bk.code}: "gloss around here with an LLM…" opens the region sheet, which`);
    eq(await pick(page), {lo: s, hi: s}, `${bk.code}: it starts picked on the chunk's own sentence (${label})`);
    const tag = await page.evaluate(n => { const el = document.querySelector('.pass.p2 .row[data-c="' + n + '"]');
                                          el.__mine = 'this very element'; return true; }, bk.n);
    let {prompt, sum} = await copyPrompt(page);
    assert(prompt !== 'SENTINEL — not written by the page' && prompt.length > 1000,
           `${bk.code}: "copy the prompt" put the prompt on the clipboard (${prompt.length} characters)`);
    assert(/on the clipboard/.test(sum) && /1 to gloss/.test(sum), `${bk.code}: the sheet says so: ${JSON.stringify(sum.split('\n')[0])}`);
    assert(prompt.includes(`- language: ${bk.name} (\`${bk.code}\`)`) &&
           prompt.includes(`- gloss language: **${bk.gloss}** (\`${bk.gcode}\`)`) &&
           new RegExp(`^# Gloss part of an? ${bk.name} book, in ${bk.gloss}, for Parseh`).test(prompt),
           `${bk.code}: the prompt is for a ${bk.name} book glossed in ${bk.gloss}`);
    let data = dataOf(prompt);
    const inSentence = recs.filter(x => x.label === r.label);
    eq(data.sentences.map(x => x.at), ['ch1:' + r.label], `${bk.code}: it holds the one sentence, ${r.label}`);
    const sent = data.sentences[0].chunks;
    eq(sent.map(c => c.fa), inSentence.map(x => x.fa), `${bk.code}: every chunk of it, divided as the .tex divides it`);
    const j = inSentence.findIndex(x => x.index === bk.n);
    eq(Object.keys(sent[j]).filter(k => GLOSS.includes(k)), [], `${bk.code}: the deleted chunk carries no gloss`);
    eq(sent[j].todo, true, `${bk.code}: and is marked todo`);
    if (bk.words) eq(sent[j].words, r.words, `${bk.code}: with its word line, read-only`);
    assert(sent.every((c, k) => k === j || (!c.todo && GLOSS.every(f => (c[f] || '') === (inSentence[k][f] || '')))),
           `${bk.code}: every other chunk is sent with its gloss exactly as the .tex has it, and not todo`);

    // the answer: what the clipboard held, with exactly the deleted gloss
    const answer = structuredClone(data);
    const mine = answer.sentences[0].chunks[j];
    delete mine.todo;
    for (const f of GLOSS) if (r[f]) mine[f] = r[f];
    await paste(page, fence(answer));
    assert(true, `${bk.code}: the answer is pasted into "the LLM's answer" with Ctrl+V`);
    let rep = await fill(page);
    assert(/filled 1 · completed 0 · replaced 0/.test(rep) && !/nothing was written/.test(rep),
           `${bk.code}: "fill from the answer" reports ${JSON.stringify(counts(rep))}`);
    eq(await page.evaluate(() => document.querySelectorAll('#rgreport details').length), 0,
       `${bk.code}: and nothing kept, dropped or unanswered`);
    assert(bytesEqual(await Deno.readFile(path), original), `${bk.code}: the .tex is byte for byte what it was before the delete`);
    eq(await glOf(page, bk.n), glN, `${bk.code}: the page shows the chunk's gloss again`);
    eq(await page.evaluate(n => document.querySelector('.pass.p2 .row[data-c="' + n + '"]').__mine, bk.n),
       'this very element', `${bk.code}: painted in place, into the same element`);
    assert(await stayed(page), `${bk.code}: with no reload`);
    eq(await page.evaluate(n => SRC[n].slice(2, 6), bk.n), [r.kana, r.tr, r.voc, r.en],
       `${bk.code}: and what the page holds for its sheets is the gloss again`);
    await page.click('#rgclose');
    await page.waitForFunction(() => !rgShown && document.querySelector('#rgbox').hidden);

    /* d) the header's sheet, a stretch of two sentences, and a hostile answer */
    await openChunk(page, bk.n);
    eq(await shown(page, '#chundo'), true, `${bk.code}: the chunk sheet still offers to undo the delete it made (kept until reload)`);
    await page.click('#chdel');
    await waitStat(page, /^gloss deleted/);
    await page.click('#chcancel');
    await page.waitForFunction(() => !chOpen);
    await page.click('#rgn');
    await page.waitForFunction(() => rgShown);
    await onScreen(page, '#rgbox', `${bk.code}: the header's "gloss with an LLM" opens the region sheet, which`);
    eq(await pick(page), {lo: s, hi: s}, `${bk.code}: and it opens on what was picked when it closed`);
    const next = await page.evaluate(s => String(SUBS[s + 1][5]), s);
    await clickSentence(page, 0, label, false);
    await clickSentence(page, 0, next, true);
    eq(await pick(page), {lo: s, hi: s + 1}, `${bk.code}: a click on ${label} and a shift-click on ${next} pick the two`);
    assert(/2 subparagraphs/.test(await text(page, '#rgbox .olsay')), `${bk.code}: and the outline says so: ${JSON.stringify(await text(page, '#rgbox .olsay'))}`);
    ({prompt, sum} = await copyPrompt(page));
    data = dataOf(prompt);
    const after1 = recs.find(y => y.index > inSentence[inSentence.length - 1].index).label;
    const two = recs.filter(x => x.label === r.label || x.label === after1);
    eq(data.sentences.map(x => x.at), ['ch1:' + r.label, 'ch1:' + two[two.length - 1].label],
       `${bk.code}: the clipboard holds the two sentences`);
    const flat = data.sentences.flatMap(x => x.chunks);
    eq(flat.map(c => c.fa), two.map(x => x.fa), `${bk.code}: every chunk of them`);
    eq(flat.filter(c => c.todo).map(c => c.fa), [r.fa], `${bk.code}: the deleted chunk the only one todo`);
    const glossedHere = flat.filter(c => !c.todo).length;
    assert(new RegExp(`${two.length} chunks, 1 to gloss, ${glossedHere} glossed sent as context`).test(sum),
           `${bk.code}: the summary counts them: ${JSON.stringify(sum.split('\n')[0])}`);
    const beforeHostile = await Deno.readFile(path);
    const hostile = structuredClone(data);
    for (const c of hostile.sentences.flatMap(x => x.chunks)) {
      if (c.todo) { delete c.todo; for (const f of GLOSS) if (r[f]) c[f] = r[f]; continue; }
      c.en = 'REWRITTEN ' + (c.en || '');
      c.tr = 'rewritten';
      c.voc = '';
      if (bk.words) c.kana = 'かきかえ';
    }
    await paste(page, fence(hostile));
    rep = await fill(page);
    assert(/filled 1 · completed 0 · replaced 0/.test(rep), `${bk.code}: the hostile answer fills the one chunk to do: ${JSON.stringify(counts(rep))}`);
    const kept = await page.evaluate(() => {
      const d = [...document.querySelectorAll('#rgreport details')].find(x => /^kept/.test(x.querySelector('summary').textContent));
      return d ? {head: d.querySelector('summary').textContent, items: [...d.querySelectorAll('li')].map(li => li.textContent)} : null;
    });
    assert(kept && kept.items.length === glossedHere && kept.items.every(t => /already glossed/.test(t)),
           `${bk.code}: the report lists every one of the ${glossedHere} glossed chunks as kept: ${JSON.stringify(kept && kept.head)}`);
    assert(bytesEqual(await Deno.readFile(path), original),
           `${bk.code}: on disk nothing that was glossed moved -- the .tex is the original, byte for byte`);
    eq(await allGl(page), glAll, `${bk.code}: and on the page every chunk shows the gloss it had`);
    assert(!bytesEqual(beforeHostile, original), `${bk.code}: (the chunk it filled was blank on disk before that answer)`);
    await page.keyboard.press('Escape');
    await page.waitForFunction(() => !rgShown);
    await page.close();
  }

  /* ---------------- e) a free paragraph, its text changed ---------------- */
  console.log('\ne) a paragraph marked free, a chunk\'s text changed through the sheet (Italian)');
  {
    const dir = B0.it, path = dir + '/ch1.tex';
    await py(RELINK, dir);
    const page = await reader('/books/italian/mini-it/reader/', 'it-free');
    const n = 3, recs = await chunksOf(path), r = recs[n];
    eq(r.fa, 'un legno di lusso,', 'the chunk as the fixture has it');
    const source = await Deno.readTextFile(dir + '/source/paras/ch1_p00.txt');
    assert(source.includes('un legno di lusso,'), 'and as source/paras/ has it');
    await openChunk(page, n);
    // the text alone, changed, is refused while the paragraph is checked
    await page.fill('#chfa', 'un legno di gran lusso,');
    const was = allowed.length;
    refusing = (status, method, path) => status === 400 && method === 'POST' && path.endsWith('/reader/__edit/chunk');
    await page.click('#chsave');
    await page.waitForFunction(() => document.querySelector('#chstat').className === 'bad', null, {timeout: 20000});
    refusing = null;
    eq(allowed.length - was, 1, 'a changed text is refused while the paragraph must reproduce its source: ' +
       JSON.stringify((await text(page, '#chstat')).split('\n')[0].slice(0, 90)));
    eq((await chunksOf(path))[n].fa, 'un legno di lusso,', 'and nothing was written');
    // the region sheet is not opened over boxes holding what nobody saved
    await page.click('#chrgn');
    await page.waitForFunction(() => /not saved yet/.test(document.querySelector('#chstat').textContent));
    eq(await page.evaluate(() => [chOpen, rgShown, document.querySelector('#chfa').value]), [true, false, 'un legno di gran lusso,'],
       '"gloss around here with an LLM…" over unsaved boxes says so, and leaves the sheet and its boxes as they are');
    await page.check('#chfree');
    await page.click('#chsave');
    await waitStat(page, /^saved fa/);
    const reading = JSON.parse(await Deno.readTextFile(dir + '/reading.json'));
    assert((reading.free || []).includes('1:1'), 'ticking "this paragraph need not reproduce source/paras/" and saving marks the paragraph free in reading.json');
    eq((await chunksOf(path))[n].fa, 'un legno di gran lusso,', 'and the changed text is in the .tex');
    eq(await Deno.readTextFile(dir + '/source/paras/ch1_p00.txt'), source, 'source/paras/ is untouched');
    await page.click('#chdel');
    await waitStat(page, /^gloss deleted/);
    await page.click('#chrgn');
    await page.waitForFunction(() => rgShown);
    const {prompt} = await copyPrompt(page);
    const data = dataOf(prompt);
    const chunks = data.sentences.flatMap(x => x.chunks);
    eq(data.sentences.map(x => x.at), ['ch1:1.2'], 'the prompt holds the chunk\'s sentence');
    eq(chunks.filter(c => c.todo).map(c => c.fa), ['un legno di gran lusso,'],
       'the prompt carries the text as the .tex has it now');
    assert(!chunks.some(c => c.fa === 'un legno di lusso,') && !prompt.includes('un legno di lusso,'),
           'and never the source\'s text');
    const answer = structuredClone(data);
    for (const c of answer.sentences.flatMap(x => x.chunks))
      if (c.todo) { delete c.todo; Object.assign(c, {tr: 'un lénnyo di gran lusso', voc: r.voc, en: 'a very fine wood,'}); }
    await paste(page, fence(answer));
    const rep = await fill(page);
    assert(/filled 1 · completed 0 · replaced 0/.test(rep), 'an answer to it lands: ' + JSON.stringify(counts(rep)));
    const now = (await chunksOf(path))[n];
    eq([now.fa, now.tr, now.voc, now.en], ['un legno di gran lusso,', 'un lénnyo di gran lusso', r.voc, 'a very fine wood,'],
       'the .tex holds the changed text and the new gloss');
    assert((await glOf(page, n)).includes('a very fine wood,') && await stayed(page), 'and the page shows it, with no reload');
    // the gloss deleted before the LLM's went in is still the page's to put back
    await page.click('#rgclose');
    await openChunk(page, n);
    eq(await boxes(page), {kana: '', tr: 'un lénnyo di gran lusso', voc: r.voc, en: 'a very fine wood,'},
       'the chunk sheet opened on it again holds the LLM\'s gloss');
    assert(await shown(page, '#chundo'), 'and still offers "undo delete"');
    await page.click('#chundo');
    await waitStat(page, /^the deleted gloss is written back/);
    const back = (await chunksOf(path))[n];
    eq([back.fa, back.tr, back.voc, back.en], ['un legno di gran lusso,', r.tr, r.voc, r.en],
       'which writes back the gloss that was deleted, over the LLM\'s, on the changed text');
    assert((await glOf(page, n)).includes(r.en), 'and the page shows it');
    await page.close();
  }

  /* ---------------- i) per field ---------------- */
  console.log('\ni) a chunk half glossed by hand, and "also fill the empty boxes of partly glossed chunks" (Persian)');
  {
    const dir = B0.fa, path = dir + '/ch1.tex';
    await py(RELINK, dir);
    const page = await reader('/books/persian/mini-fa/reader/', 'fa-perfield');
    const original = await Deno.readFile(path);
    const n = 2, r = (await chunksOf(path))[n];
    eq([r.voc, !!r.tr, !!r.en], ['', true, true], 'a chunk glossed with no vocabulary line');
    await openChunk(page, n);
    await page.click('#chdel');
    await waitStat(page, /^gloss deleted/);
    // one box filled, by hand: half a gloss, which the sheet saves
    await page.fill('#chen', r.en);
    await page.click('#chsave');
    await waitStat(page, /^saved en/);
    const half = (await chunksOf(path))[n];
    eq([half.tr, half.voc, half.en], ['', '', r.en], 'its meaning typed into the empty sheet is saved on its own: half glossed');
    await page.click('#chrgn');
    await page.waitForFunction(() => rgShown);
    let {prompt, sum} = await copyPrompt(page);
    assert(/nothing was copied/.test(sum) && prompt === 'SENTINEL — not written by the page',
           'a plain fill leaves a chunk with any gloss as it is: nothing to gloss, nothing copied');
    await page.check('#rgperfield');
    ({prompt, sum} = await copyPrompt(page));
    const data = dataOf(prompt);
    const todo = data.sentences.flatMap(x => x.chunks).filter(c => c.todo);
    eq(todo.map(c => [c.fa, c.todo, c.en]), [[r.fa, ['tr', 'voc'], r.en]],
       'ticked, the prompt asks that chunk for exactly its empty boxes, with the meaning it has');
    assert(/1 to gloss/.test(sum), 'and the summary counts it: ' + JSON.stringify(sum.split('\n')[0]));
    const answer = structuredClone(data);
    for (const c of answer.sentences.flatMap(x => x.chunks))
      if (c.todo) { delete c.todo; c.tr = r.tr; c.voc = ''; c.en = 'CHANGED BY THE LLM'; }
    await paste(page, fence(answer));
    const rep = await fill(page);
    assert(/filled 0 · completed 1 · replaced 0/.test(rep), 'the answer completes it: ' + JSON.stringify(counts(rep)));
    assert(/already glossed[^]*changed `en`/.test(rep), 'and its change to the meaning somebody wrote is listed as kept');
    assert(bytesEqual(await Deno.readFile(path), original),
           'the .tex holds the transliteration from the answer and the hand-typed meaning -- the original chunk, byte for byte');
    assert(!(await glOf(page, n)).includes('CHANGED') && (await glOf(page, n)).includes(r.tr) && await stayed(page),
           'and the page shows it, with no reload');
    await page.close();
  }

  /* ---------------- f) + g) a folded paragraph inside the stretch; re-gloss ---------------- */
  console.log('\nf) and g) the three-chapter English book, chapter 1 paragraph 2 folded: a stretch across it, re-glossed');
  {
    const dir = B0.en, p1 = dir + '/ch1.tex', p2 = dir + '/ch2.tex';
    const page = await reader('/books/english/outline-en/reader/', 'en');
    eq(await page.evaluate(() => FOLDED), [['1:2', '1:2']], 'chapter 1 paragraph 2 is folded away');
    const c1 = await chunksOf(p1), c2 = await chunksOf(p2);
    const t1 = await Deno.readFile(p1), t2 = await Deno.readFile(p2), t3 = await Deno.readFile(dir + '/ch3.tex');
    await page.click('#rgn');
    await page.waitForFunction(() => rgShown);
    await onScreen(page, '#rgbox', 'the header\'s "gloss with an LLM" opens the region sheet, which');
    eq(await page.evaluate(() => [document.querySelector('#rgcopy').disabled, document.querySelector('#rgfill').disabled]),
       [true, true], 'with nothing picked, neither copy nor fill can be pressed');
    // the folded paragraph alone: nothing in it can be sent, and the sheet
    // shows the server's sentence saying so
    await clickSentence(page, 0, '2.1', false);
    await clickSentence(page, 0, '2.2', true);
    {
      const was = allowed.length;
      refusing = (status, method, path) => status === 400 && method === 'POST' && path.endsWith('/reader/__region/prompt');
      const {prompt, sum} = await copyPrompt(page);
      refusing = null;
      eq(allowed.length - was, 1, 'f) a stretch that is all folded paragraph is refused');
      assert(prompt === 'SENTINEL — not written by the page' && /only paragraphs folded away in the reader/.test(sum) &&
             await page.evaluate(() => document.querySelector('#rgsum').classList.contains('bad')),
             'nothing is copied, and the sheet shows why: ' + JSON.stringify(sum));
    }
    await clickSentence(page, 0, '1.1', false);
    await clickSentence(page, 1, '1.1', true);
    const pk = await pick(page);
    eq(await page.evaluate(p => [SUBS[p.lo][5], SUBS[p.hi][5], SUBS[p.lo][2], SUBS[p.hi][2]], pk),
       ['1.1', '1.1', 0, 1], 'a click on chapter 1\'s 1.1 and a shift-click on chapter 2\'s 1.1 pick the stretch across the fold');
    assert(await page.evaluate(() => [...document.querySelectorAll('#rgbox .oltag.olfold')].length > 0),
           'the outline marks the folded paragraph inside it');
    // f) plain fill: the whole stretch is glossed, so nothing is to do --
    // then re-gloss ticked, and every chunk is
    let {prompt, sum} = await copyPrompt(page);
    assert(/nothing was copied/.test(sum) && prompt === 'SENTINEL — not written by the page',
           'with everything glossed and re-gloss not ticked, nothing is copied, and the sheet says so');
    assert(/tick re-gloss/.test(sum), 'and says what to do: ' + JSON.stringify(sum.split('\n').pop()));
    await page.check('#rgregloss');
    ({prompt, sum} = await copyPrompt(page));
    const data = dataOf(prompt);
    eq(data.sentences.map(x => x.at), ['ch1:1.1', 'ch1:1.2', 'ch2:1.1'],
       'f) the prompt holds the sentences either side of the fold, and none of the folded paragraph\'s');
    const inStretch = [...c1.filter(x => x.label === '1.1' || x.label === '1.2'), ...c2.filter(x => x.label === '1.1')];
    const flat = data.sentences.flatMap(x => x.chunks);
    eq(flat.map(c => c.fa), inStretch.map(x => x.fa), 'every chunk of them, chapter 2\'s from its own file');
    assert(flat.every(c => c.todo === true && GLOSS.every(f => !(f in c))),
           'g) re-gloss: every chunk is todo, and no gloss is sent');
    assert(!c1.filter(x => x.para === 2).some(x => prompt.includes(JSON.stringify(x.fa))),
           'f) no text of the folded paragraph is in the prompt');
    assert(/1 folded paragraph left out/.test(sum), 'f) the sheet says one folded paragraph was left out: ' + JSON.stringify(sum.split('\n')[0]));
    assert(/1 paragraph inside it is folded away/.test(prompt), 'and so does the prompt');
    const N = flat.length;
    // the answer re-glosses every chunk -- and names a folded sentence too,
    // which must not be written
    const answer = structuredClone(data);
    for (const c of answer.sentences.flatMap(x => x.chunks)) { delete c.todo; c.en = 'NEW ' + c.fa.toUpperCase(); }
    const foldedOne = c1.find(x => x.label === '2.1');
    answer.sentences.push({at: 'ch1:2.1', chunks: c1.filter(x => x.label === '2.1').map(x => ({fa: x.fa, en: 'FOLDED ' + x.fa}))});
    await paste(page, fence(answer));
    // THE BOXES AS THEY ARE WHEN THE ANSWER IS FILLED DECIDE, not as they
    // were when the prompt was copied: re-gloss unticked now, the same answer
    // is a plain fill, and every gloss it would replace is kept
    await page.uncheck('#rgregloss');
    let rep = await fill(page);
    assert(/filled 0 · completed 0 · replaced 0 — nothing was written/.test(rep),
           'g) with re-gloss unticked before the fill, the re-gloss answer writes nothing: ' + JSON.stringify(counts(rep)));
    const keptNow = await page.evaluate(() => {
      const d = [...document.querySelectorAll('#rgreport details')].find(x => /^kept/.test(x.querySelector('summary').textContent));
      return d ? d.querySelectorAll('li').length : 0;
    });
    eq(keptNow, flat.length, 'every chunk it would have replaced is listed as kept');
    assert(bytesEqual(await Deno.readFile(p1), t1) && bytesEqual(await Deno.readFile(p2), t2), 'and the files are as they were');
    await page.check('#rgregloss');
    rep = await fill(page);
    const button = () => page.evaluate(() => [document.querySelector('#rgfill').textContent,
                                              document.querySelector('#rgfill').classList.contains('armed')]);
    eq(await button(), [`replace ${N} glosses — press again`, true],
       `g) the first press turns the button into "replace ${N} glosses — press again"`);
    assert(new RegExp(`${N} existing glosses will be replaced`).test(rep) && /nothing has been written yet/.test(rep),
           'and the report says what the second press will do: ' + JSON.stringify(rep.split('\n')[1]));
    assert(bytesEqual(await Deno.readFile(p1), t1) && bytesEqual(await Deno.readFile(p2), t2),
           'g) the first press wrote nothing');
    await sleep(4400);
    eq(await button(), ['fill from the answer', false], 'g) left alone, the arm comes off after four seconds');
    rep = await fill(page);
    eq(await button(), [`replace ${N} glosses — press again`, true], 'pressed again, it asks again');
    // a change to the answer takes the arm off too: what was counted is gone
    await page.click('#rgans');
    await page.keyboard.press('End');
    await page.keyboard.type(' ');
    eq(await button(), ['fill from the answer', false], 'g) typing in the answer box takes the arm off at once');
    assert(bytesEqual(await Deno.readFile(p1), t1) && bytesEqual(await Deno.readFile(p2), t2), 'and still nothing is written');
    rep = await fill(page);
    eq(await button(), [`replace ${N} glosses — press again`, true], 'pressed, it asks again');
    rep = await fill(page);
    assert(new RegExp(`filled 0 · completed 0 · replaced ${N}`).test(rep), `g) the second press replaces the ${N}: ` + JSON.stringify(counts(rep)));
    const dropped = await page.evaluate(() => {
      const d = [...document.querySelectorAll('#rgreport details')].find(x => /^dropped/.test(x.querySelector('summary').textContent));
      return d ? [...d.querySelectorAll('li')].map(li => li.textContent) : [];
    });
    assert(dropped.length >= 1 && dropped.every(t => /ch1:2\.1/.test(t)),
           'f) the answer\'s sentence of the folded paragraph is dropped and listed: ' + JSON.stringify(dropped[0]));
    const a1 = await chunksOf(p1), a2 = await chunksOf(p2);
    const after = [...a1.filter(x => x.label === '1.1' || x.label === '1.2'), ...a2.filter(x => x.label === '1.1')];
    eq(after.map(x => [x.fa, x.tr, x.voc, x.en]), inStretch.map(x => [x.fa, '', '', 'NEW ' + x.fa.toUpperCase()]),
       'g) on disk every chunk of the stretch has the new gloss (tr and voc left out, so emptied)');
    eq(a1.filter(x => x.para === 2).map(fields), c1.filter(x => x.para === 2).map(fields),
       'f) and the folded paragraph is untouched');
    eq(a2.filter(x => x.label !== '1.1').map(fields), c2.filter(x => x.label !== '1.1').map(fields),
       'and so is the rest of chapter 2');
    assert(bytesEqual(await Deno.readFile(dir + '/ch3.tex'), t3), 'and chapter 3, byte for byte');
    assert(foldedOne && !(await Deno.readTextFile(p1)).includes('FOLDED'), 'no FOLDED gloss reached the file');
    const onPage = await page.evaluate(ns => ns.map(n => {
      const g = document.querySelector('.pass.p2 .row[data-c="' + n + '"] .gl .en');
      return g ? g.textContent : null;
    }), [...c1.filter(x => x.label === '1.1' || x.label === '1.2').map(x => x.index),
         ...c2.filter(x => x.label === '1.1').map(x => c1.length + x.index)]);
    eq(onPage, inStretch.map(x => 'NEW ' + x.fa.toUpperCase()),
       'g) the page shows every one of them, chapter 2\'s included, painted from its own file');
    assert(await stayed(page), 'with no reload');
    await page.close();
  }

  /* ---------------- j) the whole loop on a phone ---------------- */
  console.log('\nj) on a phone: a tap on the chunk, the pencil, delete, the region sheet, copy, paste, fill (Japanese)');
  {
    const dir = B0.ja, path = dir + '/ch1.tex';
    await py(RELINK, dir);
    const phone = await browser.newContext({viewport: {width: 390, height: 844}, isMobile: true, hasTouch: true});
    await phone.grantPermissions(['clipboard-read', 'clipboard-write'], {origin: B});
    const saved = context;
    context = phone;
    const page = await reader('/books/japanese/mini-ja/reader/', 'ja-phone');
    context = saved;
    const original = await Deno.readFile(path);
    const n = 11, r = (await chunksOf(path))[n];
    await onScreen(page, '#rgn', 'the header\'s "gloss with an LLM"');
    await page.evaluate(sel => document.querySelector(sel).scrollIntoView({block: 'center'}), row(n));
    await sleep(250);
    await page.tap(row(n));
    await page.waitForFunction(n => !document.querySelector('#chpen').hidden && penFor && +penFor.dataset.c === n, n);
    await page.tap('#chpen');
    await page.waitForFunction(n => chOpen && chN === n, n);
    await page.locator('#chdel').scrollIntoViewIfNeeded();
    await onScreen(page, '#chdel', '"delete gloss"');
    await page.tap('#chdel');
    await waitStat(page, /^gloss deleted/);
    assert(bytesEqual(await Deno.readFile(path), await deletedText(original, n)), 'the gloss is deleted, the macro kept');
    await page.locator('#chrgn').scrollIntoViewIfNeeded();
    await page.tap('#chrgn');
    await page.waitForFunction(() => rgShown);
    await onScreen(page, '#rgbox', 'the region sheet');
    eq(await page.evaluate(() => [document.documentElement.scrollWidth <= innerWidth,
                                  document.querySelector('#rgbox').scrollWidth <= document.querySelector('#rgbox').clientWidth]),
       [true, true], 'nothing is wider than the phone');
    await page.locator('#rgcopy').scrollIntoViewIfNeeded();
    await onScreen(page, '#rgcopy', '"copy the prompt"');
    await setClip(page, 'SENTINEL — not written by the page');
    await page.tap('#rgcopy');
    await page.waitForFunction(() => /clipboard/.test(document.querySelector('#rgsum').textContent));
    const data = dataOf(await clip(page));
    const answer = structuredClone(data);
    let k = 0;
    for (const c of answer.sentences.flatMap(x => x.chunks))
      if (c.todo) { k++; delete c.todo; for (const f of GLOSS) if (r[f]) c[f] = r[f]; }
    eq(k, 1, 'the clipboard holds the prompt, the deleted chunk the one to do');
    await paste(page, fence(answer));
    await page.locator('#rgfill').scrollIntoViewIfNeeded();
    await onScreen(page, '#rgfill', '"fill from the answer"');
    await page.tap('#rgfill');
    await page.waitForFunction(() => /filled/.test(document.querySelector('#rgreport').textContent), null, {timeout: 30000});
    assert(/filled 1 · completed 0 · replaced 0/.test(await text(page, '#rgreport')), 'the report says filled 1');
    assert(bytesEqual(await Deno.readFile(path), original) && (await glOf(page, n)).includes(r.en) && await stayed(page),
           'the .tex is what it was, and the page shows the gloss, with no reload');
    await phone.close();
  }

  /* ---------------- k) a browser that will not take the prompt ---------------- */
  console.log('\nk) the clipboard refused (as Safari refuses a copy made after a round trip): the prompt shown, and copied at the next press (Chinese)');
  {
    const dir = B0.zh, path = dir + '/ch1.tex';
    await py(RELINK, dir);
    // both of Parseh.copy's ways refused until the test lets them through
    const page = await reader('/books/chinese/mini-zh/reader/', 'zh-noclip', () => {
      window.__refuse = true;
      const real = window.__realWrite = navigator.clipboard.writeText.bind(navigator.clipboard);
      navigator.clipboard.writeText = t => window.__refuse ? Promise.reject(new Error('refused')) : real(t);
      const exec = document.execCommand.bind(document);
      document.execCommand = (c, ...a) => (window.__refuse && c === 'copy') ? false : exec(c, ...a);
    });
    const n = 8, before = await Deno.readFile(path);
    await openChunk(page, n);
    await page.click('#chdel');
    await waitStat(page, /^gloss deleted/);
    await page.click('#chrgn');
    await page.waitForFunction(() => rgShown);
    const {prompt, sum} = await copyPrompt(page);
    eq(prompt, 'SENTINEL — not written by the page', 'the clipboard was refused, and holds what it held');
    assert(/not copied — the browser would not put it on the clipboard/.test(sum), 'the sheet says so: ' + JSON.stringify(sum.split('\n').pop()));
    const held = await page.evaluate(() => {
      const t = document.querySelector('#rgout');
      return {shown: !document.querySelector('#rgoutrow').hidden, value: t.value,
              selected: document.activeElement === t && t.selectionStart === 0 && t.selectionEnd === t.value.length};
    });
    assert(held.shown && held.selected && dataOf(held.value).sentences.flatMap(x => x.chunks).filter(c => c.todo).length === 1,
           'the prompt is shown under the button, selected, to copy by hand');
    await page.evaluate(() => { window.__refuse = false; });
    await page.click('#rgcopy');
    await page.waitForFunction(() => /on the clipboard/.test(document.querySelector('#rgsum').textContent));
    eq(await clip(page), held.value, 'pressed again, "copy the prompt" puts that same prompt on the clipboard');
    eq(await page.evaluate(() => document.querySelector('#rgoutrow').hidden), true, 'and the box to copy by hand goes');
    // the chunk put back, through the chunk sheet's own undo
    await page.click('#rgclose');
    await openChunk(page, n);
    await page.click('#chundo');
    await waitStat(page, /^the deleted gloss is written back/);
    assert(bytesEqual(await Deno.readFile(path), before), 'and undo puts the chunk back as it was');
    await page.close();
  }

  /* ---------------- l) a reading proposed from the word line ---------------- */
  console.log('\nl) a drafted chunk: a word line and the reading proposed from it, and nothing else (Chinese)');
  {
    const dir = B0.zh, path = dir + '/ch1.tex';
    await py(RELINK, dir);
    const page = await reader('/books/chinese/mini-zh/reader/', 'zh-seed');
    const n = 12, r = (await chunksOf(path))[n];
    eq([r.macro, r.tr, r.voc, r.en, r.words], ['chw', 'kàn shū,', '', '', '看(kàn) 书(shū) ，'],
       'the chunk holds its word line and the reading proposed from it');
    eq(await page.evaluate(sel => document.querySelector(sel).dataset.seed, row(n)), 'kàn shū,',
       'the build marks its row with the proposal (data-seed)');
    await openChunk(page, n);
    eq(await page.evaluate(() => [document.querySelector('#chdel').hidden, document.querySelector('#chdel').disabled,
                                  document.querySelector('#chtr').value]), [false, true, 'kàn shū,'],
       '"delete gloss" is there but greyed out: a proposal is nobody\'s gloss');
    await page.click('#chrgn');
    await page.waitForFunction(() => rgShown);
    const {prompt, sum} = await copyPrompt(page);
    const data = dataOf(prompt);
    const todo = data.sentences.flatMap(x => x.chunks).filter(c => c.todo);
    eq(todo, [{fa: '看书，', words: r.words, tr: 'kàn shū,', todo: true}],
       'the prompt asks for it, carrying its word line and the proposed reading');
    assert(/1 to gloss/.test(sum) && /may already carry a `tr` the software\s+read off its words/.test(prompt),
           'and tells the LLM the reading is a proposal');
    // the answer keeps the proposal and gives the meaning: once the chunk is
    // written, the proposed reading counts as its own
    const answer = structuredClone(data);
    for (const c of answer.sentences.flatMap(x => x.chunks)) if (c.todo) { delete c.todo; c.en = 'legge,'; }
    await paste(page, fence(answer));
    const rep = await fill(page);
    assert(/filled 1 · completed 0 · replaced 0/.test(rep), 'the answer lands: ' + JSON.stringify(counts(rep)));
    const now = (await chunksOf(path))[n];
    eq([now.macro, now.tr, now.voc, now.en, now.words], ['chw', 'kàn shū,', '', 'legge,', r.words],
       'the .tex keeps the macro, the word line and the reading, and has the meaning');
    eq(await page.evaluate(sel => document.querySelector(sel).hasAttribute('data-seed'), row(n)), false,
       'the repainted row no longer calls its reading a proposal');
    await page.click('#rgclose');
    await openChunk(page, n);
    eq(await page.evaluate(() => document.querySelector('#chdel').disabled), false, 'and "delete gloss" is offered on it');
    assert(await stayed(page), 'all with no reload');
    await page.close();
  }

  /* ---------------- h) ---------------- */
  console.log('\nh) what the pages and the hub said');
  console.log('  (refused as expected: ' + [...new Set(allowed.map(a => a.replace(/^\S+ /, '')))].join(', ') + ')');
  assert(!errors.length, 'no page threw, logged an error or had a request refused: ' + errors.join('; '));
  const tb = log.join('');
  assert(!/Traceback/.test(tb), 'no traceback in the hub\'s log');
  const ownAfter = JSON.parse(await py(OWN, TMP));
  eq(ownAfter.leaks, [], 'nothing of this run\'s tree was remembered in the owner\'s config/digests.json or wheres.json');
  eq(ownAfter.digests, ownBefore.digests, 'the owner\'s config/, books/, youtube/videos/ and the fixtures are untouched');
  console.log(`\ngloss_llm_book: ${passed} checks passed`);
} finally {
  if (browser) await browser.close();
  if (hub) { try { hub.kill('SIGTERM'); await hub.status; } catch (_) {} }
  if (!Deno.env.get('PARSEH_KEEP')) await Deno.remove(TMP, {recursive: true}).catch(() => {});
  else console.log('kept ' + TMP);
}

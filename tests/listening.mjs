// SPDX-License-Identifier: GPL-3.0-or-later
import { chromium } from 'npm:playwright-core@1.52.0';
// Run: CHROME_BIN=/path/to/chrome PARSEH_PYTHON=python3 deno run --allow-all tests/listening.mjs
//
// LISTENING TO A BOOK RATHER THAN READING IT.  Everything else in the reader
// plays a subparagraph: the playhead is the reading place, it stops at that
// subparagraph's end, and `continuous` steps it on to the next.  `listen` puts
// the recording on instead and leaves the text alone -- no highlight, no
// scrolling, no reading place moved -- from wherever in the file you like.
//
// What has to hold, and is covered nowhere else (tests/folding.mjs has no
// recording at all, and tests/narration.mjs no folded run):
//
//   a) A FOLD IS STILL A FOLD.  A run somebody folded away is text they have
//      said they do not want; played straight through it would be read out
//      all the same.  Listening holds at the first folded stretch ahead of the
//      playhead -- not one subparagraph before it, not one after.
//   b) AND IT PREPARES TO GO ON AFTER IT.  The playhead is left at the END of
//      the folded stretch, so the next press carries on past the text that was
//      folded, which is what folding it meant.
//   c) FROM ANY MOMENT.  The seek bar starts the recording anywhere, and what
//      it is dragged onto is honoured -- a stretch somebody drops into on
//      purpose is played, or it could not be reached at all.
//   d) THE TEXT IS NOT FOLLOWED WHILE IT PLAYS, unless "follow" says
//      otherwise.  Off (the default), nothing about the text moves, and
//      reading is exactly as it was once listening is turned off again.  On,
//      the mark tracks the playhead the way a video's captions track the
//      video: moving with it, never pausing it at an ordinary subparagraph's
//      end (only a fold still does that), never touching the actual reading
//      place, and skipping a folded subparagraph exactly as the recording
//      does -- "scroll to it" says whether the page follows the mark there
//      or the reader follows it by hand.  Both are grey until listening is
//      on, and reset every time it is turned on: a habit of this moment of
//      listening, not a property of the book.
//
// The recording is real (an ffmpeg sine) and served over real HTTP with Range,
// as tests/narration.mjs is: a seek held by a route fulfilment never lands.
const root = await Deno.realPath(new URL('..', import.meta.url));
Deno.chdir(root);
const PY = Deno.env.get('PARSEH_PYTHON') || 'python3';
const TMP = await Deno.makeTempDir({prefix: 'parseh-listening-'});
const td = new TextDecoder();
let passed = 0;
const assert = (v, m) => { if (!v) throw Error('FAIL: ' + m); passed++; console.log('  ok', m); };
const eq = (got, want, m) => assert(JSON.stringify(got) === JSON.stringify(want),
                                    m + ' -- got ' + JSON.stringify(got));
async function py(code, ...args) {
  const o = await new Deno.Command(PY, {args: ['-c', code, ...args], stdout: 'piped', stderr: 'piped'}).output();
  if (!o.success) throw Error(td.decode(o.stderr) || td.decode(o.stdout));
  return td.decode(o.stdout);
}
async function ff(...args) {
  const o = await new Deno.Command('ffmpeg', {args: ['-y', '-loglevel', 'error', ...args],
                                              stdout: 'piped', stderr: 'piped'}).output();
  if (!o.success) throw Error('ffmpeg: ' + td.decode(o.stderr));
}

/* ---------------- a book with a narration and a folded run ---------------- */
// mini-en is two paragraphs of two subparagraphs each; the SECOND paragraph is
// folded away, so subparagraphs 2 and 3 are the folded stretch.
const BOOK = `${TMP}/books/english/mini-en`;
await py(`
import os, shutil, sys
sys.path.insert(0, "lib")
import reading
d = sys.argv[1]
os.makedirs(os.path.dirname(d), exist_ok=True)
shutil.copytree('tests/fixtures/books/english/mini-en', d, ignore=shutil.ignore_patterns('reader'))
os.makedirs(os.path.join(d, 'audio'), exist_ok=True)
reading.collapse(d, "1:2", "1:2", True)
`, BOOK);
// forty seconds: room for four subparagraphs three seconds apart and a tail
await ff('-f', 'lavfi', '-i', 'sine=frequency=440:duration=40', '-ac', '1', '-ar', '8000',
         `${BOOK}/audio/whole.wav`);
const info = JSON.parse(await py(`
import io, json, os, sys
sys.path.insert(0, 'lib')
import books, texparse as T, timestamp as ts
d = sys.argv[1]
b = books.Book(d)
subs = [x for ch in T.parse_book(b.main, b.lang) for pp in ch.paragraphs for x in pp.subs]
meta = json.load(io.open(os.path.join(d, 'book.json'), encoding='utf-8'))
meta['audio'] = 'audio/whole.wav'
json.dump(meta, io.open(os.path.join(d, 'book.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
ts._bind(b)
recs = {}
for k, x in enumerate(subs):
    recs[ts.subkey(x)] = {'t0': round(1.0 + k * 3.0, 3), 't1': round(3.5 + k * 3.0, 3),
                          'conf': 1.0, 'src': 'anchor', 'label': x.num}
json.dump({'audio': 'audio/whole.wav', 'book': b.slug, 'generated_by': 'test', 'subs': recs},
          io.open(os.path.join(d, 'timings.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps({'labels': [x.num for x in subs],
                  'times': [[recs[ts.subkey(x)]['t0'], recs[ts.subkey(x)]['t1']] for x in subs]}))
`, BOOK));
await py(`
import subprocess, sys
for cmd in (['lib/timestamp.py', '--book', sys.argv[1], '--from-sidecar'],
            ['lib/tex2html.py', '--book', sys.argv[1]]):
    r = subprocess.run([sys.executable] + cmd, capture_output=True, text=True)
    if r.returncode: raise SystemExit(r.stderr or r.stdout)
`, BOOK);
const FOLD = [info.times[2][0], info.times[3][1]];      // 7 .. 12.5

/* A REAL HTTP SERVER, Range and all (tests/narration.mjs says why). */
const MIME = {html: 'text/html', js: 'text/javascript', css: 'text/css',
              json: 'application/json', wav: 'audio/wav'};
const server = Deno.serve({port: 0, onListen: () => {}}, async req => {
  const path = decodeURIComponent(new URL(req.url).pathname);
  if (path.endsWith('/__lookup')) return Response.json({ok: true, have: false});
  if (path.endsWith('/api/marks')) return new Response('no', {status: 404});
  let bytes;
  try { bytes = await Deno.readFile(path); } catch (_) { return new Response('no', {status: 404}); }
  const type = MIME[path.split('.').pop()] || 'application/octet-stream';
  const m = (req.headers.get('range') || '').match(/bytes=(\d+)-(\d*)/);
  if (m) {
    const from = +m[1], to = m[2] ? Math.min(+m[2], bytes.length - 1) : bytes.length - 1;
    return new Response(bytes.slice(from, to + 1), {status: 206, headers: {
      'Content-Type': type, 'Accept-Ranges': 'bytes',
      'Content-Range': `bytes ${from}-${to}/${bytes.length}`}});
  }
  return new Response(bytes, {headers: {'Content-Type': type, 'Accept-Ranges': 'bytes'}});
});
const READER = `http://127.0.0.1:${server.addr.port}${BOOK}/reader/index.html`;
const browser = await chromium.launch({executablePath: Deno.env.get('CHROME_BIN'), headless: true,
                                       args: ['--autoplay-policy=no-user-gesture-required']});
const errors = [];
try {
  const page = await browser.newPage();
  page.on('pageerror', e => errors.push(e.message));
  await page.goto(READER);
  await page.waitForSelector('#listen');
  await page.waitForFunction(() => A.readyState >= 1, null, {timeout: 10000});

  console.log('follow and scroll to it are grey until listening is on');
  const gated = await page.evaluate(() => ({
    follow: document.getElementById('listenfollow').disabled,
    scroll: document.getElementById('listenscroll').disabled,
  }));
  assert(gated.follow && gated.scroll, 'both start disabled: ' + JSON.stringify(gated));

  console.log('the folded run, in the recording\'s own clock');
  const seen = await page.evaluate(() => ({folded: foldedSubs, windows: foldWindows(),
                                           gate: foldGate(0), subs: SUBS.map(s => [s[0], s[1]])}));
  eq(seen.folded, [[2, 3]], 'the folded paragraph is subparagraphs 2 and 3');
  eq(seen.windows, [FOLD], 'which is one stretch of the recording: its first start to its last end');
  eq(seen.gate, FOLD, 'and it is the gate ahead of the beginning');

  console.log('listening holds at the fold, and prepares to go on after it');
  await page.evaluate(() => { window.TRAIL = []; A.addEventListener('timeupdate',
    () => TRAIL.push(+A.currentTime.toFixed(2))); });
  const place = await page.evaluate(() => ({cur, scroll: Math.round(scrollY),
                                            hl: document.querySelectorAll('.sub.on-air').length}));
  await page.click('#listen');
  assert(await page.locator('#listen').evaluate(b => b.classList.contains('on')),
         'the switch says it is on');
  assert(await page.locator('#seekwrap').isVisible(), 'and the seek bar comes with it');
  await page.click('#play');
  await page.waitForFunction(() => A.paused && A.currentTime > 1, null, {timeout: 20000});
  const held = await page.evaluate(() => ({at: +A.currentTime.toFixed(2), trail: TRAIL,
    cur, scroll: Math.round(scrollY), hl: document.querySelectorAll('.sub.on-air').length}));
  const got = held.trail.filter(t => t < 20);
  assert(Math.max(...got.filter(t => t <= FOLD[0])) > FOLD[0] - 0.6,
         'it played up to the fold: ' + Math.max(...got.filter(t => t <= FOLD[0])));
  assert(!got.some(t => t > FOLD[0] + 0.3 && t < FOLD[1] - 0.3),
         'and not one second of the folded text was read out: ' + JSON.stringify(got));
  assert(Math.abs(held.at - FOLD[1]) < 0.3,
         'the playhead waits at the end of the folded run, ready to go on: ' + held.at);
  eq([held.cur, held.scroll, held.hl], [place.cur, place.scroll, place.hl],
     'and the text was not followed: no reading place moved, nothing highlighted, no scrolling');

  console.log('the next press carries on past the folded text');
  await page.click('#play');
  await page.waitForFunction(t => !A.paused && A.currentTime > t, FOLD[1] + 0.4, {timeout: 10000});
  assert(await page.evaluate(() => !A.paused && A.currentTime > 12.5),
         'it plays on from where the folded run ends');
  await page.evaluate(() => A.pause());

  console.log('follow lets the mark track the recording, the way a video\'s captions do');
  assert(!(await page.evaluate(() => document.getElementById('listenfollow').disabled)),
         'listening is on, so it is no longer grey');
  await page.evaluate(() => { A.currentTime = 0; });
  await page.click('#listenfollow');
  await page.click('#play');
  // 0 -> 1 is an ORDINARY boundary, not the fold: following must not pause there
  await page.waitForFunction(() => document.querySelector('.sub[data-s="1"]')?.classList.contains('on-air'),
                             null, {timeout: 15000});
  const followed = await page.evaluate(() => ({
    playing: !A.paused, cur, hl: [...document.querySelectorAll('.sub.on-air')].map(e => e.dataset.s),
  }));
  assert(followed.playing, 'crossing an ordinary boundary did not pause it, unlike plain play');
  eq(followed.hl, ['1'], 'the mark is on the subparagraph now playing, and only it');
  assert(followed.cur === -1, 'and the reading place itself was never touched by following: ' + followed.cur);
  await page.evaluate(() => A.pause());

  console.log('follow off, with no reading place ever set, clears the mark entirely');
  await page.click('#listenfollow');
  eq(await page.evaluate(() => document.querySelectorAll('.sub.on-air').length), 0,
     'nothing: there is no reading place to show');

  console.log('a fold is still skipped by the mark, not only by the recording');
  // the same book, the fold moved to the FIRST paragraph (subparagraphs 0-1)
  // by hand, the way tests/folding.mjs does -- leaving 2-3 real and after it
  await page.evaluate(() => { folded = [['1:1', '1:1']]; foldRanges(); applyFold(); });
  await page.evaluate(() => { A.currentTime = 0; });
  await page.click('#listenfollow');
  await page.click('#play');
  await page.waitForFunction(() => A.paused && A.currentTime > 3, null, {timeout: 15000});
  eq(await page.evaluate(() => [...document.querySelectorAll('.sub.on-air')].map(e => e.dataset.s)), [],
     'held at the fold: nothing folded is on the page for the mark to name, so it names nothing');
  await page.click('#play');
  await page.waitForFunction(() => document.querySelector('.sub[data-s="2"]')?.classList.contains('on-air'),
                             null, {timeout: 10000});
  assert(await page.evaluate(() => !A.paused),
         'carrying on past the fold follows into real text again, without pausing');
  await page.evaluate(() => A.pause());
  // put the fold back where the rest of this file expects it
  await page.evaluate(() => { folded = [['1:2', '1:2']]; foldRanges(); applyFold(); });
  await page.click('#listenfollow');

  console.log('scroll to it: off by default, the mark moves and the page does not');
  const shortCtx = await browser.newContext({viewport: {width: 700, height: 220}});
  const shortPage = await shortCtx.newPage();
  const shortErrors = []; shortPage.on('pageerror', e => shortErrors.push(e.message));
  await shortPage.goto(page.url());
  await shortPage.waitForFunction(() => A.readyState >= 1, null, {timeout: 10000});
  await shortPage.click('#listen');
  await shortPage.click('#listenfollow');
  await shortPage.evaluate(() => window.scrollTo(0, 0));
  const before = await shortPage.evaluate(() => scrollY);
  await shortPage.click('#play');
  await shortPage.waitForFunction(() => document.querySelector('.sub[data-s="1"]')?.classList.contains('on-air'),
                                  null, {timeout: 15000});
  await shortPage.waitForTimeout(300);
  assert(await shortPage.evaluate(() => scrollY) === before,
         'scroll to it off: the mark moved but the narrow page did not follow it');
  await shortPage.evaluate(() => A.pause());

  console.log('scroll to it: on, the page follows the mark too');
  await shortPage.evaluate(() => { A.currentTime = 0; window.scrollTo(0, 0); });
  await shortPage.click('#listenscroll');
  const before2 = await shortPage.evaluate(() => scrollY);
  await shortPage.click('#play');
  await shortPage.waitForFunction(() => document.querySelector('.sub[data-s="1"]')?.classList.contains('on-air'),
                                  null, {timeout: 15000});
  await shortPage.waitForTimeout(500);
  assert(await shortPage.evaluate(() => scrollY) !== before2, 'scroll to it on: the page follows the mark');
  assert(shortErrors.length === 0, 'no page errors, narrow page: ' + JSON.stringify(shortErrors));
  await shortPage.close();
  await shortCtx.close();

  console.log('and it starts from any moment of the recording');
  const seeked = await page.evaluate(async () => {
    const s = document.querySelector('#seek');
    s.value = String(Math.round((20 / A.duration) * 1000));
    s.dispatchEvent(new Event('change', {bubbles: true}));
    await new Promise(r => setTimeout(r, 500));
    return +A.currentTime.toFixed(1);
  });
  assert(Math.abs(seeked - 20) < 0.5, 'the seek bar puts it at 20 s: ' + seeked);
  // a stretch somebody drops into on purpose is played: gating it would put it
  // out of reach altogether, and the fold is about reading, not about the file
  const inside = await page.evaluate(async lo => {
    const s = document.querySelector('#seek');
    s.value = String(Math.round(((lo + 1) / A.duration) * 1000));
    s.dispatchEvent(new Event('change', {bubbles: true}));
    await new Promise(r => setTimeout(r, 500));
    document.querySelector('#play').click();
    await new Promise(r => setTimeout(r, 700));
    return {at: +A.currentTime.toFixed(2), playing: !A.paused};
  }, FOLD[0]);
  assert(inside.playing && inside.at > FOLD[0], 'dropped inside a folded stretch, it plays: '
         + JSON.stringify(inside));
  await page.evaluate(() => A.pause());

  console.log('turned off, the book reads as it always did');
  await page.click('#listen');
  assert(!await page.locator('#listen').evaluate(b => b.classList.contains('on'))
         && !await page.locator('#seekwrap').isVisible(), 'the switch and its seek bar go');
  const read = await page.evaluate(async () => {
    document.querySelectorAll('.sub')[0].click();
    await new Promise(r => setTimeout(r, 400));
    return {cur, stopAt, hl: document.querySelectorAll('.sub.on-air').length};
  });
  eq([read.cur, read.hl], [0, 1], 'a click on a subparagraph is the reading place again');
  assert(Math.abs(read.stopAt - info.times[0][1]) < 0.01,
         'and it stops at that subparagraph\'s end, as it always has: ' + read.stopAt);

  console.log('follow off returns the mark to the actual reading place, not to nothing');
  await page.click('#listen');
  await page.click('#listenfollow');
  await page.evaluate(() => { A.currentTime = 4.2; });   // into subparagraph 1's window
  await page.click('#play');
  await page.waitForFunction(() => document.querySelector('.sub[data-s="1"]')?.classList.contains('on-air'),
                             null, {timeout: 15000});
  await page.evaluate(() => A.pause());
  await page.click('#listenfollow');
  eq(await page.evaluate(() => [...document.querySelectorAll('.sub.on-air')].map(e => e.dataset.s)), ['0'],
     'the mark returns to subparagraph 0, the reading place the earlier click left, not to where listening got to');
  await page.click('#listen');

  console.log(`\nlistening: ${passed} checks passed`);
  if (errors.length) throw Error(errors.join('\n'));
} finally {
  await browser.close();
  await server.shutdown();
  await Deno.remove(TMP, {recursive: true});
}

// SPDX-License-Identifier: GPL-3.0-or-later
import { chromium } from 'npm:playwright-core@1.52.0';
// Run: CHROME_BIN=/path/to/chrome deno run --allow-all tests/narration.mjs
//
// A book read a part at a time: two recordings, each covering a stretch of the
// text, each its own file with its own clock.
//
//  a) THE PLAYER SWAPS FILE.  Clicking a subparagraph in the second region
//     points the one <audio> at the second recording and seeks inside IT --
//     the times of each region are seconds into its own file, so playing the
//     wrong one would be silent nonsense with nothing to see.
//  b) THE PANEL.  One row per recording, saying what it covers and what it has
//     timed; a file is added with the stretch it is of; a row aligns, re-says
//     what it covers, or is taken off the book.
//  c) A BOOK WITH ONE RECORDING is untouched: one row, "the whole book", and
//     the element keeps the src the build baked in.
//  e) THE DOWNLOAD SHEET says how big each of the three shapes is, from the
//     sizes the status gives for what each bundle carries -- "all of it"
//     being every recording, not the first one.
//
// The two recordings are real (ffmpeg sine waves), so the seek is a real seek.
const root = await Deno.realPath(new URL('..', import.meta.url));
Deno.chdir(root);
const PY = Deno.env.get('PARSEH_PYTHON') || 'python3';
const TMP = await Deno.makeTempDir({prefix: 'parseh-narration-'});
const td = new TextDecoder();
let passed = 0;
const assert = (v, m) => { if (!v) throw Error('FAIL: ' + m); passed++; console.log('  ok', m); };
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

/* ---------------- a book with two recordings ---------------- */
const BOOK = `${TMP}/books/english/mini-en`;
await py(`
import os, shutil, sys
d = sys.argv[1]
os.makedirs(os.path.dirname(d), exist_ok=True)
shutil.copytree('tests/fixtures/books/english/mini-en', d, ignore=shutil.ignore_patterns('reader'))
os.makedirs(os.path.join(d, 'audio'), exist_ok=True)
`, BOOK);
// six seconds each: long enough to seek inside, small enough to serve
await ff('-f', 'lavfi', '-i', 'sine=frequency=440:duration=6', '-ac', '1', '-ar', '8000', `${BOOK}/audio/part1.wav`);
await ff('-f', 'lavfi', '-i', 'sine=frequency=880:duration=6', '-ac', '1', '-ar', '8000', `${BOOK}/audio/part2.wav`);

const info = JSON.parse(await py(`
import io, json, os, sys
sys.path.insert(0, 'lib')
import books, texparse as T, timestamp as ts
d = sys.argv[1]
b = books.Book(d)
subs = [x for ch in T.parse_book(b.main, b.lang) for pp in ch.paragraphs for x in pp.subs]
labels = [x.num for x in subs]
half = len(subs) // 2
meta = json.load(io.open(os.path.join(d, 'book.json'), encoding='utf-8'))
meta['audio'] = 'audio/part1.wav'
meta['narrations'] = [
    {'id': 'n1', 'audio': 'audio/part1.wav', 'transcript': '', 'from': labels[0], 'to': labels[half - 1]},
    {'id': 'n2', 'audio': 'audio/part2.wav', 'transcript': '', 'from': labels[half], 'to': labels[-1]}]
json.dump(meta, io.open(os.path.join(d, 'book.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
ts._bind(b)
recs = {}
for k, x in enumerate(subs):
    n = 'n1' if k < half else 'n2'
    base = k if n == 'n1' else k - half
    recs[ts.subkey(x)] = {'t0': round(1.0 + base * 2.0, 3), 't1': round(2.5 + base * 2.0, 3),
                          'conf': 1.0, 'src': 'anchor', 'label': x.num, 'n': n}
json.dump({'audio': 'audio/part1.wav', 'book': b.slug, 'generated_by': 'test',
           'narrations': meta['narrations'], 'subs': recs},
          io.open(os.path.join(d, 'timings.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps({'labels': labels, 'half': half}))
`, BOOK));
await py(`
import subprocess, sys
for cmd in (['lib/timestamp.py', '--book', sys.argv[1], '--from-sidecar'],
            ['lib/tex2html.py', '--book', sys.argv[1]]):
    r = subprocess.run([sys.executable] + cmd, capture_output=True, text=True)
    if r.returncode: raise SystemExit(r.stderr or r.stdout)
`, BOOK);

/* A REAL HTTP SERVER, not an intercepted route.  A recording is fetched with
   a Range header, and media answered by a route fulfilment never finishes
   loading -- readyState stays 0 with no error at all -- so the swap could
   never be seen.  This serves the temp tree the way serve.py serves the real
   one, Range and all, and answers the narration doors beside it. */
const MIME = {html: 'text/html', js: 'text/javascript', css: 'text/css', json: 'application/json', wav: 'audio/wav'};
const server = Deno.serve({port: 0, onListen: () => {}}, async req => {
  const url = new URL(req.url);
  const path = decodeURIComponent(url.pathname);
  if (path.endsWith('/__narration/status'))
    return Response.json(STATUS);
  for (const door of ['align', 'spread', 'region', 'remove']) {
    if (path.endsWith('/__narration/' + door)) {
      let body = {};
      try { body = await req.json(); } catch (_) {}
      posted.push([door, body]);
      return Response.json({ok: true, subs: 4, timed: 4, log: '', narrations: []});
    }
  }
  if (path.endsWith('/api/marks') || path.endsWith('/timings.json'))
    return new Response('no', {status: 404});
  if (path.endsWith('/__lookup')) return Response.json({ok: true, have: false});
  let bytes;
  try { bytes = await Deno.readFile(path); }
  catch (_) { return new Response('no such file', {status: 404}); }
  const type = MIME[path.split('.').pop()] || 'application/octet-stream';
  const range = req.headers.get('range');
  const m = range && /bytes=(\d+)-(\d*)/.exec(range);
  if (m) {
    const from = +m[1], to = m[2] ? Math.min(+m[2], bytes.length - 1) : bytes.length - 1;
    return new Response(bytes.slice(from, to + 1), {
      status: 206,
      headers: {'Content-Type': type, 'Accept-Ranges': 'bytes',
                'Content-Range': `bytes ${from}-${to}/${bytes.length}`},
    });
  }
  return new Response(bytes, {headers: {'Content-Type': type, 'Accept-Ranges': 'bytes'}});
});
const PORT = server.addr.port;
const READER = `http://127.0.0.1:${PORT}${BOOK}/reader/index.html`;
const posted = [];
const VERBOSE = !!Deno.env.get('NARRATION_VERBOSE');
let STATUS = null;
const browser = await chromium.launch({executablePath: Deno.env.get('CHROME_BIN'), headless: true});
const errors = [];
try {
  const page = await browser.newPage();
  page.on('pageerror', e => { errors.push(e.message); console.log('PAGE ERROR', e.message); });
  page.on('requestfailed', r => console.log('REQ FAIL', r.url().slice(-70),
                                            (r.failure() || {}).errorText));
  page.on('console', m => { if (m.type() === 'error') console.log('CONSOLE', m.text().slice(0, 160)); });
  await page.goto(READER, {waitUntil: 'domcontentloaded'});
  await page.waitForSelector('.sub');

  console.log('a) what the page was built with');
  const built = await page.evaluate(() => ({narr: NARR, subs: SUBS}));
  assert(built.narr.length === 2 && built.narr[0].src.endsWith('part1.wav')
         && built.narr[1].src.endsWith('part2.wav'),
         'both recordings reached the page, each with the stretch it covers');
  assert(built.subs.every(s => s[3] === 'n1' || s[3] === 'n2'),
         'every subparagraph says which recording its times are in');
  // and each recording where it is, as the first and last subparagraph it
  // covers: what the player goes by when a subparagraph carries no id
  assert(JSON.stringify(built.narr.map(n => [n.lo, n.hi])) ===
         JSON.stringify([[0, info.half - 1], [info.half, info.labels.length - 1]]),
         'each recording carries the stretch it covers, worked out by the build: ' +
         JSON.stringify(built.narr.map(n => [n.lo, n.hi])));
  const src0 = await page.locator('#audio').getAttribute('src');
  assert(/part1\.wav$/.test(src0), `the element starts on the first recording (${src0})`);

  console.log('b) the player swaps file at the seam');
  const half = info.half;
  // a subparagraph in the FIRST region: the src must not move
  await page.locator('.sub').nth(0).click();
  await page.waitForFunction(() => document.querySelector('#audio').readyState >= 1);
  assert(/part1\.wav$/.test(await page.evaluate(() => document.querySelector('#audio').src)),
         'clicking inside the first region keeps the first recording loaded');
  // ...and one in the SECOND: the element is re-pointed and seeks inside it
  await page.locator('.sub').nth(half).click();
  await page.waitForFunction(() => /part2\.wav$/.test(document.querySelector('#audio').src));
  assert(true, 'clicking into the second region loads the second recording');
  await page.waitForFunction(() => {
    const a = document.querySelector('#audio');
    return a.readyState >= 1 && a.currentTime > 0.5 && a.currentTime < 4;
  }, null, {timeout: 8000});
  const at = await page.evaluate(() => document.querySelector('#audio').currentTime);
  assert(at > 0.5 && at < 4,
         `and seeks inside THAT file, not at the book-wide time (${at.toFixed(2)}s)`);
  assert(!(await page.evaluate(() => document.querySelector('#warn').style.display === 'inline')),
         'a six-second part is not called unseekable');

  console.log('c) the narration panel');
  STATUS = {
    ok: true, slug: 'mini-en', title_latin: 'mini-en',
    audio: {declared: 'audio/part1.wav', path: 'audio/part1.wav', exists: true, bytes: 96044},
    transcript: {declared: null, path: null, exists: false, bytes: 0},
    narrations: [
      // subs/manual/span are what _narration_status sends per recording: the
      // size of the stretch, so a row says "2 of 2 timed" rather than a count
      // with nothing to measure it against, how many were stamped by ear, and
      // how long the transcript runs
      {id: 'n1', audio: 'audio/part1.wav', transcript: 'audio/transcript-n1.srt',
       from: info.labels[0], to: info.labels[half - 1], exists: true, bytes: 96044,
       subs: half, timed: half, manual: 0, has_transcript: true, segments: 3, span: 6,
       lo: 0, hi: half - 1},
      {id: 'n2', audio: 'audio/part2.wav', transcript: 'audio/tr2.json',
       from: info.labels[half], to: info.labels[info.labels.length - 1],
       exists: true, bytes: 96044, subs: info.labels.length - half, timed: 2,
       manual: 0, has_transcript: true, segments: 2, span: 6,
       lo: half, hi: info.labels.length - 1},
      // a third, recorded but with no transcript yet: there is nothing to
      // align it against, and the row has to say so rather than offer it
      {id: 'n3', audio: 'audio/part3.wav', transcript: '', from: '', to: '',
       exists: true, bytes: 1024, subs: info.labels.length, timed: 0, manual: 0,
       has_transcript: false, segments: 0, lo: 0, hi: info.labels.length - 1},
    ],
    labels: info.labels.map(l => ({label: l, chapter: '1', key: '1:' + l})),
    timings: {subs: 4, manual: 0, audio: 'audio/part1.wav'},
    candidates: [], built: true, subs: 4, timed: 4,
    audio_dir: 'books/english/mini-en/audio/',
    tools: {rapidfuzz: true, ffmpeg: true, python: 'python3'},
  };
  await page.click('#narr');
  await page.waitForSelector('#nlist:not([hidden])');
  const rows = await page.locator('#nlist .nitem').count();
  assert(rows === 3, `one row per recording (${rows})`);
  // a recording with no transcript has nothing to be aligned against
  assert(await page.locator('#nlist .nitem').nth(2)
           .locator('button', {hasText: 'align'}).isDisabled(),
         'the row with no transcript cannot be aligned, and says so by going grey');
  const said = await page.locator('#nlist .nitem').first().textContent();
  assert(said.includes('part1.wav') && said.includes('covers') && said.includes('timed'),
         `a row says its file, what it covers and what it has timed: “${said.trim()}”`);
  // the two whole-sheet selects belong to ADD A RECORDING now, and to nothing
  // else: a row says what it covers in its own drawer, so these can never be
  // read by an action nobody meant
  await page.click('#naddbtn');
  await page.waitForSelector('#nadd:not([hidden])');
  // WHAT IT COVERS IS PICKED FROM THE BOOK AS AN OUTLINE (outlinePicker):
  // nothing picked is the whole book, and a paragraph opens to show its
  // subparagraphs
  assert(await page.textContent('#naddpick .olsay') === 'the whole book',
         'add a recording starts on the whole book, and says so');
  for (const tw of await page.locator('#naddpick li.ol-p > .olr > .oltw').all()) await tw.click();
  const subRows = await page.locator('#naddpick li.ol-s').count();
  assert(subRows === info.labels.length,
         `and offers every subparagraph, inside its paragraph (${subRows})`);
  // the recordings already here are marked on the rows they cover -- n3,
  // the whole book's, on none of them, since it is not a stretch
  const tagged = await page.evaluate(() => [...document.querySelectorAll('#naddpick li.ol-p')]
    .map(li => [...li.querySelectorAll(':scope > .olr .oltag')].map(t => t.textContent).join()));
  assert(JSON.stringify(tagged) === JSON.stringify(['n1', 'n2']),
         'each recording already here is marked on the paragraphs it covers: ' + JSON.stringify(tagged));
  await page.click('#naddbtn');
  // a row's drawer is built when it is opened, so it is opened to be asked --
  // and left as it was found, since the covers flow below opens it again
  const r1 = page.locator('#nlist .nitem').nth(1);
  await r1.locator('.ntog').click();
  await r1.locator('.ndraw:not([hidden])').waitFor();
  const covsay = await r1.locator('[data-x="covsay"]').textContent();
  assert(covsay === 'chapter 1, ¶ 2 · 2 subparagraphs',
         `a row's own drawer says what it covers, in words (${covsay})`);
  await r1.locator('[data-x="covchg"]').click();
  const opened = await r1.locator('.olsay').textContent();
  assert(opened === covsay, `and its outline opens on that stretch (${opened})`);
  await r1.locator('[data-x="covchg"]').click();
  await r1.locator('.ntog').click();

  console.log('d) the doors a row opens');
  // a recording that has already timed something is asked before it is timed
  // again, and the question does the work itself: the sheet closing is the
  // answer, so there is one dialog for one decision
  await page.locator('#nlist .nitem').nth(1).locator('button', {hasText: 'align'}).click();
  await page.waitForSelector('#naskbox:not([hidden])');
  await page.click('#naskok');
  // NOT waitForSelector: its default is "visible", and a selector that only
  // ever matches a HIDDEN element can never satisfy that -- it waits out the
  // full timeout while resolving the node it was asked for
  await page.waitForFunction(() => document.getElementById('naskbox').hidden);
  assert(posted.some(([d, b]) => d === 'align' && b.narration === 'n2'),
         'align on the second row asks the server to align that recording only');
  // a recording with no transcript can still be given a first guess
  await page.locator('#nlist .nitem').nth(2).locator('button', {hasText: 'estimate times'}).click();
  await page.waitForFunction(() => true);
  assert(posted.some(([d, b]) => d === 'spread' && b.narration === 'n3'),
         'estimate times shares that recording out over the text it covers');

  // WHAT A RECORDING COVERS IS EDITED IN ITS OWN ROW.  It used to reach up
  // into the whole sheet's two selects, hundreds of pixels from the row that
  // was asking; the row's toggle now opens a drawer holding its own ends.
  const row2 = page.locator('#nlist .nitem').nth(1);
  await row2.locator('.ntog').click();
  await row2.locator('.ndraw:not([hidden])').waitFor();
  await row2.locator('[data-x="covchg"]').click();
  // the second paragraph opened, its first subparagraph picked, and the pick
  // stretched with Shift to the last one of the book
  const p2 = row2.locator('.oltree li.ol-p').nth(1);
  await p2.locator(':scope > .olr > .oltw').click();
  await p2.locator('li.ol-s').first().locator(':scope > .olr').click();
  await p2.locator('li.ol-s').last().locator(':scope > .olr').click({modifiers: ['Shift']});
  await row2.locator('[data-x="savecovers"]').click();
  await page.waitForFunction(() => true);
  const last = info.labels[info.labels.length - 1];
  assert(posted.some(([d, b]) => d === 'region' && b.id === 'n2'
                                 && b.from === '1:' + info.labels[half] && b.to === '1:' + last),
         'saying what it covers sends that recording and its two ends, each named with its ' +
         'chapter: ' + JSON.stringify(posted.filter(([d]) => d === 'region')));
  // taking a recording off the book is destructive, so it is asked for by
  // name first -- the old bare click posted straight through
  await page.locator('#nlist .nitem').nth(1).locator('button', {hasText: 'remove'}).click();
  await page.waitForSelector('#naskbox:not([hidden])');
  await page.click('#naskok');
  // NOT waitForSelector: its default is "visible", and a selector that only
  // ever matches a HIDDEN element can never satisfy that -- it waits out the
  // full timeout while resolving the node it was asked for
  await page.waitForFunction(() => document.getElementById('naskbox').hidden);
  assert(posted.some(([d, b]) => d === 'remove' && b.id === 'n2'),
         'remove takes that recording off the book');

  console.log('e) the download sheet says how big each shape is');
  // `bundle` is what serve.py sums from what lib/bundle.py will pack; nine
  // recordings under audio/ are nine files in "all of it", where the sheet
  // used to give the size of the first alone.  The sheet asks once a page,
  // so a fresh page is asked.
  STATUS.bundle = {text: {bytes: 120000, files: 9, media: 0, media_bytes: 0},
                   linked: {bytes: 212000, files: 12, media: 0, media_bytes: 0},
                   full: {bytes: 76500000, files: 25, media: 9, media_bytes: 59300000}};
  await page.reload({waitUntil: 'domcontentloaded'});
  await page.waitForSelector('.sub');
  await page.click('header .dl');
  await page.waitForFunction(() => /about/.test(document.querySelector('.dlsz[data-shape="full"]').textContent));
  const sizes = await page.evaluate(() => Object.fromEntries(
    [...document.querySelectorAll('.dlsheet .dlsz')].map(e => [e.dataset.shape, e.textContent])));
  assert(sizes.full === 'about 76.5 MB, 59.3 MB of it the 9 recordings',
         'all of it: the whole bundle, and how much of it the recordings are (' + sizes.full + ')');
  assert(sizes.text === 'about 120 kB' && sizes.linked === 'about 212 kB',
         'and the other two shapes their own size (' + sizes.text + ', ' + sizes.linked + ')');
  STATUS.bundle.full = {bytes: 60000000, files: 20, media: 1, media_bytes: 59000000};
  await page.reload({waitUntil: 'domcontentloaded'});
  await page.waitForSelector('.sub');
  await page.click('header .dl');
  await page.waitForFunction(() => /about/.test(document.querySelector('.dlsz[data-shape="full"]').textContent));
  const one = await page.textContent('.dlsz[data-shape="full"]');
  assert(one === 'about 60.0 MB, nearly all of it the recording', 'one recording is "the recording" (' + one + ')');

  if (errors.length) throw Error('page errors: ' + errors.join(' | '));
  console.log(`\nnarration: ${passed} checks passed`);
} finally {
  await browser.close();
  await server.shutdown();
  await Deno.remove(TMP, {recursive: true}).catch(() => {});
}

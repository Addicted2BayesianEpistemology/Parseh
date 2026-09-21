import { chromium } from 'npm:playwright-core@1.52.0';
// Run: CHROME_BIN=/path/to/chrome deno run --allow-all tests/chapters.mjs
//
// Reading a long book, and reading it on a phone.
//
//  a) ONE CHAPTER AT A TIME.  A book of several chapters ships with the first
//     one in the page and every other one in a file beside it, fetched when it
//     is wanted -- by the contents, by scrolling near it, by the reading place.
//     The numbering (data-c, data-s) runs straight across the pieces, because a
//     piece is the very markup the build emitted, cut where the chapters were.
//  b) THE PASS TOGGLES AS ONE GROUP, and what hover mode does to them: the two
//     passes it swallows go grey (nothing they could show), the text passes
//     keep working -- hover mode with pass 1 alone is what they are for.
//  c) THE BAR ON A PHONE: away as the page moves down, back on the smallest
//     move up -- and NOT on a wide screen, which must be left alone.
//  d) THE GLOSS UNDER A FINGER: a tap in hover mode opens the chunk's cloud,
//     on a screen that claims a hover it never delivers as much as on one that
//     admits it has none.
//
// The book is the English fixture edition with a second chapter added, built.
const root = await Deno.realPath(new URL('..', import.meta.url));
Deno.chdir(root);
const PY = Deno.env.get('PARSEH_PYTHON') || 'python3';
const TMP = await Deno.makeTempDir({prefix: 'parseh-chapters-'});
const td = new TextDecoder();
async function py(code, ...args) {
  const o = await new Deno.Command(PY, {args: ['-c', code, ...args], stdout: 'piped', stderr: 'piped'}).output();
  if (!o.success) throw Error(td.decode(o.stderr) || td.decode(o.stdout));
  return td.decode(o.stdout);
}
let passed = 0;
const assert = (v, m) => { if (!v) throw Error('FAIL: ' + m); passed++; console.log('  ok', m); };
const sleep = ms => new Promise(r => setTimeout(r, ms));

// Two more chapters made out of the first, so nothing here has to author TeX:
// the same paragraphs renumbered into chapters 2 and 3, \input after it.
await py(String.raw`
import io, os, shutil, subprocess, sys
d = os.path.join(sys.argv[1], 'mini-en')
shutil.copytree('tests/fixtures/books/english/mini-en', d,
                ignore=shutil.ignore_patterns('reader', '.reader-key'))
p = os.path.join(d, 'ch1.tex')
ch1 = io.open(p, encoding='utf-8').read()
# THREE chapters, not two.  The reader deliberately fetches a chapter that has
# come within a screen or two of the window (the look-ahead that keeps reading
# from stopping), and these chapters are a few lines long, so the SECOND one is
# inside that margin the moment the book opens.  The third is far below it, and
# is what "nothing is fetched until it is wanted" can honestly be asked about.
for n in (2, 3):
    part = (ch1.replace('\\chapopen{1}', '\\chapopen{%d}' % n)
               .replace('\\parstart{1.', '\\parstart{%d.' % n)
               .replace('\\parnum{1.', '\\parnum{%d.' % n))
    io.open(os.path.join(d, 'ch%d.tex' % n), 'w', encoding='utf-8').write(part)
m = os.path.join(d, 'main.tex')
s = io.open(m, encoding='utf-8').read()
assert '\\input{ch1.tex}' in s, 'the fixture no longer inputs ch1.tex'
io.open(m, 'w', encoding='utf-8').write(
    s.replace('\\input{ch1.tex}',
              '\\input{ch1.tex}\n\\input{ch2.tex}\n\\input{ch3.tex}'))
subprocess.run([sys.executable, 'lib/tex2html.py', '--book', d], check=True, capture_output=True)
`, TMP);

const READER = `http://parseh.test${TMP}/mini-en/reader/index.html`;
const MIME = {html: 'text/html', js: 'text/javascript', css: 'text/css', json: 'application/json'};
const fetched = [];
async function serve(page) {
  await page.route('**/*', async route => {
    const url = new URL(route.request().url());
    if (url.hostname !== 'parseh.test') return route.abort();
    const path = decodeURIComponent(url.pathname);
    if (/\/ch-\d+\.html$/.test(path)) fetched.push(path.split('/').pop());
    // the reader asks for these whether or not anything answers
    if (path.endsWith('/timings.json') || path.endsWith('/api/marks'))
      return route.fulfill({status: 404, body: 'no'});
    if (path.endsWith('/__lookup')) return route.fulfill({json: {ok: true, have: false}});
    let body;
    try { body = await Deno.readTextFile(path); }
    catch (_) { return route.fulfill({status: 404, body: 'no such file'}); }
    return route.fulfill({body, contentType: MIME[path.split('.').pop()] || 'application/octet-stream'});
  });
}

/* ---------------- what the build wrote ---------------- */
console.log('a) the build splits the chapters');
const index = await Deno.readTextFile(`${TMP}/mini-en/reader/index.html`);
assert(index.includes('data-part="ch-1.html"'),
       'the page keeps the first chapter and names the file the second is in');
const frag = await Deno.readTextFile(`${TMP}/mini-en/reader/ch-1.html`);
assert(frag.startsWith('<section class="chapter"'), 'the fragment is the chapter section itself');
assert(frag.length * 10 < index.length,
       `the fragment is a fraction of the page (${frag.length} B against ${index.length} B)`);
const lastInPage = [...index.matchAll(/data-c="(\d+)"/g)].pop()[1];
const firstInFrag = frag.match(/data-c="(\d+)"/)[1];
assert(+firstInFrag === +lastInPage + 1,
       `the numbering runs across the pieces (page ends at ${lastInPage}, file starts at ${firstInFrag})`);

const browser = await chromium.launch({executablePath: Deno.env.get('CHROME_BIN'), headless: true});
const errors = [];
try {
  /* ---------------- the page, on a desktop ---------------- */
  const wide = await browser.newContext({viewport: {width: 1280, height: 900}});
  const page = await wide.newPage();
  page.on('pageerror', e => { errors.push(e.message); console.log('PAGE ERROR', e.message); });
  await serve(page);
  await page.goto(READER, {waitUntil: 'load'});

  console.log('b) the chapter arrives when it is asked for');
  assert(await page.locator('section.chapter').count() === 3, 'all three chapters are in the page');
  assert(await page.locator('section.chapter[data-part]').count() >= 1,
         'the ones below are still files: their markup is not in the page');
  const before = await page.locator('[data-c]').count();
  // the LAST chapter is far below the look-ahead margin, so opening the book
  // must not have gone near it
  assert(!fetched.includes('ch-2.html'),
         `opening the book fetched nothing that far down (${fetched.join(', ') || 'nothing at all'})`);

  // The contents: an entry of the LAST chapter, which is certainly not here.
  // AN ENTRY IS NAMED BY ITS PRINTED CHAPTER NUMBER and the sections are keyed
  // by INDEX -- 1, 2, 3 against 0, 1, 2 -- so the last chapter's entry is
  // data-ch="3" and its markup is in ch-2.html.  What the reader asked for is
  // the PARAGRAPH the entry names, and that is the only thing worth waiting
  // for: waiting on a section index instead let this pass while the jump
  // fetched a different chapter's file and the paragraph never arrived at all.
  await page.click('#toc');
  const entry = page.locator('#toclist a.toce[data-ch="3"]').first();
  assert(await entry.count() === 1, 'the contents lists the last chapter, which is not in the page');
  const want = await entry.getAttribute('href');
  await entry.click();
  await page.waitForFunction(h => !!document.getElementById(h.slice(1)), want, {timeout: 10000});
  assert(await page.evaluate(h => !!document.getElementById(h.slice(1)), want),
         `the paragraph the entry names (${want}) is in the page`);
  assert(fetched.filter(f => f === 'ch-2.html').length === 1,
         `and its own chapter's file was fetched, once (${fetched.join(', ')})`);
  const after = await page.locator('[data-c]').count();
  assert(after > before, `the chunks of that chapter are there too (${before} then ${after})`);

  console.log('c) the pass toggles are one group');
  assert(await page.locator('.pgrp .pgrpb button[data-toggle]').count() >= 2,
         'the numbered buttons live in the group');
  assert((await page.locator('.pgrp .pgrpc').textContent()).trim() === 'which passes you see',
         'and the caption under them says what they are');

  console.log('d) hover mode greys what it swallows and leaves the rest');
  const enabled = s => page.locator(s).evaluate(b => !b.disabled);
  await page.click('#hovermode');
  assert(!(await enabled('[data-toggle=no2]')), 'the chunks-and-glosses toggle goes grey');
  assert(!(await enabled('[data-toggle=nogloss]')), 'so does the gloss switch, which only acts on them');
  assert(await enabled('[data-toggle=no1]'), 'the text pass keeps its button');
  // and it WORKS: hover mode showing the hoverable text alone is the point
  await page.click('[data-toggle=no1]');
  await page.waitForFunction(() =>
    getComputedStyle(document.querySelector('.pass.p1')).display === 'none');
  assert(true, 'turning pass 1 off in hover mode really hides it');
  await page.click('[data-toggle=no1]');
  await page.click('#hovermode');
  assert(await enabled('[data-toggle=no2]'), 'and the greyed buttons come back when hover mode goes');

  console.log('e) a wide screen keeps its bar');
  await page.evaluate(() => window.scrollTo(0, 1200));
  await sleep(150);
  assert(!(await page.evaluate(() => document.body.classList.contains('barhidden'))),
         'scrolling down a desktop page changes nothing');
  await page.close();

  /* ---------------- the same book on a phone ---------------- */
  console.log('f) the bar on a phone');
  const phone = await browser.newContext({viewport: {width: 390, height: 780}, hasTouch: true});
  const ph = await phone.newPage();
  ph.on('pageerror', e => { errors.push('phone: ' + e.message); console.log('PAGE ERROR', e.message); });
  await serve(ph);
  await ph.goto(READER, {waitUntil: 'load'});
  const hidden = () => ph.evaluate(() => document.body.classList.contains('barhidden'));
  assert(!(await hidden()), 'it starts with the bar');
  await ph.evaluate(() => window.scrollTo(0, 900));
  await ph.waitForFunction(() => document.body.classList.contains('barhidden'));
  assert(true, 'moving down takes it away');
  // the smallest move up, and NOT only at the top of the page
  await ph.evaluate(() => window.scrollBy(0, -40));
  await ph.waitForFunction(() => !document.body.classList.contains('barhidden'));
  assert(await ph.evaluate(() => window.pageYOffset > 400),
         'a small move up brings it back, in the middle of the book');

  console.log('g) the gloss under a finger');
  await ph.evaluate(() => window.scrollTo(0, 0));
  await ph.click('#hovermode');
  const word = ph.locator('.p1 .w').first();
  await word.tap();
  await ph.waitForSelector('#cloud:not([hidden])');
  assert(true, "a tap in hover mode opens the chunk's gloss");
  await word.tap();
  await ph.waitForSelector('#cloud', {state: 'hidden'});
  assert(true, 'and tapping it again closes it');

  if (errors.length) throw Error('page errors: ' + errors.join(' | '));
  console.log(`\nchapters: ${passed} checks passed`);
} finally {
  await browser.close();
  await Deno.remove(TMP, {recursive: true}).catch(() => {});
}

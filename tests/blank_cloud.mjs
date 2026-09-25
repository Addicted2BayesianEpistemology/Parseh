// SPDX-License-Identifier: GPL-3.0-or-later
// Browser test of a blank's cloud in the browser interface (a0.3.1;
// markdown/app/static/app.js, bindExercises): a fill-in's blank and a
// matching exercise's place are filled from a cloud of the bank's words on
// a click, as in the mobile interface -- and the browser's own ways stay
// beside it: a word dragged, and a word picked and then its place clicked,
// which puts the word there and opens nothing.  Driven with a mouse and the
// keyboard on the studio's document page, on a deck's study and cram pages
// (tests/decks_harness.py: the real routes on a temporary library), and in
// the file the HTML export gives, opened from disk as a student opens it.
// The mobile interface is checked to have the cloud alone, as before: a
// word of the bank is neither picked nor dragged there.
//   CHROME_BIN=... PARSEH_PYTHON=python3 deno run --allow-all tests/blank_cloud.mjs
import {chromium} from 'npm:playwright-core@1.52.0';

const root = await Deno.realPath(new URL('..', import.meta.url));
const python = Deno.env.get('PARSEH_PYTHON') || 'python3';

const FILL = `:::exercise fill-blanks
prompt: Complete the sentence with the past of [go]{tl} and of [buy]{tl}.
text: [Yesterday I [[go]] to the market and [[buy]] two apples.]{tl}
- [go] [went]{tl}
- [buy] [bought]{tl}
- [ ] [goed]{tl}
:::`;
const MATCH = `:::exercise match-translations
prompt: Match each British word with the American one.
- [flat]{tl} => [apartment]{tl}
- [lift]{tl} => [elevator]{tl}
- [biscuit]{tl} => [cookie]{tl}
:::`;
const DOC = `---\ntitle: Clouds\ntarget: en\n---\n\nSome text first.\n\n${FILL}\n\n${MATCH}\n`;
const RIGHT = {flat: 'apartment', lift: 'elevator', biscuit: 'cookie'};

let passed = 0;
const assert = (v, m) => { if (!v) throw new Error('FAIL: ' + m); passed++; console.log('  ok', m); };
const eq = (got, want, m) => assert(JSON.stringify(got) === JSON.stringify(want),
  m + (JSON.stringify(got) === JSON.stringify(want) ? '' : ': got ' + JSON.stringify(got) + ' want ' + JSON.stringify(want)));
const word = w => new RegExp('^\\s*' + w + '\\s*$');

const texts = (page, sel) => page.evaluate(sel => [...document.querySelectorAll(sel)].map(x => x.textContent.trim()), sel);
/* Drawn and on top: laid out, visible, and what the pointer finds at its
   middle -- never "not hidden", which a box with no CSS at all also is. */
const drawn = (page, sel) => page.evaluate(sel => {
  const el = document.querySelector(sel);
  if (!el) return false;
  const r = el.getBoundingClientRect(), st = getComputedStyle(el);
  if (!r.width || !r.height || st.visibility !== 'visible' || st.display === 'none') return false;
  const at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
  return !!at && el.contains(at);
}, sel);
/* Polled from the browser's side: the exported file's own rules refuse the
   eval page.waitForFunction polls with. */
async function until(page, fn, arg = null, what = 'the page', timeout = 8000) {
  const end = Date.now() + timeout;
  while (!(await page.evaluate(fn, arg))) {
    if (Date.now() > end) throw Error('FAIL: timed out waiting for ' + what);
    await page.waitForTimeout(40);
  }
}
async function cloudOpen(page, X) {
  const sel = `${X} .ex-cloud`;
  const end = Date.now() + 8000;
  while (!(await drawn(page, sel))) {
    if (Date.now() > end) throw Error('FAIL: no cloud drawn in ' + X);
    await page.waitForTimeout(40);
  }
  await page.waitForTimeout(180);                 // its fade in, over
}
const pickFromCloud = (page, X, w) => page.locator(`${X} .ex-cloud button`).filter({hasText: word(w)}).click();

/* A fill-in, every way the browser interface fills it; it ends right. */
async function fillEveryWay(page, S, tag) {
  const X = `${S} .exercise[data-subtype="fill-blanks"]`;
  const blank = n => page.locator(`${X} .ex-blank`).nth(n);
  const inBank = w => page.locator(`${X} .ex-bank .ex-item`).filter({hasText: word(w)});
  const blanks = () => texts(page, `${X} .ex-blank`);
  const bank = async () => (await texts(page, `${X} .ex-bank .ex-item`)).sort();
  const cloudShown = () => drawn(page, `${X} .ex-cloud`);
  eq([await blanks(), await bank()], [['', ''], ['bought', 'goed', 'went']], `${tag}: two empty blanks, three words in the bank`);

  // a click on a blank: its cloud, as in the mobile interface
  await blank(0).click();
  await cloudOpen(page, X);
  eq((await texts(page, `${X} .ex-cloud .ex-cloud-pick`)).sort(), ['bought', 'goed', 'went'],
     `${tag}: a click on a blank opens its cloud, a copy of every word the bank holds`);
  const geo = await page.evaluate(X => {
    const c = document.querySelector(X + ' .ex-cloud').getBoundingClientRect();
    const e = document.querySelector(X).getBoundingClientRect();
    const b = document.querySelector(X + ' .ex-blank');
    const br = b.getBoundingClientRect();
    return {inside: c.left >= e.left - 0.5 && c.right <= e.right + 0.5,
            onScreen: c.top >= 0 && c.left >= 0 && c.bottom <= innerHeight && c.right <= innerWidth,
            clear: c.top >= br.bottom - 1 || c.bottom <= br.top + 1,
            says: [b.getAttribute('aria-expanded'), b.classList.contains('choosing')],
            tallest: Math.max(...[...document.querySelectorAll(X + ' .ex-cloud-pick')].map(p => p.getBoundingClientRect().height)),
            cursor: getComputedStyle(b).cursor};
  }, X);
  eq([geo.inside, geo.onScreen, geo.clear, geo.says], [true, true, true, ['true', true]],
     `${tag}: the cloud inside the exercise and the window, clear of its blank, which says its cloud is open`);
  assert(geo.tallest > 24 && geo.tallest < 48,
         `${tag}: with a mouse its words are the bank's size, not a finger's (${Math.round(geo.tallest)}px)`);
  eq(geo.cursor, 'pointer', `${tag}: a blank's pointer says it is clicked`);
  await pickFromCloud(page, X, 'went');
  eq([await blanks(), await bank(), await cloudShown()], [['went', ''], ['bought', 'goed'], false],
     `${tag}: went from the cloud: in the first blank, gone from the bank, the cloud away`);
  eq(await page.evaluate(X => document.activeElement === document.querySelector(X + ' .ex-blank'), X), true,
     `${tag}: the focus back on its blank`);

  // a drag, as it always was
  await inBank('bought').dragTo(blank(1));
  eq([await blanks(), await bank()], [['went', 'bought'], ['goed']], `${tag}: bought dragged into the second blank`);

  // a filled blank's cloud: the words left, and a way to empty it
  await blank(0).click();
  await cloudOpen(page, X);
  eq(await texts(page, `${X} .ex-cloud button`), ['goed', 'Empty this blank'],
     `${tag}: a filled blank's cloud: the word left, and Empty this blank`);
  await pickFromCloud(page, X, 'goed');
  eq([await blanks(), await bank()], [['goed', 'bought'], ['went']], `${tag}: goed put in its place, went back in the bank`);
  await blank(0).click();
  await cloudOpen(page, X);
  await pickFromCloud(page, X, 'Empty this blank');
  eq([await blanks(), await bank()], [['', 'bought'], ['goed', 'went']], `${tag}: emptied: its word back in the bank`);

  // a word picked, then its blank: the word goes there, and no cloud opens
  await inBank('went').click();
  eq(await texts(page, `${X} .picked`), ['went'], `${tag}: a word of the bank clicked is picked up`);
  assert(!(await cloudShown()), `${tag}: and opens nothing`);
  await blank(0).click();
  eq([await blanks(), await bank(), await cloudShown(), await texts(page, `${X} .picked`)],
     [['went', 'bought'], ['goed'], false, []],
     `${tag}: then its blank clicked: the picked word goes there, and no cloud opens`);

  // a drag while a cloud is open: the cloud, a copy of the bank as it was, goes
  await blank(1).click();
  await cloudOpen(page, X);
  await inBank('goed').dragTo(blank(1));
  eq([await blanks(), await bank(), await cloudShown()], [['went', 'goed'], ['bought'], false],
     `${tag}: a word dragged while a cloud is open: placed, and the cloud away`);

  // from the keyboard: Enter on a blank opens its cloud, Escape puts it away
  await blank(1).focus();
  await page.keyboard.press('Enter');
  await cloudOpen(page, X);
  eq(await page.evaluate(() => document.activeElement.closest('.ex-cloud') ? document.activeElement.textContent.trim() : null),
     'bought', `${tag}: Enter on a blank opens its cloud, its first word focused`);
  await page.keyboard.press('Escape');
  eq([await cloudShown(), await page.evaluate(X => document.activeElement === document.querySelectorAll(X + ' .ex-blank')[1], X)],
     [false, true], `${tag}: Escape puts it away, the focus back on the blank`);
  await page.keyboard.press('Enter');
  await cloudOpen(page, X);
  await page.keyboard.press('Enter');
  eq([await blanks(), await bank(), await cloudShown()], [['went', 'bought'], ['goed'], false],
     `${tag}: Enter on a word of the cloud puts it in the blank`);

  // a click anywhere else puts the cloud away
  await blank(0).click();
  await cloudOpen(page, X);
  await page.locator(`${X} .ex-prompt`).click();
  eq([await cloudShown(), await blanks()], [false, ['went', 'bought']], `${tag}: a click anywhere else puts the cloud away, and changes nothing`);
}

/* A matching exercise: one place from its cloud, one by a drag, one by a
   word picked and then its place; it ends right. */
async function matchEveryWay(page, S, tag) {
  const X = `${S} .exercise[data-primitive="matching"]`;
  const place = n => page.locator(`${X} .ex-match-drop`).nth(n);
  const inBank = w => page.locator(`${X} .ex-bank .ex-item`).filter({hasText: word(w)});
  const rows = () => page.evaluate(X => [...document.querySelectorAll(X + ' .ex-pair-row')].map(r =>
    [r.querySelector('.ex-pair-left').textContent.trim(), r.querySelector('.ex-match-drop').textContent.trim()]), X);
  const terms = (await rows()).map(r => r[0]);
  eq(terms.slice().sort(), ['biscuit', 'flat', 'lift'], `${tag}: three terms to match`);
  eq(await page.evaluate(X => getComputedStyle(document.querySelector(X + ' .ex-match-drop'), '::after').content, X),
     '"drop or click to choose"', `${tag}: an empty place says it takes a drop or a click`);
  await place(0).click();
  await cloudOpen(page, X);
  eq((await texts(page, `${X} .ex-cloud .ex-cloud-pick`)).sort(), ['apartment', 'cookie', 'elevator'],
     `${tag}: a click on a place opens its cloud, a copy of every answer the bank holds`);
  await pickFromCloud(page, X, RIGHT[terms[0]]);
  await inBank(RIGHT[terms[1]]).dragTo(place(1));
  await inBank(RIGHT[terms[2]]).click();
  await place(2).click();
  eq([(await rows()).map(r => r[1]), await drawn(page, `${X} .ex-cloud`), await texts(page, `${X} .ex-bank .ex-item`)],
     [terms.map(t => RIGHT[t]), false, []],
     `${tag}: every term matched: one from its cloud, one dragged, one picked and then its place clicked`);
}

async function startHarness() {
  const proc = new Deno.Command(python, {args: [root + '/tests/decks_harness.py', 'studio'], cwd: root,
                                         stdout: 'piped', stderr: 'inherit'}).spawn();
  const reader = proc.stdout.pipeThrough(new TextDecoderStream()).getReader();
  let buf = '', info = null;
  while (!info) {
    const {value, done} = await reader.read();
    if (done) throw Error('harness exited before READY:\n' + buf);
    buf += value;
    const m = buf.match(/READY (\{.*\})\n/);
    if (m) info = JSON.parse(m[1]);
  }
  (async () => { for (;;) { const r = await reader.read(); if (r.done) break; } })();
  return {proc, info};
}

const browser = await chromium.launch({executablePath: Deno.env.get('CHROME_BIN') || undefined});
const {proc, info} = await startHarness();
const url = p => `http://127.0.0.1:${info.port}${p}`;
const tmp = await Deno.makeTempDir({prefix: 'parseh-blank-cloud-'});
const errors = [];
const watch = (page, name) => {
  page.on('pageerror', e => errors.push(`${name}: ${e.message}`));
  page.on('console', m => {
    if (m.type() === 'error' && !/Failed to load resource/.test(m.text())) errors.push(`${name} console: ${m.text()}`);
  });
};
try {
  // a worker would answer the mobile interface's pages from its cache
  const ctx = await browser.newContext({viewport: {width: 1280, height: 900}, serviceWorkers: 'block'});
  const request = ctx.request;
  const made = await request.post(url('/api/docs'), {data: {markdown: DOC}});
  eq(made.status(), 201, 'the document is made');
  const doc = (await made.json()).meta;

  console.log('the document page, in the browser interface');
  const page = await ctx.newPage();
  watch(page, 'doc');
  await page.goto(url(`/doc/${doc.id}`));
  await page.waitForSelector('.sheet .exercise .ex-blank');
  eq(await page.evaluate(() => document.documentElement.getAttribute('data-mode')), 'browser', 'the browser interface');
  // every message the page shows while the exercises are answered
  await page.evaluate(() => {
    window.__toasts = [];
    const t = document.querySelector('#toast');
    new MutationObserver(() => window.__toasts.push(t.textContent)).observe(t, {childList: true, characterData: true, subtree: true});
  });
  // the reading view's colour palette opens over a word of the page ...
  const F = '.sheet .exercise[data-subtype="fill-blanks"]';
  const kin = await page.evaluate(F => !!document.querySelector(F + ' .ex-bank [data-fa]'), F);
  if (kin) {
    await page.locator(`${F} .ex-bank [data-fa]`).first().hover();
    await page.waitForTimeout(400);
    assert(await drawn(page, '.fapal'), 'document: the colour palette opens over a word of the bank (as it always has)');
  }
  // ... and never over a word of a blank's cloud, a copy to choose from
  await page.locator(`${F} .ex-blank`).nth(0).click();
  await cloudOpen(page, F);
  await page.locator(`${F} .ex-cloud .ex-cloud-pick`).first().hover();
  await page.waitForTimeout(700);
  eq([await drawn(page, '.fapal'), await page.evaluate(F => document.querySelectorAll(F + ' .ex-cloud [data-fa]').length, F)],
     [false, 0], 'document: no colour palette over a word of the cloud');
  await page.keyboard.press('Escape');
  await fillEveryWay(page, '.sheet', 'document');
  await matchEveryWay(page, '.sheet', 'document');
  eq(await page.evaluate(() => window.__toasts.filter(t => /^Copied/.test(t))), [],
     'document: answering copies nothing to the clipboard (no "Copied" message)');
  await page.locator('.ex-correct-all').click();
  eq(await page.locator('.ex-score').textContent(), '2 / 2 correct', 'document: Check exercises marks both right');
  eq(await page.evaluate(() => [...document.querySelectorAll('.sheet .exercise[data-scored="1"]')].map(x => x.classList.contains('correct'))),
     [true, true], 'document: each exercise marked correct');

  console.log('a deck, studied and crammed, in the browser interface');
  const deck = (await (await request.post(url('/exercises/api/decks'), {data: {name: 'Clouds', lang: 'en'}})).json()).deck;
  const api = `/exercises/api/decks/${deck.path}`;
  const fillItem = (await (await request.post(url(`${api}/items`), {data: {markdown: FILL}})).json()).item;
  const matchItem = (await (await request.post(url(`${api}/items`), {data: {markdown: MATCH}})).json()).item;
  const study = await ctx.newPage();
  watch(study, 'study');
  await study.goto(url(`/exercises/deck/${deck.path}/study`));
  await study.waitForSelector('#study-stage .exercise');
  const first = await study.evaluate(() => document.querySelector('#study-stage .exercise').dataset.primitive);
  if (first === 'matching') await matchEveryWay(study, '#study-stage', 'study');
  else await fillEveryWay(study, '#study-stage', 'study');
  for (const [item, run] of [[fillItem, fillEveryWay], [matchItem, matchEveryWay]]) {
    const cram = await ctx.newPage();
    watch(cram, 'cram');
    await cram.goto(url(`/exercises/deck/${deck.path}/`));
    await cram.evaluate(([k, id]) => sessionStorage.setItem(k, JSON.stringify([id])), [`parseh-cram:${deck.path}`, item.id]);
    await cram.goto(url(`/exercises/deck/${deck.path}/cram`));
    await cram.waitForSelector('#cram-stage .exercise');
    await run(cram, '#cram-stage', 'cram');
    await cram.locator('#cram-check').click();
    await cram.waitForFunction(() => document.querySelector('#cram-stage .exercise.correct'));
    assert(true, 'cram: checked, it is right');
    await cram.close();
  }

  console.log('the HTML export, opened from disk');
  const got = await request.get(url(`/download/${doc.id}/html`));
  eq(got.status(), 200, 'the document exported to one HTML file');
  const file = `${tmp}/clouds.html`;
  await Deno.writeFile(file, new Uint8Array(await got.body()));
  const offline = await browser.newContext({viewport: {width: 1280, height: 900}});
  await offline.route(/^https?:/, route => route.abort());
  const xp = await offline.newPage();
  watch(xp, 'export');
  await xp.goto('file://' + file);
  await until(xp, () => !!document.querySelector('.exercise .ex-blank'), null, 'the exported exercises');
  await fillEveryWay(xp, 'body', 'export');
  await matchEveryWay(xp, 'body', 'export');
  await xp.locator('.ex-correct-all').click();
  eq(await xp.locator('.ex-score').textContent(), '2 / 2 correct', 'export: Check exercises marks both right');
  await offline.close();

  console.log('the mobile interface: the cloud alone');
  await page.evaluate(() => localStorage.setItem('parseh_mode', 'mobile'));
  await page.reload();
  await page.waitForSelector('.sheet .exercise .ex-blank');
  eq(await page.evaluate(() => document.documentElement.getAttribute('data-mode')), 'mobile', 'the mobile interface');
  const X = '.sheet .exercise[data-subtype="fill-blanks"]';
  await page.locator(`${X} .ex-bank .ex-item`).first().click();
  eq(await page.evaluate(X => document.querySelectorAll(X + ' .picked, ' + X + ' .ex-cloud').length, X), 0,
     'mobile: a word of the bank clicked picks nothing up and opens nothing');
  await page.locator(`${X} .ex-bank .ex-item`).filter({hasText: word('went')}).dragTo(page.locator(`${X} .ex-blank`).nth(0));
  eq(await texts(page, `${X} .ex-blank`), ['', ''], 'mobile: a word dragged goes nowhere');
  await page.locator(`${X} .ex-blank`).nth(0).click();
  await cloudOpen(page, X);
  const tallest = await page.evaluate(X => Math.min(...[...document.querySelectorAll(X + ' .ex-cloud-pick')]
    .map(p => p.getBoundingClientRect().height)), X);
  assert(tallest >= 47.5, `mobile: the cloud's words a finger's size (${Math.round(tallest)}px)`);
  await pickFromCloud(page, X, 'went');
  eq(await texts(page, `${X} .ex-blank`), ['went', ''], 'mobile: a blank filled from its cloud');
  await page.evaluate(() => localStorage.setItem('parseh_mode', 'browser'));

  eq(errors, [], 'no page error, nothing in the console');
  await ctx.close();
  console.log(`blank_cloud: ${passed} checks passed`);
} finally {
  await browser.close();
  try { proc.kill('SIGTERM'); } catch (_) { /* gone */ }
  await Deno.remove(tmp, {recursive: true}).catch(() => {});
}

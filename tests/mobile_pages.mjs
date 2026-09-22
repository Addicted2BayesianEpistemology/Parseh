// SPDX-License-Identifier: GPL-3.0-or-later
// Browser test of the mobile interface's books and exercises (docs/mobile.md),
// against the REAL hub (serve.main, booted by tests/mobile_harness.py) over a
// temporary toolbox: the fixture editions of English (narrated), Persian,
// Arabic, Japanese, Hindi and Chinese with their readers built, the Italian one
// never built, and three exercise decks.  Measured where the page is drawn -- computed
// display, bounding rects, elementFromPoint -- on a phone held upright (390x844
// and 360x740, touch, Chromium's device emulation), on one held sideways
// (844x390, touch), and on a desktop with a mouse:
//
// shelf -- the book shelf, /m/books/:
//   a) the mobile hub's Books door, tapped, lands on /m/books/ (the browser
//      hub's lands on the library, /books/); a ctrl-click too, in a new tab;
//      sideways, the hub's doors two to a row
//   b) all there is to tap: home, the switch, the theme, the chips and one card
//      per built book, each 48px high at the least, inside the screen and
//      reached by a tap on it; the book never built says so and is no link; no
//      delete, no build, no bundle, no stop; the page never scrolls sideways;
//      sideways, the books two to a row
//   c) a chip shows its language's books and heading alone (the shelf holds
//      Persian, Arabic, Italian unbuilt, Japanese, English, Hindi, Chinese)
//   d) a book read on this phone says how far ("read on"), and its card opens
//      the reader at the address the place was kept under
//   e) Browser, pressed on the shelf, goes to the library; the shelf opened in
//      the browser mode says what it is and where the library is
// reader -- a book's reader, in the mobile mode (lib/mobilereader.js):
//   a) opened from the shelf; its header: the way out (hub, shelf), the
//      contents, the text size and ⋯ -- and on a narrated book ↺ ▶ ↻, on a
//      line of their own upright and on the one line sideways -- each 48px at
//      the least, on the screen; nothing else of the header drawn, and none of
//      the page's writing doors -- book info, the builds, the narration,
//      folding, timings, stop, download, the dictionary setup, the pencil, a
//      note's plus
//   b) ⋯ opens the rest, a group to a line: the passes, the listening (only a
//      narrated book), this page (the theme, the bars, the switch); the passes
//      still hide their pass; the theme still turns; sideways, the header
//      never taller than the screen
//   c) the contents opens, without its naming; the gloss cloud opens on a tap
//      in hover mode, with copy and without card or edit
//   d) on a desktop in the mobile mode, alt-click on a word opens no card
//      sheet and E no chunk editor -- both of which they open in the browser
//      mode, measured on the same page
//   e) play plays, and the shelf's ▤ goes to the mobile shelf
//   f) Browser, pressed, gives the reader back its browser header, the same
//      controls as it had before Mobile was pressed
//   g) ↻ and ↺ move the recording by the seconds the Listening group's field
//      says, and the reading place with it; the field keeps its number for
//      every book, and refuses nonsense; sideways, the header goes on the
//      way down and comes back on the way up, and stays while ⋯ is open
// decks -- the exercise decks, /exercises/ (markdown/app, static/mobile.css):
//   a) the mobile hub's Exercises door lands on the decks' mobile layout, the
//      browser bar display:none; all there is to tap: home, the switch, the
//      theme, the chips, and a deck's name, Study and Open -- no import,
//      backup, restore, new deck, stop, ⋯ -- each 48px at the least
//   b) a chip filters the decks; the theme button turns the page dark
//   c) a deck: its counts, Study now and Cram all, and its exercises to pick
//      from -- the filters, all, shown, by tag, none -- and no rename, add,
//      export, options, delete, nor anything in the list that changes an
//      exercise; an empty deck says where exercises are added
//   d) studying: no bar over the exercise, no Edit, no key hints, no stop; ‹
//      back to the deck; Show answer or Check, then Next in the very same
//      place and the four ratings with their intervals -- a bar at the foot
//      upright, a column down the right sideways; Next and Good schedule the
//      exercise (the deck's own file says so); a choice answered right says
//      Correct
//   e) Cram all crams every exercise of the deck, the scheduling as it was; two
//      picked by hand are crammed, and so are the ones a tag picks
//   f) Browser, pressed, brings back every control of the browser layout
// app -- the mobile interface as an app (lib/mobile.py, lib/sw.js):
//   a) the app's address, /?mode=mobile, sets the mode and is given back
//      without it; the hub, the shelf, a reader and the decks are installable
//      as Chromium judges it (the one thing it has against them is the test's
//      own incognito profile), the worker taking the pages over
//   b) the install page says this phone trusts Parseh; the hub has its door
//   c) the server stopped, a page opened says Parseh cannot be reached
//   CHROME_BIN=... PARSEH_PYTHON=python3 deno run --allow-all tests/mobile_pages.mjs
//   MOBILE_PARTS=shelf,reader,decks,app runs some of it; SHOTS=<dir> saves pictures
import { chromium } from 'npm:playwright-core@1.52.0';

const root = await Deno.realPath(new URL('..', import.meta.url));
Deno.chdir(root);
const PY = Deno.env.get('PARSEH_PYTHON') || 'python3';
const SHOTS = Deno.env.get('SHOTS') || '';
const PARTS = (Deno.env.get('MOBILE_PARTS') || 'shelf,reader,decks,app').split(',');
const td = new TextDecoder();
let passed = 0;
const assert = (v, m) => { if (!v) throw Error('FAIL: ' + m); passed++; console.log('  ok', m); };
const eq = (got, want, m) => assert(JSON.stringify(got) === JSON.stringify(want),
  m + (JSON.stringify(got) === JSON.stringify(want) ? '' : ': got ' + JSON.stringify(got) + ' want ' + JSON.stringify(want)));
const near = (a, b, tol = 2) => Math.abs(a - b) <= tol;
const sleep = ms => new Promise(r => setTimeout(r, ms));
function freePort() {
  const l = Deno.listen({hostname: '127.0.0.1', port: 0});
  const p = l.addr.port;
  l.close();
  return p;
}

// ---- the toolbox, and its server
const WORK = await Deno.makeTempDir({prefix: 'parseh-mobile-pages-'});
const built = await new Deno.Command(PY, {args: ['tests/mobile_harness.py', 'build', WORK], cwd: root,
                                          stdout: 'piped', stderr: 'piped'}).output();
if (!built.success) throw Error(td.decode(built.stderr) || td.decode(built.stdout));
const MADE = JSON.parse(td.decode(built.stdout).trim().split('\n').pop());
const port = freePort();
const log = [];
const hub = new Deno.Command(PY, {args: ['tests/mobile_harness.py', 'serve', WORK, String(port)], cwd: root,
                                  stdout: 'piped', stderr: 'piped'}).spawn();
let hubUp = true;
for (const s of [hub.stdout, hub.stderr])
  (async () => { for await (const c of s.pipeThrough(new TextDecoderStream())) log.push(c); })();
const B = `http://127.0.0.1:${port}`;
for (const t = Date.now();;) {
  try { const r = await fetch(B + '/'); await r.body?.cancel(); if (r.ok) break; } catch (_) {}
  if (Date.now() - t > 60000) throw Error('the hub did not start:\n' + log.join(''));
  await sleep(250);
}

const browser = await chromium.launch({executablePath: Deno.env.get('CHROME_BIN'), headless: true});
const errors = [];
const PHONE = {viewport: {width: 390, height: 844}, isMobile: true, hasTouch: true};
const NARROW = {viewport: {width: 360, height: 740}, isMobile: true, hasTouch: true};
// a phone held sideways, the way it is held most (docs/mobile.md)
const LAND = {viewport: {width: 844, height: 390}, isMobile: true, hasTouch: true};
const DESK = {viewport: {width: 1280, height: 800}};

async function newPage(opts, tag) {
  const ctx = await browser.newContext(opts);
  const page = await ctx.newPage();
  page.on('pageerror', e => { errors.push(tag + ': ' + e.message); console.log('PAGE ERROR', tag, e.message); });
  // Chromium's headless shell drops the touch emulation when a screenshot
  // resizes the page (tests/mobile_mode.mjs, grab): said again over CDP
  if (opts.hasTouch) {
    page.touch = await ctx.newCDPSession(page);
    await page.touch.send('Emulation.setTouchEmulationEnabled', {enabled: true, maxTouchPoints: 1});
  }
  return page;
}
const tap = async (page, sel) => { const l = page.locator(sel).first(); if (page.touch) await l.tap(); else await l.click(); };
const settle = page => page.evaluate(() => document.fonts.ready.then(() =>
  new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))));
const shot = async (page, name) => {
  if (!SHOTS) return;
  await Deno.mkdir(SHOTS, {recursive: true});
  await page.screenshot({path: `${SHOTS}/${name}.png`});
  if (page.touch) await page.touch.send('Emulation.setTouchEmulationEnabled', {enabled: true, maxTouchPoints: 1});
};
const setMode = (page, m) => page.evaluate(m => {
  // the one switch, as the pages keep it (Parseh.mode on the toolbox's own
  // pages, decks.js on the studio's): stored, and mirrored in the cookie
  localStorage.setItem('parseh_mode', m);
  document.cookie = 'parseh_mode=' + m + '; Path=/; SameSite=Lax; Max-Age=31536000';
}, m);
// The header of a mobile page goes on the way down (parseh.js, bars()): a
// test that scrolled -- or a reader that went back to its reading place --
// brings it back as a person does, with a small move up.
async function reveal(page) {
  if (!(await page.evaluate(() => document.body.classList.contains('barhidden')))) return;
  await page.evaluate(() => scrollBy(0, -12));
  await page.waitForFunction(() => !document.body.classList.contains('barhidden'));
  await sleep(250);                                   // the slide back
}
// a tap on what sel matches, brought to the middle of the screen first --
// where no bar is over it, and nothing that floats at the foot
async function tapMiddle(page, sel) {
  await page.locator(sel).first().evaluate(e => e.scrollIntoView({block: 'center'}));
  await sleep(250);
  await tap(page, sel);
}
const rect = (page, sel) => page.evaluate(sel => {
  const e = document.querySelector(sel);
  if (!e) return null;
  const r = e.getBoundingClientRect();
  return {l: r.left, r: r.right, t: r.top, b: r.bottom, w: r.width, h: r.height};
}, sel);

// ---- what a page shows, measured
const CLICKABLE = 'a[href], button, input, select, textarea, summary, [tabindex]:not([tabindex="-1"]), label[for]';
// every element that can be clicked and is drawn, said as tag:what
function clickable(page, scope) {
  return page.evaluate(([sel, scope]) => {
    const drawn = el => el.getClientRects().length > 0 && getComputedStyle(el).visibility !== 'hidden';
    const what = el => {
      const s = el.getAttribute('href') || el.getAttribute('data-parseh-mode') || el.getAttribute('data-pick') ||
        (el.hasAttribute('data-parseh-theme') ? 'theme' : '') || el.id || (el.getAttribute('data-x') || '') ||
        el.className || el.textContent.trim().slice(0, 20);
      return el.tagName.toLowerCase() + ':' + s;
    };
    const base = scope ? document.querySelector(scope) : document;
    return [...base.querySelectorAll(sel)].filter(drawn).map(what);
  }, [CLICKABLE, scope || null]);
}
// the targets matching sel: size, inside the screen, and whether a tap at
// the middle of each (scrolled into view first) reaches it
function targets(page, sel) {
  return page.evaluate(sel => [...document.querySelectorAll(sel)]
    .filter(el => el.getClientRects().length > 0 && getComputedStyle(el).visibility !== 'hidden')
    .map(el => {
      el.scrollIntoView({block: 'center', inline: 'nearest'});
      const r = el.getBoundingClientRect();
      const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
      return {what: (el.id || el.getAttribute('href') || el.getAttribute('data-parseh-mode') ||
                     el.getAttribute('data-pick') || el.className || el.textContent.trim()).toString().slice(0, 40),
              w: Math.round(r.width), h: Math.round(r.height), l: r.left, r: r.right, top: Math.round(r.top),
              inside: r.left >= -0.5 && r.right <= innerWidth + 0.5,
              hit: !!hit && (hit === el || el.contains(hit))};
    }), sel);
}
function allFit(list, m, min = 48) {
  const bad = list.filter(t => !(t.h >= min && t.w >= min && t.inside && t.hit));
  assert(list.length > 0 && bad.length === 0, m + (bad.length ? ' -- not: ' + JSON.stringify(bad) : ` (${list.length})`));
}
const sideways = page => page.evaluate(() => document.documentElement.scrollWidth - innerWidth);
const isDrawn = (page, sel) => page.evaluate(sel => [...document.querySelectorAll(sel)]
  .some(el => el.getClientRects().length > 0 && getComputedStyle(el).visibility !== 'hidden'), sel);
// the tops of what sel matches, where each stands now (nothing scrolled)
const tops = (page, sel) => page.evaluate(sel => [...document.querySelectorAll(sel)]
  .filter(e => e.getClientRects().length).map(e => Math.round(e.getBoundingClientRect().top)), sel);

// ======== shelf ========
async function partShelf() {
  for (const [opts, tag] of [[PHONE, 'phone'], [NARROW, 'narrow'], [LAND, 'landscape'], [DESK, 'desktop']]) {
    console.log(`\n== shelf, ${tag}`);
    const page = await newPage(opts, 'shelf ' + tag);
    // ---- a) the doors
    await page.goto(B + '/');
    await setMode(page, 'browser');
    await page.reload();
    if (tag === 'phone') {
      await Promise.all([page.waitForURL(B + '/books/'), tap(page, '.hub-browser a.door[href="/books/"]')]);
      assert(true, 'the browser hub: Books opens the library, /books/');
      await page.goto(B + '/');
    }
    // the switch in the browser bar, pressed as a person presses it
    await tap(page, '.parseh-bar:not(.m-bar) [data-parseh-mode=mobile]');
    eq(await page.evaluate(() => document.documentElement.getAttribute('data-mode')), 'mobile', 'Mobile pressed on the hub');
    if (tag === 'landscape') {
      // four doors, two to a row; the guide and the app's door under them
      await settle(page);
      await shot(page, 'hub-landscape');
      const doors = await page.evaluate(() => [...document.querySelectorAll('.m-doors a.m-door')]
        .map(d => { const r = d.getBoundingClientRect(); return [Math.round(r.top), Math.round(r.left)]; }));
      assert(doors.length === 4 && doors[0][0] === doors[1][0] && doors[2][0] === doors[3][0] &&
             doors[2][0] > doors[0][0] && doors[1][1] > doors[0][1],
             'sideways: the hub\'s doors two to a row ' + JSON.stringify(doors));
      assert(await sideways(page) <= 0, 'and the hub does not scroll sideways');
    }
    await Promise.all([page.waitForURL(B + '/m/books/'), tap(page, '.hub-mobile a.m-door[href="/books/"]')]);
    assert(true, 'the mobile hub: Books opens the mobile shelf, /m/books/');
    if (tag === 'desktop') {
      await page.goto(B + '/');
      const [tab] = await Promise.all([page.context().waitForEvent('page'),
        page.locator('.hub-mobile a.m-door[href="/books/"]').click({modifiers: ['Control']})]);
      await tab.waitForLoadState();
      eq(new URL(tab.url()).pathname, '/m/books/', 'and a ctrl-click opens it in a new tab');
      await tab.close();
      await page.goto(B + '/m/books/');
    }
    await settle(page);
    await shot(page, `shelf-${tag}`);

    // ---- b) what can be tapped
    const got = await clickable(page, 'body');
    // the chips and the books in the registry's order (fa ar it ja fr de tr
    // en hi es zh), a language only where it has a book
    const want = ['a:/', 'button:browser', 'button:mobile', 'button:theme', 'button:all',
                  'button:fa', 'button:ar', 'button:it', 'button:ja', 'button:en', 'button:hi', 'button:zh',
                  'a:/books/persian/mini-fa/reader/', 'a:/books/arabic/mini-ar/reader/',
                  'a:/books/japanese/mini-ja/reader/', 'a:/books/english/mini-en/reader/',
                  'a:/books/hindi/mini-hi/reader/', 'a:/books/chinese/mini-zh/reader/'];
    // (the chips row scrolls on a phone and wraps for a mouse: either way
    // every chip is drawn)
    eq(got, want, 'all there is to tap: home, the switch, the theme, the chips, one card per built book');
    for (const no of ['[data-del]', '[data-build]', '[data-parseh-stop]', 'input[type=file]', '#take', '#shelf'])
      assert(!(await page.$(no)), 'nothing on the shelf is ' + no);
    const cards = await targets(page, 'a.m-book');
    allFit(cards, 'each card at least 48px (' + cards.map(c => c.h).join(', ') + '), inside the screen, reached by a tap');
    assert(cards.every(c => c.h >= 96), 'and as tall as the hub\'s doors');
    if (tag === 'landscape' || tag === 'desktop') {
      // one book to a language here: two to a row is two cards' width a row
      const col = await page.evaluate(() => {
        const s = document.querySelector('.m-shelf').getBoundingClientRect();
        const c = document.querySelector('a.m-book').getBoundingClientRect();
        return [Math.round(s.width), Math.round(c.width)];
      });
      assert(col[1] < col[0] * 0.55, 'from 600px the books go two to a row ' + JSON.stringify(col));
    }
    await page.evaluate(() => scrollTo(0, 0));
    await sleep(250);
    allFit(await targets(page, '.m-bar a, .m-bar button'), 'the bar\'s controls: 48px, on the screen');
    const barTops = await page.evaluate(() => [...document.querySelectorAll('.m-bar a, .m-bar button')]
      .filter(e => e.getClientRects().length).map(e => Math.round(e.getBoundingClientRect().top)));
    assert(Math.max(...barTops) - Math.min(...barTops) <= 6, 'and one line of them ' + JSON.stringify(barTops));
    assert(await sideways(page) <= 0, 'the page does not scroll sideways');
    const off = await page.evaluate(() => {
      const c = document.querySelector('.m-book.m-off');
      return c && {tag: c.tagName, href: c.getAttribute('href'), said: c.textContent.replace(/\s+/g, ' '),
                   inLink: !!c.closest('a')};
    });
    assert(off && off.tag === 'DIV' && !off.href && !off.inLink && /not built yet/.test(off.said) &&
           /browser interface/.test(off.said), 'the book never built says so, and opens nothing');
    // the titles in their own direction and face
    const fa = await page.evaluate(() => {
      const t = document.querySelector('a.m-book[data-lang=fa] .m-btitle');
      return {dir: getComputedStyle(t).direction, lang: t.getAttribute('lang')};
    });
    eq(fa, {dir: 'rtl', lang: 'fa'}, 'a Persian title reads right to left');

    // ---- c) a chip
    await page.evaluate(() => scrollTo(0, 0));
    await sleep(250);
    await page.locator('.m-langs .chip[data-pick=ja]').scrollIntoViewIfNeeded();
    await tap(page, '.m-langs .chip[data-pick=ja]');
    const shown = await page.evaluate(() => [...document.querySelectorAll('.m-book, .m-lhead')]
      .filter(e => e.getClientRects().length).map(e => e.className.split(' ')[0] + ':' + e.getAttribute('data-lang')));
    eq(shown, ['m-lhead:ja', 'm-book:ja'], 'Japanese picked: its heading and its one book, nothing else');
    await tap(page, '.m-langs .chip[data-pick=all]');

    // ---- d) read on
    if (tag === 'phone') {
      const en = MADE.readers.en;
      await page.evaluate(p => localStorage.setItem('bk_pos:' + p + 'index.html', JSON.stringify({i: 2})), en);
      await page.reload();
      const card = await page.evaluate(p => {
        const a = [...document.querySelectorAll('a.m-book')].find(x => x.getAttribute('data-lang') === 'en');
        const t = a.querySelector('.m-readon');
        return {tag: t && t.textContent, href: a.getAttribute('href'), bar: getComputedStyle(a, '::after').width,
                subs: +a.getAttribute('data-subs')};
      }, en);
      const pct = Math.round(3 * 100 / card.subs);
      eq([card.tag, card.href], [`read on · ${pct}%`, en + 'index.html'],
         'a book read here says how far, and opens where the place was kept');
      assert(parseFloat(card.bar) > 0, 'with a line along its foot: ' + card.bar);
      await page.evaluate(p => localStorage.removeItem('bk_pos:' + p + 'index.html'), en);
      await page.reload();
    }

    // ---- e) Browser
    await reveal(page);
    await Promise.all([page.waitForURL(B + '/books/'), tap(page, '.m-bar [data-parseh-mode=browser]')]);
    assert(true, 'Browser pressed on the shelf: the library, /books/');
    await page.goto(B + '/m/books/');
    assert(await isDrawn(page, '.m-elsewhere'), 'opened in the browser mode, the shelf says it is the mobile one');
    eq(await page.evaluate(() => location.pathname), '/m/books/', 'and stays: nothing redirects at load');
    await setMode(page, 'mobile');
    await page.reload();
    assert(!(await isDrawn(page, '.m-elsewhere')), 'in the mobile mode it does not');
    await page.context().close();
  }
}

// ======== reader ========
const HEADER_SEL = 'header a[href], header button, header select, header input, header label[for]';
// the header's drawn controls, in the order they are SEEN -- line by line,
// then left to right -- which is not the order of the markup: the mobile
// layout places them with `order`
const headerDrawn = page => page.evaluate(sel => [...document.querySelectorAll(sel)]
  .filter(e => e.getClientRects().length > 0)
  .map(e => ({r: e.getBoundingClientRect(), name: e.id || (e.classList.contains('home')
    ? (e.classList.contains('glyph') ? 'hub' : 'shelf')
    : e.getAttribute('data-toggle') || e.getAttribute('data-parseh-mode') || e.className)}))
  .sort((a, b) => (Math.abs(a.r.top - b.r.top) > 6 ? a.r.top - b.r.top : a.r.left - b.r.left))
  .map(x => x.name), HEADER_SEL);
const WRITES = ['#bookinfo', '#buildbook', '#buildhtml', '#narr', '#fold', '#editmode', '#savetimes', '#droptimes',
                '#stopsrv', 'header .dl', '#lookupset', '#build', '#pdfstale', '#chpen', '.gap .plus', '#editmsg'];

// what the first line holds, and on a narrated book the recording's line
function firstLines(code, tag) {
  const still = ['hub', 'shelf', 'toc', 'typo', 'm-rmore'];
  if (code !== 'en') return [still];
  // upright the recording is a line of its own; sideways all of it is one
  return tag === 'landscape' ? [['hub', 'shelf', 'm-skip', 'play', 'm-skip', 'toc', 'typo', 'm-rmore']]
                             : [still, ['m-skip', 'play', 'm-skip']];
}

async function partReader() {
  for (const [opts, tag] of [[PHONE, 'phone'], [NARROW, 'narrow'], [LAND, 'landscape']]) {
    const page = await newPage(opts, 'reader ' + tag);
    await page.goto(B + '/');
    await setMode(page, 'mobile');
    for (const code of ['en', 'fa', 'ar', 'ja', 'hi', 'zh']) {
      console.log(`\n== reader ${code}, ${tag}`);
      const lines = firstLines(code, tag), want = lines.flat();
      // ---- a) from the shelf
      await page.goto(B + '/m/books/');
      await Promise.all([page.waitForURL(B + MADE.readers[code]),
                         tap(page, `a.m-book[data-lang=${code}]`)]);
      await page.waitForFunction(() => document.querySelector('.m-rmore'));
      await settle(page);
      await reveal(page);
      await shot(page, `reader-${code}-${tag}`);
      eq(await headerDrawn(page), want, `${code}: the header: ${lines.map(l => l.join(', ')).join(' / ')}`);
      const line = await targets(page, 'header a[href], header button');
      allFit(line, `${code}: each at least 48px, on the screen, reached by a tap`);
      const rows = [...new Set(line.map(t => t.top))].sort((a, b) => a - b);
      const grouped = rows.reduce((g, t) => (g.length && t - g[g.length - 1] <= 6 ? g : [...g, t]), []);
      eq(grouped.length, lines.length, `${code}: ${lines.length === 1 ? 'all on one line' : 'on two lines'} ` +
         JSON.stringify(line.map(t => t.top)));
      for (const w of WRITES) assert(!(await isDrawn(page, w)), `${code}: no ${w}`);
      assert(await sideways(page) <= 0, `${code}: the page does not scroll sideways`);
      eq(await page.evaluate(() => document.body.hasAttribute('data-mobile-page')), true, `${code}: a mobile page`);
      if (code === 'fa' || code === 'ar')
        eq(await page.evaluate(() => getComputedStyle(document.querySelector('main .p1')).direction), 'rtl',
           `${code}: the text reads right to left, under a header that reads left to right`);
      if (code !== 'en')
        assert(!(await isDrawn(page, '.m-skip, .m-rskip')), `${code}: no narration, no ↺ ↻`);

      // ---- b) ⋯
      await tap(page, '.m-rmore');
      await settle(page);
      await shot(page, `reader-${code}-${tag}-more`);
      const labs = await page.evaluate(() => [...document.querySelectorAll('.m-rlab')]
        .filter(e => e.getClientRects().length).map(e => e.getAttribute('data-g')));
      eq(labs, code === 'en' ? ['passes', 'listening', 'page'] : ['passes', 'page'],
         `${code}: ⋯ opens the groups this book has`);
      eq(await page.evaluate(() => document.querySelector('.m-rmore').getAttribute('aria-expanded')), 'true',
         `${code}: and says it is open`);
      if (tag === 'landscape')
        assert(await page.evaluate(() => document.querySelector('header').getBoundingClientRect().height <= innerHeight + 0.5),
               `${code}: sideways, open, the header is never taller than the screen`);
      allFit(await targets(page, 'header button, header select, header input'), `${code}: every control under ⋯ at least 48px`);
      for (const w of WRITES) assert(!(await isDrawn(page, w)), `${code}: still no ${w}`);
      eq(await page.evaluate(() => [...document.querySelectorAll('header [data-parseh-mode]')]
        .filter(b => b.getClientRects().length).map(b => b.getAttribute('aria-pressed'))), ['false', 'true'],
         `${code}: the switch is there, Mobile pressed`);
      // a pass still hides its pass
      const pass = await page.evaluate(() => {
        const b = document.querySelector('.pgrp [data-toggle]');
        return b && b.getAttribute('data-toggle');
      });
      const passCls = pass.replace('no', '.p');
      assert(await isDrawn(page, 'main ' + passCls), `${code}: pass ${passCls} drawn`);
      await tap(page, `.pgrp [data-toggle=${pass}]`);
      assert(!(await isDrawn(page, 'main ' + passCls)), `${code}: its button hides it`);
      await tap(page, `.pgrp [data-toggle=${pass}]`);
      assert(await isDrawn(page, 'main ' + passCls), `${code}: and brings it back`);
      if (code === 'en') {
        const t0 = await page.evaluate(() => Parseh.theme.resolved());
        await tap(page, '#theme');
        const t1 = await page.evaluate(() => Parseh.theme.resolved());
        assert(t0 !== t1, `en: the theme turns (${t0} -> ${t1})`);
        await page.evaluate(t => Parseh.theme.set(t), t0);
      }
      await page.evaluate(() => document.querySelector('header').scrollTop = 0);
      await tap(page, '.m-rmore');
      eq(await headerDrawn(page), want, `${code}: ⋯ again: the first line alone`);

      // ---- g) the recording, back and on
      if (code === 'en') await partSkip(page, tag);

      // ---- c) the contents, and the cloud
      await reveal(page);
      await tap(page, '#toc');
      await page.waitForFunction(() => !document.querySelector('#tocwrap').hidden);
      assert(await isDrawn(page, '#toclist a[href^="#par-"]'), `${code}: the contents opens, its entries there`);
      assert(!(await isDrawn(page, '.tocedit')) && !(await isDrawn(page, '#tocsecs')),
             `${code}: without the naming of chapters and sections`);
      await tap(page, '#tocx');
      await reveal(page);
      await tap(page, '.m-rmore');
      await tap(page, '#hovermode');
      await tap(page, '.m-rmore');
      await tap(page, 'main .p1 .w');
      await page.waitForFunction(() => !document.querySelector('#cloud').hidden);
      assert(await isDrawn(page, '#cloud .mkcopy'), `${code}: a tap opens the gloss cloud, with copy`);
      assert(!(await isDrawn(page, '#cloud .mkcard')) && !(await isDrawn(page, '#cloud .mkedit')),
             `${code}: and no card, no edit`);
      await page.evaluate(() => { localStorage.setItem('bk_hover', '0'); });

      // ---- e) the shelf's ▤ goes to the mobile shelf
      if (code === 'zh') {
        await page.reload();
        await page.waitForFunction(() => document.querySelector('.m-rmore'));
        await reveal(page);
        await Promise.all([page.waitForURL(B + '/m/books/'), tap(page, 'header a.home:not(.glyph)')]);
        assert(true, 'zh: ▤ goes to the mobile shelf');
      }
    }
    await page.context().close();
  }

  // ---- d) the writing gestures, on a desktop, in both modes
  console.log('\n== reader, desktop: the gestures that write');
  const page = await newPage(DESK, 'reader desktop');
  await page.goto(B + '/');
  await setMode(page, 'browser');
  const en = B + MADE.readers.en;
  await page.goto(en);
  await page.waitForFunction(() => window.ParsehMobileReader);
  const before = await headerDrawn(page);
  assert(before.includes('bookinfo') && before.includes('buildbook') && before.includes('narr'),
         'the browser mode: the header as the reader builds it ' + JSON.stringify(before));
  assert(!(await isDrawn(page, '.m-rmore, .m-rlab, .m-skip, .m-rskip')), 'with nothing of the mobile layer drawn');
  const word = 'main .p1 .wd';
  const card = async () => {
    await page.locator(word).first().click({modifiers: ['Alt']});
    await sleep(300);
    return page.evaluate(() => !document.querySelector('#anki').hidden);
  };
  const edit = async () => {
    await page.locator('main .p2 .row[data-c]').first().hover();
    await sleep(200);
    await page.keyboard.press('e');
    await sleep(300);
    return page.evaluate(() => !document.querySelector('#chbox').hidden);
  };
  assert(await card(), 'browser: alt-click on a word opens the card sheet');
  await page.locator('#acancel').click();
  assert(await edit(), 'browser: E over a chunk opens its editor');
  await page.keyboard.press('Escape');
  await page.waitForFunction(() => document.querySelector('#chbox').hidden);
  // Mobile, pressed in another tab: this one follows
  const other = await page.context().newPage();
  await other.goto(B + '/');
  await other.locator('.parseh-bar:not(.m-bar) [data-parseh-mode=mobile]').click();
  await page.waitForFunction(() => document.documentElement.getAttribute('data-mode') === 'mobile');
  await other.close();
  assert(await isDrawn(page, '.m-rmore'), 'a switch made in another tab: the reader follows, ⋯ there');
  assert(!(await card()), 'mobile: alt-click on the same word opens nothing');
  assert(!(await edit()), 'mobile: E over the same chunk opens nothing');
  // ---- e) play
  await reveal(page);
  await page.locator('#play').click();
  await page.waitForFunction(() => !document.querySelector('#audio').paused, null, {timeout: 5000});
  eq(await page.evaluate(() => document.querySelector('#play').textContent), '‖', 'play plays, and says so');
  await page.locator('#play').click();
  // ---- f) back to the browser mode
  await reveal(page);
  await page.locator('.m-rmore').click();
  await page.locator('header [data-parseh-mode=browser]').click();
  eq(await page.evaluate(() => document.documentElement.getAttribute('data-mode')), 'browser', 'Browser pressed in the reader');
  eq(await headerDrawn(page), before, 'the header is the browser\'s again, control for control');
  eq(await page.evaluate(() => document.body.hasAttribute('data-bars-held')), false,
     'and nothing holds its bars any more');
  assert(await card(), 'and alt-click makes a card again');
  await page.locator('#acancel').click();
  await page.context().close();
}

// ---- g) ↺ and ↻, on the narrated book (its recording is 8 seconds long)
async function partSkip(page, tag) {
  const K = 'bk_skip';
  const state = () => page.evaluate(() => ({t: Math.round(document.getElementById('audio').currentTime * 100) / 100,
    paused: document.getElementById('audio').paused, cur,
    on: (document.querySelector('.on-air') || {dataset: {}}).dataset.s,
    labels: [...document.querySelectorAll('.m-skip')].map(b => b.textContent + '|' + b.getAttribute('aria-label'))}));
  eq((await state()).labels, ['↺ 10|back 10 seconds', '10 ↻|on 10 seconds'],
     'en: ↺ and ↻ say ten seconds, until told otherwise');
  // two seconds a press, set in the field under ⋯ as a person sets it
  await tap(page, '.m-rmore');
  const field = page.locator('#m-skipby');
  await field.scrollIntoViewIfNeeded();
  await field.fill('2');
  await field.press('Enter');
  await page.evaluate(() => document.querySelector('header').scrollTop = 0);
  await tap(page, '.m-rmore');
  eq([await page.evaluate(k => localStorage.getItem(k), K), (await state()).labels],
     ['2', ['↺ 2|back 2 seconds', '2 ↻|on 2 seconds']], 'en: the field set to 2: kept, and said on both');
  await page.waitForFunction(() => document.getElementById('audio').readyState >= 1);
  const s0 = await state();
  eq([s0.t, s0.cur], [0, -1], 'en: at the start, nothing read yet');
  await tap(page, '.m-skip[data-skip="1"]');
  await sleep(400);
  const s1 = await state();
  // the first subparagraph is 0.8 to 3.9 seconds: two seconds in is in it
  eq([s1.t, s1.paused, s1.cur, s1.on], [2, true, 0, '0'],
     'en: ↻ paused: two seconds on, and the reading place is the subparagraph that is said there');
  eq(await page.evaluate(() => document.body.hasAttribute('data-bars-held')), true,
     'en: the header held where it is while that settles');
  await tap(page, '.m-skip[data-skip="-1"]');
  await sleep(400);
  eq((await state()).t, 0, 'en: ↺: back to the start');
  // nonsense in the field keeps the number it had; too much is the most
  await tap(page, '.m-rmore');
  for (const [typed, kept] of [['', '2'], ['0', '2'], ['99999', '600'], ['3', '3']]) {
    await field.fill(typed);
    await field.press('Enter');
    eq([await field.inputValue(), await page.evaluate(k => localStorage.getItem(k), K)], [kept, kept],
       `en: "${typed}" typed: ${kept}`);
  }
  await page.evaluate(() => document.querySelector('header').scrollTop = 0);
  await tap(page, '.m-rmore');
  // every book, and the next time: the number is the browser's
  await page.reload();
  await page.waitForFunction(() => document.querySelector('.m-skip'));
  await reveal(page);
  eq((await state()).labels, ['↺ 3|back 3 seconds', '3 ↻|on 3 seconds'], 'en: opened again, still 3');
  if (tag === 'landscape') {
    // sideways: the header goes on the way down, comes back on the way up,
    // and stays while ⋯ is open
    const hidden = () => page.evaluate(() => document.body.classList.contains('barhidden'));
    await page.evaluate(() => scrollTo(0, 0));
    await sleep(300);
    await page.evaluate(() => scrollBy(0, 240));
    await page.waitForFunction(() => document.body.classList.contains('barhidden'));
    await sleep(300);
    assert((await rect(page, 'header')).b <= 1, 'en, sideways: scrolled down, the header is away');
    await page.evaluate(() => scrollBy(0, -20));
    await page.waitForFunction(() => !document.body.classList.contains('barhidden'));
    await sleep(300);
    assert(near((await rect(page, 'header')).t, 0), 'en, sideways: a move up brings it back');
    await tap(page, '.m-rmore');
    await page.evaluate(() => scrollBy(0, 200));
    await sleep(400);
    assert(!(await hidden()), 'en, sideways: with ⋯ open the header stays');
    await tap(page, '.m-rmore');
    await page.evaluate(() => scrollTo(0, 0));
    await sleep(300);
  }
  // the place and the number, as they were: the next pages start clean
  await page.evaluate(k => { localStorage.removeItem(k);
    Object.keys(localStorage).filter(x => x.startsWith('bk_pos:')).forEach(x => localStorage.removeItem(x)); }, K);
  await page.reload();
  await page.waitForFunction(() => document.querySelector('.m-rmore'));
  await reveal(page);
}

// ======== decks ========
async function partDecks() {
  const EN = MADE.decks.en, IT = MADE.decks.it;
  for (const [opts, tag] of [[PHONE, 'phone'], [NARROW, 'narrow'], [LAND, 'landscape'], [DESK, 'desktop']]) {
    console.log(`\n== decks, ${tag}`);
    // sideways and on a desktop the answer is a column at the right
    const rail = tag === 'landscape' || tag === 'desktop';
    const page = await newPage(opts, 'decks ' + tag);
    await page.goto(B + '/');
    await setMode(page, 'mobile');
    await page.reload();
    // ---- a) the decks
    await Promise.all([page.waitForURL(B + '/exercises/'), tap(page, '.hub-mobile a.m-door[href="/exercises/"]')]);
    await page.waitForFunction(() => document.querySelectorAll('.dk-card').length === 3);
    await settle(page);
    await shot(page, `decks-${tag}`);
    assert(await isDrawn(page, '.m-topbar') && !(await isDrawn(page, 'header.topbar')),
           'the decks\' mobile layout is the one drawn, the browser bar display:none');
    eq(await page.evaluate(() => getComputedStyle(document.querySelector('header.topbar')).display), 'none',
       'the browser bar is display:none');
    const got = await clickable(page, 'body');
    const deckLinks = ['english/everyday-english', 'italian/nothing-yet', 'persian/persian-words']
      .flatMap(p => [`a:/exercises/deck/${p}/`, `a:/exercises/deck/${p}/study`, `a:/exercises/deck/${p}/`]);
    eq(got.filter(x => !/^a:\/exercises\/deck\//.test(x)),
       ['a:/', 'button:browser', 'button:mobile', 'button:theme', 'button:all', 'button:fa', 'button:it', 'button:en'],
       'the bar and the chips: home, the switch, the theme, one chip a language');
    eq(got.filter(x => /^a:\/exercises\/deck\//.test(x)).sort(), deckLinks.sort(),
       'and each deck its name, Study and Open');
    eq(await page.evaluate(() => {
      const a = document.querySelector('.dk-card[data-lang=it] [data-x=study]');
      return [a.classList.contains('dk-off'), a.getAttribute('aria-disabled')];
    }), [true, 'true'], 'an empty deck has nothing to study: its Study is off');
    for (const no of ['#btn-import', '#btn-restore', '#btn-new-deck', '#btn-stop', 'a[href$="/api/backup"]',
                      '.dk-card summary', '[data-x=delete]', '.dk-card .dropdown'])
      assert(!(await isDrawn(page, no)), 'no ' + no);
    allFit(await targets(page, '.m-topbar a, .m-topbar button'), 'the bar: 48px, on the screen');
    allFit(await targets(page, '.dk-card h3 a, .dk-card-actions a:not(.dk-off), .parseh-langs .chip'),
           'the names, the Study and Open buttons and the chips: 48px, on the screen, reached by a tap');
    assert(await sideways(page) <= 0, 'the page does not scroll sideways');
    if (rail) {
      const cols = await page.evaluate(() => [...document.querySelectorAll('.dk-card')]
        .map(c => Math.round(c.getBoundingClientRect().top)));
      assert(cols[0] === cols[1], 'from 600px the decks go two to a row ' + JSON.stringify(cols));
    }

    // ---- b) a chip, and the theme
    await page.evaluate(() => scrollTo(0, 0));
    await sleep(250);
    await tap(page, '.parseh-langs .chip[data-pick=fa]');
    eq(await page.evaluate(() => [...document.querySelectorAll('.dk-card')].filter(c => !c.hidden)
      .map(c => c.dataset.lang)), ['fa'], 'Persian picked: the Persian deck alone');
    await tap(page, '.parseh-langs .chip[data-pick=all]');
    if (tag === 'phone') {
      const t0 = await page.evaluate(() => document.body.dataset.theme || 'paper');
      await tap(page, '.m-topbar [data-parseh-theme]');
      const t1 = await page.evaluate(() => [document.body.dataset.theme || 'paper', localStorage.getItem('parseh_theme'),
                                            document.querySelector('.m-topbar [data-parseh-theme]').textContent]);
      assert(t1[0] !== t0 && t1[1] === (t1[0] === 'paper' ? 'light' : t1[0]),
             `the theme button turns the page (${t0} -> ${t1[0]}) and says so for the whole toolbox (${t1[1]}, ${t1[2]})`);
      await shot(page, `decks-${tag}-${t1[0]}`);
      await page.evaluate(() => localStorage.setItem('parseh_theme', 'light'));
    }

    // ---- c) a deck
    await Promise.all([page.waitForURL(B + `/exercises/deck/${IT.folder}/${IT.slug}/`),
                       tap(page, `.dk-card[data-lang=it] [data-x=browse]`)]);
    await page.waitForFunction(() => !document.querySelector('#deck-mobile-note').hidden);
    eq(await page.evaluate(() => document.querySelector('#deck-mobile-note').textContent),
       'This deck has no exercises yet: they are added in the browser interface.', 'an empty deck says where exercises are added');
    assert(!(await isDrawn(page, '.dk-browse')), 'and has no list to pick from');
    await page.goto(B + `/exercises/deck/${EN.folder}/${EN.slug}/`);
    await page.waitForFunction(() => !document.querySelector('#btn-practise').disabled &&
                                     document.querySelectorAll('#browse-list .dk-row').length === 5);
    await settle(page);
    await shot(page, `deck-${tag}`);
    for (const no of ['#btn-rename', '#btn-add-exercise', '.dk-deckactions summary', '#btn-options',
                      '#btn-delete-deck', '#btn-stop', '#btn-bulk-copy', '#btn-bulk-move', '#btn-bulk-add-tag',
                      '#btn-bulk-remove-tag', '#btn-bulk-new', '#btn-bulk-delete', '#btn-cram', '.dk-row-actions',
                      '.dk-selection-hint', '#m-cram'])
      assert(!(await isDrawn(page, no)), 'the deck: no ' + no);
    eq(await page.locator('#btn-practise').textContent(), 'Cram all', 'the deck: Study now, and Cram all');
    allFit(await targets(page, '#btn-study, #btn-practise, #browse-filter, #browse-type, #browse-state, ' +
                               '#browse-tag, .dk-bulkbar .btn, .dk-row .dk-select'),
           'Study now, Cram all, the filters, the five ways to pick, each exercise\'s box: 48px, on the screen');
    assert(/5 exercises/.test(await page.locator('#deck-counts').textContent()), 'its counts');
    assert(await sideways(page) <= 0, 'the deck does not scroll sideways');

    if (tag !== 'narrow') {
      // ---- e) two picked by hand, crammed
      const before = await (await fetch(B + `/exercises/api/decks/${EN.folder}/${EN.slug}`)).json();
      await tapMiddle(page, '.dk-row:nth-child(2) .dk-select');
      await tapMiddle(page, '.dk-row:nth-child(4) .dk-select');
      eq(await page.locator('#browse-selected').textContent(), '2 selected', 'two boxes tapped: two picked');
      const go = await rect(page, '#m-cram');
      eq(await page.locator('#m-cram').textContent(), 'Cram 2 exercises', 'and Cram says so');
      assert(go && go.h >= 48 && go.b <= await page.evaluate(() => innerHeight) && go.l >= 0 &&
             go.r <= await page.evaluate(() => innerWidth), 'at the foot of the screen, over the list ' + JSON.stringify(go));
      await shot(page, `deck-${tag}-picked`);
      await Promise.all([page.waitForURL(/\/cram$/), tap(page, '#m-cram')]);
      await page.waitForFunction(() => /of 2/.test(document.querySelector('#cram-progress').textContent));
      eq(await page.locator('#cram-progress').textContent(), '1 of 2', 'crammed: the two picked');
      await cramAnswerBar(page, tag, rail);
      // ---- and the ones a tag picks
      await page.goto(B + `/exercises/deck/${EN.folder}/${EN.slug}/`);
      await page.waitForFunction(() => document.querySelectorAll('#browse-list .dk-row').length === 5);
      await tap(page, '#btn-deselect-all');
      await tap(page, '#btn-select-tag');
      await page.waitForSelector('.modal.dk-modal select');
      allFit(await targets(page, '.modal.dk-modal select, .modal.dk-modal .row .btn'),
             'Select by tag: its list and its two buttons, 48px');
      await page.locator('.modal.dk-modal select').selectOption('grammar');
      await tap(page, '.modal.dk-modal .row .btn.primary');
      await page.waitForFunction(() => !document.querySelector('.modal-overlay'));
      eq(await page.locator('#browse-selected').textContent(), '2 selected', 'grammar: the two exercises tagged so');
      await Promise.all([page.waitForURL(/\/cram$/), tap(page, '#m-cram')]);
      await page.waitForFunction(() => /of 2/.test(document.querySelector('#cram-progress').textContent));
      const crammed = await page.locator('#cram-stage').textContent();
      assert(/Which article|past of/.test(crammed), 'crammed: one of the grammar ones first: ' +
             crammed.replace(/\s+/g, ' ').trim().slice(0, 50));
      const after = await (await fetch(B + `/exercises/api/decks/${EN.folder}/${EN.slug}`)).json();
      eq(after.items.map(it => JSON.stringify(it.schedule)), before.items.map(it => JSON.stringify(it.schedule)),
         'cramming leaves the scheduling as it was');
    }

    if (tag !== 'narrow') {
      // ---- d) studying, every exercise new again (the deck's own Set to new,
      // asked of its API: this viewport's session starts where the last one did)
      const all = (await (await fetch(B + `/exercises/api/decks/${EN.folder}/${EN.slug}`)).json()).items.map(it => it.id);
      const reset = await fetch(B + `/exercises/api/decks/${EN.folder}/${EN.slug}/items/bulk`, {method: 'POST',
        headers: {'Content-Type': 'application/json'}, body: JSON.stringify({action: 'set-new', ids: all})});
      await reset.body?.cancel();
      assert(reset.ok, 'the deck new again, to study');
      await page.goto(B + `/exercises/deck/${EN.folder}/${EN.slug}/`);
      await page.waitForFunction(() => !document.querySelector('#btn-practise').disabled);
      await page.evaluate(() => scrollTo(0, 0));
      await Promise.all([page.waitForURL(/\/study$/), tap(page, '#btn-study')]);
      await page.waitForFunction(() => !document.querySelector('#btn-show').hidden || !document.querySelector('#btn-check').hidden);
      for (const no of ['#btn-edit-card', '.dk-keys', '#btn-stop', '.m-topbar', 'header.topbar'])
        assert(!(await isDrawn(page, no)), 'studying: no ' + no);
      allFit(await targets(page, '.dk-studyhead .m-back'), 'studying: ‹ back to the deck, 48px');
      eq(await page.evaluate(() => new URL(document.querySelector('.dk-studyhead .m-back').href).pathname),
         `/exercises/deck/${EN.folder}/${EN.slug}/`, 'and it goes to the deck');
      const done = new Set();
      for (let round = 0; round < 5; round++) {
        const card = await page.evaluate(() => ({
          flash: !document.querySelector('#btn-show').hidden, scored: !document.querySelector('#btn-check').hidden,
          text: document.querySelector('#study-stage').textContent.replace(/\s+/g, ' ').trim().slice(0, 60)}));
        const primary = card.flash ? '#btn-show' : card.scored ? '#btn-check' : null;
        if (!primary) break;
        const box = await rect(page, '.dk-answerbar');
        const [W, H] = await page.evaluate(() => [innerWidth, innerHeight]);
        if (rail)
          assert(near(box.r, W) && near(box.t, 0) && near(box.b, H) && box.w <= 220,
                 'sideways: what to do is a column down the right edge ' + JSON.stringify(box));
        else
          assert(near(box.b, H) && near(box.l, 0) && near(box.r, W),
                 'upright: what to do is a bar at the foot of the screen ' + JSON.stringify(box));
        if (rail) {
          const stage = await rect(page, '#study-stage');
          assert(stage.r <= box.l + 0.5, 'and the exercise beside it, not under it');
        }
        allFit(await targets(page, `${primary}, #btn-skip`), `${card.flash ? 'a flashcard: Show answer' : 'Check'} and Skip, 48px`);
        const at = await rect(page, primary);
        if (card.scored && /Which article/.test(card.text)) {
          allFit(await targets(page, '#study-stage .ex-option'), 'its answers: 48px, reached by a tap');
          const right = page.locator('#study-stage .ex-option').filter({hasText: /^\s*an\s*$/});
          if (page.touch) await right.tap(); else await right.click();
        }
        const filled = card.scored && /Complete the sentence/.test(card.text);
        const matched = card.scored && /Match each British word/.test(card.text);
        if (filled) await fillByCloud(page, tag);
        if (matched) await matchByCloud(page, tag);
        await tap(page, primary);
        if (card.scored && /Which article/.test(card.text))
          eq(await page.locator('#study-result').textContent(), 'Correct', 'the choice answered right: Correct');
        if (filled)
          eq(await page.locator('#study-result').textContent(), 'Correct', 'the blanks filled from their clouds: Correct');
        if (matched)
          eq(await page.locator('#study-result').textContent(), 'Correct', 'the matches made from their clouds: Correct');
        await page.waitForFunction(() => !document.querySelector('#rating-bar').hidden &&
                                         !document.querySelector('#btn-next').hidden);
        await sleep(200);
        // Next where the answer's button was, saying what it does
        const nx = await rect(page, '#btn-next');
        assert(near(nx.l, at.l) && near(nx.r, at.r) && near(nx.b, at.b, 4),
               'Next, in the very place of ' + primary + ' ' + JSON.stringify([at, nx]));
        const says = await page.evaluate(() => {
          const n = document.querySelector('#btn-next'), r = n.dataset.rating;
          return [n.querySelector('.dk-word').textContent, n.querySelector('.dk-ivl').textContent, r,
                  document.querySelector('#rating-bar [data-rating=' + r + '] .dk-ivl').textContent];
        });
        eq(says.slice(0, 2), ['Next', `${says[2][0].toUpperCase() + says[2].slice(1)} · ${says[3]}`],
           'Next says the rating it gives, and when the exercise comes back');
        if (card.flash || /Which article/.test(card.text)) eq(says[2], 'good', 'right, or a card turned: Good');
        allFit(await targets(page, '#rating-bar .dk-rate, #btn-next'), 'the four ratings and Next: 48px, on the screen, reached by a tap');
        const rt = await tops(page, '#rating-bar .dk-rate');
        if (rail)
          assert(rt.length === 4 && rt[0] === rt[1] && rt[2] === rt[3] && rt[2] > rt[0],
                 'sideways: the ratings two by two ' + JSON.stringify(rt));
        else
          assert(rt.length === 4 && new Set(rt).size === 1, 'upright: the ratings on one line ' + JSON.stringify(rt));
        assert((await page.evaluate(() => [...document.querySelectorAll('#rating-bar .dk-ivl')].map(i => i.textContent)))
          .every(Boolean), 'each saying when the exercise comes back');
        if (round === 0) await shot(page, `study-${tag}`);
        // Good from the ratings once, Next the rest of the time
        await tap(page, round === 0 ? '#rating-bar [data-rating=good]' : '#btn-next');
        await page.waitForFunction(() => document.querySelector('#rating-bar').hidden);
        done.add(card.text);
      }
      const deck = await (await fetch(B + `/exercises/api/decks/${EN.folder}/${EN.slug}`)).json();
      const studied = deck.items.filter(it => (it.schedule || {}).state && it.schedule.state !== 'new').length;
      assert(studied >= 2, `rated by Good and by Next, the exercises are scheduled in the deck itself: ${studied} of ${deck.items.length}`);

      // ---- e) Cram all
      await page.goto(B + `/exercises/deck/${EN.folder}/${EN.slug}/`);
      await page.waitForFunction(() => !document.querySelector('#btn-practise').disabled);
      await Promise.all([page.waitForURL(/\/cram$/), tap(page, '#btn-practise')]);
      await page.waitForFunction(() => /of 5/.test(document.querySelector('#cram-progress').textContent));
      eq(await page.locator('#cram-progress').textContent(), '1 of 5', 'Cram all: every exercise of the deck, crammed');
      assert(await isDrawn(page, '.dk-cram-note[data-layout=mobile]') &&
             !(await isDrawn(page, '.dk-cram-note[data-layout=browser]')), 'said in the mobile layout\'s words');
      const after = await (await fetch(B + `/exercises/api/decks/${EN.folder}/${EN.slug}`)).json();
      eq(after.items.map(it => JSON.stringify(it.schedule)), deck.items.map(it => JSON.stringify(it.schedule)),
         'and the scheduling as it was');
    }

    // ---- f) Browser
    await page.goto(B + `/exercises/deck/${EN.folder}/${EN.slug}/`);
    // the list arrives after the page: its rows (and their actions, hidden in
    // the mobile layout) must be there before asking whether they are drawn
    await page.waitForFunction(() => document.querySelector('.dk-row-actions'));
    await tap(page, '.m-topbar [data-parseh-mode=browser]');
    eq(await page.evaluate(() => [document.documentElement.getAttribute('data-mode'), localStorage.getItem('parseh_mode'),
                                  document.cookie.includes('parseh_mode=browser')]),
       ['browser', 'browser', true], 'Browser pressed on a deck: stored, mirrored, applied');
    for (const yes of ['header.topbar', '#btn-rename', '#btn-add-exercise', '#btn-options', '#btn-delete-deck',
                       '.dk-browse', '#btn-bulk-delete', '#btn-cram', '.dk-row-actions'])
      assert(await isDrawn(page, yes), 'the browser layout is back: ' + yes);
    assert(!(await isDrawn(page, '.m-topbar')) && !(await isDrawn(page, '#btn-practise')) &&
           !(await isDrawn(page, '.m-pickhead')), 'and the mobile one is gone');
    if (tag === 'desktop') {
      // the browser layout fills a blank as it always has: a word, then its blank
      const fill = (await (await fetch(B + `/exercises/api/decks/${EN.folder}/${EN.slug}`)).json())
        .items.find(it => it.subtype === 'fill-blanks');
      await page.evaluate(([k, id]) => sessionStorage.setItem(k, JSON.stringify([id])),
                          [`parseh-cram:${EN.folder}/${EN.slug}`, fill.id]);
      await page.goto(B + `/exercises/deck/${EN.folder}/${EN.slug}/cram`);
      await page.waitForSelector('#cram-stage .ex-blank');
      await page.locator('#cram-stage .ex-blank').first().click();
      assert(!(await isDrawn(page, '.ex-cloud')), 'the browser layout: a click on a blank opens no cloud');
      await page.locator('#cram-stage .ex-bank .ex-item').filter({hasText: /^\s*went\s*$/}).click();
      await page.locator('#cram-stage .ex-blank').first().click();
      eq(await page.evaluate(() => document.querySelector('#cram-stage .ex-blank').textContent.trim()), 'went',
         'and a word, then its blank, fills it, as it always has');
    }
    await page.context().close();
  }
}

// Fill in the blanks in the mobile interface: the blank first, then the word
// (app.js, bindExercises) -- a tap on a blank opens a cloud with a copy of
// the words the bank holds, a tap on one puts it there; the bank stays
async function fillByCloud(page, tag) {
  const S = '#study-stage';
  const texts = sel => page.evaluate(sel => [...document.querySelectorAll(sel)].map(x => x.textContent.trim()), sel);
  const bank = async () => (await texts(`${S} .ex-bank .ex-item`)).sort();
  const blanks = () => texts(`${S} .ex-blank`);
  const pick = async word => {
    const l = page.locator(`${S} .ex-cloud button`).filter({hasText: new RegExp('^\\s*' + word + '\\s*$')});
    if (page.touch) await l.tap(); else await l.click();
  };
  const open = async n => {
    await tapMiddle(page, `${S} .ex-blank >> nth=${n}`);
    await page.waitForSelector(`${S} .ex-cloud`);
    await sleep(200);                                  // its fade in, over
  };
  const whole = await bank();
  eq(whole, ['bought', 'goed', 'went'], `${tag}: the fill-in's bank, three words`);
  await tapMiddle(page, `${S} .ex-bank .ex-item`);
  eq(await page.evaluate(S => document.querySelectorAll(S + ' .picked, ' + S + ' .ex-cloud').length, S), 0,
     `${tag}: a word of the bank tapped picks nothing up and opens nothing: the blanks take the words`);
  await open(0);
  eq((await texts(`${S} .ex-cloud .ex-cloud-pick`)).sort(), whole, `${tag}: a blank tapped: a cloud with a copy of every word the bank holds`);
  allFit(await targets(page, `${S} .ex-cloud button`), `${tag}: its words 48px, on the screen, reached by a tap`);
  eq(await page.evaluate(S => {
    const c = document.querySelector(S + ' .ex-cloud').getBoundingClientRect();
    const e = document.querySelector(S + ' .exercise').getBoundingClientRect();
    const f = document.querySelector(S + ' .ex-fill').getBoundingClientRect();
    return [c.left >= e.left, c.right <= e.right, c.top >= f.bottom - 1];
  }, S), [true, true, true], `${tag}: inside the exercise, under the sentence -- which it leaves to be read`);
  eq(await page.evaluate(S => document.querySelector(S + ' .ex-blank').getAttribute('aria-expanded'), S), 'true',
     `${tag}: the blank says its cloud is open`);
  await shot(page, `fill-cloud-${tag}`);
  await pick('went');
  eq([await blanks(), await bank(), await isDrawn(page, `${S} .ex-cloud`)], [['went', ''], ['bought', 'goed'], false],
     `${tag}: went picked: in the first blank, gone from the bank, the cloud away`);
  await open(1);
  eq((await texts(`${S} .ex-cloud .ex-cloud-pick`)).sort(), ['bought', 'goed'], `${tag}: the second blank's cloud: the words left`);
  await pick('bought');
  await open(0);
  eq(await texts(`${S} .ex-cloud button`), [...(await texts(`${S} .ex-cloud .ex-cloud-pick`)), 'Empty this blank'],
     `${tag}: a filled blank's cloud can empty it`);
  await pick('goed');
  eq([await blanks(), await bank()], [['goed', 'bought'], ['went']], `${tag}: another word picked there: the two change places`);
  await open(0);
  await pick('Empty this blank');
  eq([await blanks(), await bank()], [['', 'bought'], ['goed', 'went']], `${tag}: emptied: the word back in the bank`);
  await open(0);
  await tapMiddle(page, `${S} .ex-prompt, ${S} .ex-kicker`);
  assert(!(await isDrawn(page, `${S} .ex-cloud`)), `${tag}: a tap anywhere else puts the cloud away`);
  await open(0);
  await pick('went');
  eq(await blanks(), ['went', 'bought'], `${tag}: filled right`);
}

// A matching exercise in the mobile interface, the same way round: a tap on
// a term's place opens a cloud with a copy of the answers the bank holds
async function matchByCloud(page, tag) {
  const S = '#study-stage';
  const RIGHT = {flat: 'apartment', lift: 'elevator', biscuit: 'cookie'};
  const texts = sel => page.evaluate(sel => [...document.querySelectorAll(sel)].map(x => x.textContent.trim()), sel);
  const bank = async () => (await texts(`${S} .ex-bank .ex-item`)).sort();
  const rows = () => page.evaluate(S => [...document.querySelectorAll(S + ' .ex-pair-row')].map(r =>
    [r.querySelector('.ex-pair-left').textContent.trim(), r.querySelector('.ex-match-drop').textContent.trim()]), S);
  const pick = async word => {
    const l = page.locator(`${S} .ex-cloud button`).filter({hasText: new RegExp('^\\s*' + word + '\\s*$')});
    if (page.touch) await l.tap(); else await l.click();
  };
  const open = async n => {
    await tapMiddle(page, `${S} .ex-match-drop >> nth=${n}`);
    await page.waitForSelector(`${S} .ex-cloud`);
    await sleep(200);
  };
  const whole = await bank();
  eq(whole, ['apartment', 'cookie', 'elevator'], `${tag}: the match's bank, three answers`);
  eq(await page.evaluate(S => getComputedStyle(document.querySelector(S + ' .ex-match-drop'), '::after').content, S),
     '"tap to choose"', `${tag}: an empty place asks for a tap, not a drop`);
  await tapMiddle(page, `${S} .ex-bank .ex-item`);
  eq(await page.evaluate(S => document.querySelectorAll(S + ' .picked, ' + S + ' .ex-cloud').length, S), 0,
     `${tag}: an answer of the bank tapped picks nothing up: the places take the answers`);
  await open(0);
  eq((await texts(`${S} .ex-cloud .ex-cloud-pick`)).sort(), whole, `${tag}: a place tapped: a cloud with a copy of every answer the bank holds`);
  allFit(await targets(page, `${S} .ex-cloud button`), `${tag}: its answers 48px, on the screen, reached by a tap`);
  eq(await page.evaluate(S => {
    const c = document.querySelector(S + ' .ex-cloud').getBoundingClientRect();
    const e = document.querySelector(S + ' .exercise').getBoundingClientRect();
    return [c.left >= e.left, c.right <= e.right];
  }, S), [true, true], `${tag}: the cloud inside the exercise`);
  await shot(page, `match-cloud-${tag}`);
  const terms = (await rows()).map(r => r[0]);
  // the first one wrong, the rest right; then the wrong one changed
  const wrong = RIGHT[terms[1]];
  await pick(wrong);
  for (let i = 1; i < terms.length; i++) {
    await open(i);
    if (i === 1) eq((await texts(`${S} .ex-cloud .ex-cloud-pick`)).sort(), whole.filter(w => w !== wrong),
                    `${tag}: the next place's cloud: the answers left`);
    // the one the first place took is back in the bank when its row needs it
    await pick(i === 1 ? RIGHT[terms[0]] : RIGHT[terms[i]]);
  }
  eq((await rows()).map(r => r[1]), [wrong, RIGHT[terms[0]], RIGHT[terms[2]]], `${tag}: three placed, two of them crossed`);
  await open(0);
  eq(await texts(`${S} .ex-cloud button`), ['Empty this match'], `${tag}: a filled place's cloud, with the bank empty: it can be emptied`);
  await pick('Empty this match');
  eq(await bank(), [wrong], `${tag}: emptied: its answer back in the bank`);
  await open(1);
  await pick(wrong);
  eq([(await rows()).map(r => r[1]), await bank()], [['', wrong, RIGHT[terms[2]]], [RIGHT[terms[0]]]],
     `${tag}: an answer put where another was: that one back in the bank`);
  await open(0);
  await pick(RIGHT[terms[0]]);
  await open(1);
  await tapMiddle(page, `${S} .ex-prompt`);
  assert(!(await isDrawn(page, `${S} .ex-cloud`)), `${tag}: a tap anywhere else puts the cloud away`);
  await open(1);
  await pick('Empty this match');
  await open(1);
  await pick(RIGHT[terms[1]]);
  eq((await rows()).map(r => r[1]), terms.map(t => RIGHT[t]), `${tag}: every term matched right`);
}

// cramming: Skip beside the answer's button, then Next exercise in its
// place; and at the end, what was wrong and what was skipped
async function cramAnswerBar(page, tag, rail) {
  const box = await rect(page, '#cram-actions');
  const [W, H] = await page.evaluate(() => [innerWidth, innerHeight]);
  if (rail) assert(near(box.r, W) && near(box.t, 0) && near(box.b, H), 'cramming sideways: the column at the right');
  else assert(near(box.b, H) && near(box.l, 0), 'cramming upright: the bar at the foot');
  assert(!(await isDrawn(page, '.m-topbar')), 'cramming: no bar over the exercise');
  const primary = await page.evaluate(() => !document.querySelector('#cram-check').hidden ? '#cram-check' : '#cram-show');
  allFit(await targets(page, `${primary}, #cram-skip`), 'cramming: the answer\'s button and Skip, 48px');
  const at = await rect(page, primary), sk = await rect(page, '#cram-skip');
  if (rail) assert(sk.t < at.t && near(sk.l, box.l + 12, 4), 'sideways: Skip at the top of the column, the answer at its foot');
  else assert(near(sk.t, at.t, 4) && sk.r < at.l, 'upright: Skip beside the answer, on its left');
  await tap(page, primary);
  const then = primary === '#cram-check' ? '#cram-next' : '#cram-correct';
  await page.waitForFunction(sel => !document.querySelector(sel).hidden, then);
  const nx = await rect(page, then);
  assert(near(nx.b, at.b, 4) && near(nx.r, at.r), `cramming: ${then} where ${primary} was ` + JSON.stringify([at, nx]));
  await shot(page, `cram-${tag}`);
  // on to the end: this one gone on from, every other one skipped
  if (then === '#cram-next') {
    assert(!(await isDrawn(page, '#cram-skip')), 'checked, it is answered: no Skip');
    await tap(page, '#cram-next');
  } else await tap(page, '#cram-wrong');
  for (let n = 0; n < 6 && !(await isDrawn(page, '#cram-done')); n++) {
    await tap(page, (await isDrawn(page, '#cram-skip')) ? '#cram-skip' : '#cram-next');
    await sleep(150);
  }
  assert(await isDrawn(page, '#cram-done'), 'the practice over, the end is drawn');
  const tally = await page.locator('#cram-tally').textContent();
  assert(/^2 exercises: .*skipped\.$/.test(tally), 'it says how it went: ' + tally);
  await page.evaluate(() => scrollTo(0, 0));
  allFit(await targets(page, '#cram-skipped-list .dk-cram-item, #cram-done .dk-cram-list:not([hidden]) > .btn, ' +
                               '#cram-again, #cram-done .dk-back'),
         'the skipped ones listed, and every button of the end, 48px, reached by a tap');
  if (await isDrawn(page, '#cram-wrong-list'))
    eq(await page.locator('#cram-wrong-list .dk-cram-meta').first().textContent(), 'wrong once, then skipped',
       'the one answered wrong says so, and that it was skipped after');
  await tap(page, '#cram-skipped-list .dk-cram-item');
  await page.waitForSelector('#cram-skipped-list .dk-cram-solved:not([hidden]) .exercise');
  assert(true, 'a tap on one shows it solved');
  await shot(page, `cram-${tag}-end`);
}

// ======== app ========
async function partApp() {
  console.log('\n== the mobile interface as an app');
  const page = await newPage(PHONE, 'app');
  const cdp = await page.context().newCDPSession(page);
  // ---- a) the app's own address
  await page.goto(B + '/?mode=mobile#top');
  eq(await page.evaluate(() => [document.documentElement.dataset.mode, localStorage.getItem('parseh_mode'),
                                location.pathname + location.search + location.hash]),
     ['mobile', 'mobile', '/#top'], '/?mode=mobile: the mobile mode, and the address given back without it');
  await page.evaluate(() => navigator.serviceWorker.ready);
  await page.reload();
  eq(await page.evaluate(() => !!navigator.serviceWorker.controller), true, 'the worker takes the pages over');
  const man = await cdp.send('Page.getAppManifest');
  eq([new URL(man.url).pathname, man.errors], ['/manifest.webmanifest', []], 'the manifest, read without an error');
  for (const [where, url] of [['the hub', '/'], ['the shelf', '/m/books/'], ['a reader', MADE.readers.fa],
                              ['the decks', '/exercises/']]) {
    await page.goto(B + url);
    await page.waitForLoadState('load');
    await sleep(300);
    const why = (await cdp.send('Page.getInstallabilityErrors')).installabilityErrors.map(e => e.errorId);
    // a test's browser is incognito, which Chromium never installs from:
    // nothing else may stand in the way
    eq(why, ['in-incognito'], `${where}: installable, as far as a page can make it so`);
  }
  eq(await page.evaluate(() => [...document.querySelectorAll('link[rel=manifest]')].length), 1,
     'the decks name the manifest once');
  // ---- b) the install page, and the hub's door to it
  await page.goto(B + '/');
  assert(await isDrawn(page, '.hub-mobile a.m-appdoor[href="/m/install/"]'), 'the hub has the door to installing it');
  await Promise.all([page.waitForURL(B + '/m/install/'), tap(page, '.hub-mobile a.m-appdoor')]);
  await page.waitForFunction(() => /trusts/.test(document.querySelector('#m-appnow').textContent));
  assert(/This phone trusts Parseh/.test(await page.locator('#m-appnow').textContent()),
         'the install page: this phone trusts Parseh (here, the computer itself)');
  assert(!(await isDrawn(page, 'a[href$="parseh-ca.crt"]')), 'and no certificate to hand over over plain http');
  await shot(page, 'install');
  // ---- c) the server away
  hub.kill('SIGTERM');
  await hub.status;
  hubUp = false;
  await page.goto(B + '/m/books/').catch(() => {});
  await sleep(300);
  // with nothing to answer for the server, the browser's own error page
  // would be here, and nothing of the page's to read
  const said = await page.evaluate(() => [location.pathname, document.querySelector('h1') &&
    document.querySelector('h1').textContent]).catch(() => [page.url(), 'the browser\'s own error page']);
  eq(said, ['/m/books/', 'Parseh cannot be reached'],
     'the server stopped: the page says Parseh cannot be reached, at its own address');
  await shot(page, 'offline');
  await page.context().close();
}

try {
  if (PARTS.includes('shelf')) await partShelf();
  if (PARTS.includes('reader')) await partReader();
  if (PARTS.includes('decks')) await partDecks();
  // last: it stops the server
  if (PARTS.includes('app')) await partApp();
} finally {
  await browser.close();
  if (hubUp) { hub.kill('SIGTERM'); await hub.status; }
  await Deno.remove(WORK, {recursive: true}).catch(() => {});
}
if (errors.length) { console.log('\npage errors:\n  ' + errors.join('\n  ')); Deno.exit(1); }
console.log(`\n${passed} passed`);

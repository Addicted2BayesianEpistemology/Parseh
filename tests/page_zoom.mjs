// SPDX-License-Identifier: GPL-3.0-or-later
// Browser test of the page zoom (lib/pagezoom.js, a0.5.0), against the REAL
// hub (serve.main, booted by tests/mobile_harness.py) over a temporary
// toolbox: readers of six languages (English narrated, with a film beside it),
// the shelves, three exercise decks, a document -- every kind of page that is
// zoomed.  What is measured is measured WHERE IT IS DRAWN: Playwright's boxes
// and its real mouse and touch, never the page's own geometry alone (which is
// what the zoom replaces and so cannot be its own witness), on a desktop with
// a mouse (1280x800), a phone upright (390x844), turned, and a tablet, in
// Chromium:
//
// contract -- ParsehZoom, on a real page
//   a) at 100 % NOTHING is replaced: no style, no attribute, no stylesheet,
//      the engine's own functions and getters on the window, the elements and
//      the events -- on a reader BUILT BEFORE the zoom existed too, whose own
//      scripts find the shim already in place (the file is written into the
//      page by lib/parseh.js, ahead of them)
//   b) a step is stored (`parseh_zoom`), put on the page, announced
//      (`parseh:zoom`, onChange), and the page's geometry is in its own px:
//      rects, the window's size and scroll, the point a click or a finger was
//      at, what is under a point, the density -- each against the real boxes
//   c) a step is the next of the nine and the end of them says so; the way
//      back to 100 % puts every function back
//   d) another tab follows; a reload keeps it; a window made narrower is
//      given less and NEVER has what was chosen lowered (a phone turned
//      upright and back is where it was left); the 320 rule on the line
//   e) off the disk (file:) nothing is done; an engine that does not zoom
//      the way this knows is refused with a sentence and left alone; a
//      printed page is at its own size; a browser that will not store
//      still zooms
//   f) the sheets that arrive after, a style set by a script, a step taken
//      while the page is open: every viewport length follows, and the way
//      back puts the sheets back
// units -- every viewport length the toolbox's own files write (read off
//   them), as the same page at 100 % in a window 1/Z the size: each computes
//   to the same number
// pages -- every kind of page, at 100/125/150/200 on a desktop and at the
//   largest step a phone allows (the rest are refused it): in force, no
//   sideways scroll, and the page never widens the glass it is on
// clouds -- the reader's, the player's and the studio's word cloud beside
//   what they are about as they are at 100 %, and inside the window; the
//   dictionary's sheet clearing the chunk it is about (and the video pinned
//   over a transcript), on a phone and a tablet
// pointer -- a real mouse over a control's middle is over it, which the page's
//   elementFromPoint(clientX, clientY) says too; a real click lands on it
// strip -- the timeline's strip maps a drag to the same time at every zoom
// fixed -- bars, sheets and the dock stay inside the window
// app -- the installed app on a phone (its two marks answered as an app's are)
//   CHROME_BIN=... PARSEH_PYTHON=python3 deno run --allow-all tests/page_zoom.mjs
//   ZOOM_PARTS=contract,units,pages,clouds,pointer,strip,fixed,app runs some of it
//   SHOTS=<dir> also saves a screenshot of each page
import { chromium } from 'npm:playwright-core@1.52.0';

const root = await Deno.realPath(new URL('..', import.meta.url));
Deno.chdir(root);
const PY = Deno.env.get('PARSEH_PYTHON') || 'python3';
const SHOTS = Deno.env.get('SHOTS') || '';
const PARTS = (Deno.env.get('ZOOM_PARTS') || 'contract,units,pages,clouds,pointer,strip,fixed,app').split(',');
const td = new TextDecoder();
let passed = 0;
const assert = (v, m) => { if (!v) throw Error('FAIL: ' + m); passed++; console.log('  ok', m); };
const J = JSON.stringify;
const eq = (got, want, m) => assert(J(got) === J(want), m + (J(got) === J(want) ? '' : ': got ' + J(got) + ' want ' + J(want)));
const near = (a, b, tol) => Math.abs(a - b) <= tol;
const sleep = ms => new Promise(r => setTimeout(r, ms));
const NARROW = 'this screen is too narrow for more';
function freePort() {
  const l = Deno.listen({hostname: '127.0.0.1', port: 0});
  const p = l.addr.port;
  l.close();
  return p;
}

// ---- the toolbox, and its server (tests/mobile_harness.py: a temporary tree)
const WORK = await Deno.makeTempDir({prefix: 'parseh-page-zoom-'});
const built = await new Deno.Command(PY, {args: ['tests/mobile_harness.py', 'build', WORK], cwd: root,
                                          stdout: 'piped', stderr: 'piped'}).output();
if (!built.success) throw Error(td.decode(built.stderr) || td.decode(built.stdout));
const MADE = JSON.parse(td.decode(built.stdout).trim().split('\n').pop());
const port = freePort();
const log = [];
const hub = new Deno.Command(PY, {args: ['tests/mobile_harness.py', 'serve', WORK, String(port)], cwd: root,
                                  stdout: 'piped', stderr: 'piped'}).spawn();
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

const DESK = {viewport: {width: 1280, height: 800}};
const PHONE = {viewport: {width: 390, height: 844}, isMobile: true, hasTouch: true};
const LAND = {viewport: {width: 844, height: 390}, isMobile: true, hasTouch: true};
const TABLET = {viewport: {width: 820, height: 1180}, isMobile: true, hasTouch: true};
const READER = MADE.readers.en;
const VIDEO = `/youtube/v/${MADE.video}/`;
const DECK = `/exercises/deck/${MADE.decks.en.folder}/${MADE.decks.en.slug}/`;

// A DOCUMENT WITH A FILL-IN EXERCISE, whose blank opens a cloud of words
const LESSON = `---
title: Zoom lesson
lang: en
---

# Zoom lesson

Some plain text to read, and then a sentence with two blanks to fill.

:::exercise fill-blanks
prompt: Complete the sentence with the past of [go]{tl} and of [buy]{tl}.
text: [Yesterday I [[go]] to the market and [[buy]] two apples.]{tl}
- [go] [went]{tl}
- [buy] [bought]{tl}
- [ ] [goed]{tl}
explanation-correct: Right: [went]{tl} and [bought]{tl}.
:::
`;
const made = await (await fetch(B + '/studio/api/docs', {method: 'POST',
  headers: {'Content-Type': 'application/json'}, body: JSON.stringify({markdown: LESSON})})).json();
const DOC = '/studio/doc/' + made.meta.id;

// a page, in a context of its own, with what the device holds set before the
// page's first script runs: a zoom, the mode, the theme
async function open(opts, tag, set = {}) {
  const ctx = await browser.newContext(opts);
  const page = await ctx.newPage();
  page.on('pageerror', e => { errors.push(tag + ': ' + e.message); console.log('PAGE ERROR', tag, e.message); });
  // seeded once: a page that sets another size must not have it put back by a reload
  await ctx.addInitScript(s => {
    try {
      if (sessionStorage.getItem('__seeded')) return;
      sessionStorage.setItem('__seeded', '1');
      if (s.zoom && s.zoom !== 100) localStorage.setItem('parseh_zoom', String(s.zoom));
      if (s.mode) localStorage.setItem('parseh_mode', s.mode);
      if (s.theme) localStorage.setItem('parseh_theme', s.theme);
    } catch (e) {}
  }, set);
  if (set.mode) await ctx.addCookies([{name: 'parseh_mode', value: set.mode, url: B}]);
  if (opts.hasTouch) {
    page.touch = await ctx.newCDPSession(page);
    await page.touch.send('Emulation.setTouchEmulationEnabled', {enabled: true, maxTouchPoints: 1});
  }
  return page;
}
async function go(page, path) {
  await page.goto(B + path);
  await page.evaluate(() => document.fonts.ready.then(() =>
    new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))));
}
const shot = async (page, name) => {
  if (!SHOTS) return;
  await Deno.mkdir(SHOTS, {recursive: true});
  await page.screenshot({path: `${SHOTS}/${name}.png`});
  if (page.touch) await page.touch.send('Emulation.setTouchEmulationEnabled', {enabled: true, maxTouchPoints: 1});
};
const closeAll = page => page.context().close();
// the zoom in force, and what the page's own function says it is
const state = page => page.evaluate(() => {
  const de = document.documentElement, Z = window.ParsehZoom;
  let stored = 'n/a';
  try { stored = localStorage.getItem('parseh_zoom'); } catch (e) {}
  return {has: !!Z, applied: Z && Z.applied(), chosen: Z && Z.get(), factor: Z && Z.factor(), zoom: de.style.zoom,
          dz: de.getAttribute('data-zoom'), z: de.style.getPropertyValue('--z'), stored};
});
// whether each function and getter the shim replaces is the engine's own
const natives = page => page.evaluate(() => {
  const nat = f => /\[native code\]/.test(Function.prototype.toString.call(f));
  const get = (o, n) => Object.getOwnPropertyDescriptor(o, n).get;
  return {
    rect: nat(Element.prototype.getBoundingClientRect), rects: nat(Element.prototype.getClientRects),
    range: nat(Range.prototype.getBoundingClientRect), innerWidth: nat(get(window, 'innerWidth')),
    scrollY: nat(get(window, 'scrollY')), dpr: nat(get(window, 'devicePixelRatio')),
    rootClient: nat(get(Element.prototype, 'clientWidth')), rootScroll: nat(get(Element.prototype, 'scrollTop')),
    scrollTo: nat(window.scrollTo), point: nat(Document.prototype.elementFromPoint),
    mouse: nat(get(MouseEvent.prototype, 'clientX')), touch: window.Touch ? nat(get(Touch.prototype, 'clientX')) : true,
    vv: window.visualViewport ? nat(get(VisualViewport.prototype, 'width')) : true,
    io: nat(get(IntersectionObserverEntry.prototype, 'boundingClientRect'))};
});
const allNative = n => Object.values(n).every(Boolean);
const noneNative = n => Object.values(n).every(v => !v);
// a box as the browser draws it (Playwright's, in the window's own px)
const box = (page, sel) => page.locator(sel).first().boundingBox();
const waitFor = (page, fn, arg, timeout = 8000) => page.waitForFunction(fn, arg, {timeout});
// the window as it really is, whatever the zoom
const glass = page => page.evaluate(() => { const f = ParsehZoom.factor(); return [visualViewport.width * visualViewport.scale * f, visualViewport.height * visualViewport.scale * f]; });

// ======== contract ========
async function partContract() {
  console.log('\n== the contract: ParsehZoom on a real page');

  // ---- a) at 100 % nothing is replaced
  let page = await open(DESK, 'contract');
  await go(page, '/');
  let s = await state(page);
  eq([s.has, s.applied, s.chosen, s.factor, s.zoom, s.dz, s.z, s.stored], [true, 100, 100, 1, '', null, '', null],
     'a page with no zoom chosen is at 100 %, with nothing written on it');
  eq(await page.evaluate(() => [document.documentElement.getAttribute('style'),
       document.querySelectorAll('style[data-parseh-zoom]').length]), [null, 0],
     'no style on the root, no sheet of the zoom\'s in the head');
  assert(allNative(await natives(page)), 'every function and getter the shim would replace is the engine\'s own at 100 %: '
         + J(await natives(page)));
  eq(await page.evaluate(() => ParsehZoom.STEPS), [70, 80, 90, 100, 110, 125, 150, 175, 200], 'the nine steps');
  eq(await page.evaluate(() => [ParsehZoom.KEY, ParsehZoom.MIN_WIDTH]), ['parseh_zoom', 320], 'its key, and the rule\'s width');
  // the tag is written where the parser is: right after parseh.js, ahead of the page's own
  const order = await page.evaluate(() => [...document.scripts].map(x => x.src.replace(location.origin, '')).filter(Boolean));
  assert(order.indexOf('/lib/parseh.js') >= 0 && order.indexOf('/lib/pagezoom.js') === order.indexOf('/lib/parseh.js') + 1,
         'lib/parseh.js wrote the zoom\'s <script> right after itself, in the parser\'s hands: ' + J(order.slice(0, 4)));
  eq(await page.evaluate(() => document.querySelectorAll('script[src$="/lib/pagezoom.js"]').length), 1, 'and only one');
  await closeAll(page);

  // ---- a) a reader built before the zoom existed: its own scripts find the shim in place
  const html = await (await fetch(B + READER)).text();
  assert(!/pagezoom/.test(html), 'the reader (a page built, as every book\'s was, before the zoom) says nothing of it');
  for (const z of [100, 150]) {
    page = await open(DESK, 'early', {zoom: z});
    await page.route(B + READER, async route => {
      const res = await route.fetch();
      const body = (await res.text()).replace(/(<script src="[^"]*parseh\.js"><\/script>)/,
        '$1<script>window.__early={zoom:!!window.ParsehZoom,factor:window.ParsehZoom&&ParsehZoom.factor(),' +
        'zoomStyle:document.documentElement.style.zoom,body:!!document.body,' +
        'native:/\\[native code\\]/.test(Element.prototype.getBoundingClientRect.toString())}</script>');
      await route.fulfill({response: res, body});
    });
    await page.goto(B + READER);
    eq(await page.evaluate(() => window.__early), {zoom: true, factor: z / 100, zoomStyle: z === 100 ? '' : String(z / 100),
        body: false, native: z === 100},
       `at ${z} % the first script after parseh.js, in the head, finds ParsehZoom there`
       + (z === 100 ? ' and the engine untouched' : ' with the shim in and the page already zoomed'));
    await closeAll(page);
  }

  // ---- b) a step: stored, on the page, announced, in the page's own px
  page = await open(DESK, 'contract');
  await go(page, '/');
  await page.evaluate(() => {
    window.__events = []; window.__cb = [];
    document.addEventListener('parseh:zoom', e => __events.push(e.detail));
    window.__off = ParsehZoom.onChange((z, d) => __cb.push([z, d.chosen]));
  });
  eq(await page.evaluate(() => ParsehZoom.set(150)), true, 'set(150) is taken');
  s = await state(page);
  eq([s.applied, s.chosen, s.factor, s.zoom, s.dz, s.z, s.stored], [150, 150, 1.5, '1.5', '150', '1.5', '150'],
     'stored, in force, on the root as zoom, --z and data-zoom');
  eq(await page.evaluate(() => [__events, __cb]), [[{zoom: 150, chosen: 150, factor: 1.5}], [[150, 150]]],
     'the event parseh:zoom and onChange say so, once');
  assert(noneNative(await natives(page)), 'and every function and getter of the shim is replaced: ' + J(await natives(page)));
  // a box of known size and place, measured by the browser and by the page
  await page.evaluate(() => {
    document.body.style.minHeight = '3000px';
    const b = document.createElement('div');
    b.id = 'zbox';
    b.style.cssText = 'position:absolute;left:100px;top:700px;width:100px;height:50px;background:#39c;z-index:99999';
    b.textContent = 'zoom box';
    document.body.appendChild(b);
  });
  await page.evaluate(() => scrollTo(0, 500));
  await sleep(150);
  const f = 1.5;
  const real = await box(page, '#zbox');
  const seen = await page.evaluate(() => {
    const el = document.getElementById('zbox'), r = el.getBoundingClientRect();
    const rg = document.createRange(); rg.selectNodeContents(el);
    const rr = rg.getBoundingClientRect(), list = el.getClientRects(), de = document.documentElement;
    return {rect: [r.left, r.top, r.width, r.height], range: [rr.left, rr.width], rects: list.length, item: !!list.item(0),
            inner: [innerWidth, innerHeight], scroll: [scrollX, scrollY, pageYOffset, de.scrollTop],
            root: [de.clientWidth, de.clientHeight, de.scrollHeight], offset: [de.offsetWidth, de.offsetHeight],
            dpr: devicePixelRatio, vv: [visualViewport.width, visualViewport.height, visualViewport.scale],
            under: (document.elementFromPoint(150, 225) || {}).id,
            under2: document.elementsFromPoint(150, 225).map(x => x.id).slice(0, 1)};
  });
  // the page is scrolled 500 of ITS px, which is 750 of the glass's: the box, at 700, is at 200 of them
  assert(near(real.x, 150, 0.5) && near(real.y, 300, 1) && near(real.width, 150, 0.5) && near(real.height, 75, 0.5),
         'the browser draws the box 150 % bigger, 300 px down the glass: ' + J([real.x, real.y, real.width, real.height]));
  assert(near(seen.rect[0], 100, 0.1) && near(seen.rect[1], 200, 0.5) && near(seen.rect[2], 100, 0.1) && near(seen.rect[3], 50, 0.1),
         'its getBoundingClientRect() is in the page\'s px, the numbers a style takes: ' + J(seen.rect));
  assert(seen.rects === 1 && seen.item, 'getClientRects() is a list of one, with item()');
  assert(seen.range[0] > 0 && near(seen.range[0], 100, 40), 'a Range\'s rect is in them too (' + J(seen.range) + ')');
  assert(near(seen.inner[0], 1280 / f, 0.5) && near(seen.inner[1], 800 / f, 0.5), 'innerWidth and innerHeight: ' + J(seen.inner));
  assert(near(seen.scroll[1], 500, 0.5) && near(seen.scroll[2], 500, 0.5) && near(seen.scroll[3], 500, 0.5) && seen.scroll[0] === 0,
         'scrollTo(0, 500) in the page\'s px puts the page at 500 of them: ' + J(seen.scroll));
  assert(near(seen.root[0], 1280 / f, 0.5) && near(seen.root[1], 800 / f, 0.5) && near(seen.root[0], seen.offset[0], 1),
         'the root\'s clientWidth and clientHeight are the window\'s (' + J(seen.root) + '), its own width ' + seen.offset[0].toFixed(1));
  assert(near(seen.root[2], seen.offset[1], 2), 'and its scrollHeight is its own height in them (' + seen.root[2] + ', ' + seen.offset[1] + ')');
  eq(seen.dpr, f, 'devicePixelRatio is 1.5: a page px is a pixel and a half');
  assert(near(seen.vv[0], 1280 / f, 0.5) && near(seen.vv[1], 800 / f, 0.5) && seen.vv[2] === 1, 'the visual viewport: ' + J(seen.vv));
  eq([seen.under, seen.under2], ['zbox', ['zbox']], 'elementFromPoint() and elementsFromPoint() take a point in the page\'s px');
  // a real click at the middle of the box, as the browser makes it
  await page.evaluate(() => {
    window.__clicks = [];
    document.addEventListener('click', e => __clicks.push([e.clientX, e.clientY, e.pageX, e.pageY, e.x, e.y, e.target.id]), true);
  });
  await page.mouse.click(real.x + real.width / 2, real.y + real.height / 2);
  const click = await page.evaluate(() => __clicks[0]);
  assert(click && click[6] === 'zbox' && near(click[0], 150, 0.6) && near(click[1], 225, 0.6) && near(click[4], 150, 0.6)
         && near(click[5], 225, 0.6) && near(click[2], 150, 0.6) && near(click[3], 725, 0.6),
         'a real click at its middle lands on it and says where, in the page\'s px, in the window and in the page: ' + J(click));
  await closeAll(page);
  // a finger, on a phone, says it in the same px
  page = await open(PHONE, 'contract-touch', {zoom: 110});
  await go(page, '/');
  await page.evaluate(() => {
    window.__touch = [];
    document.addEventListener('touchstart', e => __touch.push([e.touches[0].clientX, e.touches[0].clientY, e.touches[0].pageX, e.touches[0].pageY]), true);
  });
  await page.touchscreen.tap(200, 300);
  const t0 = await page.evaluate(() => __touch[0]);
  assert(t0 && near(t0[0], 200 / 1.1, 0.6) && near(t0[1], 300 / 1.1, 0.6) && near(t0[2], 200 / 1.1, 0.6),
         'a touch says where it is in the page\'s px: ' + J(t0));
  await closeAll(page);

  // the same line stays where it is on the screen when a step is taken
  page = await open(DESK, 'anchor');
  await go(page, READER);
  await page.evaluate(() => { const t = document.querySelectorAll('.sub')[2]; scrollBy(0, t.getBoundingClientRect().top - 150); });
  await sleep(300);
  const before = await box(page, '.sub[data-s="2"]');
  await page.evaluate(() => ParsehZoom.set(150));
  await sleep(300);
  const after = await box(page, '.sub[data-s="2"]');
  assert(near(before.y, after.y, 40), `a step taken in the middle of a book keeps the line read where it was on the screen (${before.y.toFixed(0)} -> ${after.y.toFixed(0)})`);
  await page.evaluate(() => ParsehZoom.set(100));
  await sleep(300);
  const back = await box(page, '.sub[data-s="2"]');
  assert(near(before.y, back.y, 40), `and so does the step back (${back.y.toFixed(0)})`);
  await closeAll(page);

  // ---- c) the steps, and the way back
  page = await open(DESK, 'steps');
  await go(page, '/');
  const walk = await page.evaluate(() => {
    const out = [];
    for (let i = 0; i < 6; i++) out.push([ParsehZoom.can(1), ParsehZoom.step(1), ParsehZoom.applied()]);
    return out;
  });
  eq(walk, [[true, true, 110], [true, true, 125], [true, true, 150], [true, true, 175], [true, true, 200],
            ['this is the largest size', 'this is the largest size', 200]],
     'step(+1) climbs the nine; at the top there is a sentence for why not');
  eq(await page.evaluate(() => {
    const out = [];
    for (let i = 0; i < 10; i++) out.push([ParsehZoom.can(-1), ParsehZoom.step(-1), ParsehZoom.applied()]);
    return out.slice(5);
  }), [[true, true, 90], [true, true, 80], [true, true, 70],
       ['this is the smallest size', 'this is the smallest size', 70], ['this is the smallest size', 'this is the smallest size', 70]],
     'and step(-1) down to 70, where it says so');
  s = await state(page);
  eq([s.applied, s.factor, s.zoom, s.dz], [70, 0.7, '0.7', '70'], 'a page at 70 % is zoomed out the same way');
  assert((await page.evaluate(() => innerWidth)) > 1800 && (await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 0.5)),
         'and has the window\'s width in its own px (innerWidth is 1/0.7 of it), nothing sideways');
  eq(await page.evaluate(() => ParsehZoom.set(113)), true, 'a number that is not a step is taken as the nearest one');
  eq((await state(page)).applied, 110, '113 is 110');
  eq(await page.evaluate(() => ParsehZoom.reset()), true, 'reset() goes to 100');
  s = await state(page);
  eq([s.applied, s.zoom, s.dz, s.z, s.stored], [100, '', null, '', null], 'and takes everything off the page, the stored number too');
  assert(allNative(await natives(page)), 'every function and getter is the engine\'s own again');
  eq(await page.evaluate(() => document.documentElement.getAttribute('style')), null, 'the root has no style attribute left');
  eq(await page.evaluate(() => { const o = []; ParsehZoom.onChange(() => o.push(1))(); ParsehZoom.set(125); return o.length; }), 0,
     'the function onChange hands back stops it');
  // a stored value that is not a size is not one
  for (const [stored, want] of [['1.5', 100], ['999', 100], ['112', 110], ['abc', 100], ['', 100]]) {
    await page.evaluate(v => localStorage.setItem('parseh_zoom', v), stored);
    eq(await page.evaluate(() => ParsehZoom.get()), want, `a stored "${stored}" is ${want}`);
  }
  await closeAll(page);

  // ---- d) another tab follows, a reload keeps it
  const ctx = await browser.newContext(DESK);
  const A = await ctx.newPage(), T = await ctx.newPage();
  for (const p of [A, T]) p.on('pageerror', e => { errors.push('tabs: ' + e.message); console.log('PAGE ERROR tabs', e.message); });
  await A.goto(B + '/');
  await T.goto(B + '/books/');
  await A.evaluate(() => ParsehZoom.set(125));
  await waitFor(T, () => document.documentElement.getAttribute('data-zoom') === '125');
  eq(await T.evaluate(() => [ParsehZoom.applied(), document.documentElement.style.zoom]), [125, '1.25'],
     'a step taken in one tab is followed by another (the storage event), the page in it zoomed');
  assert(noneNative(await natives(T)), 'and its shim is in');
  await T.evaluate(() => ParsehZoom.set(100));
  await waitFor(A, () => document.documentElement.getAttribute('data-zoom') === null);
  assert(allNative(await natives(A)), 'and the step back, taken in that one, is followed by the first, which is put back');
  await A.evaluate(() => ParsehZoom.set(175));
  await A.reload();
  s = await state(A);
  eq([s.applied, s.zoom, s.dz, s.stored], [175, '1.75', '175', '175'], 'a reload keeps it');
  await ctx.close();

  // ---- d) a window made narrower is given less, and what was chosen is kept
  page = await open(DESK, 'resize', {zoom: 200});
  await go(page, '/');
  eq((await state(page)).applied, 200, 'a desktop window is given 200 %');
  const resized = async w => {
    await page.setViewportSize({width: w, height: 800});
    await waitFor(page, () => document.documentElement.style.zoom === (ParsehZoom.applied() === 100 ? '' : String(ParsehZoom.applied() / 100)));
    return await page.evaluate(() => ({applied: ParsehZoom.applied(), chosen: ParsehZoom.get(), stored: localStorage.getItem('parseh_zoom'),
      zoom: document.documentElement.style.zoom, max: ParsehZoom.allowedMax(), dz: document.documentElement.getAttribute('data-zoom')}));
  };
  // the rule on the line: width x 100 >= 320 x the step
  for (const [w, want] of [[640, 200], [639, 175], [560, 175], [559, 150], [480, 150], [479, 125], [400, 125], [399, 110],
                           [352, 110], [351, 100], [300, 100]]) {
    const r = await resized(w);
    eq([r.applied, r.max, r.chosen, r.stored, r.dz], [want, want, 200, '200', want === 100 ? null : String(want)],
       `${w} px is given ${want} %, what was chosen (200) is not lowered, the root says ${want}`);
  }
  eq(await page.evaluate(() => [ParsehZoom.can(1), ParsehZoom.set(150), ParsehZoom.set(200), localStorage.getItem('parseh_zoom')]),
     [NARROW, NARROW, NARROW, '200'], 'where a step is refused can() and set() say why, in a sentence, and set() stores nothing');
  const wide = await resized(1280);
  eq([wide.applied, wide.stored], [200, '200'], 'the window grown again is given the 200 % back');
  assert(await page.evaluate(() => ParsehZoom.fits(110, 352) && !ParsehZoom.fits(110, 351.9) && ParsehZoom.fits(125, 400)
                                   && ParsehZoom.fits(100, 10) && ParsehZoom.fits(70, 10) && ParsehZoom.fits(200, 0)),
         'the rule is whole numbers: 352 px is on the line for 110 %, 351.9 is not; 100 and less always fit; no width asks nothing');
  await closeAll(page);

  // ---- d) a phone: upright it is given 110 %, turned it is given what was chosen
  page = await open(PHONE, 'phone', {zoom: 200});
  await go(page, '/');
  s = await state(page);
  eq([s.applied, s.chosen, s.zoom, s.stored], [110, 200, '1.1', '200'], 'a 390 px phone is given 110 % of the 200 % it chose');
  eq(await page.evaluate(() => [ParsehZoom.can(1), ParsehZoom.can(-1), ParsehZoom.allowedMax()]),
     [NARROW, true, 110], 'and its stepper has a reason where it goes no further');
  await page.setViewportSize(LAND.viewport);
  await waitFor(page, () => ParsehZoom.applied() === 200 && document.documentElement.style.zoom === '2');
  s = await state(page);
  eq([s.applied, s.chosen, s.zoom, s.stored], [200, 200, '2', '200'], 'turned sideways (844 px) it is given the 200 % it chose');
  await page.setViewportSize(PHONE.viewport);
  await waitFor(page, () => ParsehZoom.applied() === 110 && document.documentElement.style.zoom === '1.1');
  eq((await state(page)).applied, 110, 'and upright again, 110');
  eq(await page.evaluate(() => ParsehZoom.set(125)), NARROW, 'a step the phone cannot take is refused');
  eq(await page.evaluate(() => [ParsehZoom.step(1), ParsehZoom.set(110), ParsehZoom.step(-1), ParsehZoom.applied(), ParsehZoom.get()]),
     [NARROW, true, true, 100, 100], 'and one it can is taken, down to 100, the choice with it');
  await closeAll(page);
}

// ---- e) the places it does nothing, or is refused, and the print
async function partRefusals() {
  console.log('\n== where it does nothing, and where it is refused');
  // off the disk: the file is named by its address, and does nothing
  const dir = await Deno.makeTempDir({prefix: 'parseh-zoom-file-'});
  const lib = new URL('../lib/pagezoom.js', import.meta.url).href;
  await Deno.writeTextFile(dir + '/p.html', `<!doctype html><html><head><meta name=viewport content="width=device-width">
<script>try { localStorage.setItem('parseh_zoom', '150'); } catch (e) {}</script><script src="${lib}"></script></head><body><p>a page off the disk</p></body></html>`);
  let ctx = await browser.newContext(DESK);
  let page = await ctx.newPage();
  await page.goto('file://' + dir + '/p.html');
  await page.reload();
  eq(await page.evaluate(() => [typeof window.ParsehZoom, document.documentElement.style.zoom, document.documentElement.getAttribute('data-zoom')]),
     ['undefined', '', null], 'a page read off the disk has no ParsehZoom and no zoom, whatever is stored (the browser\'s own is there)');
  await ctx.close();
  await Deno.remove(dir, {recursive: true});

  // an engine whose zoom is another thing: refused, with a sentence, and left alone
  page = await open(DESK, 'legacy', {zoom: 150});
  await page.addInitScript(() => {
    // what an engine with the old zoom answers: a rect in the page's own px, whatever zoom the element has
    const was = Element.prototype.getBoundingClientRect;
    Element.prototype.getBoundingClientRect = function () {
      const r = was.call(this), z = this.style && this.style.zoom ? parseFloat(this.style.zoom) : 1;
      return new DOMRect(r.x / z, r.y / z, r.width / z, r.height / z);
    };
  });
  await go(page, '/');
  let s = await state(page);
  eq([s.applied, s.zoom, s.dz, s.chosen], [100, '', null, 150], 'in an engine whose zoom reports no larger rect, a stored 150 is not put on the page');
  const why = 'this browser cannot zoom the page';
  eq(await page.evaluate(() => [ParsehZoom.can(1), ParsehZoom.can(-1), ParsehZoom.set(125), ParsehZoom.applied()]),
     [why, why, why, 100], 'and every step is refused with a sentence');
  const n = await natives(page);
  assert(n.innerWidth && n.scrollY && n.mouse && n.scrollTo && n.point, 'with nothing of the shim in: ' + J(n));
  eq(await page.evaluate(() => document.documentElement.getAttribute('style')), null, 'and nothing written on the page');
  await closeAll(page);

  // a printed page is the page at its own size
  page = await open(DESK, 'print', {zoom: 150});
  await go(page, '/');
  eq(await page.evaluate(() => getComputedStyle(document.documentElement).zoom), '1.5', 'on the screen the root is at 1.5');
  await page.emulateMedia({media: 'print'});
  eq(await page.evaluate(() => [getComputedStyle(document.documentElement).zoom,
                                getComputedStyle(document.documentElement).getPropertyValue('--z').trim()]), ['1', '1'],
     'in print it is at 1: the paper is not zoomed');
  await page.emulateMedia({media: 'screen'});
  eq(await page.evaluate(() => getComputedStyle(document.documentElement).zoom), '1.5', 'and back on the screen at 1.5');
  await closeAll(page);

  // storage that will not answer: the choice is kept for as long as the page is open
  page = await open(DESK, 'nostore');
  await page.addInitScript(() => {
    Object.defineProperty(window, 'localStorage', {get() { throw new DOMException('no', 'SecurityError'); }, configurable: true});
  });
  await go(page, '/');
  eq(await page.evaluate(() => [ParsehZoom.set(125), ParsehZoom.get(), ParsehZoom.applied(), document.documentElement.style.zoom]),
     [true, 125, 125, '1.25'], 'with no storage a step is still taken, and held while the page is open');
  await closeAll(page);
}

// ---- f) the sheets and styles that arrive after, and a step taken while open
async function partLate() {
  console.log('\n== the lengths that arrive after the zoom does');
  const css = '.zl{position:fixed;left:0;top:60px;width:100vw;height:20px;background:#c33}';
  const page = await open(DESK, 'late', {zoom: 150});
  await page.route(B + '/__zoom.css', r => r.fulfill({contentType: 'text/css', body: css}));
  await go(page, '/');
  // a <style> a script adds, a <link> that loads, a style set by script, an element given a style
  await page.evaluate(() => {
    const st = document.createElement('style');
    st.textContent = '.zs{position:fixed;left:0;top:90px;width:100vw;max-width:calc(100vw - 20px);height:20px}';
    document.head.appendChild(st);
    const l = document.createElement('link'); l.rel = 'stylesheet'; l.href = '/__zoom.css'; document.head.appendChild(l);
    for (const c of ['zs', 'zl', 'zx', 'zy', 'zm']) { const d = document.createElement('div'); d.className = c; d.id = c; document.body.appendChild(d); }
    const x = document.getElementById('zx'); x.style.cssText = 'position:fixed;left:0;top:120px;height:20px';
    x.style.width = '50vw';
    document.getElementById('zy').outerHTML = '<div id="zy" style="position:fixed;left:0;top:150px;height:20px;width:80vw"></div>';
    const m = document.getElementById('zm'); m.style.cssText = 'position:fixed;top:180px;left:0;height:20px;width:min(900px,40vw)';
  });
  const widths = () => page.evaluate(() => ['zs', 'zl', 'zx', 'zy', 'zm'].map(id => document.getElementById(id).getBoundingClientRect().width));
  const check = async (m) => {
    // (the sheet that loads is read when it has: wait for it to say so)
    await waitFor(page, () => Math.abs(document.getElementById('zl').getBoundingClientRect().width - innerWidth) < 0.6);
    const w = await page.evaluate(() => innerWidth), got = await widths();
    const exp = [w - 20, w, w * 0.5, w * 0.8, Math.min(900, w * 0.4)];
    assert(got.every((g, i) => near(g, exp[i], 0.6)), `${m}: ${J(got.map(v => +v.toFixed(1)))} in a window ${w.toFixed(1)} wide in the page's px`);
  };
  await check('150 %: a style element, a sheet that loads, a style set by script, a style written into an element, a min()');
  await page.evaluate(() => ParsehZoom.set(200));
  await check('a step while the page is open: every one follows (200 %)');
  await page.evaluate(() => ParsehZoom.set(70));
  await check('and 70 %');
  await page.evaluate(() => ParsehZoom.reset());
  const plain = await widths();
  assert(near(plain[0], 1260, 0.5) && near(plain[1], 1280, 0.5) && near(plain[2], 640, 0.5) && near(plain[3], 1024, 0.5),
         'the way back to 100 %: the same lengths are the window\'s own again ' + J(plain));
  eq(await page.evaluate(() => [...document.styleSheets].flatMap(s => { try { return [...s.cssRules]; } catch (e) { return []; } })
        .filter(r => /--z\b/.test(r.cssText)).length), 0,
     'and none of the sheets still says --z: they were put back');
  await page.evaluate(() => ParsehZoom.set(150));
  await check('and a step again after it, once more');
  await closeAll(page);
}

// ======== units ========
// every viewport length the toolbox writes, as the same page at 100 % in a window 1/Z the size
async function partUnits() {
  console.log('\n== every viewport length of the toolbox\'s own files');
  const files = [];
  for (const dir of ['lib', 'markdown/app/static', 'youtube/lib'])
    for await (const e of Deno.readDir(dir)) if (/\.(css|js|py)$/.test(e.name)) files.push(`${dir}/${e.name}`);
  const seen = new Map();
  for (const f of files) {
    const text = await Deno.readTextFile(f);
    for (const m of text.matchAll(/([a-z][a-z-]*)\s*:\s*([^;{}\n]*\d(?:dvh|svh|lvh|vh|dvw|svw|lvw|vw|vmin|vmax)\b[^;{}\n]*)/g))
      seen.set(m[1] + ':' + m[2].trim(), [m[1], m[2].trim()]);
  }
  // only what the engine takes as a declaration (a regex over a script finds some that are prose)
  const probe = await browser.newContext(DESK);
  const pp = await probe.newPage();
  await pp.goto(B + '/');
  const all = [...seen.values()];
  const valid = await pp.evaluate(d => d.map(([p, v]) => CSS.supports(p, v)), all);
  await probe.close();
  const decls = all.filter((_, i) => valid[i]);
  assert(decls.length > 80, `${decls.length} different declarations with a viewport length are written in ${files.length} files`);
  const src = `<!doctype html><html><head><meta name=viewport content="width=device-width,initial-scale=1">
<script src="/lib/pagezoom.js"></script><style>body{margin:0}
${decls.map(([p, v], i) => `.u${i}{${p}:${v}}`).join('\n')}
@media (min-width:1px){.mq{width:50vw}}</style></head><body>
${decls.map((_, i) => `<div class="u${i}" style="position:absolute;left:0;top:0"></div>`).join('')}
<div class="mq" style="position:absolute"></div>
<div id="inl" style="position:absolute;width:30vw;height:calc(100vh - 20px)"></div></body></html>`;
  const computed = async (zoom, w, h) => {
    const ctx = await browser.newContext({viewport: {width: w, height: h}});
    const page = await ctx.newPage();
    await page.route(B + '/__units', r => r.fulfill({contentType: 'text/html', body: src}));
    await ctx.addInitScript(z => { if (z !== 100) localStorage.setItem('parseh_zoom', String(z)); }, zoom);
    await page.goto(B + '/__units');
    const got = await page.evaluate(d => d.map(([p], i) => getComputedStyle(document.querySelector('.u' + i)).getPropertyValue(p)), decls);
    const extra = await page.evaluate(() => [getComputedStyle(document.querySelector('.mq')).width,
      getComputedStyle(document.getElementById('inl')).width, getComputedStyle(document.getElementById('inl')).height]);
    const zoomed = await page.evaluate(() => ParsehZoom.applied());
    await ctx.close();
    return {got, extra, zoomed};
  };
  const ref = await computed(100, 800, 600);
  // a page at z % in a window z/100 times the size is the page at 100 % in 800 px, z/100 times as big
  for (const [z, w, h] of [[150, 1200, 900], [125, 1000, 750], [200, 1600, 1200], [175, 1400, 1050], [70, 560, 420], [90, 720, 540]]) {
    const at = await computed(z, w, h);
    const bad = decls.map((d, i) => [d, ref.got[i], at.got[i]])
      .filter(([, a, b]) => a !== b && !(a.endsWith('px') && b.endsWith('px') && near(parseFloat(a), parseFloat(b), 0.06)));
    assert(bad.length === 0, `${decls.length} declarations at ${z} % in a ${w} px window compute as at 100 % in 800 px` +
           (bad.length ? ' -- differ: ' + J(bad.slice(0, 5)) : ''));
    eq([at.extra, at.zoomed], [ref.extra, z], `and so do a rule in a nested @media and a style attribute (${z} %)`);
  }
}

// ======== pages ========
// every kind of page, in force with no sideways scroll
const PAGES = [
  ['the hub', '/'], ['the book library', '/books/'], ['the video library', '/youtube/'], ['the studio library', '/studio/'],
  ['the exercise decks', '/exercises/'], ['Settings', '/settings/'],
  ['a reader (English)', READER], ['a reader (Persian, right to left)', MADE.readers.fa], ['a reader (Japanese)', MADE.readers.ja],
  ['the player', VIDEO], ['a document', DOC], ['the editor', DOC + '/edit'], ['a deck', DECK], ['study', DECK + 'study'], ['cram', DECK + 'cram'],
];
const slug = s => s.replace(/[^a-z0-9]+/gi, '-').replace(/^-|-$/g, '').toLowerCase();
// no sideways scroll, and a glass the page does not widen
async function fits(page, device, tag) {
  const r = await page.evaluate(() => {
    const de = document.documentElement, f = ParsehZoom.factor();
    window.scrollTo(5000, scrollY);
    const x = scrollX;
    window.scrollTo(0, scrollY);
    return {over: de.scrollWidth - innerWidth, x, glass: innerWidth * f, scale: visualViewport.scale};
  });
  assert(r.over <= 0.6 && r.x === 0, `${tag}: no sideways scroll (${r.over.toFixed(1)} over, scrolled to ${r.x})`);
  assert(near(r.glass, device, 1.5) && near(r.scale, 1, 0.01),
         `${tag}: laid out in the glass as it is (${r.glass.toFixed(1)} px of ${device}), not widened to fit`);
}
async function partPages() {
  console.log('\n== every kind of page, at every zoom');
  for (const [name, path] of PAGES) {
    for (const z of [100, 125, 150, 200]) {
      const page = await open(DESK, 'pages ' + name, {zoom: z});
      await go(page, path);
      await sleep(250);
      const s = await state(page);
      assert(s.applied === z && (z === 100 || (s.zoom === String(z / 100) && s.dz === String(z))), `${name} on a desktop at ${z} %: in force`);
      await fits(page, 1280, `${name}, desktop ${z} %`);
      await shot(page, `${slug(name)}-desktop-${z}`);
      await closeAll(page);
    }
  }
  // a phone: the mobile mode is what a phone reads in; the largest step it allows is 110, a larger choice is given that
  for (const [name, path] of PAGES) {
    for (const [z, want] of [[100, 100], [110, 110], [150, 110]]) {
      const page = await open(PHONE, 'pages phone ' + name, {zoom: z, mode: 'mobile'});
      await go(page, path);
      await sleep(250);
      const s = await state(page);
      assert(s.applied === want && s.chosen === z, `${name} on a phone at ${z} %: ${want} % in force, ${z} kept`);
      await fits(page, 390, `${name}, phone ${z} %`);
      if (z === 110) await shot(page, `${slug(name)}-phone-110`);
      await closeAll(page);
    }
  }
  // a tablet takes more of it; the three themes read the same
  for (const [name, path] of [['a reader', READER], ['the player', VIDEO], ['a document', DOC], ['the hub', '/']]) {
    for (const theme of ['light', 'dark', 'sepia']) {
      const page = await open(TABLET, 'pages tablet ' + name, {zoom: 175, mode: 'mobile'});
      await go(page, path);
      // the person's theme, as the toolbox keeps it (the studio's pages read the same key)
      await page.evaluate(t => {
        if (window.Parseh) Parseh.theme.set(t);
        else { localStorage.setItem('parseh_theme', t); document.documentElement.setAttribute('data-theme', t); }
      }, theme);
      await sleep(250);
      eq(await page.evaluate(() => document.documentElement.getAttribute('data-theme')), theme, `${name} on a tablet wears the ${theme} theme`);
      eq((await state(page)).applied, 175, `${name} on a tablet, ${theme}: 175 % in force (820 px / 1.75 is 468 of the page's)`);
      await fits(page, 820, `${name}, tablet, ${theme}`);
      if (theme === 'dark') await shot(page, `${slug(name)}-tablet-175-dark`);
      await closeAll(page);
    }
  }
}

// ======== clouds ========
// the room the bars leave: the lowest edge of what is pinned to the top of the
// window, and the highest of what is pinned to its foot (in the glass's px)
const room = page => page.evaluate(() => {
  const f = ParsehZoom.factor();
  // (the visual viewport answers in the page's px, as everything does; the glass is `f` times that)
  const W = visualViewport.width * visualViewport.scale * f, H = visualViewport.height * visualViewport.scale * f;
  let top = 0, bottom = H;
  for (const el of document.querySelectorAll('body *')) {
    const cs = getComputedStyle(el);
    if (cs.position !== 'fixed' && cs.position !== 'sticky') continue;
    if (cs.visibility === 'hidden' || cs.display === 'none') continue;
    const r = el.getBoundingClientRect();
    if (r.width * f < W * 0.4 || r.height === 0) continue;
    // whatever is pinned in the top half -- a bar, and under it a video held in view -- covers what is behind it
    if (r.top * f < H * 0.5 && r.bottom * f < H * 0.92) top = Math.max(top, r.bottom * f);
    if (r.bottom * f >= H - 2 && r.top * f > H * 0.5) bottom = Math.min(bottom, r.top * f);
  }
  return {top, bottom, H, W};
});
// the page stands still: a player scrolls itself to the caption being said, and a chunk measured
// while that goes on is somewhere else by the time the mouse is on it
async function still(page) {
  for (let last = null, i = 0; i < 50; i++) {
    const y = await page.evaluate(() => scrollY);
    if (y === last) return;
    last = y;
    await sleep(150);
  }
}
// the nth `sel`, brought to the middle of the room the bars leave, where the page can be scrolled so --
// measured again after each scroll, since a bar that sticks only when the page has moved takes room
// the first measure did not know of, until the middle of it is the thing itself and not a bar over it
async function centre(page, sel, n) {
  await still(page);
  const target = page.locator(sel).nth(n);
  for (let i = 0; i < 4; i++) {
    const r = await room(page);
    await target.evaluate((el, mid) => {
      const f = ParsehZoom.factor(), b = el.getBoundingClientRect();
      scrollBy(0, b.top + b.height / 2 - mid / f);
    }, (r.top + r.bottom) / 2);
    await still(page);
    const bare = await target.evaluate(el => {
      const r0 = el.getClientRects()[0], e = document.elementFromPoint(r0.left + r0.width / 2, r0.top + r0.height / 2);
      return !!e && (e === el || el.contains(e));
    });
    if (bare) break;
  }
  return target;
}
// where the cloud that `trigger` opens stands, beside `target`, in the PAGE's px (the box divided by the zoom)
async function cloudBeside(page, target, trigger, cloudSel) {
  const tb = await target.boundingBox();
  // the middle of its first line (a chunk that wraps is two boxes, and the middle of both is between them)
  const pt = await target.evaluate(el => {
    const r = el.getClientRects()[0], f = ParsehZoom.factor();
    return {x: (r.left + r.width / 2) * f, y: (r.top + r.height / 2) * f};
  });
  await trigger(pt);
  await page.waitForSelector(cloudSel, {state: 'visible', timeout: 8000});
  await sleep(450);
  const cb = await page.locator(cloudSel).first().boundingBox();
  const f = (await state(page)).factor, [W, H] = await glass(page);
  const above = cb.y + cb.height <= tb.y + 1;
  return {dx: (cb.x - tb.x) / f, gap: (above ? tb.y - (cb.y + cb.height) : cb.y - (tb.y + tb.height)) / f, above, w: cb.width / f,
          inside: cb.x >= -0.5 && cb.y >= -0.5 && cb.x + cb.width <= W + 0.5 && cb.y + cb.height <= H + 0.5, cb};
}
async function partClouds() {
  console.log('\n== clouds beside what they are about');
  const cases = [
    {name: 'the reader\'s gloss cloud', path: READER, cloud: '#cloud', tol: 2,
     prep: p => p.locator('#hovermode').click(),
     pick: p => centre(p, 'main .p1 .w', 1), go: (p, pt) => p.mouse.move(pt.x, pt.y)},
    {name: 'the player\'s gloss cloud', path: VIDEO, cloud: '#cloud', tol: 2,
     prep: p => p.waitForFunction(() => document.querySelectorAll('#segs .seg .w').length > 0),
     pick: p => centre(p, '#segs .seg .w', 0), go: (p, pt) => p.mouse.move(pt.x, pt.y)},
    {name: 'the studio\'s word cloud (a blank)', path: DOC, cloud: 'article.sheet .ex-cloud', tol: 3,
     prep: p => p.waitForSelector('article.sheet .ex-blank'),
     pick: p => centre(p, 'article.sheet .ex-blank', 0), go: (p, pt) => p.mouse.click(pt.x, pt.y)},
  ];
  for (const c of cases) {
    let ref = null;
    for (const z of [100, 125, 150, 200]) {
      const page = await open(DESK, 'clouds ' + c.name, {zoom: z});
      await go(page, c.path);
      await sleep(400);
      await c.prep(page);
      const target = await c.pick(page);
      const m = await cloudBeside(page, target, pt => c.go(page, pt), c.cloud);
      assert(m.inside, `${c.name} at ${z} %: inside the window (${J([m.cb.x, m.cb.y, m.cb.width, m.cb.height].map(v => Math.round(v)))})`);
      assert(m.gap >= -1 && m.gap <= 16, `${c.name} at ${z} %: beside what it is about, ${m.above ? 'above' : 'below'}, ${m.gap.toFixed(1)} px of the page away`);
      if (z === 100) ref = m;
      else {
        assert(near(m.dx, ref.dx, c.tol) && near(m.w, ref.w, 6),
               `${c.name} at ${z} %: ${m.dx.toFixed(1)} px of the page across from it as at 100 % (${ref.dx.toFixed(1)}), as wide (${m.w.toFixed(0)} against ${ref.w.toFixed(0)})`);
        assert(near(m.gap, ref.gap, c.tol + 0.5) || m.above !== ref.above,
               `${c.name} at ${z} %: ${m.gap.toFixed(1)} px away on its side as at 100 % (${ref.gap.toFixed(1)})`);
      }
      if (z === 150) await shot(page, 'cloud-' + slug(c.name) + '-150');
      await closeAll(page);
    }
  }

  // ---- the phone's dictionary sheet clears the chunk it is about
  console.log('\n== the dictionary\'s sheet clears the chunk');
  for (const [opts, name, zooms] of [[PHONE, 'phone', [100, 110]], [TABLET, 'tablet', [100, 150, 200]]]) {
    for (const [path, sel, what] of [[READER, 'main .p1 .w', 'a book'], [VIDEO, '#segs .seg .w', 'a video']]) {
      for (const z of zooms) {
        const page = await open(opts, 'sheet', {zoom: z, mode: 'mobile'});
        await go(page, path);
        await sleep(500);
        if (await page.$('.pf-bar')) await page.locator('.pf-stay').first().tap();
        await page.waitForSelector(sel);
        const n = await page.locator(sel).count();
        const target = page.locator(sel).nth(n - 1);
        // the last of the page, low on the screen, as a thumb finds it
        await target.evaluate(e => { const r = e.getBoundingClientRect(); scrollBy(0, r.top - innerHeight * 0.74); });
        await sleep(400);
        const before = await target.boundingBox();
        // an entry 45 % of the window tall, whatever the window is in its own px
        // (a video's page tells the sheet what it pins over the text, as the page's own call does)
        await page.evaluate(([sel, pinned]) => {
          const all = document.querySelectorAll(sel), entry = document.createElement('div');
          entry.textContent = 'an entry for the word';
          entry.style.cssText = 'font-size:14px;height:' + Math.round(innerHeight * 0.45) + 'px';
          Parseh.dictSheet({box: entry, lang: {code: 'en', dir: 'ltr'}, title: 'zoom', anchor: all[all.length - 1], pinned});
        }, [sel, what === 'a video' ? ['header', '#playerwrap'] : undefined]);
        await sleep(900);
        const after = await target.boundingBox();
        const sheet = await page.locator('.m-dsheet').boundingBox();
        const pinnedVideo = what === 'a video' ? await box(page, '#playerwrap') : null;
        const H = opts.viewport.height;
        assert(sheet.y + sheet.height <= H + 1 && sheet.y >= -1, `${what}, ${name} at ${z} %: the sheet stands inside the screen (top ${sheet.y.toFixed(0)}, ${sheet.height.toFixed(0)} tall)`);
        assert(before.y + before.height > sheet.y, `${what}, ${name} at ${z} %: the chunk was under where the sheet comes (${before.y.toFixed(0)} against ${sheet.y.toFixed(0)})`);
        // THE ROOM between what is pinned over the text (a video, on a video's page) and the sheet: where the chunk
        // fits in it, the page is scrolled to put it there, below the video and above the sheet; where it does not
        // -- the owner's rule of 2026-09-25: the sheet is as tall as its entry and covers the word where it must --
        // the page is not moved at all.  A tablet at 200 % has a video and a bar over 60 % of the screen: no room
        const ceil = pinnedVideo ? pinnedVideo.y + pinnedVideo.height : 0, room = sheet.y - ceil, need = before.height + 12;
        if (room >= need + 8) {
          assert(after.y + after.height <= sheet.y - 4 && after.y >= ceil - 1,
                 `${what}, ${name} at ${z} %: the room is ${room.toFixed(0)} px and the chunk is cleared of the sheet, scrolled into it, below what is pinned (${after.y.toFixed(0)}..${(after.y + after.height).toFixed(0)} between ${ceil.toFixed(0)} and ${sheet.y.toFixed(0)})`);
        } else if (room < need - 8) {
          assert(near(after.y, before.y, 2), `${what}, ${name} at ${z} %: there is no room (${room.toFixed(0)} px for a chunk that needs ${need.toFixed(0)}): the page is not moved, as the rule says (${before.y.toFixed(0)} -> ${after.y.toFixed(0)})`);
        } else assert(true, `${what}, ${name} at ${z} %: ${room.toFixed(0)} px of room for ${need.toFixed(0)}: on the line, nothing asked`);
        if (z === zooms[zooms.length - 1]) await shot(page, `dictionary-sheet-${name}-${z}-${slug(what)}`);
        await closeAll(page);
      }
    }
  }

}

// ======== pointer ========
// a real pointer over a control is over it, as the page's own elementFromPoint() says
async function partPointer() {
  console.log('\n== a pointer at a control\'s middle is over it, and the page says so');
  for (const [path, name, ctrl] of [[READER, 'the reader', '#loop'], [VIDEO, 'the player', '#follow'], [DOC, 'the document', '#btn-toc'], [DECK, 'a deck', '#btn-study']]) {
    for (const z of [100, 125, 150, 200]) {
      const page = await open(DESK, 'click ' + name, {zoom: z});
      await go(page, path);
      await sleep(300);
      const [W, H] = await glass(page);
      await page.evaluate(() => {
        window.__hit = []; window.__over = null;
        document.addEventListener('click', e => { const c = e.target.closest('[id]'); __hit.push(c ? c.id : e.target.tagName); }, true);
        document.addEventListener('mousemove', e => { __over = {t: e.target, x: e.clientX, y: e.clientY}; }, true);
      });
      const ids = await page.evaluate(() => [...document.querySelectorAll('header button[id], header a[id], .topbar button[id], .topbar a[id]')]
        .filter(b => b.getClientRects().length && getComputedStyle(b).visibility !== 'hidden' && !b.disabled).map(b => b.id));
      let over = 0, tried = 0, same = 0;
      for (const id of ids.slice(0, 40)) {
        const b = await box(page, '#' + id.replace(/([^a-zA-Z0-9_-])/g, '\\$1'));
        // the middle of what is drawn inside the window (a menu closed in its own corner is not on the bar)
        if (!b || b.x < 0 || b.x + b.width > W || b.y < 0 || b.y + b.height > H) continue;
        await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2);
        // the browser says what is under the pointer (the target of its mousemove), the page asks the same
        // with the point the event gave it, in the page's px
        const r = await page.evaluate(() => {
          const o = __over, found = document.elementFromPoint(o.x, o.y), c = o.t.closest('[id]');
          return {same: found === o.t, id: c ? c.id : ''};
        });
        tried++;
        if (r.same) same++;
        if (r.id === id) over++;
      }
      assert(tried >= 1 && same === tried, `${name} at ${z} %: elementFromPoint(clientX, clientY) of a real pointer is the very element the browser put it over, for each of ${tried} controls (${same})`);
      assert(over >= Math.min(3, tried), `${name} at ${z} %: and ${over} of them are what the pointer at their middle is over: the bar's own controls`);
      // and the browser's own click, on one that does something to be seen
      const tb = await box(page, ctrl);
      if (tb && tb.x >= 0 && tb.x + tb.width <= W && tb.y >= 0 && tb.y + tb.height <= H) {
        const was = await page.locator(ctrl).first().evaluate(e => e.className + '|' + e.getAttribute('aria-pressed'));
        const where = page.url();
        await page.mouse.click(tb.x + tb.width / 2, tb.y + tb.height / 2);
        await sleep(500);
        // (a control that is a link has left the page, and its own click with it: the page is another)
        let hit;
        try { hit = await page.evaluate(() => __hit.slice(-1)[0]); } catch (e) { hit = page.url() !== where ? ctrl.slice(1) : null; }
        eq(hit, ctrl.slice(1), `${name} at ${z} %: a real click at the middle of ${ctrl} lands on it (it was ${was})`);
      }
      await closeAll(page);
    }
  }
}

// ======== strip ========
async function partStrip() {
  console.log('\n== the timeline\'s strip maps a drag to the same time at every zoom');
  const secs = s => String(s).trim().split(':').reduce((a, b) => a * 60 + +b, 0);
  const results = [];
  for (const z of [100, 125, 150, 200]) {
    const page = await open(DESK, 'strip', {zoom: z});
    await go(page, READER);
    await page.waitForFunction(() => typeof SUBS !== 'undefined' && document.querySelector('.sub'));
    // the window is half bars at the larger steps: put them away, as a person does
    await page.locator('#bars').click();
    await sleep(300);
    await page.locator('.sub').nth(3).click();
    await page.waitForFunction(() => document.querySelector('.sub[data-s="3"].on-air'));
    await page.evaluate(() => document.getElementById('editbyear').click());
    await page.waitForSelector('.tl-root');
    await page.waitForFunction(() => document.querySelectorAll('.tl-band').length > 0);
    await page.waitForFunction(() => document.querySelector('.tl-strip.tl-drawn'), null, {timeout: 20000});
    await sleep(300);
    const i0 = await page.locator('.tl-band').first().getAttribute('data-i');
    const i1 = String(Number(i0) + 1);
    const nums = async i => {
      await page.locator(`.tl-band[data-i="${i}"]`).click();
      return await page.evaluate(() => [...document.querySelectorAll('.tl-at')].map(n => n.value.split(':').reduce((a, b) => a * 60 + +b, 0)));
    };
    const was1 = await nums(i1);
    await nums(i0);
    const sb = await box(page, '.tl-strip');
    const labels = await page.evaluate(() => [...document.querySelectorAll('.tl-t')].map(n => n.textContent));
    const span = secs(labels[1]) - secs(labels[0]);
    const edge = await box(page, `.tl-edge[data-who="e"][data-i="${i0}"]`);
    const ex = edge.x + edge.width / 2, ey = edge.y + edge.height / 2;
    // dragged to 62 % of the strip, whatever it is drawn as wide as
    const dropAt = sb.x + sb.width * 0.62;
    await page.mouse.move(ex, ey);
    await page.mouse.down();
    await page.mouse.move((ex + dropAt) / 2, ey, {steps: 5});
    await page.mouse.move(dropAt, ey, {steps: 4});
    await page.mouse.up();
    const now0 = await nums(i0), now1 = await nums(i1);
    const want = secs(labels[0]) + 0.62 * span;
    assert(near(now0[1], want, 0.2), `at ${z} %: the edge dropped at 62 % of the strip (${labels[0]}..${labels[1]}, ${sb.width.toFixed(0)} px wide) is at ${now0[1].toFixed(2)} s, wanted ${want.toFixed(2)}`);
    assert(near(now1[0], now0[1], 0.001) && near(now1[1], was1[1], 0.001), `at ${z} %: both numbers moved by the one act, the far end stayed`);
    results.push(now0[1]);
    // and the picture of the sound is drawn in the glass's own pixels
    const wave = await page.evaluate(() => document.querySelector('.tl-wave').width);
    const wb = await box(page, '.tl-wave');
    assert(near(wave, wb.width, 3), `at ${z} %: the picture of the sound is ${wave} px for a canvas ${wb.width.toFixed(0)} px wide on the glass`);
    if (z === 150) await shot(page, 'timeline-150');
    await closeAll(page);
  }
  assert(results.every(r => near(r, results[0], 0.25)), `the same drop is the same time at every zoom: ${J(results.map(r => +r.toFixed(2)))}`);
}

// ======== fixed ========
async function insideWindow(page, tag, least = 0) {
  const bad = await page.evaluate(() => {
    const f = ParsehZoom.factor(), out = [], n = [];
    const W = visualViewport.width * visualViewport.scale * f, H = visualViewport.height * visualViewport.scale * f;
    for (const el of document.querySelectorAll('body *')) {
      const cs = getComputedStyle(el);
      if (cs.position !== 'fixed') continue;
      if (cs.visibility === 'hidden' || cs.display === 'none' || parseFloat(cs.opacity) === 0) continue;
      const r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) continue;
      const l = r.left * f, rt = r.right * f, t = r.top * f, b = r.bottom * f;
      // wholly off the screen is a thing put away (a bar, a skip link); partly off is the fault
      if (rt <= 0 || l >= W || b <= 0 || t >= H) continue;
      n.push(el.id || el.className || el.tagName);
      if (rt > W + 1.5 || l < -1.5 || b > H + 1.5 || t < -1.5)
        out.push((el.id || el.className || el.tagName) + ' ' + [l, t, rt, b].map(Math.round).join(','));
    }
    return {out, n: n.length};
  });
  assert(bad.out.length === 0 && bad.n >= least, `${tag}: all ${bad.n} fixed things on the screen are inside the window` + (bad.out.length ? ' -- not: ' + J(bad.out) : ''));
}
async function partFixed() {
  console.log('\n== bars, sheets and the dock stay inside the window');
  for (const [name, path, least] of [['the reader', READER, 1], ['the player', VIDEO, 1], ['a document', DOC, 0], ['a deck', DECK, 0], ['cram', DECK + 'cram', 0], ['the hub', '/', 0]]) {
    for (const z of [100, 125, 150, 200]) {
      const page = await open(DESK, 'fixed ' + name, {zoom: z});
      await go(page, path);
      await sleep(300);
      await insideWindow(page, `${name}, desktop ${z} %`, least);
      await closeAll(page);
    }
    for (const z of [100, 110]) {
      const page = await open(PHONE, 'fixed phone ' + name, {zoom: z, mode: 'mobile'});
      await go(page, path);
      await sleep(300);
      await insideWindow(page, `${name}, phone ${z} %`, least);
      await closeAll(page);
    }
  }
  // the dictionary's sheet and a toast over a reader, upright and held sideways
  for (const [opts, z] of [[PHONE, 110], [LAND, 200], [TABLET, 175]]) {
    const page = await open(opts, 'sheet fixed', {zoom: z, mode: 'mobile'});
    await go(page, READER);
    await sleep(500);
    if (await page.$('.pf-bar')) await page.locator('.pf-stay').first().tap();
    await page.evaluate(() => {
      const all = document.querySelectorAll('main .p1 .w'), entry = document.createElement('div');
      entry.textContent = 'an entry for the word, '.repeat(200);
      Parseh.dictSheet({box: entry, lang: {code: 'en', dir: 'ltr'}, title: 'zoom', anchor: all[all.length - 1]});
      Parseh.toast('a toast, over everything');
    });
    await sleep(800);
    await insideWindow(page, `the dictionary's sheet and a toast over a reader, ${opts.viewport.width}x${opts.viewport.height} at ${z} %`, 2);
    await shot(page, `sheet-${opts.viewport.width}-${z}`);
    await closeAll(page);
  }
}

// ======== app ========
// the installed app: no browser chrome, no Ctrl+ and Ctrl-, so this is the only zoom it has
async function partApp() {
  console.log('\n== the installed app (display-mode: standalone)');
  const page = await open(PHONE, 'app', {zoom: 110, mode: 'mobile'});
  // A headless browser cannot be started as an installed app and CDP has no display-mode to emulate, so the two
  // things a page asks to know it is one are answered as an app answers them: the media query, and the flag
  // an iPad's home-screen app has.  (The zoom itself asks neither; this is the app's own pages in its own state.)
  await page.addInitScript(() => {
    const real = window.matchMedia.bind(window);
    window.matchMedia = q => {
      const m = real(/display-mode/.test(q) ? 'all' : q);
      if (/display-mode:\s*standalone/.test(q)) Object.defineProperty(m, 'matches', {value: true});
      return m;
    };
    Object.defineProperty(navigator, 'standalone', {value: true, configurable: true});
  });
  await go(page, '/?mode=mobile');
  eq(await page.evaluate(() => [Parseh.app.standalone(), matchMedia('(display-mode: standalone)').matches]), [true, true],
     'the page is the installed app');
  eq((await state(page)).applied, 110, 'and is zoomed to the step that was chosen');
  for (const [name, path] of [['the mobile hub', '/'], ['the book shelf', '/m/books/'], ['a book', READER], ['a video', VIDEO], ['the decks', '/exercises/'], ['a deck', DECK]]) {
    await go(page, path);
    await sleep(300);
    const s = await state(page);
    assert(s.applied === 110 && s.dz === '110', `the app, ${name}: 110 % in force, carried from page to page`);
    await fits(page, 390, `the app, ${name}`);
    await insideWindow(page, `the app, ${name}`, name === 'a book' || name === 'a video' ? 1 : 0);
  }
  eq(await page.evaluate(() => [ParsehZoom.can(1), ParsehZoom.set(100), ParsehZoom.applied(), document.documentElement.getAttribute('style')]),
     [NARROW, true, 100, null], 'where there is no key to press, the page\'s own steps put it back to 100 %, and take it all off');
  await closeAll(page);
}

try {
  if (PARTS.includes('contract')) { await partContract(); await partRefusals(); await partLate(); }
  if (PARTS.includes('units')) await partUnits();
  if (PARTS.includes('pages')) await partPages();
  if (PARTS.includes('clouds')) await partClouds();
  if (PARTS.includes('pointer')) await partPointer();
  if (PARTS.includes('strip')) await partStrip();
  if (PARTS.includes('fixed')) await partFixed();
  if (PARTS.includes('app')) await partApp();
} finally {
  await browser.close();
  hub.kill('SIGTERM');
  await hub.status;
  await Deno.remove(WORK, {recursive: true}).catch(() => {});
}
if (errors.length) { console.log('\npage errors:\n  ' + errors.join('\n  ')); Deno.exit(1); }
console.log(`\n${passed} passed`);

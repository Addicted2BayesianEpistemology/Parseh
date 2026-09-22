// Browser test of the mobile mode (docs/mobile.md), in two parts.
//
// api -- Parseh.mode itself (lib/parseh.js), on bare pages that load the
// script and nothing else, answered here (page.route):
//   a) with nothing stored the mode is browser, put on <html> before the body
//      is parsed and mirrored in the cookie; set() stores it in both, marks
//      the switch's buttons and tells onChange, and ignores anything but the
//      two modes; a reload opens in it; with nothing in localStorage the
//      cookie answers
//   b) on a mobile page, in the mobile mode, a link goes where route() says:
//      its href is rewritten in the capture phase -- for a click, a middle
//      click and a context menu alike, the query and the fragment kept --
//      but never a download, a data-no-route link, a fragment or another
//      site's; nothing is routed on a page that is not a mobile page nor in
//      the browser mode; back to browser, every link has its own address
//      again; a real click lands on the mobile page
//   c) a second tab follows a switch made in the first
//
// hub -- against the REAL hub (serve.main, booted by tests/cardkit_harness.py
// serve) over a temporary toolbox: one studio note in every language of the
// registry, so that the hub has a chip for each, and a book library page
// written by make_index.py into the temporary tree.  Measured where the page
// is drawn -- computed display, bounding rects, elementFromPoint -- at
// 390x844 on a touch screen (Chromium's phone emulation) and at 1280x800
// with a mouse:
//   a) the hub opens in the browser mode, its browser layout the one on the
//      screen, the switch at the top saying so; the doors it shows are noted
//   b) Mobile, clicked: the mobile layout is the one on the screen and the
//      browser one is not; everything on it that can be tapped is the home
//      link, the switch, the theme, the chips, four doors, the guide and the app's --
//      no stop button, no Anki, no clip tray, no dictionaries, no address --
//      each door at least 48px high, inside the screen and reached by a tap
//      on it, with its counts; the page never scrolls sideways, the chips
//      do on the phone, and wrap for the mouse, which reaches every one with
//      a plain click; a chip rewrites the doors' counts; the picked chip is
//      in view, however far along the row, after a reload, after the switch
//      and after a tap on a chip at the row's edge; on a desktop the column
//      is narrow and in the middle
//   c) the choice is kept: in localStorage and in a cookie, which the server
//      is sent; a reload is still mobile; the Books door lands on the mobile
//      shelf, /m/books/, sending the cookie; the Videos door on the video
//      index, the browser page as it is (no mobile version of it yet), whose
//      home link comes back to the mobile hub; so is a second tab, which
//      follows a switch made in the first
//   d) a door goes through Parseh.mode.route: with nothing registered it
//      lands on the browser page, and the registry says where the library, a
//      reader and the decks go (tests/mobile_pages.mjs drives those pages);
//      with a mobile version registered it lands there, and so does a
//      ctrl-click, in a new tab
//   e) Browser, clicked: the browser hub is back, its visible doors the same
//      set as in a), and drawn pixel for pixel as it was before the switch
//   f) the bar that hides on a phone scroll still does, in both modes; and
//      in the three palettes every text of the mobile hub is readable
//   g) from 320 to 430px each layout's bar is one row, all of it on the
//      screen (the browser one from 340px: at 320 it had two rows before the
//      switch was in it), the mobile bar's controls 48x48 at least; what the
//      browser bar sheds on a phone is still named for a screen reader, and
//      at 1280px it sheds nothing
//   CHROME_BIN=... PARSEH_PYTHON=python3 deno run --allow-all tests/mobile_mode.mjs
//   MOBILE_PARTS=api (or hub) runs one part; SHOTS=<dir> saves the hub's
//   screenshots (each width, each palette, each mode)
import { chromium } from 'npm:playwright-core@1.52.0';

const root = await Deno.realPath(new URL('..', import.meta.url));
Deno.chdir(root);
const PY = Deno.env.get('PARSEH_PYTHON') || 'python3';
const SHOTS = Deno.env.get('SHOTS') || '';
const td = new TextDecoder();
let passed = 0;
const assert = (v, m) => { if (!v) throw Error('FAIL: ' + m); passed++; console.log('  ok', m); };
const eq = (got, want, m) => assert(JSON.stringify(got) === JSON.stringify(want),
  m + (JSON.stringify(got) === JSON.stringify(want) ? '' : ': got ' + JSON.stringify(got) + ' want ' + JSON.stringify(want)));
const sleep = ms => new Promise(r => setTimeout(r, ms));
function freePort() {
  const l = Deno.listen({hostname: '127.0.0.1', port: 0});
  const p = l.addr.port;
  l.close();
  return p;
}
async function py(code, ...args) {
  const o = await new Deno.Command(PY, {args: ['-c', code, ...args], cwd: root, stdout: 'piped', stderr: 'piped'}).output();
  if (!o.success) throw Error(td.decode(o.stderr) || td.decode(o.stdout));
  return td.decode(o.stdout);
}
const PARTS = (Deno.env.get('MOBILE_PARTS') || 'api,hub').split(',');
const browser = await chromium.launch({executablePath: Deno.env.get('CHROME_BIN'), headless: true});
const errors = [];

// ======== api: Parseh.mode on bare pages ========
async function partApi() {
  console.log('\n== api: Parseh.mode on bare pages');
  const O = 'http://parseh.test';
  const JS = await Deno.readTextFile(root + '/lib/parseh.js');
  // a page that loads parseh.js and nothing else; the first thing in its
  // body notes what <html> says by then
  const html = (body, mobile) => '<!doctype html><html lang="en"><head><meta charset="utf-8">' +
    '<script src="/lib/parseh.js"></script></head><body' + (mobile ? ' data-mobile-page' : '') + '>' +
    '<script>window.early = document.documentElement.getAttribute("data-mode");</script>' + body + '</body></html>';
  const LINKS = '<span class="parseh-mode"><button type="button" data-parseh-mode="browser" aria-pressed="true">' +
    'Browser</button><button type="button" data-parseh-mode="mobile" aria-pressed="false">Mobile</button></span>' +
    '<a id="plain" href="/youtube/">videos</a> <a id="query" href="/youtube/?q=1#t">q</a> ' +
    '<a id="menu" href="/youtube/">menu</a> <a id="dl" href="/youtube/" download>dl</a> ' +
    '<a id="no" href="/youtube/" data-no-route>no</a> <a id="frag" href="#top">frag</a> ' +
    '<a id="ext" href="https://example.org/youtube/">ext</a>';
  const PAGES = {'/': html(LINKS, true), '/plain/': html(LINKS, false),
                 '/youtube/': html('the browser page', false), '/m/v/': html('the mobile page', true)};
  const ctx = await browser.newContext();
  await ctx.route(O + '/**', r => {
    const u = new URL(r.request().url());
    if (u.pathname === '/lib/parseh.js') return r.fulfill({body: JS, contentType: 'text/javascript'});
    const body = PAGES[u.pathname];
    return body ? r.fulfill({body, contentType: 'text/html'}) : r.fulfill({status: 404, body: 'nothing here'});
  });
  const page = await ctx.newPage();
  page.on('pageerror', e => { errors.push('api: ' + e.message); console.log('PAGE ERROR', e.message); });
  const state = p => p.evaluate(() => ({
    mode: document.documentElement.getAttribute('data-mode'), early: window.early, get: Parseh.mode.get(),
    stored: localStorage.getItem('parseh_mode'), cookie: document.cookie,
    pressed: [...document.querySelectorAll('[data-parseh-mode]')].map(b => b.getAttribute('aria-pressed'))}));
  const cookie = async () => { const c = (await ctx.cookies(O)).find(c => c.name === 'parseh_mode'); return c && c.value; };

  // ---- a) stored, mirrored, applied early
  await page.goto(O + '/');
  let s = await state(page);
  eq([s.mode, s.early, s.get, s.stored, s.pressed], ['browser', 'browser', 'browser', null, ['true', 'false']],
     'nothing stored: browser, on <html> before the body was parsed, the switch saying so');
  eq(await cookie(), 'browser', 'and the cookie mirrors it');
  await page.evaluate(() => { window.changes = []; window.off = Parseh.mode.onChange(m => changes.push(m)); });
  await page.evaluate(() => Parseh.mode.set('mobile'));
  s = await state(page);
  eq([s.mode, s.get, s.stored, s.pressed], ['mobile', 'mobile', 'mobile', ['false', 'true']],
     'set("mobile"): <html data-mode>, localStorage and the buttons follow');
  eq([await cookie(), await page.evaluate(() => [Parseh.mode.isMobile(), changes])], ['mobile', [true, ['mobile']]],
     'the cookie too, isMobile() says so, and onChange was told once');
  await page.evaluate(() => { Parseh.mode.set('tablet'); Parseh.mode.set('mobile'); });
  eq(await page.evaluate(() => [Parseh.mode.get(), changes]), ['mobile', ['mobile']],
     'a mode that is not one is ignored, and setting the same one again tells nobody');
  await page.click('[data-parseh-mode=browser]');
  eq(await page.evaluate(() => [Parseh.mode.get(), changes]), ['browser', ['mobile', 'browser']],
     'a click on the Browser button switches back');
  await page.evaluate(() => { off(); Parseh.mode.set('mobile'); });
  eq(await page.evaluate(() => changes), ['mobile', 'browser'], 'and a listener taken off hears nothing more');
  await page.reload();
  s = await state(page);
  eq([s.early, s.mode, s.pressed], ['mobile', 'mobile', ['false', 'true']], 'reloaded: mobile, before the body was parsed');
  await page.evaluate(() => localStorage.removeItem('parseh_mode'));
  await page.reload();
  eq((await state(page)).early, 'mobile', 'nothing in localStorage: the cookie answers');
  await page.evaluate(() => { document.cookie = 'parseh_mode=; Path=/; Max-Age=0'; });
  await page.reload();
  s = await state(page);
  eq([s.early, s.stored, await cookie()], ['browser', null, 'browser'], 'neither: browser, and the cookie is written again');

  // ---- b) links on a mobile page
  // what a click would leave the href as: the page's own capture listener
  // runs, then this one keeps the browser from leaving
  const after = (p, id, type) => p.evaluate(([id, type]) => {
    const a = document.getElementById(id);
    const stop = e => e.preventDefault();
    document.addEventListener(type, stop);
    a.dispatchEvent(new MouseEvent(type, {bubbles: true, cancelable: true, button: type === 'auxclick' ? 1 : type === 'contextmenu' ? 2 : 0}));
    document.removeEventListener(type, stop);
    return [a.getAttribute('href'), a.getAttribute('data-parseh-href')];
  }, [id, type]);
  const register = p => p.evaluate(() => Parseh.mode.pages.push({match: /^\/youtube\/$/, to: '/m/v/'}));
  await page.evaluate(() => Parseh.mode.set('mobile'));
  eq(await after(page, 'plain', 'click'), ['/youtube/', null], 'nothing registered: a link keeps its address');
  await register(page);
  eq(await page.evaluate(() => [Parseh.mode.route('/youtube/'), Parseh.mode.route('/youtube/?q=1#t'), Parseh.mode.route('/'),
                                Parseh.mode.route('/studio/'), Parseh.mode.route('https://example.org/youtube/')]),
     ['/m/v/', '/m/v/?q=1#t', '/', '/studio/', 'https://example.org/youtube/'],
     'registered: route() answers the mobile address, the rest their own');
  eq(await after(page, 'plain', 'click'), ['/m/v/', '/youtube/'], 'a click: the href is the mobile address, its own kept beside it');
  eq(await after(page, 'query', 'auxclick'), ['/m/v/?q=1#t', '/youtube/?q=1#t'], 'a middle click too, the query and the fragment kept');
  eq(await after(page, 'menu', 'contextmenu'), ['/m/v/', '/youtube/'], 'and a context menu (a long press)');
  for (const id of ['dl', 'no', 'frag', 'ext'])
    eq((await after(page, id, 'click'))[1], null, `#${id}: never routed`);
  await page.evaluate(() => Parseh.mode.set('browser'));
  eq(await page.evaluate(() => [...document.querySelectorAll('a')].map(a => a.getAttribute('href'))
                                  .concat(document.querySelectorAll('[data-parseh-href]').length)),
     ['/youtube/', '/youtube/?q=1#t', '/youtube/', '/youtube/', '/youtube/', '#top', 'https://example.org/youtube/', 0],
     'back to browser: every link has its own address again');
  eq(await after(page, 'plain', 'click'), ['/youtube/', null], 'and in the browser mode nothing is routed');
  await page.goto(O + '/plain/');
  await page.evaluate(() => Parseh.mode.set('mobile'));
  await register(page);
  eq([await after(page, 'plain', 'click'), await page.evaluate(() => Parseh.mode.route('/youtube/'))], [['/youtube/', null], '/m/v/'],
     'a page that is not a mobile page routes none of its links (route() still answers)');
  await page.goto(O + '/');
  await register(page);
  await Promise.all([page.waitForURL(O + '/m/v/'), page.click('#plain')]);
  assert(true, 'a real click lands on the mobile page');

  // ---- c) another tab
  await page.goto(O + '/');
  const other = await ctx.newPage();
  await other.goto(O + '/plain/');
  await other.evaluate(() => { window.changes = []; Parseh.mode.onChange(m => changes.push(m)); });
  await page.click('[data-parseh-mode=browser]');
  await other.waitForFunction(() => document.documentElement.getAttribute('data-mode') === 'browser');
  eq(await other.evaluate(() => [changes, [...document.querySelectorAll('[data-parseh-mode]')].map(b => b.getAttribute('aria-pressed'))]),
     [['browser'], ['true', 'false']], 'a second tab follows a switch made in the first, and its listeners hear it');
  await ctx.close();
}

// ======== hub: the real hub ========

// ---- what the page shows, measured
// every element that can be clicked and is drawn, with where it is
const CLICKABLE = 'a[href], button, input, select, textarea, [tabindex], [contenteditable="true"]';
function snapshot(page) {
  return page.evaluate(sel => {
    const drawn = el => el.getClientRects().length > 0 && getComputedStyle(el).visibility !== 'hidden';
    const layout = which => [...document.querySelectorAll(`[data-layout=${which}]`)];
    const what = el => {
      const s = el.getAttribute('href') || el.getAttribute('data-parseh-mode') || el.getAttribute('data-pick') ||
        (el.hasAttribute('data-parseh-theme') ? 'theme' : el.hasAttribute('data-parseh-stop') ? 'stop' : '');
      return el.tagName.toLowerCase() + ':' + s;
    };
    return {
      mode: document.documentElement.getAttribute('data-mode'),
      stored: localStorage.getItem('parseh_mode'),
      cookie: document.cookie,
      browser: layout('browser').map(e => [drawn(e), getComputedStyle(e).display]),
      mobile: layout('mobile').map(e => [drawn(e), getComputedStyle(e).display]),
      clickable: [...document.querySelectorAll(sel)].filter(drawn).map(what),
      pressed: [...document.querySelectorAll('[data-parseh-mode]')].filter(drawn)
        .map(b => [b.getAttribute('data-parseh-mode'), b.getAttribute('aria-pressed'),
                   getComputedStyle(b).backgroundColor]),
      sideways: document.documentElement.scrollWidth - innerWidth,
      w: innerWidth, h: innerHeight,
    };
  }, CLICKABLE);
}
// a door of the mobile hub, where it is and what a tap on it reaches
const doors = page => page.evaluate(() => [...document.querySelectorAll('.hub-mobile a.m-door')].map(a => {
  const r = a.getBoundingClientRect();
  a.scrollIntoView({block: 'center'});
  const s = a.getBoundingClientRect();
  const hit = document.elementFromPoint(s.left + s.width / 2, s.top + s.height / 2);
  return {href: a.getAttribute('href'), l: r.left, r: r.right, h: r.height, w: r.width,
          hit: !!hit && (hit === a || a.contains(hit)),
          tags: [...a.querySelectorAll('.tag')].map(t => t.textContent),
          counted: [...a.querySelectorAll('.tag')].every(t => t.hasAttribute('data-counts'))};
}));
// A phone: a page with touch emulation (hasTouch, isMobile), which is what
// makes (pointer:coarse) and (hover:none) true.  Chromium's headless shell
// drops that whenever a screenshot resizes the page to take it -- a
// full-page or an element screenshot: the picture is drawn for a mouse, and
// the page answers (pointer:fine) from then on -- and has it back once it is
// said again over CDP.  So every screenshot goes through grab(), which says
// it again, and a phone's screenshots for SHOTS are of its screen only.
async function phone(page) {
  page.touch = await page.context().newCDPSession(page);
  await page.touch.send('Emulation.setTouchEmulationEnabled', {enabled: true, maxTouchPoints: 1});
}
async function grab(page, target, opts) {
  const png = await target.screenshot(opts);
  if (page.touch) await page.touch.send('Emulation.setTouchEmulationEnabled', {enabled: true, maxTouchPoints: 1});
  return png;
}
// main.hub, the whole of it, as a picture to compare: taken from the whole
// page rather than from the element, which would scroll the page to it and
// have a phone's sticky bar drawn over its top, or not, as the scroll left it
// (the browser layout it is taken of does not change with the pointer)
const hubPicture = async page => grab(page, page, {fullPage: true, clip: await page.evaluate(() => {
  const b = document.querySelector('main.hub').getBoundingClientRect();
  return {x: b.left + scrollX, y: b.top + scrollY, width: b.width, height: b.height};
})});
const shot = async (page, name) => {
  if (!SHOTS) return;
  await Deno.mkdir(SHOTS, {recursive: true});
  await grab(page, page, {path: `${SHOTS}/${name}.png`, fullPage: !page.touch});
};
const settle = page => page.evaluate(() => document.fonts.ready.then(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))));
const MOBILE_CLICKABLE = page => page.evaluate(() => ['a:/', 'button:browser', 'button:mobile', 'button:theme',
  ...[...document.querySelectorAll('.m-langs .chip')].map(c => 'button:' + c.getAttribute('data-pick')),
  'a:/books/', 'a:/youtube/', 'a:/studio/', 'a:/exercises/', 'a:/guide/', 'a:/m/install/']);

// the temporary toolbox: the tree hub_inbox.mjs boots, plus a note in every
// language and the book library page
const TREE = String.raw`
import json, sys
from pathlib import Path
sys.path[:0] = ['markdown/exlex', 'markdown/app', 'lib', '.']
import languages, store, make_index
store.LIB = Path(sys.argv[1]) / 'library'
for L in languages.LANGS.values():
    store.create('---\ntitle: A note in %s\ntarget: %s\n---\n\nSome text.\n' % (L.name, L.code))
# the library page as make_index.py writes it, into the temporary tree and
# linking the tree's lib/ -- the repository's books/ and lib/ are not touched
make_index.BOOKS_DIR = str(Path(sys.argv[1]) / 'root' / 'books')
make_index.LIB = str(Path(sys.argv[1]) / 'root' / 'lib')
make_index.all_books = lambda: []
languages.write_css = lambda *a, **k: None
import contextlib, io
with contextlib.redirect_stdout(io.StringIO()):
    make_index.main()
print(json.dumps(list(languages.LANGS)))
`;

async function partHub() {
  const WORK = await Deno.makeTempDir({prefix: 'parseh-mobile-'});
  await Deno.mkdir(WORK + '/root/youtube/videos', {recursive: true});
  await Deno.mkdir(WORK + '/root/books', {recursive: true});
  await Deno.symlink(root + '/lib', WORK + '/root/lib');
  await Deno.symlink(root + '/youtube/lib', WORK + '/root/youtube/lib');
  for (const d of ['library', 'exercises', 'anki', 'tray']) await Deno.mkdir(`${WORK}/${d}`);
  const LANGS = JSON.parse(await py(TREE, WORK));
  assert(LANGS.length >= 11, 'a note in each of the ' + LANGS.length + ' languages');

  const port = freePort();
  const log = [];
  const hub = new Deno.Command(PY, {args: ['tests/cardkit_harness.py', 'serve', WORK, String(port)], cwd: root,
                                    stdout: 'piped', stderr: 'piped'}).spawn();
  for (const s of [hub.stdout, hub.stderr])
    (async () => { for await (const c of s.pipeThrough(new TextDecoderStream())) log.push(c); })();
  const B = `http://127.0.0.1:${port}`;
  for (const t = Date.now();;) {
    try { const r = await fetch(B + '/'); await r.body?.cancel(); if (r.ok) break; } catch (_) {}
    if (Date.now() - t > 60000) throw Error('the hub did not start:\n' + log.join(''));
    await sleep(250);
  }

  try {
    // a phone -- a touch screen, as Chromium's device emulation draws one --
    // and a desktop with a mouse
    for (const vp of [{width: 390, height: 844, touch: true}, {width: 1280, height: 800}]) {
      const tag = vp.width + 'x' + vp.height;
      console.log(`\n== ${tag}` + (vp.touch ? ', touch' : ', mouse'));
      // No service worker: in the mobile mode the pages register the app's
      // (lib/sw.js), which then makes a controlled page's navigations -- and
      // a request the worker makes is not the page's to read, cookie and all.
      // The worker is tests/mobile_pages.mjs's; this reads what the pages send.
      const ctx = await browser.newContext({viewport: {width: vp.width, height: vp.height}, serviceWorkers: 'block',
                                            ...(vp.touch ? {isMobile: true, hasTouch: true} : {})});
      const page = await ctx.newPage();
      if (vp.touch) await phone(page);
      page.on('pageerror', e => { errors.push(tag + ': ' + e.message); console.log('PAGE ERROR', e.message); });

      // ---- a) the browser hub, as it opens
      await page.goto(B + '/');
      await settle(page);
      let s = await snapshot(page);
      eq(s.mode, 'browser', 'nothing chosen: the hub opens in the browser mode');
      assert(s.browser.every(([d]) => d) && s.mobile.every(([d, disp]) => !d && disp === 'none'),
             'the browser layout is on the screen and the mobile one is display:none ' + JSON.stringify([s.browser, s.mobile]));
      eq(s.pressed.map(p => p.slice(0, 2)), [['browser', 'true'], ['mobile', 'false']],
         'the switch is in the browser bar, Browser pressed');
      assert(s.pressed[0][2] !== s.pressed[1][2] && !/rgba\(0, 0, 0, 0\)/.test(s.pressed[0][2]),
             'and drawn pressed: ' + s.pressed.map(p => p[2]).join(' vs '));
      const before = s.clickable;
      for (const h of ['a:/books/', 'a:/youtube/', 'a:/studio/', 'a:/exercises/', 'a:/anki/sync/', 'a:/clips/',
                       'a:/lookup/', 'button:stop', 'a:/guide/'])
        assert(before.includes(h), 'the browser hub shows ' + h);
      assert(!before.some(h => /guide\.pdf/.test(h)), 'and no link opens the PDF guide any more');
      await page.mouse.move(1, 1);
      await settle(page);
      await sleep(250);                         // the doors' hover transition, over
      const hubBefore = await hubPicture(page);
      await shot(page, `${tag}-browser`);

      // ---- b) Mobile
      await page.locator('.parseh-bar:not(.m-bar) [data-parseh-mode=mobile]').click();
      s = await snapshot(page);
      eq(s.mode, 'mobile', 'Mobile clicked: <html data-mode="mobile">, with no reload');
      assert(s.mobile.every(([d]) => d) && s.browser.every(([d, disp]) => !d && disp === 'none'),
             'the mobile layout is on the screen and the browser one is display:none ' + JSON.stringify([s.browser, s.mobile]));
      eq(s.pressed.map(p => p.slice(0, 2)), [['browser', 'false'], ['mobile', 'true']],
         'the switch is in the mobile bar too, Mobile pressed');
      assert(await page.evaluate(() => document.activeElement && document.activeElement.getAttribute('data-parseh-mode') === 'mobile'
                                       && document.activeElement.closest('.m-bar') !== null),
             'the focus went with the click to the Mobile button now on the screen');
      eq(s.clickable, await MOBILE_CLICKABLE(page),
         'all there is to tap: home, the switch, the theme, the chips, four doors, the guide and the app\'s');
      for (const no of ['button:stop', 'a:/anki/sync/', 'a:/clips/', 'a:/lookup/'])
        assert(!s.clickable.includes(no), 'no ' + no + ' on the mobile hub');
      assert(!(await page.evaluate(() => [...document.querySelectorAll('.addr, .foot')].some(e => e.getClientRects().length))),
             'and no server address, no foot');
      assert(s.sideways <= 0, 'the page does not scroll sideways (' + s.sideways + ')');
      const ds = await doors(page);
      eq(ds.map(d => d.href), ['/books/', '/youtube/', '/studio/', '/exercises/', '/guide/', '/m/install/'],
         'the doors, in order (the last installs the mobile interface as an app)');
      for (const d of ds) {
        assert(d.h >= 48 && d.l >= 0 && d.r <= vp.width && d.hit,
               `${d.href}: ${Math.round(d.h)}px high, inside the screen (${Math.round(d.l)}..${Math.round(d.r)}), reached by a tap`);
        if (d.href !== '/guide/' && d.href !== '/m/install/')
          assert(d.tags.length && d.counted && d.tags.every(t => /^\d+ /.test(t)), `${d.href} says how many: ${d.tags.join(', ')}`);
      }
      const bar = await page.evaluate(() => [...document.querySelectorAll('.m-bar a, .m-bar button')].map(b => {
        const r = b.getBoundingClientRect();
        return [b.getAttribute('data-parseh-mode') || b.textContent.trim(), Math.round(r.height), r.left >= 0 && r.right <= innerWidth];
      }));
      assert(bar.every(([, h, inside]) => h >= 48 && inside), 'every control of the mobile bar is 48px high and on the screen ' + JSON.stringify(bar));
      if (vp.width >= 1000) {
        const col = await page.evaluate(() => { const r = document.querySelector('main.hub').getBoundingClientRect(); return [r.left, r.right, r.width]; });
        // from 600px the column widens and the doors go two to a row: a
        // phone held sideways lacks height, not width (lib/mobile.css)
        assert(col[2] <= 900 && Math.abs(col[0] - (vp.width - col[1])) <= 1, 'on a desktop: a column in the middle ' + JSON.stringify(col));
      }
      // the chips: for a finger, one row, which scrolls sideways when it has
      // more than fits; for a mouse, which cannot swipe it, rows that wrap
      const row = await page.evaluate(() => {
        const r = document.querySelector('.m-langs'), cs = getComputedStyle(r);
        const chips = [...r.querySelectorAll('.chip')].map(c => c.getBoundingClientRect());
        return {wrap: cs.flexWrap, ox: cs.overflowX, tops: [...new Set(chips.map(c => Math.round(c.top)))].length,
                over: r.scrollWidth - r.clientWidth, h: Math.min(...chips.map(c => c.height)), n: chips.length,
                mouse: matchMedia('(hover:hover) and (pointer:fine)').matches};
      });
      eq(row.mouse, !vp.touch, 'the page knows the pointer for ' + (vp.touch ? 'a finger' : 'a mouse'));
      if (vp.touch) {
        assert(row.n === LANGS.length + 1 && row.tops === 1 && row.wrap === 'nowrap' && row.ox === 'auto' && row.h >= 48,
               'the chips: all ' + row.n + ' in one row, 48px high, which scrolls ' + JSON.stringify(row));
        assert(row.over > 0, 'and on a phone it does scroll: ' + row.over + 'px more than fits');
      } else {
        assert(row.n === LANGS.length + 1 && row.tops > 1 && row.wrap === 'wrap' && row.over <= 0 && row.h >= 48,
               'with a mouse the chips wrap, all ' + row.n + ' of them, and nothing is left past the edge ' + JSON.stringify(row));
        // and a plain click -- no wheel, no drag, no shift -- reaches each
        // one, from the top of the page (the doors above left it scrolled)
        await page.evaluate(() => scrollTo(0, 0));
        const missed = [];
        for (const pick of await page.evaluate(() => [...document.querySelectorAll('.m-langs .chip')].map(c => c.dataset.pick))) {
          const at = await page.evaluate(p => {
            const c = document.querySelector(`.m-langs .chip[data-pick="${p}"]`), q = c.getBoundingClientRect();
            const x = q.left + q.width / 2, y = q.top + q.height / 2, hit = document.elementFromPoint(x, y);
            return {x, y, ok: !!hit && c.contains(hit) && q.left >= 0 && q.right <= innerWidth && q.top >= 0 && q.bottom <= innerHeight};
          }, pick);
          if (at.ok) await page.mouse.click(at.x, at.y);
          if (!at.ok || await page.evaluate(() => Parseh.lang.get()) !== pick) missed.push(pick);
        }
        eq(missed, [], 'a plain mouse click picks every chip');
        await page.evaluate(() => Parseh.lang.set('all'));
      }
      // a chip rewrites the counts the doors say
      const studioTag = () => page.locator('.hub-mobile a.m-door[href="/studio/"] .tag').first().textContent();
      const allDocs = await studioTag();
      await page.locator('.m-langs .chip[data-pick=ja]').scrollIntoViewIfNeeded();
      await page.locator('.m-langs .chip[data-pick=ja]').click();
      eq(await studioTag(), '1 document', 'Japanese picked on the mobile row: the studio door counts its one note (was ' + allDocs + ')');
      assert(await page.evaluate(() => [...document.querySelectorAll('.parseh-langs .chip.on')].every(c => c.dataset.pick === 'ja')),
             'and both rows know it');
      await page.locator('.m-langs .chip[data-pick=all]').click();
      eq(await studioTag(), allDocs, 'all again: the whole count');
      // the picked chip is in view whenever the row is, however far along
      // the row it is -- else the counts answer for a language nothing on
      // the screen says is picked: after a reload, after the switch puts the
      // row back on the screen (at its start), and after a tap on a chip
      // half under the row's faded edge
      const picked = () => page.evaluate(() => {
        const row = document.querySelector('.m-langs'), on = row.querySelector('.chip.on'), cs = getComputedStyle(row);
        const r = row.getBoundingClientRect(), c = on.getBoundingClientRect();
        return {on: on.dataset.pick, y: scrollY, scrolls: row.scrollWidth > row.clientWidth,
                inside: c.left >= r.left + parseFloat(cs.paddingLeft) - 0.5 && c.right <= r.right - parseFloat(cs.paddingRight) + 0.5,
                box: [Math.round(c.left), Math.round(c.right), Math.round(r.left), Math.round(r.right)]};
      });
      const last = await page.evaluate(() => [...document.querySelectorAll('.m-langs .chip')].pop().dataset.pick);
      await page.evaluate(l => { Parseh.lang.set(l); scrollTo(0, 0); }, last);
      await page.reload();
      await settle(page);
      let pk = await picked();
      assert(pk.on === last && pk.inside && pk.y === 0,
             `${last}, the row's last chip, picked and the page reloaded: its chip is in view, the page not moved ${JSON.stringify(pk)}`);
      eq(await studioTag(), '1 document', 'and the studio door counts that language\'s note');
      await page.locator('.m-bar [data-parseh-mode=browser]').click();
      await page.locator('.parseh-bar:not(.m-bar) [data-parseh-mode=mobile]').click();
      pk = await picked();
      assert(pk.on === last && pk.inside && pk.y === 0, 'to Browser and back to Mobile: the chip is in view again ' + JSON.stringify(pk));
      if (pk.scrolls) {
        await page.evaluate(() => { document.querySelector('.m-langs').scrollLeft = 0; });
        const edge = await page.evaluate(() => {
          const row = document.querySelector('.m-langs'), r = row.getBoundingClientRect(), pad = parseFloat(getComputedStyle(row).paddingRight);
          const c = [...row.querySelectorAll('.chip')].find(c => { const q = c.getBoundingClientRect(); return q.left < r.right - pad && q.right > r.right - pad; });
          return c && c.dataset.pick;
        });
        assert(edge, 'a chip lies half under the row\'s right edge: ' + edge);
        await page.locator(`.m-langs .chip[data-pick=${edge}]`).click();
        await page.waitForFunction(() => { const row = document.querySelector('.m-langs'), c = row.querySelector('.chip.on').getBoundingClientRect(),
                                           r = row.getBoundingClientRect(); return c.left >= r.left + 16 && c.right <= r.right - 16; }, null, {timeout: 3000})
          .catch(() => {});
        pk = await picked();
        assert(pk.on === edge && pk.inside && pk.y === 0, 'picked there, it is brought into view ' + JSON.stringify(pk));
      }
      await page.evaluate(() => Parseh.lang.set('all'));
      await page.evaluate(() => scrollTo(0, 0));
      await settle(page);
      await shot(page, `${tag}-mobile`);

      // ---- c) the choice is kept
      const cookie = (await ctx.cookies(B)).find(c => c.name === 'parseh_mode');
      assert(cookie && cookie.value === 'mobile' && cookie.path === '/' && cookie.sameSite === 'Lax' &&
             cookie.expires > Date.now() / 1000 + 300 * 86400,
             'the cookie: parseh_mode=mobile, Path=/, SameSite=Lax, for a year ' + JSON.stringify(cookie));
      eq(s.stored, 'mobile', 'and localStorage parseh_mode=mobile');
      await page.reload();
      s = await snapshot(page);
      assert(s.mode === 'mobile' && s.mobile.every(([d]) => d) && s.browser.every(([d]) => !d),
             'reloaded: still the mobile hub');
      eq(s.pressed.map(p => p.slice(0, 2)), [['browser', 'false'], ['mobile', 'true']], 'Mobile still pressed');
      // a door whose page has a mobile version at an address of its own: it
      // goes there, and the server is sent the cookie
      let sent = null;
      const onReq = async r => { if (new URL(r.url()).pathname === '/m/books/' && r.isNavigationRequest()) sent = (await r.allHeaders()).cookie || ''; };
      page.on('request', onReq);
      await Promise.all([page.waitForURL(B + '/m/books/'), page.locator('.hub-mobile a.m-door[href="/books/"]').click()]);
      page.off('request', onReq);
      await settle(page);
      assert(/(^|;\s*)parseh_mode=mobile(;|$)/.test(sent || ''), 'the Books door opened the mobile shelf, /m/books/, and the server was sent parseh_mode=mobile: ' + sent);
      s = await snapshot(page);
      assert(s.mode === 'mobile' && s.stored === 'mobile' && /parseh_mode=mobile/.test(s.cookie),
             'the shelf knows the mode (data-mode, localStorage, cookie)');
      assert(!s.clickable.includes('button:stop'), 'and has no stop button');
      await Promise.all([page.waitForURL(B + '/'), page.locator('.m-bar a.home').click()]);
      // a door with no mobile version: the browser page, as it is
      await Promise.all([page.waitForURL(B + '/youtube/'), page.locator('.hub-mobile a.m-door[href="/youtube/"]').click()]);
      await settle(page);
      s = await snapshot(page);
      assert(s.mode === 'mobile' && s.clickable.includes('button:stop'),
             'the Videos door opens the video index, its browser page as it is -- there is no mobile version of it yet');
      await shot(page, `${tag}-videos-fallback`);
      await Promise.all([page.waitForURL(B + '/'), page.locator('.parseh-bar a.home').click()]);
      s = await snapshot(page);
      assert(s.mode === 'mobile' && s.mobile.every(([d]) => d), 'its home link: back on the mobile hub');
      // another tab follows a switch made in this one
      const other = await ctx.newPage();
      await other.goto(B + '/');
      eq((await snapshot(other)).mode, 'mobile', 'a second tab opens mobile');
      await page.locator('.m-bar [data-parseh-mode=browser]').click();
      await other.waitForFunction(() => document.documentElement.getAttribute('data-mode') === 'browser');
      s = await snapshot(other);
      assert(s.browser.every(([d]) => d) && s.mobile.every(([d]) => !d), 'Browser clicked in the first: the second tab shows the browser hub');
      await page.locator('.parseh-bar:not(.m-bar) [data-parseh-mode=mobile]').click();
      await other.waitForFunction(() => document.documentElement.getAttribute('data-mode') === 'mobile');
      assert((await snapshot(other)).mobile.every(([d]) => d), 'and Mobile: the mobile hub');
      await other.close();

      // ---- d) a door goes where Parseh.mode.route says
      const register = () => page.evaluate(() => Parseh.mode.pages.unshift({match: /^\/youtube\/$/, to: '/clips/'}));
      eq(await page.evaluate(() => [Parseh.mode.route('/youtube/'), Parseh.mode.route('/studio/?x=1#y')]), ['/youtube/', '/studio/?x=1#y'],
         'nothing registered: route() answers the browser address');
      eq(await page.evaluate(() => [Parseh.mode.route('/books/?x=1#y'), Parseh.mode.route('/books/index.html'),
                                    Parseh.mode.route('/books/persian/mini-fa/reader/index.html#par-1'),
                                    Parseh.mode.route('/exercises/deck/persian/words/study')]),
         ['/m/books/?x=1#y', '/m/books/', '/books/persian/mini-fa/reader/#par-1', '/exercises/deck/persian/words/study'],
         'the registry: the library to the mobile shelf; a reader and the decks are their own mobile versions');
      await register();
      eq(await page.evaluate(() => [Parseh.mode.route('/youtube/?q=1#t'), Parseh.mode.route(location.origin + '/youtube/'),
                                    Parseh.mode.route('https://example.org/youtube/')]),
         ['/clips/?q=1#t', '/clips/', 'https://example.org/youtube/'],
         'a mobile version registered: route() answers it, keeps the query and the fragment, leaves another site alone');
      await Promise.all([page.waitForURL(B + '/clips/'), page.locator('.hub-mobile a.m-door[href="/youtube/"]').click()]);
      assert(true, 'a tap on the Videos door lands on the registered mobile version');
      await page.goto(B + '/');
      await register();
      const [tab] = await Promise.all([ctx.waitForEvent('page'),
        page.locator('.hub-mobile a.m-door[href="/youtube/"]').click({modifiers: ['Control']})]);
      await tab.waitForLoadState();
      assert(new URL(tab.url()).pathname === '/clips/' && new URL(page.url()).pathname === '/',
             'a ctrl-click opens the mobile version in a new tab, and the hub stays: ' + tab.url());
      await tab.close();
      eq(await page.evaluate(() => [Parseh.mode.route('/youtube/'), document.querySelector('.hub-mobile a[href="/clips/"]') &&
                                    document.querySelector('.hub-mobile a[href="/clips/"]').getAttribute('data-parseh-href')]),
         ['/clips/', '/youtube/'], 'the door now points at the mobile version, its own address kept beside it');

      // ---- e) Browser: the browser hub as it was
      await page.locator('.m-bar [data-parseh-mode=browser]').click();
      s = await snapshot(page);
      assert(s.mode === 'browser' && s.browser.every(([d]) => d) && s.mobile.every(([d]) => !d), 'Browser clicked: the browser hub');
      eq(s.clickable, before, 'with the very doors, links and buttons it had');
      eq(await page.evaluate(() => [document.querySelectorAll('a[data-parseh-href]').length,
                                    document.querySelector('.hub-mobile a.m-door:nth-child(2)').getAttribute('href')]),
         [0, '/youtube/'], 'and the routed door has its own address back');
      eq([(await ctx.cookies(B)).find(c => c.name === 'parseh_mode').value, s.stored], ['browser', 'browser'],
         'the cookie and localStorage say browser');
      await page.evaluate(() => scrollTo(0, 0));
      await page.mouse.move(1, 1);
      await settle(page);
      await sleep(250);
      const hubAfter = await hubPicture(page);
      assert(hubAfter.length === hubBefore.length && hubAfter.every((b, i) => b === hubBefore[i]),
             'the browser hub is drawn pixel for pixel as before the switch');
      await ctx.close();
    }

    // ---- f) the phone bar in both modes, and the three palettes
    console.log('\n== the phone bar, the palettes');
    {
      const ctx = await browser.newContext({viewport: {width: 390, height: 520}, isMobile: true, hasTouch: true});
      const page = await ctx.newPage();
      await phone(page);
      page.on('pageerror', e => { errors.push('f: ' + e.message); console.log('PAGE ERROR', e.message); });
      for (const mode of ['browser', 'mobile']) {
        await page.goto(B + '/');
        await page.evaluate(m => Parseh.mode.set(m), mode);
        const sel = mode === 'mobile' ? '.m-bar' : '.parseh-bar:not(.m-bar)';
        const top = () => page.evaluate(q => Math.round(document.querySelector(q).getBoundingClientRect().bottom), sel);
        assert(await page.evaluate(() => document.documentElement.scrollHeight > innerHeight + 120), mode + ': the hub is taller than the screen');
        await page.mouse.move(195, 300);
        for (let i = 0; i < 6; i++) { await page.mouse.wheel(0, 60); await sleep(60); }
        await page.waitForFunction(() => document.body.classList.contains('barhidden'));
        await sleep(300);
        assert(await top() <= 0, mode + ': scrolled down, the bar is off the screen (bottom at ' + await top() + ')');
        await page.mouse.wheel(0, -40);
        await page.waitForFunction(() => !document.body.classList.contains('barhidden'));
        await sleep(300);
        assert(await top() > 40, mode + ': the smallest move up brings it back (bottom at ' + await top() + ')');
      }
      // every text of the mobile hub against what it is drawn on
      const contrast = () => page.evaluate(() => {
        const rgb = c => { const m = /rgba?\(([\d.]+), ([\d.]+), ([\d.]+)(?:, ([\d.]+))?\)/.exec(c); return m ? [+m[1], +m[2], +m[3], m[4] === undefined ? 1 : +m[4]] : null; };
        const lum = ([r, g, b]) => { const f = c => (c /= 255) <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b); };
        const ground = el => { for (; el; el = el.parentElement) { const c = rgb(getComputedStyle(el).backgroundColor); if (c && c[3] > 0) return c; } return [255, 255, 255, 1]; };
        const out = [];
        const texts = document.querySelectorAll('.hub-mobile .m-dname, .hub-mobile .m-dwhat, .hub-mobile .m-dfa, .hub-mobile .tag, .hub-mobile .chip .native, ' +
          '.hub-mobile .chip .n, .hub-mobile .chip[data-pick=all], .m-brand .fa, .m-brand .lat, .m-tagline, .m-bar .home, .m-bar button');
        for (const el of texts) {
          if (!el.getClientRects().length) continue;
          const cs = getComputedStyle(el), size = parseFloat(cs.fontSize), bold = parseInt(cs.fontWeight, 10) >= 700;
          const a = lum(rgb(cs.color)), b = lum(ground(el));
          // WCAG's AA: 4.5:1, and 3:1 for large text (24px, or 18.66px bold)
          out.push([el.className || el.getAttribute('data-parseh-mode') || el.textContent.trim().slice(0, 12),
                    Math.round((Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05) * 100) / 100,
                    size >= 24 || (size >= 18.66 && bold) ? 3 : 4.5]);
        }
        return out;
      });
      await page.evaluate(() => Parseh.mode.set('mobile'));
      for (const theme of ['light', 'dark', 'sepia']) {
        await page.evaluate(t => { Parseh.theme.set(t); scrollTo(0, 0); }, theme);
        await settle(page);
        const c = await contrast();
        const low = c.filter(([, r, need]) => r < need);
        assert(c.length > 20 && !low.length, `${theme}: ${c.length} texts, each readable against its ground (AA)` +
               (low.length ? ' -- too faint: ' + JSON.stringify(low) : ' (lowest ' + Math.min(...c.map(x => x[1])) + ')'));
        await page.setViewportSize({width: 390, height: 844});
        await shot(page, `390-mobile-${theme}`);
        await page.setViewportSize({width: 390, height: 520});
      }
      await ctx.close();
    }
    // ---- g) each bar is one row at a phone's width
    console.log('\n== the bars on a phone');
    {
      // how many rows a bar's items lie in, and whether each is on the screen
      const bar = (page, sel) => page.evaluate(q => {
        const b = document.querySelector(q);
        const items = [...b.children].filter(c => c.getClientRects().length && !c.classList.contains('sp'));
        const rows = new Set(items.map(c => { const r = c.getBoundingClientRect(); return Math.round(r.top + r.height / 2); }));
        const ctl = [...b.querySelectorAll('a, button')].map(c => c.getBoundingClientRect());
        return {rows: rows.size, h: Math.round(b.getBoundingClientRect().height),
                inside: ctl.every(r => r.left >= 0 && r.right <= innerWidth),
                min: [Math.round(Math.min(...ctl.map(r => r.width))), Math.round(Math.min(...ctl.map(r => r.height)))]};
      }, sel);
      const B_BAR = '.parseh-bar:not(.m-bar)';
      for (const w of [320, 340, 360, 375, 390, 412, 430]) {
        const ctx = await browser.newContext({viewport: {width: w, height: 800}, isMobile: true, hasTouch: true});
        const page = await ctx.newPage();
        page.on('pageerror', e => { errors.push('g: ' + e.message); console.log('PAGE ERROR', e.message); });
        await page.goto(B + '/');
        await settle(page);
        // the browser hub: one row as before the switch was in it -- from
        // 340px up; at 320 it had two rows already
        const b = await bar(page, B_BAR);
        if (w >= 340) assert(b.rows === 1 && b.inside, `${w}px, the browser hub: its bar is one row, all of it on the screen ${JSON.stringify(b)}`);
        else assert(b.rows <= 2 && b.inside, `${w}px, the browser hub: its bar is on the screen (two rows, as it always was here) ${JSON.stringify(b)}`);
        // the words it sheds are gone from the eye, not from a screen reader
        eq([await page.locator(B_BAR).getByRole('button', {name: /stop/}).count(),
            await page.locator(B_BAR).getByRole('link', {name: /Parseh/}).count()], [1, 1],
           `${w}px: the stop button and the home link still say what they are`);
        await page.evaluate(() => Parseh.mode.set('mobile'));
        await settle(page);
        const m = await bar(page, '.m-bar');
        assert(m.rows === 1 && m.inside && m.min[0] >= 48 && m.min[1] >= 48,
               `${w}px, the mobile hub: its bar is one row, on the screen, every control at least 48x48 ${JSON.stringify(m)}`);
        await page.evaluate(() => Parseh.mode.set('browser'));
        await ctx.close();
      }
      // and on a desktop nothing of it is shed
      const ctx = await browser.newContext({viewport: {width: 1280, height: 800}});
      const page = await ctx.newPage();
      await page.goto(B + '/');
      await settle(page);
      eq(await page.evaluate(q => [...document.querySelectorAll(q + ' .where, ' + q + ' .word')].map(e => [e.textContent.trim(), e.getBoundingClientRect().width > 20]), B_BAR),
         [['Parseh', true], ['the hub', true], ['stop', true]], '1280px: the bar says Parseh, the hub and stop, as it did');
      await ctx.close();
    }

    assert(!/Traceback/.test(log.join('')), 'no traceback in the hub\'s log');
  } catch (e) {
    console.log('hub log tail:\n' + log.join('').slice(-2000));
    throw e;
  } finally {
    try { hub.kill('SIGTERM'); await hub.status; } catch (_) {}
    await Deno.remove(WORK, {recursive: true}).catch(() => {});
  }
}

try {
  if (PARTS.includes('api')) await partApi();
  if (PARTS.includes('hub')) await partHub();
  assert(!errors.length, 'no page raised an error ' + JSON.stringify(errors));
  console.log(`\nmobile_mode: ${passed} checks passed`);
} catch (e) {
  console.log(e.stack || e);
  Deno.exitCode = 1;
} finally {
  await browser.close();
}

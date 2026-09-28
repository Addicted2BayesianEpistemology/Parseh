// SPDX-License-Identifier: GPL-3.0-or-later
// THE AUTHOR'S SIGNATURE, AS THE BROWSER DRAWS IT (a0.4.1, lib/author.py).
//
//   CHROME_BIN=... PARSEH_PYTHON=python3 deno run --allow-all tests/signature.mjs
//   SIGNATURE_PARTS=hub,mobile,settings,licences,guide,rtl runs some of them;
//   SHOTS=<dir> saves a screenshot of every place (the phone hub at 320, 390
//   and 430, the others at 1280 and 390, each in the three themes) -- the
//   pictures are for LOOKING at, the checks below are made on what was drawn
//
// The owner asked for his name and two links in a few places (TO-DO §15.17,
// decided 2026-09-28): the foot of the hub, browser layout and phone hub; the
// foot of the guide, every page and its hand-written front page; and a foot
// line on the Settings hub -- only the two links, whose visible words are
// "GitHub" and "imbrunoursino.net" -- and, on /licences/, his name beside "the
// author".  Links only: nothing is fetched from either address.
//
// Against the REAL hub (serve.main, booted by tests/cardkit_harness.py serve
// over a temporary toolbox, as tests/mobile_mode.mjs does) and the guide
// compiled by html-guide/build.py --pages into a temporary folder and opened
// off the disk, at 1280x800 with a mouse and at phone widths on a touch
// screen, in light, dark and sepia:
//   hub      the browser layout's foot, as it stands under the licences
//            line; visible words, address, target and rel, the label a screen
//            reader and a hover read, the colour against its ground (WCAG AA,
//            4.5:1), inside the window, no sideways scroll; a click opens the
//            address in a NEW tab (a stub answers there: no request leaves the
//            machine) with no opener and no Referer, and the hub stays
//   mobile   the phone hub's last line, at 320, 340, 360, 375, 390, 412 and
//            430: each link 48px high or more, inside the screen, reached by a
//            tap on its middle, side by side without overlapping, small text,
//            AA in the three themes, no sideways scroll
//   settings the Settings hub's foot line, and no other page of Settings has one
//   licences the page names him beside "the author", with the two links
//   guide    the front page's foot and a compiled page's foot: the same two
//            links, AA in the three themes, a target a finger can hit
//   rtl      the hub has no interface language, so no right-to-left one to
//            open it in: dir=rtl is put on the page by hand, as a stand-in --
//            the links stay inside the window and swap sides
// On every page, nothing is requested from either host on load (context.route
// records every attempt), and none of the pages tries to reach anything that
// is not this machine's.
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
async function run(args, opts = {}) {
  const o = await new Deno.Command(args[0], {args: args.slice(1), cwd: root, stdout: 'piped', stderr: 'piped', ...opts}).output();
  return {code: o.code, out: td.decode(o.stdout) + td.decode(o.stderr)};
}

const GITHUB = 'https://github.com/Addicted2BayesianEpistemology';
const SITE = 'https://imbrunoursino.net/';
const HOSTS = /^https?:\/\/(?:[^/]*\.)?(?:github\.com|imbrunoursino\.net)(?:[:/]|$)/;
const LABELS = ['Bruno Ursino on GitHub', "Bruno Ursino's website"];
const THEMES = ['light', 'dark', 'sepia'];
const PARTS = (Deno.env.get('SIGNATURE_PARTS') || 'hub,mobile,settings,licences,guide,rtl').split(',');
const browser = await chromium.launch({executablePath: Deno.env.get('CHROME_BIN'), headless: true});
const errors = [];

// ---- what the page has drawn ------------------------------------------------
// A phone: a touch screen as Chromium's emulation draws one; a screenshot
// drops it (see tests/mobile_mode.mjs), so every picture goes through grab().
async function phone(page) {
  page.touch = await page.context().newCDPSession(page);
  await page.touch.send('Emulation.setTouchEmulationEnabled', {enabled: true, maxTouchPoints: 1});
}
async function grab(page, opts) {
  const png = await page.screenshot(opts);
  if (page.touch) await page.touch.send('Emulation.setTouchEmulationEnabled', {enabled: true, maxTouchPoints: 1});
  return png;
}
const shot = async (page, name) => {
  if (!SHOTS) return;
  await Deno.mkdir(SHOTS, {recursive: true});
  await grab(page, {path: `${SHOTS}/${name}.png`, fullPage: !page.touch});
};
const settle = page => page.evaluate(() => document.fonts.ready.then(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))));

// The two links of a foot, as drawn: `scope` is the element that holds them.
// -> what they say, where they lead, what a screen reader and a hover read,
// where they are, what a tap on the middle of each reaches, and the WCAG
// contrast of their ink against what they are drawn on.
const measure = (page, scope, only = 'a') => page.evaluate(([sel, only]) => {
  const rgb = c => { const m = /rgba?\(([\d.]+), ([\d.]+), ([\d.]+)(?:, ([\d.]+))?\)/.exec(c); return m ? [+m[1], +m[2], +m[3], m[4] === undefined ? 1 : +m[4]] : null; };
  const lum = ([r, g, b]) => { const f = c => (c /= 255) <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b); };
  const ground = el => { for (; el; el = el.parentElement) { const c = rgb(getComputedStyle(el).backgroundColor); if (c && c[3] > 0) return c; } return [255, 255, 255, 1]; };
  const host = document.querySelector(sel);
  if (!host) return {missing: sel};
  const links = [...host.querySelectorAll(only)].map(a => {
    a.scrollIntoView({block: 'center'});
    const r = a.getBoundingClientRect(), cs = getComputedStyle(a);
    const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
    const x = lum(rgb(cs.color)), y = lum(ground(a));
    return {href: a.getAttribute('href'), text: a.textContent, target: a.getAttribute('target'), rel: a.getAttribute('rel'),
            label: a.getAttribute('aria-label'), title: a.getAttribute('title'), drawn: a.getClientRects().length > 0,
            l: r.left, r: r.right, t: r.top, b: r.bottom, w: r.width, h: r.height, size: parseFloat(cs.fontSize),
            hit: !!hit && (hit === a || a.contains(hit)), ratio: Math.round((Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05) * 100) / 100};
  });
  return {links, sideways: document.documentElement.scrollWidth - innerWidth, w: innerWidth,
          shown: host.innerText.replace(/\s+/g, ' ').trim(), dir: getComputedStyle(host).direction};
}, [scope, only]);

// what one place must be, at one width in one theme
function checkFoot(m, where, {finger = 0, aa = true} = {}) {
  assert(!m.missing, `${where}: the foot is there (${m.missing || ''})`);
  eq(m.links.map(a => [a.href, a.text]), [[GITHUB, 'GitHub'], [SITE, 'imbrunoursino.net']], `${where}: two links, and the words they say`);
  for (const a of m.links) {
    eq([a.target, a.rel], ['_blank', 'noopener noreferrer'], `${where}: ${a.text} opens in a tab of its own, telling the site nothing`);
    assert(a.drawn && a.l >= 0 && a.r <= m.w, `${where}: ${a.text} is drawn, inside the window (${Math.round(a.l)}..${Math.round(a.r)} of ${m.w})`);
    assert(a.hit, `${where}: a tap on the middle of ${a.text} reaches it`);
    if (aa) assert(a.ratio >= 4.5, `${where}: ${a.text} is readable against its ground (AA), ${a.ratio}:1`);
    if (finger) assert(a.h >= finger, `${where}: ${a.text} is ${Math.round(a.h)}px high (a finger's height is ${finger})`);
  }
  eq(m.links.map(a => [a.label, a.title]), LABELS.map(x => [x, x]), `${where}: a screen reader and a hover read who they are`);
  assert(m.sideways <= 0, `${where}: the page does not scroll sideways (${m.sideways})`);
}

// ---- the network ------------------------------------------------------------
// Every attempt to reach either host is caught here and answered by a stub, so
// nothing leaves the machine; `hits` is what the page ASKED for.  A page that
// loaded and was looked at must have asked for none.
async function newContext(vp, opts = {}) {
  const ctx = await browser.newContext({viewport: {width: vp.width, height: vp.height}, serviceWorkers: 'block',
                                        ...(vp.touch ? {isMobile: true, hasTouch: true} : {}), ...opts});
  ctx.hits = [];
  ctx.foreign = [];
  await ctx.route(HOSTS, route => {
    ctx.hits.push({url: route.request().url(), referer: route.request().headers()['referer'] || null});
    return route.fulfill({status: 200, contentType: 'text/html', body: '<!doctype html><title>stub</title><p>stub</p>'});
  });
  ctx.on('request', r => {
    const u = r.url();
    if (!/^(http:\/\/127\.0\.0\.1[:/]|file:|data:|blob:|about:)/.test(u) && !HOSTS.test(u)) ctx.foreign.push(u);
  });
  return ctx;
}
async function newPage(ctx, vp, tag) {
  const page = await ctx.newPage();
  if (vp.touch) await phone(page);
  page.on('pageerror', e => { errors.push(tag + ': ' + e.message); console.log('PAGE ERROR', e.message); });
  return page;
}
// A click on the link opens the address in a tab of its own; the tab has no
// opener and was sent no Referer; the page it came from has not moved.
async function clicked(ctx, page, sel, want, where) {
  const before = page.url();
  const n = ctx.hits.length;
  const [popup] = await Promise.all([ctx.waitForEvent('page'), page.locator(sel).first().click()]);
  await popup.waitForLoadState();
  eq(popup.url(), want, `${where}: a click opens ${want} in a new tab`);
  eq(await popup.evaluate(() => window.opener), null, `${where}: the new tab has no opener`);
  eq(ctx.hits.slice(n).map(h => [h.url, h.referer]), [[want, null]], `${where}: that click is the first and only request to it, sent no Referer`);
  eq(page.url(), before, `${where}: the page it came from stays where it was`);
  await popup.close();
}
const noneAsked = (ctx, where) => eq([ctx.hits.map(h => h.url), ctx.foreign], [[], []],
  `${where}: nothing was requested from either address, nor from anywhere but this machine`);

// ---- the hub, booted the way tests/mobile_mode.mjs boots it -------------------
async function bootHub() {
  const WORK = await Deno.makeTempDir({prefix: 'parseh-signature-'});
  await Deno.mkdir(WORK + '/root/youtube/videos', {recursive: true});
  await Deno.mkdir(WORK + '/root/books', {recursive: true});
  await Deno.symlink(root + '/lib', WORK + '/root/lib');
  await Deno.symlink(root + '/youtube/lib', WORK + '/root/youtube/lib');
  for (const d of ['library', 'exercises', 'anki', 'tray']) await Deno.mkdir(`${WORK}/${d}`);
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
  return {B, WORK, log, stop: async () => {
    try { hub.kill('SIGTERM'); await hub.status; } catch (_) {}
    await Deno.remove(WORK, {recursive: true}).catch(() => {});
  }};
}

// ======== the hub's foot, in the browser layout ========
async function partHub(B) {
  console.log('\n== hub: the browser layout\'s foot');
  for (const vp of [{width: 1280, height: 800}, {width: 390, height: 844, touch: true}]) {
    const tag = `hub-browser-${vp.width}`;
    const ctx = await newContext(vp);
    const page = await newPage(ctx, vp, tag);
    await page.goto(B + '/');
    await settle(page);
    eq(await page.evaluate(() => document.documentElement.getAttribute('data-mode')), 'browser', `${tag}: the hub opens in the browser mode`);
    for (const theme of THEMES) {
      await page.evaluate(t => Parseh.theme.set(t), theme);
      await settle(page);
      const m = await measure(page, '.hub-browser .foot', 'a[href^="https://"]');
      checkFoot(m, `${vp.width}px ${theme}`);
      // the foot's other lines are as they were, and the two links are what it ends with
      assert(m.shown.includes('is free software, under the GNU GPL, version 3 or later;') && m.shown.endsWith('licences. GitHub · imbrunoursino.net'),
             `${vp.width}px ${theme}: the foot says what it always said, and ends with the two words: ...${m.shown.slice(-60)}`);
      assert(!/Bruno|Ursino/.test(m.shown), `${vp.width}px ${theme}: the foot shows no name, only the two links (the name is for a screen reader)`);
      await page.locator('.hub-browser .foot').scrollIntoViewIfNeeded();
      await shot(page, `${tag}-${theme}`);
    }
    // the words a screen reader announces are the label, once, and only in the layout that is showing
    eq([await page.getByRole('link', {name: LABELS[0]}).count(), await page.getByRole('link', {name: LABELS[1]}).count()], [1, 1],
       `${tag}: a screen reader finds each link once, by his name`);
    await page.evaluate(() => Parseh.theme.set('light'));
    // a load, and three themes looked at, with nothing clicked
    await sleep(600);
    noneAsked(ctx, tag + ' on load, and through three themes');
    await clicked(ctx, page, `.hub-browser .foot a[href="${GITHUB}"]`, GITHUB, tag + ' GitHub');
    await clicked(ctx, page, `.hub-browser .foot a[href="${SITE}"]`, SITE, tag + ' site');
    // hover: the title is the hover, and a mouse gets the pointer's own cursor
    if (!vp.touch) eq(await page.evaluate(() => getComputedStyle(document.querySelector('.hub-browser .foot a')).cursor), 'pointer', `${tag}: a mouse gets a hand`);
    await ctx.close();
  }
}

// ======== the phone hub's last line ========
async function partMobile(B) {
  console.log('\n== mobile: the phone hub\'s last line');
  for (const w of [320, 340, 360, 375, 390, 412, 430]) {
    const vp = {width: w, height: 844, touch: true};
    const tag = `mobile-${w}`;
    const ctx = await newContext(vp);
    const page = await newPage(ctx, vp, tag);
    await page.goto(B + '/');
    await page.evaluate(() => Parseh.mode.set('mobile'));
    await settle(page);
    for (const theme of (w === 390 || w === 320 || w === 430) ? THEMES : ['light']) {
      await page.evaluate(t => { Parseh.theme.set(t); }, theme);
      await settle(page);
      const m = await measure(page, '.hub-mobile .m-by');
      checkFoot(m, `${w}px ${theme}`, {finger: 48});
      assert(m.links.every(a => a.size <= 13.5), `${w}px ${theme}: small text (${m.links.map(a => a.size)}px)`);
      const [a, b] = m.links;
      assert(a.r <= b.l + 0.5 || b.r <= a.l + 0.5 || a.b <= b.t || b.b <= a.t, `${w}px ${theme}: the two links do not overlap`);
      eq(m.shown, 'GitHub · imbrunoursino.net', `${w}px ${theme}: the line says the two words and the dot between them, nothing else`);
      // it is the last thing on the hub, under the version
      const order = await page.evaluate(() => {
        const q = s => document.querySelector(s).getBoundingClientRect();
        return [q('.hub-mobile .m-ver').bottom <= q('.hub-mobile .m-by').top + 0.5, q('.hub-mobile .m-by').bottom, document.documentElement.scrollHeight];
      });
      assert(order[0] && order[1] <= order[2], `${w}px ${theme}: under the version, and on the page`);
      if (theme !== 'light' || w === 390 || w === 320 || w === 430) {
        await page.locator('.hub-mobile .m-by').scrollIntoViewIfNeeded();
        await shot(page, `${tag}-${theme}`);
      }
    }
    // laid out in one row where there is room: how many rows the two links lie in
    await page.evaluate(() => Parseh.theme.set('light'));
    const rows = (await measure(page, '.hub-mobile .m-by')).links.map(a => Math.round((a.t + a.b) / 2));
    console.log(`  (${w}px: the links lie in ${new Set(rows).size} row${new Set(rows).size === 1 ? '' : 's'})`);
    // the other layout's foot is not drawn here, and the licence line and the version are as they were
    eq(await page.evaluate(() => [document.querySelector('.hub-mobile .m-foot').textContent.trim(), document.querySelector('.hub-mobile .m-ver').textContent.trim().split(' ')[0]]),
       ['Free software, GPL 3 or later · Licences', 'Parseh'], `${w}px: the licence line and the version are as they were`);
    await sleep(500);
    noneAsked(ctx, tag + ' on load, and through three themes');
    if (w === 390) {
      eq([await page.getByRole('link', {name: LABELS[0]}).count(), await page.getByRole('link', {name: LABELS[1]}).count()], [1, 1],
         `${tag}: a screen reader finds each link once`);
      await clicked(ctx, page, `.hub-mobile .m-by a[href="${GITHUB}"]`, GITHUB, tag + ' GitHub');
      await clicked(ctx, page, `.hub-mobile .m-by a[href="${SITE}"]`, SITE, tag + ' site');
    }
    await ctx.close();
  }
  // and a mouse on the mobile mode, the desktop's window
  {
    const vp = {width: 1280, height: 800};
    const ctx = await newContext(vp);
    const page = await newPage(ctx, vp, 'mobile-1280');
    await page.goto(B + '/');
    await page.evaluate(() => Parseh.mode.set('mobile'));
    await settle(page);
    for (const theme of THEMES) {
      await page.evaluate(t => Parseh.theme.set(t), theme);
      checkFoot(await measure(page, '.hub-mobile .m-by'), `mobile mode, 1280px ${theme}`, {finger: 48});
    }
    await shot(page, 'mobile-1280-light');
    await ctx.close();
  }
}

// ======== Settings ========
async function partSettings(B) {
  console.log('\n== settings: the hub\'s foot line');
  for (const vp of [{width: 1280, height: 800}, {width: 390, height: 844, touch: true}]) {
    const tag = `settings-${vp.width}`;
    const ctx = await newContext(vp);
    const page = await newPage(ctx, vp, tag);
    await page.goto(B + '/settings/');
    await settle(page);
    for (const theme of THEMES) {
      await page.evaluate(t => Parseh.theme.set(t), theme);
      await settle(page);
      const m = await measure(page, '.settings > p.foot');
      checkFoot(m, `${vp.width}px ${theme}`);
      eq(m.shown, 'GitHub · imbrunoursino.net', `${vp.width}px ${theme}: the line says the two words and nothing else`);
      // the last thing on the page, below the doors
      const below = await page.evaluate(() => document.querySelector('.settings > p.foot').getBoundingClientRect().top >=
                                              document.querySelector('.settings .doors').getBoundingClientRect().bottom);
      assert(below, `${vp.width}px ${theme}: it is under the doors`);
      await page.locator('.settings > p.foot').scrollIntoViewIfNeeded();
      await shot(page, `${tag}-${theme}`);
    }
    await page.evaluate(() => Parseh.theme.set('light'));
    noneAsked(ctx, tag + ' on load');
    await clicked(ctx, page, `.settings > p.foot a[href="${SITE}"]`, SITE, tag + ' site');
    await ctx.close();
  }
  // the other pages of Settings say nothing of it
  const vp = {width: 1280, height: 800};
  const ctx = await newContext(vp);
  const page = await newPage(ctx, vp, 'settings-others');
  for (const path of ['/settings/network/', '/settings/update/', '/settings/reading-help/']) {
    await page.goto(B + path);
    await settle(page);
    eq(await page.evaluate(([g, s]) => document.querySelectorAll(`a[href="${g}"], a[href="${s}"]`).length, [GITHUB, SITE]), 0,
       `${path}: no signature (only the hub has one)`);
  }
  await ctx.close();
}

// ======== /licences/ ========
async function partLicences(B) {
  console.log('\n== licences: his name beside "the author"');
  for (const vp of [{width: 1280, height: 800}, {width: 390, height: 844, touch: true}]) {
    const tag = `licences-${vp.width}`;
    const ctx = await newContext(vp);
    const page = await newPage(ctx, vp, tag);
    await page.goto(B + '/licences/');
    await settle(page);
    const line = await page.evaluate(() => {
      const p = [...document.querySelectorAll('main.notices p')].find(x => /Copyright/.test(x.textContent));
      p.setAttribute('data-sig', '');
      return p.innerText.replace(/\s+/g, ' ').trim();
    });
    eq(line, 'Copyright © 2026 Bruno Ursino, the author of Parseh — GitHub · imbrunoursino.net', `${tag}: the copyright line, with his name beside "the author"`);
    eq(await page.evaluate(() => document.body.innerText.includes('the Parseh authors')), false, `${tag}: "the Parseh authors" is gone`);
    for (const theme of THEMES) {
      await page.evaluate(t => Parseh.theme.set(t), theme);
      await settle(page);
      checkFoot(await measure(page, 'main.notices p[data-sig]'), `${vp.width}px ${theme}`);
      await page.locator('main.notices p[data-sig]').scrollIntoViewIfNeeded();
      await shot(page, `${tag}-${theme}`);
    }
    // the licences' own links keep the way they always opened
    eq(await page.evaluate(() => [...document.querySelectorAll('main.notices a[href^="https://"]')].filter(a => !a.closest('p[data-sig]'))
                                  .every(a => a.getAttribute('rel') === 'noopener' && a.getAttribute('target') === '_blank')), true,
       `${tag}: the licences' own links are as they were, rel=noopener target=_blank`);
    await page.evaluate(() => Parseh.theme.set('light'));
    noneAsked(ctx, tag);
    await clicked(ctx, page, `main.notices p[data-sig] a[href="${GITHUB}"]`, GITHUB, tag + ' GitHub');
    await ctx.close();
  }
}

// ======== the guide ========
async function partGuide() {
  console.log('\n== guide: the front page and a compiled page');
  const WORK = await Deno.makeTempDir({prefix: 'parseh-signature-guide-'});
  try {
    const r = await run([PY, 'html-guide/build.py', '--pages', `${WORK}/pages`]);
    assert(r.code === 0, 'build.py --pages lays out the guide: ' + r.out.trim().split('\n').slice(-2).join(' | '));
    const places = [['front', `file://${WORK}/pages/index.html`], ['page', `file://${WORK}/pages/site/getting-started/the-hub.html`]];
    for (const vp of [{width: 1280, height: 800}, {width: 390, height: 844, touch: true}]) {
      for (const [name, url] of places) {
        const tag = `guide-${name}-${vp.width}`;
        const ctx = await newContext(vp);
        const page = await newPage(ctx, vp, tag);
        await page.goto(url);
        await settle(page);
        for (const theme of ['light', 'sepia', 'dark']) {
          await page.evaluate(t => { localStorage.setItem('parseh_theme', t); Guide.theme.apply(); }, theme);
          await settle(page);
          const m = await measure(page, 'footer.g-foot');
          // a finger can hit a link of the guide's foot: padded to a target of 24px at least (WCAG 2.5.8)
          checkFoot(m, `${name} ${vp.width}px ${theme}`, {finger: 24});
          assert(m.shown.endsWith('GitHub · imbrunoursino.net'), `${name} ${vp.width}px ${theme}: the foot ends with the two words: ...${m.shown.slice(-70)}`);
          await page.locator('footer.g-foot').scrollIntoViewIfNeeded();
          await shot(page, `${tag}-${theme}`);
        }
        eq(await page.evaluate(() => document.querySelectorAll('footer.g-foot').length), 1, `${tag}: one foot`);
        await page.evaluate(() => { localStorage.setItem('parseh_theme', 'light'); Guide.theme.apply(); });
        noneAsked(ctx, tag);
        if (vp.width === 1280) await clicked(ctx, page, `footer.g-foot a[href="${GITHUB}"]`, GITHUB, tag + ' GitHub');
        await ctx.close();
      }
    }
  } finally {
    await Deno.remove(WORK, {recursive: true}).catch(() => {});
  }
}

// ======== a right-to-left page, as a stand-in ========
async function partRtl(B) {
  console.log('\n== rtl: the hub, with dir=rtl put on by hand');
  // The hub's words are English on a page with lang="en", and the toolbox has
  // no interface language to choose, so there is no right-to-left hub to open.
  // What can be checked is that nothing in the two lines assumes left to right.
  for (const vp of [{width: 1280, height: 800}, {width: 390, height: 844, touch: true}]) {
    const ctx = await newContext(vp);
    const page = await newPage(ctx, vp, 'rtl');
    await page.goto(B + '/');
    await page.evaluate(() => { document.documentElement.dir = 'rtl'; });
    await settle(page);
    let m = await measure(page, '.hub-browser .foot', 'a[href^="https://"]');
    eq(m.dir, 'rtl', `${vp.width}px: the page is right to left`);
    checkFoot(m, `${vp.width}px browser foot, rtl`);
    await shot(page, `rtl-hub-browser-${vp.width}`);
    await page.evaluate(() => Parseh.mode.set('mobile'));
    await settle(page);
    m = await measure(page, '.hub-mobile .m-by');
    checkFoot(m, `${vp.width}px phone hub line, rtl`, {finger: 48});
    // the links swap sides: GitHub, first in the document, is on the right
    assert(m.links[0].l > m.links[1].l, `${vp.width}px: in a right-to-left page GitHub is on the right of the website (${Math.round(m.links[0].l)} > ${Math.round(m.links[1].l)})`);
    await shot(page, `rtl-hub-mobile-${vp.width}`);
    await ctx.close();
  }
}

let hub = null;
try {
  if (PARTS.some(p => ['hub', 'mobile', 'settings', 'licences', 'rtl'].includes(p))) hub = await bootHub();
  if (PARTS.includes('hub')) await partHub(hub.B);
  if (PARTS.includes('mobile')) await partMobile(hub.B);
  if (PARTS.includes('settings')) await partSettings(hub.B);
  if (PARTS.includes('licences')) await partLicences(hub.B);
  if (PARTS.includes('guide')) await partGuide();
  if (PARTS.includes('rtl')) await partRtl(hub.B);
  assert(errors.length === 0, 'no page error: ' + errors.join(' | '));
  if (hub) assert(!/Traceback/.test(hub.log.join('')), 'no traceback in the hub\'s log');
  console.log(`\n${passed} checks passed`);
} catch (e) {
  if (hub) console.log('hub log tail:\n' + hub.log.join('').slice(-2000));
  throw e;
} finally {
  if (hub) await hub.stop();
  await browser.close();
}

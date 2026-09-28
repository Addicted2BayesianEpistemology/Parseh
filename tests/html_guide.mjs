// SPDX-License-Identifier: GPL-3.0-or-later
import { chromium } from 'npm:playwright-core@1.52.0';
import jsQR from 'npm:jsqr@1.4.0';
// Run: CHROME_BIN=/path/to/chrome PARSEH_PYTHON=/path/to/python3 deno run --allow-all tests/html_guide.mjs
//
// THE HTML GUIDE, READ THE THREE WAYS IT IS READ.  A copy of html-guide/ is
// made in a temporary tree beside the live studio (markdown/exlex,
// markdown/app and lib/, symlinked), so that nothing is written into the
// repository, and is then read:
//
//   1. straight off the disk (file://), compiled by html-guide/build.py, on a
//      desktop window and on a phone: the list of pages, the sidebar closed and
//      remembered, the drawer, the three themes, the Copy button, the search,
//      an exercise answered and a flashcard turned, the formulas, the QR code
//      (decoded), a picture opened large, a term's two definitions, and the
//      YouTube video, which plays in the page only when it was served: a
//      card that opens it on YouTube in its place, its words whole on a
//      phone;
//   2. through the Parseh server (serve.main, plain http, the guide's own
//      directory pointed at a second copy that has never been compiled): the
//      hub's guide button, the front page's "Compile the guide" button driven
//      to its end -- on the page's "Working…" pill, the server's list and the
//      hub's panel while it runs -- a page changed and the "older pages"
//      button, the real clipboard, the theme shared with the hub, the YouTube
//      player kept,
//      and what may not be fetched;
//   3. as GitHub Pages publishes it: build.py --pages, served under
//      /Parseh/ by a static server that knows nothing of Parseh -- and under
//      /guide/ too, where a website would put it, which must not make the
//      pages take that server for Parseh.
//
// Every check is on what the browser drew -- computed styles, rectangles,
// elementFromPoint, the clipboard's text -- not on what the HTML says.
const root = await Deno.realPath(new URL('..', import.meta.url));
Deno.chdir(root);
const PY = Deno.env.get('PARSEH_PYTHON') || 'python3';
const td = new TextDecoder();
let passed = 0;
const failed = [];
const assert = (v, m) => { if (v) { passed++; console.log('  ok', m); } else { failed.push(m); console.log('  FAIL', m); } };
const sleep = ms => new Promise(r => setTimeout(r, ms));
async function until(fn, what, ms = 20000) {
  const t = Date.now();
  for (;;) {
    let v = null;
    try { v = await fn(); } catch (_) { v = null; }
    if (v) return v;
    if (Date.now() - t > ms) throw Error('timed out: ' + what);
    await sleep(100);
  }
}
// On the front page: where the ink of the Persian word above the heading
// ends, and where the heading's begins.  Each element's baseline is where a
// zero-size inline-block set in it sits; the ink reaches below or above it
// by what the canvas measures in the element's own font.  (Nastaliq hangs
// its dots far below the line: they once sat on the heading's "h".)
const heroInk = () => {
  const ink = (el, below) => {
    const probe = document.createElement('i');
    probe.style.cssText = 'display:inline-block;width:0;height:0;vertical-align:baseline';
    el.appendChild(probe);
    const base = probe.getBoundingClientRect().bottom;
    probe.remove();
    const cs = getComputedStyle(el), c = document.createElement('canvas').getContext('2d');
    c.font = `${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
    const m = c.measureText(el.textContent.trim());
    return below ? base + m.actualBoundingBoxDescent : base - m.actualBoundingBoxAscent;
  };
  return [ink(document.querySelector('.g-hero-fa'), true), ink(document.querySelector('.g-hero h1'), false),
          document.fonts.check('46px "Noto Nastaliq Urdu"')];
};
// The bar on a phone: every button of it inside the window, the theme
// button what a tap on its middle reaches -- and no PDF manual, which is
// gone (the guide is the manual).
const barFits = () => {
  const t = document.querySelector('.g-top .g-theme'), r = t.getBoundingClientRect();
  const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
  const inside = [...document.querySelectorAll('.g-top > a, .g-top > button')].filter(e => !e.hidden)
    .every(e => { const q = e.getBoundingClientRect(); return q.left >= 0 && q.right <= innerWidth; });
  return [!!(hit && hit.closest('.g-theme')) && inside, !document.querySelector('.g-pdf, [data-guide-manual]'),
          Math.round(r.left), Math.round(r.right)];
};
// The showcase's YouTube video, as drawn: off the disk a card in the
// player's place (YouTube's player says only "Error 153" to a page that
// sends no Referer), on the screen and what a tap on its middle reaches,
// with the line under the figure; served, the player itself.
const youtube = async page => {
  const fig = page.locator('figure.video').first();
  await fig.scrollIntoViewIfNeeded();
  return fig.evaluate(f => {
    const a = f.querySelector('a.g-yt'), note = f.querySelector('.g-yt-note');
    const r = a ? a.getBoundingClientRect() : null;
    const hit = r && document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
    return {player: !!f.querySelector('iframe[src*="youtube"]'), card: !!a,
            href: a && a.href, target: a && a.target, say: a && a.innerText.trim(),
            onTop: !!(hit && hit.closest('a.g-yt')), inside: !!r && r.width > 150 && r.top >= 0 && r.bottom <= innerHeight,
            note: note && note.getBoundingClientRect().height > 0 ? note.innerText : null};
  });
};
// The card's label, as drawn: every word it shows shown whole (none cut
// off at the card's edge), on one line inside the card and clear of the
// play mark -- and the clip's start, read off the card's own address,
// among those words.
const ytLabel = async page => {
  const fig = page.locator('figure.video').first();
  await fig.scrollIntoViewIfNeeded();
  return fig.evaluate(f => {
    const a = f.querySelector('a.g-yt'), s = a.querySelector('.g-yt-say'), mark = a.querySelector('.g-yt-play');
    const [ra, rs, rm] = [a, s, mark].map(e => e.getBoundingClientRect());
    const t = +((/[?&]t=(\d+)s/.exec(a.href) || [])[1] || 0);
    return {say: s.innerText.trim(), card: Math.round(ra.width), shown: s.clientWidth, needs: s.scrollWidth,
            start: t ? Math.floor(t / 60) + ':' + String(t % 60).padStart(2, '0') : null,
            oneLine: rs.height < 2 * parseFloat(getComputedStyle(s).lineHeight),
            inCard: rs.left >= ra.left && rs.right <= ra.right && rs.top >= ra.top && rs.bottom <= ra.bottom,
            clear: getComputedStyle(mark).display === 'none' || rs.right <= rm.left || rs.left >= rm.right ||
                   rs.bottom <= rm.top || rs.top >= rm.bottom};
  });
};
// What a LaTeX drawing puts on the sheet, as the screen shows it: a screenshot
// of the element, read back through a canvas -> how many of its pixels stand
// apart from the sheet's own colour, and the lightest and the darkest of
// them.  (A drawing is black on nothing: on the dark sheet it is turned to
// the ink, or it is not there.)
const inkOf = async (page, locator) => {
  await locator.scrollIntoViewIfNeeded();
  const png = (await locator.screenshot()).toString('base64');
  return page.evaluate(async b64 => {
    const img = new Image();
    img.src = 'data:image/png;base64,' + b64;
    await img.decode();
    const c = document.createElement('canvas');
    c.width = img.width; c.height = img.height;
    const x = c.getContext('2d');
    x.drawImage(img, 0, 0);
    const d = x.getImageData(0, 0, c.width, c.height).data;
    const bg = [d[0], d[1], d[2]];
    let ink = 0, lightest = 0, darkest = 255;
    for (let i = 0; i < d.length; i += 4) {
      const diff = Math.max(Math.abs(d[i] - bg[0]), Math.abs(d[i + 1] - bg[1]), Math.abs(d[i + 2] - bg[2]));
      if (diff < 90) continue;
      ink++;
      const l = (d[i] + d[i + 1] + d[i + 2]) / 3;
      lightest = Math.max(lightest, l); darkest = Math.min(darkest, l);
    }
    return {ink, lightest, darkest, bg, w: c.width, h: c.height};
  }, png);
};
function freePort() {
  const l = Deno.listen({hostname: '127.0.0.1', port: 0});
  const p = l.addr.port;
  l.close();
  return p;
}
async function run(args, opts = {}) {
  const o = await new Deno.Command(args[0], {args: args.slice(1), stdout: 'piped', stderr: 'piped', ...opts}).output();
  return {code: o.code, out: td.decode(o.stdout) + td.decode(o.stderr)};
}

// ------------------------------------------------------------ the trees
const WORK = await Deno.makeTempDir({prefix: 'parseh-html-guide-'});
async function guideTree(name) {
  const base = `${WORK}/${name}`;
  await Deno.mkdir(`${base}/markdown`, {recursive: true});
  for (const d of ['markdown/exlex', 'markdown/app', 'lib']) await Deno.symlink(`${root}/${d}`, `${base}/${d}`);
  const r = await run(['cp', '-r', `${root}/html-guide`, `${base}/html-guide`]);
  if (r.code) throw Error(r.out);
  for (const d of ['site', 'engine/vendor']) await Deno.remove(`${base}/html-guide/${d}`, {recursive: true}).catch(() => {});
  return `${base}/html-guide`;
}
const DISK = await guideTree('disk');
{
  const r = await run([PY, `${DISK}/build.py`]);
  assert(r.code === 0 && /0 warnings, 0 errors/.test(r.out), 'build.py compiles the guide with no warning: ' + r.out.trim());
}
const showcaseSource = await Deno.readTextFile(`${DISK}/markdown/showcase.md`);
const pySource = showcaseSource.match(/```python[^\n]*\n([\s\S]*?)\n```/)[1];
// a block with a tab in it (a Makefile's recipe line), on the code-blocks page
const makeSource = (await Deno.readTextFile(`${DISK}/markdown/writing-this-guide/code-blocks.md`))
  .match(/```make\n([\s\S]*?)\n```/)[1];
const makeBlock = '.g-code:has(.g-code-lang:text-is("make"))';

const browser = await chromium.launch({executablePath: Deno.env.get('CHROME_BIN'), headless: true});
const children = [];
try {
  // ========================================================== 1. from the disk
  console.log('from the disk (file://), 1280x800');
  const ctx = await browser.newContext({viewport: {width: 1280, height: 800}});
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('requestfailed', r => { if (r.url().startsWith('file:')) errors.push('missing ' + r.url()); });
  const FILE = 'file://' + DISK;
  await page.goto(FILE + '/index.html');
  await page.evaluate(() => document.fonts.ready);
  {
    const [glyph, head, nastaliq] = await page.evaluate(heroInk);
    assert(nastaliq && glyph < head - 4, `the Persian word's dots stay above the heading: ink ends at ${Math.round(glyph)}, the heading's begins at ${Math.round(head)}`);
  }
  const nav = await page.$$eval('#g-nav a', as => as.map(a => a.textContent.trim()));
  assert(nav.includes('Writing this guide') && nav.includes('The showcase') && nav.includes('Code blocks'),
         'the front page draws the list of pages from site/nav.js: ' + nav.join(', '));
  assert(await page.$eval('[data-guide-compile]', b => b.hidden), 'and says nothing about compiling: it is compiled');
  const side = () => page.$eval('.g-side', s => { const r = s.getBoundingClientRect();
    return {w: r.width, left: r.left, right: r.right, shown: getComputedStyle(s).display !== 'none'}; });
  let s = await side();
  assert(s.shown && s.w > 200 && s.left >= 0, 'the sidebar stands on the left: ' + JSON.stringify(s));

  // the three themes
  const seen = [];
  for (let k = 0; k < 3; k++) {
    await page.click('[data-parseh-theme]');
    seen.push(await page.evaluate(() => [document.documentElement.dataset.theme, document.documentElement.dataset.sheet,
      getComputedStyle(document.body).backgroundColor, localStorage.getItem('parseh_theme')]));
  }
  assert(new Set(seen.map(x => x[0])).size === 3 && seen.every(x => ['light', 'dark', 'sepia'].includes(x[0]) && x[3] === x[0]),
         'the ◐ button cycles three themes, kept as parseh_theme: ' + seen.map(x => x[0]).join(' → '));
  assert(new Set(seen.map(x => x[2])).size === 3, 'and each paints another background: ' + seen.map(x => x[2]).join(' / '));
  assert(seen.every(x => x[1] === (x[0] === 'light' ? 'paper' : x[0])), 'with the studio\'s name for it beside it (data-sheet)');

  // the sidebar closed, remembered, opened again
  await page.click('[data-guide-side]');
  s = await side();
  assert(!s.shown, 'the ☰ button puts the sidebar away');
  await page.goto(FILE + '/site/showcase.html');
  s = await side();
  assert(!s.shown && await page.evaluate(() => document.documentElement.dataset.side === 'closed'),
         'and it stays away on the next page');
  await page.click('[data-guide-side]');
  s = await side();
  assert(s.shown && s.w > 200, 'and comes back');

  // a page: its section open, itself marked
  const here = await page.$eval('.g-side .g-here', a => [a.textContent, a.getAttribute('aria-current')]);
  assert(here[0] === 'The showcase' && here[1] === 'page', 'the page being read is marked in the list: ' + here);
  // the studio's sheet takes the theme too, in the studio's own colours
  // (app.css: paper #fff, sepia #f8f2e2, dark #211a1d)
  const sheets = {};
  for (let k = 0; k < 3; k++) {
    const t = await page.evaluate(() => document.documentElement.dataset.theme);
    sheets[t] = await page.evaluate(() => getComputedStyle(document.querySelector('.g-article .sheet')).backgroundColor);
    await page.click('[data-parseh-theme]');
  }
  assert(sheets.light === 'rgb(255, 255, 255)' && sheets.sepia === 'rgb(248, 242, 226)' && sheets.dark === 'rgb(33, 26, 29)',
         'the studio\'s sheet follows the theme: ' + JSON.stringify(sheets));
  const fonts = await page.evaluate(() => [getComputedStyle(document.querySelector('.g-article .sheet > p')).fontFamily,
    getComputedStyle(document.querySelector('.g-top')).fontFamily]);
  assert(/Pagella/.test(fonts[0]) && !/Pagella/.test(fonts[1]),
         'the text is set as the studio sets it, the chrome as the toolbox\'s: ' + fonts.join(' | '));

  // the video: from the disk, a card that opens it on YouTube
  {
    const v = await youtube(page);
    assert(!v.player && v.card && v.onTop && v.inside && v.target === '_blank' &&
           v.href === 'https://www.youtube.com/watch?v=aqz-KE-bpKQ&t=30s' && /^Watch on YouTube, from 0:30/.test(v.say),
           'off the disk the YouTube player is a card that opens the video on YouTube, from its start: ' + JSON.stringify(v));
    assert(/player works when the guide is served/.test(v.note || ''), 'with a line saying where it plays: ' + v.note);
  }

  // the formulas and the target language
  await until(() => page.$$eval('.g-article .math svg', x => x.length), 'MathJax draws the formulas');
  assert(true, 'the formulas are drawn by MathJax off the disk');
  const rtl = await page.$eval('.g-article .fa-par', p => [p.getAttribute('dir'), getComputedStyle(p).direction, getComputedStyle(p).textAlign]);
  assert(rtl[0] === 'rtl' && rtl[1] === 'rtl', 'a Persian paragraph is laid out right to left: ' + rtl);

  // an exercise answered and checked
  const water = page.locator('.exercise', {hasText: 'Which one means'});
  await water.locator('.ex-option[data-correct="1"]').click();
  await page.click('.ex-correct-all');
  const verdict = await water.evaluate(ex => ex.className);
  const score = await page.$eval('.ex-score', o => [o.hidden, o.textContent]);
  assert(/\bcorrect\b/.test(verdict) && !score[0] && /\d+ \/ \d+ correct/.test(score[1]),
         'a choice exercise is answered and marked by Check exercises: ' + verdict + ', ' + score[1]);
  // a blank filled by tapping, and a card turned
  const fill = page.locator('.exercise[data-subtype="fill-blanks"]').first();
  await fill.locator('.ex-bank .ex-item', {hasText: 'کتاب'}).click();
  await fill.locator('.ex-blank').click();
  assert(await fill.locator('.ex-blank .ex-item').count() === 1, 'a block goes into a blank with two taps');
  const card = page.locator('.ex-flashcard').first();
  await card.scrollIntoViewIfNeeded();
  const before = await card.locator('.ex-card-back').evaluate(b => b.hidden);
  await card.click();
  const after = await card.locator('.ex-card-back').evaluate(b => [b.hidden, getComputedStyle(b).display]);
  assert(before === true && after[0] === false && after[1] !== 'none', 'a flashcard turns over when clicked');
  const jaCard = page.locator('.g-example-out[data-lang="ja"] .ex-flashcard');
  assert(await jaCard.count() === 1, 'the Japanese example has its own flashcard, in its own language');

  // the Copy button: the exact source, no line numbers
  await page.evaluate(() => { window.__copied = null;
    navigator.clipboard.writeText = t => { window.__copied = t; return Promise.resolve(); }; });
  const pyBlock = page.locator('.g-code[data-code="python"]').first();
  await pyBlock.locator('.g-copy').click();
  const copied = await page.evaluate(() => window.__copied);
  assert(copied === pySource, 'Copy copies the block exactly as written: ' + JSON.stringify(copied));
  assert(await pyBlock.locator('.g-copy').textContent() === 'Copied', 'and says Copied');
  const lineNo = await pyBlock.locator('.g-ln').first().evaluate(n => getComputedStyle(n).userSelect);
  assert(lineNo === 'none', 'the line numbers cannot be selected either');

  // the QR code reads
  const qr = await page.$eval('.g-qr svg', svg => {
    const n = svg.viewBox.baseVal.width, cells = new Set();
    for (const m of svg.querySelector('path').getAttribute('d').matchAll(/M(\d+) (\d+)/g)) cells.add(m[1] + ',' + m[2]);
    return {n, cells: [...cells]};
  });
  {
    const S = 6, W = qr.n * S, px = new Uint8ClampedArray(W * W * 4).fill(255), on = new Set(qr.cells);
    for (let y = 0; y < qr.n; y++) for (let x = 0; x < qr.n; x++) if (on.has(x + ',' + y))
      for (let dy = 0; dy < S; dy++) for (let dx = 0; dx < S; dx++) {
        const i = ((y * S + dy) * W + x * S + dx) * 4; px[i] = px[i + 1] = px[i + 2] = 0; }
    const got = jsQR(px, W, W);
    assert(got && got.data === 'https://github.com', 'the QR code decodes to what it was given: ' + (got && got.data));
  }

  // a picture, large
  const gif = page.locator('.g-article img[src$="flashcard.gif"]');
  await gif.scrollIntoViewIfNeeded();
  await until(() => gif.evaluate(i => i.complete && i.naturalWidth > 0), 'the GIF loads');
  await gif.click();
  const box = await page.$eval('.g-lightbox img', i => { const r = i.getBoundingClientRect(); return [r.width, r.height]; });
  assert(box[0] > 300, 'a click on a picture opens it large: ' + box);
  await page.keyboard.press('Escape');
  assert(await page.$('.g-lightbox') === null, 'and Escape closes it');

  // headings carry their own address
  const anchor = await page.$eval('h2.section', h => [h.id, h.querySelector('.g-anchor').getAttribute('href')]);
  assert('#' + anchor[0] === anchor[1], 'a heading\'s # is its address: ' + anchor);

  // the search
  await page.fill('[data-guide-search]', 'nested fences');
  await until(() => page.$$eval('.g-results a', as => as.length), 'search results');
  const hits = await page.$$eval('.g-results a .g-r-t', ts => ts.map(t => t.textContent));
  assert(hits[0] === 'Code blocks', 'the search finds the page: ' + hits.join(', '));
  await page.press('[data-guide-search]', 'Enter');
  await page.waitForURL(/code-blocks\.html$/);
  assert(true, 'and Enter opens it');

  // a tab is a tab: drawn four columns wide, and copied as the tab it is
  await page.evaluate(() => { window.__copied = null;
    navigator.clipboard.writeText = t => { window.__copied = t; return Promise.resolve(); }; });
  await page.locator(makeBlock).locator('.g-copy').click();
  const copiedTab = await page.evaluate(() => window.__copied);
  assert(makeSource.includes('\t') && copiedTab === makeSource,
         'Copy copies a tab as a tab: ' + JSON.stringify(copiedTab));
  const tabWidth = await page.locator(makeBlock).evaluate(block => {
    const line = [...block.querySelectorAll('.g-line')].find(l => l.textContent.startsWith('\t'));
    const text = line.firstChild.nodeType === 3 ? line.firstChild : line.querySelector('*').firstChild;
    const r = document.createRange();
    const w = (a, b) => { r.setStart(text, a); r.setEnd(text, b); return r.getBoundingClientRect().width; };
    return [w(0, 1), w(1, 2)];
  });
  assert(Math.abs(tabWidth[0] - 4 * tabWidth[1]) < 1, 'and drawn four characters wide: ' + tabWidth.map(Math.round));

  // a term with two definitions: each definition on a line of its own, set
  // in under the term -- not run together on the term's line
  await page.goto(FILE + '/site/writing-this-guide/markdown.html');
  const defs = await page.$eval('.g-article dl.g-dl .di:has(dd + dd)', di => {
    const r = e => e.getBoundingClientRect();
    const [dt, a, b] = [di.querySelector('dt'), ...di.querySelectorAll('dd')].map(r);
    return {below: a.top >= dt.bottom - 1 && b.top >= a.bottom - 1, under: a.left > dt.left && b.left === a.left,
            at: [dt, a, b].map(q => [Math.round(q.left), Math.round(q.top)])};
  });
  assert(defs.below && defs.under, 'two definitions of a term stand on lines of their own, under it: ' + JSON.stringify(defs.at));
  assert(errors.length === 0, 'no script error and no missing file off the disk: ' + errors.join('; '));
  await ctx.close();

  // ------------------------------------------------------------ on a phone
  console.log('from the disk, 390x844 (a phone)');
  const phone = await browser.newContext({viewport: {width: 390, height: 844}, hasTouch: true, isMobile: true});
  const pp = await phone.newPage();
  await pp.goto(FILE + '/index.html');
  await pp.evaluate(() => document.fonts.ready);
  {
    const [glyph, head] = await pp.evaluate(heroInk);
    assert(glyph < head - 4, `and on a phone: ${Math.round(glyph)} / ${Math.round(head)}`);
    const bar = await pp.evaluate(barFits);
    assert(bar[0] && bar[1], 'the front page\'s bar fits a phone, and has no PDF button: ' + bar);
  }
  await pp.goto(FILE + '/site/showcase.html');
  {
    const bar = await pp.evaluate(barFits);
    assert(bar[0] && bar[1], 'and so does a compiled page\'s: ' + bar);
  }
  const off = await pp.$eval('.g-side', s => s.getBoundingClientRect().right);
  assert(off <= 0, 'the sidebar waits off the screen: its right edge at ' + off);
  // no page is wider than the phone: a sideways scroll is what a phone
  // layout must never have
  const every = await pp.$$eval('#g-nav a', as => as.map(a => a.href));
  const widths = [];
  for (const url of [FILE + '/index.html', ...every]) {
    await pp.goto(url);
    widths.push([url.split('/').pop(), await pp.evaluate(() => document.documentElement.scrollWidth)]);
  }
  assert(widths.every(w => w[1] <= 390), 'no page is wider than the phone: ' + widths.map(w => w.join(' ')).join(', '));
  await pp.goto(FILE + '/site/showcase.html');
  await pp.tap('[data-guide-side]');
  await sleep(350);
  const drawer = await pp.$eval('.g-side', s => { const r = s.getBoundingClientRect(); return [r.left, r.right]; });
  const inside = await pp.evaluate(([x]) => !!document.elementFromPoint(x, 300).closest('.g-side'), [Math.floor(drawer[1] / 2)]);
  assert(drawer[0] >= 0 && drawer[1] <= 390 && inside, 'the ☰ button slides the drawer over the page: ' + drawer);
  await pp.tap('.g-backdrop', {position: {x: 20, y: 400}}).catch(async () => { await pp.mouse.click(380, 400); });
  await sleep(350);
  const gone = await pp.$eval('.g-side', s => s.getBoundingClientRect().right);
  assert(gone <= 0, 'a tap beside it closes it');
  const topHit = await pp.evaluate(() => !!document.elementFromPoint(20, 20).closest('.g-top'));
  assert(topHit, 'the bar is on top of the page');
  const choice = pp.locator('.exercise', {hasText: 'Which one means'});
  await choice.locator('.ex-option[data-correct="1"]').scrollIntoViewIfNeeded();
  await choice.locator('.ex-option[data-correct="1"]').tap();
  assert(await choice.locator('.ex-option.selected').count() === 1, 'an exercise answers to a tap');
  // the YouTube card on a phone, where a video 70% wide is a card of
  // 180-230px: its label once ran out of room there and was cut to
  // "Watch on YouTube, from 0:…", the start time lost
  for (const width of [390, 360]) {
    await pp.setViewportSize({width, height: 780});
    for (const pg of ['showcase.html', 'dialect/media.html']) {
      await pp.goto(FILE + '/site/' + pg);
      const l = await ytLabel(pp);
      assert(l.needs <= l.shown && l.oneLine && l.inCard && l.clear && !!l.start && l.say.includes(l.start),
             `on a ${width}px phone the card on ${pg} shows its label whole, with the start: ` + JSON.stringify(l));
    }
  }
  await phone.close();

  // ------------------------------------------------------------ LaTeX drawings
  // The guide has no TeX while it compiles: its latex blocks and marks are
  // pictures made beforehand (build.py --draw).  Each is read as a reader
  // sees it -- drawn, in a box with the source beside it as every other
  // example is, and visible on all three sheets (a drawing is black on
  // nothing, and on the dark sheet it once was not there).
  console.log('the LaTeX drawings, off the disk: three themes, a desktop and a phone');
  {
    const PAGES = ['dialect/latex-drawings.html', 'dialect-exercises/latex.html'];
    const loadAll = p => p.evaluate(async () => {
      const imgs = [...document.images];
      imgs.forEach(i => { i.loading = 'eager'; });
      await Promise.all(imgs.map(i => i.complete ? 0 : new Promise(r => { i.onload = i.onerror = r; })));
    });
    const facts = p => p.evaluate(() => {
      const r = e => { const q = e.getBoundingClientRect(); return [q.left, q.top, q.right, q.bottom]; };
      const pics = [...document.querySelectorAll('.g-article figure.latex img, .g-article img.latex-inline')];
      const looks = e => { const s = getComputedStyle(e); return [s.borderTopWidth, s.borderTopStyle, s.borderTopLeftRadius,
                                                                  s.backgroundColor, s.overflow]; };
      const examples = [...document.querySelectorAll('.g-article .g-example')].filter(e => e.querySelector('.g-example-out figure.latex, .g-example-out img.latex-inline'));
      const pair = e => {
        const [ex, code, out] = [r(e), r(e.querySelector('.g-code')), r(e.querySelector('.g-example-out'))];
        const pic = r(e.querySelector('.g-example-out figure.latex img, .g-example-out img.latex-inline'));
        const tol = 1.5;
        return {codeAbove: code[3] <= out[1] + tol, picInOut: pic[0] >= out[0] - tol && pic[2] <= out[2] + tol && pic[1] >= out[1] - tol && pic[3] <= out[3] + tol,
                outInBox: out[0] >= ex[0] - tol && out[2] <= ex[2] + tol && out[3] <= ex[3] + tol,
                label: e.querySelector('.g-example-label').textContent, room: ex[3] - pic[3],
                source: e.querySelector('.g-code').dataset.code, looks: looks(e), outPad: getComputedStyle(e.querySelector('.g-example-out')).padding};
      };
      const chips = [...document.querySelectorAll('.g-article .exercise .ex-item, .g-article .exercise .ex-option, .g-article .exercise .ex-match-drop')];
      return {
        loaded: pics.every(i => i.complete && i.naturalWidth > 0 && (!i.offsetParent || i.getBoundingClientRect().height > 0)), pics: pics.length,
        blocks: examples.filter(e => e.querySelector('.g-example-out figure.latex')).length,
        marks: examples.filter(e => e.querySelector('.g-example-out img.latex-inline')).length,
        loose: [...document.querySelectorAll('figure.latex')].filter(f => !f.closest('.g-example-out')).length,
        pairs: examples.map(pair),
        frames: document.querySelectorAll('.latex-fail, .latex-inline-src').length,
        saysNotDrawn: /shown here as it is written/.test(document.body.innerText),
        rawInChips: chips.filter(c => /[$\\]/.test(c.innerText)).length, chips: chips.length,
        wide: document.documentElement.scrollWidth,
      };
    });
    for (const [device, viewport] of [['desktop', {width: 1280, height: 900}], ['phone', {width: 390, height: 844}]]) {
      for (const theme of ['light', 'sepia', 'dark']) {
        const c = await browser.newContext({viewport});
        await c.addInitScript(t => { try { localStorage.setItem('parseh_theme', t); localStorage.setItem('parseh_guide_side', 'closed'); } catch (_) {} }, theme);
        const lp = await c.newPage();
        const errs = [];
        lp.on('pageerror', e => errs.push(e.message));
        lp.on('requestfailed', r => { if (r.url().startsWith('file:')) errs.push('missing ' + r.url()); });
        const tag = `${device}, ${theme}`;
        await lp.goto(FILE + '/site/dialect/mathematics.html');
        const mathLooks = await lp.evaluate(() => { const e = document.querySelector('.g-article .g-example'), s = getComputedStyle(e);
          return [[s.borderTopWidth, s.borderTopStyle, s.borderTopLeftRadius, s.backgroundColor, s.overflow],
                  getComputedStyle(e.querySelector('.g-example-out')).padding]; });
        for (const pg of PAGES) {
          await lp.goto(FILE + '/site/' + pg);
          await loadAll(lp);
          assert(await lp.evaluate(() => document.documentElement.dataset.theme) === theme, `${tag}: ${pg} is read on the ${theme} sheet`);
          const f = await facts(lp);
          assert(f.loaded && f.pics >= 5 && f.frames === 0 && !f.saysNotDrawn,
                 `${tag}: ${pg} shows its ${f.pics} drawings as pictures, none as a frame or as its LaTeX ("shown here as it is written")`);
          assert(f.wide <= viewport.width, `${tag}: ${pg} does not scroll sideways: ${f.wide}`);
          assert(f.rawInChips === 0, `${tag}: ${pg}: no chip, option or pair shows raw LaTeX (${f.chips} looked at)`);
          assert(f.pairs.length > 0 && f.pairs.every(x => x.codeAbove && x.picInOut && x.outInBox && x.label === 'Result' && x.source === 'parseh' && x.room > 3),
                 `${tag}: ${pg}: each of its ${f.pairs.length} examples is the source above and the enlarged box round the result: ` +
                 JSON.stringify(f.pairs.filter(x => !(x.codeAbove && x.picInOut && x.outInBox && x.room > 3)).slice(0, 2)));
          assert(f.pairs.every(x => JSON.stringify(x.looks) === JSON.stringify(mathLooks[0]) && x.outPad === mathLooks[1]),
                 `${tag}: ${pg}: the box is the one the mathematics page's pairs have: ` + JSON.stringify([f.pairs[0].looks, f.pairs[0].outPad]));
          if (pg.startsWith('dialect/')) {
            assert(f.blocks === 3 && f.marks === 2 && f.loose === 0,
                   `${tag}: the dialect page has its three blocks and two marks as pairs, and no picture loose beside them: ${f.blocks}/${f.marks}/${f.loose}`);
          }
        }
        // pixels: the drawings are there on this sheet, as the screen draws them
        await lp.goto(FILE + '/site/dialect/latex-drawings.html');
        await loadAll(lp);
        const block = await inkOf(lp, lp.locator('.g-example-out figure.latex').first());
        const mark = await inkOf(lp, lp.locator('.g-example-out img.latex-inline').first());
        const seen = x => x.ink > 20 && (theme === 'dark' ? x.lightest > 150 : x.darkest < 90);
        assert(seen(block) && seen(mark),
               `${tag}: a block and a mark are visible on the ${theme} sheet (${theme === 'dark' ? 'light' : 'dark'} ink on ${block.bg}): ` +
               JSON.stringify([block.ink, block.lightest, block.darkest, mark.ink, mark.lightest, mark.darkest]));
        // the exercises, driven: a two-blank fill-in, by drag, by cloud and by keyboard
        if (device === 'desktop' && theme !== 'sepia') {
          await lp.goto(FILE + '/site/dialect-exercises/latex.html');
          await loadAll(lp);
          const fill = lp.locator('.exercise[data-subtype="fill-blanks"]').first();
          await fill.scrollIntoViewIfNeeded();
          const item = src => fill.locator(`.ex-bank .ex-item:has(img[data-latex-src="${src}"])`);
          const blank = n => fill.locator(`.ex-blank[data-slot="${n}"]`);
          assert(await fill.locator('.ex-blank').count() === 2 && await fill.locator('.ex-bank .ex-item').count() === 4,
                 `${tag}: the fill-in has two blanks and four blocks, all drawings`);
          await item('$1$').dragTo(blank('first'));
          await blank('second').click();
          await fill.locator('.ex-cloud-pick:has(img[data-latex-src="$0$"])').click();
          assert(await blank('first').locator('img').count() === 1 && await blank('second').locator('img').count() === 1 &&
                 await fill.locator('.ex-bank .ex-item').count() === 2,
                 `${tag}: a block dragged into the first blank, another chosen from the second blank's cloud`);
          await lp.click('.ex-correct-all');
          const good = await fill.evaluate(e => e.className);
          assert(/\bcorrect\b/.test(good) && await blank('first').evaluate(e => e.classList.contains('answer-correct')) &&
                 await blank('second').evaluate(e => e.classList.contains('answer-correct')),
                 `${tag}: Check exercises marks both blanks right, by what was written and not by the pictures: ` + good);
          await lp.reload();
          await loadAll(lp);
          const again = lp.locator('.exercise[data-subtype="fill-blanks"]').first();
          const two = again.locator('.ex-bank .ex-item:has(img[data-latex-src="$2$"])');
          await again.scrollIntoViewIfNeeded();
          await two.focus();
          await lp.keyboard.press('Enter');
          const picked = await two.evaluate(e => e.classList.contains('picked'));
          await again.locator('.ex-blank[data-slot="first"]').focus();
          await lp.keyboard.press('Enter');
          assert(picked && await again.locator('.ex-blank[data-slot="first"] .ex-item').count() === 1,
                 `${tag}: from the keyboard, Enter picks a block and Enter on a blank puts it there`);
          await lp.click('.ex-correct-all');
          assert(await again.evaluate(e => e.classList.contains('incorrect')) &&
                 await again.locator('.ex-blank[data-slot="first"]').evaluate(e => e.classList.contains('answer-wrong')),
                 `${tag}: and a wrong block is marked wrong`);
          // a Jolly card holding a block turns over, its back drawn too
          const card = lp.locator('.ex-flashcard').nth(1);
          await card.scrollIntoViewIfNeeded();
          const shown = await card.locator('figure.latex img').first().evaluate(i => i.complete && i.naturalWidth > 0);
          await card.click();
          const backText = await card.locator('.ex-card-back').innerText();
          assert(shown && /aspirin/.test(backText) && await card.locator('.ex-card-back img.latex-inline').count() === 1,
                 `${tag}: a Jolly card with a drawing on its front turns over to "aspirin" and a drawn formula: ` + backText.trim().replace(/\s+/g, ' '));
        }
        assert(errs.length === 0, `${tag}: no script error and no missing file: ` + errs.join('; '));
        await c.close();
      }
    }
    // a computer that is set to dark and a reader who has not chosen: the
    // same, by the system's own word
    {
      const c = await browser.newContext({viewport: {width: 1280, height: 900}, colorScheme: 'dark'});
      const lp = await c.newPage();
      await lp.goto(FILE + '/site/dialect/latex-drawings.html');
      await loadAll(lp);
      const auto = await lp.evaluate(() => [document.documentElement.dataset.theme || 'auto', document.documentElement.dataset.sheet]);
      const block = await inkOf(lp, lp.locator('.g-example-out figure.latex').first());
      const mark = await inkOf(lp, lp.locator('.g-example-out img.latex-inline').first());
      assert(auto.join() === 'auto,dark' && block.ink > 20 && block.lightest > 150 && mark.ink > 20 && mark.lightest > 150,
             'with the system set to dark and no theme chosen, the drawings are visible too: ' + JSON.stringify([auto, block.ink, block.lightest, mark.ink, mark.lightest]));
      await c.close();
    }
  }

  // ========================================================== 2. through Parseh
  console.log('through the Parseh server');
  const SERVED = await guideTree('served');
  const TREE = `${WORK}/server`;
  for (const d of ['tray', 'library', 'exercises', 'anki', 'root/youtube/videos']) await Deno.mkdir(`${TREE}/${d}`, {recursive: true});
  // the hub's own files (/lib/parseh.js, the palette) come from the tree's root
  await Deno.symlink(`${root}/lib`, `${TREE}/root/lib`);
  const port = freePort();
  const SERVE = String.raw`
import sys
from pathlib import Path
sys.path[:0] = ['markdown/exlex', 'markdown/app', 'youtube/lib', 'lib', '.']
tmp, port, guide = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
import clips, decks, store
clips.set_dir(tmp / 'tray')
import serve, ytpages, guidebuild
for st in {store, serve.studio.store}:
    st.LIB = tmp / 'library'
    st.set_clips_dir(tmp / 'tray')
decks.set_dir(tmp / 'exercises')
decks.set_clips_dir(tmp / 'tray')
# WHAT THIS MACHINE KEEPS, into the temporary tree (lib/prefs.py, and
# lib/network.py since the network settings): a suite must never read the
# owner's own reading places, theme or network doors -- nor write them, which
# is what happened here: a suite turned the theme to dark in the real
# config/prefs.json and every page of the next suite opened dark.
import prefs
import network
prefs.STORE = str(tmp / 'config' / 'prefs.json')
network.STORE = str(tmp / 'config' / 'network.json')
# and the LaTeX drawings' themes, their drawings and their packages
import latexthemes, latexdraw, texpackages
latexthemes.STORE = str(tmp / 'config' / 'latex.json')
latexdraw.DRAWN = str(tmp / 'latex-drawn')
texpackages.TREE = str(tmp / 'texmf')
import offline  # the phone-keeping memories (lib/offline.py) too
offline.DIGESTS = str(tmp / 'config' / 'digests.json')
offline.WHERES = str(tmp / 'config' / 'wheres.json')
serve.ROOT = str(tmp / 'root')
serve._AtRoot.directory = str(tmp / 'root')
ytpages.VIDEOS = str(tmp / 'root' / 'youtube' / 'videos')
serve.ANKI = ytpages.ANKI = str(tmp / 'anki')
ytpages.INBOX = str(tmp / 'anki' / 'inbox')
guidebuild.GUIDE = guide
# a compile takes about a second here, less than the hub's quickest poll
# (1.5 s): two seconds more, so the hub is seen listing it while it runs
_command = guidebuild.command
guidebuild.command = lambda guide=None: [sys.executable, '-c',
    'import subprocess, sys, time; time.sleep(2); sys.exit(subprocess.call(sys.argv[1:]))'] + _command(guide)
sys.argv = ['serve.py', '--http', '--local', port]
serve.main()
`;
  const log = [];
  const hub = new Deno.Command(PY, {args: ['-c', SERVE, TREE, String(port), SERVED], cwd: root, stdout: 'piped', stderr: 'piped'}).spawn();
  children.push(hub);
  for (const st of [hub.stdout, hub.stderr]) (async () => { for await (const c of st.pipeThrough(new TextDecoderStream())) log.push(c); })();
  const B = `http://127.0.0.1:${port}`;
  await until(async () => { const r = await fetch(B + '/guide/__status'); const j = await r.json(); return r.ok && j.parseh; },
              'the server answers', 60000);
  const sctx = await browser.newContext({viewport: {width: 1280, height: 800}});
  await sctx.grantPermissions(['clipboard-read', 'clipboard-write'], {origin: B});
  const sp = await sctx.newPage();
  const serr = [];
  sp.on('pageerror', e => serr.push(e.message + ' on ' + sp.url()));
  // (a guide never compiled has no site/ yet: its nav.js and the fonts the
  // front page would take from there are missing, which is how it finds out)
  let compiled = false;
  sp.on('response', r => { if (r.status() >= 400 && r.url().startsWith(B)
    && !(!compiled && r.url().startsWith(B + '/guide/site/'))) serr.push(r.status() + ' ' + r.url()); });
  await sp.goto(B + '/');
  const btn = await sp.$eval('.parseh-bar .parseh-btn', a => [a.textContent, a.getAttribute('href')]);
  assert(btn[0] === 'guide' && btn[1] === '/guide/', 'the hub\'s guide button leads to the HTML guide: ' + btn);
  {
    const r = await fetch(B + '/guide/site/showcase.html', {redirect: 'manual'});
    await r.body?.cancel();
    assert(r.status === 302 && r.headers.get('location') === '/guide/',
           'a page of a guide never compiled leads to its front page: ' + r.status);
  }
  await sp.click('.parseh-bar .parseh-btn');
  await sp.waitForURL(B + '/guide/');
  const notice = await until(() => sp.$eval('[data-guide-compile]', b => !b.hidden && b.textContent), 'the compile notice');
  assert(/has not been compiled yet/.test(notice), 'a guide never compiled says so: ' + notice.slice(0, 60));
  // the compile is work like any other: on the server's list while it runs,
  // on this page's "Working…" pill from the click, and on the hub, open in
  // a second tab, in its panel
  const hubTab = await sctx.newPage();
  hubTab.on('pageerror', e => serr.push(e.message + ' on the hub'));
  await hubTab.goto(B + '/');
  await hubTab.waitForFunction(() => !!window.ParsehActivity, null, {timeout: 10000});
  // what the hub's panel says, every 50 ms, kept by the hub itself
  await hubTab.evaluate(() => {
    window.__said = [];
    window.__saying = setInterval(() => {
      const s = document.getElementById('parseh-working');
      const t = s && !s.hidden ? s.textContent.replace(/\s+/g, ' ').trim() : '';
      if (t && window.__said[window.__said.length - 1] !== t) window.__said.push(t);
    }, 50);
  });
  const loaded = await sp.waitForFunction(() => !!window.ParsehActivity, null, {timeout: 10000}).then(() => true, () => false);
  assert(loaded, 'served by Parseh, the guide\'s front page loads the activity list (/lib/activity.js)');
  const listed = [];
  let listening = true;
  const listen = (async () => {
    while (listening) {
      try {
        const j = await (await fetch(B + '/__activity')).json();
        for (const e of j.running.concat(j.finished)) if (e.kind === 'compile') listed.push([e.label, e.page, e.finished ? 'finished' : 'running']);
      } catch (_) { /* the server is busy */ }
      await sleep(40);
    }
  })();
  const pillAtClick = await sp.evaluate(() => {
    document.querySelector('[data-guide-compile] [data-compile]').click();
    const e = document.querySelector('#parseh-activity .pa-pill');
    return e && !e.closest('[hidden]') ? e.textContent.replace(/\s+/g, ' ').trim() : null;
  });
  await sp.waitForFunction(() => document.querySelectorAll('#g-nav a').length > 3, null, {timeout: 60000});
  const hubSaid = await until(() => hubTab.evaluate(() =>
    window.__said.some(t => /^Done: Compiling the guide/.test(t)) && window.__said), 'the hub says it is done', 10000)
    .catch(() => hubTab.evaluate(() => window.__said));
  compiled = true;
  listening = false;
  await listen;
  assert(pillAtClick === 'Working: Compiling the guide', 'the guide\'s front page shows its compile on its pill at the click: ' + pillAtClick);
  assert(listed.some(x => x[0] === 'Compiling the guide' && x[1] === '/guide/' && x[2] === 'running') &&
         listed.some(x => x[2] === 'finished'),
         'the server lists it while it runs, and then as finished: ' + JSON.stringify([...new Set(listed.map(x => x.join(' ')))]));
  assert(hubSaid.some(t => /^Working… 1 task running\s*Compiling the guide/.test(t)) && /^Done: Compiling the guide/.test(hubSaid[hubSaid.length - 1]),
         'and the hub, in another tab, lists it in its panel while it runs, then says it is done: ' + JSON.stringify(hubSaid));
  await hubTab.close();
  assert(await sp.$eval('[data-guide-compile]', b => b.hidden), 'Compile the guide compiles it, and the page opens the result');
  const early = await fetch(B + '/guide/site/nav.js');
  await early.body?.cancel();
  assert(early.status === 200, 'site/nav.js is there now');
  const st1 = await (await fetch(B + '/guide/__status')).json();
  assert(st1.built && st1.stale === false && st1.ok === true, 'the server says it is compiled and up to date: ' + JSON.stringify({built: st1.built, stale: st1.stale, ok: st1.ok}));
  await Deno.writeTextFile(`${SERVED}/markdown/showcase.md`, '\nA line added after the compile.\n', {append: true});
  await sp.reload();
  const older = await until(() => sp.$eval('[data-guide-compile]', b => !b.hidden && b.textContent), 'the older-pages notice');
  assert(/older pages/.test(older), 'a page changed since: the front page offers to compile again');
  await sp.click('[data-guide-compile] [data-compile]');
  await until(async () => (await (await fetch(B + '/guide/__status')).json()).stale === false, 'the second compile');
  await sp.waitForFunction(() => document.querySelector('[data-guide-compile]').hidden, null, {timeout: 30000});
  assert(true, 'and compiles it again');

  await sp.goto(B + '/guide/site/showcase.html');
  // (once the server has said it is Parseh)
  const hubShown = await until(() => sp.$eval('.g-hub', a => !a.hidden), 'the way back to Parseh', 5000).catch(() => false);
  assert(hubShown, 'served, the way back to Parseh shows');
  {
    // the PDF manual's old address, kept in somebody's bookmarks, goes on to
    // the guide, which is the manual now
    const r = await fetch(B + '/guide.pdf', {redirect: 'manual'});
    await r.body?.cancel();
    const to = r.headers.get('location') || '';
    assert(r.status === 302 && new URL(to, B).pathname === '/guide/',
           'the PDF manual\'s old address goes on to the guide: ' + r.status + ' ' + to);
  }
  {
    // on a phone, the bar holds the way back to Parseh too
    const ph = await browser.newContext({viewport: {width: 390, height: 844}, hasTouch: true, isMobile: true});
    const php = await ph.newPage();
    await php.goto(B + '/guide/site/showcase.html');
    await until(() => php.$eval('.g-hub', a => !a.hidden), 'the hub button', 5000).catch(() => null);
    const bar = await php.evaluate(barFits);
    const hub = await php.$eval('.g-hub', a => !a.hidden);
    assert(hub && bar[0] && bar[1] && await php.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
           'served, on a phone, the bar holds Parseh and ◐ inside the window: ' + bar);
    await ph.close();
  }
  const added = await sp.evaluate(() => document.querySelector('.g-article').textContent.includes('A line added after the compile.'));
  assert(added, 'the page shows the line added before the second compile');
  const block = sp.locator('.g-code[data-code="python"]').first();
  await block.locator('.g-copy').click();
  await until(() => block.locator('.g-copy').textContent().then(t => t === 'Copied'), 'Copied');
  const clip = await sp.evaluate(() => navigator.clipboard.readText());
  assert(clip === pySource, 'the real clipboard holds the exact block: ' + JSON.stringify(clip));
  {
    const cp = await sctx.newPage();
    await cp.goto(B + '/guide/site/writing-this-guide/code-blocks.html');
    await cp.locator(makeBlock).locator('.g-copy').click();
    await until(() => cp.locator(makeBlock).locator('.g-copy').textContent().then(t => t === 'Copied'), 'Copied');
    const tabClip = await cp.evaluate(() => navigator.clipboard.readText());
    assert(tabClip === makeSource, 'and a tab reaches it as a tab: ' + JSON.stringify(tabClip));
    await cp.close();
  }
  const sw = sp.locator('.exercise', {hasText: 'Which one means'});
  await sw.locator('.ex-option[data-correct="0"]').first().click();
  await sp.click('.ex-correct-all');
  assert(/\bincorrect\b/.test(await sw.evaluate(ex => ex.className)), 'served, a wrong answer is marked wrong');
  {
    const v = await youtube(sp);
    assert(v.player && !v.card && !v.note, 'served, the YouTube player is kept: ' + JSON.stringify(v));
  }
  // the theme is the toolbox's: chosen in the guide, the hub has it too
  await sp.evaluate(() => localStorage.setItem('parseh_theme', 'light'));
  await sp.reload();
  await sp.click('[data-parseh-theme]');
  const picked = await sp.evaluate(() => document.documentElement.dataset.theme);
  await sp.goto(B + '/');
  const hubTheme = await sp.evaluate(() => document.documentElement.dataset.theme);
  assert(picked === 'dark' && hubTheme === 'dark', 'a theme picked in the guide is the hub\'s theme too: ' + picked + ' / ' + hubTheme);
  for (const [path, want] of [['/guide', 302], ['/guide/engine/site.py', 404], ['/guide/markdown/showcase.md', 404],
                              ['/guide/build.py', 404], ['/guide/%2e%2e/serve.py', 404], ['/guide/site/.hidden', 404],
                              ['/guide/assets/guide.css', 200], ['/guide/site/writing-this-guide/', 200]]) {
    const r = await fetch(B + path, {redirect: 'manual'});
    await r.body?.cancel();
    assert(r.status === want, `GET ${path} -> ${r.status}`);
  }
  const post = await fetch(B + '/guide/site/showcase.html', {method: 'POST', body: '{}'});
  await post.body?.cancel();
  assert(post.status === 405, 'the guide\'s files take no POST: ' + post.status);
  const ptype = await fetch(B + '/guide/site/images/flashcard.gif');
  await ptype.body?.cancel();
  assert(ptype.headers.get('content-type') === 'image/gif', 'a GIF is sent as one: ' + ptype.headers.get('content-type'));

  // a compile that ends with an error still writes every page it can: the
  // front page opens them (the list of pages has the new one) and says the
  // compile failed, with what it said
  await Deno.writeTextFile(`${SERVED}/markdown/broken.md`, '---\ntitle: A broken page\n---\n\nSee {{< ref "nowhere.md" >}}.\n');
  await sp.goto(B + '/guide/');
  await until(() => sp.$eval('[data-guide-compile]', b => !b.hidden && /older pages/.test(b.textContent)), 'the older-pages notice');
  await sp.click('[data-guide-compile] [data-compile]');
  const afterFail = await until(() => sp.evaluate(() => {
    const box = document.querySelector('[data-guide-compile]');
    const nav = [...document.querySelectorAll('#g-nav a')].map(a => a.textContent);
    return !box.hidden && /The last compile failed/.test(box.textContent) && nav.includes('A broken page') && [box.textContent, nav];
  }), 'the failed compile, and the pages it wrote', 60000).catch(() => null);
  assert(afterFail && /ref: no page 'nowhere\.md'/.test(afterFail[0]),
         'a failed compile: its pages are listed, and the notice keeps what it said: ' + (afterFail ? afterFail[0].slice(0, 90) : 'no'));
  assert(serr.length === 0, 'no script error on the served pages: ' + serr.join('; '));
  assert(!/Traceback/.test(log.join('')), 'no traceback in the server\'s log');
  await sctx.close();
  hub.kill('SIGTERM'); await hub.status;

  // ========================================================== 3. as GitHub Pages
  console.log('as GitHub Pages publishes it');
  const GH = `${WORK}/gh`;
  {
    const r = await run([PY, `${DISK}/build.py`, '--pages', `${GH}/Parseh`]);
    assert(r.code === 0, 'build.py --pages lays out the site: ' + r.out.trim());
  }
  const gport = freePort();
  const statik = new Deno.Command(PY, {args: ['-m', 'http.server', String(gport), '--bind', '127.0.0.1'], cwd: GH,
                                       stdout: 'null', stderr: 'null'}).spawn();
  children.push(statik);
  const G = `http://127.0.0.1:${gport}/Parseh/`;
  await until(async () => { const r = await fetch(G); await r.body?.cancel(); return r.ok; }, 'the static server');
  const gctx = await browser.newContext({viewport: {width: 1280, height: 800}});
  const gp = await gctx.newPage();
  const bad = [];
  gp.on('response', r => { if (r.status() >= 400 && r.url().startsWith(`http://127.0.0.1:${gport}`)) bad.push(r.status() + ' ' + r.url()); });
  await gp.goto(G);
  await gp.click('#g-nav a:text("The showcase")');
  await gp.waitForURL(/\/Parseh\/site\/showcase\.html$/);
  const drawn = await gp.evaluate(() => [getComputedStyle(document.querySelector('.g-article .sheet')).boxShadow !== 'none',
    document.querySelectorAll('.exercise').length]);
  assert(drawn[0] && drawn[1] > 5, 'under /Parseh/ the page is styled and its exercises drawn: ' + drawn);
  {
    const v = await youtube(gp);
    assert(v.player && !v.card, 'and its YouTube player is kept: ' + JSON.stringify(v));
  }
  await gp.click('a.g-prev');
  await gp.waitForLoadState();
  assert(/\/Parseh\//.test(gp.url()), 'and the way back stays under /Parseh/: ' + gp.url());
  assert(bad.length === 0, 'no address the pages ask for is missing: ' + bad.join('; '));
  // the same site under /guide/, where a website would put it: the address
  // alone once made the pages take this host for Parseh
  await Deno.symlink(`${GH}/Parseh`, `${GH}/guide`);
  const H = `http://127.0.0.1:${gport}/guide/`;
  const herr = [];
  gp.on('pageerror', e => herr.push(e.message));
  for (const url of [H, H + 'site/showcase.html']) {
    const asked = gp.waitForResponse(r => r.url() === H + '__status', {timeout: 5000}).catch(() => null);
    await gp.goto(url);
    const answer = await asked;
    await sleep(150);
    const got = await gp.evaluate(() => [!document.querySelector('.g-hub').hidden,
      document.querySelector('[data-guide-compile]')?.hidden]);
    assert(answer && answer.status() === 404 && !got[0] && got[1] !== false,
           `under /guide/ on a host that is not Parseh, ${url.slice(H.length) || 'the front page'} offers no way to a hub and no compile`);
  }
  assert(herr.length === 0, 'and no script error: ' + herr.join('; '));
  await gctx.close();
  statik.kill('SIGTERM'); await statik.status;
} finally {
  await browser.close();
  for (const c of children) { try { c.kill('SIGTERM'); } catch (_) {} }
  await Deno.remove(WORK, {recursive: true}).catch(() => {});
}
console.log(`\n${passed} passed, ${failed.length} failed`);
if (failed.length) { for (const f of failed) console.log('FAIL', f); Deno.exit(1); }

// Browser test of how two studio pages look, measured where they are drawn,
// against the REAL routes (markdown/app/server.py, htmlgen, deckroutes) on a
// temporary library and a temporary exercises store (tests/decks_harness.py,
// studio mode):
//   a) the editor on a phone (320 and 400 px wide): the page never scrolls
//      sideways, every control of its bar is on the screen and is what a tap
//      there reaches -- Save, Save & view, Exercises ▾, Audio, Recordings…,
//      Stop server among them -- Exercises ▾ opens a menu that is on the
//      screen too, and a tap on Save saves; at every width from 280 to 1440 px
//      the page stays put sideways and the bar and the open menu are on the
//      screen; on a desktop the bar keeps its layout
//   b) a flashcard written before cards held blocks (one-line jolly, vocab,
//      opposites) looks as it always did where both of its sides are shown
//      at once -- the editor's preview, on a desktop and on a phone, and a
//      deck row's preview on a phone: front and back side by side, touching,
//      on one line, no gap and no wrapping; a card with a field of blocks
//      keeps the room between its sides
//   c) a document's reading page on a phone (390x844 and 320x568), scrolled
//      by a finger: its two bars, the topbar and the toolbar, stand at the top
//      and together take little of the screen; while the page's head is still
//      on the screen they stand; a swipe down puts BOTH off the screen, so a
//      tap at the top reaches the text, and closes a menu left open on them;
//      the smallest swipe up brings both back, the toolbar right under the
//      topbar, every control of both reached by a tap once its row is
//      scrolled sideways to it; a contents jump down leaves the heading at the
//      top of the screen with the bars away, a jump up leaves it just under
//      the two bars, and a link to a heading opens with it at the top (a
//      reload keeps the place read on to); the toolbar is Contents, Glosses,
//      Linked from and Aa, which opens the typography controls, no slider in a row that
//      scrolls sideways; Tab brings each control of the topbar's row into
//      view; turned on its side mid-note, the page stays where it was; the
//      tag field typed in with the keyboard up is not under the topbar; on a
//      desktop nothing of this happens -- the topbar scrolls away with the
//      page and the toolbar stays pinned, both laid out as before
//   CHROME_BIN=... PARSEH_PYTHON=python3 deno run --allow-all tests/studio_narrow.mjs
//   NARROW_PARTS=b (or a, c) runs one part; SHOTS=<dir> saves the screenshots
//   (the editor at each width, its menu open; the reading page's bars)
import {chromium} from 'npm:playwright-core@1.52.0';

const root = await Deno.realPath(new URL('..', import.meta.url));
const python = Deno.env.get('PARSEH_PYTHON') || 'python3';
const SHOTS = Deno.env.get('SHOTS') || '';
const PARTS = (Deno.env.get('NARROW_PARTS') || 'a,b,c').split(',');
let passed = 0;
const assert = (v, m) => { if (!v) throw Error('FAIL: ' + m); passed++; console.log('  ok', m); };
const sleep = ms => new Promise(r => setTimeout(r, ms));

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

/* Where an element is, and whether a tap on its middle reaches it (a
   disabled button -- Undo with nothing to undo -- lets a tap through by
   design: it only has to be there, over its own bar). */
const placed = (page, el) => el.evaluate(b => {
  const r = b.getBoundingClientRect();
  const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
  const reach = b.disabled ? !!hit && !!b.closest('.topbar') && b.closest('.topbar').contains(hit)
                           : !!hit && (hit === b || b.contains(hit));
  return {l: Math.round(r.left), r: Math.round(r.right), t: Math.round(r.top), b: Math.round(r.bottom),
          w: innerWidth, h: innerHeight, hit: reach,
          what: (b.textContent || b.id || b.tagName).trim().slice(0, 30)};
});
const onScreen = p => p.hit && p.l >= 0 && p.r <= p.w && p.t >= 0 && p.b <= p.h;

const OLD_CARDS = `---
title: Greetings doc
target: fa
---

A one-line jolly card:

:::exercise flashcard
prompt: Say it.
card-type: jolly
front-primary: [سلام]{tl}
front-primary-size: 140
front-secondary: salâm
back-primary: **hello**
back-secondary: the everyday greeting
back-secondary-shade: accent
:::

A vocabulary card:

:::exercise flashcard
card-type: vocab
target: [خداحافظ]{tl}
transliteration: xodâhâfez
meaning: goodbye
context: said on leaving
:::

An opposites card:

:::exercise flashcard
card-type: opposites
target: [بزرگ]{tl}
opposite: [کوچک]{tl}
:::

A card with blocks:

:::exercise flashcard
card-type: jolly
front-primary: [سلام]{tl}
back-primary: |
  **hello**, the everyday greeting.

  - said on arriving
  - answered with [سلام]{tl} too
:::
`;

/* A card's two sides, measured inside it. */
const sides = card => card.evaluate(c => {
  const cs = getComputedStyle(c), R = x => Math.round(x * 10) / 10;
  const box = s => { const e = c.querySelector(':scope > ' + s); if (!e || e.hidden) return null;
                     const q = e.getBoundingClientRect(); return {l: R(q.left), r: R(q.right), t: R(q.top), b: R(q.bottom)}; };
  return {type: c.dataset.cardType, blocks: !!c.querySelector('.ex-card-blocks'), wrap: cs.flexWrap, gap: cs.columnGap,
          front: box('.ex-card-front'), back: box('.ex-card-back')};
});
/* front and back as a card without blocks has always drawn them: side by
   side, touching, on one line (HEAD: gap normal, nowrap) */
function asAlways(s, where) {
  assert(s.front && s.back, `${where}: the ${s.type} card shows both sides`);
  assert(s.wrap === 'nowrap' && s.gap === 'normal', `${where}: the ${s.type} card neither wraps nor spaces its sides (${s.wrap}, ${s.gap})`);
  const ltr = Math.abs(s.back.l - s.front.r) <= 1, rtl = Math.abs(s.front.l - s.back.r) <= 1;
  assert(ltr || rtl, `${where}: the ${s.type} card's back touches its front (front ${s.front.l}–${s.front.r}, back ${s.back.l}–${s.back.r})`);
  assert(s.back.t < s.front.b && s.front.t < s.back.b, `${where}: the ${s.type} card's sides share one line`);
}

/* A note long enough to scroll, with headings for the contents to jump to. */
const LONG_DOC = (() => {
  let md = '---\ntitle: A long note read on a phone\ntarget: it\nlang: en\n---\n\n';
  for (let i = 1; i <= 12; i++)
    md += `## Section ${i}\n\n` + 'Some prose with [parola]{tl} = *word* in it, long enough to wrap onto several lines on a narrow screen. '.repeat(6) + '\n\n';
  return md;
})();

/* The reading page's two bars where they are drawn, and whether a tap on the
   middle of Edit (topbar) and of Contents (toolbar) reaches that button. */
const bars = page => page.evaluate(() => {
  const box = s => { const e = document.querySelector(s), r = e.getBoundingClientRect();
                     return {t: Math.round(r.top), b: Math.round(r.bottom), pos: getComputedStyle(e).position,
                             tf: getComputedStyle(e).transform}; };
  const reach = s => { const e = document.querySelector(s), r = e.getBoundingClientRect();
                       const x = r.left + r.width / 2, y = r.top + r.height / 2;
                       if (y < 0 || y > innerHeight) return false;
                       const hit = document.elementFromPoint(x, y); return !!hit && (hit === e || e.contains(hit)); };
  const top = document.elementFromPoint(innerWidth / 2, 8);
  return {y: Math.round(scrollY), hidden: document.body.classList.contains('barhidden'),
          top: box('.topbar'), tool: box('#typobar'), edit: reach('.topbar a[href$="/edit"]'),
          contents: reach('#btn-toc'), textAtTop: !!top && !top.closest('.topbar, .toolbar, .metabar'),
          topbarH: getComputedStyle(document.documentElement).getPropertyValue('--topbar-h').trim()};
});
/* A finger's swipe (dy > 0 moves the page down), then waiting for the fling
   and the bars' slide to end. */
async function swipe(page, cdp, dy, from) {
  const x = 195, n = 20;
  await cdp.send('Input.dispatchTouchEvent', {type: 'touchStart', touchPoints: [{x, y: from}]});
  for (let i = 1; i <= n; i++) {
    await cdp.send('Input.dispatchTouchEvent', {type: 'touchMove', touchPoints: [{x, y: from - dy * i / n}]});
    await sleep(16);
  }
  await cdp.send('Input.dispatchTouchEvent', {type: 'touchEnd', touchPoints: []});
  await settle(page);
}
async function settle(page) {
  let last = -1;
  for (let i = 0; i < 60; i++) {
    const y = await page.evaluate(() => scrollY);
    if (y === last) break;
    last = y;
    await sleep(150);
  }
  await sleep(350);                       // the bars slide in .18 s
}

const {proc, info} = await startHarness();
const B = `http://127.0.0.1:${info.port}`;
const browser = await chromium.launch({executablePath: Deno.env.get('CHROME_BIN') || undefined, headless: true});
try {
  // ---------------------------------------------------------------- a) the editor's bar
  if (PARTS.includes('a')) console.log('a) the editor on a phone');
  for (const width of PARTS.includes('a') ? [320, 400] : []) {
    const ctx = await browser.newContext({viewport: {width, height: 860}, hasTouch: true, isMobile: true});
    const page = await ctx.newPage();
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    await page.goto(`${B}/doc/${info.doc_id}/edit`);
    await page.waitForFunction(() => /rendered/.test(document.querySelector('#pv-status')?.textContent || ''), null, {timeout: 15000});
    await page.evaluate(() => document.fonts.ready);
    await sleep(200);
    if (SHOTS) await page.screenshot({path: `${SHOTS}/editor-${width}.png`});
    const m = await page.evaluate(() => ({sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth}));
    assert(m.sw <= m.cw, `${width} px: the editor never scrolls sideways (page ${m.sw} px in a ${m.cw} px window)`);
    const controls = page.locator('.topbar :is(a, button, label, summary):visible');
    const n = await controls.count();
    const off = [];
    for (let i = 0; i < n; i++) {
      const p = await placed(page, controls.nth(i));
      if (!onScreen(p)) off.push(`${p.what} ${JSON.stringify(p)}`);
    }
    assert(n >= 25 && !off.length, `${width} px: all ${n} controls of the bar are on the screen and a tap reaches each` + (off.length ? ':\n    ' + off.join('\n    ') : ''));
    for (const [sel, name] of [['#btn-save', 'Save'], ['#btn-save-view', 'Save & view'], ['details.dropdown > summary', 'Exercises ▾'],
                               ['label[for="audio-upload"]', 'Audio'], ['#btn-audios', 'Recordings…'], ['#btn-stop', 'Stop server']]) {
      const p = await placed(page, page.locator(sel));
      assert(onScreen(p), `${width} px: ${name} is on the screen (${p.l}–${p.r} × ${p.t}–${p.b})`);
    }
    // Exercises ▾: its menu opens on the screen, and the page stays put
    await page.locator('details.dropdown > summary').tap();
    await page.locator('#btn-exercise').waitFor({state: 'visible'});
    await sleep(150);
    if (SHOTS) await page.screenshot({path: `${SHOTS}/editor-${width}-exercises.png`});
    for (const [sel, name] of [['#btn-exercise', 'Add exercise…'], ['#btn-exercise-prompt', 'Generate with LLM…'],
                               ['#btn-exercise-deck', 'Load from a deck…']]) {
      const p = await placed(page, page.locator(sel));
      assert(onScreen(p), `${width} px: the menu's ${name} is on the screen (${p.l}–${p.r})`);
    }
    assert(await page.evaluate(() => scrollX === 0), `${width} px: opening the menu does not move the page sideways`);
    await page.locator('details.dropdown > summary').tap();
    // a tap on Save saves
    const src = page.locator('#src');
    await src.evaluate((t, w) => { t.value = t.value.replace(/^Some text.*$/m, `Some text, saved at ${w} px.`); t.dispatchEvent(new Event('input', {bubbles: true})); }, width);
    await page.locator('#btn-save').tap();
    await page.waitForFunction(() => { const t = document.getElementById('toast'); return t && !t.hidden && /Saved/.test(t.textContent); }, null, {timeout: 8000});
    const text = await (await fetch(`${B}/download/${info.doc_id}/md`)).text();
    assert(text.includes(`saved at ${width} px`), `${width} px: tapping Save writes the document`);
    assert(!errors.length, `${width} px: no page errors` + (errors.length ? ': ' + errors.join('; ') : ''));
    await ctx.close();
  }
  if (PARTS.includes('a')) {
    // every width from a small phone to a desktop: where the bar wraps, any
    // control may start a line -- Exercises ▾ too, whose menu must still open
    // on the screen
    const page = await browser.newPage({viewport: {width: 1400, height: 900}});
    await page.goto(`${B}/doc/${info.doc_id}/edit`);
    await page.waitForFunction(() => /rendered/.test(document.querySelector('#pv-status')?.textContent || ''), null, {timeout: 15000});
    await page.evaluate(() => document.fonts.ready);
    const bad = [];
    let starts = 0;
    for (let width = 280; width <= 1440; width += 10) {
      await page.setViewportSize({width, height: 900});
      await sleep(40);
      const r = await page.evaluate(() => {
        const d = document.querySelector('.topbar details.dropdown');
        const off = [];
        const look = sel => {
          for (const b of document.querySelectorAll(sel)) {
            const q = b.getBoundingClientRect();
            if (!q.width) continue;
            const hit = document.elementFromPoint(q.left + q.width / 2, q.top + q.height / 2);
            const reach = b.disabled ? !!hit && b.closest('.topbar').contains(hit) : !!hit && (hit === b || b.contains(hit));
            if (q.left < 0 || q.right > innerWidth || q.top < 0 || q.bottom > innerHeight || !reach)
              off.push((b.id || b.textContent).trim().slice(0, 20));
          }
        };
        d.open = false;
        look('.topbar :is(a, button, label, summary):not(.menu *)');   // the bar (a shut menu keeps its boxes)
        d.open = true;
        look('.topbar details.dropdown .menu button');        // its open menu
        const s = d.querySelector('summary').getBoundingClientRect(), bar = document.querySelector('.topbar').getBoundingClientRect();
        d.open = false;
        return {sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth, off,
                startsLine: s.left - bar.left < 30};
      });
      if (r.startsLine) starts++;
      if (r.sw > r.cw || r.off.length) bad.push(`${width} px: page ${r.sw}, off screen or unreachable: ${r.off.join(', ')}`);
    }
    assert(!bad.length, 'from 280 to 1440 px the editor never scrolls sideways, and every control of its bar, and of the '
                        + `open Exercises ▾ menu, is on the screen and reachable (${starts} widths put Exercises ▾ at the start of a line)`
                        + (bad.length ? ':\n    ' + bad.join('\n    ') : ''));
    await page.setViewportSize({width: 1400, height: 900});
    await sleep(40);
    const bar = await page.evaluate(() => ({wrap: getComputedStyle(document.querySelector('.topbar')).flexWrap,
                                            actions: getComputedStyle(document.querySelector('.topbar-actions')).display}));
    assert(bar.wrap === 'nowrap' && bar.actions === 'flex', `1400 px: the bar keeps its desktop layout (${bar.wrap}, actions ${bar.actions})`);
    if (SHOTS) await page.screenshot({path: `${SHOTS}/editor-1400.png`});
    await page.close();
  }

  // ---------------------------------------------------------------- b) old cards
  if (PARTS.includes('b')) console.log('b) cards without blocks look as they always did');
  for (const width of PARTS.includes('b') ? [1400, 400] : []) {
    const page = await browser.newPage({viewport: {width, height: 900}});
    await page.goto(`${B}/doc/${info.doc_id}/edit`);
    await page.waitForFunction(() => /rendered/.test(document.querySelector('#pv-status')?.textContent || ''), null, {timeout: 15000});
    await page.locator('#src').evaluate((t, md) => { t.value = md; t.dispatchEvent(new Event('input', {bubbles: true})); }, OLD_CARDS);
    await page.waitForFunction(() => document.querySelectorAll('#sheet .ex-flashcard').length === 4, null, {timeout: 15000});
    await page.evaluate(() => document.fonts.ready);
    await sleep(300);
    const cards = page.locator('#sheet .ex-flashcard');
    for (let i = 0; i < 3; i++) {
      await cards.nth(i).scrollIntoViewIfNeeded();
      const s = await sides(cards.nth(i));
      assert(!s.blocks, `${width} px editor preview: card ${i + 1} (${s.type}) holds no blocks`);
      asAlways(s, `${width} px editor preview`);
    }
    await cards.nth(3).scrollIntoViewIfNeeded();
    const rich = await sides(cards.nth(3));
    assert(rich.blocks && rich.wrap === 'wrap' && rich.gap !== 'normal',
           `${width} px editor preview: the card with blocks keeps its wrap and the room between its sides (${rich.wrap}, ${rich.gap})`);
    const apart = rich.back.l - rich.front.r >= 20 || rich.front.l - rich.back.r >= 20 || rich.back.t >= rich.front.b;
    assert(apart, `${width} px editor preview: the card with blocks sets its sides apart`);
    await page.close();
  }
  if (PARTS.includes('b')) {
    const ctx = await browser.newContext({viewport: {width: 400, height: 860}, hasTouch: true, isMobile: true});
    const deck = await ctx.newPage();
    await deck.goto(`${B}/exercises/`);
    await deck.locator('a', {hasText: 'Persian practice'}).first().click();
    await deck.waitForSelector('.dk-row');
    const row = deck.locator('.dk-row', {has: deck.locator('.ex-kicker', {hasText: /flashcard/i})}).first();
    await row.locator('.dk-row-toggle').tap();
    const card = row.locator('.dk-row-preview .ex-flashcard');
    await card.waitFor();
    await deck.evaluate(() => document.fonts.ready);
    await sleep(300);
    await card.scrollIntoViewIfNeeded();
    const s = await sides(card);
    assert(!s.blocks, '400 px deck row preview: the vocab card holds no blocks');
    asAlways(s, '400 px deck row preview');
    await ctx.close();
  }

  // ---------------------------------------------------------------- c) the reading page's bars
  if (PARTS.includes('c')) {
    console.log("c) a document's reading page: both bars go away on a phone, and only there");
    const made = await (await fetch(`${B}/api/docs`, {method: 'POST', headers: {'Content-Type': 'application/json'},
                                                       body: JSON.stringify({markdown: LONG_DOC})})).json();
    const id = (made.meta || made).id;
    assert(id, 'a long note is made to scroll');
    const phone = async (width, height, hash = '') => {
      const ctx = await browser.newContext({viewport: {width, height}, deviceScaleFactor: 3, isMobile: true, hasTouch: true});
      const page = await ctx.newPage();
      const errors = [];
      page.on('pageerror', e => errors.push(e.message));
      await page.goto(`${B}/doc/${id}${hash}`);
      await page.evaluate(() => document.fonts.ready);
      await settle(page);
      return {ctx, page, errors, cdp: await ctx.newCDPSession(page)};
    };
    const heading = (page, name) => page.locator('.sheet h2', {hasText: new RegExp(name + '$')}).first()
      .evaluate(e => Math.round(e.getBoundingClientRect().top));

    for (const [W, H] of [[390, 844], [320, 568]]) {
      const at = `phone ${W}x${H}`;
      const {ctx, page, errors, cdp} = await phone(W, H);
      let s = await bars(page);
      assert(!s.hidden && s.top.pos === 'sticky' && s.tool.pos === 'sticky',
             `${at}, at the top: both bars are pinned and standing (${s.top.pos}, ${s.tool.pos})`);
      assert(s.top.t === 0 && s.tool.t >= s.top.b && s.edit && s.contents,
             `${at}, at the top: the topbar at 0, the toolbar under it, Edit and Contents reached by a tap (${JSON.stringify(s)})`);
      const pair = (s.top.b - s.top.t) + (s.tool.b - s.tool.t), head = s.tool.b;
      assert(pair <= H * 0.3, `${at}: the two bars together are a small part of the screen (${pair} of ${H} px)`);
      if (SHOTS) await page.screenshot({path: `${SHOTS}/reading-${W}-top.png`});

      // just past a finger's first move, the head of the page still on the screen: nothing goes away
      await swipe(page, cdp, 140, H - 60);
      s = await bars(page);
      assert(s.y > 80 && s.y < head && !s.hidden,
             `${at}, scrolled ${s.y} px down, while the page's head (${head} px) is still on the screen: the bars stand`);

      await swipe(page, cdp, Math.round(H * 0.7), H - 40);
      s = await bars(page);
      assert(s.y > 300 && s.hidden, `${at}, swiped down: the page moved (${s.y}) and the bars are put away`);
      assert(s.top.b <= 0 && s.tool.b <= 0, `${at}, swiped down: BOTH bars are off the screen (topbar ${s.top.t}–${s.top.b}, toolbar ${s.tool.t}–${s.tool.b})`);
      assert(s.textAtTop && !s.edit && !s.contents, `${at}, swiped down: a tap at the top of the screen reaches the text, not a bar`);
      if (SHOTS) await page.screenshot({path: `${SHOTS}/reading-${W}-down.png`});

      await swipe(page, cdp, -60, Math.round(H * 0.45));
      s = await bars(page);
      assert(!s.hidden && s.top.t === 0 && Math.abs(s.tool.t - s.top.b) <= 1,
             `${at}, swiped up a little: both bars come back, the toolbar right under the topbar (topbar ${s.top.t}–${s.top.b}, toolbar ${s.tool.t}–${s.tool.b})`);
      assert(s.edit && s.contents, `${at}, swiped up a little: Edit and Contents are reached by a tap`);
      if (SHOTS) await page.screenshot({path: `${SHOTS}/reading-${W}-up.png`});

      // every control of both bars is reached: the topbar's once its row is
      // scrolled sideways to it, the typography controls once "Aa" opens them
      const reach = sel => page.evaluate(sel => {
        const out = {missed: [], shown: 0};
        for (const el of document.querySelectorAll(sel)) {
          if (el.disabled || el.closest('[hidden], .menu') || !el.getClientRects().length) continue;
          out.shown++;
          el.scrollIntoView({block: 'nearest', inline: 'nearest'});
          const r = el.getBoundingClientRect(), x = r.left + r.width / 2, y = r.top + r.height / 2;
          const hit = x >= 0 && x <= innerWidth && y >= 0 && y <= innerHeight && document.elementFromPoint(x, y);
          if (!hit || !(hit === el || el.contains(hit) || (el.labels && [...el.labels].some(l => l.contains(hit)))))
            out.missed.push(el.id || el.textContent.trim().slice(0, 20));
        }
        return out;
      }, sel);
      let got = await reach('.topbar a, .topbar summary, .topbar button:not([hidden])');
      assert(got.shown >= 6 && !got.missed.length, `${at}: every control of the topbar is reached by a tap once its row is scrolled to it (${got.shown}, missed ${JSON.stringify(got.missed)})`);
      await page.locator('.topbar-actions').evaluate(r => { r.scrollLeft = 0; });
      const typo = () => page.evaluate(() => [...document.querySelectorAll('#typobar input, #typobar select, #btn-typo-reset, #btn-print')]
        .filter(e => e.getClientRects().length).length);
      got = await reach('#typobar button, #typobar input, #typobar select');
      // four: "Linked from" stays with Contents and Glosses on a phone (tests/doclinks.mjs)
      assert(got.shown === 4 && !got.missed.length && await typo() === 0,
             `${at}: the toolbar shows Contents, Glosses, Linked from and Aa, each reached by a tap, and no typography control (${got.shown}, missed ${JSON.stringify(got.missed)})`);
      await page.locator('#btn-typo').tap();
      await settle(page);
      got = await reach('#typobar button, #typobar input, #typobar select');
      const sideways = await page.evaluate(() => [...document.querySelectorAll('#typobar input[type=range]')].some(inp => {
        for (let a = inp.parentElement; a && a !== document.body; a = a.parentElement)
          if (a.scrollWidth > a.clientWidth + 1 && /auto|scroll/.test(getComputedStyle(a).overflowX)) return true;
        return false;
      }));
      assert(await typo() >= 9 && !got.missed.length && !sideways,
             `${at}: Aa opens the typography controls, each reached by a tap, no slider in a row that scrolls sideways (missed ${JSON.stringify(got.missed)})`);
      if (SHOTS) await page.screenshot({path: `${SHOTS}/reading-${W}-typo.png`});
      await page.locator('#btn-typo').tap();
      await settle(page);
      assert(await typo() === 0 && await page.locator('#btn-typo').getAttribute('aria-expanded') === 'false',
             `${at}: Aa closes them again`);
      // left open, the typography controls would come back with the bars over
      // most of a small screen: a swipe down closes them with the bars
      await page.locator('#btn-typo').tap();
      await settle(page);
      await swipe(page, cdp, Math.round(H * 0.5), H - 40);
      await swipe(page, cdp, -40, Math.round(H * 0.45));
      s = await bars(page);
      assert(await typo() === 0 && !s.hidden && (s.tool.b - s.top.t) <= H * 0.3,
             `${at}: the bars going away close Aa, so they come back short (${s.tool.b} of ${H} px)`);

      // Tab along the topbar's row: the control focused is in the row's view
      await page.locator('.topbar .hublink').focus();
      const cut = [];
      for (let i = 0; i < 9; i++) {
        await page.keyboard.press('Tab');
        const f = await page.evaluate(() => {
          const el = document.activeElement, row = el && el.closest('.topbar-actions');
          if (!row) return null;
          const r = el.getBoundingClientRect(), w = row.getBoundingClientRect();
          return {id: el.id || el.textContent.trim().slice(0, 12), inside: r.left >= w.left - 1 && r.right <= w.right + 1};
        });
        if (f && !f.inside) cut.push(f.id);
      }
      assert(!cut.length, `${at}: Tab along the topbar's row brings each focused control into the row's view (cut ${JSON.stringify(cut)})`);
      await page.evaluate(() => document.activeElement && document.activeElement.blur());
      await swipe(page, cdp, -40, Math.round(H * 0.45));

      // a menu open on a bar goes away with the bars
      await page.locator('.topbar summary', {hasText: 'Download'}).tap();
      let menu = await page.evaluate(() => { const d = document.querySelector('.topbar details[open] .menu'); if (!d) return null;
                                              const r = d.getBoundingClientRect(); return {t: Math.round(r.top), b: Math.round(r.bottom), l: Math.round(r.left), r: Math.round(r.right)}; });
      assert(menu && menu.t >= 0 && menu.b <= H && menu.l >= 0 && menu.r <= W, `${at}: Download ▾ opens a menu on the screen (${JSON.stringify(menu)})`);
      await swipe(page, cdp, Math.round(H * 0.5), H - 40);
      s = await bars(page);
      const open = await page.evaluate(() => document.querySelectorAll('.topbar details[open], .toolbar details[open]').length);
      assert(s.hidden && open === 0 && s.textAtTop, `${at}: the bars going away close the open menu, and a tap at the top reaches the text`);
      await swipe(page, cdp, -40, Math.round(H * 0.45));

      const jump = async name => {
        await page.locator('#btn-toc').tap();
        await page.waitForFunction(() => document.body.classList.contains('toc-open'));
        await page.locator('.toc-list a', {hasText: name}).first().tap();
        await settle(page);
        return {s: await bars(page), h: await heading(page, name)};
      };
      let j = await jump('Section 9');
      assert(j.s.hidden && j.s.top.b <= 0 && j.s.tool.b <= 0,
             `${at}, a contents jump down: the bars went away on the way (topbar ${j.s.top.b}, toolbar ${j.s.tool.b})`);
      assert(j.h >= 0 && j.h <= 40, `${at}, a contents jump down: the heading is at the top of the screen (${j.h} px)`);
      await swipe(page, cdp, -40, Math.round(H * 0.45));
      j = await jump('Section 3');
      assert(!j.s.hidden && j.s.top.t === 0, `${at}, a contents jump up: the bars came back on the way`);
      assert(j.h >= j.s.tool.b - 1 && j.h <= j.s.tool.b + 40 && j.h < H,
             `${at}, a contents jump up: the heading sits just under both bars (${j.h} px, toolbar ends at ${j.s.tool.b})`);

      // the phone turned on its side, mid-note with the bars standing: the page stays where it was
      await swipe(page, cdp, Math.round(H * 0.6), H - 40);
      await swipe(page, cdp, -40, Math.round(H * 0.45));
      s = await bars(page);
      assert(!s.hidden && s.y > 400, `${at}, mid-note with the bars standing (${s.y})`);
      await page.setViewportSize({width: H, height: W});
      await settle(page);
      const turned = await bars(page);
      assert(Math.abs(turned.y - s.y) <= 5, `${at}, turned on its side: the page stays where it was (${s.y} -> ${turned.y})`);
      await page.setViewportSize({width: W, height: H});
      await settle(page);

      await page.evaluate(() => window.scrollTo(0, 0));
      await settle(page);
      s = await bars(page);
      assert(!s.hidden && s.top.t === 0 && s.tool.t > s.top.b, `${at}, back at the top: the bars stand where the page puts them`);
      assert(!errors.length, `${at}: no page errors ` + errors.join(' | '));
      await ctx.close();
    }

    // a link to a heading, opened on a phone: the heading at the top, the bars away
    for (const [W, H] of [[390, 844], [320, 568]]) {
      const {ctx, page, errors} = await phone(W, H, '#sec-7');
      await sleep(400);
      const s = await bars(page), h = await heading(page, 'Section 7');
      assert(s.hidden && h >= 0 && h <= 40, `phone ${W}x${H}, opened at #sec-7: the heading is at the top of the screen (${h} px) with the bars away`);
      assert(!errors.length, `phone ${W}x${H}, opened at #sec-7: no page errors`);
      await ctx.close();
    }

    // a reload after a contents jump (which wrote #sec-3 into the address) keeps the place read on to
    {
      const {ctx, page, cdp} = await phone(390, 844);
      await page.locator('#btn-toc').tap();
      await page.locator('.toc-list a', {hasText: 'Section 3'}).first().tap();
      await settle(page);
      for (let i = 0; i < 4; i++) await swipe(page, cdp, 700, 800);
      const before = await bars(page);
      await page.reload();
      await page.evaluate(() => document.fonts.ready);
      await settle(page);
      const after = await bars(page);
      assert(page.url().endsWith('#sec-3') && Math.abs(after.y - before.y) <= 150,
             `phone 390x844, reloaded after reading on past a contents jump: the page is where it was read to, not back at the heading (${before.y} -> ${after.y})`);
      await ctx.close();
    }

    // the tag field, typed in with the keyboard up (the page's height shrinks)
    {
      const {ctx, page} = await phone(320, 568);
      await page.locator('#tag-input').tap();
      await page.setViewportSize({width: 320, height: 230});
      // the page moved a little as the keyboard came up: the tags row is under the pinned topbar
      await page.evaluate(() => window.scrollTo(0, 60));
      await settle(page);
      await page.locator('#tag-input').evaluate(e => e.scrollIntoView({block: 'nearest'}));
      await page.keyboard.type('abc');
      await settle(page);
      const where = await page.locator('#tag-input').evaluate(e => {
        const r = e.getBoundingClientRect(), hit = document.elementFromPoint(r.left + 10, r.top + r.height / 2);
        return {t: Math.round(r.top), value: e.value, own: hit === e};
      });
      assert(where.value === 'abc' && where.own, `phone 320, the keyboard up: the tag field typed in is not under the pinned topbar (${JSON.stringify(where)})`);
      await ctx.close();
    }

    // a context of its own, named: the bars check below opens a second page
    // in it, and two pages of one browser share the store as two tabs do
    const deskCtx = await browser.newContext({viewport: {width: 1280, height: 900}});
    const desk = await deskCtx.newPage();
    await desk.goto(`${B}/doc/${id}`);
    await settle(desk);
    let s = await bars(desk);
    const layout = await desk.evaluate(() => ({bar: getComputedStyle(document.querySelector('#typobar')).flexWrap,
                                               actions: getComputedStyle(document.querySelector('.topbar-actions')).flexWrap,
                                               topWrap: getComputedStyle(document.querySelector('.topbar')).flexWrap}));
    assert(s.top.pos === 'static' && s.tool.pos === 'sticky' && s.topbarH === '',
           `desktop: the topbar is in the flow and only the toolbar is pinned, as before (${s.top.pos}, ${s.tool.pos}, --topbar-h "${s.topbarH}")`);
    assert(layout.bar === 'wrap' && layout.actions === 'wrap' && layout.topWrap === 'nowrap',
           `desktop: both bars keep their layout (${JSON.stringify(layout)})`);
    for (let i = 0; i < 12; i++) { await desk.mouse.wheel(0, 60); await sleep(30); }
    await settle(desk);
    s = await bars(desk);
    assert(!s.hidden && s.top.b < 0 && s.tool.t === 0 && s.tool.tf === 'none',
           `desktop, scrolled down: the topbar scrolled away, the toolbar is still pinned at the top, nothing is put away (${JSON.stringify(s)})`);
    for (let i = 0; i < 2; i++) { await desk.mouse.wheel(0, -40); await sleep(30); }
    await settle(desk);
    s = await bars(desk);
    assert(!s.hidden && s.top.b < 0 && s.tool.t === 0, 'desktop, scrolled up a little: the topbar does not come back, as before');
    if (SHOTS) await desk.screenshot({path: `${SHOTS}/reading-desktop.png`});

    /* "bars": the three of them put away by hand, and the way back.  Not
       the phone's own hiding, which comes back on a move up -- this holds,
       and holds for the next document too. */
    const look = pg => pg.evaluate(() => {
      const vis = sel => { const e = document.querySelector(sel); return !!e && e.getClientRects().length > 0; };
      return {top: vis('.topbar'), meta: vis('.metabar'), bar: vis('#typobar'),
              hide: vis('#btn-bars'), show: vis('#btn-bars-show'),
              sticky: getComputedStyle(document.documentElement).getPropertyValue('--sticky-h').trim()};
    });
    let v = await look(desk);
    assert(v.top && v.meta && v.bar && v.hide && !v.show,
           `the bars stand to begin with, with "⌃ bars" among them (${JSON.stringify(v)})`);
    await desk.locator('#btn-bars').click();
    await settle(desk);
    v = await look(desk);
    assert(!v.top && !v.meta && !v.bar && !v.hide && v.show,
           `"⌃ bars" takes all three away and leaves the way back (${JSON.stringify(v)})`);
    assert(v.sticky === '10px', `and a jump to a heading no longer clears a bar (${v.sticky})`);
    await desk.evaluate(() => window.scrollTo(0, 0));
    await settle(desk);
    const gap = await desk.evaluate(() => Math.round(document.querySelector('#sheet').getBoundingClientRect().top));
    assert(gap >= 0 && gap < 60, `at the top of the page the text starts at the top of the window (${gap}px)`);
    await desk.reload();
    await settle(desk);
    v = await look(desk);
    assert(!v.top && !v.bar && v.show, 'and it is still away after a reload');
    // the same browser, so the same store: newPage() on the browser would
    // open a context of its own and remember nothing
    const other = await deskCtx.newPage();
    await other.goto(`${B}/doc/${id}`);
    await other.waitForSelector('#sheet');
    assert(!(await look(other)).bar, 'a way of reading, not a property of a page: the next document opens the same');
    await other.close();
    await desk.locator('#btn-bars-show').click();
    await settle(desk);
    v = await look(desk);
    assert(v.top && v.meta && v.bar && v.hide && !v.show, 'and the way back brings all three');
    await deskCtx.close();
  }
  console.log(`\n${passed} passed`);
} finally {
  await browser.close();
  try { proc.kill('SIGTERM'); } catch (_) { /* gone */ }
  await proc.status;
}

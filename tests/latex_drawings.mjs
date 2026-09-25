// SPDX-License-Identifier: GPL-3.0-or-later
// Browser test of the LaTeX drawings (TO-DO §8.39, a0.4.0), against the REAL
// routes on a temporary library, with the TeX this computer has:
//   a) the editor's preview draws a document's latex blocks, and a block that
//      cannot be drawn is a frame saying why, in words
//   b) the LaTeX drawing sheet: a theme chosen, the drawing made as it is
//      typed, a mistake said in words beside it, Insert putting the block in
//   c) THE PENCIL: hovering a drawing in the preview offers ✎ on the drawing,
//      it goes away again when the pointer leaves, and pressing it reopens
//      the block, whose edit goes back over the very lines it came from.
//      (It never appeared for a whole week of a0.4.0's work -- it reused the
//      RTL pencil's class, which is `display: none`, and only set `hidden` --
//      because no test had ever opened the sheet: found by driving, 2026-09-25.)
//   d) (parseh) Settings -> LaTeX drawings: its themes, the bar of its doors,
//      and a page that never scrolls sideways on a phone
// Two modes, each a tests/studio_harness.py:
//   studio  the studio's own server (studio at /)
//   parseh  Parseh's handler (studio at /studio, Settings at /settings/)
//   CHROME_BIN=... PARSEH_PYTHON=python3 deno run --allow-all tests/latex_drawings.mjs
//   LATEX_DRAWINGS_MODES=studio (or parseh) runs one; SHOTS=<dir> saves the
//   screenshots.  A computer with no xelatex skips it, saying so: the
//   drawings are TeX's, and a fresh clone must stay green.
import {chromium} from 'npm:playwright-core@1.52.0';

const root = await Deno.realPath(new URL('..', import.meta.url));
const python = Deno.env.get('PARSEH_PYTHON') || 'python3';
const modes = (Deno.env.get('LATEX_DRAWINGS_MODES') || 'studio,parseh').split(',');
const SHOTS = Deno.env.get('SHOTS') || '';
let passed = 0;
const assert = (v, m) => { if (!v) throw Error('FAIL: ' + m); passed++; console.log('  ok', m); };
const eq = (a, b, m) => assert(a === b, `${m} (got ${JSON.stringify(a)}, want ${JSON.stringify(b)})`);
const sleep = ms => new Promise(r => setTimeout(r, ms));
async function until(fn, what, ms = 20000) {
  const end = Date.now() + ms;
  for (;;) {
    let v;
    try { v = await fn(); } catch (_) { v = false; }
    if (v) return v;
    if (Date.now() > end) throw Error('FAIL: timed out: ' + what);
    await sleep(80);
  }
}

// no TeX, no drawings: a named skip
const hasTeX = await new Deno.Command('xelatex', {args: ['--version'], stdout: 'null', stderr: 'null'}).output()
  .then(r => r.success, () => false);
if (!hasTeX) {
  console.log('SKIP: no xelatex on this computer -- the drawings are made by TeX (tests/latex_drawings.mjs)');
  Deno.exit(0);
}

const DOC = `---
target: it
---
# Disegni

Una formula ordinaria: [E = mc^2]{math}.

::::latex chemistry {width=45 align=center}
\\ce{2H2 + O2 -> 2H2O}
::::

Un blocco rotto:

::::latex
\\undefinedcommandxyz
::::

Un blocco con un tema che non esiste:

::::latex nosuchtheme
x
::::
`;

async function startHarness(mode) {
  const proc = new Deno.Command(python, {args: [root + '/tests/studio_harness.py', mode], cwd: root,
                                         stdout: 'piped', stderr: 'piped'}).spawn();
  const log = [];
  (async () => {
    const r = proc.stderr.pipeThrough(new TextDecoderStream()).getReader();
    for (;;) { const {value, done} = await r.read(); if (done) break; log.push(value); }
  })();
  const reader = proc.stdout.pipeThrough(new TextDecoderStream()).getReader();
  let buf = '', info = null;
  while (!info) {
    const {value, done} = await reader.read();
    if (done) throw Error(`harness (${mode}) exited before READY:\n` + buf + log.join(''));
    buf += value;
    const m = buf.match(/READY (\{.*\})\n/);
    if (m) info = JSON.parse(m[1]);
  }
  (async () => { for (;;) { const r = await reader.read(); if (r.done) break; } })();
  return {proc, info, log};
}

async function suite(mode) {
  console.log(`\n== ${mode} ==`);
  const {proc, info, log} = await startHarness(mode);
  const origin = `http://127.0.0.1:${info.port}`, base = info.studio;
  const url = p => origin + base + p;
  const api = async (method, path, body) => {
    const r = await fetch(url(path), {method, headers: body ? {'Content-Type': 'application/json'} : {},
                                      body: body ? JSON.stringify(body) : undefined});
    const data = await r.json();
    if (!r.ok) throw Error(`${method} ${path}: ${r.status} ${JSON.stringify(data)}`);
    return data;
  };
  const browser = await chromium.launch({executablePath: Deno.env.get('CHROME_BIN'), headless: true});
  try {
    const context = await browser.newContext({viewport: {width: 1280, height: 900}});
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    const shot = async name => { if (SHOTS) await page.screenshot({path: `${SHOTS}/latex-${mode}-${name}.png`}); };
    const source = () => page.locator('#src').inputValue();
    const made = await api('POST', '/api/docs', {markdown: DOC});
    const id = made.meta.id;

    /* ---------------- a) the preview ---------------- */
    console.log('a) the preview');
    await page.goto(url(`/doc/${id}/edit`));
    await page.waitForSelector('#btn-latex-editor');
    await page.waitForSelector('#sheet figure.latex', {timeout: 30000});
    eq(await page.locator('#sheet figure.latex').count(), 1, 'the block that can be drawn is a drawing');
    const drawn = await page.evaluate(() => {
      const i = document.querySelector('#sheet figure.latex img');
      return i.complete && i.naturalWidth > 20 && /svg/.test(i.currentSrc);
    });
    assert(drawn, 'and its picture (an SVG) really loaded');
    const said = await page.locator('#sheet .latex-fail .latex-said').allTextContents();
    eq(said.length, 2, 'the two blocks that cannot be drawn are frames');
    assert(/undefinedcommandxyz is not a command LaTeX knows here on line 1 of the block/.test(said[0]),
           'one says which command and on which line: ' + said[0].slice(0, 90));
    assert(/asks for the theme .nosuchtheme., which this Parseh does not have/.test(said[1]),
           'the other says the theme is missing: ' + said[1].slice(0, 90));
    await shot('preview');

    /* ---------------- b) the sheet ---------------- */
    console.log('b) the LaTeX drawing sheet');
    // where the block goes is where the caret is, as for every button of the editor: at the end
    await page.locator('#src').click();
    await page.keyboard.press('Control+End');
    await page.click('#btn-latex-editor');
    await page.waitForSelector('.latex-overlay .lx-theme option[value="chemistry"]', {state: 'attached'});
    await page.selectOption('.latex-overlay .lx-theme', 'chemistry');
    await page.fill('.latex-overlay .lx-src', '\\ce{CH4 + 2O2 -> CO2 + 2H2O}');
    await page.waitForSelector('.latex-overlay .lx-stage img', {timeout: 30000});
    assert(await page.evaluate(() => {
      const i = document.querySelector('.latex-overlay .lx-stage img');
      return i.complete && i.naturalWidth > 20;
    }), 'the sheet draws the reaction as it is typed');
    await shot('sheet');
    await page.fill('.latex-overlay .lx-src', '\\undefinedcommandxyz');
    await until(async () => /not a command LaTeX knows/.test(await page.locator('.latex-overlay .lx-status').textContent()),
                'a mistake said in words');
    assert(true, 'a mistake in the sheet is said in words beside the drawing');
    await page.fill('.latex-overlay .lx-src', '\\ce{CH4 + 2O2 -> CO2 + 2H2O}');
    await page.waitForSelector('.latex-overlay .lx-stage img', {timeout: 30000});
    await page.click('.latex-overlay [data-x="ok"]');
    await page.waitForSelector('.latex-overlay', {state: 'detached'});
    assert(/::::latex chemistry[^\n]*\n\\ce\{CH4 \+ 2O2 -> CO2 \+ 2H2O\}\n::::/.test(await source()),
           'Insert puts a ::::latex chemistry block into the text');
    await until(async () => (await page.locator('#sheet figure.latex').count()) === 2, 'the preview draws one more');
    assert(true, 'and the preview draws one more');

    /* ---------------- c) the pencil ---------------- */
    console.log('c) the pencil on a drawing');
    const fig = page.locator('#sheet figure.latex[data-latex-src]').first();
    await fig.scrollIntoViewIfNeeded();
    const pencil = page.locator('button.rtl-edit-btn').filter({hasText: '✎'});
    assert(!(await pencil.count()) || !(await pencil.first().isVisible()), 'no pencil while the pointer is elsewhere');
    await fig.hover();
    await until(async () => (await pencil.count()) && await pencil.first().isVisible(), 'the pencil appears');
    assert(true, 'hovering a drawing offers ✎');
    const boxes = await page.evaluate(() => {
      const f = document.querySelector('#sheet figure.latex[data-latex-src]').getBoundingClientRect();
      const b = [...document.querySelectorAll('button.rtl-edit-btn')].find(x => x.textContent.trim() === '✎').getBoundingClientRect();
      return {f: [f.left, f.top, f.right, f.bottom], b: [b.left, b.top, b.right, b.bottom]};
    });
    // at the drawing's top corner: a short drawing (one line of a reaction is 21 px tall) is
    // shorter than the button, which then hangs below it -- so the corner, not the whole box
    assert(boxes.b[2] - boxes.b[0] > 5 && boxes.b[3] - boxes.b[1] > 5
           && boxes.b[2] <= boxes.f[2] + 2 && boxes.b[2] >= boxes.f[2] - 14
           && Math.abs(boxes.b[1] - boxes.f[1]) <= 8 && boxes.b[0] >= boxes.f[0] - 2,
           `and sits at the drawing's top corner (${boxes.b.map(Math.round)} against ${boxes.f.map(Math.round)})`);
    await page.mouse.move(5, 5);
    await until(async () => !(await pencil.first().isVisible()), 'the pencil goes away', 3000);
    assert(true, 'it goes away again when the pointer leaves');
    await fig.hover();
    await until(async () => await pencil.first().isVisible(), 'the pencil is back');
    await pencil.first().click();
    await page.waitForSelector('.latex-overlay .lx-src');
    eq(await page.inputValue('.latex-overlay .lx-src'), '\\ce{2H2 + O2 -> 2H2O}', 'the pencil reopens the block that was drawn');
    eq(await page.inputValue('.latex-overlay .lx-theme'), 'chemistry', 'with its theme');
    eq(await page.inputValue('.latex-overlay .lx-width'), '45', 'and its width');
    await page.fill('.latex-overlay .lx-src', '\\ce{2H2 + O2 -> 2H2O}\n% edited');
    await page.click('.latex-overlay [data-x="ok"]');
    await page.waitForSelector('.latex-overlay', {state: 'detached'});
    const text = await source();
    assert(/::::latex chemistry \{width=45( align=center)?\}\n\\ce\{2H2 \+ O2 -> 2H2O\}\n% edited\n::::\n/.test(text),  // centred is the default, so the sheet may leave it unsaid
           'saving puts the edit back over the block it came from, its fence and layout kept');
    eq((text.match(/::::latex/g) || []).length, 4, 'and no block was lost or doubled');

    /* ---------------- d) Settings ---------------- */
    if (mode === 'parseh') {
      console.log('d) Settings -> LaTeX drawings');
      await page.goto(origin + '/settings/latex/');
      await page.waitForSelector('.lx .theme');
      const names = (await page.locator('.lx .theme h3').allTextContents()).map(s => s.split('(')[0].trim());
      eq(names.join(','), 'default,chemistry,drawing', 'a fresh Parseh has three themes');
      assert(await page.locator('.parseh-doors a, nav a, .doors a').filter({hasText: 'LaTeX drawings'}).count() > 0
             || (await page.content()).includes('LaTeX drawings'), 'the bar of the doors names this page');
      await shot('settings');
      await page.setViewportSize({width: 390, height: 844});
      await sleep(300);
      const over = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      assert(over <= 1, `at 390 px the page never scrolls sideways (${over} px over)`);
      await shot('settings-phone');
    }
    eq(errors.join(' | '), '', 'no script error on any page');
  } finally {
    await browser.close();
    proc.kill('SIGTERM');
    await proc.status.catch(() => {});
  }
  return passed;
}

let total = 0;
for (const mode of modes) total += await suite(mode);
console.log(`LaTeX drawings passed (${modes.join(' + ')}: ${passed} checks)`);

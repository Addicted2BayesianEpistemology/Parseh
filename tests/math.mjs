// SPDX-License-Identifier: GPL-3.0-or-later
import { chromium } from 'npm:playwright-core@1.52.0';
// Run: CHROME_BIN=/path/to/chrome PARSEH_PYTHON=python3 deno run --allow-all tests/math.mjs
//
// MATHEMATICS IN A DOCUMENT AND IN AN EXERCISE.  `[a^2+b^2]{math}` in a
// line and a `:::math` fence on its own; drawn by MathJax (lib/mathjax/,
// vendored) through lib/mathjax.js, and set by TeX itself on paper.
//
// What has to hold:
//
//   a) THE LIBRARY IS THERE AND IS REACHED.  It is two megabytes vendored
//      into lib/, and the studio answers for it so that a page works the
//      same mounted in the toolbox or run on its own.
//   b) A FORMULA IS DRAWN WHEREVER TEXT IS RENDERED.  One hook, in
//      bindExercises, because every piece of rendered html in this toolbox
//      comes past it -- the document, the editor's preview, an exercise, a
//      deck row, the card kit's frame.
//   c) A FORMULA KEEPS ITS BRACKETS.  An interval is ordinary mathematics,
//      and the mark is read up to the `]{math}` that ends it -- which is
//      why its body is not the bracketless one `{tl}` has.
//   d) IT IS LEFT TO RIGHT whatever the page is.  Mathematics is written
//      left to right in every language, including the ones this toolbox is
//      mostly for, so it is isolated from the paragraph's direction.
//   e) THE SHEET SHOWS WHAT IT WILL BE, and says what is wrong in
//      MathJax's own words -- it does not throw on a mistake, it draws it
//      and marks it, and that mark is the only thing an author can act on.
//   f) AND THE EXERCISE FORM HAS ONE TOO, writing into the field the hand
//      was last in, with no block offered where a block cannot go.
//
// The studio is REAL (tests/studio_harness.py, a temporary library); only
// the document is made by this file.
const REPO = await Deno.realPath(new URL('..', import.meta.url));
const PY = Deno.env.get('PARSEH_PYTHON') || 'python3';

let ok = 0, fail = 0;
const assert = (v, m) => { if (v) { ok++; console.log('  ok  ', m); } else { fail++; console.log('  FAIL', m); } };

const hub = new Deno.Command(PY, {args: ['tests/studio_harness.py', 'studio'],
  cwd: REPO, stdout: 'piped', stderr: 'piped'}).spawn();
const rd = hub.stdout.getReader();
let buf = '', info = null;
while (!info) {
  const {value, done} = await rd.read();
  if (done) break;
  buf += new TextDecoder().decode(value);
  const line = buf.split('\n').find(l => l.startsWith('READY '));
  if (line) info = JSON.parse(line.slice(6));
}
const B = `http://127.0.0.1:${info.port}`;

const br = await chromium.launch({executablePath: Deno.env.get('CHROME_BIN'), headless: true});
const pg = await br.newPage({viewport: {width: 1400, height: 950}});
const errs = []; pg.on('pageerror', e => errs.push(e.message));

// ---------- a) the assets are served at all ----------
for (const u of ['/static/mathjax.js', '/static/mathjax.css', '/static/mathjax/tex-svg.js']) {
  const r = await fetch(B + u);
  assert(r.status === 200, `${u} is served: ${r.status} ${r.headers.get('content-type')}`);
}

// ---------- b) a document with maths in it ----------
const MD = `---
title: Maths
target: italian
---

# Formule

Einstein wrote [E=mc^2]{math} on the board, and an interval [x \\in [0,1]]{math} too.

:::math
\\int_0^1 x^2\\,dx = \\tfrac13
:::

:::exercise fill-blanks
prompt: Completa
text: La derivata di [x^2]{math} è [[d]].
- [d] [2x]{math}
:::
`;
const made = await (await fetch(`${B}/api/docs`, {
  method: 'POST', headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({markdown: MD})})).json();
assert(made.ok !== false, 'the document was made: ' + JSON.stringify(made).slice(0, 120));
const id = (made.meta && made.meta.id) || made.id || (made.doc && made.doc.id);
console.log('   doc id:', id);

await pg.goto(`${B}/doc/${id}`);
await pg.waitForSelector('#sheet');
await pg.waitForFunction(() => window.ParsehMath && document.querySelectorAll('.math').length > 0,
                         null, {timeout: 20000});
await pg.waitForFunction(() => [...document.querySelectorAll('.math')]
  .every(e => e.dataset.drawn), {timeout: 25000});
const drawn = await pg.evaluate(() => [...document.querySelectorAll('.math')].map(e => ({
  tex: e.dataset.tex, drawn: e.dataset.drawn, block: e.classList.contains('mathblock'),
  svg: /^<svg/.test(e.innerHTML.trim()),
})));
console.log('   formulae:', JSON.stringify(drawn.map(d => d.tex)));
assert(drawn.length === 5, 'all five formulae on the page: ' + drawn.length);
assert(drawn.every(d => d.drawn === 'yes' && d.svg), 'every one drawn as an svg');
assert(drawn.filter(d => d.block).length === 1, 'exactly one of them on its own');
assert(drawn.some(d => d.tex === 'x \\in [0,1]'), 'a formula keeps its own brackets: '
       + JSON.stringify(drawn.map(d => d.tex)));
assert(drawn.some(d => d.tex === '2x'), 'and one inside an exercise row was drawn too');
// the blank is still a blank
assert(await pg.evaluate(() => !!document.querySelector('.ex-fill')), 'the fill exercise rendered');

// ---------- b2) each formula appears ONCE ----------
// tex2svg answers the <svg> AND an <mjx-assistive-mml> beside it, for a
// screen reader.  MathJax hides that second one with a stylesheet it
// installs when IT typesets a page, and nothing here ever asks it to -- so
// without a rule of our own every formula is drawn twice, once as the
// picture and once as MathML the browser draws natively.  What says it is
// hidden is that the span is no wider than its picture.
// (a block is centred and full width by design, so its own width says
// nothing; what says it for both is that the copy is out of the flow, and
// for an inline one that the span is no wider than its picture)
const twice = await pg.evaluate(() => [...document.querySelectorAll('.math[data-drawn="yes"]')]
  .map(el => {
    const svg = el.querySelector('svg');
    const mml = el.querySelector('mjx-assistive-mml');
    if (!svg) return {tex: el.dataset.tex, bad: 'no svg'};
    if (mml && getComputedStyle(mml).position !== 'absolute')
      return {tex: el.dataset.tex, bad: 'the assistive copy is still in the flow'};
    const w = el.getBoundingClientRect().width, sw = svg.getBoundingClientRect().width;
    if (!el.classList.contains('mathblock') && w > sw + 4)
      return {tex: el.dataset.tex, w: Math.round(w), sw: Math.round(sw),
              bad: 'the span is wider than its picture'};
    return {tex: el.dataset.tex, bad: ''};
  }));
assert(twice.every(t => !t.bad), 'every formula is drawn once, not beside a second copy of itself: '
       + JSON.stringify(twice.filter(t => t.bad)));
assert(await pg.evaluate(() => !!document.querySelector('.math mjx-assistive-mml')),
       'and the copy a screen reader reads is still there, hidden rather than thrown away');

// ---------- c) it is LTR even in an RTL document ----------
const dir = await pg.evaluate(() => getComputedStyle(document.querySelector('.math')).direction);
assert(dir === 'ltr', 'a formula is left-to-right whatever the page is: ' + dir);

// ---------- d) the editor: the quick button and the sheet ----------
await pg.goto(`${B}/doc/${id}/edit`);
await pg.waitForSelector('#src');
await pg.waitForFunction(() => window.ParsehMath, null, {timeout: 20000});
assert(await pg.evaluate(() => !!document.querySelector('#ins-math')), 'the toolbar has a math button');
await pg.evaluate(() => {
  const s = document.querySelector('#src');
  s.focus();
  s.setSelectionRange(s.value.length, s.value.length);
});
await pg.click('#ins-math');
assert((await pg.inputValue('#src')).endsWith('[]{math}'), 'it inserts an empty mark at the cursor');

console.log('\n   the maths sheet');
await pg.click('#btn-math-editor');
await pg.waitForSelector('.math-modal');
await pg.fill('.mathbox', '\\frac{-b \\pm \\sqrt{b^2-4ac}}{2a}');
await pg.waitForFunction(() => /^<svg/.test(
  (document.querySelector('.math-stage').innerHTML.match(/<svg[\s\S]*/) || [''])[0]
) || document.querySelector('.math-stage svg'), null, {timeout: 20000});
assert(await pg.evaluate(() => !!document.querySelector('.math-stage svg')),
       'the picture is drawn under the notation as it is typed');
assert(await pg.evaluate(() => document.querySelector('.math-status').textContent) === '',
       'and nothing is complained about');

console.log('   a mistake is named, in MathJax\'s own words');
await pg.fill('.mathbox', '\\frac{1}{');
await pg.waitForFunction(() => document.querySelector('.math-status').textContent.length > 0,
                         null, {timeout: 20000});
const said = await pg.evaluate(() => document.querySelector('.math-status').textContent);
assert(/brace/i.test(said), 'it says what is wrong: ' + JSON.stringify(said));
assert(await pg.evaluate(() => document.querySelector('.math-status').classList.contains('err')),
       'and says it as a fault');

console.log('   on its own vs in the line');
await pg.fill('.mathbox', 'a^2+b^2=c^2');
await pg.waitForFunction(() => document.querySelector('.math-stage svg'), null, {timeout: 20000});
await pg.click('.math-opts input[value="block"]');
await pg.waitForTimeout(400);
assert(await pg.evaluate(() => !!document.querySelector('.math-stage .mathblock')),
       'choosing "on its own" redraws it as a block');
await pg.click('[data-x="ok"]');
await pg.waitForFunction(() => !document.querySelector('.math-modal'), null, {timeout: 10000});
const after = await pg.inputValue('#src');
assert(after.includes(':::math\na^2+b^2=c^2\n:::'), 'a fence went into the document: '
       + JSON.stringify(after.slice(-40)));

console.log('   Escape leaves it, which the tl sheet never allowed');
await pg.click('#btn-math-editor');
await pg.waitForSelector('.math-modal');
await pg.keyboard.press('Escape');
await pg.waitForTimeout(250);
assert(!await pg.evaluate(() => !!document.querySelector('.math-modal')), 'Escape closed it');
assert(await pg.evaluate(() => document.activeElement && document.activeElement.id) === 'src',
       'and the caret went back to the document');

console.log('\n   the exercise form has a maths button of its own');
await pg.evaluate(() => {
  openExerciseMarkdown(':::exercise fill-blanks\nprompt: Completa\ntext: La derivata e [[d]].\n- [d] due\n:::',
                       {onSave: () => {}});
});
await pg.waitForSelector('.ex-form-modal');
assert(await pg.evaluate(() => !!document.querySelector('[data-x="math"]')),
       'the form carries the button');
await pg.evaluate(() => {
  const f = [...document.querySelectorAll('.ex-form-body textarea, .ex-form-body input[type=text]')][0];
  f.focus();
  f.setSelectionRange(f.value.length, f.value.length);
});
await pg.click('[data-x="math"]');
await pg.waitForSelector('.math-modal');
assert(await pg.evaluate(() => document.querySelector('.math-opts').hidden),
       'a field has no room for a block, so the choice is not offered there');
await pg.fill('.mathbox', 'x^2');
await pg.waitForFunction(() => document.querySelector('.math-stage svg'), null, {timeout: 20000});
await pg.click('.math-modal [data-x="ok"]');
await pg.waitForFunction(() => !document.querySelector('.math-modal'), null, {timeout: 10000});
const field = await pg.evaluate(() =>
  [...document.querySelectorAll('.ex-form-body textarea, .ex-form-body input[type=text]')][0].value);
assert(field.indexOf('[x^2]{math}') >= 0,
       'the formula went into the field it came from: ' + JSON.stringify(field));
assert(await pg.evaluate(() => !!(document.activeElement && document.activeElement.closest
         && document.activeElement.closest('.ex-form-body'))),
       'and the hand is back in that field');
await pg.keyboard.press('Escape');

assert(errs.length === 0, 'nothing was thrown: ' + JSON.stringify(errs.slice(0, 3)));
console.log(`\nmath: ${ok} checks passed`);
await br.close();
try { hub.kill('SIGTERM'); } catch (e) {}
Deno.exit(fail ? 1 : 0);

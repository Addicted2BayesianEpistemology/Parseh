// Browser test of the page's hover editors landing on the copy of a word
// they were opened on, against the REAL routes on a temporary library
// (tests/studio_harness.py).  The colour palette, the transliteration field
// and the target-text overlay name what they edit by (text, occurrence);
// the page numbers each run and block, store.py finds the n-th one in the
// source (tests/test_run_occurrences.py has every construct).  Driven here:
//   a) the French starter's reading view: the second l'homme on the page (a
//      true/false question) is coloured, then given a transliteration --
//      the note above it, written earlier with the same word, is left alone
//   b) the German starter: a piece of the fill-in sentence, cut at its
//      blanks, is coloured there, not in the exercise further down
//   c) the English starter: a list item going on over an indented line
//      that is nothing but a mark
//   d) the Persian starter's editor: the second می‌روم, in an explanation
//      the preview shows, is coloured in the buffer -- not the one in the
//      inline note above it
//   e) the editor's preview of an exercise whose explanation is written
//      above its rows, and drawn below them: the word clicked in a row is the
//      row's; and a matching exercise, which draws every left side before
//      the bank of right ones: the left one clicked is the left one coloured
//   f) the editor's target-text overlay on a block of a row, written after
//      an explanation holding the same block: the row's block is replaced
//   g) the Japanese, Chinese and Hindi starters: the word right before a
//      formula is coloured, and the page drawn again still shows the formula
//      as mathematics and the word in its colour beside it
//   CHROME_BIN=... PARSEH_PYTHON=python3 deno run --allow-all tests/run_occurrences.mjs
//   SHOTS=<dir> saves screenshots
import {chromium} from 'npm:playwright-core@1.52.0';

const root = await Deno.realPath(new URL('..', import.meta.url));
const python = Deno.env.get('PARSEH_PYTHON') || 'python3';
const SHOTS = Deno.env.get('SHOTS') || '';
let passed = 0;
const assert = (v, m) => { if (!v) throw Error('FAIL: ' + m); passed++; console.log('  ok', m); };
const sleep = ms => new Promise(r => setTimeout(r, ms));
async function until(fn, what, ms = 8000) {
  const end = Date.now() + ms;
  for (;;) {
    let v;
    try { v = await fn(); } catch (_) { v = false; }
    if (v) return v;
    if (Date.now() > end) throw Error('FAIL: timed out: ' + what);
    await sleep(60);
  }
}

async function startHarness() {
  const proc = new Deno.Command(python, {args: [root + '/tests/studio_harness.py', 'studio'], cwd: root,
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
    if (done) throw Error('harness exited before READY:\n' + buf + log.join(''));
    buf += value;
    const m = buf.match(/READY (\{.*\})\n/);
    if (m) info = JSON.parse(m[1]);
  }
  (async () => { for (;;) { const r = await reader.read(); if (r.done) break; } })();
  return {proc, info, log};
}

const starter = code => Deno.readTextFile(`${root}/markdown/exlex/starters/${code}.md`);
// the lines of `after` that differ from `before`, as [index, text]
const changed = (before, after) => {
  const a = before.split('\n'), b = after.split('\n');
  return b.map((line, i) => [i, line]).filter(([i, line]) => a[i] !== line);
};
const lineOf = (md, text) => md.split('\n').findIndex(l => l.includes(text));

const {proc, info, log} = await startHarness();
const origin = `http://127.0.0.1:${info.port}`, base = info.studio;
const url = p => origin + base + p;
const api = async (method, path, body) => {
  const r = await fetch(url(path), {method, headers: body ? {'Content-Type': 'application/json'} : {},
                                    body: body ? JSON.stringify(body) : undefined});
  return r.json();
};
const create = async md => (await api('POST', '/api/docs', {markdown: md})).meta.id;
const source = async id => (await api('GET', `/api/docs/${id}`)).markdown;

const browser = await chromium.launch({executablePath: Deno.env.get('CHROME_BIN'), headless: true});
try {
  const context = await browser.newContext({viewport: {width: 1400, height: 900}});
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));

  const run = (text, occ) => page.locator(`#sheet [data-fa="${text}"][data-occ="${occ}"]`);
  /* Hover the run as a person would, see the cloud come up on screen next
     to it, and pick a colour in it. */
  async function colour(text, occ, name) {
    const span = run(text, occ);
    assert(await span.count() === 1, `the page offers ${text} #${occ} once`);
    await span.scrollIntoViewIfNeeded();
    await span.hover();
    const pal = page.locator('.fapal');
    await until(() => pal.isVisible(), 'the colour cloud opens');
    const seen = await pal.evaluate(p => {
      const r = p.getBoundingClientRect();
      return r.top >= 0 && r.left >= 0 && r.bottom <= innerHeight && r.right <= innerWidth && r.width > 50;
    });
    assert(seen, `the cloud over ${text} #${occ} is on the screen`);
    await pal.locator(`button[data-color="${name}"]`).click();
  }
  // the colour a run is drawn in, as the browser draws it
  const drawn = (text, occ) => run(text, occ).evaluate(e => getComputedStyle(e).color);
  const teal = () => page.evaluate(() => {
    const p = document.createElement('span');
    p.className = 'fac fac-teal';
    document.querySelector('#sheet').appendChild(p);
    const c = getComputedStyle(p).color;
    p.remove();
    return c;
  });

  // a) the French starter, reading view
  {
    const md = await starter('fr');
    const id = await create(md);
    await page.goto(url(`/doc/${id}`));
    await page.waitForSelector('#sheet');
    const row = lineOf(md, "- [le]{tl} + [homme]{tl} \\=> [l'homme]{tl}");
    const note = lineOf(md, "[homme]{tl} is silent, so the article loses its vowel: [l'homme]{tl}.]");
    assert(row > note && note > 0, `the note (line ${note}) is written before the question (line ${row})`);
    const ink = await drawn("l'homme", 0);
    await colour("l'homme", 1, 'teal');
    const after = await until(async () => { const s = await source(id); return s !== md && s; }, 'the colour is saved');
    assert(JSON.stringify(changed(md, after)) ===
           JSON.stringify([[row, "- [le]{tl} + [homme]{tl} \\=> [l'homme]{teal}, because the h is silent. => true"]]),
           "the second l'homme on the page is the one coloured in the source " + JSON.stringify(changed(md, after)));
    assert(await drawn("l'homme", 1) === await teal() && await drawn("l'homme", 0) === ink,
           "and it is the one drawn in teal on the page, the first as it was");
    // the transliteration field of the same cloud, on the same run
    await run("l'homme", 1).hover();
    await until(() => page.locator('.fapal').isVisible(), 'the cloud opens again');
    await page.locator('.fapal .tr-edit[data-kind="translit"] .tr-add').click();
    await page.locator('.fapal .tr-edit[data-kind="translit"] .tr-in').fill('lɔm');
    await page.keyboard.press('Enter');
    const after2 = await until(async () => { const s = await source(id); return s !== after && s; }, 'the transliteration is saved');
    assert(JSON.stringify(changed(after, after2)) ===
           JSON.stringify([[row, "- [le]{tl} + [homme]{tl} \\=> [l'homme]{teal translit:lɔm}, because the h is silent. => true"]]),
           'its transliteration is written on it, beside its colour ' + JSON.stringify(changed(after, after2)));
    if (SHOTS) await page.screenshot({path: `${SHOTS}/run-occurrences-fr.png`});
  }

  // b) the German starter: a piece of the fill-in sentence
  {
    const md = await starter('de');
    const id = await create(md);
    await page.goto(url(`/doc/${id}`));
    await page.waitForSelector('#sheet');
    const text = lineOf(md, 'text: [Gestern [[aux]] ich mit dem Zug nach Hamburg [[verb]].]{tl}');
    assert(text > 0 && lineOf(md, '- [ ] [Gestern]{tl}') > text, 'the sentence comes before the other Gestern');
    assert(await run('Gestern', 0).evaluate(e => !!e.closest('.ex-fill')), 'the first Gestern on the page is the sentence\'s');
    await colour('Gestern', 0, 'crimson');
    const after = await until(async () => { const s = await source(id); return s !== md && s; }, 'the colour is saved');
    assert(JSON.stringify(changed(md, after)) ===
           JSON.stringify([[text, 'text: [Gestern]{crimson} [[aux]] [ich mit dem Zug nach Hamburg]{tl} [[verb]][.]{tl}']]),
           'the piece is coloured where it is, the sentence written out as its pieces ' + JSON.stringify(changed(md, after)));
    // the page drawn again from the saved source: the sentence, its blanks
    await page.reload();
    await page.waitForSelector('#sheet');
    const fill = await page.locator('#sheet .ex-fill').first().evaluate(f => ({
      text: f.textContent, blanks: f.querySelectorAll('.ex-blank').length,
      red: getComputedStyle(f.querySelector('.fac-crimson')).color}));
    assert(fill.blanks === 2 && fill.text.includes('ich mit dem Zug nach Hamburg') && fill.red !== '',
           'and the sentence is drawn as before, with its two blanks ' + JSON.stringify(fill));
  }

  // c) the English starter: an item going on over a line of one mark
  {
    const md = await starter('en');
    const id = await create(md);
    await page.goto(url(`/doc/${id}`));
    await page.waitForSelector('#sheet');
    const line = lineOf(md, '  [a world record]{tl}');
    await colour('a world record', 0, 'teal');
    const after = await until(async () => { const s = await source(id); return s !== md && s; }, 'the colour is saved');
    assert(JSON.stringify(changed(md, after)) === JSON.stringify([[line, '  [a world record]{teal}']]),
           'the item\'s second line is coloured ' + JSON.stringify(changed(md, after)));
  }

  // d) the Persian starter's editor: an explanation the preview shows
  {
    const md = await starter('fa');
    const id = await create(md);
    await page.goto(url(`/doc/${id}/edit`));
    await page.waitForSelector('#src');
    await until(async () => /rendered/.test(await page.locator('#pv-status').textContent()), 'the preview renders');
    const note = lineOf(md, 'brackets^[In everyday speech می‌روم shrinks to');
    const expl = lineOf(md, 'explanation-correct: Right: با اتوبوس');
    assert(note > 0 && expl > note, 'the inline note is written before the explanation');
    await colour('می‌روم', 1, 'teal');
    const buf = await until(async () => { const s = await page.locator('#src').inputValue(); return s !== md && s; },
                            'the buffer is rewritten');
    assert(JSON.stringify(changed(md, buf)) ===
           JSON.stringify([[expl, 'explanation-correct: Right: با اتوبوس *bā otobus*, by bus, and [می‌روم]{teal} *mi-ravam*, I go.']]),
           'the explanation\'s می‌روم is coloured in the buffer, not the note\'s ' + JSON.stringify(changed(md, buf)));
    if (SHOTS) await page.screenshot({path: `${SHOTS}/run-occurrences-fa-editor.png`});
  }

  // e) an exercise drawn in an order of its own
  {
    const md = '---\ntitle: Explained first\nlang: en\ntarget: fa\n---\n\n:::exercise single-choice\n' +
               'prompt: Which one is the book?\nexplanation-correct: کتاب is the book.\n- [x] کتاب\n- [ ] دفتر\n:::\n';
    const id = await create(md);
    await page.goto(url(`/doc/${id}/edit`));
    await page.waitForSelector('#src');
    await until(async () => /rendered/.test(await page.locator('#pv-status').textContent()), 'the preview renders');
    const option = page.locator('#sheet .ex-option [data-fa="کتاب"]');
    const expl = page.locator('#sheet .ex-explanation [data-fa="کتاب"]');
    const drawnFirst = await option.evaluate((o, e) => !!(o.compareDocumentPosition(e) & Node.DOCUMENT_POSITION_FOLLOWING),
                                             await expl.elementHandle());
    assert(drawnFirst, 'the preview draws the row above the explanation');
    await colour('کتاب', Number(await option.getAttribute('data-occ')), 'teal');
    const buf = await until(async () => { const s = await page.locator('#src').inputValue(); return s !== md && s; },
                            'the buffer is rewritten');
    assert(JSON.stringify(changed(md, buf)) === JSON.stringify([[lineOf(md, '- [x] کتاب'), '- [x] [کتاب]{teal}']]),
           'the row\'s word is the one coloured, not the explanation\'s above it ' + JSON.stringify(changed(md, buf)));
  }
  {
    const md = '---\ntitle: Matching order\nlang: en\ntarget: fa\n---\n\n:::exercise match-translations\n' +
               'prompt: Match the words.\n- دفتر => کتاب\n- کتاب => book\n- قلم => pen\n:::\n';
    const id = await create(md);
    await page.goto(url(`/doc/${id}`));
    await page.waitForSelector('#sheet');
    const left = page.locator('#sheet .ex-pair-left [data-fa="کتاب"]');
    const occ = Number(await left.getAttribute('data-occ'));
    assert(occ === 1, 'the left کتاب, drawn first, is numbered as written: second (' + occ + ')');
    await colour('کتاب', occ, 'teal');
    const after = await until(async () => { const s = await source(id); return s !== md && s; }, 'the colour is saved');
    assert(JSON.stringify(changed(md, after)) === JSON.stringify([[lineOf(md, '- کتاب => book'), '- [کتاب]{teal} => book']]),
           'the left side clicked is the one coloured ' + JSON.stringify(changed(md, after)));
  }

  // f) the target-text overlay in the editor
  {
    const md = '---\ntitle: Overlay order\nlang: en\ntarget: fa\n---\n\n:::exercise single-choice\n' +
               'prompt: Which one?\nexplanation-correct: It is [کتاب!]{tl} here.\n- [x] [کتاب!]{tl}\n- [ ] [دفتر!]{tl}\n:::\n';
    const id = await create(md);
    await page.goto(url(`/doc/${id}/edit`));
    await page.waitForSelector('#src');
    await until(async () => /rendered/.test(await page.locator('#pv-status').textContent()), 'the preview renders');
    const block = page.locator('#sheet .ex-option [data-tl-src="کتاب!"]');
    assert(await block.count() === 1, 'the row offers its block to the overlay');
    await block.scrollIntoViewIfNeeded();
    await block.hover();
    const pen = page.locator('.rtl-edit-btn');
    await until(() => pen.isVisible(), 'the ✎ of the block shows');
    await pen.click();
    const box = page.locator('.modal.rtl-modal textarea');
    await until(() => box.isVisible(), 'the overlay opens');
    assert(await box.inputValue() === 'کتاب!', 'on the block\'s text');
    await box.fill('کتابها!');
    await page.locator('.modal.rtl-modal [data-x="ok"]').click();
    const buf = await until(async () => { const s = await page.locator('#src').inputValue(); return s !== md && s; },
                            'the buffer is rewritten');
    assert(JSON.stringify(changed(md, buf)) === JSON.stringify([[lineOf(md, '- [x] [کتاب!]{tl}'), '- [x] [کتابها!]{tl}']]),
           'the row\'s block is the one replaced, the explanation\'s left alone ' + JSON.stringify(changed(md, buf)));
    // the preview is drawn again a moment after the buffer changes
    assert(await until(async () => await block.count() === 0 &&
             await page.locator('#sheet .ex-explanation [data-tl-src="کتاب!"]').getAttribute('data-tl-occ') === '0',
                       'the preview is drawn again'),
           'the preview drawn again: the explanation\'s block, now the only one, is numbered first');
  }

  // g) the word right before a formula, in the Japanese, Chinese and Hindi
  //    starters: the palette writes its mark there, and the paragraph must
  //    still draw both, the word in its new colour and the formula as
  //    mathematics -- the formula used to be read from the mark's own `[`,
  //    and took the word, the colour and the prose between into itself
  for (const [code, word, tex] of [['ja', '五十音', '5 \\times 10 = 50'],
                                   ['zh', '三七二十一', '3 \\times 7 = 21'],
                                   ['hi', 'है', 'f = \\frac{60}{2000} \\times 1000 = 30']]) {
    const md = await starter(code);
    const id = await create(md);
    await page.goto(url(`/doc/${id}`));
    await page.waitForSelector('#sheet');
    const occ = await page.evaluate(([w, t]) => {
      const f = [...document.querySelectorAll('#sheet .math')].find(e => e.dataset.tex === t);
      const r = f && [...f.closest('p').querySelectorAll('[data-fa]')].find(e => e.dataset.fa === w);
      return r ? Number(r.dataset.occ) : -1;
    }, [word, tex]);
    assert(occ >= 0, `${code}: ${word} stands in the paragraph of the formula ${tex}`);
    await colour(word, occ, 'teal');
    const after = await until(async () => { const s = await source(id); return s !== md && s; }, 'the colour is saved');
    const diff = changed(md, after), at = lineOf(md, `[${tex}]{math}`);
    assert(diff.length === 1 && at - diff[0][0] >= 0 && at - diff[0][0] <= 1 &&
           diff[0][1] === md.split('\n')[diff[0][0]].replace(word, `[${word}]{teal}`),
           `${code}: the ${word} before the formula is the one coloured ` + JSON.stringify(diff));
    // the page drawn again from the saved source, and MathJax done with it
    await page.reload();
    await page.waitForSelector('#sheet');
    await page.waitForFunction(() => document.querySelectorAll('#sheet .math').length > 0 &&
      [...document.querySelectorAll('#sheet .math')].every(e => e.dataset.drawn), null, {timeout: 25000});
    const para = await page.evaluate(([w, t]) => {
      const f = [...document.querySelectorAll('#sheet .math')].find(e => e.dataset.tex === t);
      if (!f) return {formulas: [...document.querySelectorAll('#sheet .math')].map(e => e.dataset.tex)};
      const p = f.closest('p'), svg = f.querySelector('svg');
      const r = svg ? svg.getBoundingClientRect() : {width: 0, height: 0};
      f.scrollIntoView({block: 'center'});
      const s = svg ? svg.getBoundingClientRect() : null;
      const hit = s && document.elementFromPoint(s.left + s.width / 2, s.top + s.height / 2);
      const run = [...p.querySelectorAll('[data-fa]')].find(e => e.dataset.fa === w);
      return {drawn: f.dataset.drawn, w: r.width, h: r.height, onTop: !!(hit && f.contains(hit)),
              text: p.textContent, inTeal: !!(run && run.closest('.fac-teal')),
              colour: run ? getComputedStyle(run).color : ''};
    }, [word, tex]);
    assert(para.drawn === 'yes' && para.w > 20 && para.h > 5 && para.onTop,
           `${code}: the formula is drawn as mathematics, on the screen ` + JSON.stringify(para));
    // (the paragraph names `{math}` itself, in a code span)
    assert(!/\]\{|\{teal\}/.test(para.text) && !para.text.includes(tex),
           `${code}: no mark and no notation is left in the paragraph as text ` + JSON.stringify(para.text));
    assert(para.inTeal && para.colour === await teal(),
           `${code}: and ${word} is drawn in teal beside it ` + JSON.stringify(para));
    if (SHOTS) await page.screenshot({path: `${SHOTS}/run-occurrences-${code}-formula.png`});
  }

  assert(errors.length === 0, 'no script error on any page ' + JSON.stringify(errors));
} finally {
  await browser.close();
  proc.kill('SIGTERM');
  await proc.status;
}
console.log(`\n${passed} passed`);
if (log.join('').includes('Traceback')) {
  console.log(log.join(''));
  throw Error('FAIL: the server logged a traceback');
}

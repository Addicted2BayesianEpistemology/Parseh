// SPDX-License-Identifier: GPL-3.0-or-later
// Browser acceptance test for selection-first partial foreground colours and
// their actual standalone HTML export.
// CHROME_BIN=... PARSEH_PYTHON=python3 deno run --allow-all tests/partial_colour.mjs
import {chromium} from 'npm:playwright-core@1.52.0';

const root = await Deno.realPath(new URL('..', import.meta.url));
const python = Deno.env.get('PARSEH_PYTHON') || 'python3';
let passed = 0;
const assert = (v, m) => { if (!v) throw Error('FAIL: ' + m); passed++; console.log('  ok', m); };
const proc = new Deno.Command(python, {args: [root + '/tests/studio_harness.py', 'studio'], cwd: root,
                                       stdout: 'piped', stderr: 'inherit'}).spawn();
const reader = proc.stdout.pipeThrough(new TextDecoderStream()).getReader();
let buf = '', info;
while (!info) {
  const {value, done} = await reader.read();
  if (done) throw Error('harness exited before READY:\n' + buf);
  buf += value;
  const m = buf.match(/READY (\{.*\})\n/);
  if (m) info = JSON.parse(m[1]);
}
(async () => { for (;;) { const r = await reader.read(); if (r.done) break; } })();

const origin = `http://127.0.0.1:${info.port}`;
const source = `---
title: Partial colour
lang: en
target: fa
---

Plain کتاب and العربية and decomposed e\u0301. Clusters نَ, कि, が and 👩‍💻.

Segment [[ک[ت]{crimson}[ا]{indigo}ب]]{translit:ketāb} beside کتاب.
Arabic [[ا[لعر]{violet}بية]]{translit:al-ʿarabiyya} beside العربية.
`;
const tmp = await Deno.makeTempDir({prefix: 'parseh-partial-colour-'});
let browser;
try {
  const made = await (await fetch(origin + '/api/docs', {method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({markdown: source})})).json();
  const id = made.meta.id;
  browser = await chromium.launch({executablePath: Deno.env.get('CHROME_BIN'), headless: true});
  const page = await (await browser.newContext({viewport: {width: 1280, height: 900}})).newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.goto(`${origin}/doc/${id}/edit`);
  await page.waitForSelector('#src');
  await page.waitForFunction(() => /rendered/.test(document.querySelector('#pv-status').textContent));

  const select = async (needle, inner, occurrence = 0) => page.locator('#src').evaluate((el, arg) => {
    let at = -1;
    for (let i = 0; i <= arg.occurrence; i++) at = el.value.indexOf(arg.needle, at + 1);
    const p = at + arg.needle.indexOf(arg.inner);
    el.focus(); el.setSelectionRange(p, p + arg.inner.length);
  }, {needle, inner, occurrence});

  // Exact partial selection, main button, one undo.
  await select('Plain کتاب', 'تا');
  await page.click('#ins-color');
  await page.waitForFunction(() => document.querySelector('#src').value.includes('Plain [[ک[تا]{teal}ب]]'));
  assert(true, 'the main colour button colours exactly the selected letters');
  await page.click('#btn-undo');
  await page.waitForFunction(src => document.querySelector('#src').value === src, source);
  assert(true, 'one undo reverses the complete colour operation');

  // With no selection, the logical word under the caret is used; empty
  // colour syntax is never inserted.
  await select('Plain کتاب', '');
  await page.locator('#src').evaluate(el => {
    const at = el.value.indexOf('Plain کتاب') + 'Plain ک'.length;
    el.focus(); el.setSelectionRange(at, at);
  });
  await page.click('#ins-color');
  await page.waitForFunction(() => document.querySelector('#src').value.includes('Plain [کتاب]{teal}'));
  assert(!((await page.locator('#src').inputValue()).includes('[]{teal}')),
         'a caret colours its logical word and never inserts empty markup');
  await page.click('#btn-undo');

  // The selection deliberately contains only the combining mark.  The
  // browser expands it to the complete extended grapheme cluster.
  await select('e\u0301', '\u0301');
  await page.click('#ins-color');
  await page.waitForFunction(() => document.querySelector('#src').value.includes('[e\u0301]{teal}'));
  assert(true, 'a combining mark cannot be split from its base');
  await page.click('#btn-undo');
  await select('[[ک[ت]{crimson}[ا]{indigo}ب]]', 'ت');
  await page.click('.colour-pick > summary');
  await page.locator('#colour-menu [data-editor-colour=""]').click();
  await page.waitForFunction(() => document.querySelector('#src').value.includes('[[کت[ا]{indigo}ب]]{translit:ketāb}'));
  const cleared = await page.locator('#src').inputValue();
  assert(cleared.includes('[[کت[ا]{indigo}ب]]{translit:ketāb}'),
         'No colour removes only the selected interval and preserves transliteration');
  await page.click('#btn-undo');
  for (const [cluster, inside, name] of [['نَ', 'َ', 'a Persian diacritic'],
                                         ['कि', 'ि', 'a Hindi cluster'],
                                         ['が', '゙', 'a decomposed Japanese mark'],
                                         ['👩‍💻', '💻', 'an emoji ZWJ sequence']]) {
    await select(cluster, inside);
    await page.click('#ins-color');
    await page.waitForFunction(mark => document.querySelector('#src').value.includes(mark), `[${cluster}]{teal}`);
    assert(true, `${name} stays one grapheme`);
    await page.click('#btn-undo');
  }

  // Recolour inside the existing semantic node through the palette.
  await select('[[ک[ت]{crimson}[ا]{indigo}ب]]', 'ت');
  await page.click('.colour-pick > summary');
  await page.locator('#colour-menu [data-editor-colour="violet"]').click();
  await page.waitForFunction(() => document.querySelector('#src').value.includes('[[ک[ت]{violet}[ا]{indigo}ب]]'));
  assert(true, 'a palette choice immediately recolours a subsection without nesting');
  assert((await page.locator('#src').inputValue()).includes('{translit:ketāb}'),
         'palette recolouring preserves the whole-word transliteration');
  await page.click('#btn-undo');
  assert(await page.locator('.fapal button[data-color], .fapal input[type="color"], .fapal .none').count() === 0,
         'the preview cloud constructs no colour controls');

  // Actual exported artifact, opened from file:// with no server dependency.
  const html = await (await fetch(`${origin}/download/${id}/html`)).text();
  const file = `${tmp}/partial.html`;
  await Deno.writeTextFile(file, html);
  const asked = [];
  const exported = await (await browser.newContext({viewport: {width: 1000, height: 800}})).newPage();
  exported.on('request', r => { if (!/^(file|data|blob):/.test(r.url())) asked.push(r.url()); });
  exported.on('pageerror', e => errors.push('export: ' + e.message));
  await exported.goto('file://' + file);
  const run = exported.locator('.segmented-colour-run[data-fa="کتاب"]');
  await run.waitFor();
  const shape = await run.evaluate(el => {
    const kids = [...el.querySelectorAll('.seg-colour')];
    const style = kids.map(k => {
      const s = getComputedStyle(k);
      return [s.display, s.fontFamily, s.fontSize, s.direction, s.unicodeBidi,
              s.margin, s.padding];
    });
    const outer = getComputedStyle(el);
    const plain = [...document.querySelectorAll('.fa[data-fa="کتاب"]')]
      .find(x => !x.classList.contains('segmented-colour-run'));
    return {text: el.textContent, outer: el.dataset.fa, translit: el.dataset.translit,
            pieces: kids.map(k => [k.textContent, k.dataset.color]), style,
            sameFont: style.every(s => s[1] === outer.fontFamily && s[2] === outer.fontSize),
            widths: [el.getBoundingClientRect().width, plain.getBoundingClientRect().width]};
  });
  assert(shape.text === 'کتاب' && shape.outer === 'کتاب' && shape.translit === 'ketāb',
         'the exported DOM contains one flattened semantic word with its transliteration');
  assert(JSON.stringify(shape.pieces) === JSON.stringify([['ت', 'crimson'], ['ا', 'indigo']]),
         'the exported artifact preserves both visual colour pieces');
  assert(shape.sameFont && shape.style.every(s => s[0] === 'inline' && s[3] === 'rtl' && s[4] === 'normal' && s[5] === '0px' && s[6] === '0px'),
         'colour boundaries remain plain inline text with inherited shaping and bidi properties: ' + JSON.stringify(shape.style));
  assert(Math.abs(shape.widths[0] - shape.widths[1]) < 1,
         'the coloured Persian word has the same laid-out width as the plain word');

  const arabic = exported.locator('.segmented-colour-run[data-fa="العربية"]');
  const arabicShape = await arabic.evaluate(el => {
    const plain = [...document.querySelectorAll('.fa[data-fa="العربية"]')]
      .find(x => !x.classList.contains('segmented-colour-run'));
    return {text: el.textContent, pieces: el.querySelectorAll('.seg-colour').length,
            widths: [el.getBoundingClientRect().width, plain.getBoundingClientRect().width]};
  });
  assert(arabicShape.text === 'العربية' && arabicShape.pieces === 1
         && Math.abs(arabicShape.widths[0] - arabicShape.widths[1]) < 1,
         'the exported Arabic fixture remains one joined word at the plain word width');

  await run.locator('.seg-colour').first().hover();
  await exported.waitForSelector('.fapal', {state: 'visible'});
  assert((await exported.locator('.fapal .tr-val').filter({hasText: 'ketāb'}).count()) === 1,
         'pointing at an inner colour piece opens one cloud for the whole word');
  assert((await exported.locator('.fapal button[data-color], .fapal input[type="color"], .fapal .none').count()) === 0,
         'the standalone cloud has no swatches, picker or remove-colour action');
  await exported.locator('.fapal .tr-val').click();
  await exported.locator('.fapal .tr-in').fill('ketâb');
  await exported.keyboard.press('Enter');
  await exported.waitForFunction(() => document.querySelector('.segmented-colour-run[data-fa="کتاب"]').dataset.translit === 'ketâb');
  assert((await run.locator('.seg-colour').count()) === 2,
         'a page-only transliteration edit preserves every colour segment');
  assert(asked.length === 0, 'the exported page asks no server for the feature');
  assert(errors.length === 0, 'no browser script error: ' + errors.join(' | '));
  console.log(`Partial colours passed (${passed} checks)`);
} finally {
  if (browser) await browser.close();
  proc.kill('SIGTERM');
  await proc.status.catch(() => {});
  await Deno.remove(tmp, {recursive: true}).catch(() => {});
}

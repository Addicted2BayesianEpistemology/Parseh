// SPDX-License-Identifier: GPL-3.0-or-later
import { chromium } from 'npm:playwright-core@1.52.0';
// Run: CHROME_BIN=/path/to/chrome PARSEH_PYTHON=python3 deno run --allow-all tests/outline.mjs
//
// The book as an outline (outlinePicker, lib/tex2html.py): the one control
// the fold sheet, the sections sheet and the narration panel pick a stretch of
// the book with, where each used to offer every paragraph -- or every
// subparagraph -- of the book in a flat list, twice.  On a book of three
// chapters that ALL HAVE THE LABELS 1.1 1.2 2.1 2.2 (tests/outline_harness.py),
// served by the REAL server, whose doors write what is picked:
//  a) THE OUTLINE: chapters, their sections, their paragraphs by number and
//     opening words.  One click takes a whole thing; a click on the pick opens
//     it; Shift-click and "stretch it to…" take everything in between; the
//     pick is tinted, its ends marked, and said in words.
//  b) THE KEYS are a tree's: the arrows walk and open, Enter picks,
//     Shift+Enter stretches, and Escape lets a half-made stretch go before it
//     closes the sheet.
//  c) THE FILTER finds a paragraph by its words and shows where it is.
//  d) FOLDING what is picked, through the door, folds exactly that.
//  e) SECTIONS: pick what you want to name -- a chapter, or a paragraph to
//     open a section at, or a section's heading to rename or remove it.
//  f) A RECORDING OF CHAPTER 2 is stored as "2:1.1" to "2:2.2", and the
//     player plays chapter 2 -- and not chapter 1, whose labels are the same --
//     from it.
const root = await Deno.realPath(new URL('..', import.meta.url));
Deno.chdir(root);
const PY = Deno.env.get('PARSEH_PYTHON') || 'python3';
const TMP = await Deno.makeTempDir({prefix: 'parseh-outline-'});
const td = new TextDecoder();
let passed = 0;
const assert = (v, m) => { if (!v) throw Error('FAIL: ' + m); passed++; console.log('  ok', m); };
const eq = (got, want, m) => assert(JSON.stringify(got) === JSON.stringify(want),
                                    m + ' (got ' + JSON.stringify(got) + ')');
const sleep = ms => new Promise(r => setTimeout(r, ms));
function run(...args) {
  const o = new Deno.Command(PY, {args, stdout: 'piped', stderr: 'piped'}).outputSync();
  if (o.code) throw Error(td.decode(o.stderr) || td.decode(o.stdout));
  return td.decode(o.stdout);
}
const made = JSON.parse(run('tests/outline_harness.py', 'build', TMP).trim().split('\n').pop());
const PORT = 8830 + Math.floor(Math.random() * 60);
const hub = new Deno.Command(PY, {args: ['tests/outline_harness.py', 'serve', TMP, String(PORT)],
                                  stdout: 'null', stderr: 'piped'}).spawn();
const B = `http://127.0.0.1:${PORT}`;
for (let i = 0; i < 80; i++) {
  try { const r = await fetch(`${B}/books/`); await r.body?.cancel(); break; }
  catch (_) { await sleep(250); }
}
const READER = B + made.reader;
const readText = p => Deno.readTextFileSync(made.book + '/' + p);
const bookJson = () => JSON.parse(readText('book.json'));

const browser = await chromium.launch({executablePath: Deno.env.get('CHROME_BIN'), headless: true});
const errors = [];
try {
  let page = await browser.newPage({viewport: {width: 1280, height: 900}});
  page.on('pageerror', e => errors.push(e.message));
  await page.goto(READER);
  await page.waitForFunction(() => typeof SUBS !== 'undefined' && typeof outlinePicker === 'function');
  const say = sel => page.textContent(sel + ' .olsay');
  const rows = sel => page.evaluate(s => [...document.querySelectorAll(s + ' li[role="treeitem"]')]
    .filter(li => li.offsetParent !== null)
    .map(li => li.querySelector('.olk').textContent + (li.querySelector('.olt').textContent
      ? ' ' + li.querySelector('.olt').textContent : '')), sel);

  console.log('a) the outline');
  await page.click('#fold');
  await page.waitForSelector('#fdbox:not([hidden])');
  eq(await rows('#fdpick'), ['chapter 1 The Clock', 'chapter 2 The Wind', 'chapter 3'],
     'the book opens as its chapters, each by its number and its name');
  eq(await say('#fdpick'), 'nothing picked yet', 'and says that nothing is picked');
  assert(await page.isDisabled('#fddo'), 'so there is nothing to fold yet');
  const ch = n => `#fdpick li.ol-ch:nth-child(${n}) > .olr`;
  await page.click(ch(2));
  eq(await say('#fdpick'), 'chapter 2 · ⁨The Wind⁩ · 2 paragraphs',
     'one click takes a whole chapter, and the line says which, and how much');
  assert(!await page.isDisabled('#fddo'), 'and the fold button wakes');
  eq(await page.evaluate(() => [...document.querySelectorAll('#fdpick li.ol-ch')].map(li =>
       [li.classList.contains('in'), li.getAttribute('aria-selected')])),
     [[false, 'false'], [true, 'true'], [false, 'false']],
     'the chapter picked is tinted, and says so to a screen reader');
  await page.click(ch(3), {modifiers: ['Shift']});
  eq(await say('#fdpick'), 'chapters 2–3 · 4 paragraphs', 'Shift-click stretches it to the next chapter');
  eq(await page.evaluate(() => [...document.querySelectorAll('#fdpick li.ol-ch')].map(li =>
       [...li.querySelectorAll(':scope > .olr .oltag')].map(t => t.textContent).join())),
     ['', 'from', 'to'], 'its two ends are marked');
  // a click on something else picks that instead; a click on the pick opens it
  await page.click(ch(2));
  eq(await say('#fdpick'), 'chapter 2 · ⁨The Wind⁩ · 2 paragraphs', 'a plain click picks again');
  await page.click(ch(2));
  eq(await page.getAttribute('#fdpick li.ol-ch:nth-child(2)', 'aria-expanded'), 'true',
     'a click on what is picked opens it, to go finer');
  eq(await rows('#fdpick li.ol-ch:nth-child(2) > ul'), ['§ Morning', '§ Evening'],
     'and shows its sections by name');
  eq(await say('#fdpick'), 'chapter 2 · ⁨The Wind⁩ · 2 paragraphs', 'without changing the pick');
  // "stretch it to…", for a finger, or for anybody who never Shift-clicks
  await page.click('#fdpick .olstretch');
  eq(await page.getAttribute('#fdpick .olstretch', 'aria-pressed'), 'true', 'stretch it to… is pressed');
  assert(/Now pick where it ends/.test(await page.textContent('#fdpick .olhint')),
         'and the hint says what the next pick does');
  await page.click(`#fdpick li.ol-ch:nth-child(1) > .olr`);
  eq(await say('#fdpick'), 'chapters 1–2 · 4 paragraphs', 'the next pick is where it ends, backwards too');
  eq(await page.getAttribute('#fdpick .olstretch', 'aria-pressed'), 'false', 'and the stretch is done');
  await page.click('#fdpick .olopen');
  // (chapters 2 and 3 have a word of their own before every chunk, which is
  // what their opening words show)
  eq(await rows('#fdpick'), ['chapter 1 The Clock', '¶ 1 The old man wound the clock',
                             '§ The Child', '¶ 2 A child came in and asked',
                             'chapter 2 The Wind', '§ Morning', '¶ 1 Then The old man Then wound',
                             '§ Evening', '¶ 2 Then A child came in Then',
                             'chapter 3', '¶ 1 So The old man So wound', '¶ 2 So A child came in So'],
     'open all opens every chapter and every section');
  await page.click('#fdpick .olshut');
  eq((await rows('#fdpick')).length, 3, 'close all closes them again');

  console.log('b) the keys');
  await page.focus('#fdpick li.ol-ch:nth-child(1)');
  await page.keyboard.press('ArrowDown');
  await page.keyboard.press('ArrowRight');
  await page.keyboard.press('ArrowDown');
  eq(await page.evaluate(() => document.activeElement.querySelector('.olt').textContent), 'Morning',
     'the arrows walk the rows and open a chapter');
  await page.keyboard.press('Enter');
  eq(await say('#fdpick'), 'the section ⁨Morning⁩, in chapter 2 · 1 paragraph', 'Enter picks');
  await page.keyboard.press('ArrowDown');
  await page.keyboard.press('Shift+Enter');
  eq(await say('#fdpick'), 'chapter 2 · ⁨The Wind⁩ · 2 paragraphs',
     'Shift+Enter stretches -- and two sections that make a chapter are said as the chapter');
  await page.click('#fdpick .olstretch');
  await page.focus('#fdpick li.ol-ch:nth-child(1)');
  await page.keyboard.press('Escape');
  assert(!await page.isHidden('#fdbox') &&
         await page.getAttribute('#fdpick .olstretch', 'aria-pressed') === 'false',
         'Escape lets a half-made stretch go, and leaves the sheet open');

  console.log('c) the filter');
  await page.fill('#fdpick .olq', 'then a child');
  eq(await rows('#fdpick'), ['chapter 2 The Wind', '§ Evening', '¶ 2 Then A child came in Then'],
     'a paragraph found by its words is shown where it is: its chapter, its section');
  await page.fill('#fdpick .olq', 'nothing like this');
  assert(await page.isVisible('#fdpick .olnone'), 'and a search that finds nothing says so');
  await page.focus('#fdpick .olq');
  await page.keyboard.press('Escape');
  assert(await page.inputValue('#fdpick .olq') === '' && !await page.isHidden('#fdbox'),
         'Escape empties the box before it closes anything');

  console.log('d) folding what is picked');
  await page.click('#fdpick .olopen');
  await page.click('#fdpick li.ol-sec:has-text("Evening") > .olr');
  await page.click('#fdpick li.ol-ch:nth-child(3) li.ol-p:first-child > .olr', {modifiers: ['Shift']});
  eq(await say('#fdpick'), 'chapter 2, ¶ 2 → chapter 3, ¶ 1 · 2 paragraphs',
     'a stretch across a chapter\'s end is said by its two ends');
  await page.click('#fddo');
  await page.waitForFunction(() => /folded away/.test(document.querySelector('#fdstat').textContent),
                             null, {timeout: 20000});
  eq(JSON.parse(readText('reading.json')).collapsed, [['2:2', '3:1']],
     'the door folds exactly those two paragraphs, and reading.json says so');
  eq(await page.evaluate(() => [...document.querySelectorAll('#fdlist .fdsee')].map(b => b.textContent)),
     ['chapter 2, ¶ 2 → chapter 3, ¶ 1 · 2 paragraphs'], 'the run is listed in the same words');
  eq(await page.evaluate(() => [...document.querySelectorAll('#fdpick li.ol-p, #fdpick li.ol-sec')]
       .filter(li => li.querySelector(':scope > .olr .olfold')).map(li => li.querySelector('.olt').textContent)),
     ['Evening', 'Then A child came in Then', 'So The old man So wound'],
     'and the rows it covers say they are folded');
  await page.click('#fdlist .fdrun button:not(.fdsee)');
  await page.waitForFunction(() => /unfolded/.test(document.querySelector('#fdstat').textContent),
                             null, {timeout: 20000});
  // (lib/reading.py takes the file away when there is nothing left in it)
  let left = [];
  try { left = JSON.parse(readText('reading.json')).collapsed || []; } catch (_) { /* gone */ }
  eq(left, [], 'and unfolding it from the list lets it go');
  await page.keyboard.press('Escape');

  console.log('e) sections: pick what you want to name');
  await page.evaluate(() => secOpen(true, null));
  await page.waitForSelector('#secbox:not([hidden])');
  const secRows = () => page.evaluate(() => [!document.getElementById('secchrow').hidden,
                                             !document.getElementById('secrow').hidden]);
  eq(await secRows(), [false, false], 'with nothing picked, nothing is offered to name');
  await page.click('#secpick li.ol-ch:nth-child(3) > .olr');
  eq(await secRows(), [true, false], 'a chapter picked offers its name');
  await page.fill('#secchname', 'Night');
  await page.press('#secchname', 'Enter');
  await page.waitForFunction(() => /named/.test(document.querySelector('#secstat').textContent),
                             null, {timeout: 20000});
  assert(readText('ch3.tex').includes('\\chapname{Night}'), 'and the name lands in the chapter\'s file');
  await page.click('#secpick li.ol-ch:nth-child(3) > .olr');        // open it
  await page.click('#secpick li.ol-ch:nth-child(3) li.ol-p:nth-child(2) > .olr');
  eq(await secRows(), [false, true], 'a paragraph picked offers a section starting there');
  eq(await page.textContent('#secdo'), 'start a section here', 'and says it would start one');
  await page.fill('#secname', 'The End');
  await page.click('#secdo');
  await page.waitForFunction(() => /written/.test(document.querySelector('#secstat').textContent),
                             null, {timeout: 20000});
  assert(/\\secmark\{The End\}\s*\\parnum\{2\.1\}/.test(readText('ch3.tex')),
         'and the section is written before that paragraph, in its chapter\'s file');
  await page.click('#secpick li.ol-ch:nth-child(2) > .olr');
  await page.click('#secpick li.ol-ch:nth-child(2) > .olr');
  eq(await page.evaluate(() => [...document.querySelectorAll('#secpick li.ol-ch:nth-child(2) li.ol-sec')]
       .map(li => li.getAttribute('aria-disabled'))), [null, null],
     'a section\'s heading is as live as the paragraph it picks, not greyed out');
  await page.click('#secpick li.ol-sec:has-text("Morning") > .olr');
  eq(await page.evaluate(() => [document.getElementById('secdo').textContent,
                                document.getElementById('secname').value,
                                !document.getElementById('secdel').hidden]),
     ['rename this section', 'Morning', true], 'a section\'s heading offers to rename it or remove it');
  await page.click('#secpick li.ol-sec:has-text("Morning") > .olr > .oltw');   // close it
  eq(await page.evaluate(() => [...document.querySelectorAll('#secpick li.part')]
       .map(li => li.querySelector('.olk').textContent + ' ' + li.querySelector('.olt').textContent)),
     ['chapter 2 The Wind', '§ Morning'], 'and a closed row that holds the pick is marked, so it can be found');
  await page.click('#secdel');
  await page.waitForFunction(() => /taken away/.test(document.querySelector('#secstat').textContent),
                             null, {timeout: 20000});
  assert(!readText('ch2.tex').includes('\\secmark{Morning}') && readText('ch2.tex').includes('\\secmark{Evening}'),
         'and removing it takes that section away and no other');
  await page.keyboard.press('Escape');

  console.log('f) a recording of chapter 2, in a book whose chapters share their labels');
  // the doors above rebuilt the reader the way the real checkout wants it
  run('tests/outline_harness.py', 'relink', TMP);
  await page.close();
  page = await browser.newPage({viewport: {width: 1280, height: 900}});
  page.on('pageerror', e => errors.push(e.message));
  await page.goto(READER);
  await page.waitForFunction(() => typeof SUBS !== 'undefined' && typeof outlinePicker === 'function');
  const add = async (chapter, tone) => {
    await page.click('#naddbtn');
    await page.waitForSelector('#nadd:not([hidden])');
    await page.click(`#naddpick li.ol-ch:nth-child(${chapter}) > .olr`);
    const picked = await page.textContent('#naddpick .olsay');
    const [fc] = await Promise.all([page.waitForEvent('filechooser'), page.click('label:has(#npaudio)')]);
    await fc.setFiles(tone);
    await page.waitForFunction(() => document.getElementById('nadd').hidden, null, {timeout: 60000});
    return picked;
  };
  await page.click('#narr');
  await page.waitForSelector('#narrbox:not([hidden])');
  await page.click('#naddbtn');
  eq(await page.textContent('#naddpick .olsay'), 'the whole book', 'a new recording starts as the whole book');
  await page.click('#naddbtn');
  eq(await add(2, made.tones[0]), 'chapter 2 · ⁨The Wind⁩ · 4 subparagraphs',
     'chapter 2 picked, down to its subparagraphs');
  eq(bookJson().narrations.map(n => [n.id, n.from, n.to]), [['n1', '2:1.1', '2:2.2']],
     'and stored WITH ITS CHAPTER: "1.1" alone is chapter 1\'s first subparagraph too');
  await add(1, made.tones[1]);
  eq(bookJson().narrations.map(n => [n.id, n.from, n.to]),
     [['n1', '2:1.1', '2:2.2'], ['n2', '1:1.1', '1:2.2']], 'a second recording, of chapter 1');
  const st = await (await fetch(READER + '__narration/status')).json();
  eq(st.narrations.map(n => [n.id, n.lo, n.hi, n.timed, n.subs]), [['n1', 4, 7, 4, 4], ['n2', 0, 3, 4, 4]],
     'the server places each where it is, and counts what each has timed there');
  const bad = await fetch(READER + '__narration/audio?name=x.wav&from=4:1.1&to=4:2.2',
                          {method: 'POST', body: new Uint8Array(64)});
  const said = await bad.json();
  assert(bad.status === 400 && /no subparagraph 1\.1 in chapter 4/.test(said.error),
         'a stretch the book does not have is refused before the file is read: ' + said.error);

  run('tests/outline_harness.py', 'relink', TMP);
  await page.goto(READER);
  await page.waitForFunction(() => typeof SUBS !== 'undefined' && typeof narrFor === 'function');
  eq(await page.evaluate(() => SUBS.map((s, i) => (narrFor(i) || {}).id || '-')),
     ['n2', 'n2', 'n2', 'n2', 'n1', 'n1', 'n1', 'n1', '-', '-', '-', '-'],
     'the player plays chapter 1 from n2 and chapter 2 from n1, and chapter 3 from neither');
  await page.click('#narr');
  await page.waitForSelector('#nlist:not([hidden])');
  const r1 = page.locator('#nlist .nitem').first();
  await r1.locator('.ntog').click();
  eq(await r1.locator('[data-x="covsay"]').textContent(), 'chapter 2 · ⁨The Wind⁩ · 4 subparagraphs',
     'a row says what its recording covers, in words');
  await r1.locator('[data-x="covchg"]').click();
  eq(await page.evaluate(() => [...document.querySelectorAll('#nlist .nitem:first-child li.ol-ch')].map(li =>
       [li.classList.contains('in'), [...li.querySelectorAll(':scope > .olr .oltag')].map(t => t.textContent).join()])),
     [[false, 'n2'], [true, ''], [false, '']],
     'its outline opens on its own chapter, with the other recording marked where it is');
  // a stretch saved from the drawer is written with its chapter too
  await r1.locator('li.ol-ch:nth-child(3) > .olr').click({modifiers: ['Shift']});
  await r1.locator('[data-x="savecovers"]').click();
  await page.waitForFunction(() => true);
  for (let i = 0; i < 80 && bookJson().narrations[0].to !== '3:2.2'; i++) await sleep(250);
  eq(bookJson().narrations.map(n => [n.id, n.from, n.to]),
     [['n1', '2:1.1', '3:2.2'], ['n2', '1:1.1', '1:2.2']], 'stretched to chapter 3 and saved from the row');

  assert(errors.length === 0, 'the page threw nothing: ' + errors.join(' | '));
} finally {
  await browser.close();
  try { hub.kill('SIGTERM'); } catch (_) {}
  await hub.status;
  await Deno.remove(TMP, {recursive: true}).catch(() => {});
}
console.log(`\noutline: ${passed} checks passed`);

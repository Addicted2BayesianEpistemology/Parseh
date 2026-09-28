// SPDX-License-Identifier: GPL-3.0-or-later
// Browser test of which side a flashcard shows first (`direction:` forward,
// reverse, both-random, both-repeat) against the REAL routes on a temporary
// library and exercises store (tests/decks_harness.py, studio mode), and a
// REAL exported page opened as a file:
//   a) a document page, with Math.random forced to each outcome: a
//      both-random card shows either side first, `.ex-card-front` stays the
//      side shown, it turns and turns back, Enlarge shows the same side
//      first; forward, reverse and both-repeat never move; a both-repeat
//      card has its note under it, outside its box, and a click on the note
//      does not turn the card
//   b) the real draw: real page loads count both outcomes, thousands of
//      binds come out near half each, and a second bind never draws again
//   c) an RTL (fa) and two CJK (ja, zh) cards
//   d) the editor's preview (both sides, nothing drawn, the note), the
//      exercise form's "Which side appears first" with all four values,
//      `directions` narrowing it, the form's own preview, and the source it
//      saves
//   e) a deck's cram page and study page draw the side each time a card is shown
//   f) the document exported as one HTML file, and a deck exported as one,
//      opened as files: the note, the draw, the turn, no network
//   CHROME_BIN=... PARSEH_PYTHON=python3 deno run --allow-all tests/flashcard_direction.mjs
//   SHOTS=<dir> saves screenshots
import {chromium} from 'npm:playwright-core@1.52.0';

const root = await Deno.realPath(new URL('..', import.meta.url));
const python = Deno.env.get('PARSEH_PYTHON') || 'python3';
const SHOTS = Deno.env.get('SHOTS') || '';
const TMP = await Deno.makeTempDir({prefix: 'parseh-flashcard-direction-'});
let passed = 0;
const assert = (v, m) => { if (!v) throw Error('FAIL: ' + m); passed++; console.log('  ok', m); };
const sleep = ms => new Promise(r => setTimeout(r, ms));
const NOTE = 'When exported to a deck, both sides will be asked.';

const doc = (target, cards) => `---\ntitle: Directions ${target}\ntarget: ${target}\nlang: en\n---\n\n`
  + cards.map(c => `:::exercise flashcard\n${c}\n:::\n`).join('\n');
const DOCS = {
  en: doc('en', [
    'card-type: vocab\ntarget: [clock]{tl}\nmeaning: a thing that tells the time\ndirection: both-repeat',
    'card-type: vocab\ntarget: [wound]{tl}\nmeaning: turned a key\ndirection: both-random',
    'card-type: vocab\ntarget: [door]{tl}\nmeaning: a way in\ndirection: reverse',
    'card-type: vocab\ntarget: [gate]{tl}\nmeaning: a way through\ndirection: forward']),
  fa: doc('fa', ['card-type: vocab\ntarget: [کتاب]{tl}\nmeaning: a book\ndirection: both-random',
                 'card-type: vocab\ntarget: [سلام]{tl}\nmeaning: hello\ndirection: both-repeat']),
  ja: doc('ja', ['card-type: vocab\ntarget: [猫]{tl}\nreading: ねこ\nmeaning: cat\ndirection: both-random']),
  zh: doc('zh', ['card-type: vocab\ntarget: [谢谢]{tl}\ntransliteration: xièxie\nmeaning: thanks\ndirection: both-random']),
};

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

const {proc, info} = await startHarness();
const B = `http://127.0.0.1:${info.port}`;
const send = (method, path, body) => fetch(B + path, {method, headers: {'Content-Type': 'application/json'}, body});
const ids = {};
for (const [k, md] of Object.entries(DOCS))
  ids[k] = (await (await send('POST', '/api/docs', JSON.stringify({markdown: md}))).json()).meta.id;
const deck = (await (await send('POST', '/exercises/api/decks', JSON.stringify({name: 'Dir deck', lang: 'en'}))).json()).deck;
const itemIds = [];
for (const c of ['card-type: vocab\ntarget: [wound]{tl}\nmeaning: turned a key\ndirection: both-random',
                 'card-type: vocab\ntarget: [clock]{tl}\nmeaning: a thing that tells the time\ndirection: forward']) {
  const r = await (await send('POST', `/exercises/api/decks/${deck.path}/items`,
                              JSON.stringify({markdown: `:::exercise flashcard\n${c}\n:::`}))).json();
  if (!r.ok) throw Error(JSON.stringify(r));
  itemIds.push(r.item.id);
}
const study = (await (await send('POST', '/exercises/api/decks', JSON.stringify({name: 'Study deck', lang: 'en'}))).json()).deck;
{
  const r = await (await send('POST', `/exercises/api/decks/${study.path}/items`, JSON.stringify({
    markdown: ':::exercise flashcard\ncard-type: vocab\ntarget: [wound]{tl}\nmeaning: turned a key\ndirection: both-random\n:::'}))).json();
  if (!r.ok) throw Error(JSON.stringify(r));
}
// the exports are made once, as files: no server is needed to open them
const exportEn = `${TMP}/export-en.html`, exportDeck = `${TMP}/export-deck.html`;
await Deno.writeFile(exportEn, new Uint8Array(await (await send('GET', `/download/${ids.en}/html`)).arrayBuffer()));
const rd = await send('POST', `/exercises/api/decks/${deck.path}/export-html`, JSON.stringify({ids: itemIds}));
if (rd.status !== 200) throw Error('the deck export answered ' + rd.status);
await Deno.writeFile(exportDeck, new Uint8Array(await rd.arrayBuffer()));

const browser = await chromium.launch({executablePath: Deno.env.get('CHROME_BIN') || undefined, headless: true});
const forced = v => `Math.random = () => ${v};`;
const sides = card => card.evaluate(c => {
  const f = c.querySelector(':scope > .ex-card-front'), b = c.querySelector(':scope > .ex-card-back');
  return {cls: c.className, hint: c.querySelector('small').textContent, front: f.textContent, frontHidden: f.hidden,
          back: b.textContent, backHidden: b.hidden, order: [...c.children].map(x => x.className)};
});
const shot = (page, name, opts = {}) => SHOTS ? page.screenshot({path: `${SHOTS}/${name}.png`, ...opts}) : null;
try {
  /* ---------------- a) a document page, both outcomes forced ---------------- */
  console.log('a) a document page, Math.random forced');
  for (const [value, backFirst] of [[0.9, true], [0.1, false], [0.5, true], [0.4999, false]]) {
    const ctx = await browser.newContext({viewport: {width: 1280, height: 900}});
    await ctx.addInitScript(forced(value));
    const page = await ctx.newPage();
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    await page.goto(`${B}/doc/${ids.en}`);
    await page.waitForSelector('#sheet .ex-flashcard');
    const cards = page.locator('#sheet .ex-flashcard');
    const rnd = cards.nth(1);
    const shown = backFirst ? 'turned a key' : 'wound', other = backFirst ? 'wound' : 'turned a key';
    let t = await sides(rnd);
    assert(t.front === shown && !t.frontHidden && t.back === other && t.backHidden
           && t.order[0] === 'ex-card-front' && t.order[1] === 'ex-card-back',
           `random ${value}: the both-random card shows ${shown} first and .ex-card-front is that side`);
    t = await sides(cards.nth(0));
    assert(t.front === 'clock' && t.backHidden, `random ${value}: both-repeat is front first`);
    t = await sides(cards.nth(2));
    assert(t.front === 'a way in' && t.backHidden, `random ${value}: reverse is back first`);
    t = await sides(cards.nth(3));
    assert(t.front === 'gate' && t.backHidden, `random ${value}: forward is front first`);
    await rnd.click();
    t = await sides(rnd);
    assert(t.cls.includes('flipped') && t.front === shown && t.frontHidden && t.back === other && !t.backHidden
           && t.hint === 'tap to see front', 'a click turns it to the other side');
    await rnd.click();
    t = await sides(rnd);
    assert(!t.cls.includes('flipped') && !t.frontHidden && t.backHidden && t.hint === 'tap to reveal', 'and back');
    const note = page.locator('#sheet .ex-card-note');
    assert(await note.count() === 1 && (await note.textContent()) === NOTE, 'one note, in the owner\'s words');
    await note.click();
    assert(!(await cards.nth(0).evaluate(c => c.classList.contains('flipped'))), 'a click on the note does not turn the card');
    const g = await page.evaluate(() => {
      const n = document.querySelector('.ex-card-note'), c = n.previousElementSibling, e = n.closest('.exercise');
      const N = n.getBoundingClientRect(), C = c.getBoundingClientRect(), E = e.getBoundingClientRect();
      return {gap: N.top - C.bottom, inside: N.bottom <= E.bottom, centred: Math.abs((N.left + N.right) / 2 - (C.left + C.right) / 2) < 3,
              card: c.classList.contains('ex-flashcard'), inCard: c.contains(n)};
    });
    assert(g.card && !g.inCard && g.gap >= 0 && g.gap < 24 && g.inside && g.centred,
           'the note is under the card, outside its box, centred: ' + JSON.stringify(g));
    await page.locator('#sheet .exercise:has(.ex-flashcard)').nth(1).locator('.ex-card-zoom').click();
    await page.waitForSelector('.ex-zoom-stage .ex-flashcard');
    await sleep(200);
    const z = await page.locator('.ex-zoom-stage .ex-flashcard').evaluate(c => ({
      front: c.querySelector(':scope > .ex-card-front').textContent, hidden: c.querySelector(':scope > .ex-card-front').hidden,
      note: !!c.querySelector('.ex-card-note')}));
    assert(z.front === shown && !z.hidden && !z.note, 'Enlarge shows the same side first, and no note on the card');
    await page.keyboard.press('Escape');
    assert(errors.length === 0, 'no page errors ' + errors.join('|'));
    if (value === 0.9) await shot(page, 'doc-en', {fullPage: true});
    await ctx.close();
  }

  /* ---------------- b) the real draw ---------------- */
  console.log('b) the real draw');
  {
    const ctx = await browser.newContext();
    const page = await ctx.newPage();
    const N = 60;
    let back = 0;
    for (let i = 0; i < N; i++) {
      await page.goto(`${B}/doc/${ids.en}`, {waitUntil: 'domcontentloaded'});
      await page.waitForSelector('#sheet .ex-flashcard');
      if ((await sides(page.locator('#sheet .ex-flashcard').nth(1))).front === 'turned a key') back++;
    }
    assert(back > N * 0.25 && back < N * 0.75, `real page loads draw both sides (${back} of ${N} back first)`);
    const many = await page.evaluate(async () => {
      const raw = new DOMParser().parseFromString(await (await fetch(location.href)).text(), 'text/html');
      const html = raw.querySelectorAll('.exercise')[1].outerHTML;
      let backFirst = 0, redrawn = 0;
      const N = 4000;
      for (let i = 0; i < N; i++) {
        const host = document.createElement('div');
        host.innerHTML = html;
        bindExercises(host);
        const c = host.querySelector('.ex-flashcard');
        const first = c.querySelector(':scope > .ex-card-front').textContent;
        if (first === 'turned a key') backFirst++;
        bindExercises(host);
        if (c.querySelector(':scope > .ex-card-front').textContent !== first) redrawn++;
      }
      return {backFirst, N, redrawn};
    });
    assert(Math.abs(many.backFirst / many.N - 0.5) < 0.04 && many.redrawn === 0,
           `${many.N} binds: ${many.backFirst} back first, and a second bind never draws again (${many.redrawn})`);
    await ctx.close();
  }

  /* ---------------- c) right to left, and CJK ---------------- */
  console.log('c) Persian, Japanese, Chinese');
  for (const [k, back, front] of [['fa', 'a book', 'کتاب'], ['ja', 'cat', '猫'], ['zh', 'thanks', '谢谢']]) {
    for (const [v, want] of [[0.9, back], [0.1, front]]) {
      const ctx = await browser.newContext({viewport: {width: 1280, height: 700}});
      await ctx.addInitScript(forced(v));
      const page = await ctx.newPage();
      await page.goto(`${B}/doc/${ids[k]}`);
      await page.waitForSelector('#sheet .ex-flashcard');
      await page.evaluate(() => document.fonts.ready);
      const c = page.locator('#sheet .ex-flashcard').first();
      const t = await sides(c);
      assert(t.front.startsWith(want) && !t.frontHidden && t.backHidden, `${k}, random ${v}: ${want} first`);
      await c.click();
      const t2 = await sides(c);
      assert(t2.cls.includes('flipped') && !t2.backHidden && t2.frontHidden, `${k} turns`);
      if (v === 0.9) await shot(page, `random-${k}`, {clip: {x: 280, y: 200, width: 720, height: 420}});
      await ctx.close();
    }
  }
  {
    const ctx = await browser.newContext({viewport: {width: 1280, height: 900}});
    const page = await ctx.newPage();
    await page.goto(`${B}/doc/${ids.fa}`);
    await page.waitForSelector('#sheet .ex-card-note');
    const rtl = await page.evaluate(() => {
      const n = document.querySelector('.ex-card-note');
      return {dir: n.getAttribute('dir'), css: getComputedStyle(n).direction, text: n.textContent};
    });
    assert(rtl.dir === 'ltr' && rtl.css === 'ltr' && rtl.text === NOTE, 'under a Persian card the note is still its own left-to-right line');
    await ctx.close();
  }

  /* ---------------- d) the editor's preview and the form ---------------- */
  console.log('d) the editor and the exercise form');
  {
    const ctx = await browser.newContext({viewport: {width: 1400, height: 900}});
    await ctx.addInitScript(forced(0.9));
    const page = await ctx.newPage();
    await page.goto(`${B}/doc/${ids.en}/edit`);
    await page.waitForSelector('#sheet .ex-flashcard');
    await sleep(500);
    const cards = page.locator('#sheet .ex-flashcard');
    const t1 = await sides(cards.nth(1));
    assert(t1.cls.includes('flipped') && t1.front === 'wound' && !t1.frontHidden && !t1.backHidden,
           'the preview shows both sides of a both-random card, front first, and draws nothing');
    assert((await sides(cards.nth(0))).cls.includes('flipped') && await page.locator('#sheet .ex-card-note').count() === 1,
           'and the note under a both-repeat card');
    await page.locator('#sheet .exercise').nth(1).locator('.ex-edit').click();
    await page.waitForSelector('.ex-form-modal');
    const select = page.locator('.ex-form-modal label:has(> span:text-is("Which side appears first")) select');
    const opts = await select.locator('option').evaluateAll(os => os.map(o => [o.value, o.textContent, o.selected]));
    assert(JSON.stringify(opts) === JSON.stringify([['forward', 'Front', false], ['reverse', 'Back', false],
                                                    ['both-random', 'Both (random)', true], ['both-repeat', 'Both (repeat)', false]]),
           'the form offers Front, Back, Both (random) and Both (repeat), on the card\'s own: ' + JSON.stringify(opts));
    await select.scrollIntoViewIfNeeded();
    await shot(page, 'form-direction');
    await select.selectOption('both-repeat');
    await sleep(700);
    const pv = await page.evaluate(() => ({note: !!document.querySelector('.ex-form-preview .ex-card-note'),
                                           flipped: !!document.querySelector('.ex-form-preview .ex-flashcard.flipped')}));
    assert(pv.note && pv.flipped, 'the form\'s own preview shows the note once Both (repeat) is chosen');
    await page.click('.ex-form-modal [data-x="save"]');
    await page.waitForSelector('.ex-form-modal', {state: 'detached'});
    const src = await page.evaluate(() => document.querySelector('#src').value);
    assert(src.includes('meaning: turned a key\ndirection: both-repeat'), 'the source now says direction: both-repeat');
    const narrow = await page.evaluate(() => {
      const def = EXERCISE_DEFINITIONS.find(d => d.subtype === 'flashcard' && d.cardType === 'vocab');
      const pick = () => [...document.querySelectorAll('.ex-form-modal label')]
        .find(l => l.textContent.startsWith('Which side appears first')).querySelector('select');
      const offered = () => [...pick().options].map(o => o.value);
      const out = {};
      for (const [name, directions] of [['all', undefined], ['deck', ['forward', 'reverse', 'both-random']]]) {
        openExerciseForm({model: newExerciseModel(def), def, mode: 'add', onSave: () => {}, directions});
        out[name] = offered();
        document.querySelector('.ex-form-modal [data-x="cancel"]').click();
      }
      const m = newExerciseModel(def); m.fields.direction = 'both-repeat';
      openExerciseForm({model: m, def, mode: 'edit', onSave: () => {}, directions: ['forward', 'reverse', 'both-random']});
      out.kept = [pick().value, offered()];
      document.querySelector('.ex-form-modal [data-x="cancel"]').click();
      const bad = newExerciseModel(def); bad.fields.direction = 'both';
      openExerciseForm({model: bad, def, mode: 'edit', onSave: () => {}});
      out.bad = [bad.fields.direction, offered()];
      return out;
    });
    assert(JSON.stringify(narrow.all) === '["forward","reverse","both-random","both-repeat"]'
           && JSON.stringify(narrow.deck) === '["forward","reverse","both-random"]'
           && narrow.kept[0] === 'both-repeat' && narrow.kept[1].length === 4
           && narrow.bad[0] === 'forward' && narrow.bad[1].length === 4,
           'opts.directions narrows the form, keeps a value the card has, and an unknown value reads as Front: ' + JSON.stringify(narrow));
    await ctx.close();
  }

  /* ---------------- e) a deck's cram page ---------------- */
  console.log('e) a deck\'s cram page');
  for (const [v, want] of [[0.9, 'turned a key'], [0.1, 'wound']]) {
    const ctx = await browser.newContext({viewport: {width: 1100, height: 800}});
    await ctx.addInitScript(forced(v));
    const page = await ctx.newPage();
    await page.goto(`${B}/exercises/deck/${deck.path}/cram#all`);
    await page.waitForSelector('#cram-stage .ex-flashcard', {timeout: 8000});
    let seen = null;
    for (let i = 0; i < 2 && !seen; i++) {
      const c = page.locator('#cram-stage .ex-flashcard');
      const t = await sides(c);
      if (['wound', 'turned a key'].includes(t.front)) seen = t;
      else { await page.click('#cram-show'); await page.click('#cram-correct'); }
    }
    assert(seen && seen.front === want && !seen.frontHidden, `cram, random ${v}: ${want} first`);
    await page.click('#cram-show');
    const t2 = await sides(page.locator('#cram-stage .ex-flashcard'));
    assert(t2.cls.includes('flipped') && !t2.backHidden, 'Show answer turns it');
    if (v === 0.9) await shot(page, 'cram');
    await ctx.close();
  }

  for (const [v, want] of [[0.9, 'turned a key'], [0.1, 'wound']]) {
    const ctx = await browser.newContext({viewport: {width: 1100, height: 800}});
    await ctx.addInitScript(forced(v));
    const page = await ctx.newPage();
    await page.goto(`${B}/exercises/deck/${study.path}/study`);
    await page.waitForSelector('#study-stage .ex-flashcard', {timeout: 8000});
    const t = await sides(page.locator('#study-stage .ex-flashcard'));
    assert(t.front === want && !t.frontHidden && t.backHidden, `the study page, random ${v}: ${want} first`);
    await page.click('#btn-show');
    const t2 = await sides(page.locator('#study-stage .ex-flashcard'));
    assert(t2.cls.includes('flipped') && !t2.backHidden, 'Show answer turns it');
    await ctx.close();
  }

  /* ---------------- f) real exports, opened as files ---------------- */
  console.log('f) exported pages');
  {
    const html = await Deno.readTextFile(exportEn);
    assert(html.includes('class="ex-card-note"') && html.includes('data-first="random"') && html.includes('function drawFirstSide'),
           'the exported page carries the note, the marked card, and the draw in its own script');
    for (const [v, backFirst] of [[0.9, true], [0.1, false]]) {
      const ctx = await browser.newContext({viewport: {width: 1100, height: 900}});
      await ctx.addInitScript(forced(v));
      const page = await ctx.newPage();
      const errors = [], requests = [];
      page.on('pageerror', e => errors.push(e.message));
      page.on('request', r => { if (!/^(file|data|blob):/.test(r.url())) requests.push(r.url()); });
      await page.goto(`file://${exportEn}`);
      await page.waitForSelector('.ex-flashcard');
      const cards = page.locator('.ex-flashcard');
      const t = await sides(cards.nth(1));
      assert((t.front === 'turned a key') === backFirst && !t.frontHidden && t.backHidden,
             `export, random ${v}: ${backFirst ? 'the back' : 'the front'} first`);
      assert((await sides(cards.nth(0))).front === 'clock' && (await sides(cards.nth(2))).front === 'a way in',
             'export: both-repeat front first, reverse back first');
      assert(await page.locator('.ex-card-note').count() === 1 && (await page.locator('.ex-card-note').textContent()) === NOTE, 'export: the note');
      await page.locator('.ex-card-note').click();
      assert(!(await cards.nth(0).evaluate(c => c.classList.contains('flipped'))), 'export: the note turns nothing');
      await cards.nth(1).click();
      const t2 = await sides(cards.nth(1));
      assert(t2.cls.includes('flipped') && t2.frontHidden && !t2.backHidden, 'export: the card turns');
      assert(errors.length === 0 && requests.length === 0, `export: no errors and no network (${errors} ${requests})`);
      if (v === 0.9) await shot(page, 'export-en', {fullPage: true});
      await ctx.close();
    }
    const ctx = await browser.newContext();
    const page = await ctx.newPage();
    const N = 60;
    let back = 0;
    for (let i = 0; i < N; i++) {
      await page.goto(`file://${exportEn}`);
      await page.waitForSelector('.ex-flashcard');
      if ((await sides(page.locator('.ex-flashcard').nth(1))).front === 'turned a key') back++;
    }
    assert(back > N * 0.25 && back < N * 0.75, `the exported file draws both sides over real loads (${back} of ${N} back first)`);
    await ctx.close();
    for (const [v, want] of [[0.9, 'turned a key'], [0.1, 'wound']]) {
      const ctx2 = await browser.newContext({viewport: {width: 1100, height: 800}});
      await ctx2.addInitScript(forced(v));
      const p2 = await ctx2.newPage();
      const errors = [];
      p2.on('pageerror', e => errors.push(e.message));
      await p2.goto(`file://${exportDeck}`);
      await p2.waitForSelector('.ex-flashcard', {timeout: 8000});
      let seen = null;
      for (let i = 0; i < 2 && !seen; i++) {
        const t = await sides(p2.locator('.ex-flashcard'));
        if (['wound', 'turned a key'].includes(t.front)) seen = t;
        else { await p2.click('#cram-show'); await p2.click('#cram-correct'); }
      }
      assert(seen && seen.front === want && !seen.frontHidden && errors.length === 0, `the exported deck, random ${v}: ${want} first`);
      await ctx2.close();
    }
  }
  console.log(`flashcard_direction: ${passed} checks passed`);
} finally {
  await browser.close();
  proc.kill('SIGTERM');
  await Deno.remove(TMP, {recursive: true}).catch(() => {});
}

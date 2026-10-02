// SPDX-License-Identifier: GPL-3.0-or-later
// Browser test of where a vocab or opposites flashcard draws its `context`,
// `notes` and `source`: on the side the flip REVEALS, unless `<field>-side:
// question` puts one on the side shown first (mdparser.card_extras; the table
// of it is tests/test_flashcard_sides.py).  Against the REAL routes on a
// temporary library and exercises store (tests/decks_harness.py, studio
// mode), and a REAL exported page and deck opened as files:
//   a) a document page with Math.random forced to each outcome: a both-random
//      card's extras are on the revealed side whichever side the draw shows
//      first, `question` ones on the side shown first, each in the order
//      context, notes, source after the side's own fields; its recordings stay
//      with their sides; a reverse card opens on its meaning alone
//   b) the real draw: real page loads, and thousands of binds, never leave an
//      answer's extra on the side shown first nor a question's on the other
//   c) Enlarge on a drawn card, turned and turned back
//   d) the editor's preview (both sides, nothing drawn) and the exercise form:
//      a box under each of Example or context, Notes and Source's Text
//      appearance on a vocab card, two on an opposites card, none on a Jolly
//      card; ticking writes `<field>-side: question` and nothing is written
//      unticked; the form's own preview moves the field; a value the form does
//      not know is kept as written and the save is refused with a sentence;
//      the box at 1280 px and at 390 px in the light, dark and sepia themes
//   e) a deck's study and cram pages, and a both-repeat card put into a deck
//   f) the document and the decks exported as one file each, opened as files
//   CHROME_BIN=... PARSEH_PYTHON=python3 deno run --allow-all tests/flashcard_sides.mjs
//   SHOTS=<dir> saves screenshots
import {chromium} from 'npm:playwright-core@1.52.0';

const root = await Deno.realPath(new URL('..', import.meta.url));
const python = Deno.env.get('PARSEH_PYTHON') || 'python3';
const SHOTS = Deno.env.get('SHOTS') || '';
const TMP = await Deno.makeTempDir({prefix: 'parseh-flashcard-sides-'});
let passed = 0;
const assert = (v, m) => { if (!v) throw Error('FAIL: ' + m); passed++; console.log('  ok', m); };
const sleep = ms => new Promise(r => setTimeout(r, ms));
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

// every card says what it is in its fields: the word, the meaning, and the three extras
const doc = (target, cards) => `---\ntitle: Sides ${target}\ntarget: ${target}\nlang: en\n---\n\n`
  + cards.map(c => `:::exercise flashcard\n${c}\n:::\n`).join('\n');
const EN = {
  random: 'card-type: vocab\ntarget: [wound]{tl}\nreading: waund\nmeaning: turned a key\ncontext: she wound the clock\nnotes: past of wind\nsource: Oxford\ndirection: both-random',
  mixed: 'card-type: vocab\ntarget: [coil]{tl}\nmeaning: a spiral\ncontext: a coil of rope\nnotes: also a verb\nsource: Collins\nnotes-side: question\ndirection: both-random',
  reverse: 'card-type: vocab\ntarget: [door]{tl}\nmeaning: a way in\ncontext: open the door\nnotes: a noun\nsource: Longman\ndirection: reverse',
  asked: 'card-type: vocab\ntarget: [gate]{tl}\nmeaning: a way through\ncontext: shut the gate\nnotes: a noun too\nsource: Cambridge\ndirection: reverse\ncontext-side: question\nnotes-side: question\nsource-side: question',
  forward: 'card-type: vocab\ntarget: [wall]{tl}\nmeaning: a barrier\ncontext: a high wall\nnotes: of stone\nsource: Merriam\ndirection: forward',
  opposites: 'card-type: opposites\ntarget: [hot]{tl}\nopposite: [cold]{tl}\nnotes: of weather\nsource: Roget\ndirection: both-random',
  sound: 'card-type: vocab\ntarget: [bell]{tl}\nmeaning: a ringing thing\nnotes: it rings\nfront-audio: audio/bell-word.mp3\nback-audio: audio/bell-meaning.mp3\ndirection: both-random',
  jolly: 'card-type: jolly\nfront-primary: front\nback-primary: back\nback-secondary: more\ndirection: both-random',
};
const ORDER = ['random', 'mixed', 'reverse', 'asked', 'forward', 'opposites', 'sound', 'jolly'];
const DOCS = {
  en: doc('en', ORDER.map(k => EN[k])),
  fa: doc('fa', [
    'card-type: vocab\ntarget: [کتاب]{tl}\ntransliteration: ketâb\nmeaning: a book\ncontext: یک کتاب = *a book*\nnotes: plural کتاب‌ها\nsource: Dehkhoda\ndirection: reverse',
    'card-type: vocab\ntarget: [سلام]{tl}\nmeaning: hello\ncontext: سلام دوست من\nnotes: a greeting\nsource: Dehkhoda\ndirection: both-random']),
  ja: doc('ja', ['card-type: vocab\ntarget: [猫]{tl}\nreading: ねこ\nmeaning: cat\ncontext: 猫が好きです。\nnotes: a pet\nsource: Jisho\ndirection: reverse']),
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
const mkdeck = async name => (await (await send('POST', '/exercises/api/decks', JSON.stringify({name, lang: 'en'}))).json()).deck;
const addTo = async (deck, card) => {
  const r = await (await send('POST', `/exercises/api/decks/${deck.path}/items`,
                              JSON.stringify({markdown: `:::exercise flashcard\n${card}\n:::`}))).json();
  if (!r.ok) throw Error(JSON.stringify(r));
  return r;
};
// a deck of each: studied one card at a time, and a both-repeat card that becomes two
const randomDeck = await mkdeck('Random deck');
await addTo(randomDeck, EN.random);
await addTo(randomDeck, EN.mixed);
const reverseDeck = await mkdeck('Reverse deck');
await addTo(reverseDeck, EN.reverse);
const repeatDeck = await mkdeck('Repeat deck');
const repeated = await addTo(repeatDeck, EN.random.replace('both-random', 'both-repeat'));
if (repeated.items.length !== 2) throw Error('a both-repeat card is two cards in a deck');
const exportDoc = `${TMP}/export-en.html`, exportDeck = `${TMP}/export-deck.html`;
await Deno.writeFile(exportDoc, new Uint8Array(await (await send('GET', `/download/${ids.en}/html`)).arrayBuffer()));
{
  const items = (await (await send('GET', `/exercises/api/decks/${randomDeck.path}`)).json()).items.map(i => i.id);
  const rd = await send('POST', `/exercises/api/decks/${randomDeck.path}/export-html`, JSON.stringify({ids: items}));
  if (rd.status !== 200) throw Error('the deck export answered ' + rd.status);
  await Deno.writeFile(exportDeck, new Uint8Array(await rd.arrayBuffer()));
}

const browser = await chromium.launch({executablePath: Deno.env.get('CHROME_BIN') || undefined, headless: true});
const forced = v => `Math.random = () => ${v};`;
const shot = (page, name, opts = {}) => SHOTS ? page.screenshot({path: `${SHOTS}/${name}.png`, ...opts}) : null;
// a card as it stands: what each side draws, in order, and which of its fields are marked extras
const halves = card => card.evaluate(c => {
  const side = el => ({fields: [...el.children].filter(x => x.classList.contains('ex-card-field'))
                         .map(x => x.textContent.trim()),
                       marked: [...el.children].filter(x => x.hasAttribute('data-extra')).map(x => x.dataset.extra),
                       audio: [...el.querySelectorAll('audio')].map(a => a.getAttribute('src').split('/').pop().replace(/#.*/, '')),
                       hidden: el.hidden, cls: el.className});
  const f = c.querySelector(':scope > .ex-card-front'), b = c.querySelector(':scope > .ex-card-back');
  return {first: side(f), second: side(b), order: [...c.children].map(x => x.className), flipped: c.classList.contains('flipped')};
});
// a cram or an exported deck of the two random cards shows either first: the one on screen is judged by its own rule
const randomDeckCard = (h, meaningFirst) => {
  const all = [...h.first.fields, ...h.second.fields];
  if (all.includes('wound'))
    return (h.first.fields[0] === 'turned a key') === meaningFirst && same(h.second.fields.slice(-3), ['she wound the clock', 'past of wind', 'Oxford']);
  return all.includes('coil') && (h.first.fields[0] === 'a spiral') === meaningFirst && h.first.fields.slice(-1)[0] === 'also a verb'
    && same(h.second.fields.slice(-2), ['a coil of rope', 'Collins']);
};

try {
  /* ---------------- a) a document page, both outcomes forced ---------------- */
  console.log('a) a document page, Math.random forced');
  const idx = Object.fromEntries(ORDER.map((k, i) => [k, i]));
  for (const [value, meaningFirst] of [[0.1, false], [0.9, true]]) {
    const ctx = await browser.newContext({viewport: {width: 1280, height: 1000}});
    await ctx.addInitScript(forced(value));
    const page = await ctx.newPage();
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    await page.goto(`${B}/doc/${ids.en}`);
    await page.waitForSelector('#sheet .ex-flashcard');
    const cards = page.locator('#sheet .ex-flashcard');
    const at = k => cards.nth(idx[k]);

    let h = await halves(at('random'));
    const word = ['wound', 'waund'], meaning = ['turned a key'];
    const extras = ['she wound the clock', 'past of wind', 'Oxford'];
    assert(same(h.first.fields, meaningFirst ? meaning : word) && same(h.second.fields, meaningFirst ? [...word, ...extras] : [...meaning, ...extras]),
           `random ${value}: the answer's extras are on the revealed side (${meaningFirst ? 'the meaning' : 'the word'} first): ${JSON.stringify(h)}`);
    assert(!h.first.hidden && h.second.hidden && same(h.order.slice(0, 2), ['ex-card-front', 'ex-card-back'])
           && h.first.marked.length === 0 && same(h.second.marked, ['context', 'notes', 'source']),
           `random ${value}: .ex-card-front is the side shown, the marked fields are the revealed side's three`);

    h = await halves(at('mixed'));
    assert(same(h.first.fields, meaningFirst ? ['a spiral', 'also a verb'] : ['coil', 'also a verb'])
           && same(h.second.fields, meaningFirst ? ['coil', 'a coil of rope', 'Collins'] : ['a spiral', 'a coil of rope', 'Collins']),
           `mixed ${value}: notes-side: question stays on the side shown first, the other two on the revealed one, in order: ${JSON.stringify(h)}`);
    assert(same(h.first.marked, ['notes']) && same(h.second.marked, ['context', 'source']), `mixed ${value}: each field is marked where it is`);

    h = await halves(at('opposites'));
    assert(same(h.first.fields, meaningFirst ? ['cold'] : ['hot']) && same(h.second.fields, meaningFirst ? ['hot', 'of weather', 'Roget'] : ['cold', 'of weather', 'Roget']),
           `opposites ${value}: notes and source on the revealed side`);

    h = await halves(at('sound'));
    assert(same(h.first.audio, [meaningFirst ? 'bell-meaning.mp3' : 'bell-word.mp3']) && same(h.second.audio, [meaningFirst ? 'bell-word.mp3' : 'bell-meaning.mp3'])
           && same(h.first.fields, meaningFirst ? ['a ringing thing'] : ['bell'])
           && same(h.second.fields, meaningFirst ? ['bell', 'it rings'] : ['a ringing thing', 'it rings']),
           `sound ${value}: each recording stays on the side that names it, the first side's is the one that plays first, the note is on the revealed side: ${JSON.stringify(h)}`);

    h = await halves(at('jolly'));
    assert(same(h.first.fields, meaningFirst ? ['back', 'more'] : ['front']) && same(h.first.marked.concat(h.second.marked), []),
           `jolly ${value}: swapped as ever, and nothing marked`);

    // the cards that are not drawn are what they say
    h = await halves(at('reverse'));
    assert(same(h.first.fields, ['a way in']) && same(h.second.fields, ['door', 'open the door', 'a noun', 'Longman']) && h.first.marked.length + h.second.marked.length === 0,
           `reverse ${value}: opens on its meaning alone, the example, notes and source come with the word`);
    h = await halves(at('asked'));
    assert(same(h.first.fields, ['a way through', 'shut the gate', 'a noun too', 'Cambridge']) && same(h.second.fields, ['gate']),
           `asked ${value}: three question sides put a reverse card as it was`);
    h = await halves(at('forward'));
    assert(same(h.first.fields, ['wall']) && same(h.second.fields, ['a barrier', 'a high wall', 'of stone', 'Merriam']),
           `forward ${value}: as it always was`);

    // turning: the other side, with what it holds
    await at('random').click();
    h = await halves(at('random'));
    assert(h.flipped && h.first.hidden && !h.second.hidden && same(h.second.fields, meaningFirst ? [...word, ...extras] : [...meaning, ...extras]),
           `random ${value}: a click turns it to the revealed side, extras with it`);
    await at('random').click();
    h = await halves(at('random'));
    assert(!h.flipped && !h.first.hidden && h.second.hidden, `random ${value}: and back`);
    assert(errors.length === 0, 'no page errors ' + errors.join('|'));
    if (value === 0.9) { await at('reverse').scrollIntoViewIfNeeded(); await shot(page, 'doc-en-1280', {fullPage: true}); }
    await ctx.close();
  }

  /* ---------------- a2) the cards as a person looks at them ---------------- */
  console.log('a2) the cards at 1280 and 390 px, light and dark, asked and turned');
  const laidOut = page => page.evaluate(() => {
    const bad = [];
    document.querySelectorAll('#sheet .ex-flashcard').forEach((c, i) => {
      c.scrollIntoView({block: 'center'});       // elementFromPoint sees only what is in the window
      const cr = c.getBoundingClientRect();
      if (cr.right > innerWidth + 1 || cr.left < -1) bad.push(`card ${i} is outside the window`);
      c.querySelectorAll('.ex-card-field').forEach(f => {
        if (f.closest('[hidden]')) return;
        const r = f.getBoundingClientRect();
        if (!r.width || !r.height) bad.push(`card ${i}: ${f.textContent.trim()} has no box`);
        if (r.left < cr.left - 1 || r.right > cr.right + 1 || r.top < cr.top - 1 || r.bottom > cr.bottom + 1)
          bad.push(`card ${i}: ${f.textContent.trim()} sticks out of its card`);
        // and nothing covers it: what is at its centre is the field itself or something in it
        const at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
        if (!at || !f.contains(at)) bad.push(`card ${i}: ${f.textContent.trim()} is covered by ${at && at.className}`);
      });
    });
    return {bad, scroll: document.documentElement.scrollWidth <= innerWidth + 1};
  });
  for (const theme of ['light', 'dark']) {
    for (const [w, h] of [[1280, 900], [390, 844]]) {
      for (const which of ['en', 'fa', 'ja']) {
        const ctx = await browser.newContext({viewport: {width: w, height: h}});
        await ctx.addInitScript(forced(0.9));
        await ctx.addInitScript(t => { try { localStorage.setItem('parseh_theme', t); } catch (e) { /* none */ } }, theme);
        const page = await ctx.newPage();
        const errors = [];
        page.on('pageerror', e => errors.push(e.message));
        await page.goto(`${B}/doc/${ids[which]}`);
        await page.waitForSelector('#sheet .ex-flashcard');
        await page.evaluate(() => document.fonts.ready);
        // the cards are asked: look at each card where it stands, then turn each and look again
        const cards = page.locator('#sheet .ex-flashcard');
        const n = await cards.count();
        let out = await laidOut(page);
        const tag = `${which}-${theme}-${w}`;
        for (let i = 0; i < n; i++) await cards.nth(i).scrollIntoViewIfNeeded();
        await page.evaluate(() => scrollTo(0, 0));
        if (which === 'en' || w === 1280) await shot(page, `cards-${tag}-asked`, {fullPage: true});
        const askedOk = out.bad.length === 0 && out.scroll;
        for (let i = 0; i < n; i++) { await cards.nth(i).scrollIntoViewIfNeeded(); await cards.nth(i).click({position: {x: 8, y: 8}}); }
        await sleep(150);
        out = await laidOut(page);
        await page.evaluate(() => scrollTo(0, 0));
        if (which === 'en' || w === 1280) await shot(page, `cards-${tag}-turned`, {fullPage: true});
        assert(askedOk && out.bad.length === 0 && out.scroll && errors.length === 0,
               `${tag}: every field of ${n} cards, asked and turned, is inside its card and uncovered, and nothing scrolls sideways ${JSON.stringify(out.bad.slice(0, 3))} ${errors.join('|')}`);
        await ctx.close();
      }
    }
  }
  {
    // right to left and CJK: the extras keep the direction of their own text, and come after the word's own fields
    const ctx = await browser.newContext({viewport: {width: 1280, height: 900}});
    await ctx.addInitScript(forced(0.9));
    const page = await ctx.newPage();
    await page.goto(`${B}/doc/${ids.fa}`);
    await page.waitForSelector('#sheet .ex-flashcard');
    const fa = await halves(page.locator('#sheet .ex-flashcard').nth(0));
    assert(same(fa.first.fields, ['a book']) && fa.second.fields.length === 5 && fa.second.fields[0] === 'کتاب' && fa.second.fields[1] === 'ketâb'
           && fa.second.fields[2].startsWith('یک کتاب') && fa.second.fields[3].includes('plural') && fa.second.fields[4] === 'Dehkhoda',
           'Persian, turned round: the meaning opens the card, the word, its transliteration, the example, the notes and the source answer in order: ' + JSON.stringify(fa));
    const dirs = await page.locator('#sheet .ex-flashcard').nth(0).evaluate(c =>
      [...c.querySelectorAll(':scope > .ex-card-back .ex-card-field')].map(f => getComputedStyle(f).direction + '/' + getComputedStyle(f).textAlign));
    assert(dirs.every(d => d.endsWith('/center')), 'each field of the revealed side is centred, as every field of a card is: ' + JSON.stringify(dirs));
    const mixed = await halves(page.locator('#sheet .ex-flashcard').nth(1));
    assert(same(mixed.first.fields, ['hello']) && same(mixed.second.fields, ['سلام', 'سلام دوست من', 'a greeting', 'Dehkhoda']),
           'Persian, drawn meaning first: the word, then the example, the notes and the source: ' + JSON.stringify(mixed));
    const ja = await (async () => {
      await page.goto(`${B}/doc/${ids.ja}`);
      await page.waitForSelector('#sheet .ex-flashcard');
      return halves(page.locator('#sheet .ex-flashcard').first());
    })();
    assert(same(ja.first.fields, ['cat']) && same(ja.second.fields, ['猫', 'ねこ', '猫が好きです。', 'a pet', 'Jisho']),
           'Japanese, turned round: the meaning alone asks, the word, its reading, the example, the notes and the source answer: ' + JSON.stringify(ja));
    await ctx.close();
  }

  /* ---------------- a3) a word coloured in parts: the a0.4.3 dialect, where the renderer has it ---------------- */
  console.log('a3) a field holding a word coloured in parts moves whole');
  {
    const seg = await (await send('POST', '/api/docs', JSON.stringify({markdown: doc('en', [
      'card-type: vocab\ntarget: [stem]{tl}\nmeaning: a root\ncontext: [[un[break]{crimson}able]]\nnotes: coloured in parts\ndirection: both-random'])
      .replace('title: Sides en', 'title: A word in parts')}))).json();
    const probe = await (await fetch(`${B}/doc/${seg.meta.id}`)).text();
    if (!probe.includes('segmented-colour-run')) {
      console.log('  (waits for the a0.4.3 dialect: markdown/exlex/segcolour.py)');
    } else {
      for (const [v, meaningFirst] of [[0.1, false], [0.9, true]]) {
        const ctx = await browser.newContext({viewport: {width: 1100, height: 700}});
        await ctx.addInitScript(forced(v));
        const page = await ctx.newPage();
        await page.goto(`${B}/doc/${seg.meta.id}`);
        await page.waitForSelector('#sheet .ex-flashcard');
        const where = await page.locator('#sheet .ex-flashcard').evaluate(c => {
          const own = side => [...c.querySelector(':scope > ' + side).children].filter(x => x.classList.contains('ex-card-field'));
          const word = f => f.querySelector('.segmented-colour-run');
          const field = own('.ex-card-back').find(word);
          return {onFirst: own('.ex-card-front').some(word), onSecond: !!field, text: field && field.textContent,
                  pieces: field ? [...field.querySelectorAll('.seg-colour')].map(p => p.dataset.color + ':' + p.textContent) : [],
                  first: own('.ex-card-front').map(f => f.textContent.trim()), second: own('.ex-card-back').map(f => f.textContent.trim())};
        });
        assert(!where.onFirst && where.onSecond && where.text === 'unbreakable' && same(where.pieces, ['crimson:break'])
               && same(where.first, [meaningFirst ? 'a root' : 'stem']) && where.second.slice(-2).join('|') === 'unbreakable|coloured in parts',
               `random ${v}: the word coloured in parts is on the revealed side in one piece, its colour with it: ${JSON.stringify(where)}`);
        await ctx.close();
      }
    }
  }

  /* ---------------- a4) every combination of sides, drawn both ways ---------------- */
  console.log('a4) every combination of sides on a both-random card, drawn both ways');
  {
    // a card for each set of the extras said to be `question`, every field naming itself
    const combos = [];
    for (const kind of ['vocab', 'opposites']) {
      const keys = kind === 'vocab' ? ['context', 'notes', 'source'] : ['notes', 'source'];
      for (let mask = 0; mask < (1 << keys.length); mask++)
        combos.push({kind, keys, asked: keys.filter((k, i) => mask & (1 << i))});
    }
    const NAME = {target: 'WORD', reading: 'READING', transliteration: 'TRANSLIT', meaning: 'MEANING', opposite: 'OPPOSITE',
                  'opposite-reading': 'OREADING', 'opposite-transliteration': 'OTRANSLIT', context: 'CONTEXT', notes: 'NOTES', source: 'SOURCE'};
    const own = {vocab: ['target', 'reading', 'transliteration', 'meaning'],
                 opposites: ['target', 'reading', 'transliteration', 'opposite', 'opposite-reading', 'opposite-transliteration']};
    const wordSide = ['target', 'reading', 'transliteration'];
    const cards = combos.map(c => 'card-type: ' + c.kind + '\n' + own[c.kind].map(k => `${k}: ${NAME[k]}`).join('\n') + '\n'
      + c.keys.map(k => `${k}: ${NAME[k]}`).join('\n') + '\n' + c.asked.map(k => `${k}-side: question`).join('\n')
      + (c.asked.length ? '\n' : '') + 'direction: both-random');
    const all = await (await send('POST', '/api/docs', JSON.stringify({markdown: doc('en', cards)
      .replace('title: Sides en', 'title: Every combination')}))).json();
    for (const [v, meaningFirst] of [[0.1, false], [0.9, true]]) {
      const ctx = await browser.newContext({viewport: {width: 1100, height: 700}});
      await ctx.addInitScript(forced(v));
      const page = await ctx.newPage();
      await page.goto(`${B}/doc/${all.meta.id}`);
      await page.waitForSelector('#sheet .ex-flashcard');
      const got = await page.locator('#sheet .ex-flashcard').evaluateAll(cs => cs.map(c => {
        const f = side => [...c.querySelector(':scope > ' + side).children].filter(x => x.classList.contains('ex-card-field')).map(x => x.textContent.trim());
        return [f('.ex-card-front'), f('.ex-card-back')];
      }));
      let wrong = [];
      combos.forEach((c, i) => {
        const word = wordSide.map(k => NAME[k]);
        const meaning = own[c.kind].filter(k => !wordSide.includes(k)).map(k => NAME[k]);
        const asked = c.keys.filter(k => c.asked.includes(k)).map(k => NAME[k]);
        const answered = c.keys.filter(k => !c.asked.includes(k)).map(k => NAME[k]);
        // what the first side holds, and what the other: the side shown first has the question's extras, the other the answer's
        const want = meaningFirst ? [[...meaning, ...asked], [...word, ...answered]] : [[...word, ...asked], [...meaning, ...answered]];
        if (!same(got[i], want)) wrong.push(`${c.kind} ${c.asked.join('+') || 'none'}: ${JSON.stringify(got[i])} not ${JSON.stringify(want)}`);
      });
      assert(wrong.length === 0, `random ${v}: all ${combos.length} combinations of sides are drawn as the rule says: ${wrong.slice(0, 2).join(' | ')}`);
      await ctx.close();
    }
  }

  /* ---------------- b) the real draw ---------------- */
  console.log('b) the real draw');
  {
    const ctx = await browser.newContext();
    const page = await ctx.newPage();
    const N = 60;
    let meaningFirst = 0, wrong = 0;
    for (let i = 0; i < N; i++) {
      await page.goto(`${B}/doc/${ids.en}`, {waitUntil: 'domcontentloaded'});
      await page.waitForSelector('#sheet .ex-flashcard');
      const h = await halves(page.locator('#sheet .ex-flashcard').nth(idx.random));
      if (h.first.fields[0] === 'turned a key') meaningFirst++;
      if (h.first.fields.some(x => ['she wound the clock', 'past of wind', 'Oxford'].includes(x))) wrong++;
    }
    assert(meaningFirst > N * 0.25 && meaningFirst < N * 0.75 && wrong === 0,
           `${N} real page loads draw both sides (${meaningFirst} meaning first) and no extra was ever on the side shown first (${wrong})`);
    const many = await page.evaluate(async idxs => {
      const raw = new DOMParser().parseFromString(await (await fetch(location.href)).text(), 'text/html');
      const html = [...raw.querySelectorAll('.exercise')];
      const out = {};
      const N = 3000;
      const FIELD = c => [...c.children].filter(x => x.classList.contains('ex-card-field')).map(x => x.textContent.trim());
      for (const [name, i] of Object.entries(idxs)) {
        const stat = {meaningFirst: 0, extrasOnQuestion: 0, wrongOrder: 0, lost: 0, again: 0};
        for (let n = 0; n < N; n++) {
          const host = document.createElement('div');
          host.innerHTML = html[i].outerHTML;
          bindExercises(host);
          const c = host.querySelector('.ex-flashcard');
          const f = FIELD(c.querySelector(':scope > .ex-card-front')), b = FIELD(c.querySelector(':scope > .ex-card-back'));
          const meaningIsFirst = name === 'opposites' ? f[0] === 'cold' : f[0] === 'turned a key';
          if (meaningIsFirst) stat.meaningFirst++;
          // whichever is first, the answer's three are on the other side, in order
          const tail = name === 'opposites' ? ['of weather', 'Roget'] : ['she wound the clock', 'past of wind', 'Oxford'];
          if (f.some(x => tail.includes(x))) stat.extrasOnQuestion++;
          if (JSON.stringify(b.slice(-tail.length)) !== JSON.stringify(tail)) stat.wrongOrder++;
          if (f.length + b.length !== (name === 'opposites' ? 4 : 6)) stat.lost++;
          const before = JSON.stringify([f, b]);
          bindExercises(host);
          const g = host.querySelector('.ex-flashcard');
          if (JSON.stringify([FIELD(g.querySelector(':scope > .ex-card-front')), FIELD(g.querySelector(':scope > .ex-card-back'))]) !== before) stat.again++;
        }
        out[name] = {...stat, N};
      }
      return out;
    }, {random: idx.random, opposites: idx.opposites});
    for (const [name, s] of Object.entries(many))
      assert(Math.abs(s.meaningFirst / s.N - 0.5) < 0.04 && s.extrasOnQuestion === 0 && s.wrongOrder === 0 && s.lost === 0 && s.again === 0,
             `${name}: ${s.N} binds, ${s.meaningFirst} meaning first; never an answer's extra on the side shown first, always its own order, none lost or doubled, a second bind draws nothing again: ${JSON.stringify(s)}`);
    await ctx.close();
  }

  /* ---------------- c) Enlarge ---------------- */
  console.log('c) Enlarge');
  for (const [value, meaningFirst] of [[0.9, true], [0.1, false]]) {
    const ctx = await browser.newContext({viewport: {width: 1280, height: 900}});
    await ctx.addInitScript(forced(value));
    const page = await ctx.newPage();
    await page.goto(`${B}/doc/${ids.en}`);
    await page.waitForSelector('#sheet .ex-flashcard');
    for (const k of ['random', 'mixed', 'reverse']) {
      const onPage = await halves(page.locator('#sheet .ex-flashcard').nth(idx[k]));
      await page.locator('#sheet .exercise:has(.ex-flashcard)').nth(idx[k]).locator('.ex-card-zoom').click();
      await page.waitForSelector('.ex-zoom-stage .ex-flashcard');
      await sleep(250);
      const big = await halves(page.locator('.ex-zoom-stage .ex-flashcard'));
      assert(same(big.first.fields, onPage.first.fields) && same(big.second.fields, onPage.second.fields) && same(big.first.marked, onPage.first.marked),
             `${k}, random ${value}: the enlarged card shows the same side first with the same fields on each: ${JSON.stringify(big.first.fields)} | ${JSON.stringify(big.second.fields)}`);
      await page.locator('.ex-zoom-stage .ex-flashcard').click();
      const turned = await halves(page.locator('.ex-zoom-stage .ex-flashcard'));
      assert(turned.flipped && same(turned.second.fields, onPage.second.fields) && !turned.second.hidden && turned.first.hidden,
             `${k}, random ${value}: turned, the revealed side holds what it holds on the page`);
      await page.keyboard.press('Escape');
      await page.waitForSelector('.ex-zoom-stage', {state: 'detached'});
    }
    await ctx.close();
  }

  /* ---------------- d) the editor's preview, and the exercise form ---------------- */
  console.log('d) the editor and the exercise form');
  const FORM = '.ex-form-modal';
  const openForm = async (page, k) => {
    await page.locator('#sheet .exercise').nth(idx[k]).locator('.ex-edit').click();
    await page.waitForSelector(FORM);
  };
  const fieldBox = (page, label) => page.locator(`${FORM} label.ex-author-field:has(> span:text-is("${label}"))`);
  {
    const ctx = await browser.newContext({viewport: {width: 1400, height: 1000}});
    await ctx.addInitScript(forced(0.9));
    const page = await ctx.newPage();
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    await page.goto(`${B}/doc/${ids.en}/edit`);
    await page.waitForSelector('#sheet .ex-flashcard');
    await sleep(600);
    const cards = page.locator('#sheet .ex-flashcard');
    let h = await halves(cards.nth(idx.random));
    assert(h.flipped && same(h.first.fields, ['wound', 'waund']) && same(h.second.fields, ['turned a key', 'she wound the clock', 'past of wind', 'Oxford']),
           'the preview shows both sides of a both-random card as it is composed (front first) and draws nothing');
    h = await halves(cards.nth(idx.reverse));
    assert(h.flipped && same(h.first.fields, ['a way in']) && same(h.second.fields, ['door', 'open the door', 'a noun', 'Longman']),
           'the preview shows a reverse card meaning first, its extras with the word');

    // a vocabulary card: a box under each of the three
    await openForm(page, 'forward');
    const toggles = await page.evaluate(F => [...document.querySelectorAll(F + ' .ex-side-toggle')].map(t => ({
      field: t.closest('label.ex-author-field').querySelector(':scope > span').textContent, text: t.textContent.trim(),
      checked: t.querySelector('input').checked, open: t.closest('details').open, kind: t.querySelector('input').type})), FORM);
    assert(same(toggles.map(t => t.field), ['Example or context', 'Notes', 'Source']) && toggles.every(t => !t.checked && !t.open && t.kind === 'checkbox'
           && t.text === 'Show on the side shown first'),
           'a vocabulary card has the box under Example or context, Notes and Source, unticked, in a disclosure that is shut: ' + JSON.stringify(toggles));
    assert(await page.locator(`${FORM} label.ex-author-field:has(> span:text-is("Word or expression")) .ex-side-toggle`).count() === 0
           && await page.locator(`${FORM} label.ex-author-field:has(> span:text-is("Meaning")) .ex-side-toggle`).count() === 0
           && await page.locator(`${FORM} label.ex-author-field:has(> span:text-is("Reading")) .ex-side-toggle`).count() === 0,
           'and none under the word, the reading or the meaning');
    const shut = fieldBox(page, 'Notes').locator('.ex-side-toggle');
    assert(!(await shut.isVisible()), 'it is hidden together with the size and the colour, until Text appearance is opened');
    await fieldBox(page, 'Notes').locator('summary').click();
    assert(await shut.isVisible(), 'opened, it is there');
    const g = await page.evaluate(F => {
      const t = document.querySelector(F + ' details[open] .ex-side-toggle'), i = t.querySelector('input');
      const r = i.getBoundingClientRect(), m = document.querySelector(F).getBoundingClientRect(), tr = t.getBoundingClientRect();
      const top = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
      return {w: r.width, h: r.height, inside: r.left >= m.left && r.right <= m.right && r.top >= m.top && r.bottom <= m.bottom,
              hit: top === i, textHit: document.elementFromPoint(tr.left + 60, tr.top + tr.height / 2).closest('.ex-side-toggle') === t,
              help: t.parentElement.querySelector(':scope > small').textContent};
    }, FORM);
    assert(g.w < 24 && g.h < 24 && g.inside && g.hit && g.textHit && g.help.startsWith('Unticked, it goes on the other side'),
           'the box is a checkbox of its own size, inside the window and what a click on it or its words reaches: ' + JSON.stringify(g));
    await shot(page, 'form-vocab-1400', {});

    // ticking it moves the field in the form's own preview, and writes the line, and only when ticked
    const pv = () => page.evaluate(F => {
      const c = document.querySelector(F + ' .ex-form-preview .ex-flashcard');
      const f = x => [...c.querySelector(':scope > ' + x).children].filter(e => e.classList.contains('ex-card-field')).map(e => e.textContent.trim());
      return {first: f('.ex-card-front'), second: f('.ex-card-back')};
    }, FORM);
    // the preview is drawn a moment after a change: wait for what it should say, and say what it did
    const settled = async want => {
      let got = null;
      for (let i = 0; i < 40; i++) {
        got = await pv().catch(() => null);
        if (same(got, want)) break;
        await sleep(200);
      }
      return got;
    };
    const start = {first: ['wall'], second: ['a barrier', 'a high wall', 'of stone', 'Merriam']};
    assert(same(await settled(start), start), 'the form\'s preview starts as the card is');
    await shut.locator('input').check();
    const noted = {first: ['wall', 'of stone'], second: ['a barrier', 'a high wall', 'Merriam']};
    assert(same(await settled(noted), noted), 'ticking Notes moves it in the form\'s preview to the side shown first, after the word');
    await fieldBox(page, 'Source').locator('summary').click();
    // a click on its words ticks it as well as a click on the box, and so does the keyboard
    const words = fieldBox(page, 'Source').locator('.ex-side-toggle');
    await words.click({position: {x: 90, y: 8}});
    assert(await words.locator('input').isChecked(), 'a click on the words of the box ticks it');
    await words.click({position: {x: 90, y: 8}});
    assert(!(await words.locator('input').isChecked()), 'and the next unticks it');
    await words.locator('input').focus();
    await page.keyboard.press('Space');
    assert(await words.locator('input').isChecked(), 'Space on the focused box ticks it');
    const sourced = {first: ['wall', 'of stone', 'Merriam'], second: ['a barrier', 'a high wall']};
    assert(same(await settled(sourced), sourced), 'and Source after it');
    await page.click(`${FORM} [data-x="save"]`);
    await page.waitForSelector(FORM, {state: 'detached'});
    let src = await page.evaluate(() => document.querySelector('#src').value);
    const saved = src.slice(src.indexOf('target: [wall]{tl}'), src.indexOf('target: [wall]{tl}') + 260);
    assert(/\nnotes-side: question\n/.test(saved) && /\nsource-side: question\n/.test(saved) && !/context-side/.test(saved),
           'saved, the source says notes-side: question and source-side: question, and nothing of the context: ' + JSON.stringify(saved));
    // and unticked it is written no more
    await sleep(700);
    await openForm(page, 'forward');
    const boxes = await page.evaluate(F => [...document.querySelectorAll(F + ' .ex-side-toggle input')].map(i => i.checked), FORM);
    assert(same(boxes, [false, true, true]), 'reopened, the form shows what the card says: ' + JSON.stringify(boxes));
    await fieldBox(page, 'Notes').locator('summary').click();
    await fieldBox(page, 'Source').locator('summary').click();
    await fieldBox(page, 'Notes').locator('.ex-side-toggle input').uncheck();
    await fieldBox(page, 'Source').locator('.ex-side-toggle input').uncheck();
    await page.click(`${FORM} [data-x="save"]`);
    await page.waitForSelector(FORM, {state: 'detached'});
    src = await page.evaluate(() => document.querySelector('#src').value);
    assert(!/-side/.test(src.slice(src.indexOf('target: [wall]{tl}'), src.indexOf('target: [wall]{tl}') + 260)),
           'unticked again, no `-side` line is left in the source');
    await sleep(900);

    // `answer` said out is the default said out: the form reads it as unticked and writes nothing
    const rt = await page.evaluate(() => {
      const model = parseExerciseSource(':::exercise flashcard\ncard-type: vocab\ntarget: [x]{tl}\nmeaning: y\nnotes: n\nnotes-side: answer\ncontext: c\ncontext-side: banana\nsource: s\nsource-side: Question\n:::');
      const def = definitionFor(model);
      let refused = '';
      try { validateExercise(model, def); } catch (e) { refused = e.message; }
      return {fields: model.fields, out: exerciseSource(model, def), refused};
    });
    assert(!/notes-side/.test(rt.out) && /\ncontext-side: banana\n/.test(rt.out) && /\nsource-side: Question\n/.test(rt.out),
           'the model keeps a value it does not know as written (banana, Question), and drops `answer` as the default: ' + JSON.stringify(rt.out));
    assert(rt.refused === 'The side of the context must be answer or question: tick or untick its box under Text appearance',
           'and refuses to save it, in a sentence naming the field: ' + rt.refused);

    // an opposites card has two, a Jolly card none
    await openForm(page, 'opposites');
    assert(same(await page.evaluate(F => [...document.querySelectorAll(F + ' .ex-side-toggle')].map(t => t.closest('label.ex-author-field').querySelector(':scope > span').textContent), FORM),
                ['Notes', 'Source']), 'an opposites card has the box under Notes and Source only');
    await page.click(`${FORM} [data-x="cancel"]`);
    await openForm(page, 'jolly');
    assert(await page.locator(`${FORM} .ex-side-toggle`).count() === 0, 'a Jolly card has none: its fields are said where they stand');
    await page.click(`${FORM} [data-x="cancel"]`);
    assert(errors.length === 0, 'no page errors ' + errors.join('|'));
    await ctx.close();
  }
  // the refusal as a person meets it: a card with a side the form does not know
  {
    const bad = await (await send('POST', '/api/docs', JSON.stringify({markdown: doc('en', [
      'card-type: vocab\ntarget: [lamp]{tl}\nmeaning: a light\nnotes: it shines\nnotes-side: banana'])
      .replace('title: Sides en', 'title: A side that is neither')}))).json();
    const ctx = await browser.newContext({viewport: {width: 1400, height: 1000}});
    const page = await ctx.newPage();
    await page.goto(`${B}/doc/${bad.meta.id}/edit`);
    await page.waitForSelector('#sheet .exercise');
    await sleep(600);
    assert((await page.locator('#sheet .ex-invalid').textContent()).includes('notes-side must be answer or question'),
           'the card shows the parser\'s sentence on the page');
    await page.locator('#sheet .exercise').first().locator('.ex-edit').click();
    await page.waitForSelector(FORM);
    assert(!(await page.locator(`${FORM} .ex-side-toggle input`).first().isChecked()), 'its box is unticked');
    await page.click(`${FORM} [data-x="save"]`);
    await page.waitForSelector('#toast.err:not([hidden])');
    assert((await page.textContent('#toast')).startsWith('The side of the notes must be answer or question'),
           'saving it says so: ' + await page.textContent('#toast'));
    assert(await page.locator(FORM).count() === 1, 'and the form stays open');
    // ticking and unticking the box mends it
    await fieldBox(page, 'Notes').locator('summary').click();
    await fieldBox(page, 'Notes').locator('.ex-side-toggle input').check();
    await fieldBox(page, 'Notes').locator('.ex-side-toggle input').uncheck();
    await page.click(`${FORM} [data-x="save"]`);
    await page.waitForSelector(FORM, {state: 'detached'});
    assert(!/-side/.test(await page.evaluate(() => document.querySelector('#src').value)), 'ticking the box and unticking it mends it');
    await ctx.close();
  }

  /* the box at both widths, in every theme */
  console.log('d2) the box at 1280 and 390, light, dark and sepia');
  for (const theme of ['light', 'dark', 'sepia']) {
    for (const [w, h] of [[1280, 900], [390, 844]]) {
      const ctx = await browser.newContext({viewport: {width: w, height: h}});
      await ctx.addInitScript(t => { try { localStorage.setItem('parseh_theme', t); } catch (e) { /* none */ } }, theme);
      const page = await ctx.newPage();
      await page.goto(`${B}/doc/${ids.en}/edit`);
      await page.waitForSelector('#sheet .ex-flashcard');
      await sleep(500);
      await page.locator('#sheet .exercise').nth(idx.reverse).locator('.ex-edit').click();
      await page.waitForSelector(FORM);
      await fieldBox(page, 'Notes').locator('summary').click();
      await fieldBox(page, 'Notes').locator('.ex-side-toggle input').check();
      const box = fieldBox(page, 'Notes').locator('.ex-side-toggle');
      await box.scrollIntoViewIfNeeded();
      await sleep(500);
      const m = await page.evaluate(F => {
        const t = document.querySelector(F + ' details[open] .ex-side-toggle'), i = t.querySelector('input');
        const modal = document.querySelector(F), mr = modal.getBoundingClientRect(), r = t.getBoundingClientRect(), ir = i.getBoundingClientRect();
        const body = modal.querySelector('.ex-form-body').getBoundingClientRect();
        const cs = getComputedStyle(t), bg = getComputedStyle(modal).backgroundColor;
        const hit = document.elementFromPoint(ir.left + ir.width / 2, ir.top + ir.height / 2);
        const hitText = document.elementFromPoint(r.left + 40, r.top + r.height / 2);
        return {theme: document.body.dataset.theme || document.documentElement.dataset.theme || '', color: cs.color, bg,
                insideWindow: r.left >= 0 && r.right <= innerWidth && ir.top >= body.top && ir.bottom <= body.bottom,
                insideModal: ir.left >= mr.left && r.right <= mr.right + 1,
                noSideScroll: document.documentElement.scrollWidth <= innerWidth + 1, boxSize: [ir.width, ir.height],
                hit: hit === i, hitText: !!hitText && hitText.closest('.ex-side-toggle') === t, checked: i.checked,
                wrapped: r.height > 40};
      }, FORM);
      // the words are readable: colour against the modal's colour differ
      const contrast = await page.evaluate(F => {
        const rgb = s => s.match(/[\d.]+/g).slice(0, 3).map(Number);
        const lum = ([r, g, b]) => { const f = v => { v /= 255; return v <= .03928 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4; }; return .2126 * f(r) + .7152 * f(g) + .0722 * f(b); };
        const t = document.querySelector(F + ' details[open] .ex-side-toggle');
        let bg = t, c = [0, 0, 0, 0];
        while (bg && (getComputedStyle(bg).backgroundColor.match(/[\d.]+/g) || []).length && (getComputedStyle(bg).backgroundColor.match(/[\d.]+/g) || [])[3] === '0') bg = bg.parentElement;
        const a = lum(rgb(getComputedStyle(t).color)), b = lum(rgb(getComputedStyle(bg || document.body).backgroundColor));
        return (Math.max(a, b) + .05) / (Math.min(a, b) + .05);
      }, FORM);
      assert(m.insideWindow && m.insideModal && m.noSideScroll && m.hit && m.hitText && m.checked && m.boxSize[0] < 24 && contrast >= 4.5,
             `${theme} ${w}px: the box is inside the window, ticked, reached by a click on it and on its words, nothing scrolls sideways, contrast ${contrast.toFixed(1)}: ${JSON.stringify(m)}`);
      await shot(page, `form-notes-${theme}-${w}`, {});
      await ctx.close();
    }
  }

  /* ---------------- e) a deck ---------------- */
  console.log('e) a deck\'s study and cram pages');
  const studied = async (page, stage, forcedValue) => {
    await page.waitForSelector(`${stage} .ex-flashcard`, {timeout: 8000});
    return halves(page.locator(`${stage} .ex-flashcard`).first());
  };
  for (const [v, meaningFirst] of [[0.9, true], [0.1, false]]) {
    const ctx = await browser.newContext({viewport: {width: 1100, height: 900}});
    await ctx.addInitScript(forced(v));
    const page = await ctx.newPage();
    await page.goto(`${B}/exercises/deck/${randomDeck.path}/study`);
    let h = await studied(page, '#study-stage');
    assert(same(h.first.fields, meaningFirst ? ['turned a key'] : ['wound', 'waund'])
           && same(h.second.fields, meaningFirst ? ['wound', 'waund', 'she wound the clock', 'past of wind', 'Oxford'] : ['turned a key', 'she wound the clock', 'past of wind', 'Oxford']),
           `the study page, random ${v}: the extras are on the revealed side: ${JSON.stringify(h)}`);
    await page.click('#btn-show');
    h = await halves(page.locator('#study-stage .ex-flashcard'));
    assert(h.flipped && !h.second.hidden && h.second.fields.slice(-3).join('|') === 'she wound the clock|past of wind|Oxford', 'Show answer turns it to them');
    await shot(page, `study-random-${v}`, {});
    await ctx.close();
  }
  {
    const ctx = await browser.newContext({viewport: {width: 1100, height: 900}});
    const page = await ctx.newPage();
    await page.goto(`${B}/exercises/deck/${reverseDeck.path}/study`);
    let h = await studied(page, '#study-stage');
    assert(same(h.first.fields, ['a way in']) && same(h.second.fields, ['door', 'open the door', 'a noun', 'Longman']),
           'the study page of a reverse card: the meaning alone asks, the word and its example, notes and source answer');
    await page.click('#btn-show');
    h = await halves(page.locator('#study-stage .ex-flashcard'));
    assert(h.flipped && !h.second.hidden, 'and Show answer shows them');
    await ctx.close();
  }
  {
    // the browse page: a row opened shows the card with both sides at once
    const ctx = await browser.newContext({viewport: {width: 1100, height: 900}});
    const page = await ctx.newPage();
    await page.goto(`${B}/exercises/deck/${reverseDeck.path}`);
    await page.waitForSelector('.dk-row');
    await page.locator('.dk-row-toggle').first().click();
    await page.waitForSelector('.dk-row-preview .ex-flashcard');
    const h = await halves(page.locator('.dk-row-preview .ex-flashcard').first());
    assert(h.flipped && same(h.first.fields, ['a way in']) && same(h.second.fields, ['door', 'open the door', 'a noun', 'Longman']) && !h.second.hidden,
           'the browse page shows a reverse card with the meaning alone on the side shown first and the example, notes and source on the other: ' + JSON.stringify(h));
    await ctx.close();
  }
  {
    const ctx = await browser.newContext({viewport: {width: 1100, height: 900}});
    await ctx.addInitScript(forced(0.9));
    const page = await ctx.newPage();
    await page.goto(`${B}/exercises/deck/${randomDeck.path}/cram#all`);
    const h = await studied(page, '#cram-stage');
    assert(randomDeckCard(h, true), 'the cram page draws it the same: ' + JSON.stringify(h));
    await ctx.close();
  }
  {
    // the two cards of a both-repeat card: each by the rule for its own direction
    const items = (await (await send('GET', `/exercises/api/decks/${repeatDeck.path}`)).json()).items;
    assert(items.length === 2 && items[0].direction === 'forward' && items[1].direction === 'reverse',
           'a both-repeat card is two cards of a deck, one a direction');
    const drawn = [];
    for (const item of items) {
      const r = await (await send('GET', `/exercises/api/decks/${repeatDeck.path}/items/${item.id}`)).json();
      const ctx = await browser.newContext();
      const page = await ctx.newPage();
      await page.setContent(`<div id=h>${r.html}</div>`);
      drawn.push(await page.evaluate(() => {
        const c = document.querySelector('.ex-flashcard');
        const f = x => [...c.querySelector(':scope > ' + x).children].filter(e => e.classList.contains('ex-card-field')).map(e => e.textContent.trim());
        return {first: f('.ex-card-front'), second: f('.ex-card-back')};
      }));
      await ctx.close();
    }
    assert(same(drawn[0], {first: ['wound', 'waund'], second: ['turned a key', 'she wound the clock', 'past of wind', 'Oxford']})
           && same(drawn[1], {first: ['turned a key'], second: ['wound', 'waund', 'she wound the clock', 'past of wind', 'Oxford']}),
           'the forward card asks the word and answers the meaning with the extras; the reverse card asks the meaning and answers with the word and the extras: ' + JSON.stringify(drawn));
  }

  /* ---------------- f) exports, opened as files ---------------- */
  console.log('f) exported pages');
  {
    const html = await Deno.readTextFile(exportDoc);
    assert(html.includes('function drawFirstSide') && html.includes('data-extra'),
           'the exported page carries the draw (with the move) in its own script, and the marked fields');
    for (const [v, meaningFirst] of [[0.9, true], [0.1, false]]) {
      const ctx = await browser.newContext({viewport: {width: 1100, height: 900}});
      await ctx.addInitScript(forced(v));
      const page = await ctx.newPage();
      const errors = [], requests = [];
      page.on('pageerror', e => errors.push(e.message));
      page.on('request', r => { if (!/^(file|data|blob):/.test(r.url())) requests.push(r.url()); });
      await page.goto(`file://${exportDoc}`);
      await page.waitForSelector('.ex-flashcard');
      const cards = page.locator('.ex-flashcard');
      let h = await halves(cards.nth(idx.random));
      assert(same(h.first.fields, meaningFirst ? ['turned a key'] : ['wound', 'waund'])
             && same(h.second.fields.slice(-3), ['she wound the clock', 'past of wind', 'Oxford']) && same(h.first.marked, []),
             `export, random ${v}: the extras are on the revealed side`);
      h = await halves(cards.nth(idx.mixed));
      assert(h.first.fields.slice(-1)[0] === 'also a verb' && same(h.second.fields.slice(-2), ['a coil of rope', 'Collins']),
             `export, random ${v}: notes-side: question stays with the side shown first`);
      h = await halves(cards.nth(idx.reverse));
      assert(same(h.first.fields, ['a way in']) && same(h.second.fields, ['door', 'open the door', 'a noun', 'Longman']), 'export: a reverse card');
      await cards.nth(idx.random).click();
      h = await halves(cards.nth(idx.random));
      assert(h.flipped && !h.second.hidden && h.first.hidden, 'export: the card turns');
      assert(errors.length === 0 && requests.length === 0, `export: no errors and no network (${errors} ${requests})`);
      await ctx.close();
    }
    for (const [v, meaningFirst] of [[0.9, true], [0.1, false]]) {
      const ctx = await browser.newContext({viewport: {width: 1100, height: 800}});
      await ctx.addInitScript(forced(v));
      const p2 = await ctx.newPage();
      const errors = [];
      p2.on('pageerror', e => errors.push(e.message));
      await p2.goto(`file://${exportDeck}`);
      await p2.waitForSelector('.ex-flashcard', {timeout: 8000});
      const h = await halves(p2.locator('.ex-flashcard').first());
      assert(errors.length === 0 && randomDeckCard(h, meaningFirst),
             `the exported deck, random ${v}: the extras on the revealed side, a question one on the first: ${JSON.stringify(h)}`);
      await ctx.close();
    }
  }
  console.log(`flashcard_sides: ${passed} checks passed`);
} finally {
  await browser.close();
  proc.kill('SIGTERM');
  await Deno.remove(TMP, {recursive: true}).catch(() => {});
}

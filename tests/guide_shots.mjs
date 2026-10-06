// SPDX-License-Identifier: GPL-3.0-or-later
import {chromium} from 'npm:playwright-core@1.52.0';
import {gearOpen, gearClose, gearRow} from './gear_driver.mjs';
// THE GUIDE'S PICTURES, retaken from the real pages (a0.5.0).
//
// Run (from the checkout, with the toolchain of tests/ on the path):
//   CHROME_BIN=/path/to/chrome PARSEH_PYTHON=python3 deno run --allow-all tests/guide_shots.mjs
//   GUIDE_SHOTS_ONLY=reader,gear-reader   retakes only those pictures (the keys of FILES below)
//   GUIDE_SHOTS_OUT=<dir>                 saves into <dir>/<section>/shots/ instead of html-guide/markdown/
//   GUIDE_SHOTS_LIST=1                    prints the names and stops
// Then compile the guide again (python3 html-guide/build.py): site/ holds the pictures too.
//
// WHAT IT DOES.  It boots the REAL hub (serve.main) on a temporary toolbox, the one tests/mobile_harness.py builds
// for tests/mobile_pages.mjs and tests/gear_reader.mjs (the fixture editions of six languages, a narrated English
// book with its film, three exercise decks), adds what the pictures need (a Persian video with a film to play, a
// small Persian dictionary, studio documents that link to each other, flags to review later), and drives the pages
// in a real Chromium the way the suites do: a mouse at a computer's size, a finger at a phone's.  Nothing is drawn by
// hand: every picture is a screenshot of a page a person would meet, in the light colours, at 1x, and only what the
// person is to look at is kept (a clip).  Nothing of the checkout's config/, books/, youtube/ or exercises/ is read or
// written: it all lives in the temporary tree, which is removed at the end.
//
// A PICTURE THAT DOES NOT MATCH THE SENTENCE BESIDE IT IS A BUG OF THE PICTURE: look at every file this saves before
// the guide is compiled.
const root = await Deno.realPath(new URL('..', import.meta.url));
Deno.chdir(root);
const PY = Deno.env.get('PARSEH_PYTHON') || 'python3';
const OUT = Deno.env.get('GUIDE_SHOTS_OUT') || `${root}/html-guide/markdown`;
const ONLY = (Deno.env.get('GUIDE_SHOTS_ONLY') || '').split(',').filter(Boolean);
const td = new TextDecoder();
const sleep = ms => new Promise(r => setTimeout(r, ms));
const run = async (args, opts = {}) => {
  const o = await new Deno.Command(args[0], {args: args.slice(1), stdout: 'piped', stderr: 'piped', ...opts}).output();
  if (!o.success) throw Error(td.decode(o.stderr) || td.decode(o.stdout));
  return td.decode(o.stdout);
};
const py = (code, ...args) => run([PY, '-c', code, ...args]);

/* ------------------------------------------------------------------ the pictures: name -> where it is saved */
const FILES = {
  // the book's reader
  'reader':            'books/shots/reader.png',                         // the header and a few chunks
  'reader-switch':     'lookup-and-languages/shots/reader-switch.png',   // gloss, hover, dictionary
  'gear-reader':       'getting-started/shots/gear-reader.png',          // the gear open on a book, wide
  'gear-reader-phone': 'getting-started/shots/gear-reader-phone.png',    // the sheet on a phone
  'gear-zoom':         'getting-started/shots/gear-zoom.png',            // the Zoom group, the page at 150 %
  'levels-names':      'books/shots/levels-names.png',                   // the Levels rows, one level renamed
  'diacritics-on':     'books/shots/diacritics-on.png',                  // a Persian line with its marks ...
  'diacritics-off':    'books/shots/diacritics-off.png',                 // ... and without
  // the video's player
  'player':            'videos/shots/player.png',
  'gear-player':       'getting-started/shots/gear-player.png',
  // the studio's pages
  'doc-linked':        'studio/shots/linked-from.png',                   // a document, its bars, its drawer
  'gear-document':     'getting-started/shots/gear-document.png',
  'gear-deck':         'getting-started/shots/gear-deck.png',
  // the hub
  'editor':            'studio/shots/editor.png',
  'study-gif':         'exercises/shots/study.gif',                      // a card turned over, rated, and the next
  // the hub
  'hub':               'getting-started/shots/hub.png',
  'hub-later':         'getting-started/shots/hub-later.png',            // the Review later door
  'hub-foot':          'getting-started/shots/hub-foot.png',             // the foot: the addresses, the version, the two links
  'modes-gif':         'getting-started/shots/modes.gif',                // a phone's hub: Mobile, the colours, Browser
  'dictionary-sheet':  'getting-started/shots/dictionary-sheet.png',     // a phone's dictionary sheet: a book and a video
  'later-hub':         'books/shots/later-hub.png',                      // the Review later page
  'later-cloud':       'books/shots/later-cloud.png',                    // the gloss cloud with its review later button
  'later-marks':       'books/shots/later-marks.png',                    // two chunks flagged, the dotted line
  'later-panel':       'books/shots/later-panel.png',                    // the list beside the book, on a computer
  'later-phone':       'books/shots/later-phone.png',                    // the list as a sheet, on a phone
  'later-player':      'videos/shots/later-player.png',                  // a video: two phrases flagged, the list on the right
};
const wanted = name => !ONLY.length || ONLY.includes(name);
if (Deno.env.get('GUIDE_SHOTS_LIST')) { console.log(Object.keys(FILES).join('\n')); Deno.exit(0); }
const saved = [];
async function save(page, name, clip) {
  const file = `${OUT}/${FILES[name]}`;
  await Deno.mkdir(file.replace(/\/[^/]*$/, ''), {recursive: true});
  const target = clip && typeof clip.screenshot === 'function' ? clip : null;
  if (target) await target.screenshot({path: file});
  else await page.screenshot({path: file, ...(clip ? {clip} : {})});
  saved.push(FILES[name]);
  console.log('  saved', FILES[name]);
}

/* ------------------------------------------------------------------ the toolbox */
const WORK = await Deno.makeTempDir({prefix: 'parseh-guide-shots-'});
const MADE = JSON.parse((await run([PY, 'tests/mobile_harness.py', 'build', WORK])).trim().split('\n').pop());
const READERS = MADE.readers;
const FAVID = 'fA6bK2mQ8sT';                                       // the Persian fixture video, "at the greengrocer's"

// A Persian video with a film to play (tests/fixtures/videos), and what the dictionary will answer for it
await py(String.raw`
import shutil, subprocess, sys
from pathlib import Path
work, vid = Path(sys.argv[1]), sys.argv[2]
src = Path('tests/fixtures/videos/persian') / vid
dst = work / 'root' / 'youtube' / 'videos' / 'persian' / vid
shutil.copytree(src, dst, ignore=shutil.ignore_patterns('parts'))
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', 'testsrc=duration=40:size=640x360:rate=10',
                '-f', 'lavfi', '-i', 'sine=frequency=330:duration=40', '-shortest', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                '-c:a', 'aac', str(dst / 'media.mp4')], check=True)
`, WORK, FAVID);

// one entry for a word, its senses one to a line (lib/lookup.py)
const DICTS = {fa: [
  ['هیچ', 'hič', 'det', 'no, none\nnothing\nnot any'], ['جا', 'jā', 'noun', 'place\nroom, space\nseat'],
  ['دنیا', 'donyā', 'noun', 'world\nthe earth\nlife'], ['سیب', 'sib', 'noun', 'apple\napple tree'],
  ['چند', 'čand', 'det', 'how many\nhow much\nsome'], ['است', 'ast', 'verb', 'is\nthere is']]};
const SERVE = String.raw`
import json, os, sys
from pathlib import Path
tmp, port = Path(sys.argv[1]), int(sys.argv[2])
repo = Path.cwd()
sys.path[:0] = [str(repo / p) for p in ('markdown/exlex', 'markdown/app', 'youtube/lib', 'lib', 'tests', '.')]
import lookup, corpus, getmt
lookup.DICT_DIR = str(tmp / 'dict')
corpus.CORPUS_DIR = str(tmp / 'nocorpus')
getmt.MT_DIR = str(tmp / 'nomt')
getmt.ENGINE_DIR = str(tmp / 'nomt' / 'engine')
os.makedirs(lookup.DICT_DIR, exist_ok=True)
for code, rows in json.loads(sys.argv[3]).items():
    c = lookup.create(lookup.path_for(code))
    for head, translit, pos, sense, *forms in rows:
        cur = c.execute("INSERT INTO entry (headword, translit, pos, sense) VALUES (?,?,?,?)", (head, translit, pos, sense))
        for form in [head] + forms:
            c.execute("INSERT INTO form (form, entry_id, note) VALUES (?,?,?)", (form, cur.lastrowid, ''))
    c.executemany("INSERT INTO meta (key, value) VALUES (?,?)", [('lang', code), ('source', 'a test dictionary'), ('licence', 'none')])
    c.commit()
    c.close()
import mobile_harness
mobile_harness.serve_it(tmp, port)
`;
const port = await (async () => { const l = Deno.listen({hostname: '127.0.0.1', port: 0}); const p = l.addr.port; l.close(); return p; })();
const hub = new Deno.Command(PY, {args: ['-c', SERVE, WORK, String(port), JSON.stringify(DICTS)], stdout: 'null', stderr: 'null'}).spawn();
const B = `http://127.0.0.1:${port}`;
for (const t = Date.now();;) {
  try { const r = await fetch(B + '/'); await r.body?.cancel(); if (r.ok) break; } catch (_) {}
  if (Date.now() - t > 60000) throw Error('the hub did not start');
  await sleep(250);
}
const post = (path, data) => fetch(B + path, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)});

// the studio's documents: a lesson and two that point at it (the "Linked from" drawer), and a deck of flashcards
const LESSON = `---
title: Verbs of motion
subtitle: [رفتن]{tl} and [آمدن]{tl}, and the verbs built on them
target: fa
---

Notes for the second lesson

Two verbs carry most of the movement in Persian: [رفتن]{tl} = *to go* and [آمدن]{tl} = *to come*.

:::exercise flashcard
card-type: vocab
target: [رفتن]{tl}
transliteration: raftan
meaning: to go
context: [من هر روز به خانه می‌روم.]{tl}
:::
`;
const LINKER = (title, text) => `---\ntitle: ${title}\ntarget: fa\n---\n\n${text}\n`;
const makeDoc = async (md, tags) => (await (await post('/studio/api/docs', {markdown: md, tags})).json()).meta.id;
const lessonId = await makeDoc(LESSON, ['grammar', 'verbs']);
await makeDoc(LINKER('Everyday questions', 'For the verb [رفتن]{tl}, see [the verbs of motion](doc:Verbs of motion) first.'), []);
await makeDoc(LINKER('Travel phrases', 'The verbs in these phrases are explained in [Verbs of motion](doc:Verbs of motion).'), []);
const deckPath = (await (await post('/exercises/api/decks', {name: 'Everyday Persian', lang: 'fa'})).json()).deck.path;
for (const markdown of [
  ':::exercise flashcard\ncard-type: vocab\ntarget: [خداحافظ]{tl}\ntransliteration: xodāhāfez\nmeaning: goodbye\n:::',
  ':::exercise flashcard\ncard-type: vocab\ntarget: [سلام]{tl}\ntransliteration: salām\nmeaning: hello\ncontext: [سلام، حال شما چطور است؟]{tl}\n:::',
  ':::exercise flashcard\ncard-type: vocab\ntarget: [کتاب]{tl}\ntransliteration: ketāb\nmeaning: book\n:::',
]) { const r = await post(`/exercises/api/decks/${deckPath}/items`, {markdown}); if (!r.ok) throw Error(await r.text()); }

// what a person has flagged to review later, put in by the door the pages use (lib/later.py): two chunks of a Persian
// book, one of a Persian video, one of an English book
const bookTitle = async path => JSON.parse(await Deno.readTextFile(`${WORK}/root/books/${path}/book.json`)).title_latin || '';
async function seedFlags() {
  const FA = '/books/persian/mini-fa/reader/', EN = '/books/english/mini-en/reader/', at = Date.now() / 1000;
  const faTitle = await bookTitle('persian/mini-fa'), enTitle = await bookTitle('english/mini-en');
  const add = (record, ago) => ({op: 'add', record: {by: 'Linux computer · Chrome', glossLang: 'en', at: at - ago, ...record}});
  const ops = [
    add({id: `later:book:${FA}:1.1-1ac09deff425:0:q1a`, kind: 'book', ref: FA, lang: 'fa', title: faTitle,
         where: {sub: '1.1-1ac09deff425', k: 0, para: '1:1', label: '1.1', chapter: '1', t: null},
         text: 'هیچ جایِ دُنیا', tr: 'hič jā-ye donyā', en: 'nowhere in the world', voc: 'جا jā place, + ezafe -ye',
         sentence: 'هیچ جایِ دُنیا تَروُ خُشک را مِثلِ ایران با هَم نِمی سوزانَند.'}, 3 * 3600),
    add({id: `later:book:${FA}:1.1-1ac09deff425:3:q1b`, kind: 'book', ref: FA, lang: 'fa', title: faTitle,
         where: {sub: '1.1-1ac09deff425', k: 3, para: '1:1', label: '1.1', chapter: '1', t: null},
         text: 'نِمی سوزانَند.', tr: 'nemi-suzānand', en: 'do they burn', voc: 'سوزاندن suzāndan · to burn (something)',
         sentence: 'هیچ جایِ دُنیا تَروُ خُشک را مِثلِ ایران با هَم نِمی سوزانَند.'}, 3 * 3600 - 60),
    add({id: `later:video:${FAVID}:12:2:q1c`, kind: 'video', ref: FAVID, lang: 'fa', title: 'در میوه‌فروشی',
         where: {start: 12, j: 1, text: 'کیلویی سی هزار تومان، تازه آمده'},
         text: 'تازه آمده', tr: 'tāze āmade', en: 'just come in', voc: 'تازه tāze fresh, newly · آمده āmade come'}, 26 * 3600),
    add({id: `later:book:${EN}:1.1-aa11bb22cc33:1:q1d`, kind: 'book', ref: EN, lang: 'en', title: enTitle,
         where: {sub: '1.1-aa11bb22cc33', k: 1, para: '1:1', label: '1.1', chapter: '1', t: 4.2},
         text: 'wound the clock', en: 'gave the clock its weekly winding'}, 5 * 86400),
  ];
  const r = await post('/__later', {by: 'the guide', ops});
  if (!r.ok) throw Error('the flags were refused: ' + await r.text());
}
// the panel scrolled so that a group's own name is at its top (the head of the panel stays where it is)
async function scrollGroup(page, id) {
  await page.evaluate(id => {
    const b = document.querySelector('.pg-panel .pg-body'), g = document.querySelector(`.pg-panel [data-pg-group="${id}"]`);
    if (b && g) b.scrollTop += g.getBoundingClientRect().top - b.getBoundingClientRect().top - 2;
  }, id);
  await sleep(200);
}

async function resetPrefs() {
  const at = Date.now() / 1000, keys = {bk_rate: '1', bk_gap: '0', bk_skip: '10', bk_stopbnd: '0', bk_cont: '1', parseh_theme: 'auto'};
  for (const c of ['fa', 'ar', 'it', 'ja', 'fr', 'de', 'tr', 'en', 'hi', 'es', 'zh'])
    for (const k of ['vocal', 'chunks', 'bare', 'alt', 'aloud']) keys[`bk_lvl:${c}:${k}`] = '';
  const settings = {};
  for (const [k, v] of Object.entries(keys)) settings[k] = {v, at};
  const r = await post('/__prefs', {by: 'the guide', settings});
  await r.body?.cancel();
  await sleep(60);
}

async function flagChunks(page, which, how = 'flag') {
  for (const k of which) {
    const row = page.locator('main .row .fa').nth(k);
    await row.scrollIntoViewIfNeeded();
    await row.hover();
    await sleep(350);
    if (how === 'flag') await page.locator('.later-flag').first().click();
    else await page.keyboard.press('l');
    await sleep(500);
    await page.mouse.move(2, 2);
    await sleep(300);
  }
  // the line that says it was flagged goes by itself
  await sleep(4500);
}

// the flags too go back to none before every picture: the key that flags a chunk takes the flag off one that has it,
// so what one picture flagged would be undone by the next
async function resetLater() {
  const j = await (await fetch(B + '/__later?all=1')).json();
  const ops = (j.items || []).filter(x => !x.gone).map(x => ({op: 'remove', id: x.id, at: (x.at || 0) + 0.001}));
  if (ops.length) { const r = await post('/__later', {by: 'the guide', ops}); await r.body?.cancel(); }
}

const browser = await chromium.launch({executablePath: Deno.env.get('CHROME_BIN'), headless: true});
const DESK = w => ({viewport: {width: w, height: 800}});
const PHONE = {viewport: {width: 390, height: 844}, isMobile: true, hasTouch: true, deviceScaleFactor: 1};
async function context(opts, seed = {}) {
  const ctx = await browser.newContext(opts);
  ctx.touch = !!opts.hasTouch;
  // the device's own settings, put in before the first page is drawn, once (what a person set earlier)
  await ctx.addInitScript(s => {
    try {
      if (localStorage.getItem('__shots_seed')) return;
      localStorage.setItem('__shots_seed', '1');
      for (const [k, v] of Object.entries(s)) localStorage.setItem(k, v);
      if (s.parseh_mode) document.cookie = 'parseh_mode=' + s.parseh_mode + '; Path=/; SameSite=Lax; Max-Age=31536000';
    } catch (e) {}
  }, seed);
  return ctx;
}
const hit = async (page, sel) => { const l = typeof sel === 'string' ? page.locator(sel).filter({visible: true}).first() : sel; if (page.touch) await l.tap(); else await l.click(); };
async function newPage(ctx, size) {
  const page = await ctx.newPage();
  page.touch = ctx.touch;
  if (size) await page.setViewportSize(size);
  page.on('pageerror', e => console.log('PAGE ERROR', e.message));
  return page;
}
async function openReader(ctx, code, size) {
  const page = await newPage(ctx, size);
  await page.goto(B + READERS[code], {waitUntil: 'load'});
  await page.waitForSelector('[data-parseh-gear]', {state: 'attached', timeout: 15000});
  await sleep(500);
  if (await page.$('.pf-bar')) await hit(page, '.pf-stay');
  await page.evaluate(() => document.fonts.ready);
  await sleep(200);
  return page;
}
async function openPlayer(ctx, size) {
  const page = await newPage(ctx, size);
  await page.goto(`${B}/youtube/v/${FAVID}/`, {waitUntil: 'load'});
  await page.waitForSelector('[data-parseh-gear]', {state: 'attached', timeout: 15000});
  await page.waitForSelector('#segs .seg', {timeout: 15000});
  await page.evaluate(() => document.fonts.ready);
  await sleep(600);
  return page;
}
const box = (page, sel) => page.evaluate(sel => { const r = document.querySelector(sel).getBoundingClientRect(); return {x: r.x, y: r.y, width: r.width, height: r.height}; }, sel);
const grow = (b, d) => ({x: Math.max(0, b.x - d), y: Math.max(0, b.y - d), width: b.width + 2 * d, height: b.height + 2 * d});

/* ------------------------------------------------------------------ the pictures */
const PICS = {
  async reader() {
    const ctx = await context(DESK(860));
    const page = await openReader(ctx, 'fa', {width: 860, height: 560});
    await save(page, 'reader');
    await ctx.close();
  },
  async 'reader-switch'() {
    const ctx = await context(DESK(1000));
    const page = await openReader(ctx, 'fa');
    await page.waitForSelector('#dictmode:not([hidden])', {timeout: 15000});
    await page.click('#dictmode');
    await sleep(300);
    const a = await box(page, '[data-toggle=nogloss]'), z = await box(page, '#dictmode');
    await save(page, 'reader-switch', {x: a.x - 8, y: a.y - 8, width: z.x + z.width - a.x + 16, height: a.height + 16});
    await ctx.close();
  },
  async 'gear-reader'() {
    const ctx = await context(DESK(1000));
    const page = await openReader(ctx, 'fa', {width: 1000, height: 760});
    await gearOpen(page);
    await save(page, 'gear-reader');
    await ctx.close();
  },
  async 'gear-reader-phone'() {
    const ctx = await context(PHONE, {parseh_mode: 'mobile'});
    const page = await openReader(ctx, 'fa');
    await gearOpen(page);
    await sleep(400);
    await save(page, 'gear-reader-phone');
    await ctx.close();
  },
  async 'gear-zoom'() {
    const ctx = await context(DESK(1280), {parseh_zoom: '150'});
    const page = await openReader(ctx, 'fa', {width: 1280, height: 720});
    await gearOpen(page);
    await scrollGroup(page, 'zoom');
    await save(page, 'gear-zoom', {x: 400, y: 0, width: 880, height: 720});
    await ctx.close();
  },
  async 'levels-names'() {
    const ctx = await context(DESK(1000));
    const page = await openReader(ctx, 'fa', {width: 1000, height: 760});
    await gearOpen(page);
    const field = gearRow(page, 'levels').locator('input.pg-lvname').nth(2);
    await field.fill('Newspaper');
    await field.press('Enter');
    await sleep(800);
    await save(page, 'levels-names', gearRow(page, 'levels'));
    await ctx.close();
  },
  async 'diacritics-on'() {
    const ctx = await context(DESK(860));
    const page = await openReader(ctx, 'fa', {width: 860, height: 700});
    const line = async () => page.evaluate(() => {
      const rs = [...document.querySelectorAll('.p1')[0].querySelectorAll('.w')].flatMap(w => [...w.getClientRects()]);
      const x = Math.min(...rs.map(r => r.left)), y = Math.min(...rs.map(r => r.top));
      return {x: Math.max(0, x - 16), y: Math.max(0, y - 4), width: Math.min(860, Math.max(...rs.map(r => r.right)) + 16) - Math.max(0, x - 16),
              height: Math.max(...rs.map(r => r.bottom)) - y + 14};
    });
    const b = await line();
    await save(page, 'diacritics-on', b);
    await gearOpen(page);
    await gearRow(page, 'marks').locator('button.pg-switch').click();
    await sleep(300);
    await gearClose(page);
    await sleep(300);
    await save(page, 'diacritics-off', b);
    await ctx.close();
  },
  async player() {
    const ctx = await context(DESK(1000));
    const page = await openPlayer(ctx, {width: 1000, height: 625});
    await page.click('#sbs');
    await sleep(400);
    await page.evaluate(() => { ParsehPlayer.seek(12); ParsehPlayer.pause(); });
    await sleep(900);
    await page.locator('.seg[data-i="2"] .fa .w').nth(1).hover();
    await page.waitForSelector('#cloud', {state: 'visible', timeout: 8000});
    await sleep(400);
    await save(page, 'player');
    await ctx.close();
  },
  async 'gear-player'() {
    const ctx = await context(DESK(1280));
    const page = await openPlayer(ctx, {width: 1280, height: 760});
    await gearOpen(page);
    await scrollGroup(page, 'watching');
    await save(page, 'gear-player', {x: 540, y: 0, width: 740, height: 760});
    await ctx.close();
  },
  async 'doc-linked'() {
    const ctx = await context(DESK(1280));
    const page = await newPage(ctx, {width: 1280, height: 560});
    await page.goto(`${B}/studio/doc/${lessonId}`, {waitUntil: 'load'});
    await page.waitForSelector('[data-parseh-gear]', {state: 'attached', timeout: 15000});
    await page.evaluate(() => document.fonts.ready);
    await sleep(500);
    await page.locator('button:has-text("Linked from")').first().click();
    await sleep(700);
    await save(page, 'doc-linked');
    await ctx.close();
  },
  async 'gear-document'() {
    const ctx = await context(DESK(1280));
    const page = await newPage(ctx, {width: 1280, height: 760});
    await page.goto(`${B}/studio/doc/${lessonId}`, {waitUntil: 'load'});
    await page.waitForSelector('[data-parseh-gear]', {state: 'attached', timeout: 15000});
    await page.evaluate(() => document.fonts.ready);
    await sleep(300);
    await gearOpen(page);
    await scrollGroup(page, 'text');
    await save(page, 'gear-document', {x: 640, y: 0, width: 640, height: 760});
    await ctx.close();
  },
  async editor() {
    const ctx = await context(DESK(1280));
    const page = await newPage(ctx, {width: 1280, height: 640});
    await page.goto(`${B}/studio/doc/${lessonId}/edit`, {waitUntil: 'load'});
    await page.waitForSelector('[data-parseh-gear]', {state: 'attached', timeout: 15000});
    await page.waitForSelector('#sheet .exercise, #sheet h1', {timeout: 15000});
    await page.evaluate(() => document.fonts.ready);
    await sleep(700);
    await save(page, 'editor');
    await ctx.close();
  },
  async 'gear-deck'() {
    const ctx = await context(DESK(1280));
    const page = await newPage(ctx, {width: 1280, height: 760});
    await page.goto(`${B}/exercises/deck/${deckPath}/`, {waitUntil: 'load'});
    await page.waitForSelector('[data-parseh-gear]', {state: 'attached', timeout: 15000});
    await page.evaluate(() => document.fonts.ready);
    await sleep(300);
    await gearOpen(page);
    await scrollGroup(page, 'text');
    await save(page, 'gear-deck', {x: 640, y: 0, width: 640, height: 760});
    await ctx.close();
  },
  async 'study-gif'() {
    // studying a deck: the front of a card, its back with the four ratings, the pointer on Good, and the next card
    const dir = `${WORK}/study`;
    await Deno.mkdir(dir, {recursive: true});
    const ctx = await context(DESK(720));
    const page = await newPage(ctx, {width: 720, height: 560});
    await page.goto(`${B}/exercises/deck/${deckPath}/study`, {waitUntil: 'load'});
    await page.waitForSelector('#study-stage .ex-flashcard', {timeout: 15000});
    await page.evaluate(() => document.fonts.ready);
    await sleep(600);
    await page.screenshot({path: `${dir}/f0.png`});
    await page.getByRole('button', {name: 'Show answer'}).click();
    await sleep(700);
    await page.screenshot({path: `${dir}/f1.png`});
    const good = page.locator('button:has-text("Good")').first();
    await good.hover();
    await sleep(400);
    await page.screenshot({path: `${dir}/f2.png`});
    await good.click();
    await sleep(900);
    await page.screenshot({path: `${dir}/f3.png`});
    const file = `${OUT}/${FILES['study-gif']}`;
    await Deno.mkdir(file.replace(/\/[^/]*$/, ''), {recursive: true});
    await run(['magick', '-delay', '170', '-loop', '0', `${dir}/f0.png`, `${dir}/f1.png`, '-delay', '90', `${dir}/f2.png`,
               '-delay', '220', `${dir}/f3.png`, '-layers', 'Optimize', '-colors', '64', file]);
    saved.push(FILES['study-gif']);
    console.log('  saved', FILES['study-gif']);
    await ctx.close();
  },
  // REVIEW LATER in the reader (lib/later-reader.js).  A chunk is flagged the way a person does it with a keyboard:
  // the pointer on the chunk and the L key.
  async 'later-cloud'() {
    const ctx = await context(DESK(1000));
    const page = await openReader(ctx, 'fa', {width: 1000, height: 640});
    await gearOpen(page);
    await gearRow(page, 'hover').locator('button.pg-switch').click();
    await gearClose(page);
    await page.locator('main .p1 .w').nth(1).hover();
    await page.waitForSelector('#cloud .mklater', {state: 'visible', timeout: 8000});
    await sleep(500);
    const b = await box(page, '#cloud');
    await save(page, 'later-cloud', grow({x: b.x, y: b.y, width: b.width, height: b.height}, 16));
    await ctx.close();
  },
  async 'later-marks'() {
    const ctx = await context(DESK(860));
    const page = await openReader(ctx, 'fa', {width: 860, height: 700});
    await flagChunks(page, [0, 2]);
    await page.mouse.move(5, 5);
    await sleep(400);
    const b = await page.evaluate(() => { const a = document.querySelector('main .sub'); const r = a.getBoundingClientRect(); return {x: r.x, y: r.y, width: r.width, height: r.height}; });
    await save(page, 'later-marks', {x: Math.max(0, b.x - 20), y: Math.max(0, b.y - 10), width: Math.min(860, b.width + 40), height: Math.min(380, b.height + 20)});
    await ctx.close();
  },
  async 'later-panel'() {
    const ctx = await context(DESK(1000));
    const page = await openReader(ctx, 'fa', {width: 1000, height: 640});
    await flagChunks(page, [0, 2]);
    await hit(page, '.later-btn');
    await page.waitForSelector('.lp-panel', {state: 'visible', timeout: 8000});
    await sleep(900);
    await save(page, 'later-panel');
    await ctx.close();
  },
  async 'later-phone'() {
    const ctx = await context(PHONE, {parseh_mode: 'mobile'});
    const page = await openReader(ctx, 'fa');
    await flagChunks(page, [0, 2], 'key');
    await page.waitForSelector('.later-btn:not([hidden])', {timeout: 8000});
    await hit(page, '.later-btn');
    await page.waitForSelector('.lp-panel', {state: 'visible', timeout: 8000});
    await sleep(900);
    await save(page, 'later-phone');
    await ctx.close();
  },
  async 'later-player'() {
    const ctx = await context(DESK(1000));
    const page = await openPlayer(ctx, {width: 1000, height: 625});
    await page.click('#sbs');
    await sleep(400);
    for (const [i, j] of [[1, 2], [2, 1]]) {
      const w = page.locator(`.seg[data-i="${i}"] .fa .w`).nth(j);
      await w.scrollIntoViewIfNeeded();
      await w.hover();
      await sleep(500);
      await page.keyboard.press('l');
      await sleep(500);
      await page.mouse.move(2, 2);
      await sleep(400);
    }
    await sleep(4500);
    await hit(page, '.later-btn');
    await page.waitForSelector('.lp-panel', {state: 'visible', timeout: 8000});
    await sleep(900);
    await save(page, 'later-player');
    await ctx.close();
  },
  async hub() {
    const ctx = await context(DESK(1000));
    const page = await newPage(ctx, {width: 1000, height: 484});
    await page.goto(B + '/', {waitUntil: 'load'});
    await page.evaluate(() => document.fonts.ready);
    await sleep(500);
    await save(page, 'hub');
    await ctx.close();
  },
  async 'hub-later'() {
    await seedFlags();
    const ctx = await context(DESK(1000));
    const page = await newPage(ctx, {width: 1000, height: 600});
    await page.goto(B + '/', {waitUntil: 'load'});
    await page.evaluate(() => document.fonts.ready);
    await sleep(600);
    const door = page.locator('a.door[href="/later/"]');
    await door.scrollIntoViewIfNeeded();
    await sleep(300);
    await save(page, 'hub-later', door);
    await ctx.close();
  },
  async 'hub-foot'() {
    const ctx = await context(DESK(1000));
    const page = await newPage(ctx, {width: 1000, height: 700});
    await page.goto(B + '/', {waitUntil: 'load'});
    await page.evaluate(() => document.fonts.ready);
    // the temporary toolbox listens on a free port; the picture says the address a person's own Parseh answers on
    await page.evaluate(() => { const a = document.querySelector('.foot .addr'); if (a) a.textContent = 'https://localhost:7654/'; });
    const foot = page.locator('.hub-browser .foot, .foot').first();
    await foot.scrollIntoViewIfNeeded();
    await sleep(400);
    await save(page, 'hub-foot', foot);
    await ctx.close();
  },
  async 'later-hub'() {
    await seedFlags();
    const ctx = await context(DESK(1000));
    const page = await newPage(ctx, {width: 1000, height: 640});
    await page.goto(B + '/later/', {waitUntil: 'load'});
    await page.waitForSelector('.lr', {timeout: 15000});
    await page.evaluate(() => document.fonts.ready);
    await sleep(700);
    await save(page, 'later-hub');
    await ctx.close();
  },
  async 'modes-gif'() {
    // a phone's hub: the browser interface, Mobile pressed, ◐ through dark and sepia, and back to Browser
    const dir = `${WORK}/modes`;
    await Deno.mkdir(dir, {recursive: true});
    const ctx = await context({viewport: {width: 390, height: 640}, isMobile: true, hasTouch: true, deviceScaleFactor: 1},
                              {parseh_mode: 'browser', parseh_theme: 'light'});
    const page = await newPage(ctx);
    await page.goto(B + '/', {waitUntil: 'load'});
    await page.evaluate(() => document.fonts.ready);
    await sleep(700);
    let n = 0;
    const frame = async () => { await sleep(700); await page.screenshot({path: `${dir}/f${n++}.png`}); };
    await frame();
    await hit(page, '[data-parseh-mode="mobile"]');
    await frame();
    await hit(page, '[data-parseh-theme]');
    await frame();
    await hit(page, '[data-parseh-theme]');
    await frame();
    await hit(page, '[data-parseh-mode="browser"]');
    await frame();
    const file = `${OUT}/${FILES['modes-gif']}`;
    await Deno.mkdir(file.replace(/\/[^/]*$/, ''), {recursive: true});
    await run(['magick', '-delay', '130', '-loop', '0', `${dir}/f0.png`, `${dir}/f1.png`, `${dir}/f2.png`, `${dir}/f3.png`,
               '-delay', '220', `${dir}/f4.png`, '-layers', 'Optimize', '-colors', '128', file]);
    saved.push(FILES['modes-gif']);
    console.log('  saved', FILES['modes-gif']);
    await ctx.close();
  },
  async 'dictionary-sheet'() {
    // a phone, the dictionary switched on, a chunk tapped: over a book, and over a video under its pinned picture
    const dir = `${WORK}/sheets`;
    await Deno.mkdir(dir, {recursive: true});
    const ctx = await context(PHONE, {parseh_mode: 'mobile'});
    const book = await openReader(ctx, 'fa');
    await book.waitForSelector('#dictmode:not([hidden])', {state: 'attached', timeout: 15000});
    await gearOpen(book);
    await gearRow(book, 'dictmode').locator('button.pg-switch').tap();
    await gearRow(book, 'hover').locator('button.pg-switch').tap();
    await sleep(300);
    await gearClose(book);
    await book.locator('main .p1 .w').first().evaluate(e => e.scrollIntoView({block: 'center'}));
    await sleep(300);
    await book.locator('main .p1 .w').first().tap();
    await book.waitForFunction(() => !document.getElementById('cloud').hidden, null, {timeout: 8000});
    await hit(book, '#cloud .mkdict');
    await book.waitForSelector('.m-dsheet', {state: 'visible', timeout: 8000});
    await sleep(900);
    await book.screenshot({path: `${dir}/book.png`});
    const video = await openPlayer(ctx);
    await gearOpen(video);
    await gearRow(video, 'dict').locator('button.pg-switch').tap();
    await sleep(300);
    await gearClose(video);
    await video.locator('.seg[data-i="1"] .fa .w').nth(2).tap();
    await video.waitForFunction(() => !document.getElementById('cloud').hidden, null, {timeout: 8000});
    await hit(video, '#cloud .mkdict');
    await video.waitForSelector('.m-dsheet', {state: 'visible', timeout: 8000});
    await sleep(1200);
    await video.screenshot({path: `${dir}/video.png`});
    const file = `${OUT}/${FILES['dictionary-sheet']}`;
    await Deno.mkdir(file.replace(/\/[^/]*$/, ''), {recursive: true});
    await run(['magick', `${dir}/book.png`, '-background', 'white', '-splice', '0x0', '(', '-size', '24x844', 'xc:white', ')',
               `${dir}/video.png`, '+append', file]);
    saved.push(FILES['dictionary-sheet']);
    console.log('  saved', FILES['dictionary-sheet']);
    await ctx.close();
  },
};

try {
  for (const name of Object.keys(PICS)) {
    if (!wanted(name)) continue;
    console.log('\n' + name);
    try { await resetPrefs(); await resetLater(); await PICS[name](); }
    catch (e) { console.log('  FAILED:', e.message.split('\n')[0]); }
  }
} finally {
  await browser.close();
  try { hub.kill('SIGTERM'); } catch (_) {}
  await hub.status.catch(() => {});
  await Deno.remove(WORK, {recursive: true}).catch(() => {});
}
console.log(`\n${saved.length} pictures saved`);

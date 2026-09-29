// SPDX-License-Identifier: GPL-3.0-or-later
import {chromium} from 'npm:playwright-core@1.52.0';
// Run: CHROME_BIN=/path/to/chrome PARSEH_PYTHON=/path/to/python3 deno run --allow-all tests/making.mjs
//      SHOTS=<dir> saves a screenshot of every view it looks at (1280 and 390 px, the three themes)
//      PARSEH_KEEP=1 keeps the temporary tree, to read what was written
//
// A BOOK MADE BY AN AGENT, IN PLACE (a0.4.2, TO-DO §8.40), driven end to end in a real browser
// against a scratch install -- a copy of this checkout that is a whole Parseh of its own
// (tests/making_agent.py scratch), so that nothing the owner has is ever in reach.  The agent is
// a scripted stand-in (tests/making_agent.py) that calls Parseh's real tools with Parseh's real
// Python, batch by batch, while the page is watched.  Every action is a person's: the add page's
// card, its fields and its buttons, the library, the reader's header, sheets and pencil.
//
//  a) THE PAGE, way 3 of /books/add/: no terminal left in it (no script to copy, no setup, no
//     return); the original is a file picker; Learn from is "none"; the box about the person's own
//     books is off; the folder's button says why it cannot be pressed; the instructions shown are
//     what the copy button copies, to the letter, and are what the folder gets; making the folder
//     writes the whole folder, on this computer, from an uploaded file -- and the page says where,
//     copies the path, opens the folder (the file manager stood in for) and says what to tell the
//     agent; a second press names the slug that is taken
//  b) THE LIBRARY: the book is there at once, marked being made, and its card moves as the agent
//     works, without a reload
//  c) THE READER, while the agent works: a button in the header and a panel that moves by itself
//     (source recovered, chapter table, batch N of M, the tools' words); the page is said to be
//     older than the newest batch, and look at it now brings it (the panel comes back open); what
//     is still to come is said under the last batch; the PDF of these chapters is made beside the
//     book and never as main.pdf
//  d) NO EDITING WHILE IT IS MADE: the pencil says why, the chunk sheet shows the chunk and shuts
//     what writes it, offers ask about this chunk -- written to ASKS.md with the chunk's address
//     and text -- and the server refuses the doors whatever the page does
//  e) STEERING: what to change from now on, written to ASKS.md; the agent reads it before its next
//     batch and says in NOTES.md what it did; Parseh updated during the making is said
//  f) ANOTHER DEVICE: on a phone (390 px, the mobile interface) the panel is read and an ask
//     written; from a device that is not the computer the folder and Finish are refused, in the
//     table's words, and the panel says so where the buttons would be
//  g) NO SH (Windows): the PDF of these chapters is said not to be available and the reader is;
//     look at it now still builds it
//  h) FINISH: a paragraph that no longer reproduces its source stops it, in words, and the making
//     goes on; then, both clean, the making ends: the book is an ordinary book (its pencil edits
//     the .tex, its card says nothing), its bundle carries the original and annot/ and none of the
//     agent's files, and the format number is 3
//  i) A RIGHT-TO-LEFT BOOK: Persian, made from the page (its title box reads right to left, the folder
//     is on the Persian shelf, book.json keeps the letters), worked by the stand-in, watched in the
//     panel, its chunk shut with the ask offered, and an ask in Persian reaches ASKS.md as written
//  j) and last: no page threw, and the owner's books/ and config/ are as they were
// and every view it looks at (1280 and 390 px, light and dark) is measured too: the page does not
// scroll sideways and the making panel lies inside the window
const root = await Deno.realPath(new URL('..', import.meta.url));
Deno.chdir(root);
const PY = Deno.env.get('PARSEH_PYTHON') || 'python3';
const SHOTS = Deno.env.get('SHOTS') || '';
const TMP = await Deno.makeTempDir({prefix: 'parseh-making-'});
const INSTALL = TMP + '/install';
const td = new TextDecoder();
const sleep = ms => new Promise(r => setTimeout(r, ms));
let passed = 0;
const assert = (v, m) => { if (!v) throw Error('FAIL: ' + m); passed++; console.log('  ok', m); };
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const eq = (got, want, m) => assert(same(got, want),
  m + (same(got, want) ? '' : ': got ' + JSON.stringify(got) + ' want ' + JSON.stringify(want)));

async function run(cmd, args, opt = {}) {
  const o = await new Deno.Command(cmd, {args, cwd: root, stdout: 'piped', stderr: 'piped', ...opt}).output();
  return {code: o.code, out: td.decode(o.stdout), err: td.decode(o.stderr)};
}
async function py(args) {
  const r = await run(PY, args);
  if (r.code) throw Error(args.join(' ') + ' -> ' + (r.err || r.out));
  return r.out.trim();
}
const agent = (...args) => py(['tests/making_agent.py', ...args]);
function freePort() {
  const l = Deno.listen({hostname: '127.0.0.1', port: 0});
  const p = l.addr.port;
  l.close();
  return p;
}
function drain(stream, sink) {
  (async () => {
    const r = stream.pipeThrough(new TextDecoderStream()).getReader();
    for (;;) { const {value, done} = await r.read(); if (done) break; sink.push(value); }
  })();
}
// a wait for some text that a page in the middle of a reload (no <main> yet, no panel yet) does not break
const waitText = (pg, sel, re, timeout = 30000) => pg.waitForFunction(
  ([s, src, fl]) => { const e = document.querySelector(s); return !!e && new RegExp(src, fl).test(e.textContent); },
  [sel, re.source, re.flags], {timeout});
const waitNoText = (pg, sel, re, timeout = 30000) => pg.waitForFunction(
  ([s, src, fl]) => { const e = document.querySelector(s); return !!e && !new RegExp(src, fl).test(e.textContent); },
  [sel, re.source, re.flags], {timeout});
// the panel comes back open after a reload when it was open: give that its moment, and open it by the
// button only if it is not
async function openPanel(pg, layout = 'browser') {
  await pg.waitForSelector(`.mk-btn[data-layout=${layout}]`);
  await pg.evaluate(() => window.ParsehMaking.refresh());
  await sleep(300);
  if (!(await pg.$('#mkbox:not([hidden])'))) await pg.click(`.mk-btn[data-layout=${layout}]`);
  await pg.waitForSelector('#mkbox:not([hidden])');
}
// a view in the widths and themes the work is looked at in: 1280 and 390 px, light and dark.
// In each of them nothing this work draws may lie past the window's edge -- the making button,
// the panel, the words under the last batch, the locked chunk sheet with its note and its ask --
// and the library and the add page, which are wholly this work's, must not scroll sideways
// either: a phone's screen is the one nobody can resize.  A reader's own layout is not what this
// suite is about, so there only what the making adds is measured.  The screenshots are taken
// only when SHOTS says where to put them.
async function views(pg, name, {full = false} = {}) {
  // a tab that is not in front is not drawn, and a screenshot of it waits for a frame that never comes
  await pg.bringToFront();
  const was = pg.viewportSize();
  for (const [w, h] of [[1280, 900], [390, 844]])
    for (const theme of ['light', 'dark']) {
      await pg.setViewportSize({width: w, height: h});
      await pg.evaluate(t => Parseh.theme.set(t), theme);
      await sleep(350);
      const fit = await pg.evaluate(() => {
        const de = document.documentElement, cw = de.clientWidth, past = [];
        const whole = !/\/reader\//.test(location.pathname);
        for (const sel of ['.mk-btn', '#mkbox', '#mktocome', '#chbox', '#chbox .mk-chnote', '#chbox .mk-ask'])
          for (const e of document.querySelectorAll(sel)) {
            const r = e.getBoundingClientRect(), st = getComputedStyle(e);
            if (!r.width || st.visibility === 'hidden' || st.display === 'none') continue;
            if (r.right > cw + 1 || r.left < -1) past.push(sel + ' ' + Math.round(r.left) + '..' + Math.round(r.right));
          }
        if (whole && de.scrollWidth > cw + 1) {
          past.push('the page is ' + de.scrollWidth + ' wide');
          for (const e of document.querySelectorAll('body *')) {
            const r = e.getBoundingClientRect(), st = getComputedStyle(e);
            if (r.width && r.right > cw + 1 && st.position !== 'fixed' && st.visibility !== 'hidden' && st.display !== 'none')
              past.push(e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') + ' to ' + Math.round(r.right));
            if (past.length > 5) break;
          }
        }
        return {cw, past};
      });
      assert(!fit.past.length, `${name} at ${w} px, ${theme}: nothing lies past the window's edge (${fit.cw} wide` +
             `${fit.past.length ? '; past it: ' + fit.past.join(', ') : ''})`);
      if (!SHOTS) continue;
      try {
        await pg.screenshot({path: `${SHOTS}/${name}-${w}-${theme}.png`, fullPage: full, timeout: 20000});
      } catch (e) {
        console.log('  screenshot', name, w, theme, 'failed:', e.message.split('\n')[0],
                    JSON.stringify(await pg.evaluate(() => [document.readyState, Math.round(performance.now()), document.hidden]).catch(x => String(x))));
        throw e;
      }
    }
  await pg.evaluate(() => Parseh.theme.set('light'));
  await pg.setViewportSize(was);
  await sleep(250);
}
const shot = async (page, name) => { if (SHOTS) { await page.bringToFront(); await page.screenshot({path: `${SHOTS}/${name}.png`}); } };
async function exists(p) { try { await Deno.stat(p); return true; } catch { return false; } }
async function tree(dir) {
  const out = [];
  for await (const e of Deno.readDir(dir)) {
    if (e.isDirectory) for (const f of await tree(dir + '/' + e.name)) out.push(e.name + '/' + f);
    else out.push(e.name);
  }
  return out.sort();
}

// what is the owner's, which nothing here may touch: their digests now, compared at the end
const OWN = String.raw`
import hashlib, json, os, sys
out = {}
for top in ('config', 'books'):
    for d, _, files in os.walk(top):
        for f in files:
            p = os.path.join(d, f)
            out[p] = hashlib.md5(open(p, 'rb').read()).hexdigest()
print(json.dumps(out, sort_keys=True))
`;
const ownBefore = await py(['-c', OWN]);
// the PDF of a few chapters and the full build are LaTeX's: where there is none the suite says so and
// checks what such a machine does instead (Finish builds the reader and leaves the PDF)
const HAS_TEX = (await run('which', ['lualatex'])).code === 0;
if (!HAS_TEX) console.log('  note: no lualatex on this machine -- the draft PDF and the full build are not driven');

/* ---------------- the scratch install, the original, the servers ---------------- */
await agent('scratch', INSTALL);
const MODEL = root + '/tests/fixtures/books/english/mini-en';
await agent('original', MODEL, TMP + '/the-clock.txt');
const ORIGINAL_TEXT = await Deno.readTextFile(TMP + '/the-clock.txt');
assert(ORIGINAL_TEXT.trim().split(/\n\s*\n/).length === 2, 'the original is two paragraphs');
const BOOK = INSTALL + '/books/english/the-clock';

const logs = [];
const servers = [];
async function serve(extra = [], env = {}) {
  const port = freePort();
  const p = new Deno.Command(PY, {
    args: ['tests/making_agent.py', 'serve', INSTALL, String(port), ...extra], cwd: root,
    env: {PARSEH_PYTHON: PY, HOME: Deno.env.get('HOME') || '', TMPDIR: Deno.env.get('TMPDIR') || '/tmp',
          PATH: Deno.env.get('PATH') || '', ...env},
    clearEnv: true, stdout: 'piped', stderr: 'piped'}).spawn();
  drain(p.stdout, logs); drain(p.stderr, logs);
  servers.push(p);
  for (let i = 0; i < 150; i++) {
    try { const r = await fetch(`http://127.0.0.1:${port}/__activity`); await r.body?.cancel(); if (r.ok) return `http://127.0.0.1:${port}`; }
    catch { /* not yet */ }
    await sleep(200);
  }
  throw Error('the server did not come up: ' + logs.join('').slice(-800));
}
const B = await serve();                                   // this computer
const PHONE = await serve(['--phone']);                    // a phone let in over the Wi-Fi
const NOSH = await serve([], {PATH: '/nonexistent'});      // a machine with no sh: Windows

/* ---------------- the browser ---------------- */
const errors = [];
const browser = await chromium.launch({executablePath: Deno.env.get('CHROME_BIN'), headless: true});
async function context(base, opt = {}) {
  const c = await browser.newContext({viewport: {width: 1280, height: 900}, ...opt});
  await c.grantPermissions(['clipboard-read', 'clipboard-write'], {origin: base});
  return c;
}
function watch(page, label) {
  page.on('pageerror', e => errors.push({label, text: 'pageerror: ' + e.message, url: ''}));
  page.on('console', m => {
    const u = m.location().url || '';
    // the reader asks for a few optional files a temporary book has none of
    if (m.type() === 'error' && !/favicon|\/timings\.json|\/mt\//.test(u))
      errors.push({label, text: m.text(), url: u});
  });
}
// the refusals this suite asks for on purpose, each of which the browser logs as an error: the lock on
// editing, the doors of a phone that are the computer's, the draft on a machine with no shell.  Each
// must have happened -- a refusal that never came is a lock that was never tried
const DELIBERATE = [['computer', 409, /\/reader\/__edit\/chunk$/],
  ['phone', 403, /\/__making\/finish$/], ['phone', 403, /\/__making\/open$/],
  ['phone', 403, /\/books\/__make\?/], ['phone', 403, /\/books\/__making\/instructions$/],
  ['no sh', 409, /\/reader\/__build$/]];
const clip = page => page.evaluate(() => navigator.clipboard.readText());
const inView = async (page, sel) => page.$eval(sel, e => {
  const r = e.getBoundingClientRect();
  return r.width > 0 && r.height > 0 && r.left >= -1 && r.top >= -1 &&
         r.right <= innerWidth + 1 && r.bottom <= innerHeight + 1;
});
// what is drawn at the middle of a control is the control (or something in it): nothing lies over it
const onTop = (page, sel) => page.$eval(sel, e => {
  const r = e.getBoundingClientRect();
  const at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
  return !!at && (at === e || e.contains(at));
});
let failure = null;
try {
const ctx = await context(B);
const page = await ctx.newPage();
watch(page, 'computer');

/* ================= a) the page ================= */
console.log('a) the add page, way 3');
await page.goto(B + '/books/add/');
await page.click('.path[data-path="llm"]');
await page.waitForSelector('#lane-llm:not([hidden])');
const said = await page.evaluate(() => document.body.innerText);
for (const gone of [/terminal/i, /conda/i, /setup script/i, /return script/i, /PROMPT\.md/, /copy the setup/i,
                    /bring it back/i, /working folder/i])
  assert(!gone.test(said), 'no ' + gone + ' on the page');
assert(/Let an agent make it/.test(said), 'the card is the agent\'s');
eq(await page.$eval('#original', e => [e.type, e.accept]), ['file', '.pdf,.epub,.txt,application/pdf,application/epub+zip,text/plain'],
   'the original is a file picker, not a path typed on the server');
eq(await page.$eval('#ref', e => [e.value, e.options.length, e.options[0].textContent]), ['', 1, 'none'],
   'Learn from is "none", and there is no finished book to pick');
eq(await page.$eval('#examples', e => e.checked), false, 'the box about my own books is off');
assert(await page.$eval('#mkfolder', b => b.disabled), 'the folder\'s button cannot be pressed at first');
eq(await page.$eval('#mkfolder', b => b.title), 'the title comes first', '... and says why');
await page.selectOption('#lang', 'en');
await page.fill('#title', 'The Clock');
await page.fill('#title_latin', 'The Clock');
await page.fill('#author', 'a fable');
await page.fill('#author_latin', 'a fable');
eq(await page.$eval('#mkfolder', b => b.title), 'choose the original first', '... and then what is next');
await page.setInputFiles('#original', TMP + '/the-clock.txt');
await page.waitForFunction(() => !document.querySelector('#mkfolder').disabled);
assert(/the-clock\.txt, 1 kB/.test(await page.$eval('#originalnote', e => e.textContent)), 'the chosen file is named, with its size');
await page.fill('#pages', 'nine');
assert(/ignored/.test(await page.$eval('#pagesnote', e => e.textContent)), 'a page range that is no range is said to be ignored');
await page.fill('#pages', '');
// the instructions: what the row shows is what it copies is what the folder gets
await page.click('#ishow summary');
await page.waitForFunction(() => document.querySelector('#itext').textContent.length > 500);
const shown = await page.$eval('#itext', e => e.textContent);
await page.click('#icopy');
await sleep(400);
eq(await clip(page), shown, 'the instructions copied are exactly the ones shown');
assert(shown.includes(INSTALL + '/books/english/the-clock') && shown.includes(INSTALL + '/lib') &&
       /Write only inside this folder/.test(shown) && /ASKS\.md/.test(shown) && /making\.json/.test(shown),
       'they name this folder, this Parseh\'s tools, ASKS.md and making.json by their full paths');
assert(/^\d[\d,]* characters$/.test(await page.$eval('#ilen', e => e.textContent)), 'and say how long they are');
await views(page, 'C-add', {full: true});
// make the folder
await page.click('#mkfolder');
await page.waitForSelector('#mkcopy', {timeout: 60000});
const made = await page.$eval('.bigpath', e => e.textContent);
eq(made, BOOK, 'the page says where the folder is');
assert(/read AGENTS\.md and begin/.test(await page.$eval('#mkresult', e => e.textContent)), '... and what to tell the agent');
assert(!/start(s|ed) (an|the) agent/i.test((await page.$eval('#mkresult', e => e.textContent)).replace(/does not start an agent/, '')),
       'Parseh starts no agent and names none');
await page.click('#mkcopy');
await sleep(300);
eq(await clip(page), BOOK, 'copy the path copies the path');
await page.click('#mkopen');
for (let i = 0; i < 30 && !(await exists(INSTALL + '/opened.txt')); i++) await sleep(100);
eq((await Deno.readTextFile(INSTALL + '/opened.txt')).trim(), BOOK, 'open the folder asks the system\'s file manager for it');
eq(await tree(BOOK), ['AGENTS.md', 'ASKS.md', 'CLAUDE.md', 'NOTES.md', 'annot/', 'book.json', 'main.tex',
                      'making.json', 'original/the-clock.txt', 'reader/index.html', 'source/paras/'].filter(n => !n.endsWith('/')),
   'the folder holds what the brief says, and the reader');
eq(await Deno.readTextFile(BOOK + '/original/the-clock.txt'), ORIGINAL_TEXT, 'the original is the uploaded file, byte for byte');
eq((await Deno.stat(BOOK + '/ASKS.md')).size, 0, 'ASKS.md is empty');
const making0 = JSON.parse(await Deno.readTextFile(BOOK + '/making.json'));
eq([making0.state, making0.stage], ['making', 'folder'], 'making.json says it is being made');
assert(!await exists(INSTALL + '/others'), 'nothing was put in others/');
eq(await Deno.readTextFile(BOOK + '/AGENTS.md'), shown, 'the folder\'s AGENTS.md is the text the page showed');
assert(await page.$eval('#mkfolder', b => b.disabled) &&
       /a book is already at books\/english\/the-clock\//.test(await page.$eval('#mkfwhy', e => e.textContent)),
       'a second press is shut and names the slug that is taken');
await views(page, 'C-add-made', {full: true});

/* ================= b) the library ================= */
console.log('b) the library');
const lib = await ctx.newPage();
watch(lib, 'library');
await lib.goto(B + '/books/');
await lib.waitForSelector('a.book[data-making]');
eq(await lib.$eval('[data-making-tag]', e => e.textContent.replace(/ · (just now|\d+ minutes? ago)$/, '')),
   'being made · not started yet', 'the book is on the library at once, marked being made');
await views(lib, 'C-library');
console.log('c) the reader, while the agent works');
const url = B + '/books/english/the-clock/reader/';
await page.goto(url);
await page.waitForSelector('.mk-btn[data-layout=browser]');
assert(await inView(page, '.mk-btn[data-layout=browser]') && await onTop(page, '.mk-btn[data-layout=browser]'),
       'the making button is in the header, in the window, and nothing lies over it');
eq(await page.$eval('.mk-btn[data-layout=browser] .mk-txt', e => e.textContent), 'being made · not started yet',
   'it says where the making stands');
assert(/Nothing to read yet/.test(await page.$eval('#mktocome', e => e.textContent)), 'a book with no chapter says so, and does not fail');
assert(await page.$eval('#bookinfo', b => b.disabled) && await page.$eval('#rgn', b => b.disabled),
       'book info and gloss with an LLM are off, each with its reason');
assert(/being made by an agent/.test(await page.$eval('#rgn', b => b.title)), '... in its title');
await page.click('.mk-btn[data-layout=browser]');
await page.waitForSelector('#mkbox:not([hidden])');
assert(await inView(page, '#mkbox') && await onTop(page, '#mkbox h2'), 'the panel is in the window and on top');
await views(page, 'C-panel-not-started');
// the library moves by itself while the agent works
assert(/source recovered/.test(await agent('step', BOOK, MODEL)), 'the stand-in recovers the source');
await waitText(lib, '[data-making-tag]', /source recovered/, 20000);
assert(true, 'the library card moved without a reload');
await waitText(page, '#mkbox .mk-where', /source recovered/, 20000);
assert(true, 'the panel moved without a reload');
assert(/chapter table/.test(await agent('step', BOOK, MODEL)), 'the chapter table is written');
await waitText(page, '#mkbox', /Still to come: 1, 2/, 20000);
assert(/The chapter table: 1 \(1 paragraph\), 2 \(1 paragraph\)/.test(await page.$eval('#mkbox', e => e.textContent)),
       'the chapters the agent decided on are said, and which are still to come');
assert(/batch 1 of 2: chapter 1 assembled/.test(await agent('step', BOOK, MODEL)), 'batch 1 is assembled');
await waitText(page, '#mkbox .mk-where', /batch 2 of 2/, 20000);
const checks = await page.$$eval('#mkbox ul li', els => els.map(e => e.textContent));
assert(checks.includes('check_batch: 0 errors') && checks.includes('assemble: ALL PARAGRAPHS CLEAN'), 'the tools\' own words are shown');
assert(/has written more since this page was built/.test(await page.$eval('#mkbox', e => e.textContent)) &&
       /More is written than this page shows/.test(await page.$eval('#mktocome', e => e.textContent)),
       'the page is said to be older than the newest batch, in the panel and under the text');
assert(!await page.$('.row[data-c]'), '... and it is: no chunk is drawn yet');
await views(page, 'C-panel-batch');
// look at it now: the reader is rebuilt, the page reloads, the panel comes back open
await page.click('#mkbox button:has-text("look at it now")');
await page.waitForFunction(() => document.querySelector('.row[data-c]'), null, {timeout: 90000});
await page.waitForFunction(() => document.querySelector('#mkbox') && !document.querySelector('#mkbox').hidden, null, {timeout: 20000});
assert(/The old man wound the clock/.test(await page.$eval('main', e => e.textContent)), 'look at it now shows the new batch');
await waitText(page, '#mktocome', /Still to come:\s*chapter 2/);
assert(true, 'and says which chapter is still to come');
assert(!/has written more since/.test(await page.$eval('#mkbox', e => e.textContent)), 'the page is current again');
await views(page, 'C-reader-batch-1');

/* ================= the draft PDF ================= */
console.log('   the PDF of these chapters');
assert(await page.$eval('#mkbox button:has-text("the PDF of these chapters")', b => !b.hidden), 'the draft is offered where there is a shell');
if (HAS_TEX) {
  await page.click('#mkbox button:has-text("the PDF of these chapters")');
  await waitText(page, '#mkbox', /open the PDF/, 240000);
  assert(await exists(BOOK + '/frankdraft.pdf'), 'the draft is frankdraft.pdf beside the book');
  assert(!await exists(BOOK + '/main.pdf'), '... never main.pdf: the two cannot collide');
  const pdf = await page.$eval('#mkbox a.mk-a', a => a.href);
  const got = await fetch(pdf);
  eq([got.status, got.headers.get('content-type'), td.decode((await got.arrayBuffer()).slice(0, 5))], [200, 'application/pdf', '%PDF-'],
     'the PDF is served and is one');
  await views(page, 'C-panel-draft');
}

/* ================= d) no editing ================= */
console.log('d) no editing while it is made');
await page.click('#mkbox button.mk-x');
await page.hover('.row[data-c="0"]');
await page.waitForSelector('#chpen:not([hidden])');
assert(/editing is off while an agent makes this book/.test(await page.$eval('#chpen', b => b.title)), 'the pencil says why');
const texBefore = await Deno.readTextFile(BOOK + '/ch1.tex');
await page.click('#chpen');
await page.waitForSelector('#chbox:not([hidden])');
await page.waitForSelector('#chbox .mk-ask');
eq(await page.$eval('#chsave', b => getComputedStyle(b).display), 'none', 'save chunk is not offered');
eq(await page.$$eval('#chdel, #chundo, #chsplit, #chjoin, #chjoinp, #chfree, #chrgn, #chins',
                     els => els.map(e => getComputedStyle(e.closest('.arow') || e).display !== 'none' && getComputedStyle(e).display !== 'none')),
   [false, false, false, false, false, false, false, false], 'nor deleting, dividing, freeing, the LLM row or the macro buttons');
eq(await page.$$eval('#chfa, #chtr, #chvoc, #chen', els => els.map(e => e.readOnly)), [true, true, true, true],
   'the boxes show the chunk and cannot be typed in');
assert(/erased by its next batch/.test(await page.$eval('#chbox .mk-chnote', e => e.textContent)), 'the sheet says why, in words');
assert(await inView(page, '#mkchask') && await onTop(page, '#mkchask'), 'ask about this chunk is in the window and nothing lies over it');
assert(await onTop(page, '#chsrc'), 'the dictionary work (sources) is still there');
await views(page, 'C-chunk-sheet');
await page.fill('#chbox .mk-ask textarea', 'This meaning is too free: make it literal.');
await page.click('#mkchask');
await waitText(page, '#chbox .mk-said', /written to ASKS\.md/);
const asks1 = await Deno.readTextFile(BOOK + '/ASKS.md');
assert(/^## \d{4}-\d\d-\d\d \d\d:\d\d — about a chunk\n\nchapter 1, paragraph 1, subparagraph 1\.1, chunk 0:\n> The old man\n\nThis meaning is too free: make it literal\.\n$/.test(asks1),
       'the ask carries the chunk\'s address and text and the line: ' + JSON.stringify(asks1));
// the server refuses whatever the page does
const refused = await page.evaluate(async () => {
  const r = await fetch('__edit/chunk', {method: 'POST', headers: {'Content-Type': 'application/json'},
                                          body: JSON.stringify({index: 0, fields: {en: 'changed by hand'}})});
  return [r.status, (await r.json())];
});
eq([refused[0], refused[1].making], [409, true], 'the door refuses an edit');
assert(/erased by its next batch/.test(refused[1].error), '... in words');
eq(await Deno.readTextFile(BOOK + '/ch1.tex'), texBefore, 'and the .tex is exactly as the agent left it');
await page.keyboard.press('Escape');
await page.waitForFunction(() => document.querySelector('#chbox').hidden);

/* ================= e) steering ================= */
console.log('e) steering the agent');
await page.click('.mk-btn[data-layout=browser]');
await page.waitForSelector('#mkbox:not([hidden])');
await page.fill('#mkbox textarea', 'Please write the meanings in capitals from now on.');
await page.click('#mkbox button:has-text("ask")');
await waitText(page, '#mkbox', /written to ASKS\.md at/);
const asks2 = await Deno.readTextFile(BOOK + '/ASKS.md');
assert(/— what to change from now on\n\nPlease write the meanings in capitals from now on\.\n$/.test(asks2), 'the ask is a dated entry in ASKS.md');
await waitText(page, '#mkbox', /2 asks written so far/, 20000);
assert(true, 'the panel counts the asks');
assert(/batch 2 of 2: chapter 2 assembled/.test(await agent('step', BOOK, MODEL)), 'the stand-in does its next batch');
const notes = await Deno.readTextFile(BOOK + '/NOTES.md');
assert(/ASKS\.md, [^\n]*about a chunk[^\n]*noted, and left/.test(notes) && /Please write the meanings in capitals[^\n]*done from batch 2 on/.test(notes),
       'it read ASKS.md before the batch, and NOTES.md says what it did about each entry');
assert(/\\ch\{\}\{A child came in\}\{[^}]*\}\{[^\n]*\}\{A CHILD CAME IN\}/.test(await Deno.readTextFile(BOOK + '/ch2.tex')),
       'the next batch is in capitals, as asked');
assert(!/THE OLD MAN/.test(await Deno.readTextFile(BOOK + '/ch1.tex')), 'and the batch already checked is not touched');
await page.click('#mkbox button:has-text("look at it now")');
await waitText(page, 'main', /A CHILD CAME IN/, 90000);
await waitText(page, '#mktocome', /Still being made/);
assert(true, 'with every chapter of the table in, it says it is still being made');
// Parseh updated during the making
const mk = JSON.parse(await Deno.readTextFile(BOOK + '/making.json'));
await Deno.writeTextFile(BOOK + '/making.json', JSON.stringify({...mk, parseh: 'a0.1.0'}, null, 2));
await waitText(page, '#mkbox', /Parseh was updated during the making/, 20000);
assert(/began under a0\.1\.0 and this is a0\./.test(await page.$eval('#mkbox .mk-note', e => e.textContent)), 'Parseh updated during the making is said, with both versions');
await Deno.writeTextFile(BOOK + '/making.json', JSON.stringify(mk, null, 2));
// a file half written by the agent is said, and the book is still being made
await Deno.writeTextFile(BOOK + '/making.json', '{"state": "maki');
await waitText(page, '#mkbox', /cannot be read just now/, 20000);
assert(await page.$eval('#bookinfo', b => b.disabled), 'a half-written making.json does not lift the lock');
await Deno.writeTextFile(BOOK + '/making.json', JSON.stringify(mk, null, 2));
await waitNoText(page, '#mkbox', /cannot be read just now/, 20000);

/* ================= the themes and the widths ================= */
console.log('   themes and widths');
for (const theme of ['dark', 'sepia']) {
  await page.evaluate(t => Parseh.theme.set(t), theme);
  await sleep(300);
  assert(await inView(page, '#mkbox') && await onTop(page, '#mkbox h2'), 'the panel in the ' + theme + ' theme is in the window');
  await shot(page, 'C-panel-batch-2-1280-' + theme);
}
await page.evaluate(() => Parseh.theme.set('light'));
await page.setViewportSize({width: 390, height: 844});
await sleep(400);
assert(await inView(page, '#mkbox'), 'the panel fits a 390 px window (the browser interface)');
await shot(page, 'C-panel-390-browser-light');
await page.setViewportSize({width: 1280, height: 900});

/* ================= f) another device ================= */
console.log('f) a phone, and a device that is not the computer');
const pctx = await context(PHONE, {viewport: {width: 390, height: 844}, isMobile: true, hasTouch: true});
await pctx.addInitScript(() => { try { localStorage.setItem('parseh_mode', 'mobile'); } catch (e) { /* refused */ } });
const phone = await pctx.newPage();
watch(phone, 'phone');
await phone.goto(PHONE + '/books/english/the-clock/reader/');
await phone.waitForSelector('.mk-btn[data-layout=mobile]');
assert(await phone.$eval('.mk-btn[data-layout=mobile]', b => getComputedStyle(b).display !== 'none') &&
       await phone.$eval('.mk-btn[data-layout=browser]', b => getComputedStyle(b).display === 'none'),
       'in the mobile interface the panel\'s button is the mobile one');
await phone.click('.mk-btn[data-layout=mobile]');
await phone.waitForSelector('#mkbox:not([hidden])');
assert(await inView(phone, '#mkbox') && await onTop(phone, '#mkbox h2'), 'the panel fits the phone and is on top');
const ptext = await phone.$eval('#mkbox', e => e.textContent);
assert(/all batches in|batch 2 of 2/.test(ptext) && /check_batch: 0 errors/.test(ptext), 'the phone reads where the making stands');
assert(!await phone.$('#mkbox code.mk-path') && !await phone.$('#mkbox button:has-text("open the folder")'),
       'the computer\'s own path is not shown to it, and it is offered no folder to open');
assert(/on the computer Parseh runs on/.test(await phone.$eval('#mkbox', e => e.textContent)) &&
       (await phone.$$('#mkbox .mk-lock')).length === 2, 'the folder and Finish each say they are the computer\'s');
assert(!await phone.$('#mkbox button:has-text("finish")'), 'and no Finish button is drawn');
await shot(phone, 'C-panel-phone-390-light');
await phone.fill('#mkbox textarea', 'From the phone: keep the vocabulary short.');
await phone.click('#mkbox button:has-text("ask")');
await waitText(phone, '#mkbox', /written to ASKS\.md at/);
assert(/From the phone: keep the vocabulary short\./.test(await Deno.readTextFile(BOOK + '/ASKS.md')), 'a phone may write an ask');
const forbidden = await phone.evaluate(async () => {
  const out = {};
  for (const [name, url, opt] of [
      ['finish', 'the-clock/__making/finish', {method: 'POST', body: '{}'}],
      ['open', 'the-clock/__making/open', {method: 'POST', body: '{}'}],
      ['make', '/books/__make?name=a.txt&book=%7B%7D', {method: 'POST', body: 'x'}],
      ['instructions', '/books/__making/instructions', {method: 'POST', body: '{}'}]]) {
    const r = await fetch(url.startsWith('/') ? url : '/books/english/' + url,
                          {headers: {'Content-Type': 'application/json'}, ...opt});
    out[name] = [r.status, (await r.json()).error];
  }
  return out;
});
for (const k of ['finish', 'open', 'make', 'instructions'])
  assert(forbidden[k][0] === 403 && /changed on the computer .* runs on and nowhere else, because it changes what Parseh will run/.test(forbidden[k][1]),
         k + ' is refused a phone, in the table\'s words');
assert(await exists(BOOK + '/making.json') && JSON.parse(await Deno.readTextFile(BOOK + '/making.json')).state === 'making',
       'and nothing changed');
const phoneAdd = await ctx.newPage();
await phoneAdd.goto(PHONE + '/books/add/?path=llm');
await phoneAdd.waitForSelector('#lane-llm:not([hidden])');
assert(await phoneAdd.$eval('#mklock', e => !e.hidden && /changed on the computer/.test(e.textContent)) &&
       await phoneAdd.$eval('#mkfolder', b => b.disabled), 'the add page on a phone shows the button shut and the reason');
await phoneAdd.close();
await pctx.close();

/* ================= g) a machine with no sh ================= */
console.log('g) no sh: the PDF of these chapters is not available, the reader is');
const nctx = await context(NOSH);
const nosh = await nctx.newPage();
watch(nosh, 'no sh');
await nosh.goto(NOSH + '/books/english/the-clock/reader/');
await nosh.waitForSelector('.mk-btn[data-layout=browser]');
await nosh.click('.mk-btn[data-layout=browser]');
await nosh.waitForSelector('#mkbox:not([hidden])');
assert(await nosh.$eval('#mkbox button:has-text("the PDF of these chapters")', b => b.hidden), 'the draft button is not drawn');
assert(/not available on this computer, which has no shell to make it\. The reader is available/.test(await nosh.$eval('#mkbox', e => e.textContent)),
       'it is said plainly not to be available, and that the reader is');
await shot(nosh, 'C-panel-no-sh-1280-light');
const rs = await nosh.evaluate(async () => {
  const r = await fetch('__build', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({what: 'draft'})});
  return [r.status, (await r.json()).error];
});
eq(rs[0], 409, 'the door refuses the draft too');
assert(/not available on this computer/.test(rs[1]), '... in the same words');
// the reader is what such a machine can build: made stale by the agent, then brought by look at it now
await Deno.writeTextFile(BOOK + '/ch2.tex', (await Deno.readTextFile(BOOK + '/ch2.tex')) + '% the agent touched this batch\n');
await waitText(nosh, '#mkbox', /has written more since this page was built/, 20000);
const back = nosh.waitForNavigation({timeout: 180000});
await nosh.click('#mkbox button:has-text("look at it now")');
await back;
await nosh.waitForFunction(() => document.querySelector('#mkbox') && !document.querySelector('#mkbox').hidden, null, {timeout: 20000});
assert(!/has written more since/.test(await nosh.$eval('#mkbox', e => e.textContent)), 'look at it now builds the reader without sh, all the same');
await nctx.close();

/* ================= h) finish ================= */
console.log('h) finish');
assert(/final/.test(await agent('step', BOOK, MODEL)), 'the stand-in checks everything and says every batch is in');
await page.reload();
await openPanel(page);
await waitText(page, '#mkbox .mk-where', /all batches in/, 20000);
// a paragraph that no longer reproduces its source stops it
const paraFile = BOOK + '/source/paras/ch1_p00.txt';
const paraWas = await Deno.readTextFile(paraFile);
await Deno.writeTextFile(paraFile, paraWas.trim().replace('old man', 'old men') + '\n');
await page.click('#mkbox button:has-text("finish…")');
await waitText(page, '#mkbox', /Has the agent stopped\?/);
await shot(page, 'C-finish-question-1280-light');
await page.click('#mkbox button:has-text("not yet")');
assert(!/Has the agent stopped\?/.test(await page.$eval('#mkbox', e => e.textContent)), '"not yet" takes the question away');
await page.click('#mkbox button:has-text("finish…")');
await page.click('#mkbox button:has-text("yes, finish now")');
await waitText(page, '#mkbox', /not finished/, 120000);
const fin = await page.$eval('#mkbox', e => e.textContent);
assert(/1 paragraph does not reproduce its source/.test(fin) && /chapter 1 paragraph 1 does not reproduce its source \(it differs at character \d+\)/.test(fin),
       'a paragraph that does not reproduce its source stops Finish, and says which: ' + fin.slice(-400));
assert(/put what is said above right, then finish again/.test(fin), '... and what to do');
eq(JSON.parse(await Deno.readTextFile(BOOK + '/making.json')).state, 'making', 'the making goes on');
assert(await page.$eval('#bookinfo', b => b.disabled), 'and the reader still does not edit');
await views(page, 'C-finish-refused');
await Deno.writeTextFile(paraFile, paraWas);
await page.click('#mkbox button:has-text("finish…")');
await page.click('#mkbox button:has-text("yes, finish now")');
// both clean: the making ends and the page is an ordinary book again
await page.waitForFunction(() => !document.querySelector('.mk-btn'), null, {timeout: 400000});
eq(JSON.parse(await Deno.readTextFile(BOOK + '/making.json')).state, 'finished', 'making.json says finished');
assert(/— finished\n\nThe person finished this book from Parseh\. Stop:/.test(await Deno.readTextFile(BOOK + '/ASKS.md')),
       'a running agent is told to stop, in the file it reads before every batch');
assert(/stop: the book is finished|finished: the person ended the making/.test(await agent('step', BOOK, MODEL)), 'the stand-in reads it and stops');
assert(HAS_TEX ? await exists(BOOK + '/main.pdf') : !await exists(BOOK + '/main.pdf'),
       HAS_TEX ? 'the full build ran: main.pdf is there' : 'no TeX: the reader was built and the PDF left');
assert(await exists(BOOK + '/annot/ch1_p00.json') && await exists(BOOK + '/original/the-clock.txt'), 'annot/ stays as the record, and the original with it');
await page.waitForSelector('.row[data-c]');
eq(await page.$$eval('.mk-btn, #mkbox, #mktocome', e => e.length), 0, 'no making button, no panel, no still-to-come');
assert(!await page.$eval('#bookinfo', b => b.disabled) && !await page.$eval('#rgn', b => b.disabled), 'book info and gloss with an LLM work again');
await lib.reload();
assert(!await lib.$('[data-making-tag]'), 'the library card says nothing of being made');
// the reader's doors edit the .tex now
await page.hover('.row[data-c="0"]');
await page.waitForSelector('#chpen:not([hidden])');
await page.click('#chpen');
await page.waitForSelector('#chbox:not([hidden])');
assert(await page.$eval('#chsave', b => getComputedStyle(b).display !== 'none') && !await page.$eval('#chfa', e => e.readOnly),
       'the chunk sheet writes again');
assert(!await page.$('#chbox .mk-ask'), 'and offers no ask about this chunk');
await page.fill('#chen', 'the old fellow');
await page.click('#chsave');
await waitText(page, '#chstat', /saved en into ch1\.tex/, 60000);
assert(/\{the old fellow\}/.test(await Deno.readTextFile(BOOK + '/ch1.tex')), 'an edit is written into the .tex');
// its download carries the original and annot/, never the agent's files
const dl = await fetch(B + '/books/english/the-clock/__download');
const zipPath = TMP + '/the-clock-book.zip';
await Deno.writeFile(zipPath, new Uint8Array(await dl.arrayBuffer()));
const names = JSON.parse(await py(['-c', 'import json,sys,zipfile; z=zipfile.ZipFile(sys.argv[1]); print(json.dumps([sorted(z.namelist()), json.loads(z.read("parseh-bundle.json"))["format"]]))', zipPath]));
for (const want of ['original/the-clock.txt', 'annot/ch1_p00.json', 'annot/ch2_p00.json', 'NOTES.md', 'book.json', 'main.tex', 'ch1.tex', 'ch2.tex'])
  assert(names[0].includes('the-clock/' + want), 'the download carries ' + want);
for (const never of ['AGENTS.md', 'CLAUDE.md', 'ASKS.md', 'making.json', 'frankdraft.pdf', 'main.pdf'])
  assert(!names[0].some(n => n.endsWith('/' + never)), 'the download never carries ' + never);
eq(names[1], 'parseh-bundle/3', 'the bundle\'s format number is 3');
await views(page, 'C-finished-reader');

/* ================= i) a right-to-left book ================= */
console.log('i) Persian: a book that is read the other way, made from the page');
const MODEL_FA = root + '/tests/fixtures/books/persian/mini-fa';
await agent('original', MODEL_FA, TMP + '/farsi.txt');
const FA = INSTALL + '/books/persian/farsi-shekar-ast';
await page.goto(B + '/books/add/');
await page.click('.path[data-path="llm"]');
await page.waitForSelector('#lane-llm:not([hidden])');
await page.selectOption('#lang', 'fa');
await page.fill('#title', 'فارسی شکر است');
await page.fill('#title_latin', 'Farsi shekar ast');
await page.fill('#author', 'محمدعلی جمال‌زاده');
await page.fill('#author_latin', 'Mohammad-Ali Jamalzadeh');
eq(await page.$eval('#title', e => getComputedStyle(e).direction), 'rtl', 'the title box reads right to left');
await page.setInputFiles('#original', TMP + '/farsi.txt');
await page.waitForFunction(() => !document.querySelector('#mkfolder').disabled);
await page.click('#mkfolder');
await page.waitForSelector('#mkcopy', {timeout: 60000});
eq(await page.$eval('.bigpath', e => e.textContent), FA, 'the folder is on the Persian shelf, named from the transliterated title');
const faJson = JSON.parse(await Deno.readTextFile(FA + '/book.json'));
eq([faJson.language, faJson.title, faJson.author], ['fa', 'فارسی شکر است', 'محمدعلی جمال‌زاده'], 'book.json keeps the Persian, letter for letter');
assert(/Persian/.test(await Deno.readTextFile(FA + '/AGENTS.md')), 'the instructions say it is a Persian book');
await views(page, 'C-fa-add-made', {full: true});
await lib.goto(B + '/books/');
await lib.waitForSelector('a.book[data-making*="persian"]');
eq(await lib.$eval('a.book[data-making*="persian"] [data-making-tag]', e => e.textContent.replace(/ · (just now|\d+ minutes? ago)$/, '')),
   'being made · not started yet', 'the Persian book is on the library at once, marked being made');
await views(lib, 'C-fa-library');
assert(/source recovered/.test(await agent('step', FA, MODEL_FA)), 'the stand-in recovers the Persian source');
assert(/chapter table/.test(await agent('step', FA, MODEL_FA)), '... writes its chapter table');
assert(/batch 1 of 2: chapter 1 assembled/.test(await agent('step', FA, MODEL_FA)), '... and assembles a batch');
await page.goto(B + '/books/persian/farsi-shekar-ast/reader/');
await page.waitForSelector('.mk-btn[data-layout=browser]');
await page.click('.mk-btn[data-layout=browser]');
await page.waitForSelector('#mkbox:not([hidden])');
await page.click('#mkbox button:has-text("look at it now")');
await page.waitForFunction(() => document.querySelector('.row[data-c]'), null, {timeout: 90000});
await page.waitForFunction(() => document.querySelector('#mkbox') && !document.querySelector('#mkbox').hidden, null, {timeout: 20000});
assert(await inView(page, '.mk-btn[data-layout=browser]') && await onTop(page, '.mk-btn[data-layout=browser]') && await inView(page, '#mkbox'),
       'the making button and the panel of a right-to-left book lie inside the window, and nothing over them');
eq(await page.$eval('.mk-btn[data-layout=browser] .mk-txt', e => e.textContent), 'being made · batch 2 of 2', 'the button says where it is');
await views(page, 'C-fa-panel');
await page.click('#mkbox button.mk-x');
await page.hover('.row[data-c="0"]');
await page.waitForSelector('#chpen:not([hidden])');
await page.click('#chpen');
await page.waitForSelector('#chbox .mk-ask');
eq(await page.$$eval('#chfa, #chtr, #chvoc, #chen', els => els.map(e => e.readOnly)), [true, true, true, true],
   'the Persian chunk is shown and cannot be typed in');
assert(await inView(page, '#mkchask') && await onTop(page, '#mkchask'), 'ask about this chunk is in the window in a right-to-left book too');
await page.fill('#chbox .mk-ask textarea', 'معنی را تحت‌اللفظی بنویس');
await page.click('#mkchask');
await waitText(page, '#chbox .mk-said', /written to ASKS\.md/);
assert((await Deno.readTextFile(FA + '/ASKS.md')).includes('معنی را تحت‌اللفظی بنویس'), 'an ask in Persian reaches ASKS.md letter for letter');
await views(page, 'C-fa-chunk-sheet');

/* ================= j) last ================= */
console.log('j) nothing broke, nothing of the owner\'s was touched');
const rest = [...errors];
for (const [label, status, url] of DELIBERATE) {
  const at = rest.findIndex(e => e.label === label && e.text.includes('status of ' + status) && url.test(e.url));
  assert(at >= 0, label + ' was refused ' + status + ' at ' + url + ', on purpose');
  rest.splice(at, 1);
}
eq(rest, [], 'nothing else threw or logged an error');
assert(!/Traceback/.test(logs.join('')), 'no server printed a traceback: ' + (logs.join('').match(/Traceback[\s\S]{0,600}/) || [''])[0]);
eq(await py(['-c', OWN]), ownBefore, 'the checkout\'s books/ and config/ are exactly as they were');
console.log('\n%d checks passed', passed);
} catch (e) {
  failure = e;
} finally {
  try { await browser.close(); } catch { /* gone */ }
  for (const sv of servers) { try { sv.kill(); } catch { /* gone */ } }
  if (!Deno.env.get('PARSEH_KEEP')) await Deno.remove(TMP, {recursive: true});
}
if (failure) { console.error(failure); Deno.exit(1); }
Deno.exit(0);

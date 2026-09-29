// SPDX-License-Identifier: GPL-3.0-or-later
// Browser test of Settings -> Your prompts (brief §8.5, a0.4.2), against Parseh's REAL handler, page and routes
// on a temporary tree (tests/prompts_harness.py: the store, the network settings and the studio's library are
// in it), from TWO DEVICES at once -- the computer, at 127.0.0.1, and a device let in over the Wi-Fi, at
// localhost with the header the harness reads (two origins to a browser, each with storage of its own):
//   a) an empty store says where a prompt is made, and the page is the door it says it is (a pill: any device
//      let in; no lock line and no dead button; the row of Settings' doors has it; the hub has its card)
//   b) prompts made elsewhere are listed by the place they are for, in the kit's order, each with what it is:
//      its kind, its language, its size, when it changed; a right-to-left name and text are laid out right to left
//   c) export: the file that downloads is the prompt, in the shape it says (format stamp, fields) and under its name
//   d) delete: asked in the row, never at once; Keep it puts everything back, focus included; Delete it takes it
//      away from the store, and the other device no longer sees it
//   e) import: the file that was exported comes back under a new name where the name is taken, never over the
//      prompt that has it; a file that is not one, one that names what Parseh does not fill in, and a newer one
//      are refused in words and keep nothing
//   f) keeping up with Parseh: a prompt in place of Parseh's says when Parseh's own changed since it began from it;
//      a prompt added after it never does; saying "mine stands" (through the route) ends it
//   g) one store for every device: what one makes the other lists, whichever route it went in by (the toolbox's,
//      the studio's own copy)
//   h) another SITE cannot write: a page at another origin sends the simple request a browser lets through
//      unasked, and the store is as it was
//   i) 1280 and 390, light, dark and sepia: never a sideways scroll, targets big enough, words readable against
//      their ground, nothing wider than the screen, from both devices
//   j) the keyboard reaches every control, and a redraw never drops it
// Run:  CHROME_BIN=... PARSEH_PYTHON=python3 deno run --allow-all tests/your_prompts.mjs
//   PROMPTS_WHO=computer (or phone) runs one device; SECTIONS=ah runs only those; SHOTS=<dir> saves the screenshots.
import {chromium} from 'npm:playwright-core@1.52.0';

const root = await Deno.realPath(new URL('..', import.meta.url));
const python = Deno.env.get('PARSEH_PYTHON') || 'python3';
const SHOTS = Deno.env.get('SHOTS') || '';
const who = (Deno.env.get('PROMPTS_WHO') || 'computer,phone').split(',');
const only = (Deno.env.get('SECTIONS') || '').toLowerCase();
let passed = 0;
const failures = [];
const assert = (v, m) => { if (!v) throw Error('FAIL: ' + m); passed++; console.log('  ok', m); };
const eq = (a, b, m) => assert(JSON.stringify(a) === JSON.stringify(b), `${m} (got ${JSON.stringify(a)}, want ${JSON.stringify(b)})`);
const has = (text, part, m) => assert(text.includes(part), `${m} (wanted ${JSON.stringify(part)} in ${JSON.stringify(text.slice(0, 300))})`);
const lacks = (text, part, m) => { if (text.includes(part)) throw Error(`FAIL: ${m} (found ${JSON.stringify(part)})`); passed++; console.log('  ok', m); };
const sleep = ms => new Promise(r => setTimeout(r, ms));
async function until(fn, what, ms = 20000) {
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
  const proc = new Deno.Command(python, {args: [root + '/tests/prompts_harness.py'], cwd: root,
                                         stdin: 'piped', stdout: 'piped', stderr: 'piped'}).spawn();
  const log = [];
  (async () => {
    const r = proc.stderr.pipeThrough(new TextDecoderStream()).getReader();
    for (;;) { const {value, done} = await r.read(); if (done) break; log.push(value); }
  })();
  const lines = [], waiting = [];
  let buf = '';
  const reader = proc.stdout.pipeThrough(new TextDecoderStream()).getReader();
  (async () => {
    for (;;) {
      const {value, done} = await reader.read();
      if (done) break;
      buf += value;
      let at;
      while ((at = buf.indexOf('\n')) >= 0) {
        const line = buf.slice(0, at); buf = buf.slice(at + 1);
        if (waiting.length) waiting.shift()(line); else lines.push(line);
      }
    }
  })();
  const next = () => new Promise(res => { if (lines.length) res(lines.shift()); else waiting.push(res); });
  const ready = await Promise.race([next(), sleep(60000).then(() => 'TIMEOUT')]);
  if (!ready.startsWith('READY ')) throw Error('harness did not start: ' + ready + '\n' + log.join(''));
  const info = JSON.parse(ready.slice(6));
  const writer = proc.stdin.getWriter();
  const enc = new TextEncoder();
  const send = async cmd => {
    await writer.write(enc.encode(JSON.stringify(cmd) + '\n'));
    const got = await next();
    if (!got.startsWith('OK')) throw Error('harness: ' + got);
    return got.length > 3 ? JSON.parse(got.slice(3)) : null;
  };
  return {info, send, log, stop: async () => { try { proc.kill('SIGTERM'); } catch (_) {} await proc.status; }};
}

const tmpdir = await Deno.makeTempDir({prefix: 'parseh-your-prompts-'});
const RTL = {surface: 'studio-doc', name: 'قواعد من', kind: 'added', text: 'لا تكتب أسماء الناس بالحروف اللاتينية.\nاكتب كل شيء بالعربية.', languages: ['fa']};
const BRIT = {surface: 'video-region', name: 'British spellings', kind: 'added', text: 'Prefer British spellings in {{GLOSS_LANGUAGE}}.'};
const OWN = {surface: 'video-region', name: 'Persian own rules', kind: 'replace', text: 'Gloss the stretch below, chunk by chunk.\nKeep the order of the text.', languages: ['fa']};
const BOOK = {surface: 'book-region', name: 'for books', kind: 'added', text: 'Say it short.'};
const ASK = {surface: 'ask', name: 'plain translation', kind: 'replace', text: 'Translate {{LANGUAGE}} into {{GLOSS_LANGUAGE}}, word for word.'};

async function suite(h) {
  const port = h.info.port;
  const devices = {
    computer: {origin: `http://127.0.0.1:${port}`, headers: {}, viewport: {width: 1280, height: 900}},
    phone: {origin: `http://localhost:${port}`, headers: {'X-Test-Device': 'phone'}, viewport: {width: 390, height: 844}},
  };
  const browser = await chromium.launch({executablePath: Deno.env.get('CHROME_BIN'), headless: true});
  try {
    const seat = {};
    for (const name of who) {
      const d = devices[name];
      const context = await browser.newContext({viewport: d.viewport, extraHTTPHeaders: d.headers, acceptDownloads: true,
                                                isMobile: name === 'phone', hasTouch: name === 'phone'});
      const page = await context.newPage();
      const errors = [];
      page.on('pageerror', e => errors.push(e.message));
      page.on('console', m => { if (m.type() === 'error' && !/Failed to load resource/.test(m.text())) errors.push('console: ' + m.text()); });
      page.on('response', r => { if (r.status() >= 400 && !/favicon/.test(r.url()) && !r.url().includes('/settings/api/prompts/')) errors.push(`http ${r.status()} ${r.url()}`); });
      seat[name] = {name, page, context, origin: d.origin, errors, request: context.request};
    }
    const on = seat[who[0]];
    // a section that fails is said, and the rest still run; SECTIONS=ah runs only those (by their letters)
    const section = async (title, fn) => {
      if (only && !only.includes(title[0])) return;
      console.log(title);
      try { await fn(); } catch (e) { failures.push(`${title}: ${e.message}`); console.log('  ' + e.message); }
    };
    const shot = async (s, n) => { if (SHOTS) await s.page.screenshot({path: `${SHOTS}/prompts-${s.name}-${n}.png`, fullPage: true}); };
    const door = async s => { await s.page.goto(s.origin + '/settings/prompts/'); await s.page.waitForSelector('#pr section'); };
    const text = async (s, sel) => (await s.page.locator(sel).first().innerText()).replace(/\s+/g, ' ');
    const api = (s, what, body) => s.page.evaluate(async ([what, body]) => (await (await fetch('/settings/api/prompts/' + what, {
      method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body || {})})).json()), [what, body]);
    const stored = () => h.send({cmd: 'stored'});
    const names = async () => ((await stored()) || {prompts: []}).prompts.map(p => p.name).sort();
    const card = (s, name) => s.page.locator('.pk', {has: s.page.locator('h3', {hasText: name})});
    const world = async (...made) => {
      await h.send({cmd: 'clear'});
      await h.send({cmd: 'parseh', changed: false});
      const ids = [];
      for (const p of made) ids.push(await h.send({cmd: 'save', prompt: p}));
      return ids;
    };

    await section('a) an empty store', async () => {
      for (const s of Object.values(seat)) {
        await world();
        await door(s);
        eq(await s.page.locator('h1.idx').textContent(), 'your prompts', `${s.name}: the page says what it is`);
        has(await text(s, '[data-none]'), 'You have no prompts of your own yet', `${s.name}: an empty store says so`);
        has(await text(s, '[data-none]'), 'prompt menu beside the button that copies a prompt', `${s.name}: and where a prompt is made`);
        const st = JSON.parse(await s.page.locator('#pr-state').textContent());
        eq(st.where, s.name === 'phone' ? 'lan' : 'self', `${s.name}: the page knows where it is asked from`);
        eq(st.may, {'prompts.save': true, 'prompts.delete': true}, `${s.name}: every button is allowed, from here too`);
        has(await text(s, '.whomay'), 'any device that has been let in', `${s.name}: the door's pill says who may`);
        eq(await s.page.locator('.gate:not(.open)').evaluateAll(els => els.filter(e => e.closest('.whomay')).length), 0,
           `${s.name}: and none of this page's own pills says the computer only`);
        eq(await s.page.locator('[data-lock], .lockline').count(), 0, `${s.name}: no lock line`);
        eq(await s.page.locator('#pr button:disabled').count(), 0, `${s.name}: no dead button`);
        eq(await s.page.locator('.sdoor.on').getAttribute('href'), '/settings/prompts/', `${s.name}: Settings' row of doors marks this one`);
        has(await text(s, '#pr'), 'Import a prompt', `${s.name}: and an import is offered`);
        const guide = await s.page.locator('.foot a').getAttribute('href');
        has(guide, '/guide/site/studio/your-prompts.html', `${s.name}: the guide's page is linked`);
        await s.page.goto(s.origin + '/settings/');
        const cardHref = s.page.locator('a.door[href="/settings/prompts/"]');
        eq(await cardHref.count(), 1, `${s.name}: the hub has a card for it`);
        has(await cardHref.innerText(), 'Your prompts', `${s.name}: named`);
        has(await cardHref.innerText(), 'any device let in', `${s.name}: with the pill that says who may`);
        await cardHref.click();
        await s.page.waitForSelector('#pr section');
        eq(new URL(s.page.url()).pathname, '/settings/prompts/', `${s.name}: and it opens the door`);
        await shot(s, 'a-empty');
      }
    });

    await section('b) what was made elsewhere, by the place it is for', async () => {
      await world(RTL, ASK, BRIT, OWN, BOOK);
      for (const s of Object.values(seat)) {
        await door(s);
        const heads = await s.page.locator('#pr section h2').allInnerTexts();
        eq(heads.map(x => x.replace(/\s+/g, ' ').trim()).slice(0, 5),
           ["the studio's prompt for a new document 1", 'a stretch of a video, glossed by an LLM 2', 'a stretch of a book, glossed by an LLM 1',
            'Ask LLM, one sentence in the sources 1', 'Import a prompt'],
           `${s.name}: a section for each place that has one, in the kit's order, with how many`);
        const brit = await text(s, '.pk:has(h3:text("British spellings"))');
        has(brit, `added after Parseh’s instructions · for every language · ${BRIT.text.length} characters · changed a moment ago`, `${s.name}: what a prompt is, in one line`);
        const own = await text(s, '.pk:has(h3:text("Persian own rules"))');
        has(own, 'in place of Parseh’s instructions · for Persian only', `${s.name}: a prompt in place of Parseh's, and the language it is for`);
        has(own, `${OWN.text.length} characters`, `${s.name}: its size`);
        const rtl = await s.page.locator('.pk:has(h3:text("قواعد من"))');
        eq(await rtl.locator('h3').evaluate(e => getComputedStyle(e).direction), 'rtl', `${s.name}: a right-to-left name is laid out right to left`);
        eq(await rtl.locator('pre').evaluate(e => getComputedStyle(e).direction), 'rtl', `${s.name}: and so is its text`);
        eq(await s.page.locator('details[open]').count(), 0, `${s.name}: the text is folded until it is asked for`);
        await card(s, 'British spellings').locator('summary').click();
        has(await card(s, 'British spellings').locator('pre').innerText(), 'Prefer British spellings in {{GLOSS_LANGUAGE}}.', `${s.name}: read it shows the words as written`);
        eq(await card(s, 'British spellings').locator('pre').isVisible(), true, `${s.name}: and shows them`);
        await shot(s, 'b-listed');
      }
      // what a person wrote is text, whatever it holds: no tag of theirs is ever drawn as one
      await h.send({cmd: 'save', prompt: {surface: 'ask', name: 'a & <b>bold</b> <img src=x onerror=alert(1)>', kind: 'added',
                                          text: 'Say "hi" & </script><script>alert(1)</script> <img src=x onerror=alert(2)> {{LANGUAGE}}'}});
      for (const s of Object.values(seat)) {
        await door(s);
        const nasty = s.page.locator('.pk', {has: s.page.locator('h3', {hasText: 'bold'})});
        eq(await nasty.locator('h3').innerText(), 'a & <b>bold</b> <img src=x onerror=alert(1)>', `${s.name}: a name with tags in it is drawn as the text it is`);
        await nasty.locator('summary').click();
        has(await nasty.locator('pre').innerText(), 'Say "hi" & </script><script>alert(1)</script> <img src=x onerror=alert(2)>', `${s.name}: and so are its words`);
        eq(await s.page.locator('#pr img, #pr b, #pr script').count(), 0, `${s.name}: and none of it became an element`);
        eq(s.errors.length, 0, `${s.name}: and nothing ran (${s.errors.join(' | ')})`);
      }
    });

    await section('c) export', async () => {
      const [brit] = await world(BRIT);
      for (const s of Object.values(seat)) {
        await door(s);
        const link = card(s, 'British spellings').locator('a', {hasText: 'Export'});
        eq(await link.getAttribute('aria-label'), 'Export British spellings', `${s.name}: named for what it exports`);
        const [dl] = await Promise.all([s.page.waitForEvent('download'), link.click()]);
        eq(dl.suggestedFilename(), 'British-spellings.parseh-prompt.json', `${s.name}: the file is named for the prompt`);
        const file = JSON.parse(await Deno.readTextFile(await dl.path()));
        eq(file.format, 'parseh-prompt/1', `${s.name}: it says what it is`);
        eq(file.software, 'Parseh', `${s.name}: and whose`);
        eq(file.prompt, {name: 'British spellings', surface: 'video-region', kind: 'added', languages: [], text: BRIT.text},
           `${s.name}: and holds the prompt, its words as written`);
        const direct = await s.request.get(s.origin + '/settings/api/prompts/export?id=' + brit);
        has(direct.headers()['content-disposition'], "attachment; filename*=UTF-8''British-spellings.parseh-prompt.json", `${s.name}: sent as a download`);
        eq((await s.request.get(s.origin + '/settings/api/prompts/export?id=pgone0000')).status(), 404, `${s.name}: an id that is gone is a 404`);
      }
    });

    await section('d) delete', async () => {
      for (const s of Object.values(seat)) {
        const other = Object.values(seat).find(x => x !== s) || s;
        await world(BRIT, BOOK);
        await door(s);
        const brit = card(s, 'British spellings');
        await brit.locator('button', {hasText: 'Delete'}).click();
        eq(await s.page.locator('.sure').count(), 1, `${s.name}: a delete is asked about, in the row`);
        has(await text(s, '.sure'), 'Delete British spellings? It cannot be got back.', `${s.name}: naming what goes`);
        eq(await names(), ['British spellings', 'for books'], `${s.name}: and nothing has gone yet`);
        eq(await s.page.evaluate(() => document.activeElement && document.activeElement.textContent), 'Keep it', `${s.name}: focus is on the safe answer`);
        await shot(s, 'd-asking');
        await s.page.locator('.sure button', {hasText: 'Keep it'}).click();
        eq(await s.page.locator('.sure').count(), 0, `${s.name}: Keep it puts the row back`);
        eq(await s.page.evaluate(() => document.activeElement && document.activeElement.textContent.trim()), 'Delete…', `${s.name}: with the keyboard where it was`);
        eq(await names(), ['British spellings', 'for books'], `${s.name}: nothing gone`);
        await brit.locator('button', {hasText: 'Delete'}).click();
        await s.page.locator('.sure button', {hasText: 'Delete it'}).click();
        await until(async () => (await names()).length === 1, `${s.name}: the delete`);
        eq(await names(), ['for books'], `${s.name}: Delete it takes it out of the store`);
        has(await text(s, '[data-said]'), 'Deleted “British spellings”.', `${s.name}: and says so`);
        eq(await s.page.locator('.pk').count(), 1, `${s.name}: and off the page`);
        await door(other);
        eq(await other.page.locator('.pk h3').allInnerTexts(), ['for books'], `${s.name}: the other device no longer sees it`);
        // a delete of one that another device has taken away already is said in words, and the page is right again
        await door(s);
        await card(s, 'for books').locator('button', {hasText: 'Delete'}).click();
        await h.send({cmd: 'clear'});
        await s.page.locator('.sure button', {hasText: 'Delete it'}).click();
        await until(async () => (await text(s, '[data-said]')).includes('there is no prompt of yours with that id'), `${s.name}: a delete of a prompt already gone says so`);
        eq(await s.page.locator('.pk').count(), 0, `${s.name}: and the page reads the store again`);
      }
    });

    await section('e) import', async () => {
      for (const s of Object.values(seat)) {
        const [brit] = await world(BRIT, OWN);
        await door(s);
        const file = `${tmpdir}/${s.name}-british.json`;
        await Deno.writeTextFile(file, await (await s.request.get(s.origin + '/settings/api/prompts/export?id=' + brit)).text());
        await s.page.setInputFiles('[data-import]', file);
        await until(async () => (await text(s, '[data-said]')).includes('Imported as'), `${s.name}: the import`);
        has(await text(s, '[data-said]'), 'Imported as “British spellings (2)”: you have a prompt called “British spellings” for this already, and an import never writes over one.', `${s.name}: a name that is taken is renamed, and it says so`);
        eq(await s.page.locator('.pk h3').allInnerTexts(), ['British spellings', 'Persian own rules', 'British spellings (2)'], `${s.name}: both are listed`);
        assert((await stored()).prompts.find(p => p.name === 'British spellings').id === brit, `${s.name}: and the first is the same prompt it was`);
        // the same file into a place that has no prompt of that name: kept as it is called
        await h.send({cmd: 'clear'});
        await h.send({cmd: 'save', prompt: OWN});
        await door(s);
        await s.page.setInputFiles('[data-import]', file);
        await until(async () => (await text(s, '[data-said]')).includes('Imported as'), `${s.name}: the import into a place without one`);
        has(await text(s, '[data-said]'), 'Imported as “British spellings”.', `${s.name}: kept as it is called`);
        lacks(await text(s, '[data-said]'), 'never writes over', `${s.name}: with nothing about a clash`);
        // files that are not a prompt Parseh reads
        const refuse = async (name, body, said) => {
          const bad = `${tmpdir}/${s.name}-${name}.json`;
          await Deno.writeTextFile(bad, body);
          const before = await names();
          await s.page.setInputFiles('[data-import]', bad);
          await until(async () => (await text(s, '[data-said]')).includes(said), `${s.name}: ${name} is refused in words`);
          eq(await s.page.locator('[data-said].bad').count(), 1, `${s.name}: as a problem (${name})`);
          eq(await names(), before, `${s.name}: and keeps nothing (${name})`);
        };
        const good = JSON.parse(await Deno.readTextFile(file));
        await refuse('not-json', 'this is not json', 'that file is not a prompt exported by Parseh');
        await refuse('another-format', JSON.stringify({format: 'parseh-latex-theme/1'}), 'that file is not a prompt this Parseh reads (it wants parseh-prompt/1)');
        await refuse('newer', JSON.stringify(Object.assign({}, good, {format: 'parseh-prompt/2'})), 'exported by a newer Parseh (it says parseh-prompt/2)');
        await refuse('unknown-name', JSON.stringify(Object.assign({}, good, {prompt: Object.assign({}, good.prompt, {text: 'Be brief. {{FROM_LATER}}'})})),
                     '{{FROM_LATER}} is not something Parseh fills in for this prompt');
        await refuse('empty', JSON.stringify(Object.assign({}, good, {prompt: Object.assign({}, good.prompt, {text: '  '})})), 'no words in it');
        await refuse('no-place', JSON.stringify(Object.assign({}, good, {prompt: Object.assign({}, good.prompt, {surface: 'the-moon'})})), 'is not a prompt Parseh has');
        await shot(s, 'e-refused');
      }
    });

    await section('f) keeping up with Parseh', async () => {
      const [, replaced] = await world(BRIT, OWN);
      for (const s of Object.values(seat)) {
        await h.send({cmd: 'parseh', changed: false});
        await door(s);
        eq(await s.page.locator('[data-old]').count(), 0, `${s.name}: nothing is said while Parseh's own is what it was`);
        await h.send({cmd: 'parseh', changed: true});
        await door(s);
        eq(await s.page.locator('[data-old]').count(), 1, `${s.name}: one prompt says Parseh's own changed`);
        has(await text(s, '.pk:has([data-old])'), 'Persian own rules', `${s.name}: the one in place of Parseh's`);
        has(await text(s, '[data-old]'), 'Parseh’s own prompt has changed since you started from this one.', `${s.name}: in those words`);
        eq(await s.page.locator('.pk:has(h3:text("British spellings")) [data-old]').count(), 0, `${s.name}: a prompt added after Parseh's never does`);
        await shot(s, 'f-old');
        const said = await api(s, 'uptodate', {id: replaced});
        eq(said.ok, true, `${s.name}: "mine stands" is a route`);
        await door(s);
        eq(await s.page.locator('[data-old]').count(), 0, `${s.name}: and ends it`);
        await h.send({cmd: 'parseh', changed: false});
        await door(s);
        eq(await s.page.locator('[data-old]').count(), 1, `${s.name}: Parseh's own changing back is a change again`);
        await api(s, 'uptodate', {id: replaced});
      }
      await h.send({cmd: 'parseh', changed: false});
    });

    await section('g) one store for every device', async () => {
      await world();
      const devs = Object.values(seat);
      for (const s of devs) {
        const other = devs.find(x => x !== s) || s;
        const made = await api(s, 'save', BRIT);
        eq(made.ok, true, `${s.name}: makes a prompt through the toolbox's route`);
        await door(other);
        eq(await other.page.locator('.pk h3').allInnerTexts(), ['British spellings'], `${s.name}: and the other device lists it`);
        const studio = await s.page.evaluate(async body => (await (await fetch('/studio/api/prompts/save', {
          method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)})).json()), BOOK);
        eq(studio.ok, true, `${s.name}: and one through the studio's own copy`);
        await door(other);
        eq(await other.page.locator('.pk h3').allInnerTexts(), ['British spellings', 'for books'], `${s.name}: the other device lists both, by place`);
        assert((await names()).length === 2, `${s.name}: two prompts in one store`);
        await world();
      }
    });

    await section('h) another site writes nothing', async () => {
      await world(BRIT);
      const before = JSON.stringify(await stored());
      const s = on;
      // a page at ANOTHER ORIGIN -- localhost, when Parseh is at 127.0.0.1, and the other way round -- sends the request a
      // browser lets through without asking first (text/plain), which is all a foreign page can do to a server with no login
      const foreign = s.name === 'computer' ? `http://localhost:${port}` : `http://127.0.0.1:${port}`;
      const p2 = await s.context.newPage();
      await p2.goto(foreign + '/settings/prompts/');
      const target = s.origin + '/settings/api/prompts/';
      await p2.evaluate(async t => {
        await fetch(t + 'save', {method: 'POST', mode: 'no-cors', headers: {'Content-Type': 'text/plain'},
                                 body: JSON.stringify({surface: 'ask', name: 'planted', text: 'hello'})}).catch(() => {});
        await fetch(t + 'delete', {method: 'POST', mode: 'no-cors', headers: {'Content-Type': 'text/plain'},
                                   body: JSON.stringify({id: 'nothing'})}).catch(() => {});
      }, target);
      await sleep(400);
      eq(JSON.stringify(await stored()), before, 'a simple request from another site changed nothing');
      const seen = [];
      p2.on('response', r => seen.push([r.status(), r.url()]));
      const status = await p2.evaluate(async t => (await fetch(t + 'save', {method: 'POST', mode: 'no-cors', headers: {'Content-Type': 'text/plain'},
                                                                              body: '{}'}).then(r => r.type)), target);
      eq(status, 'opaque', 'the other page cannot read what came back');
      // and what the same request says, read with the header a browser puts on it
      const said = await s.request.post(s.origin + '/settings/api/prompts/save', {
        headers: {'Sec-Fetch-Site': 'cross-site', 'Content-Type': 'text/plain'}, data: JSON.stringify({surface: 'ask', name: 'planted', text: 'x'})});
      eq(said.status(), 403, 'the server refuses it');
      has((await said.json()).error, 'it came from another site', 'in words');
      eq(JSON.stringify(await stored()), before, 'and the store is as it was');
      await p2.close();
    });

    await section('i) widths and themes', async () => {
      await world(RTL, ASK, BRIT, OWN, BOOK);
      await h.send({cmd: 'parseh', changed: true});
      const ratio = s => s.page.evaluate(() => {
        const lum = c => { const v = c.match(/[\d.]+/g).slice(0, 3).map(Number).map(x => { x /= 255; return x <= .03928 ? x / 12.92 : ((x + .055) / 1.055) ** 2.4; }); return .2126 * v[0] + .7152 * v[1] + .0722 * v[2]; };
        const ground = el => { for (let e = el; e; e = e.parentElement) { const b = getComputedStyle(e).backgroundColor; const m = b.match(/[\d.]+/g); if (m && (m.length < 4 || Number(m[3]) > .9)) return b; } return 'rgb(255,255,255)'; };
        document.querySelectorAll('#pr details').forEach(d => { d.open = true; });
        const worst = [];
        for (const sel of ['.pk h3', '.pk .facts', '.pk summary', '.pk pre', '.pk .old', '.whomay span', 'h2', '.why']) {
          for (const el of document.querySelectorAll('main ' + sel)) {
            if (!el.offsetParent || !el.textContent.trim()) continue;
            const a = lum(getComputedStyle(el).color), b = lum(ground(el));
            worst.push([(Math.max(a, b) + .05) / (Math.min(a, b) + .05), sel]);
          }
        }
        worst.sort((x, y) => x[0] - y[0]);
        return worst[0];
      });
      const soft = (v, m) => { if (v) { passed++; console.log('  ok', m); } else { failures.push(`i) ${m}`); console.log('  FAIL:', m); } };
      for (const s of Object.values(seat)) {
        for (const w of [1280, 390]) {
          await s.page.setViewportSize({width: w, height: w === 390 ? 844 : 900});
          for (const theme of ['light', 'dark', 'sepia']) {
            await door(s);
            await s.page.evaluate(t => { if (window.Parseh && Parseh.theme) Parseh.theme.set(t); else document.documentElement.setAttribute('data-theme', t); }, theme);
            const label = `${s.name} ${w}px ${theme}`;
            const over = await s.page.evaluate(() => ({sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth}));
            soft(over.sw <= over.cw + 1, `${label}: no sideways scroll (${over.sw} in ${over.cw})`);
            const out = await s.page.evaluate(() => {
              const vw = document.documentElement.clientWidth;
              return [...document.querySelectorAll('#pr .pk, #pr button, #pr a.plain, #pr pre')]
                .filter(e => e.offsetParent && e.getBoundingClientRect().right > vw + 1).map(e => e.className || e.tagName);
            });
            soft(out.length === 0, `${label}: nothing wider than the screen (${out.join()})`);
            const small = await s.page.evaluate(min => [...document.querySelectorAll('#pr button, #pr a.plain')]
              .filter(e => e.offsetParent && e.getBoundingClientRect().height < min).map(e => e.textContent.trim()), w === 390 ? 40 : 30);
            soft(small.length === 0, `${label}: every button is big enough to press (${small.join()})`);
            const r = await ratio(s);
            soft(r[0] >= 4.5, `${label}: the words are readable against their ground (worst ${r[0].toFixed(2)}:1 on ${r[1]})`);
            const inside = await s.page.locator('.pk h3[dir=auto]').evaluateAll(els => els.every(e => { const b = e.getBoundingClientRect(); return b.left >= 0 && b.right <= innerWidth; }));
            soft(inside, `${label}: every name, the right-to-left one too, is inside the screen`);
            await shot(s, `i-${w}-${theme}`);
          }
        }
        await s.page.setViewportSize(devices[s.name].viewport);
        await s.page.evaluate(() => { if (window.Parseh && Parseh.theme) Parseh.theme.set('auto'); });
      }
      await h.send({cmd: 'parseh', changed: false});
    });

    await section('j) the keyboard', async () => {
      await world(BRIT, BOOK);
      for (const s of Object.values(seat)) {
        await door(s);
        const order = [];
        await s.page.evaluate(() => { document.activeElement && document.activeElement.blur(); document.querySelector('#pr').scrollIntoView(); });
        await s.page.locator('#pr summary').first().focus();
        for (let i = 0; i < 9; i++) {
          order.push(await s.page.evaluate(() => { const e = document.activeElement; return e ? (e.getAttribute('aria-label') || e.textContent.trim().slice(0, 30)) : ''; }));
          await s.page.keyboard.press('Tab');
        }
        has(order.join(' | '), 'Export ', `${s.name}: Tab reaches Export`);
        has(order.join(' | '), 'Delete ', `${s.name}: and Delete`);
        has(order.join(' | '), 'read it', `${s.name}: and the fold that shows the words`);
        has(order.join(' | '), 'Import a prompt…', `${s.name}: and Import`);
        await s.page.locator('.pk button', {hasText: 'Delete'}).first().focus();
        await s.page.keyboard.press('Enter');
        eq(await s.page.evaluate(() => document.activeElement.textContent), 'Keep it', `${s.name}: Enter asks, and focus lands on Keep it`);
        await s.page.keyboard.press('Enter');
        eq(await s.page.evaluate(() => (document.activeElement.textContent || '').trim()), 'Delete…', `${s.name}: Enter on Keep it, and it is back where it was`);
        eq((await names()).length, 2, `${s.name}: nothing went`);
      }
    });

    for (const s of Object.values(seat)) {
      if (s.errors.length) failures.push(`${s.name}: the page had errors: ${s.errors.slice(0, 3).join(' | ')}`);
      else { passed++; console.log(`  ok ${s.name}: no page error, no console error, no failed request`); }
    }
  } finally {
    await browser.close();
  }
}

const h = await startHarness();
try {
  await suite(h);
} finally {
  await h.stop();
  await Deno.remove(tmpdir, {recursive: true}).catch(() => {});
}
console.log(`\n${passed} ok, ${failures.length} FAIL`);
for (const f of failures) console.log('FAIL: ' + f);
Deno.exit(failures.length ? 1 : 0);

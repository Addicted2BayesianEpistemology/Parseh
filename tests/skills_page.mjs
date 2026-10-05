// SPDX-License-Identifier: GPL-3.0-or-later
// Browser test of Settings -> Skills for your chatbot and of the row's skill button (brief §9, a0.4.2), against
// Parseh's REAL handler, page and routes on a temporary tree (tests/prompts_harness.py), from TWO DEVICES -- the
// computer, at 127.0.0.1, and a device let in over the Wi-Fi, at localhost with the header the harness reads:
//   a) the door: what each skill is (its size, version and hash), a button that downloads it, how to install it
//      tool by tool with each tool's own help; NO install button; the pill says any device let in; the row of
//      Settings' doors and the hub have it
//   b) the download: a zip, laid out as the tools want it (one folder named like the skill, SKILL.md inside), whose
//      size is what the page says, and the same bytes the second time
//   c) what this device remembers of the skill it downloaded: nothing said before, a line when Parseh would make
//      another now, gone again after a download
//   d) the row on the studio's prompt page: the second button appears with the prompt, its note says what the request
//      saves and links the page, a press puts the request (its header, the hash of the skill built now) on the
//      clipboard, the last button used comes first; a prompt of the person's added to Parseh's travels in it and one in
//      place of Parseh's is said to be unable to
//   e) 1280 and 390, light, dark and sepia: never a sideways scroll, nothing wider than the screen
//   f) a reading only: a request that writes is refused
// Run:  CHROME_BIN=... PARSEH_PYTHON=python3 deno run --allow-all tests/skills_page.mjs
//   SKILLS_WHO=computer (or phone) runs one device; SECTIONS=ab runs only those; SHOTS=<dir> saves screenshots.
import {chromium} from 'npm:playwright-core@1.52.0';

const root = await Deno.realPath(new URL('..', import.meta.url));
const python = Deno.env.get('PARSEH_PYTHON') || 'python3';
const SHOTS = Deno.env.get('SHOTS') || '';
const who = (Deno.env.get('SKILLS_WHO') || 'computer,phone').split(',');
const only = (Deno.env.get('SECTIONS') || '').toLowerCase();
let passed = 0;
const failures = [];
const assert = (v, m) => { if (!v) throw Error('FAIL: ' + m); passed++; console.log('  ok', m); };
const eq = (a, b, m) => assert(a === b, `${m} (got ${JSON.stringify(a)}, want ${JSON.stringify(b)})`);
const has = (text, part, m) => assert(text.includes(part), `${m} (wanted ${JSON.stringify(part)} in ${JSON.stringify(text.slice(0, 300))})`);
const lacks = (text, part, m) => assert(!text.includes(part), `${m} (found ${JSON.stringify(part)})`);
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

const ADDED = {surface: 'studio-doc', name: 'british', kind: 'added', text: 'Prefer British spellings.'};
const REPLACE = {surface: 'studio-doc', name: 'my own way', kind: 'replace', text: 'Write the document my way: {{?vocab}}entries{{/vocab}}.'};

async function suite(h) {
  const port = h.info.port;
  const devices = {
    computer: {origin: `http://127.0.0.1:${port}`, headers: {}, viewport: {width: 1280, height: 900}},
    phone: {origin: `http://localhost:${port}`, headers: {'X-Test-Device': 'phone'}, viewport: {width: 390, height: 844}},
  };
  const browser = await chromium.launch({executablePath: Deno.env.get('CHROME_BIN'), headless: true});
  try {
    for (const name of who) {
      const d = devices[name];
      console.log(`\n== ${name} ==`);
      const context = await browser.newContext({viewport: d.viewport, extraHTTPHeaders: d.headers, acceptDownloads: true,
                                                isMobile: name === 'phone', hasTouch: name === 'phone',
                                                permissions: ['clipboard-read', 'clipboard-write']});
      const page = await context.newPage();
      const errors = [];
      page.on('pageerror', e => errors.push(e.message));
      page.on('console', m => { if (m.type() === 'error' && !/Failed to load resource/.test(m.text())) errors.push('console: ' + m.text()); });
      page.on('response', r => { if (r.status() >= 400 && !/favicon|\/api\/prompts?(\/|\?)|\/api\/skills\//.test(r.url())) errors.push(`http ${r.status()} ${r.url()}`); });
      const section = async (title, fn) => {
        if (only && !only.includes(title[0])) return;
        console.log(title);
        try { await fn(); } catch (e) { failures.push(`${name}: ${title}: ${e.message}`); console.log('  ' + e.message); }
      };
      const shot = async n => { if (SHOTS) await page.screenshot({path: `${SHOTS}/skills-${name}-${n}.png`, fullPage: true}); };
      const door = async () => { await page.goto(d.origin + '/settings/skills/'); await page.waitForSelector('[data-skill]'); };
      const text = async sel => (await page.locator(sel).first().innerText()).replace(/\s+/g, ' ');
      const state = () => page.evaluate(() => fetch('/settings/api/skills/state').then(r => r.json()));
      const names = async () => (await state()).skills.map(s => s.name);

      await section('a) the door', async () => {
        await door();
        eq(await page.locator('h1.idx').textContent(), 'skills for your chatbot', 'the page says what it is');
        has(await text('.whomay'), 'any device let in', "the door's pill says who may");
        has(await text('.whomay'), 'there is no install button', 'and that there is no install button');
        const st = await state();
        assert(st.ok && st.skills.length >= 2, 'the state lists the skills this tree can make');
        for (const s of st.skills) {
          const card = page.locator(`[data-skill="${s.name}"]`);
          eq(await card.count(), 1, `${s.name} has a card`);
          const t = (await card.innerText()).replace(/\s+/g, ' ');
          has(t, s.version, `${s.name}: its version`);
          has(t, s.hash, `${s.name}: its hash`);
          has(t, 'download (.zip)', `${s.name}: the download`);
          has(t, s.what.slice(0, 30), `${s.name}: what it does`);
        }
        const body = await text('main');
        for (const tool of ['claude.ai and the Claude desktop app', 'Claude Code', 'Codex, Gemini CLI, Cursor, GitHub Copilot and VS Code',
                            'The Gemini app', 'ChatGPT', 'A phone', 'A chatbot with no skills']) has(body, tool, `how to install: ${tool}`);
        has(body, 'Customize → Skills', 'claude.ai: where the upload is');
        has(body, '.agents/skills/', 'the folder the other tools read');
        has(body, 'not documented, so nothing more is promised', 'a phone: only what is known');
        assert(await page.locator('main a[href^="https://"]').count() >= 8, "each tool's own help is linked");
        eq(await page.locator('main button').count(), 0, 'no button of any kind, and so no install button');
        eq((await page.locator('main').innerText()).toLowerCase().includes('install it for you'), false, 'nothing installs for the person');
        eq(await page.locator('a.sdoor[href="/settings/skills/"][aria-current="page"]').count(), 1, 'the row of Settings doors has it, marked');
        await page.goto(d.origin + '/settings/');
        assert(await page.locator('a.door[href="/settings/skills/"]').count() === 1, 'the hub has its card');
        await shot('door');
      });

      await section('b) the download', async () => {
        await door();
        const st = await state();
        const sk = st.skills.find(s => s.name === 'parseh-gloss');
        const [dl] = await Promise.all([page.waitForEvent('download'), page.locator('[data-skill="parseh-gloss"] [data-download]').click()]);
        eq(dl.suggestedFilename(), 'parseh-gloss.zip', 'it downloads as <name>.zip');
        const bytes = await Deno.readFile(await dl.path());
        eq(bytes.length, sk.zip, 'its size is what the page says');
        eq(String.fromCharCode(...bytes.slice(0, 2)), 'PK', 'it is a zip');
        const all = new TextDecoder('latin1').decode(bytes);
        has(all, 'parseh-gloss/SKILL.md', 'one folder named like the skill, SKILL.md in capitals inside it');
        has(all, 'parseh-gloss/references/stretch/fa.md', 'and its references under it');
        lacks(all, 'parseh-gloss/skill.md', 'no lower-case spelling');
        const again = await page.evaluate(n => fetch('/settings/api/skills/download?name=' + n).then(r => r.arrayBuffer()).then(b => Array.from(new Uint8Array(b)).length), 'parseh-gloss');
        eq(again, sk.zip, 'the same bytes the second time');
        const gone = await page.evaluate(() => fetch('/settings/api/skills/download?name=nope').then(r => r.status));
        eq(gone, 404, 'a skill that does not exist is not found');
      });

      await section('c) what this device remembers', async () => {
        await door();
        await page.evaluate(() => { try { localStorage.clear(); } catch (e) {} });
        await door();
        eq(await page.locator('[data-old]:visible').count(), 0, 'nothing is said before a download');
        const st = await state();
        const sk = st.skills.find(s => s.name === 'parseh-markdown');
        const [dl] = await Promise.all([page.waitForEvent('download'), page.locator('[data-skill="parseh-markdown"] [data-download]').click()]);
        await dl.path();
        eq(await page.evaluate(() => localStorage.getItem('parseh_skill_parseh-markdown')), sk.hash, 'the hash downloaded is kept on this device');
        await door();
        eq(await page.locator('[data-old]:visible').count(), 0, 'and nothing is said while it is the one Parseh would make');
        await page.evaluate(() => localStorage.setItem('parseh_skill_parseh-markdown', 'zzzz'));
        await door();
        has(await text('[data-skill="parseh-markdown"] [data-old]'), 'your skill may be older than this Parseh — download it again', 'a skill that is not what Parseh would make now is said to be older');
        await shot('stale');
        const [dl2] = await Promise.all([page.waitForEvent('download'), page.locator('[data-skill="parseh-markdown"] [data-download]').click()]);
        await dl2.path();
        eq(await page.locator('[data-skill="parseh-markdown"] [data-old]:visible').count(), 0, 'and the line is gone after a download');
      });

      await section('d) the row beside the prompt', async () => {
        await h.send({cmd: 'clear'});
        await page.goto(d.origin + '/studio/prompt');
        await page.waitForSelector('#llm-row .llmrow-copy');
        await until(async () => (await page.locator('#llm-row .llmrow-skill').isVisible()), 'the skill button appears with the prompt');
        const k = page.locator('#llm-row .llmrow-skill');
        has(await k.innerText(), 'copy the request for the skill', 'the button says what it copies');
        const note = await text('#llm-row .llmrow-skillnote');
        has(note, 'in a chat where the parseh-markdown skill is installed, paste this', 'the reminder names the skill');
        assert(/— [\d,]+ characters instead of [\d,]+\./.test(note), 'and says what the request saves');
        has(note, 'copy the prompt instead', 'and what to do where the skill is not there');
        eq(await page.locator('#llm-row .llmrow-skillnote a').getAttribute('href'), '/settings/skills/', 'the link goes to the page');
        await k.click();
        await until(async () => (await text('#llm-row .llmrow-say')).includes('copied'), 'it is copied');
        const clip = await page.evaluate(() => navigator.clipboard.readText());
        has(clip.split('\n')[0], 'Parseh request · parseh-markdown · ', 'the clipboard holds the request');
        const st = await state();
        has(clip.split('\n')[0], ' · ' + st.skills.find(s => s.name === 'parseh-markdown').hash + ' · ', 'with the hash of the skill built now');
        has(clip.split('\n')[0], 'features: ', 'and the boxes ticked');
        assert(clip.length < 900, 'and is short');
        // the last button used comes first
        await page.reload();
        await page.waitForSelector('#llm-row .llmrow-skill:visible');
        const order = await page.evaluate(() => Array.from(document.querySelectorAll('#llm-row .llmrow-bar button')).map(b => b.className.split(' ')[0]));
        eq(order.indexOf('llmrow-skill') < order.indexOf('llmrow-copy'), true, 'the button last used is first, and neither is hidden');
        await shot('row');
        // a prompt of the person's added to Parseh's travels in the request; one in place of Parseh's cannot
        await h.send({cmd: 'save', prompt: ADDED});
        await h.send({cmd: 'save', prompt: REPLACE});
        await page.reload();
        await page.waitForSelector('#llm-row .llmrow-skill:visible');
        const sel = page.locator('#llm-row .llmrow-pm select').first();
        const opts = await sel.locator('option').allInnerTexts();
        const pick = async n => { await sel.selectOption({label: opts.find(o => o.includes(n))}); await sleep(400); };
        await pick('british');
        await until(async () => (await text('#llm-row .llmrow-skillnote')).includes('skill is installed'), 'the note is back');
        await page.locator('#llm-row .llmrow-skill').click();
        await until(async () => (await page.evaluate(() => navigator.clipboard.readText())).includes('Prefer British spellings.'), 'an added prompt follows the header');
        has((await page.evaluate(() => navigator.clipboard.readText())).split('\n')[0], 'custom: british', 'and is named in it');
        has(await text('#llm-row .llmrow-skillnote'), 'Your prompt “british” goes with it', 'and the row says that it goes with the request');
        await pick('my own way');
        await until(async () => (await text('#llm-row .llmrow-skillnote')).includes('takes the place of Parseh'), 'a prompt in place of Parseh’s is said to be unable to travel');
        assert(await page.locator('#llm-row .llmrow-skill').isDisabled(), 'and the button is off');
      });

      await section('e) 1280 and 390, three themes', async () => {
        for (const w of [1280, 390]) {
          await page.setViewportSize({width: w, height: 900});
          for (const theme of ['light', 'dark', 'sepia']) {
            await door();
            await page.evaluate(t => { document.documentElement.setAttribute('data-theme', t); document.body.setAttribute('data-theme', t); }, theme);
            const wide = await page.evaluate(() => ({scroll: document.documentElement.scrollWidth, view: window.innerWidth}));
            assert(wide.scroll <= wide.view + 1, `${w}px ${theme}: no sideways scroll (${wide.scroll} in ${wide.view})`);
            const over = await page.evaluate(() => Array.from(document.querySelectorAll('main *')).filter(e => e.getBoundingClientRect().right > window.innerWidth + 1).length);
            eq(over, 0, `${w}px ${theme}: nothing wider than the screen`);
            const small = await page.evaluate(() => Array.from(document.querySelectorAll('main a.primary')).filter(e => { const r = e.getBoundingClientRect(); return r.height < 32; }).length);
            eq(small, 0, `${w}px ${theme}: the download is big enough to press`);
            // the words are readable against their ground in every theme (WCAG contrast of the computed colours)
            const ratios = await page.evaluate(() => {
              const rgb = c => { const m = c.match(/[\d.]+/g).map(Number); return {r: m[0], g: m[1], b: m[2], a: m.length > 3 ? m[3] : 1}; };
              const lum = ({r, g, b}) => { const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b); };
              const bg = el => { for (; el; el = el.parentElement) { const c = rgb(getComputedStyle(el).backgroundColor); if (c.a > 0.5) return c; } return {r: 255, g: 255, b: 255}; };
              return ['.tool .links a', '.sk .what', '.sk .facts', '.tool p', 'a.primary'].map(sel => {
                const el = document.querySelector('main ' + sel);
                const a = lum(rgb(getComputedStyle(el).color)), b = lum(bg(el));
                return [sel, Math.round((Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05) * 10) / 10];
              });
            });
            for (const [sel, ratio] of ratios) assert(ratio >= 4.5 || (sel === 'a.primary' && ratio >= 3), `${w}px ${theme}: ${sel} is readable against its ground (contrast ${ratio})`);
            await shot(`${w}-${theme}`);
          }
        }
        await page.setViewportSize(d.viewport);
      });

      await section('f) a reading only', async () => {
        await door();
        const r = await page.evaluate(() => fetch('/settings/api/skills/state', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}'}).then(r => r.status));
        eq(r, 405, 'a request that writes is not allowed at a reading');
        const r2 = await page.evaluate(() => fetch('/settings/api/skills/download?name=parseh-gloss', {method: 'POST'}).then(r => r.status));
        eq(r2, 405, 'nor at the download');
      });

      if (errors.length) failures.push(`${name}: page errors: ${errors.slice(0, 5).join(' | ')}`);
      await context.close();
    }
  } finally {
    await browser.close();
  }
}

const h = await startHarness();
try { await suite(h); } finally { await h.stop(); }
console.log(`\n${passed} ok, ${failures.length} FAIL`);
for (const f of failures) console.log('FAIL', f);
Deno.exit(failures.length ? 1 : 0);

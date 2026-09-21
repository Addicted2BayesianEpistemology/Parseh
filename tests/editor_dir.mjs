// Browser test of the direction of the studio editor's source (app.js
// initEdit, "⇤ RTL editor"), against the REAL routes (markdown/app/server.py)
// on a temporary library and exercises store (tests/decks_harness.py, studio
// mode), documents written through POST /api/docs:
//   a) by default the source goes the way its prose language (`lang:`) is
//      written -- Persian and Arabic prose right to left, from the right, in
//      the registry's face for them (Vazirmatn, Noto Naskh Arabic); English
//      and Italian prose left to right in the monospace -- and the button
//      says what a click does; the preview is not touched by any of it.
//      The face is the one the renderer draws the source's glyphs in (asked
//      through the DevTools protocol), not only the one the style names
//   b) the button turns it, the choice is remembered for the document
//      (parseh_editor_dir:<id>) and comes back on a reload, either way; right
//      to left with an English prose it takes the Persian target's face, and
//      with no right-to-left language at all (Japanese) it stays monospace
//   c) right to left, the panes still line up: the hidden mirror that counts
//      the wrapped rows has the textarea's direction and face, the rows it
//      counts are the rows the textarea has, and a source line scrolled to
//      brings its block in the preview to the same height
//   d) right to left, the whole source is: every line is drawn right to
//      left (a click at its right end puts the caret at its start, one at
//      its left end at its end) -- a Persian paragraph, a heading, a key
//      whose value is a Persian sentence (its key on the right, its full
//      stop on the left, where the sentence ends), and a line of the dialect
//      in Latin letters alone, a fence or an English `context:`, as any
//      right-to-left editor draws it (the fence's ::: on the right; the
//      English read left to right inside the line, its key where the
//      English starts and its full stop on the left) -- where each part of
//      a line sits measured in a copy of it laid out as the textarea lays
//      it out; typing, an insert at the cursor, Undo and Redo (the buttons
//      and the keys), and a picture dropped on the editor all work
//   e) with no choice made, a `lang:` typed into the front matter turns it
//   f) a new document: the choice made before its first save is kept with
//      its page (history.state, over a reload) and is its own after it
//      (parseh_editor_dir:<id>); the next new document starts from its own
//      `lang:` and follows one typed in, whatever was chosen for another
//   g) the exercise form's own direction buttons are their own
//   h) on a phone (390x844) the button is on the screen, a tap reaches it and
//      turns the source, and the page does not scroll sideways
//   CHROME_BIN=... PARSEH_PYTHON=python3 deno run --allow-all tests/editor_dir.mjs
//   SHOTS=<dir> saves the editor in both directions
import {chromium} from 'npm:playwright-core@1.52.0';

const root = await Deno.realPath(new URL('..', import.meta.url));
const python = Deno.env.get('PARSEH_PYTHON') || 'python3';
const SHOTS = Deno.env.get('SHOTS') || '';
let passed = 0;
const assert = (v, m) => { if (!v) throw Error('FAIL: ' + m); passed++; console.log('  ok', m); };
const sleep = ms => new Promise(r => setTimeout(r, ms));
const PNG_B64 = 'iVBORw0KGgoAAAANSUhEUgAAADwAAAAoCAIAAAAt2Q6oAAAAO0lEQVR42u3OQQkAAAgEsItjOjMZ1RQ+hMECLNXzTqSlpaWlpaWlpaWlpaWlpaWlpaWlpaWlpaWlpS8tUIta5t7QVXgAAAAASUVORK5CYII=';

// A Persian writing to teach English: Persian prose, English runs marked
const prosePara = 'فعل [to take off]{tl} یعنی «بلند شدن» هواپیما، یا «درآوردن» لباس. مثال: [The plane took off at six.]{tl} این جمله را چند بار بخوانید تا خوب یاد بگیرید.';
let PERSIAN = `---
title: English for Persians
lang: fa
target: en
---

:::exercise flashcard
prompt: این واژه را به یاد بسپارید.
card-type: vocab
target: [to take off]{tl}
meaning: بلند شدن، درآوردن
context: The plane took off at six.
:::
`;
for (let i = 1; i <= 8; i++)
  PERSIAN += `\n## درس ${i}\n\n${prosePara}\n\n- [to give up]{tl} = دست کشیدن\n- [to find out]{tl} = فهمیدن\n\n${prosePara} ${prosePara}\n`;
const ENGLISH = `---
title: Persian for English speakers
lang: en
target: fa
---

## Greetings

The everyday greeting is سلام, answered with سلام too.

خداحافظ is what is said on leaving.
`;
const ARABIC = `---
title: Le français pour les arabophones
lang: ar
target: fr
---

## التحية

نقول [bonjour]{tl} في الصباح و[bonsoir]{tl} في المساء.
`;
const JAPANESE = `---
title: Giapponese per italiani
lang: it
target: ja
---

## Saluti

Si dice [こんにちは]{kana:こんにちは translit:konnichiwa} di giorno.
`;

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
async function create(markdown) {
  const r = await fetch(B + '/api/docs', {method: 'POST', headers: {'Content-Type': 'application/json'},
                                          body: JSON.stringify({markdown})});
  const data = await r.json();
  if (!r.ok) throw Error('POST /api/docs: ' + JSON.stringify(data));
  return data.meta.id;
}
const docs = {Persian: await create(PERSIAN), English: await create(ENGLISH),
              Arabic: await create(ARABIC), Japanese: await create(JAPANESE)};

/* The source as it is drawn, and what the button says. */
const source = page => page.evaluate(() => {
  const src = document.querySelector('#src'), cs = getComputedStyle(src), btn = document.querySelector('#btn-editor-dir');
  const sheet = document.querySelector('#sheet');
  return {dir: cs.direction, align: cs.textAlign, face: cs.fontFamily.split(',')[0].replace(/["']/g, '').trim(),
          size: parseFloat(cs.fontSize), label: btn.textContent, title: btn.title,
          sheetDir: getComputedStyle(sheet).direction, sheetAttr: sheet.getAttribute('dir'),
          stored: Object.fromEntries(Object.keys(localStorage).filter(k => k.startsWith('parseh_editor_dir:'))
                                      .map(k => [k, localStorage.getItem(k)]))};
});
const rendered = page => page.waitForFunction(() => /rendered/.test(document.querySelector('#pv-status')?.textContent || ''),
                                               null, {timeout: 15000});
async function openEditor(page, id) {
  await page.goto(`${B}/doc/${id}/edit`);
  await rendered(page);
  await page.evaluate(() => document.fonts.ready);
  await sleep(250);                      // the panes lined up after the faces load
}
async function setSource(page, fn) {      // an edit typed into the textarea, as the input event says
  await page.locator('#src').evaluate((t, f) => {
    t.value = (new Function('v', 'return ' + f))(t.value);
    t.dispatchEvent(new Event('input', {bubbles: true}));
  }, fn);
}
/* The preview drawn again from the source, told by what it shows: the
   status line only says the second it was drawn in. */
const previewShows = async (page, fn, arg) => {
  await page.waitForFunction(fn, arg, {timeout: 15000});
  await sleep(150);
};
const prose = (page, code) => previewShows(page, c => document.querySelector('#sheet').lang === c, code);

/* The panes lined up: the rows the mirror counts against the rows the
   textarea really holds (its scroll height), and a source line brought to
   the height the editor's scroll keeps in step (35% down) against where its
   block in the preview comes to. */
const lineUp = page => page.evaluate(async () => {
  const src = document.querySelector('#src'), sc = document.querySelector('.preview-scroll');
  const mirror = document.querySelector('.src-mirror'), cs = getComputedStyle(src), ms = getComputedStyle(mirror);
  const lh = parseFloat(src.style.lineHeight), off = parseFloat(src.style.paddingTop);
  const rows = mirror.scrollHeight / 20;
  const counted = off + rows * lh + parseFloat(cs.paddingBottom);
  const blocks = [...document.querySelectorAll('#sheet [data-src-line]')];
  const el = blocks[Math.floor(blocks.length / 2)], line = +el.dataset.srcLine;
  const row = mirror.children[line].offsetTop / 20;
  src.scrollTop = off + row * lh - src.clientHeight * 0.35;
  await new Promise(r => setTimeout(r, 400));
  return {mirrorDir: ms.direction, mirrorFace: ms.fontFamily === cs.fontFamily, lh, rows,
          counted: Math.round(counted), real: src.scrollHeight, line,
          want: Math.round(sc.clientHeight * 0.35), got: Math.round(el.getBoundingClientRect().top - sc.getBoundingClientRect().top)};
});

/* The faces the source's text is really drawn in, most glyphs first: the
   renderer's own answer (CSS.getPlatformFontsForNode, on the inner editor a
   textarea keeps its text in, in a shadow root of the browser's own).  A
   face the style names but the page could not load is not among them.
   `web` is a face the page loaded (@font-face), as against the system's. */
async function drawnFaces(page) {
  await page.evaluate(async () => {
    document.querySelector('#src').offsetHeight;  // a face just named starts loading
    await document.fonts.ready;
  });
  const cdp = await page.context().newCDPSession(page);
  try {
    await cdp.send('DOM.enable');
    await cdp.send('CSS.enable');
    const {root} = await cdp.send('DOM.getDocument', {depth: -1, pierce: true});
    const find = n => n.nodeName === 'TEXTAREA' && (n.attributes || []).join(' ').includes('id src') ? n
      : [...(n.children || []), ...(n.shadowRoots || [])].reduce((f, c) => f || find(c), null);
    const inner = find(root).shadowRoots[0].children.find(c => c.nodeName === 'DIV');
    const {fonts} = await cdp.send('CSS.getPlatformFontsForNode', {nodeId: inner.nodeId});
    return fonts.sort((a, b) => b.glyphCount - a.glyphCount)
                .map(f => ({family: f.familyName, web: f.isCustomFont, glyphs: f.glyphCount}));
  } finally {
    await cdp.detach();
  }
}
const drawnIn = (faces, family) => faces.some(f => f.family === family && f.web);
const named = faces => faces.map(f => `${f.family}${f.web ? '' : ' (system)'} ${f.glyphs}`).join(', ');

/* Where a click at the right end of a source line puts the caret, counted
   from the line's start: the letter drawn rightmost is a line's last when
   the line runs left to right, its first when it runs right to left.  The
   click is a real one, on the textarea as it is drawn. */
async function caretAt(page, text, side) {
  const at = await page.evaluate(async ([t, side]) => {
    const src = document.querySelector('#src'), mirror = document.querySelector('.src-mirror');
    const lines = src.value.split('\n'), i = lines.indexOf(t);
    const start = lines.slice(0, i).reduce((n, l) => n + l.length + 1, 0);
    const cs = getComputedStyle(src), lh = parseFloat(cs.lineHeight), off = parseFloat(cs.paddingTop);
    const row = mirror.children[i].offsetTop / 20;
    src.scrollTop = Math.max(0, off + row * lh - src.clientHeight / 3);
    await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
    const R = src.getBoundingClientRect();
    return {i, start, y: R.top + src.clientTop + off + row * lh - src.scrollTop + lh / 2,
            x: side === 'right' ? R.left + src.clientLeft + src.clientWidth - parseFloat(cs.paddingRight) - 2
                                : R.left + src.clientLeft + parseFloat(cs.paddingLeft) + 2};
  }, [text, side]);
  if (at.i < 0) throw Error('no source line ' + text);
  await page.mouse.click(at.x, at.y);
  return await page.locator('#src').evaluate(t => t.selectionStart) - at.start;
}

/* Where the parts of a source line are drawn, from the right: the middle
   of each one's letters, across the page.  A click only tells which way a
   line runs, not where its key or its full stop sits in it; a textarea
   gives no box for a letter of it, so the line is drawn again, for the
   moment it is measured, in a copy laid out as the textarea lays out its
   text -- its face and size, its direction and bidi, its alignment and
   width -- over the textarea itself.  A part is found from the line's
   start, the full stop (".") from its end. */
async function drawnAt(page, text, parts) {
  return await page.evaluate(([t, parts]) => {
    const src = document.querySelector('#src'), cs = getComputedStyle(src), R = src.getBoundingClientRect();
    const copy = document.createElement('div');
    for (const p of ['direction', 'unicodeBidi', 'fontFamily', 'fontSize', 'fontWeight', 'fontStyle', 'lineHeight',
                     'letterSpacing', 'wordSpacing', 'textAlign', 'tabSize', 'whiteSpace', 'overflowWrap', 'wordBreak',
                     'paddingLeft', 'paddingRight', 'color', 'backgroundColor'])
      copy.style[p] = cs[p];
    Object.assign(copy.style, {position: 'fixed', left: R.left + src.clientLeft + 'px', top: R.top + src.clientTop + 'px',
                               width: src.clientWidth + 'px', boxSizing: 'border-box', zIndex: 1000});
    copy.textContent = t;
    document.body.append(copy);
    const range = document.createRange();
    const xs = parts.map(p => {
      const i = p === '.' ? t.lastIndexOf('.') : t.indexOf(p);
      range.setStart(copy.firstChild, i);
      range.setEnd(copy.firstChild, i + p.length);
      const r = range.getBoundingClientRect();
      return r.left + r.width / 2;
    });
    copy.remove();
    return xs;
  }, [text, parts]);
}

const browser = await chromium.launch({executablePath: Deno.env.get('CHROME_BIN') || undefined, headless: true});
const pageErrors = [];
try {
  const ctx = await browser.newContext({viewport: {width: 1400, height: 900}});
  const page = await ctx.newPage();
  page.on('pageerror', e => pageErrors.push(e.message));
  page.on('dialog', d => d.accept());

  // ------------------------------------------------ a) the default
  console.log('a) the prose language decides until a choice is made');
  const sheetBefore = {};
  for (const [name, dir, face] of [['Persian', 'rtl', 'Vazirmatn'], ['Arabic', 'rtl', 'Noto Naskh Arabic'],
                                   ['English', 'ltr', 'ui-monospace'], ['Japanese', 'ltr', 'ui-monospace']]) {
    await openEditor(page, docs[name]);
    const s = await source(page);
    assert(s.dir === dir && s.align === (dir === 'rtl' ? 'right' : 'start') && s.face === face,
           `${name} prose: the source is ${s.dir}, aligned ${s.align}, in ${s.face}`);
    const faces = await drawnFaces(page);
    assert(dir === 'rtl' ? drawnIn(faces, face) : !faces.some(f => f.web),
           `${name} prose: and drawn in ${dir === 'rtl' ? face + ', loaded by the page' : 'the system\'s monospace, no face of the page'} (${named(faces)})`);
    assert(s.label === (dir === 'rtl' ? '⇥ LTR editor' : '⇤ RTL editor')
           && s.title.startsWith(`The source is written ${dir === 'rtl' ? 'right to left' : 'left to right'}. Click to write it`),
           `${name} prose: the button says what a click does ("${s.label}") and the title what the source is`);
    assert(s.sheetDir === 'ltr' && s.sheetAttr === null && !Object.keys(s.stored).length,
           `${name} prose: the preview keeps its own direction, and nothing is stored before a choice`);
    sheetBefore[name] = await page.locator('#sheet').innerHTML();
    if (SHOTS) await page.screenshot({path: `${SHOTS}/editor-${name}-default.png`});
  }

  // ------------------------------------------------ b) the button, remembered
  console.log('b) the button turns it, and the document remembers');
  await openEditor(page, docs.English);
  await page.click('#btn-editor-dir');
  let s = await source(page);
  assert(s.dir === 'rtl' && s.align === 'right' && s.face === 'Vazirmatn' && s.label === '⇥ LTR editor',
         `English prose turned right to left: from the right, in the Persian target's face (${s.face})`);
  let faces = await drawnFaces(page);
  assert(drawnIn(faces, 'Vazirmatn'), `and its text is drawn in Vazirmatn, loaded when it was turned (${named(faces)})`);
  assert(s.stored[`parseh_editor_dir:${docs.English}`] === 'rtl', 'the choice is stored for this document');
  assert(await page.locator('#sheet').innerHTML() === sheetBefore.English && s.sheetDir === 'ltr',
         'the preview is drawn exactly as before');
  assert(await page.evaluate(() => document.activeElement.id) === 'src', 'the writing goes on in the source');
  if (SHOTS) await page.screenshot({path: `${SHOTS}/editor-English-rtl.png`});
  await openEditor(page, docs.English);
  s = await source(page);
  assert(s.dir === 'rtl' && s.label === '⇥ LTR editor', 'reloaded, the English document is still written right to left');
  await page.click('#btn-editor-dir');
  await openEditor(page, docs.English);
  s = await source(page);
  assert(s.dir === 'ltr' && s.face === 'ui-monospace' && s.stored[`parseh_editor_dir:${docs.English}`] === 'ltr',
         'turned back and reloaded: left to right, monospace, and that is stored too');
  await openEditor(page, docs.Persian);
  await page.click('#btn-editor-dir');
  await openEditor(page, docs.Persian);
  s = await source(page);
  assert(s.dir === 'ltr' && s.label === '⇤ RTL editor', 'a Persian document turned left to right stays so over its prose language');
  await page.click('#btn-editor-dir');
  await openEditor(page, docs.Japanese);
  await page.click('#btn-editor-dir');
  s = await source(page);
  assert(s.dir === 'rtl' && s.face === 'ui-monospace',
         'with no right-to-left language to take a face from (Italian prose, Japanese target), it stays monospace');
  await page.click('#btn-editor-dir');

  // ------------------------------------------------ c) the panes line up
  console.log('c) right to left, the panes still line up');
  for (const turn of [false, true]) {
    await openEditor(page, docs.Persian);
    if (turn) { await page.click('#btn-editor-dir'); await sleep(250); }
    const want = turn ? 'ltr' : 'rtl';
    const a = await lineUp(page);
    assert(a.mirrorDir === want && a.mirrorFace, `${want}: the mirror counting the rows has the textarea's direction and face`);
    assert(Math.abs(a.counted - a.real) <= a.lh / 2,
           `${want}: the ${a.rows} rows it counts are the textarea's (${a.counted} px counted, ${a.real} px there)`);
    assert(Math.abs(a.got - a.want) <= 4,
           `${want}: source line ${a.line + 1} scrolled to brings its block to the same height in the preview (${a.got} px for ${a.want})`);
  }
  await page.click('#btn-editor-dir');     // back to the prose language's own, right to left

  // ------------------------------------------------ d) writing right to left
  console.log('d) typing, inserting, Undo and Redo, a picture dropped');
  await openEditor(page, docs.Persian);
  assert((await source(page)).dir === 'rtl', 'the Persian document is written right to left');
  // (a line of one row: a click past either end of it lands at that end;
  // and its parts, from the right, where each is drawn)
  for (const [line, what, order] of [
    ['prompt: این واژه را به یاد بسپارید.', 'its key on the right, its full stop on the left, where the Persian sentence ends', ['prompt', 'این', '.']],
    ['meaning: بلند شدن، درآوردن', 'its key on the right, the Persian after it', ['meaning', 'بلند']],
    ['## درس 1', 'its ## on the right', ['##', 'درس']],
    [':::exercise flashcard', 'a fence in Latin letters alone, its ::: on the right', [':::', 'exercise']],
    ['context: The plane took off at six.', 'an English sentence read left to right inside it, its key where the English starts, left of "six", and its full stop on the left', ['six', 'context', '.']],
    ['title: English for Persians', 'the front matter', null]]) {
    const right = await caretAt(page, line, 'right'), left = await caretAt(page, line, 'left');
    assert(right === 0 && left === line.length,
           `"${line}" is drawn right to left: a click at its right end is at its start (${right}),`
           + ` one at its left end at its end (${left} of ${line.length})`);
    if (!order) continue;
    const xs = await drawnAt(page, line, order);
    assert(xs.every((x, k) => !k || x < xs[k - 1] - 1),
           `"${line}", ${what}: from the right, ${order.map((p, k) => `"${p}" at ${Math.round(xs[k])}`).join(', ')}`);
  }
  // (a paragraph of several rows: its first row starts on the right)
  assert(await caretAt(page, prosePara, 'right') === 0, `"${prosePara.slice(0, 24)}…" is drawn right to left: its first mark is the rightmost`);
  const bidi = await page.evaluate(() => [document.querySelector('#src'), document.querySelector('.src-mirror > div')]
    .map(e => getComputedStyle(e).unicodeBidi));
  assert(bidi[0] !== 'plaintext' && bidi[1] === bidi[0],
         `no line takes a direction of its own from its first letter, in the textarea or in the mirror counting its rows (${bidi.join(', ')})`);
  const src = page.locator('#src');
  await src.focus();
  await page.keyboard.press('Control+End');
  await page.keyboard.type('\n\nسلام دنیا، این یک آزمایش است.');
  await previewShows(page, () => document.querySelector('#sheet').textContent.includes('سلام دنیا، این یک آزمایش است.'));
  assert((await src.inputValue()).endsWith('\n\nسلام دنیا، این یک آزمایش است.')
         && (await page.locator('#sheet').textContent()).includes('سلام دنیا، این یک آزمایش است.'),
         'typed at the end: in the source, and drawn in the preview');
  await sleep(800);                          // a step of its own in the history
  await page.click('#ins-guill');
  let v = await src.inputValue(), at = await src.evaluate(t => t.selectionStart);
  assert(v.endsWith('است.«»') && at === v.length - 1, 'an insert goes in at the cursor, the cursor inside it');
  await page.click('#btn-undo');
  assert((await src.inputValue()).endsWith('است.'), 'Undo takes the insert out');
  await page.click('#btn-redo');
  assert((await src.inputValue()).endsWith('است.«»'), 'Redo puts it back');
  await src.focus();
  await page.keyboard.press('Control+z');
  assert((await src.inputValue()).endsWith('است.'), 'and so does Ctrl+Z');
  await page.keyboard.press('Control+y');
  assert((await src.inputValue()).endsWith('است.«»'), 'and Ctrl+Y');
  await page.keyboard.press('Control+End');      // the picture goes in after the «», not inside it
  await src.evaluate((t, b64) => {
    const bytes = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
    const dt = new DataTransfer();
    dt.items.add(new File([bytes], 'dot.png', {type: 'image/png'}));
    for (const type of ['dragover', 'drop'])
      t.dispatchEvent(new DragEvent(type, {dataTransfer: dt, bubbles: true, cancelable: true}));
  }, PNG_B64);
  await page.waitForFunction(() => /images\/dot\.png/.test(document.querySelector('#src').value), null, {timeout: 8000});
  await previewShows(page, () => !!document.querySelector('#sheet img[src$="/images/dot.png"]'));
  assert(await page.locator('#sheet img[src$="/images/dot.png"]').count() === 1,
         'a picture dropped on the editor is stored, embedded in the source and drawn in the preview');
  await page.click('#btn-save');
  await page.waitForFunction(() => /Saved/.test(document.querySelector('#toast')?.textContent || ''), null, {timeout: 8000});
  const saved = await (await fetch(`${B}/download/${docs.Persian}/md`)).text();
  assert(saved.includes('سلام دنیا، این یک آزمایش است.«»') && saved.includes('images/dot.png'), 'and Save writes all of it');

  // ------------------------------------------------ e) a lang: typed
  console.log('e) a `lang:` typed into the front matter');
  await openEditor(page, docs.English);
  await page.evaluate(() => localStorage.removeItem(Object.keys(localStorage).find(k => k.endsWith(document.body.dataset.docId))));
  await openEditor(page, docs.English);
  assert((await source(page)).dir === 'ltr', 'no choice made: the English prose is written left to right');
  await setSource(page, "v.replace(/^lang: en$/m, 'lang: fa')");
  await prose(page, 'fa');
  s = await source(page);
  assert(s.dir === 'rtl' && s.face === 'Vazirmatn' && !(`parseh_editor_dir:${docs.English}` in s.stored),
         '`lang: fa` typed in: the source turns right to left, in Vazirmatn, and nothing is stored');
  faces = await drawnFaces(page);
  assert(drawnIn(faces, 'Vazirmatn'), `and it is drawn in it (${named(faces)})`);
  await setSource(page, "v.replace(/^lang: fa$/m, 'lang: en')");
  await prose(page, 'en');
  assert((await source(page)).dir === 'ltr', 'and `lang: en` typed back turns it back');
  await page.click('#btn-editor-dir');
  await setSource(page, "v.replace(/^lang: en$/m, 'lang: it')");
  await prose(page, 'it');
  assert((await source(page)).dir === 'rtl', 'once chosen, the choice stands whatever `lang:` says');
  await setSource(page, "v.replace(/^lang: it$/m, 'lang: en')");
  await ctx.close();

  // ------------------------------------------------ f) a new document
  console.log('f) a new document');
  {
    const ctx = await browser.newContext({viewport: {width: 1400, height: 900}});
    const page = await ctx.newPage();
    page.on('pageerror', e => pageErrors.push(e.message));
    page.on('dialog', d => d.accept());      // leaving a new document written into
    const kept = () => page.evaluate(() => (history.state || {}).editorDir || null);
    await page.goto(`${B}/new?target=fa`);
    await rendered(page);
    assert((await source(page)).dir === 'ltr', 'a new document starts the way its starter\'s prose (English) is written');
    await page.click('#btn-editor-dir');
    s = await source(page);
    assert(s.dir === 'rtl' && await kept() === 'rtl' && !Object.keys(s.stored).length,
           'turned before it has an id: kept with its page, nothing stored for every new document');
    await page.reload();
    await rendered(page);
    assert((await source(page)).dir === 'rtl', 'reloaded, the page still has its choice');
    await setSource(page, "v.replace(/^title:.*$/m, 'title: A new one')");
    await Promise.all([page.waitForURL(/\/doc\/[^/]+\/edit$/), page.click('#btn-save')]);
    const id = decodeURIComponent(new URL(page.url()).pathname.split('/')[2]);
    await rendered(page);
    s = await source(page);
    assert(s.dir === 'rtl' && s.stored[`parseh_editor_dir:${id}`] === 'rtl' && Object.keys(s.stored).length === 1,
           `saved, it is document ${id}, and the choice is its own (parseh_editor_dir:${id}) and only its own`);
    await page.goto(`${B}/new?target=it`);
    await rendered(page);
    s = await source(page);
    assert(s.dir === 'ltr' && await kept() === null,
           'the next new document starts from its own prose language (English, left to right), not from that choice');
    await setSource(page, "v.replace(/^lang:.*$/m, 'lang: fa')");
    await prose(page, 'fa');
    assert((await source(page)).dir === 'rtl', 'and follows a `lang: fa` typed in: right to left');
    await page.click('#btn-editor-dir');
    assert((await source(page)).dir === 'ltr' && await kept() === 'ltr', 'turned left to right on this page');
    await page.goto(`${B}/new?target=fa`);
    await rendered(page);
    await setSource(page, "v.replace(/^lang:.*$/m, 'lang: fa')");
    await prose(page, 'fa');
    s = await source(page);
    assert(s.dir === 'rtl' && await kept() === null && !('parseh_editor_dir:new' in s.stored),
           'a third new document with `lang: fa` is written right to left: the second one\'s choice stayed with it');
    await ctx.close();
  }

  // ------------------------------------------------ g) the exercise form's own buttons
  console.log('g) the exercise form\'s direction buttons are their own');
  {
    const ctx = await browser.newContext({viewport: {width: 1400, height: 900}});
    const page = await ctx.newPage();
    page.on('pageerror', e => pageErrors.push(e.message));
    await openEditor(page, docs.Persian);
    await page.click('details.dropdown > summary');
    await page.click('#btn-exercise');
    await page.locator('.ex-type', {hasText: 'Embedded vocabulary flashcard'}).click();
    await page.waitForSelector('.ex-form-modal');
    const field = page.locator('.ex-form-modal .ex-dir-field').first();
    const before = await field.locator('textarea, input[type="text"]').first().evaluate(i => i.dir);
    await field.locator('.ex-text-direction').click();
    const after = await field.locator('textarea, input[type="text"]').first().evaluate(i => getComputedStyle(i).direction);
    assert(before === 'auto' && after === 'rtl' && (await source(page)).dir === 'rtl',
           `a field of the form starts dir=auto whatever the editor's direction, and its own button turns it alone (${after})`);
    await ctx.close();
  }

  // ------------------------------------------------ h) on a phone
  console.log('h) on a phone');
  {
    const ctx = await browser.newContext({viewport: {width: 390, height: 844}, isMobile: true, hasTouch: true});
    const page = await ctx.newPage();
    page.on('pageerror', e => pageErrors.push(e.message));
    await openEditor(page, docs.Persian);
    const place = () => page.locator('#btn-editor-dir').evaluate(b => {
      const r = b.getBoundingClientRect(), hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
      return {l: r.left, r: r.right, t: r.top, b: r.bottom, reached: hit === b || b.contains(hit),
              sideways: document.documentElement.scrollWidth > document.documentElement.clientWidth};
    });
    const p = await place();
    assert(p.reached && p.l >= 0 && p.r <= 390 && p.t >= 0 && p.b <= 844 && !p.sideways,
           `the button is on the screen (${Math.round(p.l)}–${Math.round(p.r)} × ${Math.round(p.t)}–${Math.round(p.b)}), a tap reaches it, nothing scrolls sideways`);
    assert((await source(page)).dir === 'rtl', 'the Persian document is written right to left on a phone too');
    if (SHOTS) await page.screenshot({path: `${SHOTS}/editor-phone-rtl.png`});
    await page.locator('#btn-editor-dir').tap();
    s = await source(page);
    assert(s.dir === 'ltr' && s.stored[`parseh_editor_dir:${docs.Persian}`] === 'ltr', 'a tap turns it left to right');
    if (SHOTS) await page.screenshot({path: `${SHOTS}/editor-phone-ltr.png`});
    await ctx.close();
  }

  assert(!pageErrors.length, 'no page errors' + (pageErrors.length ? ': ' + pageErrors.join('; ') : ''));
  console.log(`editor direction passed (${passed} checks)`);
} finally {
  await browser.close();
  proc.kill('SIGTERM');
  await proc.status;
}

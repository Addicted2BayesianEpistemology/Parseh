// SPDX-License-Identifier: GPL-3.0-or-later
// The authoring sheet for a ::::latex drawing: preview left of source on a
// desktop, source then preview on a phone, folded placement controls, and a
// footer that remains in the dialog.  It drives the real temporary Studio
// harness and real XeLaTeX; no document is saved and no owner setting moves.
//
// CHROME_BIN=... PARSEH_PYTHON=python3 deno run --allow-all tests/latex_sheet.mjs
// L7_MODES=studio (or parseh) limits it to one mount.  SHOTS=<dir> retains
// the desktop and phone views for the required visual check.
import {chromium} from 'npm:playwright-core@1.52.0';

const root = await Deno.realPath(new URL('..', import.meta.url));
const python = Deno.env.get('PARSEH_PYTHON') || 'python3';
const modes = (Deno.env.get('L7_MODES') || 'studio,parseh').split(',');
const shots = Deno.env.get('SHOTS') || '';
let passed = 0;
const assert = (value, message) => {
  if (!value) throw Error('FAIL: ' + message);
  passed++;
  console.log('  ok', message);
};
const eq = (got, want, message) => assert(got === want,
  `${message} (got ${JSON.stringify(got)}, want ${JSON.stringify(want)})`);

const hasTeX = await new Deno.Command('xelatex', {args: ['--version'], stdout: 'null', stderr: 'null'}).output()
  .then(r => r.success, () => false);
if (!hasTeX) {
  console.log('SKIP: no xelatex on this computer -- the drawing preview needs XeLaTeX (tests/latex_sheet.mjs)');
  Deno.exit(0);
}
if (shots) await Deno.mkdir(shots, {recursive: true});

async function startHarness(mode, extra = []) {
  const proc = new Deno.Command(python, {args: [root + '/tests/studio_harness.py', mode, ...extra], cwd: root,
                                         stdout: 'piped', stderr: 'piped'}).spawn();
  const log = [];
  (async () => {
    const reader = proc.stderr.pipeThrough(new TextDecoderStream()).getReader();
    for (;;) {
      const {value, done} = await reader.read();
      if (done) break;
      log.push(value);
    }
  })();
  const reader = proc.stdout.pipeThrough(new TextDecoderStream()).getReader();
  let all = '', info = null;
  while (!info) {
    const {value, done} = await reader.read();
    if (done) throw Error(`harness (${mode}) ended before READY:\n${all}${log.join('')}`);
    all += value;
    const match = all.match(/READY (\{.*\})\n/);
    if (match) info = JSON.parse(match[1]);
  }
  (async () => { for (;;) { const next = await reader.read(); if (next.done) break; } })();
  return {proc, info, log};
}

async function suite(mode) {
  console.log(`\n== ${mode} ==`);
  const {proc, info, log} = await startHarness(mode);
  const origin = `http://127.0.0.1:${info.port}`, base = info.studio;
  const url = path => origin + base + path;
  const browser = await chromium.launch({executablePath: Deno.env.get('CHROME_BIN'), headless: true});
  try {
    const context = await browser.newContext({viewport: {width: 1280, height: 900}});
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(url(`/doc/${info.rich_doc_id}/edit`));
    await page.waitForSelector('#btn-latex-editor');

    // A new block defaults to the compact, natural-size route.  The preview
    // is nevertheless large enough to inspect and its controls do not make
    // the source move beneath the actions.
    await page.click('#btn-latex-editor');
    // an <option> inside a closed <select> reports an empty box in headless
    // Chromium, so the default visible-state wait never resolves: attached is
    // what a select's own option can promise (tests/latex_drawings.mjs:155).
    await page.waitForSelector('.latex-modal .lx-theme option', {state: 'attached'});
    await page.fill('.latex-modal .lx-src', '$\\displaystyle\\frac{1}{1+x^2}$');
    await page.waitForSelector('.latex-modal .lx-stage img', {timeout: 30000});
    await page.waitForFunction(() => { const i = document.querySelector('.lx-stage img'); return i && i.complete && i.naturalWidth > 0; });
    const desktop = await page.evaluate(() => {
      const bounds = selector => {
        const el = document.querySelector(selector), r = el && el.getBoundingClientRect();
        return r && {left: r.left, top: r.top, right: r.right, bottom: r.bottom, width: r.width, height: r.height};
      };
      return {
        preview: bounds('.lx-preview-pane'), editor: bounds('.lx-editor-pane'),
        stage: bounds('.lx-stage'), body: bounds('.latex-modal-body'), footer: bounds('.latex-modal-actions'),
        modal: bounds('.latex-modal'), layoutOpen: document.querySelector('.lx-layout').open,
        natural: document.querySelector('.lx-natural').checked,
        sizeButtons: document.querySelectorAll('[data-lx-preview], .lx-preview-size').length,
        image: (() => {
          // what the eye sees: the picture's own box against the stage's inner width
          const img = document.querySelector('.lx-stage img'), stage = document.querySelector('.lx-stage');
          const cs = getComputedStyle(stage), r = img.getBoundingClientRect();
          const inner = stage.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
          return {width: r.width, height: r.height, inner, w: +img.style.getPropertyValue('--lx-w'),
                  naturalWidth: img.naturalWidth, naturalHeight: img.naturalHeight};
        })(),
      };
    });
    assert(desktop.preview.right <= desktop.editor.left + 1 && desktop.preview.top < desktop.editor.bottom,
           `desktop: preview is the left column (${JSON.stringify(desktop.preview)} / ${JSON.stringify(desktop.editor)})`);
    assert(desktop.stage.width >= desktop.preview.width - 50 && desktop.stage.height >= 250,
           `desktop: preview has usable room (${Math.round(desktop.stage.width)} × ${Math.round(desktop.stage.height)})`);
    assert(!desktop.layoutOpen && desktop.natural, 'a new drawing leaves Size and position folded at its natural size');
    // the owner: the sheet's preview scales the drawing to its pane; natural size is for the page.
    // (The first version of this suite measured the stage, never the picture, and passed while the
    // water drawing sat at 63 x 26 px in a 560 x 400 stage.)
    assert(desktop.sizeButtons === 0, 'the preview has no Fit / Actual size buttons: it always fills its pane');
    assert(desktop.image.w > 5 && desktop.image.width >= 0.7 * desktop.image.inner,
           `a small drawing (${desktop.image.w} pt wide) is scaled up to fill the pane: ${Math.round(desktop.image.width)} of ${Math.round(desktop.image.inner)} px`);
    assert(Math.abs(desktop.image.height / desktop.image.width - desktop.image.naturalHeight / desktop.image.naturalWidth) < 0.02,
           'scaled with its own proportions');
    assert(desktop.image.width <= desktop.image.w * 12 + 1, 'and never past twelve times its own size');
    assert(desktop.footer.top >= desktop.body.bottom - 2 && desktop.footer.bottom <= desktop.modal.bottom + 1,
           'the Cancel and Insert footer is outside the scrolling body and stays in the dialog');
    if (shots) await page.screenshot({path: `${shots}/latex-sheet-${mode}-desktop.png`});

    // A drawing is black ink on nothing: read its real pixels through the
    // filter the page applies, on the paper sheet and on the dark one.
    const ink = () => page.evaluate(async () => {
      const img = document.querySelector('.lx-preview-image');
      const c = document.createElement('canvas');
      c.width = 200; c.height = Math.max(1, Math.round(200 * img.naturalHeight / img.naturalWidth));
      const ctx = c.getContext('2d');
      ctx.filter = getComputedStyle(img).filter;
      ctx.drawImage(img, 0, 0, c.width, c.height);
      const px = ctx.getImageData(0, 0, c.width, c.height).data;
      let sum = 0, n = 0;
      for (let i = 0; i < px.length; i += 4) if (px[i + 3] > 200) { sum += (px[i] + px[i + 1] + px[i + 2]) / 3; n++; }
      return {n, mean: n ? sum / n : -1};
    });
    const paperInk = await ink();
    await page.evaluate(() => { document.body.dataset.theme = 'dark'; });
    const darkInk = await ink();
    if (shots) await page.screenshot({path: `${shots}/latex-sheet-${mode}-dark.png`});
    await page.evaluate(() => { document.body.dataset.theme = 'paper'; });
    assert(paperInk.n > 50 && paperInk.mean < 60, `on the paper sheet a drawing's ink is dark (mean ${Math.round(paperInk.mean)})`);
    assert(darkInk.n > 50 && darkInk.mean > 180, `on the dark sheet a drawing's ink is light, not black on dark (mean ${Math.round(darkInk.mean)})`);

    // Reopening a block that already has a non-default shape reveals the
    // placement controls rather than concealing why it lands where it does.
    await page.click('.latex-modal [data-x="cancel"]');
    await page.waitForSelector('.latex-modal', {state: 'detached'});
    await page.evaluate(() => openLatexOverlay({tex: '$x^2$', layout: {width: 45, align: 'left', offset: 8},
                                                onSave: () => {}}));
    await page.waitForSelector('.latex-modal .lx-theme option', {state: 'attached'});
    const existing = await page.evaluate(() => ({
      open: document.querySelector('.lx-layout').open,
      width: document.querySelector('.lx-width').value,
      align: document.querySelector('.lx-align').value,
      offset: document.querySelector('.lx-offset').value,
    }));
    assert(existing.open && existing.width === '45' && existing.align === 'left' && existing.offset === '8',
           `an existing non-default layout opens Size and position (${JSON.stringify(existing)})`);

    // THE CAPTION is content, not layout: a field of its own under the LaTeX and above the folded
    // section, filled from the block it reopens, written as caption="…" in the braces.
    await page.click('.latex-modal [data-x="cancel"]');
    await page.waitForSelector('.latex-modal', {state: 'detached'});
    await page.evaluate(() => {
      window.__saved = null;
      openLatexOverlay({tex: '\\ce{H2O}', layout: {width: 45, align: 'left', caption: 'Water & *care*'},
                        onSave: text => { window.__saved = text; }});
    });
    await page.waitForSelector('.latex-modal .lx-theme option', {state: 'attached'});
    const field = await page.evaluate(() => {
      const box = s => document.querySelector(s).getBoundingClientRect();
      const cap = document.querySelector('.lx-caption');
      return {src: box('.lx-src').bottom, top: box('.lx-caption').top, bottom: box('.lx-caption').bottom,
              width: box('.lx-caption').width, layout: box('.lx-layout').top, value: cap.value,
              folded: !!cap.closest('details'), label: cap.closest('label').textContent.trim().split('\n')[0]};
    });
    assert(field.width > 100 && !field.folded && field.src <= field.top && field.bottom <= field.layout,
           `the caption field is visible, under the LaTeX and above Size and position (${JSON.stringify(field)})`);
    eq(field.value, 'Water & *care*', 'it opens with the caption of the block being edited');
    await page.click('.latex-modal [data-x="ok"]');
    eq(await page.evaluate(() => window.__saved),
       '::::latex {width=45 align=left caption="Water & *care*"}\n\\ce{H2O}\n::::',
       'Save writes it in the braces, in double quotes, beside the layout');
    await page.evaluate(() => openLatexOverlay({tex: '\\ce{H2O}', theme: '', onSave: text => { window.__saved = text; }}));
    await page.waitForSelector('.latex-modal .lx-theme option', {state: 'attached'});
    eq(await page.inputValue('.latex-modal .lx-caption'), '', 'a new drawing has no caption');
    await page.click('.latex-modal [data-x="ok"]');
    eq(await page.evaluate(() => window.__saved), '::::latex\n\\ce{H2O}\n::::', 'and writes none');
    await page.evaluate(() => openLatexOverlay({tex: '\\ce{H2O}', onSave: text => { window.__saved = text; }}));
    await page.waitForSelector('.latex-modal .lx-theme option', {state: 'attached'});
    await page.fill('.latex-modal .lx-caption', 'He said "hi"');
    eq(await page.inputValue('.latex-modal .lx-caption'), 'He said ”hi”',
       'a typed " becomes ” at once: the dialect has no escape inside the quotes');
    await page.click('.latex-modal [data-x="ok"]');
    eq(await page.evaluate(() => window.__saved), '::::latex {caption="He said ”hi”"}\n\\ce{H2O}\n::::',
       'so what is written reads back as it was typed');
    // a card's sheet (no offset) takes one too
    await page.evaluate(() => openLatexOverlay({tex: 'x', offset: false, layout: {caption: 'On a card'},
                                                onSave: text => { window.__saved = text; }}));
    await page.waitForSelector('.latex-modal .lx-theme option', {state: 'attached'});
    await page.click('.latex-modal [data-x="ok"]');
    eq(await page.evaluate(() => window.__saved), '::::latex {caption="On a card"}\nx\n::::', 'the card sheet keeps its caption');

    // ...and the pencil on a rendered drawing brings a caption back, and editing it draws nothing again
    const block = '\n\n::::latex chemistry {width=45 caption="Kept *as* written"}\n\\ce{2H2 + O2 -> 2H2O}\n::::\n';
    await page.locator('#src').fill((await page.locator('#src').inputValue()) + block);
    await page.waitForSelector('#sheet figure.latex figcaption', {timeout: 60000});
    eq(await page.locator('#sheet figure.latex figcaption').innerText(), 'Kept as written', 'the preview sets the caption under the drawing');
    const drawing = () => page.locator('#sheet figure.latex img').getAttribute('src');
    const before = await drawing();
    const figure = page.locator('#sheet figure.latex[data-latex-src]').first();
    await figure.scrollIntoViewIfNeeded();
    await figure.hover();
    const pencil = page.locator('button.rtl-edit-btn').filter({hasText: '✎'});
    await pencil.first().waitFor({state: 'visible'});
    await pencil.first().click();
    await page.waitForSelector('.latex-modal .lx-caption');
    eq(await page.inputValue('.latex-modal .lx-caption'), 'Kept *as* written', 'the pencil reopens the block with its caption');
    await page.waitForSelector('.latex-modal .lx-theme option', {state: 'attached'});
    eq(await page.inputValue('.latex-modal .lx-theme'), 'chemistry', 'and its theme');
    eq(await page.inputValue('.latex-modal .lx-width'), '45', 'and its width');
    await page.fill('.latex-modal .lx-caption', 'Edited, the same drawing');
    await page.click('.latex-modal [data-x="ok"]');
    await page.waitForSelector('.latex-modal', {state: 'detached'});
    const rewritten = await page.locator('#src').inputValue();
    assert(rewritten.includes('::::latex chemistry {width=45 caption="Edited, the same drawing"}\n\\ce{2H2 + O2 -> 2H2O}\n::::'),
           'saving writes the edited caption back over the block it came from: ' + JSON.stringify(rewritten.slice(-200)));
    await page.waitForFunction(() => /Edited, the same drawing/.test(document.querySelector('#sheet figure.latex figcaption')?.textContent || ''),
                               null, {timeout: 60000});
    eq(await drawing(), before, 'a caption edit drew nothing again: the drawing is the same file');

    // A phone has one readable column: author first, preview next, its action
    // footer still wholly on-screen and no horizontal page scroll.
    await page.evaluate(() => openLatexOverlay({tex: '$\\displaystyle\\frac{1}{1+x^2}$', layout: {caption: 'A caption under the drawing'},
                                                onSave: () => {}}));
    await page.waitForSelector('.latex-modal .lx-stage img', {timeout: 30000});
    await page.setViewportSize({width: 390, height: 844});
    await page.waitForFunction(() => { const i = document.querySelector('.lx-stage img'); return i && i.complete && i.naturalWidth > 0; });
    await page.waitForTimeout(150);
    const phoneImage = await page.evaluate(() => {
      const img = document.querySelector('.lx-stage img'), stage = document.querySelector('.lx-stage');
      const cs = getComputedStyle(stage);
      return {width: img.getBoundingClientRect().width, w: +img.style.getPropertyValue('--lx-w'),
              inner: stage.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight)};
    });
    assert(phoneImage.width >= 0.7 * phoneImage.inner && phoneImage.width <= phoneImage.w * 12 + 1,
           `phone: the small drawing fills the preview too (${Math.round(phoneImage.width)} of ${Math.round(phoneImage.inner)} px)`);
    const phone = await page.evaluate(() => {
      const bounds = selector => {
        const el = document.querySelector(selector), r = el && el.getBoundingClientRect();
        return r && {left: r.left, top: r.top, right: r.right, bottom: r.bottom, width: r.width, height: r.height};
      };
      return {editor: bounds('.lx-editor-pane'), preview: bounds('.lx-preview-pane'), footer: bounds('.latex-modal-actions'),
              modal: bounds('.latex-modal'), height: innerHeight, over: document.documentElement.scrollWidth - innerWidth,
              editorSpill: ['.lx-editor-pane', '.lx-preview-pane'].map(s => {
                const pane = document.querySelector(s);
                return pane.scrollHeight - pane.clientHeight;
              })};
    });
    assert(phone.editor.top < phone.preview.top && Math.abs(phone.editor.left - phone.preview.left) <= 1,
           `phone: source stacks above its preview (${JSON.stringify(phone.editor)} / ${JSON.stringify(phone.preview)})`);
    assert(phone.editor.bottom <= phone.preview.top + 1 && phone.editorSpill.every(n => n <= 1),
           `phone: the two panes do not overlap: each holds all its own content (${JSON.stringify(phone.editorSpill)})`);
    assert(phone.footer.top >= 0 && phone.footer.bottom <= phone.height + 1 && phone.over <= 1,
           `phone: actions stay visible and the page does not scroll sideways (${JSON.stringify(phone)})`);
    if (shots) await page.screenshot({path: `${shots}/latex-sheet-${mode}-phone.png`});
    assert(errors.length === 0, 'the drawing sheet caused no browser error: ' + errors.join(' | '));
    await context.close();
  } finally {
    await browser.close();
    proc.kill('SIGTERM');
    await proc.status.catch(() => {});
    if (log.length) console.log(log.join(''));
  }
}

// THE THEMES' MISSING PACKAGES (TO-DO §8.39's L14).  The harness's --latex-missing says every TeX
// file is absent (as Settings' own browser pass does), which changes what the computer REPORTS and
// nothing it compiles with: the sheet marks the themes, and a drawing that really asks for a file that
// is not there (real XeLaTeX: \input{zzmissingpackage}) is answered with an Install link when this
// Parseh has a Settings page to install it from.
async function missingSuite(mode) {
  console.log(`\n== ${mode}: packages missing ==`);
  const {proc, info, log} = await startHarness(mode, ['--latex-missing', '--latex-own-missing']);
  const origin = `http://127.0.0.1:${info.port}`, base = info.studio;
  const browser = await chromium.launch({executablePath: Deno.env.get('CHROME_BIN'), headless: true});
  try {
    const context = await browser.newContext({viewport: {width: 1280, height: 900}});
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(origin + base + `/doc/${info.rich_doc_id}/edit`);
    await page.waitForSelector('#btn-latex-editor');
    await page.click('#btn-latex-editor');
    await page.waitForSelector('.latex-modal .lx-theme option[value="drawing"]', {state: 'attached'});
    const said = await page.evaluate(() => fetch(LATEX_BASE + '/api/latex/themes').then(r => r.json()));
    eq(Object.keys(said.missing).join(','), 'default,chemistry,drawing', 'the server says which themes lack files');
    assert(said.missing.chemistry.some(m => m.id === 'mhchem' && m.install === 'mhchem,chemgreek'),
           'a theme names what it lacks and the TeX Live package that brings it: ' + JSON.stringify(said.missing.chemistry.slice(-2)));
    if (mode === 'parseh') eq(said.settings, '/settings/latex/', 'and, where Parseh has one, its Settings page');
    else eq(said.settings, null, 'and none where the studio stands alone');
    const options = await page.$$eval('.lx-theme option', all => all.map(o => o.textContent));
    eq(options.length, 4, 'the default and the three themes');
    assert(options.every(t => / — needs .+, not installed$/.test(t)), 'every one is marked in its own words: ' + JSON.stringify(options));
    assert(/^chemistry — needs standalone, .*and \d+ more, not installed$/.test(options[2]),
           'a long lack is three names and a count, not a paragraph in a list: ' + options[2]);
    await page.selectOption('.latex-modal .lx-theme', 'drawing');
    await page.fill('.latex-modal .lx-src', '\\input{zzmissingpackage}');
    await page.waitForFunction(() => /is not installed on this computer/.test(document.querySelector('.lx-status').textContent),
                               null, {timeout: 60000});
    const status = await page.evaluate(() => {
      const a = document.querySelector('.lx-status a');
      return {text: document.querySelector('.lx-status').textContent, href: a && a.getAttribute('href'),
              target: a && a.target, rel: a && a.rel, label: a && a.textContent};
    });
    if (mode === 'parseh') {
      eq(status.href, '/settings/latex/?install=zzmissingpackage', 'the sheet offers to install it, at Settings');
      eq(status.label, 'Get zzmissingpackage…', 'in words');
      assert(status.target === '_blank' && /noopener/.test(status.rel), 'in a new tab, so the drawing being written is not left behind');
    } else {
      assert(status.href === null, 'the studio alone has no Settings: it says what is missing and links nowhere');
    }
    for (const size of [[1280, 900], [390, 844]]) {
      await page.setViewportSize({width: size[0], height: size[1]});
      await page.waitForTimeout(200);
      const fit = await page.evaluate(() => ({over: document.documentElement.scrollWidth - innerWidth,
        select: document.querySelector('.lx-theme').getBoundingClientRect().right - document.querySelector('.lx-editor-pane').getBoundingClientRect().right}));
      assert(fit.over <= 1 && fit.select <= 1, `${size[0]} px: a long marked option does not push the sheet wider (${JSON.stringify(fit)})`);
      if (shots) await page.screenshot({path: `${shots}/latex-sheet-${mode}-missing-${size[0]}.png`});
    }
    assert(errors.length === 0, 'no browser error: ' + errors.join(' | '));
    await context.close();
  } finally {
    await browser.close();
    proc.kill('SIGTERM');
    await proc.status.catch(() => {});
    if (log.length) console.log(log.join(''));
  }
}

for (const mode of modes) { await suite(mode); await missingSuite(mode); }
console.log(`LaTeX drawing sheet passed (${modes.join(' + ')}: ${passed} checks)`);

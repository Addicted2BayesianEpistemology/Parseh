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

async function startHarness(mode) {
  const proc = new Deno.Command(python, {args: [root + '/tests/studio_harness.py', mode], cwd: root,
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
        fit: [document.querySelector('.lx-stage').dataset.lxPreviewMode,
              document.querySelector('[data-lx-preview="fit"]').getAttribute('aria-pressed'),
              document.querySelector('[data-lx-preview="actual"]').getAttribute('aria-pressed')],
      };
    });
    assert(desktop.preview.right <= desktop.editor.left + 1 && desktop.preview.top < desktop.editor.bottom,
           `desktop: preview is the left column (${JSON.stringify(desktop.preview)} / ${JSON.stringify(desktop.editor)})`);
    assert(desktop.stage.width >= desktop.preview.width - 50 && desktop.stage.height >= 250,
           `desktop: preview has usable room (${Math.round(desktop.stage.width)} × ${Math.round(desktop.stage.height)})`);
    assert(!desktop.layoutOpen && desktop.natural, 'a new drawing leaves Size and position folded at its natural size');
    eq(desktop.fit.join(','), 'fit,true,false', 'Fit is the first preview size');
    assert(desktop.footer.top >= desktop.body.bottom - 2 && desktop.footer.bottom <= desktop.modal.bottom + 1,
           'the Cancel and Insert footer is outside the scrolling body and stays in the dialog');
    if (shots) await page.screenshot({path: `${shots}/latex-sheet-${mode}-desktop.png`});

    await page.click('.latex-modal [data-lx-preview="actual"]');
    eq(await page.evaluate(() => [document.querySelector('.lx-stage').dataset.lxPreviewMode,
                                  document.querySelector('[data-lx-preview="fit"]').getAttribute('aria-pressed'),
                                  document.querySelector('[data-lx-preview="actual"]').getAttribute('aria-pressed')].join(',')),
       'actual,false,true', 'Actual size is a real, announced preview mode');
    await page.click('.latex-modal [data-lx-preview="fit"]');

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

    // A phone has one readable column: author first, preview next, its action
    // footer still wholly on-screen and no horizontal page scroll.
    await page.setViewportSize({width: 390, height: 844});
    await page.waitForTimeout(150);
    const phone = await page.evaluate(() => {
      const bounds = selector => {
        const el = document.querySelector(selector), r = el && el.getBoundingClientRect();
        return r && {left: r.left, top: r.top, right: r.right, bottom: r.bottom, width: r.width, height: r.height};
      };
      return {editor: bounds('.lx-editor-pane'), preview: bounds('.lx-preview-pane'), footer: bounds('.latex-modal-actions'),
              modal: bounds('.latex-modal'), height: innerHeight, over: document.documentElement.scrollWidth - innerWidth};
    });
    assert(phone.editor.top < phone.preview.top && Math.abs(phone.editor.left - phone.preview.left) <= 1,
           `phone: source stacks above its preview (${JSON.stringify(phone.editor)} / ${JSON.stringify(phone.preview)})`);
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

for (const mode of modes) await suite(mode);
console.log(`LaTeX drawing sheet passed (${modes.join(' + ')}: ${passed} checks)`);

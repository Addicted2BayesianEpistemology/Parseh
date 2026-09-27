// SPDX-License-Identifier: GPL-3.0-or-later
// Browser test of the LaTeX drawings (TO-DO §8.39, a0.4.0), against the REAL
// routes on a temporary library, with the TeX this computer has:
//   a) the editor's preview draws a document's latex blocks, and a block that
//      cannot be drawn is a frame saying why, in words
//   b) the LaTeX drawing sheet: a theme chosen, the drawing made as it is
//      typed, a mistake said in words beside it, Insert putting the block in
//   c) THE PENCIL: hovering a drawing in the preview offers ✎ on the drawing,
//      it goes away again when the pointer leaves, and pressing it reopens
//      the block, whose edit goes back over the very lines it came from.
//      (It never appeared for a whole week of a0.4.0's work -- it reused the
//      RTL pencil's class, which is `display: none`, and only set `hidden` --
//      because no test had ever opened the sheet: found by driving, 2026-09-25.)
//   d) (parseh) Settings -> LaTeX drawings: its themes, the bar of its doors,
//      and a page that never scrolls sideways on a phone
// Two modes, each a tests/studio_harness.py:
//   studio  the studio's own server (studio at /)
//   parseh  Parseh's handler (studio at /studio, Settings at /settings/)
//   CHROME_BIN=... PARSEH_PYTHON=python3 deno run --allow-all tests/latex_drawings.mjs
//   LATEX_DRAWINGS_MODES=studio (or parseh) runs one; SHOTS=<dir> saves the
//   screenshots. LATEX_DRAWINGS_SETTINGS_ONLY=1 runs just the Settings checks,
//   without compiling a drawing, on Parseh's handler. A computer with no
//   xelatex otherwise skips it, saying so: the drawings are TeX's, and a
//   fresh clone must stay green.
import {chromium} from 'npm:playwright-core@1.52.0';

const root = await Deno.realPath(new URL('..', import.meta.url));
const python = Deno.env.get('PARSEH_PYTHON') || 'python3';
const settingsOnly = Deno.env.get('LATEX_DRAWINGS_SETTINGS_ONLY') === '1';
const modes = settingsOnly ? ['parseh']
  : (Deno.env.get('LATEX_DRAWINGS_MODES') || 'studio,parseh').split(',');
const SHOTS = Deno.env.get('SHOTS') || '';
let passed = 0;
const assert = (v, m) => { if (!v) throw Error('FAIL: ' + m); passed++; console.log('  ok', m); };
const eq = (a, b, m) => assert(a === b, `${m} (got ${JSON.stringify(a)}, want ${JSON.stringify(b)})`);
const sleep = ms => new Promise(r => setTimeout(r, ms));
async function until(fn, what, ms = 20000) {
  const end = Date.now() + ms;
  for (;;) {
    let v;
    try { v = await fn(); } catch (_) { v = false; }
    if (v) return v;
    if (Date.now() > end) throw Error('FAIL: timed out: ' + what);
    await sleep(80);
  }
}

// no TeX, no drawings: a named skip
if (!settingsOnly) {
  const hasTeX = await new Deno.Command('xelatex', {args: ['--version'], stdout: 'null', stderr: 'null'}).output()
    .then(r => r.success, () => false);
  if (!hasTeX) {
    console.log('SKIP: no xelatex on this computer -- the drawings are made by TeX (tests/latex_drawings.mjs)');
    Deno.exit(0);
  }
}

const DOC = `---
target: it
---
# Disegni

Una formula ordinaria: [E = mc^2]{math}.

::::latex chemistry {width=45 align=center}
\\ce{2H2 + O2 -> 2H2O}
::::

Un blocco rotto:

::::latex
\\undefinedcommandxyz
::::

Un blocco con un tema che non esiste:

::::latex nosuchtheme
x
::::
`;

async function startHarness(mode) {
  const args = [root + '/tests/studio_harness.py', mode];
  if (mode === 'parseh') args.push('--latex-missing');
  if (settingsOnly && mode === 'parseh') args.push('--latex-compiler-states');
  const proc = new Deno.Command(python, {args, cwd: root,
                                         stdout: 'piped', stderr: 'piped'}).spawn();
  const log = [];
  (async () => {
    const r = proc.stderr.pipeThrough(new TextDecoderStream()).getReader();
    for (;;) { const {value, done} = await r.read(); if (done) break; log.push(value); }
  })();
  const reader = proc.stdout.pipeThrough(new TextDecoderStream()).getReader();
  let buf = '', info = null;
  while (!info) {
    const {value, done} = await reader.read();
    if (done) throw Error(`harness (${mode}) exited before READY:\n` + buf + log.join(''));
    buf += value;
    const m = buf.match(/READY (\{.*\})\n/);
    if (m) info = JSON.parse(m[1]);
  }
  (async () => { for (;;) { const r = await reader.read(); if (r.done) break; } })();
  return {proc, info, log};
}

async function suite(mode) {
  console.log(`\n== ${mode} ==`);
  const {proc, info, log} = await startHarness(mode);
  const origin = `http://127.0.0.1:${info.port}`, base = info.studio;
  const url = p => origin + base + p;
  const api = async (method, path, body) => {
    const r = await fetch(url(path), {method, headers: body ? {'Content-Type': 'application/json'} : {},
                                      body: body ? JSON.stringify(body) : undefined});
    const data = await r.json();
    if (!r.ok) throw Error(`${method} ${path}: ${r.status} ${JSON.stringify(data)}`);
    return data;
  };
  const browser = await chromium.launch({executablePath: Deno.env.get('CHROME_BIN'), headless: true});
  try {
    const context = await browser.newContext({viewport: {width: 1280, height: 900}});
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    const shot = async name => { if (SHOTS) await page.screenshot({path: `${SHOTS}/latex-${mode}-${name}.png`}); };
    if (!settingsOnly) {
      const source = () => page.locator('#src').inputValue();
      const made = await api('POST', '/api/docs', {markdown: DOC});
      const id = made.meta.id;

    /* ---------------- a) the preview ---------------- */
    console.log('a) the preview');
    await page.goto(url(`/doc/${id}/edit`));
    await page.waitForSelector('#btn-latex-editor');
    await page.waitForSelector('#sheet figure.latex', {timeout: 30000});
    eq(await page.locator('#sheet figure.latex').count(), 1, 'the block that can be drawn is a drawing');
    const drawn = await page.evaluate(() => {
      const i = document.querySelector('#sheet figure.latex img');
      return i.complete && i.naturalWidth > 20 && /svg/.test(i.currentSrc);
    });
    assert(drawn, 'and its picture (an SVG) really loaded');
    const said = await page.locator('#sheet .latex-fail .latex-said').allTextContents();
    eq(said.length, 2, 'the two blocks that cannot be drawn are frames');
    assert(/undefinedcommandxyz is not a command LaTeX knows here on line 1 of the block/.test(said[0]),
           'one says which command and on which line: ' + said[0].slice(0, 90));
    assert(/asks for the theme .nosuchtheme., which this Parseh does not have/.test(said[1]),
           'the other says the theme is missing: ' + said[1].slice(0, 90));
    await shot('preview');

    /* ---------------- b) the sheet ---------------- */
    console.log('b) the LaTeX drawing sheet');
    // where the block goes is where the caret is, as for every button of the editor: at the end
    await page.locator('#src').click();
    await page.keyboard.press('Control+End');
    await page.click('#btn-latex-editor');
    await page.waitForSelector('.latex-overlay .lx-theme option[value="chemistry"]', {state: 'attached'});
    await page.selectOption('.latex-overlay .lx-theme', 'chemistry');
    await page.fill('.latex-overlay .lx-src', '\\ce{CH4 + 2O2 -> CO2 + 2H2O}');
    await page.waitForSelector('.latex-overlay .lx-stage img', {timeout: 30000});
    assert(await page.evaluate(() => {
      const i = document.querySelector('.latex-overlay .lx-stage img');
      return i.complete && i.naturalWidth > 20;
    }), 'the sheet draws the reaction as it is typed');
    await shot('sheet');
    await page.fill('.latex-overlay .lx-src', '\\undefinedcommandxyz');
    await until(async () => /not a command LaTeX knows/.test(await page.locator('.latex-overlay .lx-status').textContent()),
                'a mistake said in words');
    assert(true, 'a mistake in the sheet is said in words beside the drawing');
    await page.fill('.latex-overlay .lx-src', '\\ce{CH4 + 2O2 -> CO2 + 2H2O}');
    await page.waitForSelector('.latex-overlay .lx-stage img', {timeout: 30000});
    await page.click('.latex-overlay [data-x="ok"]');
    await page.waitForSelector('.latex-overlay', {state: 'detached'});
    assert(/::::latex chemistry[^\n]*\n\\ce\{CH4 \+ 2O2 -> CO2 \+ 2H2O\}\n::::/.test(await source()),
           'Insert puts a ::::latex chemistry block into the text');
    await until(async () => (await page.locator('#sheet figure.latex').count()) === 2, 'the preview draws one more');
    assert(true, 'and the preview draws one more');

    /* ---------------- c) the pencil ---------------- */
    console.log('c) the pencil on a drawing');
    const fig = page.locator('#sheet figure.latex[data-latex-src]').first();
    await fig.scrollIntoViewIfNeeded();
    const pencil = page.locator('button.rtl-edit-btn').filter({hasText: '✎'});
    assert(!(await pencil.count()) || !(await pencil.first().isVisible()), 'no pencil while the pointer is elsewhere');
    await fig.hover();
    await until(async () => (await pencil.count()) && await pencil.first().isVisible(), 'the pencil appears');
    assert(true, 'hovering a drawing offers ✎');
    const boxes = await page.evaluate(() => {
      const f = document.querySelector('#sheet figure.latex[data-latex-src]').getBoundingClientRect();
      const b = [...document.querySelectorAll('button.rtl-edit-btn')].find(x => x.textContent.trim() === '✎').getBoundingClientRect();
      return {f: [f.left, f.top, f.right, f.bottom], b: [b.left, b.top, b.right, b.bottom]};
    });
    // at the drawing's top corner: a short drawing (one line of a reaction is 21 px tall) is
    // shorter than the button, which then hangs below it -- so the corner, not the whole box
    assert(boxes.b[2] - boxes.b[0] > 5 && boxes.b[3] - boxes.b[1] > 5
           && boxes.b[2] <= boxes.f[2] + 2 && boxes.b[2] >= boxes.f[2] - 14
           && Math.abs(boxes.b[1] - boxes.f[1]) <= 8 && boxes.b[0] >= boxes.f[0] - 2,
           `and sits at the drawing's top corner (${boxes.b.map(Math.round)} against ${boxes.f.map(Math.round)})`);
    await page.mouse.move(5, 5);
    await until(async () => !(await pencil.first().isVisible()), 'the pencil goes away', 3000);
    assert(true, 'it goes away again when the pointer leaves');
    await fig.hover();
    await until(async () => await pencil.first().isVisible(), 'the pencil is back');
    await pencil.first().click();
    await page.waitForSelector('.latex-overlay .lx-src');
    eq(await page.inputValue('.latex-overlay .lx-src'), '\\ce{2H2 + O2 -> 2H2O}', 'the pencil reopens the block that was drawn');
    eq(await page.inputValue('.latex-overlay .lx-theme'), 'chemistry', 'with its theme');
    eq(await page.inputValue('.latex-overlay .lx-width'), '45', 'and its width');
    await page.fill('.latex-overlay .lx-src', '\\ce{2H2 + O2 -> 2H2O}\n% edited');
    await page.click('.latex-overlay [data-x="ok"]');
    await page.waitForSelector('.latex-overlay', {state: 'detached'});
    const text = await source();
    assert(/::::latex chemistry \{width=45( align=center)?\}\n\\ce\{2H2 \+ O2 -> 2H2O\}\n% edited\n::::\n/.test(text),  // centred is the default, so the sheet may leave it unsaid
           'saving puts the edit back over the block it came from, its fence and layout kept');
      eq((text.match(/::::latex/g) || []).length, 4, 'and no block was lost or doubled');
    }

    /* ---------------- d) Settings ---------------- */
    if (mode === 'parseh') {
      console.log('d) Settings -> LaTeX drawings');
      await page.goto(origin + '/settings/latex/');
      await page.waitForSelector('.lx .theme');
      const names = (await page.locator('.lx .theme h3').allTextContents()).map(s => s.split('(')[0].trim());
      eq(names.join(','), 'default,chemistry,drawing', 'a fresh Parseh has three themes');
      const themeActions = await page.locator('.lx [data-edit], .lx [data-rename], .lx [data-default], .lx [data-delete]')
        .evaluateAll(buttons => buttons.map(button => ({text: button.textContent.trim(), label: button.getAttribute('aria-label')})));
      assert(themeActions.length > 6 && themeActions.every(action => action.label
             && action.label.toLowerCase().includes('theme')),
             'repeated theme-card actions say which theme they affect: ' + JSON.stringify(themeActions));
      const compilerList = page.locator('.lx dl.tex-status');
      const compilerFacts = await compilerList.evaluate(list => ({
        rows: [...list.children].map(row => ({
          compiler: row.getAttribute('data-compiler'),
          term: row.querySelector('dt')?.textContent.trim(),
          state: row.querySelector('.st')?.textContent.trim(),
          version: row.querySelector('.compiler-version')?.textContent.trim() || '',
        })),
        table: !!list.querySelector('table'),
      }));
      assert(compilerFacts.rows.length === 3 && !compilerFacts.table
             && compilerFacts.rows.every(row => row.term === row.compiler && row.state),
             'compiler facts are a semantic status list, not a headerless table: ' + JSON.stringify(compilerFacts));
      const xetex = compilerFacts.rows.find(row => row.compiler === 'xelatex');
      const pdftex = compilerFacts.rows.find(row => row.compiler === 'pdflatex');
      const luatex = compilerFacts.rows.find(row => row.compiler === 'lualatex');
      assert(xetex?.state === '✓ Available' && xetex.version === 'XeTeX test 2026'
             && pdftex?.state === '— Not on this computer' && !pdftex.version
             && luatex?.state === '✓ Available' && /LuaHBTeX/.test(luatex.version),
             'available and unavailable compilers say their status in words, with a version when available');
      const desktopCompilerLayout = await compilerList.evaluate(list => [...list.children].map(row => {
        const term = row.querySelector('dt').getBoundingClientRect();
        const description = row.querySelector('dd').getBoundingClientRect();
        return {termLeft: term.left, descriptionLeft: description.left};
      }));
      assert(desktopCompilerLayout.every(row => row.descriptionLeft > row.termLeft),
             'at desktop width, compiler names and their facts form compact status rows');
      const planReply = (names, licence = 'lppl1.3c') => ({
        ok: true, can: true, tex: 'TeX Live test', why: '',
        packages: names.map((name, at) => ({name, size: 185000 + at * 1000,
          licence, here: 'missing', repository: 'available', can_get: true, why: ''})),
      });
      const planCalls = [];
      let replyToPlan = async (route, packages) => {
        await route.fulfill({json: planReply(packages.length ? packages : ['mhchem'])});
      };
      await page.route('**/settings/api/latex/package-plan', async route => {
        const packages = route.request().postDataJSON().packages;
        planCalls.push(packages);
        await replyToPlan(route, packages);
      });
      const reviewPackages = async viewport => {
        const review = page.locator('.lx [data-install]').first();
        eq((await review.textContent()).trim(), 'Review packages…',
           'the missing-package action truthfully says it reviews packages first');
        assert(/^Review packages needed by /.test(await review.getAttribute('aria-label')),
               'each repeated Review packages action says which theme it belongs to');
        const expected = (await review.getAttribute('data-install')).split(' ').filter(
          (name, at, all) => name && all.indexOf(name) === at);
        const panel = page.locator('.lx [data-package-panel]');
        assert(await panel.locator('[data-package-row]').count() >= expected.length,
               'missing theme packages are persistent rows, before anyone reviews a cost');
        await page.evaluate(() => window.scrollTo(0, 0));
        await review.focus();
        await page.keyboard.press('Enter');
        const get = panel.locator('[data-package-get]').first();
        await get.waitFor();
        assert(/Nothing has been downloaded/.test(await panel.locator('[data-pkg-said]').textContent()),
               'the package rows say clearly that reviewing changed nothing yet');
        assert(await get.evaluate(button => button.classList.contains('go')),
               'Get it is the magenta action that starts an acquisition');
        const getName = await get.getAttribute('data-package-get');
        assert(expected.includes(getName) && (await get.getAttribute('aria-label')).startsWith(`Get ${getName}, `),
           'Get it says its package and quoted cost to a screen reader');
        eq(JSON.stringify(planCalls[planCalls.length - 1]), JSON.stringify(expected),
           'the review sends the selected theme\'s missing packages to the planner');
        const getNames = await panel.locator('[data-package-get]').evaluateAll(buttons =>
          buttons.map(button => button.getAttribute('data-package-get')));
        assert(expected.every(name => getNames.includes(name)),
           'each quoted package has its own Get it action in the packages table: ' + JSON.stringify(getNames));
        assert(await panel.locator('[data-package-get-all]').count() === 1,
               'Get all is available beside the individual package actions');
        const rowFacts = await panel.locator('[data-package-row]').evaluateAll(rows => rows.map(row => ({
          name: row.getAttribute('data-package-row'), scope: row.querySelector('th')?.getAttribute('scope'),
          state: row.querySelector('.pkg-state')?.textContent.trim(), action: row.querySelector('.pkg-action')?.textContent.trim(),
        })));
        assert(expected.every(name => rowFacts.some(row => row.name === name && row.scope === 'row'
               && /To get/.test(row.state) && /Get it/.test(row.action))),
               'each planned package has semantic table facts, state, and its local action: ' + JSON.stringify(rowFacts));
        await until(() => get.evaluate(button => document.activeElement === button),
                    `the first Get it receives keyboard focus after the ${viewport} review`);
        await until(() => panel.evaluate(el => {
          const r = el.getBoundingClientRect();
          return r.top <= innerHeight / 2 && r.bottom >= innerHeight / 2;
        }), `the ${viewport} package rows are centred in view`);
        for (const theme of ['light', 'sepia', 'dark']) {
          await page.evaluate(theme => { document.documentElement.dataset.theme = theme; }, theme);
          const color = await get.evaluate(button => {
            const swatch = document.createElement('i');
            swatch.style.color = 'var(--accent)';
            document.body.appendChild(swatch);
            const answer = {accent: getComputedStyle(swatch).color,
                            background: getComputedStyle(button).backgroundColor};
            swatch.remove();
            return answer;
          });
          eq(color.background, color.accent, `Get it uses the ${theme} magenta`);
          await shot(`package-review-${viewport}-${theme}`);
        }
        await page.evaluate(() => document.documentElement.removeAttribute('data-theme'));
      };
      await reviewPackages('desktop');
      let staleCalls = 0, releaseOlder, olderDone = false;
      const older = new Promise(resolve => { releaseOlder = resolve; });
      replyToPlan = async (route, packages) => {
        staleCalls++;
        if (staleCalls === 1) {
          await older;
          await route.fulfill({json: planReply(packages, 'older-licence')});
          olderDone = true;
        } else await route.fulfill({json: planReply(packages, 'newer-licence')});
      };
      const packageName = page.locator('.lx [data-pkgname]');
      await packageName.fill('older-quote');
      await page.locator('.lx [data-package-plan]').click();
      await until(() => staleCalls === 1, 'the first of two package reviews reaches the planner');
      await packageName.fill('newer-quote');
      await page.locator('.lx [data-package-plan]').click();
      await until(async () => /newer-licence/.test(await page.locator('.lx [data-package-panel]').textContent()),
                  'the later package review reaches the page');
      releaseOlder();
      await until(() => olderDone, 'the delayed first package review completes');
      await sleep(80);
      assert(/newer-licence/.test(await page.locator('.lx [data-package-panel]').textContent())
             && !/older-licence/.test(await page.locator('.lx [data-package-panel]').textContent()),
             'a late quote never replaces the newer review');
      replyToPlan = async route => { await route.abort('failed'); };
      await packageName.fill('failed-quote');
      await page.locator('.lx [data-package-plan]').click();
      const failedPlan = page.locator('.lx [data-pkg-said]');
      await until(async () => /Could not ask what the packages cost/.test(await failedPlan.textContent()),
                  'a network failure is said beside the package rows');
      assert(await failedPlan.evaluate(out => document.activeElement === out),
               'a failed quote leaves keyboard focus on its explanation');
      replyToPlan = async (route, packages) => {
        await route.fulfill({json: planReply(packages.length ? packages : ['mhchem'])});
      };
      await page.locator('.lx [data-edit="default"]').click();
      eq(await page.locator('.lx .grp h4').first().textContent(), 'Base packages',
         'the public package group does not name Formulae');
      assert(/The basics every drawing uses/.test(await page.locator('.lx .grp-why').first().textContent()),
             'Base packages says plainly what it is for');
      assert(await page.locator('.lx [data-save]').evaluate(button => button.classList.contains('go')),
             'Save the theme is its form\'s magenta commit');
      assert(await page.locator('.lx [data-draw-sample]').evaluate(button => button.classList.contains('plain'))
             && await page.locator('.lx [data-cancel]').evaluate(button => button.classList.contains('plain')),
             'drawing a sample and cancelling stay quiet reversible actions');
      const actions = await page.locator('.lx button').evaluateAll(buttons => buttons.map(button => ({
        text: button.textContent.trim(), className: button.className,
      })));
      assert(actions.length > 8 && actions.every(button => /\b(go|plain|parseh-btn)\b/.test(button.className)),
             'every LaTeX action has the shared affirmative, quiet, or existing link-style control: '
             + JSON.stringify(actions));
      const exportButton = page.locator('.lx .theme a.parseh-btn').first();
      await page.locator('.lx [data-rename="default"]').focus();
      await page.keyboard.press('Tab');
      assert(await exportButton.evaluate(link => document.activeElement === link
             && link.matches(':focus-visible') && getComputedStyle(link).outlineWidth === '2px'),
             'Export keeps its established quiet control and has the shared visible keyboard focus');
      const importButton = page.locator('.lx [data-import-open]');
      eq(await importButton.evaluate(button => button.tagName), 'BUTTON',
         'Import a theme is a keyboard-focusable button, not a file-input label');
      await importButton.focus();
      assert(await page.evaluate(() => document.activeElement.matches('.lx [data-import-open]')),
             'Import a theme receives keyboard focus');
      for (const theme of ['light', 'sepia', 'dark']) {
        const colors = await page.evaluate(theme => {
          document.documentElement.dataset.theme = theme;
          const swatch = document.createElement('i');
          swatch.style.color = 'var(--accent)';
          document.body.appendChild(swatch);
          const want = getComputedStyle(swatch).color;
          const got = [...document.querySelectorAll('.lx [data-pkg], .lx input[name="lx-comp"]')]
            .map(input => getComputedStyle(input).accentColor);
          const save = getComputedStyle(document.querySelector('.lx [data-save]')).backgroundColor;
          swatch.remove();
          return {want, got, save};
        }, theme);
        assert(colors.got.length > 1 && colors.got.every(color => color === colors.want),
               `package checks and compiler choices use the ${theme} accent (${JSON.stringify(colors)})`);
        eq(colors.save, colors.want, `Save the theme uses the ${theme} magenta`);
        await shot(`settings-${theme}`);
        await page.locator('.lx [data-save]').scrollIntoViewIfNeeded();
        await shot(`editor-actions-${theme}`);
      }
      await page.evaluate(() => document.documentElement.removeAttribute('data-theme'));
      await page.locator('.lx [data-cancel]').click();
      assert(await page.locator('.lx [data-save-limit]').evaluate(button => button.classList.contains('go')),
             'Save is the magenta commit for the time-limit form');
      for (const theme of ['light', 'sepia', 'dark']) {
        await page.evaluate(theme => { document.documentElement.dataset.theme = theme; }, theme);
        await compilerList.scrollIntoViewIfNeeded();
        await shot(`compiler-status-desktop-${theme}`);
      }
      await page.evaluate(() => document.documentElement.removeAttribute('data-theme'));
      assert(await page.locator('.parseh-doors a, nav a, .doors a').filter({hasText: 'LaTeX drawings'}).count() > 0
             || (await page.content()).includes('LaTeX drawings'), 'the bar of the doors names this page');
      await shot('settings');
      await page.setViewportSize({width: 390, height: 844});
      await sleep(300);
      await reviewPackages('phone');
      const phonePackageLayout = await page.locator('.lx [data-package-row]').first().evaluate(row => {
        const cells = [...row.querySelectorAll('th,td')].map(cell => getComputedStyle(cell).display);
        const action = row.querySelector('button')?.getBoundingClientRect();
        return {display: getComputedStyle(row).display, cells, actionHeight: action ? Math.round(action.height) : 0};
      });
      assert(phonePackageLayout.display === 'block' && phonePackageLayout.cells.slice(0, 5).every(display => display === 'grid')
             && phonePackageLayout.cells[5] === 'block'
             && phonePackageLayout.actionHeight >= 44,
             'at phone width, each package table row becomes a labelled action card: ' + JSON.stringify(phonePackageLayout));
      for (const theme of ['light', 'sepia', 'dark']) {
        const layout = await page.evaluate(theme => {
          document.documentElement.dataset.theme = theme;
          return {
            over: document.documentElement.scrollWidth - window.innerWidth,
            compilers: (() => {
              const list = document.querySelector('.lx .tex-status');
              return {over: list ? list.scrollWidth - list.clientWidth : Infinity,
                      rows: list ? [...list.children].map(row => {
                        const term = row.querySelector('dt').getBoundingClientRect();
                        const description = row.querySelector('dd').getBoundingClientRect();
                        return {width: row.getBoundingClientRect().width, stacked: description.top > term.bottom};
                      }) : []};
            })(),
            touch: [...document.querySelectorAll('.lx button.go, .lx button.plain, .lx .parseh-btn')]
              .filter(control => !!(control.offsetWidth || control.offsetHeight))
              .map(control => ({text: control.textContent.trim(), height: Math.round(control.getBoundingClientRect().height)})),
          };
        }, theme);
        assert(layout.over <= 1, `at 390 px in ${theme}, the page never scrolls sideways (${layout.over} px over)`);
        assert(layout.touch.length > 0 && layout.touch.every(control => control.height >= 44),
               `at 390 px in ${theme}, each visible action has a 44 px touch target (${JSON.stringify(layout.touch)})`);
        assert(layout.compilers.over <= 1 && layout.compilers.rows.length === 3
               && layout.compilers.rows.every(row => row.stacked),
               `at 390 px in ${theme}, each compiler fact fits its status list (${JSON.stringify(layout.compilers)})`);
        await page.locator('.lx .tex-status').scrollIntoViewIfNeeded();
        await shot(`compiler-status-phone-${theme}`);
        await shot(`settings-phone-${theme}`);
      }
      await page.evaluate(() => document.documentElement.removeAttribute('data-theme'));
      await shot('settings-phone');
    }
    eq(errors.join(' | '), '', 'no script error on any page');
  } finally {
    await browser.close();
    proc.kill('SIGTERM');
    await proc.status.catch(() => {});
  }
  return passed;
}

let total = 0;
for (const mode of modes) total += await suite(mode);
console.log(`LaTeX drawings passed (${modes.join(' + ')}: ${passed} checks)`);

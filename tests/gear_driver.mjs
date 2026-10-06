// SPDX-License-Identifier: GPL-3.0-or-later
/* What the browser suites that touch a book's reader share about its gear (lib/gear-reader.js, a0.5.0): open
   the ⚙, find a row, flip a switch, choose from a menu, shut it again -- the way a person does, by a tap on a
   phone (a suite marks its touch pages with `page.touch`, as tests/mobile_pages.mjs does) and by a click with a
   mouse.  The reader's own controls are still on the page and a few of them still drawn; what the gear took
   off the page -- the passes' numbers, ⋯, hover ⏸, stop at a change, the definitions -- is reached only here. */
const press = async (page, l) => { if (page.touch) await l.tap(); else await l.click(); };
const sleep = ms => new Promise(r => setTimeout(r, ms));

export const GEAR = '[data-parseh-gear]';
export const gearUp = page => page.evaluate(() => {
  const p = document.querySelector('.pg-panel');
  return !!p && !p.hidden;
});
// the gear open (its button pressed unless it already is), and, where a group is named, scrolled to it
export async function gearOpen(page, group) {
  if (!(await gearUp(page))) {
    await page.waitForSelector(GEAR, {state: 'visible', timeout: 15000});
    await press(page, page.locator(GEAR).first());
    await page.waitForFunction(() => { const p = document.querySelector('.pg-panel'); return !!p && !p.hidden; });
    await sleep(120);
  }
  if (group) await page.evaluate(g => {
    const b = document.querySelector('.pg-panel .pg-body'), e = document.querySelector('.pg-panel [data-pg-group="' + g + '"]');
    if (b && e && !e.hidden) b.scrollTop = Math.max(0, e.offsetTop - 8);
  }, group);
}
export async function gearClose(page) {
  if (!(await gearUp(page))) return;
  await press(page, page.locator('.pg-panel .pg-x'));
  await page.waitForFunction(() => document.querySelector('.pg-panel').hidden);
  await sleep(80);
}
export const gearRow = (page, id) => page.locator(`.pg-panel [data-pg-row="${id}"]`);
// whether a row is drawn right now (the gear is open): its row is not hidden and has a box
export const rowDrawn = (page, id) => page.evaluate(id => {
  const r = document.querySelector(`.pg-panel [data-pg-row="${id}"]`);
  return !!r && !r.hidden && r.getClientRects().length > 0;
}, id);
// a switch row's state, and the state it is flipped to: opened, flipped if it is not so already, shut
export async function gearSwitch(page, id, want) {
  await gearOpen(page);
  const sw = gearRow(page, id).locator('button.pg-switch');
  await sw.scrollIntoViewIfNeeded();
  const on = (await sw.getAttribute('aria-checked')) === 'true';
  if (on !== !!want) { await press(page, sw); await sleep(150); }
  await gearClose(page);
}
// a menu row ("choice" drawn as a <select>): its value set by name or value, the page's handler run
export async function gearSelect(page, id, value) {
  await gearOpen(page);
  const s = gearRow(page, id).locator('select.pg-select');
  await s.scrollIntoViewIfNeeded();
  await s.selectOption({label: String(value)}).catch(() => s.selectOption(String(value)));
  await sleep(150);
  await gearClose(page);
}

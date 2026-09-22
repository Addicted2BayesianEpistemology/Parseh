// The app's icons, the ones beside this script (docs/mobile.md, "Parseh as
// an app"): پ, white, in the toolbox's own Noto Nastaliq Urdu, on its accent
// #be3455.  Drawn on a canvas in headless Chromium with the letter's INK box
// -- measureText's actual bounds, dots and all -- in the middle, since a
// nastaliq line box is far taller than the letter and would hang it low.
// Not run by anything: the PNGs are kept in the repository, and this is how
// they were made, to make them again.
//   CHROME_BIN=... deno run --allow-all lib/icons/make.mjs
import { chromium } from 'npm:playwright-core@1.52.0';
const OUT = new URL('.', import.meta.url).pathname;
const bytes = await Deno.readFile(new URL('../fonts/NotoNastaliqUrdu.woff2', import.meta.url));
let bin = '';
for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
const FONT = 'data:font/woff2;base64,' + btoa(bin);
// shape: a circle with clear corners (the "any" icons, like the bars' badge),
// or the whole square (maskable: the launcher cuts its own shape out of it,
// keeping at least the middle 80%; Apple rounds its own corners); ink: the
// letter's height, dots and all, as a share of the side
const ICONS = [
  {name: 'parseh-192.png', side: 192, shape: 'circle', ink: .56},
  {name: 'parseh-512.png', side: 512, shape: 'circle', ink: .56},
  {name: 'parseh-maskable-512.png', side: 512, shape: 'square', ink: .44},
  {name: 'apple-touch-icon.png', side: 180, shape: 'square', ink: .52},
];
const browser = await chromium.launch({executablePath: Deno.env.get('CHROME_BIN'), headless: true});
const page = await browser.newPage();
await page.setContent(`<!doctype html><style>@font-face{font-family:N;src:url(${FONT}) format('woff2')}</style>
  <span style="font-family:N" lang="fa">پ</span>`);
await page.evaluate(() => document.fonts.load('100px N', 'پ'));
for (const ic of ICONS) {
  const url = await page.evaluate(ic => {
    const c = document.createElement('canvas');
    c.width = c.height = ic.side;
    const g = c.getContext('2d');
    g.fillStyle = '#be3455';
    if (ic.shape === 'circle') { g.beginPath(); g.arc(ic.side / 2, ic.side / 2, ic.side / 2, 0, 2 * Math.PI); g.fill(); }
    else g.fillRect(0, 0, ic.side, ic.side);
    // the ink's height at 100px, scaled to the share wanted
    g.font = '100px N';
    let m = g.measureText('پ');
    const h100 = m.actualBoundingBoxAscent + m.actualBoundingBoxDescent;
    const fs = 100 * ic.ink * ic.side / h100;
    g.font = fs + 'px N';
    m = g.measureText('پ');
    const w = m.actualBoundingBoxLeft + m.actualBoundingBoxRight;
    const h = m.actualBoundingBoxAscent + m.actualBoundingBoxDescent;
    // the ink box's top-left where the middle wants it, then back to the pen
    const x = (ic.side - w) / 2 + m.actualBoundingBoxLeft;
    const y = (ic.side - h) / 2 + m.actualBoundingBoxAscent;
    g.fillStyle = '#ffffff';
    g.fillText('پ', x, y);
    return c.toDataURL('image/png');
  }, ic);
  await Deno.writeFile(`${OUT}/${ic.name}`, Uint8Array.from(atob(url.split(',')[1]), ch => ch.charCodeAt(0)));
  console.log('wrote', ic.name);
}
await browser.close();

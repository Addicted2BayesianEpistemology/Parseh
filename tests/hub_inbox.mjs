import { chromium } from 'npm:playwright-core@1.52.0';
// Run: CHROME_BIN=/path/to/chrome PARSEH_PYTHON=/path/to/python3 deno run --allow-all tests/hub_inbox.mjs
//
// THE TESTS' HUBS KEEP THE ANKI SYNC INBOX IN THEIR TEMPORARY TREE.  Four
// tests boot the real hub (serve.main) over a temporary toolbox and point
// every store it writes into it: tests/cardkit_harness.py's `serve`, and the
// boot code inside tests/player_cards.mjs, tests/youtube_capture.mjs and
// tests/book_cards.mjs -- read out of those files here, so it is their own
// code that runs.  The Anki store is pointed there by ytpages.ANKI; the sync
// wizard's inbox is ytpages.INBOX, worked out once from the real anki/ when
// ytpages is imported, and has to be pointed there as well.  For each boot,
// an .apkg is dropped on /anki/sync/ the way a person does it (step 1's
// "I have the file →", then the drop zone's file picker), and the file is
// looked for on the disk: in <tmp>/anki/inbox/, and NOT in the repository's
// youtube/anki/inbox/.  Anything the drop put in the repository is taken out
// again, pass or fail.
const root = await Deno.realPath(new URL('..', import.meta.url));
Deno.chdir(root);
const PY = Deno.env.get('PARSEH_PYTHON') || 'python3';
const td = new TextDecoder();
// every boot is checked, whatever the one before it came to
let passed = 0;
const failed = [];
const assert = (v, m) => { if (v) { passed++; console.log('  ok', m); } else { failed.push(m); console.log('  FAIL', m); } };
const sleep = ms => new Promise(r => setTimeout(r, ms));
function freePort() {
  const l = Deno.listen({hostname: '127.0.0.1', port: 0});
  const p = l.addr.port;
  l.close();
  return p;
}
async function listing(dir) {
  const out = [];
  try { for await (const e of Deno.readDir(dir)) out.push(e.name); } catch (_) { return null; }
  return out.sort();
}

// the boot code of each test, as that test runs it
async function between(file, re) {
  const m = (await Deno.readTextFile(file)).match(re);
  if (!m) throw Error('FAIL: no boot code found in ' + file);
  return m[1];
}
const BOOTS = [
  {name: 'tests/cardkit_harness.py serve', args: (tmp, port) => ['tests/cardkit_harness.py', 'serve', tmp, String(port)]},
  {name: 'tests/player_cards.mjs BOOT', code: await between('tests/player_cards.mjs', /const BOOT = `([\s\S]*?)`;\n/),
   args: (tmp, port, code) => ['-c', code, root, tmp, String(port)]},
  {name: 'tests/youtube_capture.mjs BOOT', code: await between('tests/youtube_capture.mjs', /const BOOT = `([\s\S]*?)`;\n/),
   args: (tmp, port, code) => ['-c', code, root, tmp, String(port)]},
  {name: 'tests/book_cards.mjs SERVE', code: await between('tests/book_cards.mjs', /const SERVE = String\.raw`([\s\S]*?)`;\n/),
   args: (tmp, port, code) => ['-c', code, tmp, String(port)]},
];

const REPO_INBOX = root + '/youtube/anki/inbox';
const repoBefore = await listing(REPO_INBOX);
const WORK = await Deno.makeTempDir({prefix: 'parseh-hub-inbox-'});
// an .apkg is a zip: this one holds a single small file, which is all the
// upload looks at (it must start as a zip does)
const APKG = WORK + '/inbox-check.apkg';
{
  const o = await new Deno.Command(PY, {args: ['-c',
    'import sys, zipfile\nwith zipfile.ZipFile(sys.argv[1], "w") as z:\n    z.writestr("media", "{}")', APKG]}).output();
  if (o.code) throw Error(td.decode(o.stderr));
}
const apkgBytes = await Deno.readFile(APKG);

// whatever a drop put in the repository goes again
async function tidyRepo() {
  const now = await listing(REPO_INBOX);
  if (!now) return;
  for (const n of now) if (!(repoBefore || []).includes(n)) await Deno.remove(`${REPO_INBOX}/${n}`).catch(() => {});
  if (repoBefore === null) await Deno.remove(REPO_INBOX).catch(() => {});
}

const browser = await chromium.launch({executablePath: Deno.env.get('CHROME_BIN'), headless: true});
let hub = null;
const log = [];
try {
  for (const boot of BOOTS) {
    console.log(boot.name);
    const tmp = await Deno.makeTempDir({dir: WORK, prefix: 'tree-'});
    await Deno.mkdir(tmp + '/root/youtube/videos', {recursive: true});
    await Deno.symlink(root + '/lib', tmp + '/root/lib');
    await Deno.symlink(root + '/youtube/lib', tmp + '/root/youtube/lib');
    for (const d of ['library', 'exercises', 'anki', 'tray']) await Deno.mkdir(`${tmp}/${d}`);
    const port = freePort();
    log.length = 0;
    hub = new Deno.Command(PY, {args: boot.args(tmp, port, boot.code), cwd: root, stdout: 'piped', stderr: 'piped'}).spawn();
    for (const s of [hub.stdout, hub.stderr])
      (async () => { for await (const c of s.pipeThrough(new TextDecoderStream())) log.push(c); })();
    const B = `http://127.0.0.1:${port}`;
    for (const t = Date.now();;) {
      try { const r = await fetch(B + '/clips/api/status'); await r.body?.cancel(); if (r.ok) break; } catch (_) {}
      if (Date.now() - t > 60000) throw Error('the hub did not start:\n' + log.join(''));
      await sleep(250);
    }
    const page = await browser.newPage({viewport: {width: 1280, height: 900}});
    await page.goto(B + '/anki/sync/');
    await page.click('[data-done="1"]');
    await page.waitForSelector('#drop');
    const chooser = page.waitForEvent('filechooser');
    await page.click('#drop');
    await (await chooser).setFiles(APKG);
    await page.waitForFunction(() => { const i = document.getElementById('upinfo');
      return !i.hidden && /good|bad/.test(i.className); }, null, {timeout: 15000});
    const said = await page.evaluate(() => [document.getElementById('upinfo').className, document.getElementById('upinfo').textContent]);
    assert(said[0].includes('good') && /^Saved as /.test(said[1]), 'the page takes the drop: ' + said[1]);
    const inTree = (await listing(tmp + '/anki/inbox')) || [];
    const saved = inTree.filter(n => n.endsWith('-inbox-check.apkg'));
    const bytes = saved.length === 1 ? await Deno.readFile(`${tmp}/anki/inbox/${saved[0]}`) : new Uint8Array();
    assert(saved.length === 1 && bytes.length === apkgBytes.length && bytes.every((b, i) => b === apkgBytes[i]),
           'the file is in the temporary tree\'s anki/inbox/, byte for byte: ' + JSON.stringify(inTree));
    const repoNow = await listing(REPO_INBOX);
    assert(JSON.stringify(repoNow) === JSON.stringify(repoBefore),
           'and the repository\'s youtube/anki/inbox/ is as it was: ' + JSON.stringify(repoBefore) + ' -> ' + JSON.stringify(repoNow));
    assert(!/Traceback/.test(log.join('')), 'no traceback in the hub\'s log');
    await page.close();
    hub.kill('SIGTERM'); await hub.status; hub = null;
    await tidyRepo();
  }
  if (failed.length) throw Error('FAIL: ' + failed.length + ' check(s):\n  ' + failed.join('\n  '));
  console.log(`\nhub_inbox: ${passed} checks passed`);
} catch (e) {
  console.log(e.stack || e);
  console.log('hub log tail:\n' + log.join('').slice(-2000));
  Deno.exitCode = 1;
} finally {
  await browser.close();
  if (hub) { try { hub.kill('SIGTERM'); await hub.status; } catch (_) {} }
  await tidyRepo();
  await Deno.remove(WORK, {recursive: true}).catch(() => {});
}

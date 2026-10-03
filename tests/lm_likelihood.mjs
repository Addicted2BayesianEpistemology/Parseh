// SPDX-License-Identifier: GPL-3.0-or-later
// Offline browser checks. Generate fixtures with tests/lm_likelihood_fixture.py.
// PLAYWRIGHT_CORE=/path/to/playwright-core/index.mjs node tests/lm_likelihood.mjs
import { readFile } from 'node:fs/promises';
import assert from 'node:assert/strict';
const { chromium } = await import(process.env.PLAYWRIGHT_CORE || 'playwright-core');
const browser = await chromium.launch({executablePath: process.env.CHROME_BIN || '/usr/bin/google-chrome', headless: true, args: ['--no-sandbox']});
const fixture = JSON.parse(await readFile('/tmp/parseh-likelihood-browser-fixture.json', 'utf8'));
let checks = 0;
function ok(condition, message) { assert.ok(condition, message); checks++; }
try {
  const page = await browser.newPage();
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  await page.setContent('<textarea id="transcript">existing draft</textarea><div id="review"></div>');
  await page.addScriptTag({path: 'youtube/lib/asrreview.js'});
  await page.evaluate(data => {
    window.calls = []; window.view = data;
    window.connection = {configured: false, likelihood: {configured: true, available: true, revision: 'saved-revision', model: 'tiny-installed'}};
    window.review = ParsehAsrReview.mount(document.getElementById('review'), {
      choose: (...args) => calls.push(['choose', ...args]), retry: (...args) => calls.push(['retry', ...args]),
      cancel: () => calls.push(['cancel']),
      use: (decisions, edits) => { calls.push(['use', decisions, edits]); document.getElementById('transcript').value = 'explicit application'; }
    });
    review.show(data, 'choice', connection);
  }, fixture);
  ok(await page.locator('#stt_review_likelihood').isEnabled(), 'numeric method works without a chat connection');
  await page.locator('#stt_review_likelihood').click();
  ok((await page.evaluate(() => calls[0]))[1] === 'likelihood', 'explicit numeric method choice');
  await page.evaluate(() => review.show(view, 'review', connection));
  await page.locator('[data-review-word="s0w1"]').focus();
  ok((await page.locator('#stt_review_details').textContent()).includes('Raw log likelihood'), 'keyboard exposes scores');
  ok((await page.locator('#stt_review_details').textContent()).includes('LM beam search'), 'extra-candidate origins are displayed');
  ok((await page.locator('#stt_review_details').textContent()).includes('original Whisper'), 'original is displayed alongside alternatives');
  await page.evaluate(() => { view.review.result.suggestions[0].likelihood.hardware = {backend:'cuda',gpu_device:0,offloaded_layers:2,context_tokens:256,device:{description:'Local test GPU'}}; review.show(view, 'review', connection); });
  await page.locator('[data-review-word="s0w1"]').focus();
  ok((await page.locator('#stt_review_details').textContent()).includes('2 layers offloaded'), 'actual GPU offload diagnostics are displayed');
  await page.locator('#stt_review_details').getByRole('button', {name:'Accept this alternative', exact:true}).nth(1).click();
  ok(await page.locator('#transcript').inputValue() === 'existing draft', 'accept modifies only pending draft');
  await page.locator('#stt_use').click();
  ok(await page.locator('#transcript').inputValue() === 'explicit application', 'explicit Use invokes application');
  await page.evaluate(() => { document.getElementById('transcript').value = 'kept'; view.review.result.suggestions[0].candidates[0].applicable = false; view.review.result.suggestions[0].candidates[0].error = 'timeout'; view.review.result.suggestions[0].likelihood.coverage.state = 'partial'; review.show(view, 'review', connection); });
  await page.locator('[data-review-word="s0w1"]').click();
  ok(await page.locator('#stt_review_details').getByRole('button', {name:'Accept this alternative', exact:true}).first().isDisabled(), 'unscored candidate cannot be applied');
  await page.locator('#stt_review_cancel').click();
  ok(await page.locator('#transcript').inputValue() === 'kept', 'cancel leaves transcript untouched');
  await page.evaluate(() => review.show(view, 'correcting', connection));
  ok(await page.locator('#stt_use').isDisabled(), 'cannot apply in-flight results');
  ok(await page.locator('#stt_review_likelihood').isDisabled(), 'cannot start overlapping likelihood run');
  await page.evaluate(() => { view.review.result.suggestions[0].candidates[0].text = '<img src=x onerror="window.injected=true">'; review.show(view, 'review', connection); });
  await page.locator('[data-review-word="s0w1"]').click();
  ok(await page.locator('#stt_review_details img').count() === 0, 'candidate text is escaped');
  await page.evaluate(() => { view.review.evidence.language = 'fa'; document.documentElement.dir = 'rtl'; review.show(view, 'review', connection); });
  ok(await page.locator('[data-review-word="s0w1"]').count() === 1, 'RTL keeps stable IDs and accessible word controls');
  ok(errors.length === 0, 'review has no JavaScript errors');

  const settings = await browser.newPage();
  const defaults = JSON.parse(await readFile('/tmp/parseh-likelihood-browser-defaults.json', 'utf8'));
  await settings.route('http://parseh.test/**', async route => {
    if (!route.request().url().includes('/settings/api/')) return route.fulfill({status:200, contentType:'text/html', body:route.request().isNavigationRequest() ? await readFile('/tmp/parseh-likelihood-settings-host.html','utf8') : ''});
    const action = route.request().url().split('/').pop();
    const data = action === 'models' ? {models:[{id:'installed-id',model_id:'installed Qwen / Q4_1',architecture:'qwen3',bytes:1000}],errors:[]} : {configured:true,available:true,model:'installed Qwen / Q4_1',runtime:{available:true,gpu_devices:[{backend:'cuda',index:0,description:'Local test GPU',free_bytes:1073741824,total_bytes:4294967296}]},settings:defaults,install:{state:'not-requested'},loaded_workers:0};
    return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({ok:true,...data})});
  });
  await settings.goto('http://parseh.test/settings/lm-likelihood/');
  await settings.addScriptTag({path:'lib/lmlikelihoodsettings.js'});
  await settings.waitForFunction(() => document.getElementById('lm_devices').textContent.includes('CUDA device 0'));
  ok((await settings.locator('#lm_devices').textContent()).includes('Local test GPU'), 'runtime-discovered device and memory are displayed');
  ok(await settings.locator('#lm_gpu_device').inputValue() === '0', 'saved GPU selection is populated');
  await settings.locator('#lm_refresh').click();
  await settings.waitForFunction(() => document.getElementById('lm_models').value === 'installed-id');
  ok((await settings.locator('#lm_models').textContent()).includes('installed Qwen / Q4_1'), 'installed model selector is populated');
  const saved = settings.waitForRequest(req => req.url().endsWith('/select'));
  await settings.locator('#lm_select').click();
  ok(JSON.stringify((await saved).postDataJSON()) === JSON.stringify({id:'installed-id'}), 'selection sends inventory ID only');
  await settings.setContent(await readFile('/tmp/parseh-likelihood-settings-remote.html','utf8'));
  ok(await settings.locator('#lm_path').isDisabled(), 'remote browser cannot set arbitrary local path');
  ok(await settings.locator('#lm_gpu_device').isDisabled(), 'remote browser cannot alter worker hardware');
  ok(await settings.locator('#lm_models').isEnabled(), 'remote browser can select discovered models');
  console.log(`${checks} browser checks passed`);
} finally { await browser.close(); }

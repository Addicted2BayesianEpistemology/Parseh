// SPDX-License-Identifier: GPL-3.0-or-later
// Offline UI contracts: shared catalogue, model choices and second-pass controls.
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {readFile} from 'node:fs/promises';
const {chromium}=await import(process.env.PLAYWRIGHT_CORE || 'npm:playwright-core@1.52.0');
const python=process.env.PARSEH_PYTHON || 'python3';
const rendered=spawnSync(python,['-c',"import sys,json;sys.path[:0]=['lib','youtube/lib','.'];import speechpage;print(json.dumps({'script':speechpage.SCRIPT,'style':speechpage.lookuppage.STYLE+speechpage.STYLE}))"],{encoding:'utf8'});
assert.equal(rendered.status,0,rendered.stderr);
const assets=JSON.parse(rendered.stdout), origin='http://parseh.invalid';
const runtime={ready:true,have:true,state:'ready',version:'1.2.1',ctranslate2:'4.8.2',python:'cp312',size:1000};
function model(label,language,option,ready,available=true){return {label,language,languages:language?[language]:[],option,tag:option,hint:'Local speech recognition.',have:ready,ready,state:ready?'ready':'absent',size:ready?1000:0,download:2000,available,availability_reason:available?'':'A verified package is not yet available.',repo:'pinned/model',source:{repo:'source/<escaped>',revision:'1'.repeat(40)},limitations:['Quality on conversation is not established.'],compatibility:'package-verified',fully_compatible:false};}
const state={ok:true,where:'self',device:'test',preferences:{second_pass:true,models_by_language:{}},may:{},jobs:{speech:{}},sizes:{},credits:{},free:10000,kept:2000,
 languages:[{code:'fa',name:'Persian',native:'فارسی',rtl:true,whisper:true},{code:'hi',name:'Hindi',native:'हिन्दी',whisper:true},{code:'it',name:'Italian',native:'Italiano',whisper:true}],
 speech:{runtime,hardware:{checked:true,cpu:{compute:'int8',threads:2,logical:2,said:'CPU available'},cuda:{state:'none',ready:false,supported_build:false}},pin:{help:'/guide/'},aligners:{},requirements:[],models:{
  'large-v3-turbo':model('Whisper turbo',null,'Standard',true),'large-v3':model('Whisper large',null,'Standard',true),
  'fa-fast':model('Persian fast','fa','Fast',true),'fa-accuracy':model('Persian accuracy','fa','Accuracy, slower',false),
  'hi-fast':model('Hindi fast','hi','Fast',false,false),'it-special':model('Italian local','it','Language-specific',false),
 }}};
state.speech.models['it-special'].distribution='local-package';
state.speech.models['it-special'].package={name:'italian-prepared.zip',size:16,sha256:'a'.repeat(64)};
state.speech.models['it-special'].package_imported=false;
for(const id of ['runtime',...Object.keys(state.speech.models)])state.sizes['speech:'+id]={download:2000,kept:3000};
let checks=0;const ok=(v,m)=>{assert.ok(v,m);checks++;};
let browser,scene='settings',uploadBytes=0,pauseUpload=false,stoppedUploads=[];
try{
 browser=await chromium.launch({executablePath:process.env.CHROME_BIN || '/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
 const page=await browser.newPage({viewport:{width:1200,height:850}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.route(origin+'/**',async route=>{
   const request=route.request(),url=new URL(request.url());
   if(url.pathname==='/add-fixture/')return route.fulfill({contentType:'text/html',body:'<!doctype html><div class="addvid"><textarea id="box">Existing draft</textarea><div id="stt"></div></div>'});
   if(url.pathname==='/settings/api/speech/import-package'){
     uploadBytes=request.postDataBuffer().length;
     if(pauseUpload){await new Promise(resolve=>setTimeout(resolve,1000));return route.fulfill({json:{ok:false,error:'Upload cancelled'}}).catch(()=>{});}
     state.speech.models['it-special'].package_imported=true;
     Object.assign(state.speech.models['it-special'],{ready:true,have:true,state:'ready'});
     return route.fulfill({json:{ok:true}});
   }
   if(url.pathname==='/settings/speech/')return route.fulfill({contentType:'text/html',body:'<!doctype html><style>'+assets.style+'</style><div class="settings rh sp"><div id="sp-band"></div><input type="checkbox" id="sp_second_pass" checked><p id="sp_preferences_status"></p><div id="sp"></div></div><script type="application/json" id="sp-state">'+JSON.stringify(state).replace(/</g,'\\u003c')+'</script><script>'+assets.script+'</script>'});
   const body=request.postDataJSON() || {};
   if(url.pathname==='/lookup/api/stopspeech')stoppedUploads.push(body.key);
   if(url.pathname==='/settings/api/speech/save')Object.assign(state.preferences,body);
   if(url.pathname==='/settings/api/speech/select-model'){
     if(body.model)state.preferences.models_by_language[body.language]=body.model;else delete state.preferences.models_by_language[body.language];
   }
   if(scene==='add'){
     if(url.pathname==='/lookup/api/speech')return route.fulfill({json:{ok:true,installed:true,runtime,models:Object.entries(state.speech.models).map(([id,value])=>({id,...value})),default_model:'large-v3-turbo',processing:[{id:'auto',ready:true,now:'cpu'},{id:'cpu',ready:true}],aligners:[],preferences:state.preferences,languages:{fa:true,it:true,hi:true}}});
     if(url.pathname==='/youtube/api/transcribe/pending')return route.fulfill({json:{ok:true,pending:[]}});
     if(url.pathname==='/youtube/api/transcribe/start')return route.fulfill({json:{ok:true,job:'test-job',say:'Starting'}});
     if(url.pathname==='/youtube/api/transcribe/status')return route.fulfill({json:{ok:true,state:'whisper-second-pass',second_pass:{done:1,total:2,failed:0},say:'Whisper second pass'}});
     return route.fulfill({json:{ok:true,preferences:state.preferences}});
   }
   return route.fulfill({json:url.pathname.startsWith('/settings/api/')?{ok:true,preferences:state.preferences}:state});
 });
 await page.goto(origin+'/settings/speech/');
 ok(await page.locator('[data-row="fa-accuracy"]').count()===1,'full catalogue visible beyond the two standard models');
 await page.selectOption('#sp_language','fa');
 ok(await page.locator('[data-row="large-v3-turbo"]').count()===1,'standard models remain available in a language filter');
 ok(await page.locator('[data-row="hi-fast"]').count()===0,'other languages are excluded by filter');
 ok((await page.locator('[data-row="fa-accuracy"]').innerText()).includes('Accuracy, slower'),'Persian intended trade-off is explicit');
 await page.selectOption('#sp_preferred_model','fa-fast');
 await page.waitForFunction(()=>document.getElementById('sp_model_preference_status').textContent.startsWith('Saved'));
 ok(state.preferences.models_by_language.fa==='fa-fast','settings save the selected language model');
 await page.locator('#sp_installed_only').check();
 ok(await page.locator('[data-row="fa-accuracy"]').count()===0,'installed-only filter removes missing model');
 await page.locator('#sp_second_pass').uncheck();
 await page.waitForFunction(()=>document.getElementById('sp_preferences_status').textContent.startsWith('Saved'));
 ok(state.preferences.second_pass===false,'automatic second pass can be disabled');
 ok(state.preferences.models_by_language.fa==='fa-fast','second-pass preference preserves model selections');
 await page.locator('#sp_installed_only').uncheck();await page.selectOption('#sp_language','hi');
 ok(await page.locator('[data-row="hi-fast"] [data-get]').count()===0,'unverified package has no misleading installation control');
 ok((await page.locator('[data-row="hi-fast"]').innerText()).includes('A verified package is not yet available.'),'unavailable model explains why');
 ok(await page.locator('escaped').count()===0,'source metadata is escaped rather than inserted as HTML');
 await page.selectOption('#sp_language','it');
 ok(await page.locator('[data-row="it-special"] [data-get]').count()===0,'prepared packages require explicit import before installing');
 const wrongChooser=page.waitForEvent('filechooser');await page.click('[data-import="it-special"]');
 await (await wrongChooser).setFiles({name:'wrong.zip',mimeType:'application/zip',buffer:Buffer.alloc(17)});
 ok((await page.locator('[data-row="it-special"]').innerText()).includes('expected package size'),'wrong package size is refused before upload');
 await page.click('[data-cancel="it-special"]');
 const chooser=page.waitForEvent('filechooser');await page.click('[data-import="it-special"]');
 await (await chooser).setFiles({name:'italian-prepared.zip',mimeType:'application/zip',buffer:Buffer.alloc(16)});
 await page.waitForFunction(()=>document.querySelector('[data-row="it-special"]').textContent.includes('Installed'));
 ok(uploadBytes===16,'prepared package upload sends its exact bytes and refreshes installation status');
 pauseUpload=true;
 Object.assign(state.speech.models['it-special'],{ready:false,have:false,state:'absent',package_imported:false});
 await page.reload();await page.selectOption('#sp_language','it');
 const cancelledChooser=page.waitForEvent('filechooser');await page.click('[data-import="it-special"]');
 await (await cancelledChooser).setFiles({name:'italian-prepared.zip',mimeType:'application/zip',buffer:Buffer.alloc(16)});
 await page.waitForSelector('[data-upload-stop="it-special"]');await page.click('[data-upload-stop="it-special"]');
 await page.waitForFunction(()=>document.querySelector('[data-row="it-special"]').textContent.includes('upload cancelled'));
 ok(stoppedUploads.includes('it-special'),'upload cancel aborts HTTP work and stops the host installation job');
 pauseUpload=false;Object.assign(state.speech.models['it-special'],{ready:true,have:true,state:'ready',package_imported:true});
 await page.setViewportSize({width:390,height:850});
 ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'narrow settings layout stays inside the viewport');
 ok(errors.length===0,'catalogue settings have no browser script errors');
 const review=await readFile('youtube/lib/asrreview.js','utf8');
 scene='add';await page.goto(origin+'/add-fixture/');
 await page.addStyleTag({content:await readFile('youtube/lib/addstt.css','utf8')});
 await page.addScriptTag({content:review});await page.addScriptTag({content:await readFile('youtube/lib/addstt.js','utf8')});
 await page.evaluate(()=>{
  localStorage.clear();window.currentLanguage={code:'fa',name:'Persian',native:'فارسی'};
  window.addReview=ParsehAddStt.mount({root:document.getElementById('stt'),source:()=>({kind:'film',value:'/a/local/film.mp4'}),lang:()=>currentLanguage,transcript:()=>document.getElementById('box').value,setTranscript:text=>document.getElementById('box').value=text,confirm:()=>true});
 });
 await page.waitForFunction(()=>document.querySelector('#stt_model').options.length===3);
 ok(await page.inputValue('#stt_model')==='fa-fast','Add Video selects the saved language model');
 ok(await page.locator('#stt_model option[value="it-special"]').count()===0,'Add Video hides installed models for other languages');
 await page.selectOption('#stt_model','large-v3');
 await page.waitForFunction(()=>document.querySelector('#stt_model').value==='large-v3');
 await page.evaluate(()=>{currentLanguage={code:'it',name:'Italian',native:'Italiano'};addReview.langChanged();});
 ok(await page.locator('#stt_model option[value="it-special"]').count()===1,'changing language refreshes applicable installed models');
 await page.evaluate(()=>{currentLanguage={code:'fa',name:'Persian',native:'فارسی'};addReview.langChanged();});
 ok(await page.inputValue('#stt_model')==='large-v3','model selections are remembered independently by language');
 await page.click('#stt_go');await page.waitForSelector('#stt_second_pass',{state:'visible'});
 ok((await page.locator('#stt_second_pass_label').textContent()).includes('1 / 2'),'second pass has completed/total suspect-word progress');
 ok(await page.locator('#stt_second_pass_bar').getAttribute('aria-valuenow')==='1','second-pass progress is accessible');
 ok(await page.inputValue('#box')==='Existing draft','second-pass processing leaves transcript box untouched');
 await page.click('#stt_cancel');await page.waitForFunction(()=>document.getElementById('stt').dataset.state==='idle');
 ok(await page.locator('#stt_second_pass').isHidden(),'cancellation clears second-pass progress');
 ok(errors.length===0,'language selection and second-pass processing have no script errors');
 console.log(`${checks} catalogue and second-pass browser checks passed`);
}finally{if(browser)await browser.close();}

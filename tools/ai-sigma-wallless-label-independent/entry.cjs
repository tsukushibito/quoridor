'use strict';
const fs=require('fs'),path=require('path'),CP=require('child_process'),crypto=require('crypto'),{createRequire}=require('module');
const {OwnedProcesses,boundedStop}=require('../ai-sigma-actual-boundary-repair/cleanup.cjs'),{createMonitor}=require('../ai-sigma-actual-boundary-repair/pause-check.cjs');
const ROOT=path.resolve(__dirname,'../..'),run=process.argv[2],BASE=ROOT+'/.artifacts/ai-sigma/resume-20261002/WALLLESS-LABEL-INDEPENDENT',OUT=BASE+'/runs/'+run;
async function main(){
 const cfg=JSON.parse(fs.readFileSync(ROOT+'/research-data/ai-sigma/143-wallless-label-independent/config.json')),a=JSON.parse(fs.readFileSync(BASE+'/runs/'+run+'.admission.json'));
 if(a.decision!=='launch_allowed'||a.remaining_unknown!==0||!a.ownership_confirmed||Date.now()-Date.parse(a.UTC)>30000||Date.now()>=Date.parse(cfg.newjob_deadline))throw Error('ADMISSION_REFUSED_OR_STALE');
 fs.mkdirSync(OUT,{recursive:true});const save=(n,x)=>fs.writeFileSync(OUT+'/'+n+'.json',JSON.stringify(x)+'\n');
 const monitor=createMonitor({out:OUT,subjectIssue:'quoridor-4lc.143',deadlineUTC:cfg.processing_deadline,windowEndUTC:'2026-10-02T23:20:59Z'}),owner=new OwnedProcesses({tracePath:OUT+'/cleanup.jsonl'});let browser=null,page=null,primary=null;
 try{
  await monitor.start();monitor.check();const{chromium}=createRequire('/workspaces/quoridor/package.json')('playwright'),original=CP.spawn;CP.spawn=(...args)=>owner.observeChild(original(...args));
  try{browser=await chromium.launch({headless:true,executablePath:'/workspaces/quoridor/artifacts/playwright/chromium-1243/chrome-linux64/chrome',args:['--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--disable-software-rasterizer','--use-gl=disabled','--renderer-process-limit=1']});}finally{CP.spawn=original;}
  page=await browser.newPage();await page.route('**/*',r=>r.abort());await page.addScriptTag({content:"globalThis.workerAttempts=0;globalThis.Worker=class{constructor(){workerAttempts++;throw Error('WORKER_FORBIDDEN');}};"});
  const sources=[];for(const p of ['tools/ai-sigma-actual-boundary-repair/game.js','tools/ai-sigma-actual-boundary-repair/context.js','tools/ai-sigma-wallless-label-independent/checker.js']){const text=fs.readFileSync(ROOT+'/'+p,'utf8');sources.push({path:p,SHA256:crypto.createHash('sha256').update(text).digest('hex')});await page.addScriptTag({content:text});}
  const echoes=await page.evaluate(()=>[...document.scripts].map(s=>s.textContent));save('served-source',{sources,browser_echo_SHA256:echoes.map(s=>crypto.createHash('sha256').update(s).digest('hex')),independent_fetch:false,inline_echo:true});
  const inputText=fs.readFileSync(BASE+'/input.json','utf8');save('input-ref',{SHA256:crypto.createHash('sha256').update(inputText).digest('hex'),JSON_text_parse_in_browser:true});
  monitor.check();save('preflight',await page.evaluate(text=>preflight(text),inputText));
  for(let i=0;i<2;i++){monitor.check();const result=await page.evaluate(k=>executeCase(k),i);save('case-'+i,result);if(!result.root_intervals_equal)throw Error('INDEPENDENT_ROOT_INTERVAL_MISMATCH');}
  save('browser-status',await page.evaluate(()=>({Worker_attempts:workerAttempts,Model:0,NN:0,solver_started:WL.started,solver_completed:WL.completed,main_active:WL.active,timer_message:0})));monitor.check();
 }catch(e){primary={name:e.name,message:e.message,stack:e.stack};save('primary',primary);if(page)try{save('partial-status',await page.evaluate(()=>({Worker_attempts:workerAttempts,started:WL.started,completed:WL.completed,active:WL.active})));}catch(_){};}
 finally{await monitor.stop();save('monitor-stop',{callback_stopped:true});save('controlled-stop',await boundedStop({owner,stop:async()=>{if(browser)await browser.close();return{remaining_pids:0};}}));}
 save('summary',{primary,NN:0,Model:0,AIWorker:0,new_games:0});if(primary)process.exitCode=1;
}
main().catch(e=>{console.error(e.stack);process.exitCode=1;});

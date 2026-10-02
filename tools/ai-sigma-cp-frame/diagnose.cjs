'use strict';
const fs=require('fs');
const path=require('path');
const {boundedStop}=require('../ai-sigma-actual-boundary-repair/cleanup.cjs');
const ROOT=path.resolve(__dirname,'../..');
const OUT=ROOT+'/.artifacts/ai-sigma/resume-20261002/CP-FRAME';
async function main() {
  if(process.argv[2]!=='--config')throw Error('CONFIG_REQUIRED');
  const config=JSON.parse(fs.readFileSync(process.argv[3]));
  if(config.issue!=='quoridor-4lc.107'||config.frame!==7)throw Error('FRAME_BINDING');
  const mode=config.kind==='browser-preflight'?'preflight':'NN';
  if(!['preflight','NN'].includes(mode))throw Error('MODE_REQUIRED');
  const run=config.run_id;
  const directory=OUT+'/runs/'+run;
  fs.mkdirSync(directory,{recursive:false});
  const save=(name,data)=>fs.writeFileSync(directory+'/'+name+'.json',JSON.stringify(data,null,2)+'\n');

  const fixtures=JSON.parse(fs.readFileSync(ROOT+'/.artifacts/ai-sigma/reference-fixtures/SIGMA-PARITY-PLAN/fixtures.json')).fixtures;
  const references=JSON.parse(fs.readFileSync(ROOT+'/.artifacts/ai-sigma/runs/SIGMA-INFERENCE-PROBE/ort-a.outputs.json'));
  const monitor=require('../ai-sigma-actual-boundary-repair/pause-check.cjs').createMonitor({out:directory,subjectIssue:'quoridor-4lc.107',deadlineUTC:config.processing_deadline,windowEndUTC:'2026-10-02T10:02:31Z'});
  let browser=null,primary=null,secondary=[],rows=[],startup=null;
  try {
    await monitor.start();monitor.check();
    browser=await require('./browser-sab.cjs').open(directory,()=>{throw Error('PER_CP_NODE_BINDING_FORBIDDEN');},()=>{throw Error('PER_HAND_NODE_ACK_BINDING_FORBIDDEN');});
    save('browser-preflight',await browser.page.evaluate(()=>browserPreflight()));
    if(mode==='NN') {
      if(Date.now()>=Date.parse(config.newjob_deadline))throw Error('NEW_HEAVY_CUTOFF');
      monitor.check();save('config',config);
      await browser.load();
      startup=await browser.page.evaluate(({fixtures,references})=>browserStartup(fixtures,references),{fixtures,references});save('startup',startup);
      // One evaluate drives all requests in browser; Node never supplies per-hand clocks or judges.
      const result=await browser.page.evaluate(({config,references})=>runFunctional(config,references),{config,references});
      rows=result.rows;save('browser-result',result);save('rows',rows);

    }
  } catch(error) {
    primary={name:error.name,message:error.message,stack:error.stack};save('primary',primary);
    if(browser)try{const partial=await browser.page.evaluate(()=>collectBrowser());rows=partial.rows;save('partial-browser-result',partial);}catch(error){secondary.push({stage:'partial-collect',message:error.message});}
  } finally {
    if(browser)try{save('main-timers-stop',await browser.page.evaluate(()=>abortBrowserTimers()));}catch(error){secondary.push({stage:'main-timers-stop',message:error.message});}
    if(browser&&browser.loadState.ready)try{save('finally-model-drop',await browser.page.evaluate(()=>dropEarly()));}catch(error){secondary.push({stage:'finally-drop',message:error.message});}
    if(browser)try {save('outer-controlled-stop',await boundedStop(browser));}catch(error){secondary.push({stage:'browser-stop',message:error.message});}
    try{await monitor.stop();}catch(error){secondary.push({stage:'monitor-stop',message:error.message});}
  }
  const summary={issue:'quoridor-4lc.107',mode,run,diagnostic:true,actual_go:false,games:0,holdout:0,planned:mode==='NN'?config.schedule.length+(config.dynamic_plies??0):0,completed:rows.length,missing:mode==='NN'?config.schedule.length+(config.dynamic_plies??0)-rows.length:0,startup_NN:startup?.startup_NN??0,hand_NN:rows.reduce((n,row)=>n+row.hand_NN,0),primary,secondary,browser_judgement:true,per_CP_Node_binding_calls:0,Node_per_hand_clock_calls:0};
  save('summary',summary);console.log(JSON.stringify(summary));
  if(primary||secondary.length)process.exitCode=1;
}
main().catch(error=>{console.error(error.stack);process.exitCode=1;});

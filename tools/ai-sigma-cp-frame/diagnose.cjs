'use strict';
const fs=require('fs');
const path=require('path');
const {boundedStop}=require('../ai-sigma-actual-boundary-repair/cleanup.cjs');
const ROOT=path.resolve(__dirname,'../..');
const OUT=ROOT+'/.artifacts/ai-sigma/resume-20261002/CP-FRAME';
async function main() {
  const mode=process.argv[2];
  if(!['preflight','NN'].includes(mode))throw Error('MODE_REQUIRED');
  const run=mode==='NN'?'browser-sab-r1':'static-browser-r1';
  const directory=OUT+'/'+run;
  fs.mkdirSync(directory,{recursive:false});
  const save=(name,data)=>fs.writeFileSync(directory+'/'+name+'.json',JSON.stringify(data,null,2)+'\n');
  const config=JSON.parse(fs.readFileSync(OUT+'/browser-config.json'));
  const fixtures=JSON.parse(fs.readFileSync(ROOT+'/.artifacts/ai-sigma/reference-fixtures/SIGMA-PARITY-PLAN/fixtures.json')).fixtures;
  const references=JSON.parse(fs.readFileSync(ROOT+'/.artifacts/ai-sigma/runs/SIGMA-INFERENCE-PROBE/ort-a.outputs.json'));
  const monitor=require('../ai-sigma-actual-boundary-repair/pause-check.cjs').createMonitor({out:directory,subjectIssue:'quoridor-4lc.107',deadlineUTC:'2026-10-02T05:20:00Z',windowEndUTC:'2026-10-02T05:39:12Z'});
  let browser=null,primary=null,secondary=[],rows=[],startup=null;
  try {
    await monitor.start();monitor.check();
    browser=await require('./browser-sab.cjs').open(directory,()=>{throw Error('PER_CP_NODE_BINDING_FORBIDDEN');},()=>{throw Error('PER_HAND_NODE_ACK_BINDING_FORBIDDEN');});
    save('browser-preflight',await browser.page.evaluate(()=>browserPreflight()));
    if(mode==='NN') {
      if(Date.now()>=Date.parse('2026-10-02T05:15:00Z'))throw Error('NEW_HEAVY_CUTOFF');
      monitor.check();save('config',config);
      await browser.load();
      startup=await browser.page.evaluate(({fixtures,references})=>browserStartup(fixtures,references),{fixtures,references});save('startup',startup);
      // One evaluate drives all requests in browser; Node never supplies per-hand clocks or judges.
      const result=await browser.page.evaluate(async({config,references})=>{
        const rows=[];
        for(const spec of config.schedule)rows.push(await browserRequest(spec,references.find(row=>row.id==='initial-p1')));
        return rows;
      },{config,references});
      rows=result;save('rows',rows);
      save('model-drop',await browser.page.evaluate(()=>dropEarly()));
    }
  } catch(error) {
    primary={name:error.name,message:error.message,stack:error.stack};save('primary',primary);
  } finally {
    if(browser)try {save('outer-controlled-stop',await boundedStop(browser));}catch(error){secondary.push({stage:'browser-stop',message:error.message});}
    try{await monitor.stop();}catch(error){secondary.push({stage:'monitor-stop',message:error.message});}
  }
  const summary={issue:'quoridor-4lc.107',mode,run,diagnostic:true,actual_go:false,games:0,holdout:0,planned:mode==='NN'?config.schedule.length:0,completed:rows.length,missing:mode==='NN'?config.schedule.length-rows.length:0,startup_NN:startup?.startup_NN??0,hand_NN:rows.reduce((n,row)=>n+row.hand_NN,0),primary,secondary,browser_judgement:true,per_CP_Node_binding_calls:0,Node_per_hand_clock_calls:0};
  save('summary',summary);console.log(JSON.stringify(summary));
  if(primary||secondary.length)process.exitCode=1;
}
main().catch(error=>{console.error(error.stack);process.exitCode=1;});

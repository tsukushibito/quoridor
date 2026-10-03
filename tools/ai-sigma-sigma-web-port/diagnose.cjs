'use strict';
const fs=require('fs'),path=require('path'),crypto=require('crypto'),{boundedStop}=require('../ai-sigma-actual-boundary-repair/cleanup.cjs');
const ROOT=path.resolve(__dirname,'../..'),OUT=ROOT+'/.artifacts/ai-sigma/resume-20261003/SIGMA-WEB-PORT';
async function main(){
 if(process.argv[2]!=='--config')throw Error('CONFIG_REQUIRED');const config=JSON.parse(fs.readFileSync(process.argv[3]));if(config.issue!=='quoridor-4lc.151'||config.seed!==1979)throw Error('PORT_CONFIG');
 const dir=OUT+'/runs/'+config.run_id;fs.mkdirSync(dir,{recursive:false});const save=(n,d)=>fs.writeFileSync(dir+'/'+n+'.json',JSON.stringify(d,null,2)+'\n');
 const fixtures=JSON.parse(fs.readFileSync(ROOT+'/.artifacts/ai-sigma/reference-fixtures/SIGMA-PARITY-PLAN/fixtures.json')).fixtures,references=JSON.parse(fs.readFileSync(ROOT+'/.artifacts/ai-sigma/runs/SIGMA-INFERENCE-PROBE/ort-a.outputs.json'));
 const monitor=require('./pause-monitor.cjs').createMonitor({out:dir,subjectIssue:'quoridor-4lc.151',deadlineUTC:config.processing_deadline,windowEndUTC:'2026-10-03T04:15:21Z'});let browser=null,primary=null,secondary=[],startup=null,result=null,timer=null,busy=false,promise=null;
 try{
  await monitor.start();monitor.check();browser=await require('./browser.cjs').open(dir,config);
  save('config',config);save('preflight',await browser.page.evaluate(()=>browserPreflight()));save('rules-mock',await browser.page.evaluate(()=>browserRulesMock()));save('routing-mock',await browser.page.evaluate(({config,fixtures})=>portMock(config,fixtures),{config,fixtures}));
  if(config.generate_only){const plan=JSON.parse(fs.readFileSync(config.seed_table));save('generated-prefixes',await browser.page.evaluate(plan=>portGenerate(plan),plan));}
  else{
   const binary=fs.readFileSync(OUT+'/build/faithful.wasm');if(crypto.createHash('sha256').update(binary).digest('hex')!==config.binary_SHA256)throw Error('SERVED_BINARY_BINDING');
   const input=JSON.parse(fs.readFileSync(config.fixed_input_path));if(crypto.createHash('sha256').update(fs.readFileSync(config.fixed_input_path)).digest('hex')!==config.fixed_input_SHA256)throw Error('FIXED_INPUT_BINDING');
   timer=setInterval(()=>{if(busy)return;busy=true;promise=(async()=>{try{monitor.check();}catch(e){clearInterval(timer);timer=null;try{save('monitor-abort',await browser.page.evaluate(reason=>browserAbort(reason),{code:e.message}));}catch(e){secondary.push({stage:'monitor-abort',message:e.message})}}finally{busy=false}})();},250);
   monitor.check();save('monitor-ready-before-NN',{UTC:new Date().toISOString(),state:monitor.state,ready:monitor.ready});await browser.load();startup=await browser.page.evaluate(({fixtures,references})=>browserStartup(fixtures,references),{fixtures,references});save('startup',startup);
   if(config.kind==='stageA')result=await browser.page.evaluate(({config,input})=>runPortMechanism(config,input.fixtures),{config,input});
   else{
    await browser.page.exposeFunction('saveFinishedGame',d=>{if(!config.games.some(g=>g.id===d.game.id))throw Error('UNREGISTERED_GAME');save('completed-game-'+d.game.id,d)});
    fixtures.push(...input.prefixes.filter(x=>x.accepted).map(x=>x.fixture));result=await browser.page.evaluate(({config,fixtures,references})=>runBrowserGames(config,fixtures,references),{config,fixtures,references});
   }
   save('browser-result',result);save('clock-end',await browser.page.evaluate(()=>calibratePlayerClocks()));if(result.errors?.length)throw Error('STAGEA_GATE_FAILURE');
  }
 }catch(e){primary={name:e.name,message:e.message,stack:e.stack};save('primary',primary);}
 finally{
  if(timer){clearInterval(timer);timer=null;}if(promise)await promise;save('monitor-callback-stop',{timer:!!timer,busy,waited:!busy});
  if(browser)try{save('main-timers-stop',await browser.page.evaluate(()=>abortBrowserTimers()));}catch(e){secondary.push({stage:'main-timers',message:e.message})}
  if(browser?.loadState.ready)try{save('finally-model-drop',await browser.page.evaluate(()=>dropEarly()));}catch(e){secondary.push({stage:'model-drop',message:e.message})}
  try{await monitor.stop();const status=JSON.parse(fs.readFileSync(dir+'/pause-monitor-stop.json'));save('control-status',{state:status.state,failure:status.failure,all_owned_read_callbacks_waited:status.all_owned_read_callbacks_waited,scientific_result_stored:!!result,scope:'control outcome separate from completed scientific rows'});if(status.state!=='READY'||status.failure)secondary.push({stage:'late_monitor_control_failure',message:status.failure?.code??status.state,scientific_rows_not_replaced:true});}catch(e){secondary.push({stage:'monitor-stop',message:e.message})}
  if(browser)try{save('outer-controlled-stop',await boundedStop(browser))}catch(e){secondary.push({stage:'controlled-stop',message:e.message})}
 }
 const summary={issue:config.issue,kind:config.kind,run:config.run_id,startup_NN:startup?.startup_NN??0,model_sessions:startup?2:0,hand_NN:result?.hand_NN??0,started:result?.started??result?.started_games??0,planned:config.searches?.length??config.games?.length??0,primary,secondary};save('summary',summary);console.log(JSON.stringify(summary));if(primary||secondary.length)process.exitCode=1;
}
main().catch(e=>{console.error(e.stack);process.exitCode=1});

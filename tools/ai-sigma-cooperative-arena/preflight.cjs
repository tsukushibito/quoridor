'use strict';
const fs = require('fs');
const assert = require('assert/strict');
const A = require('./arena.cjs');
const G = require('../ai-sigma-actual-boundary-repair/game-loop.cjs');
const {createMonitor} = require('../ai-sigma-actual-boundary-repair/pause-check.cjs');
const {OwnedProcesses, boundedStop} = require('../ai-sigma-actual-boundary-repair/cleanup.cjs');
const CP = require('child_process');

async function main() {
  const config = JSON.parse(fs.readFileSync(process.argv[2]));
  const out = A.OUT + '/preflight-r2';
  fs.mkdirSync(out, {recursive:false});
  const save = (name, value) => fs.writeFileSync(out+'/'+name+'.json', JSON.stringify(value)+'\n');
  const append = (name, value) => fs.appendFileSync(out+'/'+name+'.jsonl', JSON.stringify(value)+'\n');
  A.validate(config);
  assert.equal(typeof require('../ai-sigma-tail-transport/real-backend.cjs').factory, 'function');
  assert.throws(() => A.validate({...config,games_before:6}));
  const monitor = createMonitor({out,subjectIssue:config.issue,deadlineUTC:config.processing_deadline,windowEndUTC:'2026-10-02T05:39:12Z'});
  await monitor.start();
  let stopCount=0, dropped=false;
  const createBackend = async () => ({
    startup:{ready:true,mock:true},
    create({identity,meta}) {
      assert.equal(meta.tail_condition,'cooperative');
      assert.equal(identity.deadline_ms-identity.t0_ms,500);
      assert.equal(identity.commit_cutoff_ms-identity.t0_ms,402);
      return {identity};
    },
    submit(context) {
      const state=A.J.state(context.identity.legal_prefix);
      return {engine:context.identity.engine,echo:context.identity,accepted:true,checkpoint:true,action:A.J.rustAction(state,state.getLegalActions()[0]),value:0,fallback:0};
    },
    async finish() {stopCount++;return {handles:0,activeNN:0,live_searches:0};},
    async stop() {dropped=true;return {handles:0,activeNN:0,controlledPID0:true};}
  });
  const result=await A.execute({...config,run_id:'mock-four-ply-r1',stage:'four-ply'}, {createBackend,monitor,save,append,diagnosticMock:true});
  assert.equal(result.primary,null);
  assert.equal(result.secondary.length,0);
  assert.equal(result.turns,4);
  assert.equal(result.NN_hand,0);
  assert.equal(stopCount,4);
  assert(dropped);
  const rows=fs.readFileSync(out+'/turns.jsonl','utf8').trim().split('\n').map(JSON.parse);
  for(let i=1;i<rows.length;i++) assert(rows[i].t0_ms>=rows[i-1].stop_ACK_ms);
  const fault=await G.runGame({prefix:[],candidateColor:1,platform:'browser',clock:A.clock.now,choose:async engine=>({engine,accepted:false,error:'NO_COMPLETED_SNAPSHOT',action:null})});
  assert.equal(fault.kind,'engine_loss');
  assert.equal(fault.responsible_engine,'candidate');
  const owner=new OwnedProcesses({tracePath:out+'/guardian.jsonl'});
  assert.equal(owner.rootIdentity.ppid,process.ppid);
  try {
    const child=owner.observeChild(CP.spawn('python3',['-B','-c',"import pathlib,os,time\np=pathlib.Path(os.environ['TMPDIR'])\nfor i in range(20):\n f=p/('race'+str(i));f.write_bytes(b'x'*4096);f.unlink()\ntime.sleep(.05)"]));
    await new Promise((resolve,reject)=>{child.once('error',reject);child.once('exit',resolve)});
    await owner.registrationReceipt();
  } finally {save('guardian-stop',await boundedStop({owner,stop:async()=>({remaining_pids:0})}));}
  save('checks',{passed:true,NN:0,Chromium:0,checks:['cooperative-factory-interface','D500-cutoff402','game-loop-legal-four-ply','Judge-UTF8-before-stamp','next-t0-after-owned-ACK','typed-noCP-candidate-loss','owned-child-PPID-TMP-race-stop','monitor-READY-stop']});
  console.log('PREFLIGHT_PASS');
}
main().catch(error=>{console.error(error.stack);process.exitCode=1});

'use strict';
const fs=require('fs'),CP=require('child_process'),assert=require('assert/strict'),{BASE,DEADLINE}=require('./run-scope.cjs'),{OwnedProcesses,boundedStop}=require('./cleanup.cjs'),{createMonitor}=require('./pause-check.cjs');
async function main(){const owner=new OwnedProcesses({tracePath:BASE+'/guardian-owned.jsonl'});let monitor;try{
 monitor=createMonitor({out:BASE,subjectIssue:'quoridor-4lc.77',deadlineUTC:DEADLINE});await monitor.start();monitor.check();
 assert.equal(owner.rootIdentity.ppid,process.ppid);
 const child=owner.observeChild(CP.spawn('python3',['-c',`import os,time,pathlib
p=pathlib.Path(os.environ['TMPDIR'])
for i in range(50):
 f=p/('race'+str(i));f.write_bytes(b'x'*4096);f.unlink()
if os.fork()==0:
 os.setsid()
 if os.fork()==0:time.sleep(.25);os._exit(0)
 os._exit(0)
time.sleep(.05)`]));
 await new Promise((resolve,reject)=>{child.once('error',reject);child.once('exit',resolve)});await new Promise(r=>setTimeout(r,450));await owner.registrationReceipt();
 fs.writeFileSync(BASE+'/guardian-gate.json',JSON.stringify({pass:true,NN:0,Chromium:0,ownedPPID:true,created_unlinked_files:50,monitor_READY:true})+'\n');
 }finally{if(monitor)await monitor.stop();const proof=await boundedStop({owner,stop:async()=>({remaining_pids:0})});fs.writeFileSync(BASE+'/guardian-cleanup.json',JSON.stringify(proof)+'\n')}}
main().catch(e=>{fs.writeFileSync(BASE+'/guardian-primary.json',JSON.stringify({name:e.name,message:e.message,stack:e.stack})+'\n');console.error(e);process.exitCode=1});

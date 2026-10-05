'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const {Worker}=require('node:worker_threads');
const path=require('node:path');
const protocol=require('./shared-best-action.cjs');
const cases=[];
function check(name, action) { action(); cases.push(name); }
const context={generation:7,key:'initial-position',legalActions:[3,5,13]};
const buffer=protocol.create(context);
const producer=protocol.bind(buffer,context,context);
const consumer=protocol.bind(buffer,context,context);
const cp={completed:true,sequence:1,action:13,value:0.5,visits:4};
check('first-none',()=>assert.equal(consumer.readLatest(),null));
check('complete-fields-bits',()=>{producer.publish(cp);assert.deepEqual(consumer.readLatest(),cp);});
check('update',()=>{producer.publish({...cp,sequence:2,action:3,value:-1,visits:5});assert.equal(consumer.readLatest().action,3);});
check('incomplete-rejected',()=>assert.throws(()=>producer.publish({...cp,sequence:3,completed:false}),/INCOMPLETE/));
check('NaN-rejected',()=>assert.throws(()=>producer.publish({...cp,sequence:3,value:NaN}),/VALUE/));
check('Inf-rejected',()=>assert.throws(()=>producer.publish({...cp,sequence:3,value:Infinity}),/VALUE/));
check('range-rejected',()=>assert.throws(()=>producer.publish({...cp,sequence:3,value:1.0001}),/VALUE/));
check('illegal-rejected',()=>assert.throws(()=>producer.publish({...cp,sequence:3,action:200}),/ILLEGAL/));
check('old-sequence-rejected',()=>assert.throws(()=>producer.publish(cp),/SEQUENCE/));
check('old-generation-rejected',()=>assert.throws(()=>protocol.bind(buffer,{...context,generation:8},{...context,generation:8}),/GENERATION/));
check('foreign-position-rejected',()=>assert.throws(()=>protocol.bind(buffer,{...context,key:'foreign'},context),/CONTEXT/));
check('budget-preserves-complete',()=>{producer.stop('budget');assert.equal(consumer.readLatest().sequence,2);assert.equal(producer.publish({...cp,sequence:3}),false);});
check('cancel-invalidates',()=>{consumer.stop('cancel');assert.equal(consumer.readLatest(),null);assert.equal(producer.publish({...cp,sequence:3}),false);});
const fresh=protocol.create({...context,generation:8});
check('fresh-no-old-cp',()=>assert.equal(protocol.bind(fresh,{...context,generation:8},{...context,generation:8}).readLatest(),null));
const mixed=protocol.create(context),mw=protocol.bind(mixed,context,context),mr=protocol.bind(mixed,context,context);
mw.publish(cp);mr.readLatest();
check('odd-write-bounded-old-cache',()=>{Atomics.store(new Int32Array(mixed),protocol.INDEX.revision,3);Atomics.store(new Int32Array(mixed),protocol.INDEX.action,5);assert.deepEqual(mr.readLatest(),cp);});
check('odd-first-write-null',()=>{const b=protocol.create(context);Atomics.store(new Int32Array(b),protocol.INDEX.revision,1);assert.equal(protocol.bind(b,context,context).readLatest(),null);});
check('fault-invalidates-cache',()=>{mr.stop('fault');assert.equal(mr.readLatest(),null);});

async function concurrency() {
  const shared=protocol.create(context),reader=protocol.bind(shared,context,context);
  const worker=new Worker(`const {workerData}=require('node:worker_threads');const p=require(workerData.module);const writer=p.bind(workerData.shared,workerData.context,workerData.context);for(let sequence=1;sequence<=20000;sequence++)writer.publish({completed:true,sequence,action:sequence%2?3:13,value:sequence%2?0.5:-0.5,visits:sequence});`,{eval:true,workerData:{module:path.resolve(__dirname,'shared-best-action.cjs'),shared,context}});
  let finished=false,reads=0;
  const ended=new Promise((resolve,reject)=>{worker.once('exit',code=>{finished=true;code===0?resolve():reject(Error('MOCK_WORKER_EXIT_'+code));});worker.once('error',reject);});
  while(!finished) {
    for(let i=0;i<64;i++) {
      const snapshot=reader.readLatest();
      if(snapshot) {
        assert.equal(snapshot.visits,snapshot.sequence);
        assert.equal(snapshot.action,snapshot.sequence%2?3:13);
        assert.equal(snapshot.value,snapshot.sequence%2?0.5:-0.5);
        reads++;
      }
    }
    await new Promise(resolve=>setImmediate(resolve));
  }
  await ended;
  assert.equal(reader.readLatest().sequence,20000);
  return {publications:20000,consistent_reads:reads,worker_thread_exit:0,bounded_reader_attempts:2,main_Atomics_wait_calls:0,scope:'Node worker_threads SAB protocol only; not browser/AI validation'};
}
concurrency().then(concurrent=>{
  const result={issue:'quoridor-4lc.107',NN:0,Chromium:0,cases,concurrent};
  fs.writeFileSync(path.resolve(__dirname,'../../.artifacts/ai-sigma/resume-20261002/CP-FRAME/protocol-mock.json'),JSON.stringify(result,null,2)+'\n');
  console.log(JSON.stringify(result));
}).catch(error=>{console.error(error.stack);process.exitCode=1;});

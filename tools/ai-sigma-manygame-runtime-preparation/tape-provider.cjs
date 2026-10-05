'use strict';
// Saved evidence only, no ORT/Torch imports or forward calls; supports exactly two K32 tapes.
const fs=require('fs'),readline=require('readline'),assert=require('assert');
const saved=JSON.parse(fs.readFileSync(process.argv[2])),names=['initial-p1','asym-hv-p2'];let count=0;
const tapes=new Map(names.map(n=>[n,saved.rows.find(x=>x.engine==='candidate'&&x.fixture_id===n).numeric]));
const emit=x=>process.stdout.write(JSON.stringify(x)+'\n');
readline.createInterface({input:process.stdin}).on('line',s=>{let q={};try{q=JSON.parse(s);if(q.op==='stop'){emit({request_id:q.request_id,ok:true,result:{count,cap:64,model_sessions:0,saved_tape:true}});process.stdin.destroy();return;}assert(q.op==='infer_batch'&&q.items.length>=1&&q.items.length<=8);assert(count+q.items.length<=64,'TAPE_CAP');const items=q.items.map(x=>{const n=tapes.get(x.tape_fixture)?.[x.tape_index];assert(n,'TAPE_ENTRY');assert.deepStrictEqual(x.features_bits648,n.features_bits);return{id:x.id,logits:n.policy_logits,value:n.value,f32bits137:n.NN_bits}});count+=items.length;emit({request_id:q.request_id,ok:true,result:{items,actual_batch:items.length,model_sessions:0,saved_tape:true}});}catch(e){emit({request_id:q.request_id,ok:false,error:{message:e.message}})}});

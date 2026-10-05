'use strict';
const fs=require('fs'),assert=require('assert'),crypto=require('crypto'),{n,q,now}=require('./engine.cjs'),leaf=require('./leaf.cjs');
const c=JSON.parse(fs.readFileSync(process.argv[2])),{w,m}=n.load(c.weight_manifest),cases=JSON.parse(fs.readFileSync(c.cases_manifest)).cases;
let NN=0,processed=0;const begin=now(),results=[];
const saveCounter=()=>fs.writeFileSync(c.counter_file,JSON.stringify({all_samples:NN,processed,completed_conditions:results.filter(x=>x.status==='COMPLETED').length})+'\n');saveCounter();
const save=partial=>fs.writeFileSync(c.output,JSON.stringify({UTC:new Date().toISOString(),samples:NN,processed,results,partial,wholewall_ms:now()-begin,scope:'239 saved-selected exploratory counterfactual; root children each searched full-window; not old nonbest failsoft or teacher truth'},null,2)+'\n');
for(const [caseIndex,f] of cases.entries())for(const engine of ['NNUE','distance'])for(const depth of [1,2]){
 const start=now(),root=q.r.fromPrefix(f.before_prefix),key=root._positionKey(),hist=n.history(root);assert.equal(key,f.before_position_key);assert.equal(root.getCurrentPlayer(),f.side);assert.equal(root.depth,f.ply);
 const stats={processed:0,NN:0,D_evals:0,terminal:0,clone:0,full:0,delta:0,legal_list:0,cutoffs:0},spans={terminal_inclusive_ms:0,legal_inclusive_ms:0,clone_ms:0,input_inclusive_ms:0,evaluation_ms:0};
 const measure=(name,fn)=>{const t=now();try{return fn()}finally{spans[name]+=now()-t}};
 function control(){if(now()-begin>=c.internal_hard_ms)throw Error('INTERNAL_TIME_CAP');if(NN>=c.NNcap)throw Error('GLOBAL_NN_CAP');if(processed>=c.processed_cap)throw Error('PROCESSED_CAP')}
 function legal(s){stats.legal_list++;return measure('legal_inclusive_ms',()=>s.getLegalActions().map(action=>({action,Action:q.r.rustAction(s,action)})).sort((a,b)=>a.Action-b.Action))}
 function child(s,a){stats.clone++;return measure('clone_ms',()=>s.next(a))}
 function delta(a,s){if(engine!=='NNUE')return null;stats.delta++;return measure('input_inclusive_ms',()=>q.delta(a,s,w))}
 function visit(s,a,d,alpha,beta){control();processed++;stats.processed++;const t=measure('terminal_inclusive_ms',()=>d===0?leaf.terminal(s,stats):q.r.terminalResult(s));if(t){stats.terminal++;return t.value}if(d===0)return measure('evaluation_ms',()=>{if(engine==='NNUE'){control();NN++;stats.NN++;return n.valueScaled(a,w,m)}stats.D_evals++;return leaf.distanceKnownNonterminal(s,m)});let v=-Infinity;for(const item of legal(s)){const ch=child(s,item.action),x=-visit(ch,delta(a,ch),d-1,-beta,-alpha);v=Math.max(v,x);alpha=Math.max(alpha,x);if(alpha>=beta){stats.cutoffs++;break}}assert(Number.isFinite(v));return v}
 const row={caseIndex,slot:f.slot,ply:f.ply,source_hand_id:f.source_hand_id,source_selected_Action:f.Action,source_completed_depth:f.completed_depth,engine,depth,status:'STARTED',values:[],stats,spans};results.push(row);
 try{control();assert(!q.r.terminalResult(root));const actions=legal(root);let accum=null,buffer=null;if(engine==='NNUE'){stats.full++;accum=measure('input_inclusive_ms',()=>q.full(root,w));buffer=accum.a.map(x=>Array.from(x))}
 for(const item of actions){control();const ch=child(root,item.action),v=-visit(ch,delta(accum,ch),depth-1,-Infinity,Infinity);assert(Number.isFinite(v));row.values.push({Action:item.Action,action:item.action,value:v,bound:'EXACT_FINITE_DEPTH_FULL_WINDOW'});saveCounter()}
 assert.equal(row.values.length,actions.length);assert.equal(root._positionKey(),key);assert.equal(n.history(root),hist);if(accum)assert.deepStrictEqual(accum.a.map(x=>Array.from(x)),buffer);
 const max=Math.max(...row.values.map(x=>x.value));row.max_value=max;row.argmax_Actions=row.values.filter(x=>x.value===max).map(x=>x.Action);row.strict_first_Action=row.argmax_Actions[0];const selected=row.values.find(x=>x.Action===f.Action);assert(selected);row.source_selected_value=selected.value;row.source_selected_gap=max-selected.value;row.legal_count=actions.length;row.parent_copy_key_history_buffer_restored=true;row.status='COMPLETED';
 }catch(e){if(!['INTERNAL_TIME_CAP','GLOBAL_NN_CAP','PROCESSED_CAP'].includes(e.message))throw e;row.status='INCOMPLETE';row.typed_stop=e.message;row.all_exact_child_values_adopted=false}
 row.wall_ms=now()-start;saveCounter();save(true);
}
save(false);console.log(JSON.stringify({conditions:results.length,completed:results.filter(x=>x.status==='COMPLETED').length,samples:NN,processed,wholewall_ms:now()-begin}));

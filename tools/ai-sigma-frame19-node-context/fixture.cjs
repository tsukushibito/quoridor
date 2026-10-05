"use strict";
const fs=require('fs'),assert=require('assert'),crypto=require('crypto'),{performance}=require('perf_hooks');
const {r,createNodeContext,stamp,VERSION}=require('./node-context.cjs');
const out=process.argv[2],witnesses=[];let checks=0;
function check(name,fn){fn();checks++;witnesses.push(name);}
function throws(fn,code){assert.throws(fn,e=>e.code===code);}
function state(){return new r.State({boardsize:9,walls_p1:10,walls_p2:10,walls_initial:10});}
function equivalent(s,key){const c=createNodeContext(s,key),v=c.read(s,key);assert.deepStrictEqual(v.terminal,r.terminalResult(s)?{...r.terminalResult(s)}:null);if(!v.terminal)assert.equal(JSON.stringify(v.legal),JSON.stringify(s.getLegalActions()));return c;}
// Fixed deterministic all-legal replay, no teacher/game outcome collection.
const states=[];let s=state();for(let i=0;i<32;i++){states.push(s);const legal=s.getLegalActions();const walls=legal.filter(a=>a.type==='wall');const pawns=legal.filter(a=>a.type==='pawn');const safe=pawns.filter(a=>s.next(a).winner()===0);const lateral=safe.filter(a=>a.direction[0]!==0);const choices=lateral.length?lateral:safe;const a=i%6===4&&walls.length?walls[Math.floor(walls.length/2)]:choices[i%Math.max(1,choices.length)]||walls[0];assert(a&&!r.terminalResult(s));s=s.next(a);}
for(let i=0;i<32;i++)check('legal-prefix-'+i,()=>equivalent(states[i],'fixture/'+i));
for(const [name,mutate] of [
 ['side',s=>s.depth++],['depth-draw',s=>s.depth=200],['p1goal',s=>s.player1pos=[4,8]],['p2goal',s=>s.player2pos=[4,0]],
 ['history',s=>s.position_history.set('new-context',2)],['rem',s=>s.walls_p1--],['hsegments',s=>s.hwalls[0]=1],['vsegments',s=>s.vwalls[0]=1],
 ['anchors',s=>s.hwall_anchors.add('0,0')],['dist',s=>s.p1_dist=new Int32Array(s.p1_dist).fill(0)],['path',s=>s.p1_path_edges=new Set()],['legalcache',s=>s._legal_actions_cache.pop()]
])check('invalidate-'+name,()=>{const t=state(),c=equivalent(t,name);mutate(t);throws(()=>c.read(t,name),'STATE_MUTATED');throws(()=>c.read(t,name),'NODE_CONTEXT_INVALIDATED');});
check('clone-identity',()=>{const t=state(),c=equivalent(t,'clone');throws(()=>c.read(t.copy(),'clone'),'IDENTITY_OR_CONTEXT_CHANGED');});
check('context-generation',()=>{const t=state(),c=equivalent(t,'g1');throws(()=>c.read(t,'g2'),'IDENTITY_OR_CONTEXT_CHANGED');});
check('cancel',()=>{const t=state(),c=equivalent(t,'cancel');throws(()=>c.read(t,'cancel',{cancelled:true}),'CANCELLED');throws(()=>c.read(t,'cancel'),'NODE_CONTEXT_INVALIDATED');});
check('dispose',()=>{const t=state(),c=equivalent(t,'dispose');c.dispose();throws(()=>c.read(t,'dispose'),'NODE_CONTEXT_INVALIDATED');});
check('rule-method',()=>{const t=state(),c=equivalent(t,'rule');t.winner=()=>0;throws(()=>c.read(t,'rule'),'STATE_MUTATED');});
check('parent-restoration',()=>{const t=state(),c=equivalent(t,'parent'),b=stamp(t);const a=t.getLegalActions()[0];t.next(a);assert.equal(stamp(t),b);assert(c.read(t,'parent'));});
for(const [name,opts,expected] of [['goalP1',{player1pos:[4,8]},1],['goalP2',{player2pos:[4,0],depth:1},1],['draw200',{depth:200},0]])check(name,()=>{const t=new r.State({boardsize:9,walls_p1:10,walls_p2:10,...opts}),c=equivalent(t,name),v=c.read(t,name);assert.equal(v.terminal.value,expected);assert.equal(v.legal,null);});
check('history-no-legal',()=>{const t=new r.State({boardsize:9,walls_p1:0,walls_p2:0,walls_initial:10});for(const a of t.getLegalActions()){const n=t.next(a);t.position_history.set(n._positionKey(),2);}t._legal_actions_cache=null;assert.equal(t.getLegalActions().length,0);const c=equivalent(t,'no-legal');assert.equal(c.read(t,'no-legal').terminal.value,0);});
check('return-immutable',()=>{const t=state(),c=equivalent(t,'immutable'),v=c.read(t,'immutable');assert(Object.isFrozen(v)&&Object.isFrozen(v.legal)&&Object.isFrozen(v.legal[0]));assert.throws(()=>v.legal.pop(),TypeError);});
// Same semantic work: term at search, legal at expansion, term at D wrapper.
// No distance/model evaluation. Same per-round replay clone cohort, both orderings.
function replay(mode,cohort,repeats){let checksum=0;for(let j=0;j<repeats;j++)for(let i=0;i<cohort.length;i++){const t=cohort[i];if(mode==='original'){const term=r.terminalResult(t);if(term)checksum+=term.value;else{checksum+=t.getLegalActions().length;assert.equal(r.terminalResult(t),null);}}else{const c=createNodeContext(t,'bench/'+i),v=c.read(t,'bench/'+i);if(v.terminal)checksum+=v.terminal.value;else{checksum+=v.legal.length;assert.equal(v.terminal,null);}c.dispose();}}return checksum;}
const measurements=[];
for(const [round,order] of [['AB',['original','module']],['BA',['module','original']],['AB2',['original','module']],['BA2',['module','original']]]){
 const row={round,order,times_ms:{},checksums:{},states:32,repeats:10};
 for(const mode of order){const prepStart=performance.now(),cohort=states.map(s=>{const t=s.copy();t.getLegalActions();return t;});row[mode+'_cohort_prep_ms']=performance.now()-prepStart;const before=cohort.map(stamp);const start=performance.now();row.checksums[mode]=replay(mode,cohort,10);row.times_ms[mode]=performance.now()-start;assert.deepStrictEqual(cohort.map(stamp),before);}
 assert.equal(row.checksums.original,row.checksums.module);measurements.push(row);
}
// Mutation stamp assertions are outside both replay timers; safety stamps inside module remain charged.
const original=measurements.reduce((a,x)=>a+x.times_ms.original,0),moduleTotal=measurements.reduce((a,x)=>a+x.times_ms.module,0);
const result={schema:'node-context-fixture-v1',version:VERSION,checks,witnesses,replay_states:32,measurements,original_total_ms:original,module_total_ms:moduleTotal,ratio:moduleTotal/original,meaning:'terminal/legal wrappers only; no NN/distance/search/arena speed claim',state_source_readonly:true,cache_hit_work:true,NN:0,GPU:0,notes:['full state/history/derived/legal-cache safety stamp and immutable Action copies are charged','common pre/post preservation assertions outside route timer; module safety stamps inside timer','timed cohorts legal-cache prepopulated equally; cohort preparation reported outside route','AB/BA order, one finite script; no unlimited warmups','prefix fixtures are diagnostics, not new teacher games']};
fs.writeFileSync(out,JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify({checks,original_total_ms:original,module_total_ms:moduleTotal,ratio:result.ratio,NN:0}));

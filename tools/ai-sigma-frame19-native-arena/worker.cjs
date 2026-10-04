'use strict';
const fs=require('fs'),readline=require('readline'),{search,now,n,q}=require('./engine.cjs');
const loaded=n.load(process.argv[2]);let allNN=0,active=null,latest=-1;
const emit=x=>process.stdout.write(JSON.stringify(x)+'\n');emit({type:'READY',pid:process.pid,allNN});
readline.createInterface({input:process.stdin}).on('line',line=>{
 let c;try{c=JSON.parse(line);if(c.kind==='STOP'){active=null;return emit({type:'STOP_ACK',id:c.id,allNN})}if(c.kind==='CLOSE'){emit({type:'CLOSE_ACK',allNN});process.exit(0)}
 if(c.kind!=='SEARCH'||!Number.isInteger(c.generation)||c.generation<=latest)return emit({type:'REJECTED',id:c.id,reason:'STALE_GENERATION',allNN});latest=c.generation;active=c.id;
 const s=q.r.fromPrefix(c.prefix);if(s._positionKey()!==c.key||n.history(s)!==c.history)throw Error('INPUT_IDENTITY');
 const r=search(s,c.engine,loaded.w,loaded.m,{nodeCap:c.node_cap,maxDepth:c.maxdepth,deadlineMs:c.deadline_ms,ordering:c.ordering,onNN:()=>{if(allNN>=c.NNcap)throw Error('GLOBAL_NN_CAP');allNN++}});
 emit({type:'RESULT',id:c.id,generation:c.generation,key:c.key,history:c.history,allNN,search:r,worker_complete_ms:now()});active=null;
 }catch(e){emit({type:'FAULT',id:c?.id,allNN,reason:e.stack});active=null}
});

'use strict';
const fs=require('fs'),readline=require('readline'),{search,now,n,q}=require('./engine.cjs');
const {mode}=require('./schema.cjs');
const models=JSON.parse(fs.readFileSync(process.argv[2]));const loadedModels={L:n.load(models.L),I:n.load(models.I)};let allNN=0,allProcessed=0,active=null,latest=-1;
const emit=x=>process.stdout.write(JSON.stringify(x)+'\n');emit({type:'READY',pid:process.pid,allNN});
readline.createInterface({input:process.stdin}).on('line',line=>{
 let c;try{c=JSON.parse(line);if(c.kind==='STOP'){active=null;return emit({type:'STOP_ACK',id:c.id,allNN})}if(c.kind==='CLOSE'){emit({type:'CLOSE_ACK',allNN});process.exit(0)}
 if(c.kind!=='SEARCH'||!Number.isInteger(c.generation)||c.generation<=latest)return emit({type:'REJECTED',id:c.id,reason:'STALE_GENERATION',allNN});latest=c.generation;active=c.id;
 const {leafPackage,distanceMode}=mode(c);const loaded=loadedModels[c.model_id];const s=q.r.fromPrefix(c.prefix);if(s._positionKey()!==c.key||n.history(s)!==c.history)throw Error('INPUT_IDENTITY');
 const r=search(s,c.engine,loaded.w,loaded.m,{leafPackage,distanceMode,nodeCap:Math.min(c.node_cap,c.processedCap-allProcessed),maxDepth:c.maxdepth,deadlineMs:c.deadline_ms,ordering:c.ordering,onNN:()=>{if(allNN>=c.NNcap)throw Error('GLOBAL_NN_CAP');allNN++}});
 allProcessed+=r.stats.processed;emit({type:'RESULT',model_id:c.model_id,allProcessed,distance_mode:distanceMode,leaf_package:leafPackage,id:c.id,generation:c.generation,key:c.key,history:c.history,allNN,search:r,worker_complete_ms:now()});active=null;
 }catch(e){emit({type:'FAULT',id:c?.id,allNN,reason:e.stack});active=null}
});

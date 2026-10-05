'use strict';
const {GamePool,ArtificialRegistry}=require('./gamepool.cjs'),I=require('./identity.cjs');
const number=Number(process.argv[2]),maxHandles=Number(process.argv[3]),worker='w'+number,run=process.argv[4],backend=new ArtificialRegistry(number),pending=new Map,waits=new Map;let pool,waitId=0;
const broker={
 infer:(identity,features_bits648)=>new Promise((resolve,reject)=>{pending.set(identity.request_id,{identity,resolve,reject});process.send({kind:'infer',identity,features_bits648});}),
 cancel:(w,g,generation,r)=>{process.send({kind:'cancel',worker:w,game:g,generation,run:r});return{pending:true};},
 quiescentGame:(w,g,r)=>new Promise(resolve=>{const id='drain.'+(++waitId);waits.set(id,resolve);process.send({kind:'wait_game',worker:w,game:g,run:r,id});})
};
pool=new GamePool(worker,backend,broker,{run,maxHandles});
process.on('message',q=>{if(q.kind==='reply'){const p=pending.get(q.request_id);if(!p)return;pending.delete(q.request_id);if(q.error)p.reject(Error(q.error));else if(I.key(q.data.identity)!==I.key(p.identity))p.reject(Error('WORKER_REPLY_IDENTITY'));else p.resolve(q.data);}
 else if(q.kind==='drained'){waits.get(q.id)?.();waits.delete(q.id);}
 else if(q.kind==='cancel')pool.cancel(q.game,q.generation);
 else if(q.kind==='run'){void Promise.all(q.games.map(game=>pool.search(game,{K:4}))).then(results=>process.send({kind:'result',worker,results,resumes:backend.resumes.length,zero:{handles:backend.trees.size,pending:pending.size,waits:waits.size,active:pool.games.size}})).catch(e=>process.send({kind:'fatal',error:e.stack}));}
 else if(q.kind==='close'){pool.stop();if(pool.games.size||pending.size||waits.size)process.send({kind:'fatal',error:'CLOSE_NONZERO'});else{process.send({kind:'closed',worker});process.disconnect();}}
});

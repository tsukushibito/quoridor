'use strict';
const {GamePool}=require('../ai-sigma-common/generation/game-pool.cjs'),{ArtificialRegistry}=require('./mock-registry.cjs'),I=require('../ai-sigma-common/generation/identity.cjs');
const number=Number(process.argv[2]),maxHandles=Number(process.argv[3]),worker='w'+number,run=process.argv[4],backend=new ArtificialRegistry(number);let pool;
const {WorkerBroker}=require('../ai-sigma-common/generation/worker-broker.cjs');
const broker=new WorkerBroker(message=>process.send(message),{identityError:'WORKER_REPLY_IDENTITY'});
pool=new GamePool(worker,backend,broker,{run,maxHandles});
process.on('message',q=>{if(broker.handle(q))return;
 if(q.kind==='cancel')pool.cancel(q.game,q.generation);
 else if(q.kind==='run'){void Promise.all(q.games.map(game=>pool.search(game,{K:4}))).then(results=>process.send({kind:'result',worker,results,resumes:backend.resumes.length,zero:{handles:backend.trees.size,pending:broker.pending.size,waits:broker.waits.size,active:pool.games.size}})).catch(e=>process.send({kind:'fatal',error:e.stack}));}
 else if(q.kind==='close'){pool.stop();if(pool.games.size||broker.pending.size||broker.waits.size)process.send({kind:'fatal',error:'CLOSE_NONZERO'});else{process.send({kind:'closed',worker});process.disconnect();}}
});

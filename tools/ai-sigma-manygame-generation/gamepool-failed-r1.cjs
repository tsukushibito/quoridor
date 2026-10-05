'use strict';
const I=require('./identity.cjs');
class GamePool{
 constructor(worker,backend,broker,{run='native187',maxHandles=8}={}){if(![4,8].includes(maxHandles))throw Error('HANDLE_CAP');Object.assign(this,{worker,backend,broker,run,maxHandles});this.games=new Map;this.seq=0;this.stopped=false;}
 async search(game,{K=4,generation=1,fixture={}}={}){if(this.stopped)throw Error('POOL_STOPPED');if(this.games.has(game))throw Error('ACTIVE_GAME');if(this.games.size>=this.maxHandles)throw Error('HANDLE_CAP');const s={game,generation,handle:null,pending:null,cancelled:false,NN_started:0,NN_returned:0,NN_discarded:0,completed:0};this.games.set(game,s);let cp=null,typed=null,firstNN=null,last_leafNN=null,firstPending=null;
  try{s.handle=await this.backend.new(fixture,generation,K);while(!s.cancelled){const z=await this.backend.begin(s.handle,generation);let done=!!z.done;if(z.pending){if(s.pending)throw Error('ONE_PENDING_PER_GAME');const id=I.validate({run_id:this.run,worker_id:this.worker,game_id:game,generation,handle:s.handle,token:z.token,request_id:this.worker+':'+(++this.seq)});s.pending=id;s.NN_started++;let row;try{row=await this.broker.infer(id,z.features_bits);s.NN_returned++;if(firstNN===null){firstPending=z;firstNN={features_bits:z.features_bits,NN_bits:row.NN.f32bits137,policy_logits:row.NN.logits,value:row.NN.value};}last_leafNN={value:row.NN.value,side:z.turn+1,ply:z.ply,view:"last expanded NN leaf side-to-move"};}catch(e){if(e.message==='CANCEL_RETURN_DISCARDED'){s.NN_returned++;s.NN_discarded++;}throw e;}if(I.key(row.identity)!==I.key(id))throw Error('GENERATION_HANDLE_TOKEN_ATTRIBUTION');if(s.cancelled){s.NN_discarded++;throw Error('CANCEL_RETURN_DISCARDED')}s.pending=null;const resumed=await this.backend.resume(s.handle,generation,z.token,row.NN);done=!!resumed.done;s.completed=resumed.simulations;}await new Promise(resolve=>setImmediate(resolve));if(done&&!s.cancelled){cp=await this.backend.checkpoint(s.handle,generation);s.completed=cp.simulations;break;}}if(s.cancelled)typed='CANCELLED';}
  catch(e){typed=e.message;}
  finally{if(s.pending){this.broker.cancel(this.worker,game,generation,this.run);await this.broker.quiescentGame(this.worker,game,this.run);s.pending=null;}if(s.handle!==null){await this.backend.cancel(s.handle,generation);await this.backend.free(s.handle);}this.games.delete(game);}
  return{first_NN:firstNN,firstPending,last_leafNN,game_id:game,generation,cp,typed,status:typed?'CONTROL_OR_MOCK_UNKNOWN':cp?.root_visits===K?'MOCK_OR_TAPE_COMPLETE':'TERMINAL_OR_INCOMPLETE',counters:{started:s.NN_started,returned:s.NN_returned,discarded:s.NN_discarded,completed:s.completed},zero:{pending:0,handle:0},mock_or_tape:false,model_forward:s.NN_started};
 }
 cancel(game,generation){const s=this.games.get(game);if(!s)return{active:false};if(s.generation!==generation)return{active:true,error:'STALE_CANCEL_GENERATION'};s.cancelled=true;return this.broker.cancel(this.worker,game,generation,this.run);}
 stop(){this.stopped=true;for(const s of this.games.values())this.cancel(s.game,s.generation);}
}
class ArtificialRegistry{
 constructor(workerNumber=0){this.next=0;this.trees=new Map;this.workerNumber=workerNumber;this.resumes=[];}
 async new(fixture,generation,K){const h=++this.next;this.trees.set(h,{generation,K,n:0,pending:false,token:0,marker:this.workerNumber*100+h,fixture});return h;}
 get(h,g){const s=this.trees.get(h);if(!s||s.generation!==g)throw Error('REGISTRY_GENERATION');return s;}
 async begin(h,g){const s=this.get(h,g);if(s.pending)throw Error('REGISTRY_ONE_PENDING');if(s.fixture.guard)throw Error('MOCK_CAPACITY_GUARD');if(s.fixture.terminal)return{done:true,pending:false};if(s.n>=s.K)return{done:true,pending:false};if(s.fixture.terminal_steps&&s.n>0){s.n++;return{done:s.n===s.K,pending:false};}s.pending=true;s.token++;const bits=Array(648).fill(0);bits[0]=new Uint32Array(new Float32Array([s.marker]).buffer)[0];return{pending:true,token:s.token,features_bits:bits};}
 async resume(h,g,token,NN){const s=this.get(h,g);if(!s.pending||s.token!==token||NN.logits[0]!==s.marker)throw Error('MOCK_TREE_MIX');s.pending=false;s.n++;this.resumes.push({handle:h,generation:g,token});return{done:s.n===s.K,simulations:s.n,nn_calls:s.n};}
 async checkpoint(h,g){const s=this.get(h,g);return{root_visits:s.n,simulations:s.n,root_mean:.25,action:s.n?0:null,root_edges:s.n>1?[{action:0,visits:s.n-1}]:[]};}
 async cancel(h,g){this.get(h,g).pending=false;return{discarded:true};}
 async free(h){this.trees.delete(h);}
}
module.exports={GamePool,ArtificialRegistry};

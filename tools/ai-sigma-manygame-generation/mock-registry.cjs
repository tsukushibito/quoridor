'use strict';
// Synthetic backend only; this is not a teacher or a model implementation.
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
module.exports={ArtificialRegistry};

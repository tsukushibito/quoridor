/* Research-only receiver: immutable completed snapshots; no inference at seal. */
(function(root){
 const eq=(a,b)=>JSON.stringify(a)===JSON.stringify(b), copy=x=>JSON.parse(JSON.stringify(x));
 const freeze=x=>{if(x&&typeof x==='object'){Object.values(x).forEach(freeze);Object.freeze(x)}return x};
 function finiteTree(x){if(typeof x==='number'&&!Number.isFinite(x))throw Error('NONFINITE');if(x&&typeof x==='object')Object.values(x).forEach(finiteTree)}
 class SnapshotCache{
  constructor(identity,expected,clock){this.identity=freeze(copy(identity));this.expected=expected;this.clock=clock;this.sequence=0;this.cache=null;this.sealed=false;this.fault=null;this.events=[];this.result=null;this.stateVersion=0;}
  receive(m){const received=this.clock(),version=this.stateVersion;const event={kind:m.kind,sequence:m.sequence??null,received_ms:received,accepted:false};try{
   if(this.sealed)throw Error('AFTER_SEAL');if(received>=this.identity.deadline_ms)throw Error('AFTER_DEADLINE');if(!eq(m.identity,this.identity))throw Error('IDENTITY_MISMATCH');
   if(m.kind==='fault'||m.kind==='cancel'){if(typeof m.error!=='string'||!m.error.length)throw Error('FAULT_TYPE');this.stateVersion++;this.fault=m.error??'CANCELLED';this.cache=null;event.accepted=true;return true;}
   if(this.fault)throw Error('REQUEST_DISCARDED');if(received>=(this.identity.commit_cutoff_ms??this.identity.deadline_ms))throw Error('AFTER_CUTOFF');if(m.kind!=='snapshot')throw Error('KIND');if(!Number.isSafeInteger(m.sequence)||m.sequence<=this.sequence)throw Error('NONMONOTONIC_SEQUENCE');
   const o=m.owned,c=o?.cp;finiteTree(m);
   if(!o||!c||!eq(o.identity,{request_id:this.identity.request_id,generation:this.identity.generation,fixture:this.identity.fixture??null,prefix:this.identity.prefix,seed:1979,simulations:this.identity.limits.simulations,max_nodes:512,max_depth:24}))throw Error('OWNED_IDENTITY');
   if(this.expected.terminal!=null&&o?.completed_token!==null)throw Error('TERMINAL_TOKEN');
   if(this.expected.terminal==null&&(!Number.isSafeInteger(o?.completed_token)||o.completed_token<=0))throw Error('COMPLETION_TOKEN_TYPE');
   if(o.pending_token!==null||!Number.isSafeInteger(o.completed_NN)||o.completed_NN<0||!Number.isSafeInteger(o.NN_attempts)||o.NN_attempts!==o.completed_NN||o.completed_NN!==c.nn_calls||o.completed_token==null&&this.expected.terminal==null)throw Error('COMPLETION_TOKEN');
   if(!Number.isFinite(o.completed_at)||!Number.isFinite(m.sent_ms)||o.completed_at>m.sent_ms||m.sent_ms>received+(this.expected.clock_error_ms??.2)||o.completed_at>=this.identity.deadline_ms)throw Error('COMPLETION_CLOCK');
   if(c.generation!==this.identity.generation||c.policy_fallbacks!==0||c.value_fallbacks!==0||!Array.isArray(c.root_edges))throw Error('CHECKPOINT');
   for(const k of ['simulations','nn_calls','nodes','nodes_count','edges_count','max_depth','arena_bytes','high_water'])if(!Number.isSafeInteger(c[k])||c[k]<0)throw Error('STATS_TYPE');
   if(c.simulations>this.identity.limits.simulations||c.nodes!==c.nodes_count||c.nodes>512||c.max_depth>24||c.nn_calls!==o.completed_NN||c.high_water<c.arena_bytes||typeof c.cap!=='boolean')throw Error('STATS_CONSISTENCY');
   const ids=c.root_edges.map(e=>e[0]);if(ids.length!==new Set(ids).size||!eq([...ids].sort((a,b)=>a-b),[...this.expected.legal].sort((a,b)=>a-b)))throw Error('LEGAL_SET');
   let priors=0,visits=0;for(const e of c.root_edges){if(e.length!==4||!Number.isInteger(e[0])||!Number.isFinite(e[1])||e[1]<0||e[1]>1||!Number.isSafeInteger(e[2])||e[2]<0||!Number.isFinite(e[3])||Math.abs(e[3])>e[2]+1e-5)throw Error('EDGE_RANGE');priors+=e[1];visits+=e[2];}
   if(this.expected.terminal){if(c.action!==null||c.terminal_value!==this.expected.terminal.value||c.nn_calls!==0||c.simulations!==0||ids.length)throw Error('TERMINAL');}
   else if(!this.expected.legal.includes(c.action)||c.terminal_value!==null||Math.abs(priors-1)>1e-4||visits!==Math.max(0,c.simulations-1))throw Error('LEGAL_OR_STATS');
   if(this.cache){const old=this.cache.owned;if(c.simulations<old.cp.simulations||o.completed_NN<old.completed_NN||c.nodes<old.cp.nodes||c.edges_count<old.cp.edges_count||c.high_water<old.cp.high_water)throw Error('REGRESSING_STATS');if(o.completed_NN>old.completed_NN&&o.completed_token<=old.completed_token||o.completed_NN===old.completed_NN&&o.completed_token!==old.completed_token)throw Error('NONMONOTONIC_COMPLETION_TOKEN');}
   if(!Number.isFinite(m.value)||Math.abs(m.value)>1)throw Error('STRICT_VALUE');
   const candidate=freeze(copy(m));if(this.expected.validationHook)this.expected.validationHook(candidate);
   const completed=this.clock();event.validation_finished_ms=completed;
   if(this.sealed||this.fault||version!==this.stateVersion||this.expected.getGeneration&&this.expected.getGeneration()!==this.identity.generation)throw Error('VALIDATION_STATE_CHANGED');
   if(completed>=(this.identity.commit_cutoff_ms??this.identity.deadline_ms))throw Error('VALIDATION_FINISHED_AFTER_CUTOFF');
   this.sequence=m.sequence;this.cache=candidate;event.accepted=true;event.validated_cache_ms=completed;return true;
  }catch(e){event.error=e.message;return false;}finally{this.events.push(event)}}
  seal(reason='deadline'){if(this.sealed)return this.result;const decision=this.clock();if(['deadline','early_seal'].includes(reason)&&decision<(this.identity.seal_ms??this.identity.deadline_ms))throw Error('EARLY_TIMER');if(this.expected.getGeneration&&this.expected.getGeneration()!==this.identity.generation){this.fault='STALE_GENERATION';this.cache=null;}this.sealed=true;this.stateVersion++;
   const cp=this.cache?.owned.cp??null;this.result=freeze({request_id:this.identity.request_id,generation:this.identity.generation,identity:this.identity,action:this.fault?null:cp?.action??null,checkpoint:!!cp&&!this.fault,error:this.fault??(!cp?'NO_COMPLETED_SNAPSHOT':null),sequence:this.sequence,owned:this.fault?null:this.cache?.owned??null,decision_ms:decision,snapshot_age_ms:cp?decision-this.cache.owned.completed_at:null,timer_lateness_ms:reason==='deadline'?Math.max(0,decision-this.identity.deadline_ms):0,seal_reason:reason});return this.result;
  }
 }
 SnapshotCache.prototype.invalidate=function(reason){this.stateVersion++;if(!this.sealed){this.fault=reason;this.cache=null}};
 const api={SnapshotCache,freeze,copy};if(typeof module!=='undefined')module.exports=api;Object.assign(root,api);
})(globalThis);

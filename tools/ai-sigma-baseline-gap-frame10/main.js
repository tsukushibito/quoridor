"use strict";
const gapBaseFailure=gameFailureResult;
gameFailureResult=function(classification,currentPlayer,engine,fault=null){
 const shared=/IDENTITY|MODEL_BIND|PRODUCER_LIMITS|PLAYER_|SAB_|SHARED_|UNKNOWN_SHARED/.test(fault?.error??'');
 if(classification==='engine_fault'&&shared)return {status:'unfinished',winner:null,reason:'shared_infrastructure_fault',pair_invalid:true,responsible_engine:engine,fault};
 const result=gapBaseFailure(classification,currentPlayer,engine,fault);
 if(result.status==='responsibility_loss'&&engine==='reference')result.reference_fault=true;
 return result;
};
function gapMock(config,fixtures){
 if(config.seed!==1979||config.adopt_ms!==411||config.sample_interval_ms!==1)throw Error('FIXED_CLOCK_SEED');
 const first=frame8Mock(config,fixtures),controls=[PlayerControl.create(1),PlayerControl.create(2)];
 if(controls[0]===controls[1])throw Error('SHARED_CONTROL');
 const cases=['initial_no_completed_cp','engine_fault','late','judge_error','automation_abort'].map(c=>({classification:c,A:gameFailureResult(c,1,'candidate'),B:gameFailureResult(c,1,'reference')}));
 const unknown=gameFailureResult('engine_fault',1,'reference',{error:'UNKNOWN_SHARED_FAULT'});
 if(unknown.status!=='unfinished'||unknown.winner!==null)throw Error('SHARED_FAULT_PRIORITY');
 return {first,cases,unknown,seed:1979,NN:0,controls_distinct:true,SAB_sessions_actual_binding:'checked in runtime setup/load; mock not actual session proof',no_game:true};
}
const gapValidate=validateAfterProgression;
validateAfterProgression=async function(){
 await gapValidate();
 for(const row of collectedRows){
  if(row.identity.limits.seed!==1979||row.diagnostic?.identity?.limits?.seed!==1979)throw Error('REAL_REQUEST_RECEIPT_SEED');
  row.firstCP=row.diagnostic.sab_publications?.[0]??null;
  row.adoptedCP=row.diagnostic.sab_publications?.find(x=>x.sequence===row.response.body.sequence)??null;
  if(row.diagnostic.sab_publications?.some(x=>x.actual_owned_seed!==1979))throw Error('ACTUAL_OWNED_SEED');
  const cp=row.diagnostic.validated_cp;
  if(cp){row.completed_backup_convention={root_visits:cp.root_visits,raw_simulations:cp.simulations,edge_visits:cp.root_edges?.reduce((n,e)=>n+e[2],0),completed_backup:row.spec.engine==='reference'?cp.root_visits:cp.simulations,NN_not_backup:true};}
  row.completed_without_NN={count:cp?Math.max(0,row.completed_backup_convention.completed_backup-cp.nn_calls):null,basis:'adoptable last validated CP completed backup minus its cp.nn_calls; excludes pending/retired API; candidate cap pseudo-leaf not isolated',terminal_noNN_direct_count:null,terminal_count_missing:true};
 }
};

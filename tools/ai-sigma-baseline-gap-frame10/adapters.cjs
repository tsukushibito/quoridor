"use strict";
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const base=require('../ai-sigma-cpu-sigma-frame8/adapters.cjs');
const ROOT=path.resolve(__dirname,'../..');
function change(s,a,b,n=1){if(s.split(a).length-1!==n)throw Error('GAP_ADAPTER_COUNT '+a);return s.split(a).join(b);}
function script(name){
 if(name==='reference')return fs.readFileSync(ROOT+'/tools/ai-sigma-actual-boundary-repair/reference-core.js','utf8');
 let s=base.script(name);
 if(name==='producer')s=change(s,'![1979,2098].includes(id.limits.seed)','id.limits.seed!==1979');
 if(name==='worker')s=change(s,'publications.push({ sequence: message.sequence, action: cp.action, begin_ms: begin, validation_end_ms: workerNow() });','publications.push({ sequence: message.sequence, action: cp.action, begin_ms: begin, validation_end_ms: workerNow(), raw_simulations:cp.simulations, root_visits:cp.root_visits??null, completed_backup:boundEngine===\'reference\'?cp.root_visits:cp.simulations, completed_NN:cp.nn_calls, depth:cp.max_depth??null, cap:cp.cap??null, actual_owned_seed:message.owned.identity.seed });');
 if(name==='main'){
  s=change(s,'collectedGames.push(game);startedGames++;','game.start_ms=epochMain();collectedGames.push(game);startedGames++;');
  s=change(s,"game.final_key=state._positionKey();game.total_ply=state.depth;","game.final_key=state._positionKey();game.total_ply=state.depth;game.end_ms=epochMain();");
  s=change(s,'return collectBrowser();','return gapCollectForSave();');
  s=change(s,'let state=referenceState(fixture);','let state=diversePrefixState(fixture);');
  s=change(s,"await settlePlayerSearches();\n    if(game.status==='unfinished')break;","await settlePlayerSearches();\n    await validateAfterProgression();\n    if(typeof window.saveFinishedGame!==\'function\')throw Error(\'POSTGAME_SAVE_ENTRY_MISSING\');\n    await window.saveFinishedGame({game,rows:collectedRows.filter(r=>r.spec.game_id===game.id)});\n    if(game.status==='unfinished')break;");
  // Restore histories through actual legal actions; classify shared faults before engine loss.
  s=change(s,"if(!diagnostic?.numeric?.length)throw Error('ROOT_NUMERIC_MISSING');\n    row.gate=BrowserNumeric.check({engine:row.spec.engine,state,numeric:diagnostic.numeric[0],cp:diagnostic.validated_cp,reference});","if(!diagnostic?.numeric?.length){row.gate={missing:'ROOT_NUMERIC_MISSING',typed_classification:row.response.classification};if(row.response.classification==='completed_legal')throw Error('ROOT_NUMERIC_MISSING');}else row.gate=BrowserNumeric.check({engine:row.spec.engine,state,numeric:diagnostic.numeric[0],cp:diagnostic.validated_cp,reference});");
  s+='\n'+fs.readFileSync(__dirname+'/input.js','utf8')+'\n'+fs.readFileSync(__dirname+'/main.js','utf8');
 }
 return s;
}
function bindings(){const r=base.bindings();for(const n of Object.keys(r))r[n].adapted_SHA256=crypto.createHash('sha256').update(script(n)).digest('hex');
 r.reference={path:'tools/ai-sigma-actual-boundary-repair/reference-core.js',SHA256:crypto.createHash('sha256').update(script('reference')).digest('hex'),unchanged:true};
 r.local=Object.fromEntries(['input.js','main.js','adapters.cjs'].map(n=>[n,crypto.createHash('sha256').update(fs.readFileSync(__dirname+'/'+n)).digest('hex')]));return r;}
module.exports={script,bindings};

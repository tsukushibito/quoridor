'use strict';
function sameSet(a, b) {
  return JSON.stringify(a.map(x=>JSON.stringify(x)).sort()) === JSON.stringify(b.map(x=>JSON.stringify(x)).sort());
}
function tacticalState(input) {
  const state = fromPrefix(input.legal_prefix);
  if (terminalResult(state) || state._positionKey() !== input.key || state.depth !== input.depth || state.getCurrentPlayer() !== input.player) throw Error('TACTICAL_CONTEXT');
  if (JSON.stringify([...state.position_history]) !== JSON.stringify(input.history)) throw Error('TACTICAL_HISTORY');
  if (JSON.stringify([state.player1pos,state.player2pos]) !== JSON.stringify(input.pawns) || JSON.stringify([state.walls_p1,state.walls_p2]) !== JSON.stringify(input.walls_remaining)) throw Error('TACTICAL_BOARD');
  if (!sameSet([...state.hwall_anchors],input.H) || !sameSet([...state.vwall_anchors],input.V)) throw Error('TACTICAL_WALLS');
  return state;
}
function tacticalPreflight(document) {
  if (document.issue !== 'quoridor-4lc.127' || document.inputs.length !== 4 || document.labels.length !== 4) throw Error('LABEL_DOCUMENT');
  const results = [];
  for (const input of document.inputs) {
    const state = tacticalState(input);
    const saved = document.labels.find(x=>x.case===input.case)?.certificate;
    if (!saved) throw Error('MISSING_CERTIFICATE');
    const observed = certify(state,20000);
    if (JSON.stringify(observed) !== JSON.stringify(saved)) throw Error('LABEL_CERTIFICATE_DIFFERENCE');
    if (!sameSet(state.getLegalActions(),saved.root_legal) || !saved.immediate_wins_complete) throw Error('LABEL_LEGAL_INCOMPLETE');
    if (['own-near-goal','both-near'].includes(input.case)) {
      if (!saved.immediate_wins.length) throw Error('LABEL_IMMEDIATE_EMPTY');
    } else if (!saved.next_ply_labels_complete) throw Error('LABEL_DEFENCE_INCOMPLETE');
    if (input.case==='opponent-threat' && !sameSet(saved.next_ply_loss_avoid,[{type:'wall',x:3,y:0,orientation:'h'},{type:'wall',x:4,y:0,orientation:'h'}])) throw Error('LABEL_DEFENCE_CHANGED');
    if (input.case==='wall-protected-threat' && !sameSet(saved.next_ply_loss_avoid,saved.root_legal)) throw Error('LABEL_NEGATIVE_CONTROL');
    results.push({case:input.case,player:input.player,key:input.key,history_exact:true,legal_count:saved.root_legal_count,label_exact:true,nodes:saved.nodes,terminal:false});
  }
  return {cases:results,NN:0,model_load:0,sharedRuleA_not_independent:true};
}
function tacticalLabel(input, certificate, row) {
  if (row.response.classification !== 'completed_legal') return {classification:row.response.classification,label_verdict:null,causes:row.response.causes};
  const action = row.response.body.action;
  let accepted;
  if (['own-near-goal','both-near'].includes(input.case)) {
    if (!certificate.immediate_wins_complete || !certificate.immediate_wins.length) throw Error('UNAVAILABLE_WIN_LABEL');
    accepted = certificate.immediate_wins;
  } else {
    if (!certificate.next_ply_labels_complete) throw Error('UNAVAILABLE_DEFENCE_LABEL');
    accepted = certificate.next_ply_loss_avoid;
  }
  const pass = accepted.some(a=>sameAction(a,action));
  return {classification:pass?'pass':'certified_legal_blunder',label_verdict:pass,action:structuredClone(action),label_scope:input.case==='wall-protected-threat'?'all-legal negative control':'finite immediate/next-ply goal label',immediate_goal:terminalResult(fromPrefix(input.legal_prefix).next(action))?.winner===input.player};
}
async function runTacticalEvaluation(config, document) {
  const errors = [], verdicts = [];
  let started = 0;
  async function timedRequirement(task) {
    let timer;
    const timeout = new Promise((resolve,reject)=>{timer=setTimeout(()=>{browserAbort({code:'REQUIREMENT_TIMEOUT',scope:'infra/owned recovery'});reject(Error('REQUIREMENT_TIMEOUT'));},config.requirement_timeout_ms);pendingTimers.add(timer);});
    try {return await Promise.race([task(),timeout]);}
    finally {clearTimeout(timer);pendingTimers.delete(timer);}
  }
  for (const planned of config.requirements) {
    if (planned.condition==='S' && verdicts.filter(x=>x.condition!=='S').length!==8) break;
    if (planned.condition==='S' && collectedRows.slice(0,8).some(r=>r.response.classification!=='completed_legal'||!r.gate)) break;
    try {
      await timedRequirement(async()=>{
        await settlePlayerSearches();
        if (planned.condition==='S' && planned.engine!=='candidate') throw Error('STRESS_ENGINE_BINDING');
        const input = document.inputs.find(x=>x.case===planned.case);
        const certificate = document.labels.find(x=>x.case===planned.case)?.certificate;
        if (!input || !certificate) throw Error('LABEL_INPUT_MISSING');
        const state = tacticalState(input);
        started++;
        const {row} = await chooseBrowser({...planned,cancel:false},state,input.legal_prefix,null,config);
        await settlePlayerSearches();
        await validateAfterProgression();
        const cp = row.diagnostic?.validated_cp;
        const adopted = row.response.adopt_checkpoint;
        const publications = row.diagnostic?.sab_publications ?? [];
        const matching = !!cp && !!adopted && row.response.body.sequence===adopted.sequence && publications.at(-1)?.sequence===adopted.sequence;
        row.adopted_stats = matching ? {completed_backup:planned.engine==='candidate'?cp.simulations:cp.simulations+1,simulations:cp.simulations,rootN:planned.engine==='candidate'?cp.simulations:cp.root_visits,rootN_origin:planned.engine==='candidate'?'source convention sim, not direct tree':'raw root_visits',edge_sum:cp.root_edges.reduce((n,e)=>n+e[2],0),cp_NN_calls:cp.nn_calls,terminal_noNN_backup:(planned.engine==='candidate'?cp.simulations:cp.simulations+1)-cp.nn_calls,sequence:adopted.sequence,exactAtomicstore_missing:true} : null;
        if (!matching && row.response.body.completed) throw Error('ADOPTED_STATS_BINDING');
        if (planned.condition==='S' && (!matching || cp.simulations!==1 || cp.nn_calls!==1 || row.hand_NN!==1 || publications.length!==1 || row.diagnostic.NN_control_events.some(x=>x.result_discarded))) throw Error('STRESS_ROOT_ONE_NOT_ESTABLISHED');
        const verdict = tacticalLabel(input,certificate,row);
        row.tactical_verdict = {...verdict,case:planned.case,condition:planned.condition,request_id:row.identity.request_id};
        verdicts.push(row.tactical_verdict);
      });
    } catch (error) {
      errors.push({planned,name:error.name,message:error.message,stack:error.stack});break;
    }
  }
  const result = collectBrowser();
  const root_pairs = [];
  for (const input of document.inputs) {
    const a = result.rows.find(r=>r.spec.case===input.case&&r.spec.condition==='A');
    const b = result.rows.find(r=>r.spec.case===input.case&&r.spec.condition==='B');
    if (!a?.diagnostic?.numeric?.[0] || !b?.diagnostic?.numeric?.[0]) {root_pairs.push({case:input.case,missing:true});continue;}
    const x=a.diagnostic.numeric[0],y=b.diagnostic.numeric[0];
    if (JSON.stringify(x.features_bits)!==JSON.stringify(y.features_bits)) throw Error('ROOT_INPUT_DIFFERENCE');
    const logits=x.policy_logits??x.logits,other=y.policy_logits??y.logits;
    const maximum=Math.max(...logits.map((v,i)=>Math.abs(v-other[i])),Math.abs(x.value-y.value));
    const mixed=logits.every((v,i)=>Math.abs(v-other[i])<=1e-4+1e-4*Math.abs(other[i]))&&Math.abs(x.value-y.value)<=1e-4+1e-4*Math.abs(y.value);
    if(!mixed)throw Error('ROOT_NN_MIXED');
    root_pairs.push({case:input.case,features648_exact:true,NN137_mixed:true,max_abs:maximum,fixed_NN_reference:false,engine_gates:[a.gate,b.gate]});
  }
  return {...result,started,errors,verdicts,root_pairs,completed:result.rows.length,planned:config.requirements.length,games:[]};
}

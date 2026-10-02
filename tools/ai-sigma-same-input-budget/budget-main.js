'use strict';
async function runSameInputBudget(config, fixtures) {
  const errors = [];
  let started = 0;
  for (const planned of config.requirements) {
    try {
      await settlePlayerSearches();
      const fixture = fixtures.find(row => row.id === planned.fixture_id);
      if (!fixture) throw Error('INPUT_MISSING');
      const state = diversePrefixState(fixture);
      started++;
      const {row} = await chooseBrowser({...planned, cancel:false}, state, fixture.legal_prefix, null, config);
      await settlePlayerSearches();
      await validateAfterProgression(); // Details are requested only after adoption and owned zero.
      const cp = row.diagnostic?.validated_cp;
      const adopted = row.response.adopt_checkpoint;
      const publication = row.diagnostic?.sab_publications?.find(p => p.sequence === adopted?.sequence);
      const matching = !!cp && !!adopted && row.response.body.sequence === adopted.sequence && publication?.sequence === row.diagnostic.sab_publications.at(-1)?.sequence;
      row.adopted_stats = matching ? {
        completed_backup:planned.engine === 'candidate' ? cp.simulations : cp.simulations+1,
        rootN:planned.engine === 'candidate' ? cp.simulations : cp.root_visits,
        simulations:cp.simulations, edge_sum:cp.root_edges.reduce((n,e)=>n+e[2],0),
        cp_NN_calls:cp.nn_calls, adopted_SAB_visits:adopted.visits, sequence:adopted.sequence,
        terminal_noNN_backup:cp.terminal_value === null ? 0 : null,
        exact_atomic_store_time_missing:true, cp_sequence_bound_to_adoption:true
      } : null;
      row.root_sample_selected = planned.phase === 'steady' && planned.engine_repetition === 1;
      if (!matching && row.response.body.completed) throw Error('ADOPTED_CP_STATS_BINDING');
    } catch (error) {
      errors.push({planned, name:error.name, message:error.message, stack:error.stack});
      break;
    }
  }
  const result = collectBrowser();
  const root_pairs = [];
  for (const id of config.input_order) {
    const rows = result.rows.filter(r=>r.spec.fixture_id===id && r.root_sample_selected);
    const a = rows.find(r=>r.spec.engine==='candidate');
    const b = rows.find(r=>r.spec.engine==='reference');
    if (!a || !b) {root_pairs.push({fixture_id:id,missing:true});continue;}
    const x = a.diagnostic.numeric[0], y = b.diagnostic.numeric[0];
    if (JSON.stringify(x.features_bits)!==JSON.stringify(y.features_bits))throw Error('ROOT_INPUT_DIFFERENCE');
    const logits = x.policy_logits ?? x.logits, other = y.policy_logits ?? y.logits;
    const max_abs = Math.max(...logits.map((v,i)=>Math.abs(v-other[i])),Math.abs(x.value-y.value));
    const mixed = logits.every((v,i)=>Math.abs(v-other[i])<=1e-4+1e-4*Math.abs(other[i])) && Math.abs(x.value-y.value)<=1e-4+1e-4*Math.abs(y.value);
    if (!mixed) throw Error('ROOT_NN_MIXED');
    root_pairs.push({fixture_id:id,features648_exact:true,NN137_mixed:true,max_abs,fixed_reference:false,engine_prior_gates:[a.gate,b.gate]});
  }
  return {...result, started, errors, root_pairs, completed:result.rows.length, planned:config.requirements.length, games:[]};
}

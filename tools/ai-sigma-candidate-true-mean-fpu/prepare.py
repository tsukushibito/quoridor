from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parents[2];T=Path(__file__).parent;D=R/'research-data/ai-sigma/140-candidate-true-mean-fpu';O=R/'.artifacts/ai-sigma/resume-20261002/CANDIDATE-TRUE-MEAN-FPU'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
base=R/'tools/ai-sigma-deep-node-comparison/baseline';P=T/'private';(P/'src').mkdir(parents=True,exist_ok=True)
for n in ['kernel.rs','lib.rs','research.rs']:(P/'src'/n).write_bytes((base/'src'/n).read_bytes())
(P/'Cargo.toml').write_text((base/'Cargo.toml').read_text().replace('research=[]','research=[]\ntrue-mean-fpu=[]'))
(P/'Cargo.lock').write_bytes((base/'Cargo.lock').read_bytes())
s=(P/'src/kernel.rs').read_text()
s=s.replace('    expanded: bool,\n    visits: u32,','    expanded: bool,\n    visits: u32,\n    true_value_sum: f32,')
s=s.replace('            expanded: false,\n            visits: 0,','            expanded: false,\n            visits: 0,\n            true_value_sum: 0.0,')
s=s.replace('    stats: SearchStats,','    stats: SearchStats,\n    pub(crate) select_trace: Vec<serde_json::Value>,\n    pub(crate) visit_trace: Vec<serde_json::Value>,\n    pub(crate) deep_trace: Vec<serde_json::Value>,')
s=s.replace('            seed,\n            #[cfg','            seed,\n            select_trace: Vec::new(),\n            visit_trace: Vec::new(),\n            deep_trace: Vec::new(),\n            #[cfg')
s=s.replace('self.nodes[index].visits += 1;','self.visit_node(index, value);').replace('self.nodes[parent].visits += 1;','self.visit_node(parent, value);')
s=s.replace('s.nodes[index].visits += 1','s.visit_node(index, value);').replace('s.nodes[parent].visits += 1;','s.visit_node(parent, value);')
s=s.replace('fn select(&self, index: usize)', 'fn select(&mut self, index: usize)')
s=s.replace('        let root = (node.visits as f32 + 1.0).sqrt();','''        let root = (node.visits as f32 + 1.0).sqrt();
        let true_mean = if node.visits == 0 {None} else {Some(node.true_value_sum / node.visits as f32)};
        let visited_prior: f32 = node.edges.iter().filter(|e| e.visits > 0).map(|e| e.prior).sum();
        // Zero visits has no mean. Normal expanded selection follows one completed backup;
        // artificial N0 uses Q0 without a division, and explicitly records mean absent.
        let fpu = true_mean.map(|q| q - 0.2_f32 * visited_prior.sqrt());
        let unvisited_q = if cfg!(feature="true-mean-fpu") {fpu.unwrap_or(0.0)} else {0.0};''')
s=s.replace('let q = if edge.visits == 0 {\n                0.0','let q = if edge.visits == 0 {\n                unvisited_q')
s=s.replace('        best\n    }\n}', '''        let chosen = &node.edges[best];
        assert!(self.select_trace.len() < 4096 * 24, "select trace hard cap");
        self.select_trace.push(serde_json::json!({"sim_completed_before":self.stats.simulations,
            "node_index":index,"nodeN":node.visits,"node_value_sum":node.true_value_sum,
            "true_mean":true_mean,"visited_original_prior_sum":visited_prior,"fpu":fpu,
            "FPU_enabled":cfg!(feature="true-mean-fpu"),"Action":chosen.action,"visited":chosen.visits>0,
            "edge_visits":chosen.visits,"edge_value_sum":chosen.value_sum,"prior":chosen.prior,
            "actual_q":if chosen.visits==0 {unvisited_q} else {chosen.value_sum/chosen.visits as f32},
            "actual_score":best_score,"N0_mean_missing":true_mean.is_none()}));
        best
    }
    fn visit_node(&mut self, index:usize, value:f32) {
        let n=&mut self.nodes[index];let preN=n.visits;let preSum=n.true_value_sum;
        n.visits+=1;n.true_value_sum+=value;
        assert!(self.visit_trace.len()<4096*25, "visit trace hard cap");
        self.visit_trace.push(serde_json::json!({"sim_completed_before":self.stats.simulations,
            "node_index":index,"turn":n.position.turn,"value_own_side":value,
            "preN":preN,"postN":n.visits,"preSum":preSum,"postSum":n.true_value_sum}));
    }
}''',1)
# First root +7 unique actual completed leaves with actual context and pre/post path.
s=s.replace('Self::backup(s, index, path, leaf_is_node, value);','Self::backup(s, index, path, leaf_is_node, value, &cursor);')
s=s.replace('Self::backup(&mut self.search, c.index, c.path, c.leaf_is_node, value);','Self::backup(&mut self.search, c.index, c.path, c.leaf_is_node, value, &c.request.context);')
s=s.replace('        mut value: f32,\n    ) {\n        s.stats.max_depth_reached', '''        mut value: f32,
        cursor: &RuleCursor,
    ) {
        let selected=leaf_is_node && s.deep_trace.len()<8 && !s.deep_trace.iter().any(|v|v["node_index"].as_u64()==Some(index as u64));
        let pre=if selected {Some(serde_json::json!({"leaf_visits":s.nodes[index].visits,"leaf_true_sum":s.nodes[index].true_value_sum,
            "path":path.iter().map(|&(p,e)|{let edge=&s.nodes[p].edges[e];serde_json::json!({"parent_index":p,"Action":edge.action,"parent_visits":s.nodes[p].visits,"parent_true_sum":s.nodes[p].true_value_sum,"edge_visits":edge.visits,"edge_value_sum":edge.value_sum})}).collect::<Vec<_>>()}))}else{None};
        let trace_path=if selected {path.clone()} else {Vec::new()};let leaf_value=value;
        s.stats.max_depth_reached''')
pos=s.index('    pub fn checkpoint(&mut self, g: u32)');x=s[:pos];end=x.rfind('    }')
x=x[:end]+'''        if let Some(pre)=pre {
            let ctx=cursor.as_ref().expect("actual research context");let p=ctx.position();
            s.deep_trace.push(serde_json::json!({"node_index":index,"key":quoridor_core::research::HistoryKey::from(p).sigma_string(),"turn":p.turn,
                "ply":ctx.total_ply(),"history":ctx.history_counts().iter().map(|(k,n)|(k.sigma_string(),*n)).collect::<Vec<_>>(),
                "features_bits":quoridor_core::research::features(p).map(f32::to_bits).to_vec(),"terminal":ctx.terminal_value(),"winner":p.winner,
                "leaf_side_value":leaf_value,"pre":pre,"post_leaf_visits":s.nodes[index].visits,"post_leaf_true_sum":s.nodes[index].true_value_sum,
                "post_path":trace_path.iter().map(|&(p,e)|{let edge=&s.nodes[p].edges[e];serde_json::json!({"parent_index":p,"Action":edge.action,"parent_visits":s.nodes[p].visits,"parent_true_sum":s.nodes[p].true_value_sum,"edge_visits":edge.visits,"edge_value_sum":edge.value_sum})}).collect::<Vec<_>>()}));
        }
'''+x[end:];s=x+s[pos:];(P/'src/kernel.rs').write_text(s)
s=(P/'src/research.rs').read_text().replace('    pub visits: u32,','    pub visits: u32,\n    pub true_value_sum: f32,').replace('                visits: n.visits,','                visits: n.visits,\n                true_value_sum:n.true_value_sum,');(P/'src/research.rs').write_text(s)
s=(P/'src/lib.rs').read_text().replace('"visits":n.visits','"visits":n.visits,"true_value_sum":n.true_value_sum')
s=s.replace('        "begin" => match s.begin(g)? {','        "mean_trace" => Ok(json!({"selections":s.search.select_trace,"visits":s.search.visit_trace,"nodes":s.search.deep_trace,"FPU_enabled":cfg!(feature="true-mean-fpu")})),\n        "begin" => match s.begin(g)? {');(P/'src/lib.rs').write_text(s)
fixed=R/'research-data/ai-sigma/132-deep-node-comparison/fixed-inputs.json';assert sha(fixed)=='fffc171a2b2fc5f36cab950299e651912fa95287ee0e6121bebb35d18bf56b01'
fixtures=json.loads(fixed.read_text())['fixtures'][2:];(D/'fixed-inputs.json').write_text(json.dumps({'fixtures':fixtures},indent=2)+'\n')
intake=json.loads((D/'intake.json').read_text());deadline=intake['processing'];new=intake['newheavy']
# Own configured guardian, preserving sole-root kernel/ledger logic and readonly imports.
s=(R/'tools/ai-sigma-fixed-policy-cost/runner.py').read_text().replace('FIXED-POLICY-COST','CANDIDATE-TRUE-MEAN-FPU').replace('cost137-','fpu140-').replace('quoridor-4lc.137','quoridor-4lc.140').replace('137-fixed-policy-cost','140-candidate-true-mean-fpu').replace('FRAME137','FRAME140')
s=s.replace("['cost','protocol']","['mechanism','quality','build','protocol']")
s=s.replace('RSS_GUARD=939524096 if CPU==0 else 5905580032','RSS_GUARD=3758096384 if PHASE==\'build\' else 939524096 if CPU==0 else 5905580032')
s=s.replace('STORAGE_GUARD=58720256','STORAGE_GUARD=234881024').replace('CONTRACT_RAM=1073741824 if CPU==0 else 6442450944','CONTRACT_RAM=4294967296 if PHASE==\'build\' else 1073741824 if CPU==0 else 6442450944')
s=s.replace('MAX_WALL=60 if CPU==0 else 90','MAX_WALL=120 if PHASE in [\'build\',\'mechanism\'] else 60 if CPU==0 else 180').replace('TOTAL_WALL=180 if CPU==0 else 180','TOTAL_WALL={\'build\':300,\'mechanism\':180,\'quality\':1440,\'protocol\':180}[PHASE]')
s=s.replace("if d.get('phase')==PHASE or (PHASE not in ['build','protocol'] and d.get('phase') not in ['build','protocol']):","if d.get('phase')==PHASE:")
s=s.replace("   if PHASE!='build' and Path(directory).is_relative_to(OUT.parent/'build'):continue\n",'')
# CPU sampling retained resource safety but detailed TID cost samples not relevant/newcpuclaim.
s=s.replace('  sample_threads(members)','  # TID affinity safety remains; no detailed CPU inference attribution.')
(T/'runner.py').write_text(s)
(T/'commit-own.sh').write_text((R/'tools/ai-sigma-fixed-policy-cost/commit-own.sh').read_text().replace('FIXED-POLICY-COST','CANDIDATE-TRUE-MEAN-FPU'))
stop=R/'research-data/ai-sigma/137-fixed-policy-cost/runtime-source-stopped-before-report.json';assert sha(stop)=='79ea43cea782575b004b37561f04267448f375a34b030fbc094362162def240d'
baseconfig={'issue':'quoridor-4lc.140','frame':9,'seed':1979,'processing_deadline':deadline,'newjob_deadline':new,'pin_owned_TIDs':True,'dependency_stop':str(stop),'dependency_stop_SHA256':sha(stop)}
for variant in ['q0','fpu']:
 c={**baseconfig,'kind':'build','run_id':'fpu140-build-'+variant,'variant':variant,'forecast_bytes':80*1024**2,'minimum_remaining_heavy_seconds':30};(D/f'build-{variant}-config.json').write_text(json.dumps(c,indent=2)+'\n')
plans=[{'fixture_id':fixtures[i]['id'],'variant':v,'K':32} for i,vs in enumerate([['original','q0','fpu'],['fpu','q0','original']]) for v in vs]
c={**baseconfig,'kind':'mechanism','run_id':'fpu140-mechanism-r1','forecast_bytes':16*1024**2,'minimum_remaining_heavy_seconds':60,'count_timeout_ms':10000,'searches':plans,'fixed_input_path':str(D/'fixed-inputs.json')};(D/'config.json').write_text(json.dumps(c,indent=2)+'\n')
(D/'source-input-binding.json').write_text(json.dumps({'contract_Git':'78a93bb3f4f81bd5c57420c62058a20fa84dd444','original_binary':{'path':'.artifacts/ai-sigma/runs/SIGMA-ORT-SEARCH/final.wasm','SHA256':sha(R/'.artifacts/ai-sigma/runs/SIGMA-ORT-SEARCH/final.wasm')},'baseline_source':{str(p.relative_to(R)):sha(p) for p in base.rglob('*') if p.is_file()},'original_build_binding':{'path':'research-data/ai-sigma/132-deep-node-comparison/build-binding.json','SHA256':sha(R/'research-data/ai-sigma/132-deep-node-comparison/build-binding.json'),'past_bytes_equal_not_new_rebuild':True},'fixed_input_source':{'path':str(fixed.relative_to(R)),'SHA256':sha(fixed)},'selected_input_SHA256':sha(D/'fixed-inputs.json'),'new_private':{str(p.relative_to(R)):sha(p) for p in P.rglob('*') if p.is_file()},'139_proposal_SHA256':sha(R/'research-data/ai-sigma/139-next-information-choice/next-experiment-v1.json')},indent=2)+'\n')
print('private source and fixed plans prepared')

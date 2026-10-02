"""Private, bounded read-only backup recorder; search formulas stay unchanged."""
from pathlib import Path
T=Path(__file__).parent
p=T/'trace/src/kernel.rs';s=p.read_text()
s=s.replace('    stats: SearchStats,','    stats: SearchStats,\n    pub(crate) deep_trace: Vec<serde_json::Value>,')
s=s.replace('            seed,\n            #[cfg','            seed,\n            deep_trace: Vec::new(),\n            #[cfg')
s=s.replace('Self::backup(s, index, path, leaf_is_node, value);','Self::backup(s, index, path, leaf_is_node, value, &cursor);')
s=s.replace('Self::backup(&mut self.search, c.index, c.path, c.leaf_is_node, value);','Self::backup(&mut self.search, c.index, c.path, c.leaf_is_node, value, &c.request.context);')
s=s.replace('        mut value: f32,\n    ) {\n        s.stats.max_depth_reached', '''        mut value: f32,
        cursor: &RuleCursor,
    ) {
        let selected = leaf_is_node && s.deep_trace.len() < 8
            && !s.deep_trace.iter().any(|v| v["node_index"].as_u64() == Some(index as u64));
        let before = if selected {
            Some(serde_json::json!({
                "node_index":index,"leaf_visits":s.nodes[index].visits,
                "path":path.iter().map(|&(p,e)| {let edge=&s.nodes[p].edges[e];
                    serde_json::json!({"parent_index":p,"child_index":edge.child,"action":edge.action,
                        "parent_visits":s.nodes[p].visits,"edge_visits":edge.visits,"edge_value_sum":edge.value_sum})
                }).collect::<Vec<_>>()
            }))
        } else {None};
        let leaf_value = value;
        let trace_path = if selected {path.clone()} else {Vec::new()};
        s.stats.max_depth_reached''')
needle='''    pub fn checkpoint(&mut self, g: u32)'''
pos=s.index(needle);before=s[:pos]
end=before.rfind('    }')
before=before[:end]+'''        if let Some(pre) = before {
            let ctx = cursor.as_ref().expect("trace research context");
            let position = ctx.position();
            s.deep_trace.push(serde_json::json!({
                "node_index":index,"key":quoridor_core::research::HistoryKey::from(position).sigma_string(),
                "ply":ctx.total_ply(),"history":ctx.history_counts().iter().map(|(k,n)|(k.sigma_string(),*n)).collect::<Vec<_>>(),
                "features_bits":quoridor_core::research::features(position).map(f32::to_bits).to_vec(),
                "turn":position.turn,"terminal":ctx.terminal_value(),"winner":position.winner,
                "leaf_side_value":leaf_value,"pre":pre,"post_leaf_visits":s.nodes[index].visits,
                "post_path":trace_path.iter().map(|&(p,e)| {let edge=&s.nodes[p].edges[e];
                    serde_json::json!({"parent_index":p,"child_index":edge.child,"action":edge.action,
                        "parent_visits":s.nodes[p].visits,"edge_visits":edge.visits,"edge_value_sum":edge.value_sum})
                }).collect::<Vec<_>>(),"parentQ_missing":true,"node_valueSum_missing":true
            }));
        }
'''+before[end:]
s=before+s[pos:];p.write_text(s)
p=T/'trace/src/lib.rs';s=p.read_text().replace('        "begin" => match s.begin(g)? {','        "trace" => Ok(serde_json::json!({"nodes":s.search.deep_trace})),\n        "begin" => match s.begin(g)? {');p.write_text(s)

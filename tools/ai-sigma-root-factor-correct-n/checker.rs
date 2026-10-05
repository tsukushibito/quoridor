use std::{fs,env,collections::HashSet};
#[derive(Clone)] struct Edge { action:u16, prior:f32, visits:u32, value_sum:f32, rank:u32 }
#[derive(Clone)] struct Root { id:String, seed:u64, expected:u16, edge_sum:u32, n:u32, edges:Vec<Edge> }
fn tie(seed:u64,action:u16)->u64 { let mut x=seed^action as u64;x=(x^(x>>30)).wrapping_mul(0xbf58_476d_1ce4_e5b9);x=(x^(x>>27)).wrapping_mul(0x94d0_49bb_1331_11eb);x^(x>>31) }
fn finish(r:&Root)->u16 { r.edges.iter().max_by(|a,b|a.visits.cmp(&b.visits).then_with(||a.prior.total_cmp(&b.prior)).then_with(||tie(r.seed,b.action).cmp(&tie(r.seed,a.action)))).unwrap().action }
fn validate(r:&Root)->Result<(), &'static str> {
 if r.edges.is_empty()||r.edges.len()>209{return Err("edge_count");}
 if r.n!=r.edge_sum.checked_add(1).ok_or("sum_overflow")?{return Err("node_visits_independent");}
 if r.seed!=1979{return Err("seed");}
 let mut acts=HashSet::new();let mut ranks=HashSet::new();let mut sum=0u32;
 for e in &r.edges {if e.action>208||!acts.insert(e.action){return Err("action");}if e.rank>=r.edges.len() as u32||!ranks.insert(e.rank){return Err("enumeration_rank");}if !e.prior.is_finite()||e.prior<0.0||e.prior>1.0||!e.value_sum.is_finite(){return Err("finite_or_prior");}if e.visits==0&&e.value_sum!=0.0{return Err("unvisited_sum");}sum=sum.checked_add(e.visits).ok_or("sum_overflow")?;}
 if sum!=r.edge_sum{return Err("edge_sum_independent");}if !acts.contains(&r.expected){return Err("expected_action");}Ok(())
}
struct Choice {action:u16,score:f32,margin:Option<f32>,ties:usize,near:usize,visits:u32,all:Vec<u32>}
fn select(r:&Root,c:f32,plus:bool,first:bool,ref_order:bool)->Choice {
 let root=(r.n as f32+if plus{1.0}else{0.0}).sqrt();let mut es:Vec<&Edge>=r.edges.iter().collect();if ref_order{es.sort_by_key(|e|e.rank)}
 let mut scores=Vec::new();let mut best=0usize;let mut best_score=f32::NEG_INFINITY;
 for(i,e) in es.iter().enumerate(){let q=if e.visits==0{0.0}else{e.value_sum/e.visits as f32};let score=q+c*e.prior*root/(e.visits+1)as f32;assert!(score.is_finite());scores.push(score);if score>best_score||(score==best_score&&!first&&tie(r.seed,e.action)<tie(r.seed,es[best].action)){best=i;best_score=score;}}
 let second=scores.iter().enumerate().filter(|(i,_)|*i!=best).map(|(_,x)|*x).fold(f32::NEG_INFINITY,f32::max);
 Choice {action:es[best].action,score:best_score,margin:if es.len()>1{Some(best_score-second)}else{None},ties:scores.iter().filter(|x|**x==best_score).count(),near:scores.iter().filter(|x|(best_score-**x).abs()<=1e-6).count(),visits:es[best].visits,all:scores.iter().map(|x|x.to_bits()).collect()}
}
fn boundary(){let r=Root{id:"singleton".into(),seed:1979,expected:10,edge_sum:0,n:1,edges:vec![Edge{action:10,prior:1.0,visits:0,value_sum:0.0,rank:0}]};assert!(validate(&r).is_ok());assert_eq!(finish(&r),10);assert!(select(&r,1.5,true,false,false).margin.is_none());let mut bad=r.clone();bad.n=0;assert_eq!(validate(&bad),Err("node_visits_independent"));bad=r.clone();bad.edge_sum=1;bad.n=2;assert_eq!(validate(&bad),Err("edge_sum_independent"));for prior in [-0.1,f32::NAN,f32::INFINITY]{bad=r.clone();bad.edges[0].prior=prior;assert_eq!(validate(&bad),Err("finite_or_prior"));}bad=r.clone();bad.edges[0].value_sum=f32::NAN;assert_eq!(validate(&bad),Err("finite_or_prior"));bad=r.clone();bad.edges.clear();assert_eq!(validate(&bad),Err("edge_count"));bad=r.clone();bad.edges[0].rank=1;assert_eq!(validate(&bad),Err("enumeration_rank"));bad=r.clone();bad.edges[0].action=209;assert_eq!(validate(&bad),Err("action"));bad=r.clone();bad.edges[0].visits=1;bad.edges[0].value_sum=-0.5;bad.edge_sum=1;bad.n=2;assert!(validate(&bad).is_ok());assert_eq!(select(&bad,1.5,true,false,false).action,10);eprintln!("BOUNDARY_OK sum/node separated singleton negativevalue valid negativeprior/NaN/inf/empty/rank/action rejected");}
fn next<T:std::str::FromStr>(t:&mut std::str::SplitWhitespace)->T {t.next().expect("missing_token").parse().ok().expect("typed_token")}
fn main(){let a:Vec<String>=env::args().collect();boundary();if a.get(1).map(|x|x.as_str())==Some("--boundary"){return;}
 let input=fs::read_to_string(&a[1]).unwrap();let mut t=input.split_whitespace();let count:usize=next(&mut t);assert_eq!(count,765,"actual roots only");let mut roots=Vec::new();let mut ids=HashSet::new();
 for _ in 0..count {let id=t.next().unwrap().to_owned();let seed=next(&mut t);let expected=next(&mut t);let edge_sum=next(&mut t);let n=next(&mut t);let len:usize=next(&mut t);let mut edges=Vec::new();for _ in 0..len{edges.push(Edge{action:next(&mut t),prior:f32::from_bits(next(&mut t)),visits:next(&mut t),value_sum:f32::from_bits(next(&mut t)),rank:next(&mut t)});}let r=Root{id,seed,expected,edge_sum,n,edges};assert!(ids.insert(r.id.clone()));validate(&r).unwrap();roots.push(r);}
 assert!(t.next().is_none(),"extra_input");for r in &roots{assert_eq!(finish(r),r.expected,"original_finish_exact_gate {}",r.id);}eprintln!("FINISH_GATE_OK 765/765 original; restored N=sim=edge_sum+1, not direct raw node.visits");
 if a.get(2).map(|x|x.as_str())==Some("--gate"){return;}
 println!("id\tkind\taction\tscore_bits\tmargin_bits\tties\tnear\tchosen_visits\tall_score_bits");
 for r in &roots{for(kind,c,plus,first,order)in [("base",1.5,true,false,false),("C1",1.0,true,false,false),("sqrtN",1.5,false,false,false),("score_first",1.5,true,true,false),("first_reforder",1.5,true,true,true)]{let x=select(r,c,plus,first,order);println!("{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}",r.id,kind,x.action,x.score.to_bits(),x.margin.map(|x|x.to_bits().to_string()).unwrap_or_else(||"null".into()),x.ties,x.near,x.visits,x.all.iter().map(|x|x.to_string()).collect::<Vec<_>>().join(","));}}
}

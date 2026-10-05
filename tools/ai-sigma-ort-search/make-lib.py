from pathlib import Path
old=Path('../ai-sigma-nn-search/src/lib.rs').read_text()
s='''pub mod kernel;
use kernel::{PendingSearch,SearchLimits,Evaluation};
use quoridor_core::{research::{features,p2_permutation,rust_to_sigma,sigma_to_rust,HistoryKey,SigmaContext,DIRECTIONS},Position};
use serde_json::{json,Value};
use std::cell::RefCell;
'''
s+=old[old.index('pub fn policy('):old.index('impl Evaluator for NnEvaluator')]
s+=old[old.index('fn n(v:'):old.index('pub struct Session')]
s+='''
fn snapshot(s:&mut PendingSearch,g:u32)->Result<Value,String>{
 let cp=s.checkpoint(g)?;let st=cp.stats;
 let nodes:Vec<_>=s.search.research_tree_snapshot().iter().map(|n|json!({"index":n.index,"key":HistoryKey::from(n.context.position()).sigma_string(),"ply":n.context.total_ply(),"history":n.context.history_counts().iter().map(|(k,n)|(k.sigma_string(),*n)).collect::<Vec<_>>(),"legal":n.context.legal_ids(),"terminal":n.context.terminal_value(),"expanded":n.expanded,"edges":n.edges.iter().map(|e|(e.0,e.1.to_bits(),e.2,e.3.to_bits())).collect::<Vec<_>>(),"children":n.children,"visits":n.visits})).collect();
 Ok(json!({"action":cp.action,"simulations":st.simulations,"nodes_count":st.nodes,"edges_count":st.edges,"max_depth":st.max_depth_reached,"arena_bytes":st.arena_bytes,"high_water":st.high_water_bytes,"cap":st.budget_exhausted,"policy_fallbacks":st.policy_fallbacks,"value_fallbacks":st.value_fallbacks,"nn_calls":s.calls,"root_edges":s.search.root_edges(),"tree":nodes}))
}
struct Registry{next:u32,bytes:std::collections::BTreeMap<u32,Vec<u8>>,sessions:std::collections::BTreeMap<u32,PendingSearch>}
thread_local!{static REG:RefCell<Registry>=RefCell::new(Registry{next:0,bytes:Default::default(),sessions:Default::default()});}
impl Registry{fn id(&mut self)->u32{self.next=self.next.checked_add(1).unwrap();self.next}fn bytes(&mut self,v:Vec<u8>)->u32{let h=self.id();self.bytes.insert(h,v);h}}
#[no_mangle] pub extern "C" fn ort_buffer(n:usize)->u32{if n>2000000{return 0}REG.with(|r|r.borrow_mut().bytes(vec![0;n]))}
#[no_mangle] pub extern "C" fn ort_ptr(h:u32)->usize{REG.with(|r|r.borrow_mut().bytes.get_mut(&h).map_or(0,|v|v.as_mut_ptr() as usize))}
#[no_mangle] pub extern "C" fn ort_len(h:u32)->usize{REG.with(|r|r.borrow().bytes.get(&h).map_or(0,|v|v.len()))}
#[no_mangle] pub extern "C" fn ort_free(h:u32)->u32{REG.with(|r|{let mut r=r.borrow_mut();(r.bytes.remove(&h).is_some()||r.sessions.remove(&h).is_some()) as u32})}
fn dispatch(r:&mut Registry,v:Value)->Result<Value,String>{
 let g=v["generation"].as_u64().unwrap_or(1) as u32;
 if v["op"]=="raw"{let c=context(&v["fixture"],true)?;let p=c.position();let f=features(p);return Ok(json!({"features_bits":f.map(f32::to_bits).to_vec(),"raw_legal":c.raw_legal_ids(),"effective_legal":c.legal_ids(),"terminal":c.terminal_value(),"turn":p.turn}))}
 if v["op"]=="raw_policy"{let c=context(&v["fixture"],true)?;let logits=logits(&v["logits"])?;let legal=c.raw_legal_ids();let priors=if legal.is_empty(){Vec::new()}else{policy(c.position(),&legal,&logits)?};return Ok(json!({"priors":priors}))}
 if v["op"]=="new"{let c=context(v.get("fixture").unwrap_or(&v),v["diagnostic"]==true)?;let lim=SearchLimits{simulations:v["simulations"].as_u64().unwrap_or(32).try_into().map_err(|_|"LIMIT")?,max_nodes:v["max_nodes"].as_u64().unwrap_or(64).try_into().map_err(|_|"LIMIT")?,max_depth:v["max_depth"].as_u64().unwrap_or(8).try_into().map_err(|_|"LIMIT")?};let s=PendingSearch::new(c,lim,v["seed"].as_u64().unwrap_or(1979),g).map_err(|e|format!("SEARCH:{e:?}"))?;let h=r.id();r.sessions.insert(h,s);return Ok(json!({"handle":h}))}
 let h=v["handle"].as_u64().ok_or("SESSION_HANDLE")? as u32;
 let s=r.sessions.get_mut(&h).ok_or("INVALID_SESSION")?;
 match v["op"].as_str().unwrap_or(""){
 "begin"=>match s.begin(g)?{Some(q)=>{let ft=features(q.position);Ok(json!({"pending":true,"token":q.token,"generation":q.generation,"features_bits":ft.map(f32::to_bits).to_vec(),"legal":q.legal,"turn":q.position.turn,"key":HistoryKey::from(q.position).sigma_string(),"ply":q.context.as_ref().map(|c|c.total_ply()),"history":q.context.as_ref().map(|c|c.history_counts().iter().map(|(k,n)|(k.sigma_string(),*n)).collect::<Vec<_>>())}))},None=>Ok(json!({"pending":false,"done":s.search.done()}))},
 "resume"=>{let result=(||{let log=logits(&v["logits"])?;let value=v["value"].as_f64().ok_or("VALUE")? as f32;if !value.is_finite()||!(-1.0..=1.0).contains(&value){return Err("VALUE_RANGE".into())}let q=s.request().ok_or("NO_PENDING_OR_DUPLICATE")?;let weights=policy(q.position,&q.legal,&log)?;s.resume(g,v["token"].as_u64().ok_or("TOKEN")?,Evaluation{weights,value})?;Ok(json!({"done":s.search.done(),"simulations":s.search.stats().simulations,"nn_calls":s.calls}))})();if result.is_err(){s.cancel()}result},
 "snapshot"|"checkpoint"=>snapshot(s,g),
 "cancel"=>{s.cancel();Ok(json!({"discarded":true}))},
 _=>Err("OPERATION".into())}
}
fn logits(v:&Value)->Result<Vec<f32>,String>{let a=v.as_array().ok_or("LOGITS_SHAPE")?;if a.len()!=136{return Err("LOGITS_SHAPE".into())}a.iter().map(|x|{let f=x.as_f64().ok_or("LOGITS_FINITE")? as f32;if !f.is_finite(){Err("LOGITS_FINITE".into())}else{Ok(f)}}).collect()}
#[no_mangle] pub extern "C" fn ort_call(h:u32)->u32{REG.with(|r|{let mut r=r.borrow_mut();let result=(||{let b=r.bytes.get(&h).ok_or("INVALID_HANDLE")?;let v=serde_json::from_slice(b).map_err(|e|format!("INPUT_JSON:{e}"))?;dispatch(&mut r,v)})();let v=match result{Ok(v)=>json!({"ok":true,"data":v}),Err(e)=>json!({"ok":false,"error":e,"discarded":true})};r.bytes(serde_json::to_vec(&v).unwrap())})}
'''
Path('src/lib.rs').write_text(s)
p=Path('src/kernel.rs');s=p.read_text().replace('self.next_token+=1;','self.next_token=TOKEN.with(|t|{let n=t.get()+1;t.set(n);n});');s=s.replace('    pub fn force_arena_cap','    pub fn request(&self)->Option<Request>{self.pending.as_ref().map(|c|c.request.clone())}\n    pub fn force_arena_cap');s+='\nthread_local!{static TOKEN:std::cell::Cell<u64>=const {std::cell::Cell::new(0)};}\n';p.write_text(s)

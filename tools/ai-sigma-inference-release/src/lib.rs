//! Research owned API. Caller MUST SHA256-check the exact bytes before passing
//! the verified digest. Digest parameter is a host attestation, not Rust hashing.
use tract_onnx::prelude::*;
use std::{io::Cursor,cell::RefCell,collections::BTreeMap};
pub const MODEL_SHA:&str="d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d";
pub const SCHEMA:&str="sigma-full-canonical-8x9x9-136-v1";
type Plan=SimplePlan<TypedFact,Box<dyn TypedOp>,TypedModel>;
#[derive(Debug)]pub struct Error{pub code:u32,pub detail:String}
impl std::fmt::Display for Error{fn fmt(&self,f:&mut std::fmt::Formatter)->std::fmt::Result{write!(f,"{}: {}",self.code,self.detail)}}
impl std::error::Error for Error{}
fn err(code:u32,s:impl ToString)->Error{Error{code,detail:s.to_string()}}
pub struct Model{plan:Plan}
pub struct Prediction{pub policy:[f32;136],pub value:f32}
impl Model{
 pub fn load_verified(bytes:&[u8],digest:&str,schema:&str)->Result<Self,Error>{
  if digest!=MODEL_SHA{return Err(err(1,"host verified SHA256 mismatch"))}if schema!=SCHEMA{return Err(err(2,"schema mismatch"))}
  if bytes.len()!=11663428{return Err(err(3,"model byte length mismatch"))}
  let model=tract_onnx::onnx().model_for_read(&mut Cursor::new(bytes)).map_err(|e|err(4,e))?.into_optimized().map_err(|e|err(4,e))?;
  if model.input_outlets().map_err(|e|err(4,e))?.len()!=1||model.output_outlets().map_err(|e|err(4,e))?.len()!=2{return Err(err(2,"IO count"))}
  for (f,shape) in [(model.input_fact(0).map_err(|e|err(4,e))?,&[1,8,9,9][..]),(model.output_fact(0).map_err(|e|err(4,e))?,&[1,136][..]),(model.output_fact(1).map_err(|e|err(4,e))?,&[1,1][..])]{if f.datum_type!=DatumType::F32||f.shape.as_concrete()!=Some(shape){return Err(err(2,"IO fact"))}}
  Ok(Self{plan:model.into_runnable().map_err(|e|err(4,e))?})
 }
 pub fn infer(&self,features:&[f32])->Result<Prediction,Error>{
  if features.len()!=648{return Err(err(5,"feature length"))}if features.iter().any(|v|!v.is_finite()){return Err(err(6,"nonfinite feature"))}
  let t=Tensor::from_shape(&[1,8,9,9],features).map_err(|e|err(7,e))?;let v=self.plan.run(tvec!(t.into())).map_err(|e|err(7,e))?;
  if v.len()!=2||v[0].shape()!=[1,136]||v[1].shape()!=[1,1]{return Err(err(8,"output shape"))}
  let p=v[0].to_array_view::<f32>().map_err(|e|err(8,e))?;let mut policy=[0f32;136];for (a,b) in policy.iter_mut().zip(p.iter()){*a=*b}
  let value=*v[1].to_array_view::<f32>().map_err(|e|err(8,e))?.iter().next().ok_or_else(||err(8,"empty value"))?;
  if policy.iter().any(|x|!x.is_finite())||!value.is_finite()|| !(-1.0..=1.0).contains(&value){return Err(err(9,"output finite/range"))}Ok(Prediction{policy,value})
 }
}
enum Entry{Bytes(Vec<u8>),Floats(Vec<f32>),Model(Model)}
struct Registry{next:u32,entries:BTreeMap<u32,Entry>,error:Error}
impl Registry{fn insert(&mut self,e:Entry)->u32{if self.next==u32::MAX{self.error=err(12,"handle exhausted");return 0}self.next+=1;self.entries.insert(self.next,e);self.next}fn fail(&mut self,e:Error)->u32{self.error=e;0}}
thread_local!{static REG:RefCell<Registry>=RefCell::new(Registry{next:0,entries:BTreeMap::new(),error:err(0,"ok")});}
#[no_mangle]pub extern "C" fn buffer_new(kind:u32,len:usize)->u32{REG.with(|r|{let mut r=r.borrow_mut();if kind==0&&len<=12000000{r.insert(Entry::Bytes(vec![0;len]))}else if kind==1&&len<=648{r.insert(Entry::Floats(vec![0.;len]))}else{r.fail(err(5,"buffer kind/length"))}})}
/// Pointer is a borrowed host view, valid only while the handle lives. Host must
/// use checked handle wrappers and discard every typed-array view before free.
#[no_mangle]pub extern "C" fn buffer_ptr(h:u32)->usize{REG.with(|r|{let mut r=r.borrow_mut();match r.entries.get_mut(&h){Some(Entry::Bytes(v))=>v.as_mut_ptr() as usize,Some(Entry::Floats(v))=>v.as_mut_ptr() as usize,_=>{r.fail(err(10,"invalid buffer handle"));0}}})}
#[no_mangle]pub extern "C" fn release_handle(h:u32)->u32{REG.with(|r|{let mut r=r.borrow_mut();if r.entries.remove(&h).is_some(){1}else{r.fail(err(10,"invalid/stale handle"))}})}
#[no_mangle]pub extern "C" fn model_load(b:u32,d:u32,schema:u32)->u32{REG.with(|r|{let mut r=r.borrow_mut();let result=(||{if schema!=1{return Err(err(2,"schema mismatch"))}let bytes=match r.entries.get(&b){Some(Entry::Bytes(v))=>v,_=>return Err(err(10,"model bytes handle"))};let digest=match r.entries.get(&d){Some(Entry::Bytes(v))=>std::str::from_utf8(v).map_err(|_|err(1,"digest encoding"))?,_=>return Err(err(10,"digest handle"))};Model::load_verified(bytes,digest,SCHEMA)})();match result{Ok(m)=>r.insert(Entry::Model(m)),Err(e)=>r.fail(e)}})}
#[no_mangle]pub extern "C" fn model_run(m:u32,f:u32)->u32{REG.with(|r|{let mut r=r.borrow_mut();let result=(||{let model=match r.entries.get(&m){Some(Entry::Model(v))=>v,_=>return Err(err(10,"stale model"))};let features=match r.entries.get(&f){Some(Entry::Floats(v))=>v,_=>return Err(err(10,"features handle"))};model.infer(features)})();match result{Ok(v)=>{let mut out=v.policy.to_vec();out.push(v.value);r.insert(Entry::Floats(out))},Err(e)=>r.fail(e)}})}
#[no_mangle]pub extern "C" fn error_code()->u32{REG.with(|r|r.borrow().error.code)}
#[no_mangle]pub extern "C" fn live_handles()->usize{REG.with(|r|r.borrow().entries.len())}
#[cfg(target_arch="wasm32")]
#[link(wasm_import_module="env")]
extern "C"{fn probe_entropy(p:*mut u8,n:usize)->i32;}
#[cfg(target_arch="wasm32")]
fn host_random(d:&mut[u8])->Result<(),getrandom::Error>{if unsafe{probe_entropy(d.as_mut_ptr(),d.len())}==0{Ok(())}else{Err(getrandom::Error::UNSUPPORTED)}}
#[cfg(target_arch="wasm32")]
getrandom::register_custom_getrandom!(host_random);

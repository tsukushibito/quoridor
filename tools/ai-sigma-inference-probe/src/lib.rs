use tract_onnx::prelude::*;
use std::io::Cursor;
pub type Plan = SimplePlan<TypedFact, Box<dyn TypedOp>, TypedModel>;
pub fn load(bytes: &[u8]) -> TractResult<Plan> {
 tract_onnx::onnx().model_for_read(&mut Cursor::new(bytes))?.with_input_fact(0,f32::fact([1,8,9,9]).into())?.into_optimized()?.into_runnable()
}
pub fn infer(plan: &Plan, features:&[f32]) -> TractResult<Vec<f32>> {
 let t=Tensor::from_shape(&[1,8,9,9],features)?;
 let result=plan.run(tvec!(t.into()))?;
 assert!(result.len()==2 && result[0].shape()==[1,136] && result[1].shape()==[1,1],"shape mismatch");
 let mut out=result[0].to_array_view::<f32>()?.iter().copied().collect::<Vec<_>>();out.extend(result[1].to_array_view::<f32>()?.iter().copied());Ok(out)
}
#[no_mangle] pub extern "C" fn alloc_bytes(n:usize)->*mut u8 {Box::into_raw(vec![0u8;n].into_boxed_slice()) as *mut u8}
#[no_mangle] pub unsafe extern "C" fn model_load(p:*const u8,n:usize)->*mut Plan {match load(std::slice::from_raw_parts(p,n)){Ok(m)=>Box::into_raw(Box::new(m)),Err(_)=>std::ptr::null_mut()}}
#[no_mangle] pub extern "C" fn alloc_features()->*mut f32 {Box::into_raw(vec![0f32;648].into_boxed_slice()) as *mut f32}
#[no_mangle] pub unsafe extern "C" fn model_run(m:*const Plan,p:*const f32)->*mut f32 {match infer(&*m,std::slice::from_raw_parts(p,648)){Ok(v)=>Box::into_raw(v.into_boxed_slice()) as *mut f32,Err(_)=>std::ptr::null_mut()}}
#[cfg(target_arch="wasm32")]
#[link(wasm_import_module="env")]
extern "C" { fn probe_entropy(p:*mut u8,n:usize)->i32; }
#[cfg(target_arch="wasm32")]
fn host_random(dest:&mut [u8])->Result<(),getrandom::Error>{
 let rc=unsafe{probe_entropy(dest.as_mut_ptr(),dest.len())};
 if rc==0{Ok(())}else{Err(getrandom::Error::UNSUPPORTED)}
}
#[cfg(target_arch="wasm32")]
getrandom::register_custom_getrandom!(host_random);

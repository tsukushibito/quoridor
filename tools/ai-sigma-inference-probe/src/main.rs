use ai_sigma_inference_probe::{load,infer};
fn main()->Result<(),Box<dyn std::error::Error>> {
 let a=std::env::args().collect::<Vec<_>>();eprintln!("stage graph_load_optimize");let m=load(&std::fs::read(&a[1])?)?;eprintln!("stage loaded");
 let inputs:serde_json::Value=serde_json::from_slice(&std::fs::read(&a[2])?)?;let mut out=Vec::new();
 for f in inputs.as_array().unwrap(){let features=f["features"].as_array().unwrap().iter().map(|x|x.as_f64().unwrap() as f32).collect::<Vec<_>>();let v=infer(&m,&features)?;out.push(serde_json::json!({"id":f["id"],"policy_logits":&v[..136],"value":v[136]}));eprintln!("stage inference {}",f["id"]);}
 std::fs::write(&a[3],serde_json::to_vec(&out)?)?;Ok(())
}

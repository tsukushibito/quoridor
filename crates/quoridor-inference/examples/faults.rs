use quoridor_inference::{AotiBackend, TensorRtBackend};
use sha2::{Digest, Sha256};
use std::{fs, path::Path, time::Instant};
const SHA: &str = "d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d";
fn main() {
    let a: Vec<String> = std::env::args().collect();
    let output = Path::new(&a[3]);
    fs::create_dir_all(output).unwrap();
    let start = Instant::now();
    let mut cases = Vec::new();
    for device in [-1, 127] {
        let error = AotiBackend::new(Path::new(&a[1]), SHA, 24, device, true)
            .err()
            .expect("invalid device accepted")
            .to_string();
        cases.push(serde_json::json!({"backend":"aoti","device":device,"error":error}));
        let error = TensorRtBackend::new(Path::new(&a[2]), SHA, 24, device, true)
            .err()
            .expect("invalid device accepted")
            .to_string();
        cases.push(serde_json::json!({"backend":"tensorrt","device":device,"error":error}));
    }
    for (backend, runtime, name) in [
        ("aoti", "2.14.0+cu130", "corrupt.pt2"),
        ("tensorrt", "11.3.0.99", "corrupt.engine"),
    ] {
        let package = output.join(name);
        let bytes = b"corrupt package, initialization must unwind";
        fs::write(&package, bytes).unwrap();
        let hash = format!("{:x}", Sha256::digest(bytes));
        fs::write(format!("{}.manifest.json",package.display()),serde_json::to_vec(&serde_json::json!({"schema":"quoridor-native-inference-v1","backend":backend,"source_model_sha256":SHA,"artifact_sha256":hash,"dtype":"float32","tf32":false,"amp":false,"max_batch":24,"input_shape":["batch",8,9,9],"output_shapes":[["batch",136],["batch",1]],"runtime_version":runtime})).unwrap()).unwrap();
        for attempt in 0..3 {
            let error = if backend == "aoti" {
                AotiBackend::new(&package, SHA, 24, 0, true)
                    .err()
                    .expect("corrupt package accepted")
                    .to_string()
            } else {
                TensorRtBackend::new(&package, SHA, 24, 0, true)
                    .err()
                    .expect("corrupt engine accepted")
                    .to_string()
            };
            cases.push(serde_json::json!({"backend":backend,"attempt":attempt,"error":error}));
        }
    }
    let result = serde_json::json!({"cases":cases,"wall_seconds":start.elapsed().as_secs_f64(),"model_forward_calls":0,"resources":"no Rust handle returned on failing constructors; C++ RAII unwinds SDK session/streams/pinned buffers"});
    fs::write(
        output.join("faults.json"),
        serde_json::to_vec_pretty(&result).unwrap(),
    )
    .unwrap();
    println!("{result}");
}

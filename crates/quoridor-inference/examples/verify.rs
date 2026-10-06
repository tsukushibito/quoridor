use quoridor_inference::{FEATURES, InferenceBackend, OrtBackend};
use std::{path::Path, time::Instant};
fn main() {
    let args: Vec<String> = std::env::args().collect();
    let inputs: Vec<[f32; FEATURES]> =
        serde_json::from_reader::<_, Vec<Vec<f32>>>(std::fs::File::open(&args[4]).unwrap())
            .unwrap()
            .into_iter()
            .map(|row| row.try_into().unwrap())
            .collect();
    let start = Instant::now();
    let mut backend: Box<dyn InferenceBackend> = if args[1] == "ort" {
        Box::new(
            OrtBackend::new(
                Path::new(&args[2]),
                Path::new(&args[3]),
                "d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d",
            )
            .unwrap(),
        )
    } else if args[1] == "tensorrt" {
        #[cfg(feature = "tensorrt")]
        {
            Box::new(
                quoridor_inference::TensorRtBackend::new(
                    Path::new(&args[2]),
                    "d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d",
                    24,
                    0,
                    true,
                )
                .unwrap(),
            )
        }
        #[cfg(not(feature = "tensorrt"))]
        {
            panic!("requires tensorrt")
        }
    } else {
        #[cfg(feature = "cuda-aoti")]
        {
            Box::new(
                quoridor_inference::AotiBackend::new(
                    Path::new(&args[2]),
                    "d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d",
                    24,
                    0,
                    args[1] == "graph",
                )
                .unwrap(),
            )
        }
        #[cfg(not(feature = "cuda-aoti"))]
        {
            panic!("requires cuda-aoti")
        }
    };
    let initialization = start.elapsed().as_secs_f64();
    let mut times = Vec::new();
    let mut results = Vec::new();
    for _ in 0..9 {
        let t = Instant::now();
        results = backend.infer(&inputs).unwrap();
        times.push(t.elapsed().as_secs_f64());
    }
    let counters = backend.counters();
    println!(
        "{}",
        serde_json::json!({"backend":backend.metadata().backend,"inference_counters":{"logical_rows":counters.logical_rows,"executed_rows":counters.executed_rows,"warm_rows":counters.warm_rows,"failed_rows":counters.failed_rows,"failed_warm_rows":counters.failed_warm_rows,"capture_rows":counters.capture_rows,"physical_rows":counters.physical_rows()},"initialization_seconds":initialization,"forward_seconds":times,"outputs":results.into_iter().map(|v|{let mut a=v.logits.to_vec();a.push(v.value);a}).collect::<Vec<_>>()})
    );
}

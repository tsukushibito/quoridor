//! The maintained direct JSONL cache entry. No generator/training mode.
use sha2::{Digest, Sha256};

fn main() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let args = std::env::args().skip(1).collect::<Vec<_>>();
    if args.as_slice() == ["research-bindings"] {
        let sources = compiled_sources();
        println!(
            "{}",
            serde_json::to_string(&serde_json::json!({
                "artifact_target":"terminal-cache", "model_calls":0, "search_calls":0,
                "executable_sha256":format!("{:x}", Sha256::digest(std::fs::read(std::env::current_exe()?)?)),
                "compiled_sources":sources
            }))?
        );
        return Ok(());
    }
    if args.as_slice() == ["--help"] {
        println!("terminal-cache STREAM NEW_OUTPUT INTAKE_BINDING BINDING_SHA256");
        return Ok(());
    }
    if args.len() != 4 {
        return Err("expected STREAM NEW_OUTPUT INTAKE_BINDING BINDING_SHA256".into());
    }
    let cache = quoridor_data::terminal_stream::write_cache(
        std::path::Path::new(&args[0]),
        std::path::Path::new(&args[1]),
        std::path::Path::new(&args[2]),
        &args[3],
    )?;
    println!("{}", serde_json::to_string(&cache)?);
    Ok(())
}

fn compiled_sources() -> std::collections::BTreeMap<&'static str, String> {
    [
        (
            "crates/quoridor-data/src/bin/terminal-cache.rs",
            include_bytes!("terminal-cache.rs").as_slice(),
        ),
        (
            "crates/quoridor-data/src/lib.rs",
            include_bytes!("../lib.rs").as_slice(),
        ),
        (
            "crates/quoridor-data/src/terminal.rs",
            include_bytes!("../terminal.rs").as_slice(),
        ),
        (
            "crates/quoridor-data/src/terminal_stream.rs",
            include_bytes!("../terminal_stream.rs").as_slice(),
        ),
        (
            "crates/quoridor-data/src/terminal_cache.rs",
            include_bytes!("../terminal_cache.rs").as_slice(),
        ),
        (
            "crates/quoridor-data/src/common_corpus.rs",
            include_bytes!("../common_corpus.rs").as_slice(),
        ),
        (
            "crates/quoridor-data/src/lossless_jsonl.rs",
            include_bytes!("../lossless_jsonl.rs").as_slice(),
        ),
        (
            "crates/quoridor-core/src/lib.rs",
            include_bytes!("../../../quoridor-core/src/lib.rs").as_slice(),
        ),
        (
            "crates/quoridor-core/src/game.rs",
            include_bytes!("../../../quoridor-core/src/game.rs").as_slice(),
        ),
        (
            "crates/quoridor-core/src/position.rs",
            include_bytes!("../../../quoridor-core/src/position.rs").as_slice(),
        ),
        (
            "crates/quoridor-core/src/research.rs",
            include_bytes!("../../../quoridor-core/src/research.rs").as_slice(),
        ),
        (
            "crates/quoridor-core/src/profiling.rs",
            include_bytes!("../../../quoridor-core/src/profiling.rs").as_slice(),
        ),
        (
            "crates/quoridor-nnue/src/lib.rs",
            include_bytes!("../../../quoridor-nnue/src/lib.rs").as_slice(),
        ),
        (
            "crates/quoridor-nnue/src/features.rs",
            include_bytes!("../../../quoridor-nnue/src/features.rs").as_slice(),
        ),
        (
            "crates/quoridor-nnue/src/quantized.rs",
            include_bytes!("../../../quoridor-nnue/src/quantized.rs").as_slice(),
        ),
        (
            "crates/quoridor-nnue/src/residual.rs",
            include_bytes!("../../../quoridor-nnue/src/residual.rs").as_slice(),
        ),
        (
            "crates/quoridor-nnue/src/simd.rs",
            include_bytes!("../../../quoridor-nnue/src/simd.rs").as_slice(),
        ),
        (
            "crates/quoridor-nnue/src/distance_step.rs",
            include_bytes!("../../../quoridor-nnue/src/distance_step.rs").as_slice(),
        ),
        (
            "crates/quoridor-data/Cargo.toml",
            include_bytes!("../../Cargo.toml").as_slice(),
        ),
        (
            "crates/quoridor-core/Cargo.toml",
            include_bytes!("../../../quoridor-core/Cargo.toml").as_slice(),
        ),
        (
            "crates/quoridor-nnue/Cargo.toml",
            include_bytes!("../../../quoridor-nnue/Cargo.toml").as_slice(),
        ),
        (
            "Cargo.toml",
            include_bytes!("../../../../Cargo.toml").as_slice(),
        ),
        (
            "Cargo.lock",
            include_bytes!("../../../../Cargo.lock").as_slice(),
        ),
    ]
    .into_iter()
    .map(|(path, raw)| (path, format!("{:x}", Sha256::digest(raw))))
    .collect()
}

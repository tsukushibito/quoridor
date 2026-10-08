//! The maintained direct JSONL cache entry. No generator/training mode.
fn main() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let args = std::env::args().skip(1).collect::<Vec<_>>();
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

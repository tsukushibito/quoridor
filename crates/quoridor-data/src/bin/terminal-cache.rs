//! The maintained ordered stream-to-cache converter.
use quoridor_data::{Result, terminal_stream::BoundJson};
use std::path::PathBuf;
struct Args {
    inputs: Vec<PathBuf>,
    output: PathBuf,
    binding: Option<BoundJson>,
}
fn parse(args: &[String]) -> Result<Args> {
    let mut inputs = Vec::new();
    let mut output = None;
    let mut path = None;
    let mut sha = None;
    let mut i = 0;
    while i < args.len() {
        let value = args.get(i + 1).ok_or("flag requires a value")?;
        match args[i].as_str() {
            "--input" => inputs.push(PathBuf::from(value)),
            "--output" if output.is_none() => output = Some(PathBuf::from(value)),
            "--input-binding" if path.is_none() => path = Some(PathBuf::from(value)),
            "--binding-sha256" if sha.is_none() => sha = Some(value.clone()),
            _ => return Err("unknown or repeated converter flag".into()),
        }
        i += 2;
    }
    let binding = match (path, sha) {
        (Some(path), Some(sha256)) => Some(BoundJson { path, sha256 }),
        (None, None) => None,
        _ => return Err("input binding path and SHA must be supplied together".into()),
    };
    if inputs.is_empty() {
        return Err("at least one --input required".into());
    }
    Ok(Args {
        inputs,
        output: output.ok_or("--output required")?,
        binding,
    })
}
fn main() -> Result<()> {
    let args = std::env::args().skip(1).collect::<Vec<_>>();
    if args.as_slice() == ["--help"] {
        println!(
            "terminal-cache --input STREAM [--input STREAM ...] --output NEW_OUTPUT [--input-binding PATH --binding-sha256 SHA]"
        );
        return Ok(());
    }
    let a = parse(&args)?;
    let cache =
        quoridor_data::terminal_stream::write_cache(&a.inputs, &a.output, a.binding.as_ref())?;
    println!("{}", serde_json::to_string(&cache)?);
    Ok(())
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn configured_converter_preserves_input_order_and_optional_binding_pair() {
        let argv =
            ["--input", "/b.gz", "--input", "/a.gz", "--output", "/fresh"].map(str::to_owned);
        let a = parse(&argv).unwrap();
        assert_eq!(
            a.inputs,
            vec![PathBuf::from("/b.gz"), PathBuf::from("/a.gz")]
        );
        assert!(a.binding.is_none());
        let mut argv = argv.to_vec();
        argv.extend(["--input-binding".into(), "/lineage.json".into()]);
        assert!(parse(&argv).is_err());
        argv.extend(["--binding-sha256".into(), "a".repeat(64)]);
        assert_eq!(
            parse(&argv).unwrap().binding.unwrap().sha256,
            "a".repeat(64)
        );
        assert!(
            parse(&[
                "old-stream".into(),
                "old-output".into(),
                "binding".into(),
                "sha".into()
            ])
            .is_err()
        );
    }
}

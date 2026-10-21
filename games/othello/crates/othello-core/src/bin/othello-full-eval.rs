//! Explicit scalar correspondence entry; no search, game generation or defaults.
//! Input JSONL: {"op":"evaluate","state":<existing version1 GameState>}.
//! Weight identities are caller-verified bindings, not locally computed hashes.

use othello_core::{
    GameState,
    bitboard::Position,
    full_eval::{FeatureState, FullEvaluator, FullWeights, TableInterpretation},
};
use serde::Deserialize;
use serde_json::{Value, json};
use std::io::{self, BufRead, BufReader, Write};

#[derive(Deserialize)]
#[serde(tag = "op", rename_all = "camelCase", deny_unknown_fields)]
enum Request {
    Evaluate { state: GameState },
}

struct Loaded {
    weights: FullWeights,
    interpretation: TableInterpretation,
    midgame_id: String,
    ordering_id: String,
}

fn identity(input: &str) -> Result<String, &'static str> {
    let hash = input
        .strip_prefix("sha256:")
        .ok_or("identity requires sha256:HEX")?;
    if hash.len() != 64 || !hash.bytes().all(|b| b.is_ascii_hexdigit()) {
        return Err("identity requires a 64-digit SHA256");
    }
    Ok(input.to_ascii_lowercase())
}

fn load(args: &[String]) -> Result<Loaded, Box<dyn std::error::Error>> {
    if args.len() != 10
        || args[0] != "--midgame"
        || args[2] != "--ordering"
        || args[4] != "--midgame-id"
        || args[6] != "--ordering-id"
        || args[8] != "--interpretation"
    {
        return Err("usage: othello-full-eval --midgame PATH --ordering PATH --midgame-id sha256:HEX --ordering-id sha256:HEX --interpretation generic|simd".into());
    }
    let midgame_id = identity(&args[5])?;
    let ordering_id = identity(&args[7])?;
    let interpretation = args[9].parse()?;
    let weights = FullWeights::read(
        BufReader::new(std::fs::File::open(&args[1])?),
        BufReader::new(std::fs::File::open(&args[3])?),
    )?;
    Ok(Loaded {
        weights,
        interpretation,
        midgame_id,
        ordering_id,
    })
}

fn respond(input: &str, loaded: &Loaded) -> Result<Value, Box<dyn std::error::Error>> {
    let Request::Evaluate { state } = serde_json::from_str(input)?;
    let features = FeatureState::new(Position::from(&state));
    let evaluator = FullEvaluator::new(&loaded.weights, loaded.interpretation);
    Ok(json!({
        "ok":true,"evaluation":evaluator.trace(&features)?,
        "weights":{"midgameId":loaded.midgame_id,"orderingId":loaded.ordering_id,
            "identityBinding":"callerVerified","decodedBytes":loaded.weights.decoded_bytes()}
    }))
}

fn main() -> io::Result<()> {
    let loaded = load(&std::env::args().skip(1).collect::<Vec<_>>())
        .map_err(|error| io::Error::new(io::ErrorKind::InvalidInput, error.to_string()))?;
    let mut output = io::BufWriter::new(io::stdout().lock());
    for line in io::stdin().lock().lines() {
        let response = respond(&line?, &loaded)
            .unwrap_or_else(|error| json!({"ok":false,"error":error.to_string()}));
        serde_json::to_writer(&mut output, &response)?;
        writeln!(output)?;
        output.flush()?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn full_eval_native_boundary_is_explicit_and_strict() {
        assert!(serde_json::from_str::<Request>(r#"{"op":"evaluate","state":null}"#).is_err());
        let request = json!({"op":"evaluate","state":GameState::new(),"extra":1});
        assert!(serde_json::from_value::<Request>(request).is_err());
        assert!(load(&[]).is_err());
        assert!(identity("sha256:abc").is_err());
        assert_eq!(
            identity(&format!("sha256:{}", "A".repeat(64))).unwrap(),
            format!("sha256:{}", "a".repeat(64))
        );
        assert!("unknown".parse::<TableInterpretation>().is_err());
    }
}

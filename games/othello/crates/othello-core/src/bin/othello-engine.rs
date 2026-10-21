//! Stateless JSONL protocol: each request owns its state and its search budget.

use othello_core::{
    GameState,
    bitboard::Position,
    pattern::PatternWeights,
    search::{Evaluator, SearchOptions, search_native},
};
use serde::Deserialize;
use serde_json::{Value, json};
use std::io::{self, BufRead, Read, Write};

#[derive(Deserialize)]
#[serde(tag = "op", rename_all = "camelCase", deny_unknown_fields)]
enum Request {
    New {},
    Status {
        state: GameState,
    },
    Play {
        state: GameState,
        r#move: u32,
    },
    Pass {
        state: GameState,
    },
    Simple {
        state: GameState,
    },
    Evaluate {
        state: GameState,
    },
    Search {
        state: GameState,
        #[serde(default = "default_time", rename = "timeMs")]
        time_ms: u64,
        #[serde(default = "default_tt", rename = "ttMiB")]
        tt_mib: usize,
        #[serde(default = "default_depth", rename = "maxDepth")]
        max_depth: u8,
        #[serde(default = "default_exact", rename = "exactEmpties")]
        exact_empties: u8,
    },
}

fn default_time() -> u64 {
    1000
}
fn default_tt() -> usize {
    32
}
fn default_depth() -> u8 {
    64
}
fn default_exact() -> u8 {
    12
}

struct LoadedPattern {
    weights: PatternWeights,
    model_id: String,
    bytes: usize,
}

fn load_pattern(args: &[String]) -> Result<Option<LoadedPattern>, Box<dyn std::error::Error>> {
    if args.is_empty() {
        return Ok(None);
    }
    if args.len() != 4 || args[0] != "--pattern" || args[2] != "--model-id" {
        return Err("usage: othello-engine [--pattern PATH --model-id sha256:HEX]".into());
    }
    let Some(hash) = args[3].strip_prefix("sha256:") else {
        return Err("model-id requires sha256:HEX".into());
    };
    if hash.len() != 64 || !hash.bytes().all(|b| b.is_ascii_hexdigit()) {
        return Err("model-id requires a 64-digit SHA256".into());
    }
    // Root binds image+input SHA/bytes before launch. This ID is explicitly caller
    // verified, not claimed as a digest computed here; no hashing dependency added.
    let mut input = String::new();
    std::fs::File::open(&args[1])?
        .take(128 * 1024 + 1)
        .read_to_string(&mut input)?;
    Ok(Some(LoadedPattern {
        weights: PatternWeights::from_json(&input)?,
        model_id: args[3].to_ascii_lowercase(),
        bytes: input.len(),
    }))
}

fn evaluation_identity(model: Option<&LoadedPattern>) -> Value {
    match model {
        Some(model) => {
            json!({"kind":"patternV1","modelId":model.model_id,"modelBytes":model.bytes,"identityBinding":"callerVerified"})
        }
        None => json!({"kind":"v1Heuristic"}),
    }
}

fn respond(line: &str, model: Option<&LoadedPattern>) -> Result<Value, Box<dyn std::error::Error>> {
    let evaluator = model.map_or(Evaluator::V1Heuristic, |model| {
        Evaluator::Pattern(&model.weights)
    });
    Ok(match serde_json::from_str::<Request>(line)? {
        Request::New {} => json!({"ok":true, "state":GameState::new()}),
        Request::Status { state } => json!({"ok":true, "status":state.status()}),
        Request::Play { state, r#move } => json!({"ok":true, "state":state.play(r#move)?}),
        Request::Pass { state } => json!({"ok":true, "state":state.pass()?}),
        Request::Simple { state } => json!({"ok":true, "move":state.choose_move()}),
        Request::Evaluate { state } => {
            json!({"ok":true,"score":evaluator.evaluate(Position::from(&state)),
            "scoreKind":"heuristic","proven":false,"evaluation":evaluation_identity(model)})
        }
        Request::Search {
            state,
            time_ms,
            tt_mib,
            max_depth,
            exact_empties,
        } => {
            let options = SearchOptions {
                time_ms,
                tt_mi_b: tt_mib,
                max_depth,
                exact_empties,
            };
            let mut result = serde_json::to_value(search_native(&state, options, evaluator)?)?;
            result["ok"] = json!(true);
            result["evaluation"] = evaluation_identity(model);
            result
        }
    })
}

fn main() -> io::Result<()> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let model = load_pattern(&args)
        .map_err(|error| io::Error::new(io::ErrorKind::InvalidInput, error.to_string()))?;
    let stdin = io::stdin();
    let mut stdout = io::BufWriter::new(io::stdout().lock());
    for line in stdin.lock().lines() {
        let line = line?;
        let response = respond(&line, model.as_ref())
            .unwrap_or_else(|error| json!({"ok":false,"error":error.to_string()}));
        serde_json::to_writer(&mut stdout, &response)?;
        writeln!(stdout)?;
        stdout.flush()?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn protocol_recovers_after_bad_requests_and_keeps_search_flat() {
        for bad in ["{", r#"{"op":"wat"}"#, r#"{"op":"new","extra":1}"#] {
            assert!(
                respond(bad, None).is_err(),
                "invalid request accepted: {bad}"
            );
        }
        let initial = respond(r#"{"op":"new"}"#, None).unwrap()["state"].clone();
        for op in ["status", "simple", "search"] {
            let mut request = json!({"op":op,"state":initial});
            if op == "search" {
                request["timeMs"] = json!(0);
            }
            let response = respond(&request.to_string(), None).unwrap();
            assert_eq!(response["ok"], true);
            if op == "search" {
                assert_eq!(response["scoreKind"], "heuristic");
                assert_eq!(response["proven"], false);
                assert_eq!(response["timedOut"], true);
            }
        }
        assert!(respond(&json!({"op":"pass","state":initial}).to_string(), None).is_err());
        let played = respond(
            &json!({"op":"play","state":initial,"move":19}).to_string(),
            None,
        )
        .unwrap();
        assert_eq!(played["state"]["toMove"], 2);
    }

    #[test]
    fn pattern_native_boundary_keeps_selection_identity_and_simple_explicit() {
        let input = json!({"version":1,"shapes":[[0,1,2,8,9,10],[1,2,3,4,5,6]],
            "cellOrder":"shape-list-lsb-ternary","encoding":"empty0-stm1-opponent2",
            "transforms":"mirror-then-clockwise-rotations-0-1-2-3",
            "phase":"min(3,clamp(occupied-4,0,60)//15)","score":"stm-centidiscs",
            "quantization":{"scale":1,"rounding":"nearest-ties-even","minimum":-32767,"maximum":32767},
            "weights":vec![vec![vec![0;729];2];4]}).to_string();
        let loaded = LoadedPattern {
            weights: PatternWeights::from_json(&input).unwrap(),
            model_id: format!("sha256:{}", "0".repeat(64)),
            bytes: input.len(),
        };
        let state = GameState::new().play(19).unwrap();
        let evaluate = json!({"op":"evaluate","state":state}).to_string();
        let baseline = respond(&evaluate, None).unwrap();
        let selected = respond(&evaluate, Some(&loaded)).unwrap();
        assert_eq!(baseline["score"], -3);
        assert_eq!(selected["score"], 0);
        assert_eq!(selected["proven"], false);
        assert_eq!(selected["evaluation"]["modelId"], loaded.model_id);
        assert_eq!(selected["evaluation"]["identityBinding"], "callerVerified");
        let simple = json!({"op":"simple","state":state}).to_string();
        assert_eq!(
            respond(&simple, None).unwrap(),
            respond(&simple, Some(&loaded)).unwrap()
        );
        let search = json!({"op":"search","state":state,"timeMs":0,"ttMiB":0}).to_string();
        let selected = respond(&search, Some(&loaded)).unwrap();
        assert_eq!(selected["score"], 0);
        assert_eq!(selected["timedOut"], true);
        assert_eq!(selected["evaluation"]["kind"], "patternV1");
        assert!(load_pattern(&[]).unwrap().is_none());
        assert!(load_pattern(&["--pattern".into()]).is_err());
        assert!(
            load_pattern(&[
                "--pattern".into(),
                "unused".into(),
                "--model-id".into(),
                "sha256:bad".into()
            ])
            .is_err()
        );
    }
}

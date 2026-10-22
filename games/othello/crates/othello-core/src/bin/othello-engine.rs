//! Stateless JSONL protocol: each request owns its state and its search budget.

use othello_core::{
    GameState,
    bitboard::Position,
    heuristic,
    search::{SearchOptions, search_native},
};
use serde::Deserialize;
use serde_json::{Value, json};
use std::io::{self, BufRead, Write};

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

fn respond(line: &str) -> Result<Value, Box<dyn std::error::Error>> {
    Ok(match serde_json::from_str::<Request>(line)? {
        Request::New {} => json!({"ok":true, "state":GameState::new()}),
        Request::Status { state } => json!({"ok":true, "status":state.status()}),
        Request::Play { state, r#move } => json!({"ok":true, "state":state.play(r#move)?}),
        Request::Pass { state } => json!({"ok":true, "state":state.pass()?}),
        Request::Simple { state } => json!({"ok":true, "move":state.choose_move()}),
        Request::Evaluate { state } => {
            json!({"ok":true,"score":heuristic::evaluate(Position::from(&state)),
            "scoreKind":"heuristic","proven":false,"evaluation":json!({"kind":"v1Heuristic"})})
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
            let mut result = serde_json::to_value(search_native(&state, options)?)?;
            result["ok"] = json!(true);
            result["evaluation"] = json!({"kind":"v1Heuristic"});
            result
        }
    })
}

fn main() -> io::Result<()> {
    if std::env::args_os().len() != 1 {
        return Err(io::Error::new(
            io::ErrorKind::InvalidInput,
            "usage: othello-engine",
        ));
    }
    let stdin = io::stdin();
    let mut stdout = io::BufWriter::new(io::stdout().lock());
    for line in stdin.lock().lines() {
        let line = line?;
        let response =
            respond(&line).unwrap_or_else(|error| json!({"ok":false,"error":error.to_string()}));
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
            assert!(respond(bad).is_err(), "invalid request accepted: {bad}");
        }
        let initial = respond(r#"{"op":"new"}"#).unwrap()["state"].clone();
        for op in ["status", "simple", "evaluate", "search"] {
            let mut request = json!({"op":op,"state":initial});
            if op == "search" {
                request["timeMs"] = json!(0);
            }
            let response = respond(&request.to_string()).unwrap();
            assert_eq!(response["ok"], true);
            if op == "evaluate" {
                assert_eq!(response["evaluation"], json!({"kind":"v1Heuristic"}));
                assert_eq!(response["scoreKind"], "heuristic");
                assert_eq!(response["proven"], false);
            }
            if op == "search" {
                assert_eq!(response["scoreKind"], "heuristic");
                assert_eq!(response["proven"], false);
                assert_eq!(response["timedOut"], true);
            }
        }
        assert!(respond(&json!({"op":"pass","state":initial}).to_string()).is_err());
        let played = respond(&json!({"op":"play","state":initial,"move":19}).to_string()).unwrap();
        assert_eq!(played["state"]["toMove"], 2);
    }
}

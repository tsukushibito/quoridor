// SPDX-License-Identifier: GPL-3.0-or-later
//! Explicit full-weight engine-disc JSONL boundary; baseline engine unchanged.
use othello_core::{
    GameState,
    full_eval::{FullWeights, TableInterpretation},
    full_search::{FullSearch, FullSearchOptions, MpcCoefficients},
};
use serde::Deserialize;
use serde_json::{Value, json};
use std::{
    fs::File,
    io::{self, BufRead, BufReader, Write},
};

#[derive(Deserialize)]
#[serde(tag = "op", rename_all = "camelCase", deny_unknown_fields)]
enum Request {
    Search {
        state: GameState,
        #[serde(default)]
        options: FullSearchOptions,
    },
    Clear {},
    Info {},
}
fn identity(text: &str) -> Result<String, &'static str> {
    let hash = text
        .strip_prefix("sha256:")
        .ok_or("identity requires sha256:HEX")?;
    if hash.len() != 64 || !hash.bytes().all(|b| b.is_ascii_hexdigit()) {
        return Err("identity requires64 hex digits");
    }
    Ok(text.to_ascii_lowercase())
}
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if ![10, 14].contains(&args.len())
        || args[0] != "--midgame"
        || args[2] != "--ordering"
        || args[4] != "--midgame-id"
        || args[6] != "--ordering-id"
        || args[8] != "--interpretation"
        || (args.len() == 14 && (args[10] != "--hash-level" || args[12] != "--coefficients"))
    {
        return Err("usage: othello-full-search --midgame PATH --ordering PATH --midgame-id sha256:HEX --ordering-id sha256:HEX --interpretation generic|simd [--hash-level6..20 --coefficients JSON]".into());
    }
    let midgame_id = identity(&args[5])?;
    let ordering_id = identity(&args[7])?;
    let interpretation: TableInterpretation = args[9].parse()?;
    let weights = FullWeights::read(
        BufReader::new(File::open(&args[1])?),
        BufReader::new(File::open(&args[3])?),
    )?;
    let coefficients = if args.len() == 14 {
        serde_json::from_str(&args[13])?
    } else {
        MpcCoefficients::default()
    };
    let hash_level = if args.len() == 14 {
        args[11].parse()?
    } else {
        20
    };
    let mut engine = FullSearch::new(weights, interpretation, hash_level, coefficients)?;
    let input = io::stdin();
    let mut output = io::BufWriter::new(io::stdout().lock());
    for line in input.lock().lines() {
        let line = line?;
        let response=(||->Result<Value,Box<dyn std::error::Error>> {
            Ok(match serde_json::from_str::<Request>(&line)? {
                Request::Search {state,options}=>json!({"ok":true,"result":engine.search_native(&state,options)?}),
                Request::Clear {}=>{engine.clear();json!({"ok":true})},
                Request::Info {}=>json!({"ok":true,"engine":"console7.8.1-rust-singlethread-source-port","upstreamCommit":othello_core::full_eval::UPSTREAM_COMMIT,"interpretation":interpretation,"midgameId":midgame_id,"orderingId":ordering_id,"identityBinding":"callerVerified","hashLevel":hash_level,"hashSeed":20261022,"coefficients":coefficients,"workerPool":0}),
            })
        })().unwrap_or_else(|error|json!({"ok":false,"error":error.to_string()}));
        serde_json::to_writer(&mut output, &response)?;
        writeln!(output)?;
        output.flush()?;
    }
    Ok(())
}

//! One binding manifest for configuration, replay, implementation and the whole slot census.
use crate::{arena, arena_statistics::Slot, config::Config, runtime::RunReport};
use quoridor_data::Result;
use serde::Serialize;
use sha2::{Digest, Sha256};
use std::{
    collections::BTreeMap,
    fs::{self, File, OpenOptions},
    io::{Read, Write},
    path::Path,
    process::{Command, Stdio},
};

pub fn search_source_sha256(kind: &str) -> String {
    if kind == "mcts" {
        arena::digest(include_bytes!("../../quoridor-ai/src/sigma_mcts.rs"))
    } else {
        arena::digest(include_bytes!("../../quoridor-ai/src/alphabeta.rs"))
    }
}
pub fn source_bindings() -> BTreeMap<&'static str, String> {
    // Compiled bytes, rather than a mutable source tree read after the run.
    let sources: &[(&str, &[u8])] = &[
        ("Cargo.lock", include_bytes!("../../../Cargo.lock")),
        ("runner/Cargo.toml", include_bytes!("../Cargo.toml")),
        ("runner/main.rs", include_bytes!("main.rs")),
        ("runner/lib.rs", include_bytes!("lib.rs")),
        ("runner/runtime.rs", include_bytes!("runtime.rs")),
        ("runner/config.rs", include_bytes!("config.rs")),
        ("runner/resources.rs", include_bytes!("resources.rs")),
        ("runner/native_input.rs", include_bytes!("native_input.rs")),
        ("runner/arena_book.rs", include_bytes!("arena_book.rs")),
        (
            "runner/nnue-diagnose.rs",
            include_bytes!("bin/nnue-diagnose.rs"),
        ),
        ("runner/arena.rs", include_bytes!("arena.rs")),
        ("runner/arena_clock.rs", include_bytes!("arena_clock.rs")),
        ("runner/sigma_clock.rs", include_bytes!("sigma_clock.rs")),
        (
            "runner/arena_statistics.rs",
            include_bytes!("arena_statistics.rs"),
        ),
        (
            "runner/arena_manifest.rs",
            include_bytes!("arena_manifest.rs"),
        ),
        (
            "core/lib.rs",
            include_bytes!("../../quoridor-core/src/lib.rs"),
        ),
        (
            "core/game.rs",
            include_bytes!("../../quoridor-core/src/game.rs"),
        ),
        (
            "core/position.rs",
            include_bytes!("../../quoridor-core/src/position.rs"),
        ),
        (
            "core/research.rs",
            include_bytes!("../../quoridor-core/src/research.rs"),
        ),
        ("ai/lib.rs", include_bytes!("../../quoridor-ai/src/lib.rs")),
        (
            "ai/alphabeta.rs",
            include_bytes!("../../quoridor-ai/src/alphabeta.rs"),
        ),
        (
            "ai/sigma_mcts.rs",
            include_bytes!("../../quoridor-ai/src/sigma_mcts.rs"),
        ),
        (
            "nnue/lib.rs",
            include_bytes!("../../quoridor-nnue/src/lib.rs"),
        ),
        (
            "nnue/features.rs",
            include_bytes!("../../quoridor-nnue/src/features.rs"),
        ),
        (
            "nnue/simd.rs",
            include_bytes!("../../quoridor-nnue/src/simd.rs"),
        ),
        (
            "nnue/residual.rs",
            include_bytes!("../../quoridor-nnue/src/residual.rs"),
        ),
        (
            "nnue/quantized.rs",
            include_bytes!("../../quoridor-nnue/src/quantized.rs"),
        ),
        (
            "inference/lib.rs",
            include_bytes!("../../quoridor-inference/src/lib.rs"),
        ),
        (
            "inference/cuda.rs",
            include_bytes!("../../quoridor-inference/src/cuda.rs"),
        ),
        (
            "inference/tensorrt.rs",
            include_bytes!("../../quoridor-inference/src/tensorrt.rs"),
        ),
        (
            "data/lib.rs",
            include_bytes!("../../quoridor-data/src/lib.rs"),
        ),
    ];
    sources
        .iter()
        .map(|&(p, b)| (p, arena::digest(b)))
        .collect()
}
pub fn file_sha256(path: &Path) -> Result<String> {
    let mut file = File::open(path)?;
    let mut sha = Sha256::new();
    let mut buf = [0u8; 65536];
    loop {
        let n = file.read(&mut buf)?;
        if n == 0 {
            break;
        }
        sha.update(&buf[..n]);
    }
    Ok(sha.finalize().iter().map(|b| format!("{b:02x}")).collect())
}
pub fn slots(c: &Config, planned: &[(usize, String, Vec<u16>)]) -> Result<Vec<Slot>> {
    planned
        .iter()
        .map(|(game, family, opening)| {
            let metadata = c.arena.as_ref().map(|a| &a.book.openings[game / 2]);
            let replay = arena::replay(opening);
            let reference_q_stm = metadata
                .and_then(|m| m.reference.as_ref())
                .and_then(|r| replay.as_ref().ok().and_then(|p| r.q_stm(p.turn)));
            Ok(Slot {
                game: *game,
                family: family.clone(),
                candidate_color: (game % 2) as u8,
                cohort: metadata.map_or("unclassified".into(), |m| format!("{:?}", m.cohort)),
                lineage: metadata
                    .map_or("legacy_independence_unknown".into(), |m| m.lineage.clone()),
                opening: opening.clone(),
                replay_error: replay.as_ref().err().map(ToString::to_string),
                replay: replay.ok(),
                reference_q_stm,
                reference_q_band: reference_q_stm.map(|q| {
                    if q.abs() <= 0.2 {
                        "provisional_main"
                    } else if q.abs() <= 0.4 {
                        "auxiliary"
                    } else {
                        "tilted_diagnostic"
                    }
                    .into()
                }),
            })
        })
        .collect()
}
pub fn preflight(c: &Config, slots: &[Slot]) -> Result<()> {
    let metadata = serde_json::to_vec(c)?.len() as u64 + serde_json::to_vec(slots)?.len() as u64;
    // Includes result + manifest + gzip + journal/CSV and final source bindings.
    let needed = metadata
        .saturating_mul(6)
        .saturating_add(262144)
        .saturating_add(
            (c.games as u64)
                .saturating_mul(c.max_plies as u64)
                .saturating_mul(16384),
        );
    if needed > c.max_output_bytes {
        return Err(format!(
            "arena output forecast {needed} exceeds {}",
            c.max_output_bytes
        )
        .into());
    }
    Ok(())
}
pub fn write(c: &Config, name: &str, value: &impl Serialize) -> Result<()> {
    write_bytes(c, name, &serde_json::to_vec(value)?)
}
fn write_bytes(c: &Config, name: &str, bytes: &[u8]) -> Result<()> {
    if crate::resources::directory_bytes(&c.output)?.saturating_add(bytes.len() as u64)
        > c.max_output_bytes
    {
        return Err("arena evidence output limit".into());
    }
    let mut f = OpenOptions::new()
        .create_new(true)
        .write(true)
        .open(c.output.join(name))?;
    f.write_all(bytes)?;
    f.sync_all()?;
    Ok(())
}
pub fn journal(c: &Config, outcome: &crate::runtime::Outcome) -> Result<()> {
    let mut bytes = serde_json::to_vec(outcome)?;
    bytes.push(b'\n');
    if crate::resources::directory_bytes(&c.output)?.saturating_add(bytes.len() as u64)
        > c.max_output_bytes
    {
        return Err("arena outcome journal limit".into());
    }
    let mut f = OpenOptions::new()
        .create(true)
        .append(true)
        .open(c.output.join("completed.jsonl"))?;
    f.write_all(&bytes)?;
    f.sync_data()?;
    Ok(())
}
pub fn begin(c: &Config, slots: &[Slot], admission: &crate::resources::Admission) -> Result<()> {
    let exe = std::env::current_exe()?;
    let requested_tt = c.arena.as_ref().map_or(65536, |a| a.tt_entries);
    write(
        c,
        "manifest-start.json",
        &serde_json::json!({
        "schema":arena::SCHEMA,"schema_sources_sha256":arena::json_digest(&serde_json::json!({
            "arena":arena::digest(include_bytes!("arena.rs")),"clock":arena::digest(include_bytes!("arena_clock.rs")),
            "statistics":arena::digest(include_bytes!("arena_statistics.rs")),"runtime":arena::digest(include_bytes!("runtime.rs"))}))?,
            "run_id":c.run_id,"config":c,"config_sha256":arena::json_digest(c)?,
            "book_sha256":c.arena.as_ref().map(|a| arena::json_digest(&a.book)).transpose()?,
            "planned_slots":slots,"planned_sha256":arena::json_digest(&slots)?,
        "compiled_sources":source_bindings(),"executable":exe,"executable_sha256":file_sha256(&exe)?,
        "build":{"os":std::env::consts::OS,"arch":std::env::consts::ARCH,"cuda_aoti":cfg!(feature="cuda-aoti"),"tensorrt":cfg!(feature="tensorrt")},
            "rules":arena::RULES,"admission":admission,
            "engine_tt_source_policy":c.engines.iter().enumerate().filter(|(_,e)| e.kind != "mcts").map(|(index,e)| serde_json::json!({
                "engine_index":index,"kind":e.kind,"requested_slots":requested_tt,
                "effective_slots_from_source":requested_tt.min(4096),"persistent_byte_cap_from_source":1048576,
                "actual_build_capacity":null,"actual_retained_bytes":null,
                "measurement":"source policy only; bind actual allocation in the software/runtime receipt"
            })).collect::<Vec<_>>(),
            "cpu_model":fs::read_to_string("/proc/cpuinfo").ok().and_then(|s| s.lines().find(|l| l.starts_with("model name")).map(str::to_owned)),
            "clock":{"origin":"monotonic, per game worker","start":"before session/limits setup","acceptance":"after legal replay immediately before state publication",
                "last_completed_iteration_timestamp":"after completed-depth full-history legal check, before caller deadline","persistent_session_completion_callback":true,"hard_realtime_guarantee":false,
                "internal_spans":"search elapsed nested in whole caller; startup/model load separate; do not sum",
                "cap_stop":"depth/node/K stop does not imply full clock consumption"},
            "cancel":{"mechanism":"runner guard AtomicBool, joined workers; external research-job handles exact process cleanup",
                "poll_ms":1,"forced_engine_return_guarantee":false},
            "limitations":["Single compiled search revision; versioned dual search adapter pending.","Timed Sigma waits for synchronous inference; no hard real-time guarantee. Completed simulations and alpha-beta depths are distinct.",
                "Legacy books have unknown lineage/selection; research uses explicit frozen provenance.","Deterministic repeats are not independent samples."]
        }),
    )
}
pub fn finish(c: &Config, report: &RunReport) -> Result<()> {
    let start: serde_json::Value =
        serde_json::from_slice(&fs::read(c.output.join("manifest-start.json"))?)?;
    let mut csv = String::from("game,family,candidate_color,started,status,winner,plies,failure\n");
    let mut observations = Vec::new();
    for o in &report.outcomes {
        let quote = |s: &str| format!("\"{}\"", s.replace('"', "\"\""));
        csv.push_str(&format!(
            "{},{},{},{},{},{},{},{}\n",
            o.game,
            quote(&o.family),
            o.candidate_color,
            o.started,
            o.status,
            o.winner.map_or(String::new(), |w| w.to_string()),
            o.plies,
            o.failure.map_or(String::new(), |f| format!("{f:?}"))
        ));
        for m in &o.observations {
            let row = serde_json::to_vec(&serde_json::json!({"game":o.game,"observation":m}))?;
            if observations.len().saturating_add(row.len() + 1) as u64 > c.max_output_bytes / 2 {
                return Err("bounded observation limit".into());
            }
            observations.extend(row);
            observations.push(b'\n');
        }
    }
    write_bytes(c, "games.csv", csv.as_bytes())?;
    // Existing system gzip, no Cargo dependency or downloaded runtime. Always reap the owned child.
    if crate::resources::directory_bytes(&c.output)?
        .saturating_add(observations.len() as u64 + 1024)
        > c.max_output_bytes
    {
        return Err("compressed observation output forecast limit".into());
    }
    let output = OpenOptions::new()
        .create_new(true)
        .write(true)
        .open(c.output.join("moves.jsonl.gz"))?;
    let mut gzip = Command::new("/usr/bin/gzip")
        .args(["-n", "-c"])
        .stdin(Stdio::piped())
        .stdout(Stdio::from(output))
        .stderr(Stdio::null())
        .spawn()?;
    let written = gzip
        .stdin
        .take()
        .ok_or("gzip stdin")
        .and_then(|mut p| p.write_all(&observations).map_err(|_| "gzip write"));
    if written.is_err() {
        let _ = gzip.kill();
    }
    let status = gzip.wait()?;
    written?;
    if !status.success() {
        return Err("gzip observation failure".into());
    }
    let mut artifacts = BTreeMap::new();
    for name in [
        "config.json",
        "planned.json",
        "admission.json",
        "evaluator-identities.json",
        "result.json",
        "completed.jsonl",
        "games.csv",
        "moves.jsonl.gz",
    ] {
        let p = c.output.join(name);
        if p.exists() {
            artifacts.insert(
                name,
                serde_json::json!({"sha256":file_sha256(&p)?,"bytes":fs::metadata(&p)?.len()}),
            );
        }
    }
    let identities = fs::read(c.output.join("evaluator-identities.json"))
        .ok()
        .and_then(|b| serde_json::from_slice::<serde_json::Value>(&b).ok());
    write(
        c,
        "manifest.json",
        &serde_json::json!({"binding":start,"artifacts":artifacts,
        "loaded_evaluators":identities,"result":report,"summary":report.arena_summary,
        "cleanup":{"all_workers_joined":report.all_workers_joined,"gzip_child_reaped":true},
        "evaluator_initialization_seconds":report.pump.evaluator_initialization_seconds,
        "backend_initialization_seconds":report.pump.backend_initialization_seconds,
        "model_warmup":report.pump.backend_work,
        "startup_cost":"evaluator load and backend initialization excluded from move clock, included in run wall budget",
        "counts":"complete pairs primary; secondary valid-game score excludes unknown; planned bound assigns every unknown 0 or 1"}),
    )
}

/// Read-only recovery/audit, without loading a model or executing a search.
pub fn audit(output: &Path) -> Result<crate::arena_statistics::Summary> {
    let manifest: serde_json::Value =
        serde_json::from_slice(&fs::read(output.join("manifest.json"))?)?;
    let binding = &manifest["binding"];
    if binding["schema"] != arena::SCHEMA {
        return Err("arena manifest schema".into());
    }
    let config: Config = serde_json::from_value(binding["config"].clone())?;
    // No live deadline check: this is a historical run, not execution admission.
    let mut historical = config.clone();
    historical.deadline_unix_ms = 0;
    historical.validate()?;
    let slots: Vec<Slot> = serde_json::from_value(binding["planned_slots"].clone())?;
    if slots.iter().any(|s| {
        s.game >= config.games
            || s.family != format!("{}-family-{:06}", config.run_id, s.game / 2)
            || config
                .arena
                .as_ref()
                .is_some_and(|a| s.opening != a.book.openings[s.game / 2].prefix)
    }) {
        return Err("planned slot/book correspondence mismatch".into());
    }
    let restored = self::slots(
        &config,
        &slots
            .iter()
            .map(|s| (s.game, s.family.clone(), s.opening.clone()))
            .collect::<Vec<_>>(),
    )?;
    if restored != slots {
        return Err("replayed slot metadata/history/Q mismatch".into());
    }
    if binding["config_sha256"] != arena::json_digest(&config)?
        || binding["planned_sha256"] != arena::json_digest(&slots)?
        || binding["book_sha256"]
            != serde_json::to_value(
                config
                    .arena
                    .as_ref()
                    .map(|a| arena::json_digest(&a.book))
                    .transpose()?,
            )?
    {
        return Err("config/book/planned binding mismatch".into());
    }
    let artifacts = manifest["artifacts"]
        .as_object()
        .ok_or("manifest artifacts")?;
    for name in [
        "config.json",
        "planned.json",
        "admission.json",
        "result.json",
        "games.csv",
        "moves.jsonl.gz",
    ] {
        if !artifacts.contains_key(name) {
            return Err("missing required artifact binding".into());
        }
    }
    for (name, v) in artifacts {
        if !matches!(
            name.as_str(),
            "config.json"
                | "planned.json"
                | "admission.json"
                | "evaluator-identities.json"
                | "result.json"
                | "completed.jsonl"
                | "games.csv"
                | "moves.jsonl.gz"
        ) {
            return Err("unknown artifact path".into());
        }
        let p = output.join(name);
        if v["sha256"] != file_sha256(&p)? || v["bytes"] != fs::metadata(p)?.len() {
            return Err(format!("artifact binding mismatch: {name}").into());
        }
    }
    let report: RunReport = serde_json::from_slice(&fs::read(output.join("result.json"))?)?;
    if report.run_id != config.run_id
        || report.planned != slots.len()
        || report.outcomes.len() != slots.len()
    {
        return Err("run census identity mismatch".into());
    }
    if serde_json::from_slice::<serde_json::Value>(&fs::read(output.join("config.json"))?)?
        != binding["config"]
        || serde_json::from_slice::<serde_json::Value>(&fs::read(output.join("planned.json"))?)?
            != binding["planned_slots"]
    {
        return Err("saved config/plan differs from bound values".into());
    }
    if serde_json::to_value(&report)? != manifest["result"] {
        return Err("result manifest mismatch".into());
    }
    for s in &slots {
        let replay = arena::replay(&s.opening);
        if replay.as_ref().ok() != s.replay.as_ref()
            || (replay.is_err() != s.replay_error.is_some())
        {
            return Err("planned replay/history mismatch".into());
        }
    }
    for o in &report.outcomes {
        if !o.started && arena::replay(&o.moves).is_err() {
            if o.status != "unknown"
                || !slots
                    .iter()
                    .any(|s| s.game == o.game && s.replay_error.is_some() && s.opening == o.moves)
            {
                return Err("invalid-prefix outcome mismatch".into());
            }
            continue;
        }
        let r = arena::replay(&o.moves)?;
        if o.started && r.total_ply != o.plies {
            return Err("outcome total ply mismatch".into());
        }
        if o.status == "unknown" {
            continue;
        }
        match o.status.as_str() {
            "goal" if r.winner == o.winner && r.terminal_value_stm.is_some_and(|v| v != 0.) => {}
            "draw" if r.terminal_value_stm == Some(0.) && o.winner.is_none() => {}
            "forfeit"
                if config
                    .arena
                    .as_ref()
                    .is_some_and(|a| a.clock_policy == arena::ClockPolicy::StrictForfeit)
                    && o.failure.is_some_and(crate::arena_clock::forfeitable)
                    && o.observations
                        .last()
                        .is_some_and(|m| !m.accepted && o.winner == Some(1 - m.side)) => {}
            _ => return Err("adjudication replay mismatch".into()),
        }
    }
    if let Some(a) = &config.arena {
        let identities = manifest["loaded_evaluators"].as_array();
        if report
            .stopped
            .as_ref()
            .is_none_or(|s| !s.starts_with("initialization"))
        {
            let actual = identities
                .ok_or("missing loaded model binding")?
                .iter()
                .map(|e| {
                    e["content_sha256"]
                        .as_str()
                        .map(str::to_owned)
                        .ok_or("loaded identity")
                })
                .collect::<std::result::Result<Vec<_>, _>>()?;
            arena::validate_loaded_bindings(
                a,
                &actual,
                &config
                    .engines
                    .iter()
                    .map(|e| {
                        binding["compiled_sources"][if e.kind == "mcts" {
                            "ai/sigma_mcts.rs"
                        } else {
                            "ai/alphabeta.rs"
                        }]
                        .as_str()
                        .map(str::to_owned)
                        .ok_or("search source identity")
                    })
                    .collect::<std::result::Result<Vec<_>, _>>()?,
            )?;
        }
    }
    let a = config.arena.as_ref();
    let summary = crate::arena_statistics::summarize(
        &slots,
        &report.outcomes,
        a.map_or(config.seed, |a| a.bootstrap_seed),
        a.map_or(2000, |a| a.bootstrap_resamples),
    )?;
    if summary.complete_pair_mean != report.score {
        return Err("primary score mismatch".into());
    }
    if serde_json::to_value(&summary)? != manifest["summary"] {
        return Err("summary mismatch".into());
    }
    Ok(summary)
}
pub fn recover(output: &Path) -> Result<serde_json::Value> {
    let start: serde_json::Value =
        serde_json::from_slice(&fs::read(output.join("manifest-start.json"))?)?;
    let config: Config = serde_json::from_value(start["config"].clone())?;
    let slots: Vec<Slot> = serde_json::from_value(start["planned_slots"].clone())?;
    if start["config_sha256"] != arena::json_digest(&config)?
        || start["planned_sha256"] != arena::json_digest(&slots)?
    {
        return Err("recovery manifest binding mismatch".into());
    }
    let path = output.join("completed.jsonl");
    let mut historical = config.clone();
    historical.deadline_unix_ms = 0;
    historical.validate()?;
    if slots.len() != config.games
        || slots.iter().any(|s| {
            s.game >= config.games
                || s.family != format!("{}-family-{:06}", config.run_id, s.game / 2)
                || config
                    .arena
                    .as_ref()
                    .is_some_and(|a| s.opening != a.book.openings[s.game / 2].prefix)
        })
    {
        return Err("recovery plan/book mismatch".into());
    }
    let restored = self::slots(
        &config,
        &slots
            .iter()
            .map(|s| (s.game, s.family.clone(), s.opening.clone()))
            .collect::<Vec<_>>(),
    )?;
    if restored != slots {
        return Err("recovery history/Q mismatch".into());
    }
    let mut outcomes = Vec::new();
    let mut partial_tail = false;
    if path.exists() {
        if fs::metadata(&path)?.len() > config.max_output_bytes {
            return Err("recovery journal exceeds bound".into());
        }
        let journal = fs::read(path)?;
        for row in journal.split_inclusive(|&b| b == b'\n') {
            if row.last() != Some(&b'\n') {
                partial_tail = true;
                break;
            }
            outcomes.push(serde_json::from_slice::<crate::runtime::Outcome>(row)?);
        }
    }
    // summarize fills absent planned slots as unknown, validates unique slots/history/side.
    let a = config.arena.as_ref();
    let summary = crate::arena_statistics::summarize(
        &slots,
        &outcomes,
        a.map_or(config.seed, |a| a.bootstrap_seed),
        a.map_or(2000, |a| a.bootstrap_resamples),
    )?;
    let observed: std::collections::BTreeSet<_> = outcomes.iter().map(|o| o.game).collect();
    Ok(
        serde_json::json!({"schema":arena::SCHEMA,"finalized":false,"partial_journal_tail":partial_tail,
        "observed_outcomes":outcomes,"missing_slots":slots.iter().filter(|s|!observed.contains(&s.game)).collect::<Vec<_>>(),"summary":summary,
        "limitations":["Recovery is a read-only census of durable complete journal records, not final run acceptance.",
            "Started count is observed only; missing slots may have started before interruption.","No resume, new search, interval stopping rule or overwrite is performed."]}),
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn reconstructs_sibling_history_and_invalid_prefix_without_engine_execution() {
        let mut c: Config =
            serde_json::from_str(include_str!("../../../configs/arena/smoke.json")).unwrap();
        let family = format!("{}-family-000000", c.run_id);
        let prefix = c.arena.as_ref().unwrap().book.openings[0].prefix.clone();
        let planned = vec![
            (0, family.clone(), prefix.clone()),
            (1, family.clone(), prefix),
        ];
        let pair = slots(&c, &planned).unwrap();
        assert_eq!(pair[0].replay, pair[1].replay);
        assert_eq!(pair[0].candidate_color, 0);
        assert_eq!(pair[1].candidate_color, 1);
        c.arena.as_mut().unwrap().book.openings[0].prefix = vec![999];
        let invalid = slots(
            &c,
            &[(0, family.clone(), vec![999]), (1, family, vec![999])],
        )
        .unwrap();
        assert!(
            invalid
                .iter()
                .all(|s| s.replay.is_none() && s.replay_error.is_some())
        );
    }
    #[test]
    fn recovery_keeps_unique_slots_partial_pair_unknown_and_incomplete_tail() {
        let mut c: Config =
            serde_json::from_str(include_str!("../../../configs/arena/smoke.json")).unwrap();
        c.output = std::env::temp_dir().join(format!(
            "arena-journal-{}-{}",
            std::process::id(),
            crate::config::unix_ms()
        ));
        fs::create_dir(&c.output).unwrap();
        let family = format!("{}-family-000000", c.run_id);
        let prefix = c.arena.as_ref().unwrap().book.openings[0].prefix.clone();
        let planned = slots(
            &c,
            &[
                (0, family.clone(), prefix.clone()),
                (1, family.clone(), prefix.clone()),
            ],
        )
        .unwrap();
        write(&c,"manifest-start.json",&serde_json::json!({"schema":arena::SCHEMA,"config":c,"config_sha256":arena::json_digest(&c).unwrap(),"planned_slots":planned,"planned_sha256":arena::json_digest(&planned).unwrap()})).unwrap();
        let mut moves = prefix;
        moves.push(76);
        let o = crate::runtime::Outcome {
            game: 0,
            family,
            candidate_color: 0,
            status: "goal".into(),
            winner: Some(0),
            plies: 15,
            reason: Some("goal".into()),
            nn_calls: 0,
            moves,
            persistent_tt: Vec::new(),
            advance_calls: 0,
            terminal_no_nn: 0,
            allocated_nodes_peak: 0,
            started: true,
            failure: None,
            observations: Vec::new(),
        };
        journal(&c, &o).unwrap();
        let r = recover(&c.output).unwrap();
        assert_eq!(r["finalized"], false);
        assert_eq!(r["summary"]["census"]["complete_pairs"], 0);
        assert_eq!(r["summary"]["census"]["unknown_games"], 1);
        assert_eq!(r["missing_slots"][0]["game"], 1);
        let mut f = OpenOptions::new()
            .append(true)
            .open(c.output.join("completed.jsonl"))
            .unwrap();
        f.write_all(b"{\"game\":1").unwrap();
        drop(f);
        assert_eq!(recover(&c.output).unwrap()["partial_journal_tail"], true);
        fs::write(
            c.output.join("completed.jsonl"),
            format!(
                "{}\n{}\n",
                serde_json::to_string(&o).unwrap(),
                serde_json::to_string(&o).unwrap()
            ),
        )
        .unwrap();
        assert!(recover(&c.output).is_err());
        fs::remove_dir_all(c.output).unwrap();
    }
}

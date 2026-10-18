//! One binding manifest for configuration, replay, implementation and the whole slot census.
use crate::{arena, arena_statistics::Slot, config::Config, runtime::RunReport};
use quoridor_data::Result;
use serde::Serialize;
use sha2::{Digest, Sha256};
use std::{
    collections::BTreeMap,
    fs::{self, File, OpenOptions},
    io::{BufRead, BufReader, Read, Write},
    path::Path,
};

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
            let width = c
                .arena
                .as_ref()
                .map_or(2, |a| if a.decision_only { 1 } else { 2 });
            let metadata = c.arena.as_ref().map(|a| &a.book.openings[game / width]);
            let replay = arena::replay(opening, c.ruleset);
            let reference_q_stm = metadata
                .and_then(|m| m.reference.as_ref())
                .and_then(|r| replay.as_ref().ok().and_then(|p| r.q_stm(p.turn)));
            Ok(Slot {
                game: *game,
                family: family.clone(),
                candidate_color: if c.arena.as_ref().is_some_and(|a| a.decision_only) {
                    0
                } else {
                    crate::value_search_strength::candidate_color(c, *game)
                },
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
    // One retained archive plus the bounded live journal, not three retained reports.
    let raw = (c.games as u64).saturating_mul(outcome_cap(c).saturating_add(1));
    let needed = metadata
        .saturating_mul(6)
        .saturating_add(8 * 1024 * 1024)
        .saturating_add(raw)
        .saturating_add(archive_cap(raw));
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
    crate::value_search_strength::retained_outcome(c, outcome)?;
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
    let requested_tt_byte_cap =
        quoridor_ai::alphabeta::SearchSession::requested_tt_byte_limit(requested_tt)?;
    let main_owned = c
        .arena
        .as_ref()
        .is_some_and(|a| a.comparison == arena::Comparison::WholeWallTime);
    write(
        c,
        "manifest-start.json",
        &serde_json::json!({
        "schema":arena::SCHEMA,
            "run_id":c.run_id,"config":c,"config_sha256":arena::json_digest(c)?,
            "book_sha256":c.arena.as_ref().map(|a| arena::json_digest(&a.book)).transpose()?,
            "planned_slots":slots,"planned_sha256":arena::json_digest(&slots)?,
        "executable":exe,"executable_sha256":file_sha256(&exe)?,
        "build":{"os":std::env::consts::OS,"arch":std::env::consts::ARCH,"cuda_aoti":cfg!(feature="cuda-aoti"),"tensorrt":cfg!(feature="tensorrt")},
            "rules":c.ruleset.id(),"admission":admission,
            "engine_tt_source_policy":c.engines.iter().enumerate().filter(|(_,e)| e.kind != "mcts").map(|(index,e)| serde_json::json!({
                "engine_index":index,"kind":e.kind,"requested_slots":requested_tt,
                "effective_slots_from_source":requested_tt,"persistent_byte_cap_from_source":requested_tt_byte_cap,
                "actual_build_capacity":null,"actual_retained_bytes":null,
                "measurement":"requested slots and canonical Table ABI-derived byte limit; actual allocation/retained bytes require admitted per-game TT profiles and runtime receipt"
            })).collect::<Vec<_>>(),
            "cpu_model":fs::read_to_string("/proc/cpuinfo").ok().and_then(|s| s.lines().find(|l| l.starts_with("model name")).map(str::to_owned)),
            "clock":{"origin":if main_owned {"monotonic, main-owned game"} else {"monotonic, per game worker"},"start":if main_owned {"main before turn dispatch/session/limits setup"} else {"before session/limits setup"},"acceptance":if main_owned {"actual main receipt before100ms; legal replay and terminal collection before state commit"} else {"after legal replay immediately before state publication"},
                "last_completed_iteration_timestamp":if main_owned {"actual main receipt of immutable completed result before decision cutoff"} else {"after completed-depth full-history legal check, before caller deadline"},"persistent_session_completion_callback":true,"hard_realtime_guarantee":false,
                "internal_spans":"search elapsed nested in whole caller; startup/model load separate; do not sum",
                "cap_stop":"depth/node/K stop does not imply full clock consumption"},
            "cancel":{"mechanism":"runner guard AtomicBool, joined workers; external research-job handles exact process cleanup",
                "poll_ms":1,"forced_engine_return_guarantee":false},
            "limitations":["Single compiled search revision; versioned dual search adapter pending.",if main_owned {"AI worker synchronous ORT is not preemptible. Main deadline response and actual terminal collection are distinct; no next turn before terminal. Completed simulations and alpha-beta depths are distinct."} else {"Timed Sigma waits for synchronous inference; no hard real-time guarantee. Completed simulations and alpha-beta depths are distinct."},
                "Legacy books have unknown lineage/selection; research uses explicit frozen provenance.","Deterministic repeats are not independent samples."]
        }),
    )
}
pub const PUBLICATION_SCHEMA: &str = "quoridor.arena.reference-result.v1";
fn outcome_cap(c: &Config) -> u64 {
    c.arena
        .as_ref()
        .and_then(|a| a.retained_outcome_bytes)
        .map_or(
            (c.max_plies as u64)
                .saturating_mul(16384)
                .saturating_add(16384),
            |v| v as u64,
        )
}
/// Hard output allowance, including expansion/framing; exceeding it is failure, not truncation.
fn archive_cap(raw: u64) -> u64 {
    raw.saturating_add(raw.div_ceil(8192).saturating_mul(5))
        .saturating_add(64)
}
#[derive(Serialize, serde::Deserialize)]
#[serde(deny_unknown_fields)]
struct Publication {
    schema: String,
    report: RunReport,
    archive: quoridor_data::lossless_jsonl::Content,
    outcome_count: usize,
    journal_count: usize,
    journal_bytes: u64,
    journal_sha256: String,
    failure_attribution: Option<crate::arena_clock::Failure>,
    archive_wall_seconds: f64,
    archive_allocated_bytes: u64,
}
fn line(reader: &mut impl BufRead, cap: u64) -> Result<Vec<u8>> {
    let mut bytes = Vec::new();
    reader
        .take(cap.saturating_add(2))
        .read_until(b'\n', &mut bytes)?;
    if !bytes.is_empty() && (bytes.len() as u64 > cap + 1 || bytes.last() != Some(&b'\n')) {
        return Err("torn/oversize outcome journal record".into());
    }
    Ok(bytes)
}
fn outcome_value(outcome: &crate::runtime::Outcome) -> Result<serde_json::Value> {
    Ok(serde_json::to_value(outcome)?)
}
/// Reconstruct only the two defined final-primary failure attributions. Raw journal bytes stay exact.
fn final_outcome(mut o: crate::runtime::Outcome, stopped: Option<&str>) -> crate::runtime::Outcome {
    if let Some(reason) = stopped {
        crate::runtime::attach_primary_failure(&mut o, reason);
    }
    o
}
fn archive(c: &Config, report: &RunReport) -> Result<Publication> {
    let started = std::time::Instant::now();
    if report.planned != c.games || report.outcomes.len() != c.games {
        return Err("full planned outcome denominator required before archive publication".into());
    }
    let expected = report
        .outcomes
        .iter()
        .map(|o| (o.game, o))
        .collect::<BTreeMap<_, _>>();
    if expected.len() != c.games || expected.keys().copied().ne(0..c.games) {
        return Err("duplicate/missing/unplanned final outcomes".into());
    }
    let raw_cap = (c.games as u64)
        .checked_mul(outcome_cap(c).saturating_add(1))
        .ok_or("archive raw cap overflow")?;
    if crate::resources::directory_bytes(&c.output)?.saturating_add(archive_cap(raw_cap))
        > c.max_output_bytes
    {
        return Err("canonical archive live-overlap bound".into());
    }
    let mut writer = quoridor_data::lossless_jsonl::Writer::create(
        &c.output.join("completed.jsonl.gz"),
        raw_cap,
        archive_cap(raw_cap),
    )?;
    let raw_path = c.output.join("completed.jsonl");
    let mut seen = std::collections::BTreeSet::new();
    let mut journal_hash = Sha256::new();
    let mut journal_bytes = 0u64;
    if raw_path.exists() {
        if fs::symlink_metadata(&raw_path)?.file_type().is_symlink()
            || fs::metadata(&raw_path)?.len() > raw_cap
        {
            return Err("raw journal type/upper".into());
        }
        let mut reader = BufReader::new(File::open(&raw_path)?);
        loop {
            let bytes = line(&mut reader, outcome_cap(c))?;
            if bytes.is_empty() {
                break;
            }
            let original: crate::runtime::Outcome = serde_json::from_slice(&bytes)?;
            let game = original.game;
            let final_record = expected.get(&game).ok_or("unplanned raw journal game")?;
            if !seen.insert(game)
                || outcome_value(final_record)?
                    != outcome_value(&final_outcome(original.clone(), report.stopped.as_deref()))?
            {
                return Err("journal/final outcome correspondence".into());
            }
            crate::value_search_strength::retained_outcome(c, &original)?;
            journal_hash.update(&bytes);
            journal_bytes = journal_bytes
                .checked_add(bytes.len() as u64)
                .ok_or("journal bytes overflow")?;
            writer.append(&bytes)?;
        }
        if journal_bytes != fs::metadata(&raw_path)?.len()
            || format!("{:x}", journal_hash.clone().finalize()) != file_sha256(&raw_path)?
        {
            return Err("raw journal changed during archival".into());
        }
    }
    let journal_count = seen.len();
    for o in &report.outcomes {
        if seen.insert(o.game) {
            if o.started || o.status != "unknown" {
                return Err("unjournaled started outcome cannot become durable completion".into());
            }
            crate::value_search_strength::retained_outcome(c, o)?;
            let mut bytes = serde_json::to_vec(o)?;
            bytes.push(b'\n');
            writer.append(&bytes)?;
        }
    }
    let content = writer.finish()?;
    quoridor_data::lossless_jsonl::verify(&content)?;
    let mut metadata = serde_json::to_value(report)?;
    metadata["outcomes"] = serde_json::json!([]);
    use std::os::unix::fs::MetadataExt;
    let archive_allocated_bytes = fs::metadata(&content.compressed.path)?
        .blocks()
        .saturating_mul(512);
    let publication = Publication {
        schema: PUBLICATION_SCHEMA.into(),
        report: serde_json::from_value(metadata)?,
        archive: content,
        outcome_count: report.outcomes.len(),
        journal_count,
        journal_bytes,
        journal_sha256: format!("{:x}", journal_hash.finalize()),
        archive_wall_seconds: started.elapsed().as_secs_f64(),
        archive_allocated_bytes,
        failure_attribution: report
            .stopped
            .as_deref()
            .map(crate::arena_clock::failure_from_reason),
    };
    if serde_json::to_value(decode(c, &publication)?)? != serde_json::to_value(report)? {
        return Err("closed archive/final report roundtrip differs".into());
    }
    Ok(publication)
}
fn decode(c: &Config, publication: &Publication) -> Result<RunReport> {
    let raw_cap = (c.games as u64).saturating_mul(outcome_cap(c).saturating_add(1));
    if !publication.archive_wall_seconds.is_finite()
        || publication.archive_wall_seconds < 0.0
        || publication.schema != PUBLICATION_SCHEMA
        || !publication.report.outcomes.is_empty()
        || publication.report.planned != c.games
        || publication.report.run_id != c.run_id
        || publication.failure_attribution
            != publication
                .report
                .stopped
                .as_deref()
                .map(crate::arena_clock::failure_from_reason)
        || publication.outcome_count != c.games
        || publication.journal_count > c.games
        || publication.archive.compressed.path != c.output.join("completed.jsonl.gz")
        || publication.archive.raw_bytes > raw_cap
        || publication.archive.compressed.bytes > archive_cap(raw_cap)
    {
        return Err("reference report/schema/census/owned archive binding".into());
    }
    let mut reader = BufReader::new(quoridor_data::lossless_jsonl::Reader::open(
        &publication.archive,
    )?);
    let mut outcomes = BTreeMap::new();
    let mut raw_count = 0usize;
    let mut prefix_bytes = 0u64;
    let mut prefix_hash = Sha256::new();
    loop {
        let bytes = line(&mut reader, outcome_cap(c))?;
        if bytes.is_empty() {
            break;
        }
        if raw_count >= c.games {
            return Err("extra archived outcome".into());
        }
        let original: crate::runtime::Outcome = serde_json::from_slice(&bytes)?;
        crate::value_search_strength::retained_outcome(c, &original)?;
        if raw_count < publication.journal_count {
            prefix_bytes += bytes.len() as u64;
            prefix_hash.update(&bytes);
        } else if original.started || original.status != "unknown" {
            return Err("missing-at-journal publication cannot manufacture a played result".into());
        }
        let final_o = final_outcome(original, publication.report.stopped.as_deref());
        if final_o.game >= c.games || outcomes.insert(final_o.game, final_o).is_some() {
            return Err("duplicate/unplanned archived outcome".into());
        }
        raw_count += 1;
    }
    if raw_count != publication.outcome_count
        || prefix_bytes != publication.journal_bytes
        || format!("{:x}", prefix_hash.finalize()) != publication.journal_sha256
    {
        return Err("archive count/raw journal prefix mismatch".into());
    }
    let mut report: RunReport = serde_json::from_value(serde_json::to_value(&publication.report)?)?;
    report.outcomes = outcomes.into_values().collect();
    Ok(report)
}
/// The normal saved-result reader joins closed detailed facts; metadata alone is never completion.
pub fn read_report(output: &Path) -> Result<RunReport> {
    let c: Config = serde_json::from_slice(&fs::read(output.join("config.json"))?)?;
    if c.output != output || fs::metadata(output.join("result.json"))?.len() > 1024 * 1024 {
        return Err("owned bounded saved report".into());
    }
    let publication: Publication = serde_json::from_slice(&fs::read(output.join("result.json"))?)?;
    decode(&c, &publication)
}
/// Failure-only reconstruction: use the same bounded journal row/attribution ports.
/// A torn/absent/untrusted row is never a canonical completion or a reason to replay.
fn failure_facts(c: &Config, report: &RunReport) -> Result<serde_json::Value> {
    let mut metadata = serde_json::to_value(report)?;
    metadata["outcomes"] = serde_json::json!([]);
    let census = report.outcomes.iter().map(|o| serde_json::json!({
        "game":o.game,"family":o.family,"candidate_color":o.candidate_color,"started":o.started,
        "status":o.status,"winner":o.winner,"plies":o.plies,"reason":o.reason,"failure":o.failure
    })).collect::<Vec<_>>();
    let mut recoverable = std::collections::BTreeSet::new();
    let mut seen = std::collections::BTreeSet::new();
    let raw = c.output.join("completed.jsonl");
    let raw_cap = (c.games as u64).saturating_mul(outcome_cap(c).saturating_add(1));
    let recovery: Result<()> = (|| {
        let info = match fs::symlink_metadata(&raw) {
            Ok(info) => info,
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(()),
            Err(error) => return Err(error.into()),
        };
        if !info.is_file() || info.file_type().is_symlink() || info.len() > raw_cap {
            return Err("failure journal type/upper; raw retained".into());
        }
        let mut reader = BufReader::new(File::open(&raw)?);
        loop {
            let bytes = line(&mut reader, outcome_cap(c))?;
            if bytes.is_empty() {
                break;
            }
            let original: crate::runtime::Outcome = serde_json::from_slice(&bytes)?;
            let game = original.game;
            if !seen.insert(game) {
                recoverable.remove(&game);
                return Err("duplicate failed journal record; raw retained".into());
            }
            let mut matching = report.outcomes.iter().filter(|o| o.game == game);
            if let Some(outcome) = matching.next()
                && matching.next().is_none()
                && outcome_value(outcome)?
                    == outcome_value(&final_outcome(original, report.stopped.as_deref()))?
                && !report
                    .pump
                    .publication_failures
                    .iter()
                    .any(|f| f.game == Some(game))
            {
                recoverable.insert(game);
            }
        }
        Ok(())
    })();
    // Complete bytes with a known failed append/sync are also retained here: the
    // failed writer did not establish durable custody. Other matched rows need no copy.
    let available = report
        .outcomes
        .iter()
        .filter(|o| !recoverable.contains(&o.game))
        .collect::<Vec<_>>();
    let detail_bytes = serde_json::to_vec(&available)?.len() as u64;
    if detail_bytes > raw_cap.saturating_add(2) {
        return Err("failure-only available-detail upper; original in-memory report retained by error funnel".into());
    }
    Ok(serde_json::json!({
        "schema":PUBLICATION_SCHEMA,"closed_archive":false,"report":metadata,
        "planned_outcome_census":census,"available_outcomes":available,
        "available_detail_bytes":detail_bytes,"available_detail_upper_B":raw_cap.saturating_add(2),
        "recoverable_journal_games":recoverable,"journal_recovery_error":recovery.err().map(|e|e.to_string()),
        "detail_status":"FAILED_OR_UNKNOWN; failed-only available facts plus retained raw/partial archive; no salvage PASS"
    }))
}
pub fn save_failure(c: &Config, report: &RunReport) -> Result<()> {
    write(c, "publication-failure.json", &failure_facts(c, report)?)
}
pub fn finish(c: &Config, report: &RunReport) -> Result<()> {
    let publication = archive(c, report)?;
    let start: serde_json::Value =
        serde_json::from_slice(&fs::read(c.output.join("manifest-start.json"))?)?;
    let mut csv = String::from("game,family,candidate_color,started,status,winner,plies,failure\n");
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
    }
    write_bytes(c, "games.csv", csv.as_bytes())?;
    write(c, "result.json", &publication)?;
    let mut artifacts = BTreeMap::new();
    for name in [
        "config.json",
        "planned.json",
        "admission.json",
        "evaluator-identities.json",
        "result.json",
        "completed.jsonl.gz",
        "games.csv",
    ] {
        let p = c.output.join(name);
        if p.exists() {
            use std::os::unix::fs::PermissionsExt;
            artifacts.insert(name, serde_json::json!({"sha256":file_sha256(&p)?,
                "bytes":fs::metadata(&p)?.len(),"mode":format!("{:04o}", fs::metadata(&p)?.permissions().mode() & 0o7777)}));
        }
    }
    let identities = fs::read(c.output.join("evaluator-identities.json"))
        .ok()
        .and_then(|b| serde_json::from_slice::<serde_json::Value>(&b).ok());
    write(
        c,
        "manifest.json",
        &serde_json::json!({"binding":start,"artifacts":artifacts,
        "loaded_evaluators":identities,"result":publication,"summary":report.arena_summary,
        "cleanup":{"all_workers_joined":report.all_workers_joined,"archive_closed_verified":true},
        "evaluator_initialization_seconds":report.pump.evaluator_initialization_seconds,
        "backend_initialization_seconds":report.pump.backend_initialization_seconds,
        "model_warmup":report.pump.backend_work,
        "startup_cost":"evaluator load and backend initialization excluded from move clock, included in run wall budget",
        "counts":"complete pairs primary; every missing/capped/failed slot stays UNKNOWN"}),
    )?;
    // Only our transient live journal: exact decoded prefix was verified, both updated references
    // fsynced, and this function owns all its readers. Irreproducible failed files stay on any error.
    File::open(&c.output)?.sync_all()?;
    let raw = c.output.join("completed.jsonl");
    if raw.exists() {
        if fs::metadata(&raw)?.len() != publication.journal_bytes
            || file_sha256(&raw)? != publication.journal_sha256
        {
            return Err("live journal retirement correspondence drift".into());
        }
        fs::remove_file(raw)?;
        File::open(&c.output)?.sync_all()?;
    }
    Ok(())
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
        "completed.jsonl.gz",
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
                | "games.csv"
                | "completed.jsonl.gz"
        ) {
            return Err("unknown artifact path".into());
        }
        let p = output.join(name);
        if v["sha256"] != file_sha256(&p)? || v["bytes"] != fs::metadata(p)?.len() {
            return Err(format!("artifact binding mismatch: {name}").into());
        }
    }
    let report = read_report(output)?;
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
    if serde_json::from_slice::<serde_json::Value>(&fs::read(output.join("result.json"))?)?
        != manifest["result"]
    {
        return Err("result manifest mismatch".into());
    }
    if binding["rules"] != config.ruleset.id() {
        return Err("ruleset binding mismatch".into());
    }
    for s in &slots {
        let replay = arena::replay(&s.opening, config.ruleset);
        if replay.as_ref().ok() != s.replay.as_ref()
            || (replay.is_err() != s.replay_error.is_some())
        {
            return Err("planned replay/history mismatch".into());
        }
    }
    for o in &report.outcomes {
        if !o.started && arena::replay(&o.moves, config.ruleset).is_err() {
            if o.status != "unknown"
                || !slots
                    .iter()
                    .any(|s| s.game == o.game && s.replay_error.is_some() && s.opening == o.moves)
            {
                return Err("invalid-prefix outcome mismatch".into());
            }
            continue;
        }
        let r = arena::replay(&o.moves, config.ruleset)?;
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
                    .map(|_| {
                        binding["executable_sha256"]
                            .as_str()
                            .map(str::to_owned)
                            .ok_or("search artifact identity")
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
    if output.join("manifest.json").exists() {
        let summary = audit(output)?;
        return Ok(serde_json::json!({"schema":arena::SCHEMA,"finalized":true,
            "summary":summary,"result_reference":output.join("result.json"),
            "scope":"closed archive audited; no model/search or new scientific run"}));
    }

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
    fn three_engine_374_lossless_reference_publication_partial_torn_and_io_refuse() {
        // File/codec/publication only: no evaluator, geometry, search or child process.
        let mut c: Config =
            serde_json::from_str(include_str!("../../../configs/arena/smoke.json")).unwrap();
        c.games = 2;
        c.max_output_bytes = 16 * 1024 * 1024;
        c.output = std::env::temp_dir().join(format!(
            "reference374-{}-{}",
            std::process::id(),
            crate::config::unix_ms()
        ));
        fs::create_dir(&c.output).unwrap();
        write(&c, "config.json", &c).unwrap();
        write(&c, "manifest-start.json", &serde_json::json!({"config":c})).unwrap();
        let original = crate::runtime::Outcome {
            game: 0,
            family: "synthetic-original-family".into(),
            candidate_color: 0,
            status: "unknown".into(),
            winner: None,
            plies: 1,
            reason: Some("original error with exact bytes".into()),
            nn_calls: 0,
            moves: vec![13],
            persistent_tt: vec![],
            advance_calls: 0,
            terminal_no_nn: 0,
            allocated_nodes_peak: 0,
            started: false,
            failure: Some(crate::arena_clock::Failure::Cancelled),
            observations: vec![],
        };
        journal(&c, &original).unwrap();
        let original_bytes = fs::read(c.output.join("completed.jsonl")).unwrap();
        let mut missing = original.clone();
        missing.game = 1;
        missing.failure = Some(crate::arena_clock::Failure::NotStarted);
        let stopped = Some("inference:first primary".to_string());
        let mut pump = crate::runtime::PumpProfile::default();
        pump.publication_failures
            .push(crate::runtime::PublicationFailure {
                game: None,
                reason: "first IO".into(),
            });
        pump.publication_failures
            .push(crate::runtime::PublicationFailure {
                game: Some(0),
                reason: "secondary sync".into(),
            });
        let report = RunReport {
            schema: arena::SCHEMA.into(),
            run_id: c.run_id.clone(),
            planned: 2,
            outcomes: vec![
                final_outcome(original, stopped.as_deref()),
                final_outcome(missing, stopped.as_deref()),
            ],
            rows: 0,
            eligible_rows: 0,
            nn_calls: 0,
            actual_batches: BTreeMap::new(),
            wall_seconds: 1.0,
            inference_seconds: 0.0,
            peak_rss: 0,
            stopped,
            dataset: None,
            score: None,
            model_sha: None,
            process_id: std::process::id(),
            all_workers_joined: true,
            pump,
            arena_summary: None,
        };
        finish(&c, &report).unwrap();
        assert!(!c.output.join("completed.jsonl").exists());
        assert!(!c.output.join("moves.jsonl.gz").exists());
        let mut publication: Publication =
            serde_json::from_slice(&fs::read(c.output.join("result.json")).unwrap()).unwrap();
        assert!(publication.report.outcomes.is_empty());
        assert_eq!(publication.journal_count, 1);
        assert_eq!(publication.journal_sha256, arena::digest(&original_bytes));
        assert_eq!(
            serde_json::to_value(read_report(&c.output).unwrap()).unwrap(),
            serde_json::to_value(&report).unwrap()
        );
        assert_eq!(publication.report.pump.publication_failures.len(), 2);
        // A rewritten FileRef cannot make a torn codec footer become valid detailed data.
        let gz = c.output.join("completed.jsonl.gz");
        let mut bytes = fs::read(&gz).unwrap();
        bytes.truncate(bytes.len() - 3);
        fs::write(&gz, &bytes).unwrap();
        publication.archive.compressed.bytes = bytes.len() as u64;
        publication.archive.compressed.sha256 = file_sha256(&gz).unwrap();
        assert!(decode(&c, &publication).is_err());
        // No second publication/overwrite can salvage it.
        assert!(finish(&c, &report).is_err());
        let first_output = c.output.clone();
        c.output = first_output.join("torn-live");
        fs::create_dir(&c.output).unwrap();
        fs::write(c.output.join("completed.jsonl"), b"{\"game\":0").unwrap();
        assert!(archive(&c, &report).is_err());
        assert_eq!(
            fs::read(c.output.join("completed.jsonl")).unwrap(),
            b"{\"game\":0"
        );
        c.output = first_output.join("IO-refusal");
        fs::create_dir(&c.output).unwrap();
        c.max_output_bytes = 1;
        assert!(archive(&c, &report).is_err());
        assert!(!c.output.join("result.json").exists());
        fs::remove_dir_all(first_output).unwrap();
    }
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

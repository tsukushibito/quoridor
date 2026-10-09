//! Prospective target-blind starts and fixed paired schedule. No evaluator is used here.
use crate::{arena, config::Config, runtime::Rng};
use quoridor_core::research::{HistoryKey, Ruleset, SigmaContext};
use quoridor_data::Result;
use serde::{Deserialize, Serialize};
use std::collections::BTreeSet;

pub const SCHEMA: &str = "quoridor.value-search-strength.book.v1";
pub const PLAN_SHA256: &str = "b3e41602eeed250d120444cf65783012e87f8b5f860bef2862c7aac5fd9c24b2";
pub const OLD_PREFIX_SHA256: &str =
    "be50f486ccfdef3ae1c1bddde33d8369398a19c2a6ccd3d3324b64863f322dbc";
pub const FAMILIES: usize = 128;
pub const SEED: u64 = 35520261009;
pub const ATTEMPTS_PER_FAMILY: usize = 8;
pub const OBSERVATION_BYTES: usize = 3072;
pub const OUTCOME_BYTES: usize = 200 * OBSERVATION_BYTES + 16384;
pub const BATCH_OUTPUT_BYTES: u64 = 96 * 1024 * 1024;
pub const CONTROL_OUTPUT_BYTES: u64 = 4 * 1024 * 1024;
pub const BEST51_WEIGHTS: &str = "9ca438e43b0c105ac5f802a302946f2ba71623ea2bc443b9c54cc9a8468b75b0";
pub const BEST43_WEIGHTS: &str = "046fe926e56b955b0fb7de8f147a74ec33eace9cbc00a55c307f9b6541ab9841";
/// Approved complete353 manifests and actual returned evaluator fingerprints, BEST51 then BEST43.
/// These cover scaler, distance_fit and route metadata as well as unchanged weight bytes.
pub const APPROVED_DESCRIPTOR_SHA256: [&str; 2] = [
    "c4712e0872b6831e33fcf59b99d9d7f774d18a3e8d5236d7923ba65e64aabc39",
    "46ec2c4708f96dcf9fad579c2fb0d1299c6663df27412f0faac98267467715e1",
];
pub const APPROVED_EVALUATOR_SHA256: [&str; 2] = [
    "519410ed5eb0b340d1d25df8626d67f508bee7706cbd4ba8a7175bf4e613e645",
    "96a5f41f875022d1752b9c999595ad58bfb2d42687a8f06de08d42b1c4215875",
];

fn approved_model_identity(
    index: usize,
    descriptor_sha256: &str,
    evaluator_sha256: &str,
) -> Result<()> {
    if index >= 2
        || descriptor_sha256 != APPROVED_DESCRIPTOR_SHA256[index]
        || evaluator_sha256 != APPROVED_EVALUATOR_SHA256[index]
    {
        return Err("CAMPAIGN_APPROVED_FULL_DESCRIPTOR_AND_EVALUATOR_REQUIRED".into());
    }
    Ok(())
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct GenerationRequest {
    pub plan: crate::sigma_qualification::BoundControl,
    pub old_admission: crate::sigma_qualification::BoundControl,
    pub output: std::path::PathBuf,
}
fn bounded_read<T: serde::de::DeserializeOwned>(
    b: &crate::sigma_qualification::BoundControl,
) -> Result<T> {
    if std::fs::symlink_metadata(&b.path)?.file_type().is_symlink()
        || std::fs::metadata(&b.path)?.len() > 1024 * 1024
    {
        return Err("CAMPAIGN_CONTROL_FILE_LIMIT_OR_SYMLINK".into());
    }
    b.read()
}
fn write_new(output: &std::path::Path, name: &str, value: &impl Serialize) -> Result<()> {
    use std::io::Write;
    let bytes = serde_json::to_vec(value)?;
    if crate::resources::directory_bytes(output)?
        .checked_add(bytes.len() as u64)
        .is_none_or(|n| n > CONTROL_OUTPUT_BYTES)
    {
        return Err("CAMPAIGN_CONTROL_OUTPUT_LIMIT".into());
    }
    let mut f = std::fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(output.join(name))?;
    f.write_all(&bytes)?;
    f.sync_all()?;
    Ok(())
}
/// The external owned job must hold the supported source/private/whole-phase lifetime lease.
/// This inlet independently checks physical admission before any geometric generation.
pub fn generate_bound(request: GenerationRequest) -> Result<serde_json::Value> {
    if request.plan.sha256 != PLAN_SHA256 {
        return Err("CAMPAIGN_FIXED_PLAN".into());
    }
    let _: serde_json::Value = bounded_read(&request.plan)?;
    let old: serde_json::Value = bounded_read(&request.old_admission)?;
    let openings = old["frozen_arena_config"]["arena"]["book"]["openings"]
        .as_array()
        .ok_or("CAMPAIGN_OLD_BOOK_POINTER")?;
    let prefixes: Vec<Vec<u16>> = openings
        .iter()
        .map(|o| serde_json::from_value(o["prefix"].clone()))
        .collect::<std::result::Result<_, _>>()?;
    if arena::json_digest(&prefixes)? != OLD_PREFIX_SHA256 {
        return Err("CAMPAIGN_EXACT_OLD_OPEN8".into());
    }
    let admission = crate::resources::admit(
        1,
        &[0],
        false,
        4 * 1024 * 1024 * 1024,
        Some(512 * 1024 * 1024),
    )?;
    crate::resources::pin(admission.worker_cores[0])?;
    std::fs::create_dir(&request.output)?;
    write_new(
        &request.output,
        "generation-start.json",
        &serde_json::json!({"request":request,"admission":admission,"compiled_sources":crate::compiled_source_bindings(),"planned_families":128,"attempt_upper":1024,"transition_upper":16384,"models_loaded":0,"search_calls":0,"games_started":0}),
    )?;
    let book = generate(&prefixes, request.old_admission.sha256.clone())?;
    write_new(&request.output, "book.json", &book)?;
    write_new(&request.output, "schedule.json", &schedule())?;
    let receipt = serde_json::json!({"schema":SCHEMA,"complete":book.complete,"families":book.families.len(),"attempted":book.attempted,"transitions":book.transitions,"book_sha256":arena::json_digest(&book)?,"schedule_sha256":arena::json_digest(&schedule())?,"models_loaded":0,"search_calls":0,"games_started":0,"external_finalization":"PENDING; native receipt alone cannot admit campaign"});
    write_new(&request.output, "generation-result.json", &receipt)?;
    if !book.complete {
        return Err("CAMPAIGN_GENERATION_PARTIAL; retained attempts, no games".into());
    }
    Ok(receipt)
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CampaignRequest {
    pub book: crate::sigma_qualification::BoundControl,
    /// BEST51 then BEST43; configurations contain actual future evaluator identities.
    pub templates: [crate::sigma_qualification::BoundControl; 2],
    pub model_descriptors: [crate::sigma_qualification::BoundControl; 2],
    pub weights_sha256: [String; 2],
    pub output: std::path::PathBuf,
}
/// Config/512-slot publication only; no model load, calibration or games.
pub fn materialize(request: CampaignRequest) -> Result<serde_json::Value> {
    if request.weights_sha256 != [BEST51_WEIGHTS.to_string(), BEST43_WEIGHTS.to_string()] {
        return Err("CAMPAIGN_FIXED_TWO_MODELS".into());
    }
    let book: GeneratedBook = bounded_read(&request.book)?;
    let templates: [Config; 2] = [
        bounded_read(&request.templates[0])?,
        bounded_read(&request.templates[1])?,
    ];
    for c in &templates {
        if c.engines.len() != 2
            || c.arena
                .as_ref()
                .is_none_or(|a| a.evaluator_sha256.len() != 2)
        {
            return Err("CAMPAIGN_TEMPLATE_BINDINGS_REQUIRED".into());
        }
    }
    // Pin approved identities BEFORE normalization clears the permitted model difference.
    // BoundControl::read below also requires actual descriptor bytes to match this fixed digest.
    for (i, c) in templates.iter().enumerate() {
        approved_model_identity(
            i,
            &request.model_descriptors[i].sha256,
            &c.arena
                .as_ref()
                .expect("validated template")
                .evaluator_sha256[0],
        )?;
    }
    let normalized = |c: &Config| -> Result<serde_json::Value> {
        let mut v = serde_json::to_value(c)?;
        v["run_id"] = serde_json::Value::Null;
        v["output"] = serde_json::Value::Null;
        v["engines"][0]["model"] = serde_json::Value::Null;
        v["arena"]["evaluator_sha256"][0] = serde_json::Value::Null;
        Ok(v)
    };
    if normalized(&templates[0])? != normalized(&templates[1])? {
        return Err("CAMPAIGN_SAME_SETTINGS_BOTH_MATCHUPS".into());
    }
    // Reading actual descriptor metadata binds exact immutable weights identity; no weights payload.
    for (i, c) in templates.iter().enumerate() {
        let path = c
            .engines
            .first()
            .and_then(|e| e.model.as_ref())
            .ok_or("CAMPAIGN_MODEL_PATH")?;
        if *path != request.model_descriptors[i].path || std::fs::metadata(path)?.len() != 677 {
            return Err("CAMPAIGN_MODEL_DESCRIPTOR_LIMIT".into());
        }
        let model: serde_json::Value = bounded_read(&request.model_descriptors[i])?;
        if model["weights_SHA"] != request.weights_sha256[i] {
            return Err("CAMPAIGN_ACTUAL_DESCRIPTOR_WEIGHTS_IDENTITY".into());
        }
    }
    validate_book(&book)?;
    let configs = (0..16)
        .map(|batch| batch_config_validated(&templates[(batch / 2 + batch % 2) % 2], &book, batch))
        .collect::<Result<Vec<_>>>()?;
    std::fs::create_dir(&request.output)?;
    write_new(&request.output, "schedule.json", &schedule())?;
    let mut bindings = Vec::new();
    for (batch, c) in configs.iter().enumerate() {
        let name = format!("batch-{batch:02}.json");
        write_new(&request.output, &name, c)?;
        bindings.push(serde_json::json!({"batch":batch,"matchup":(batch/2+batch%2)%2,"path":request.output.join(name),"config_sha256":arena::json_digest(c)?,"planned_slots":32}));
    }
    let receipt = serde_json::json!({"book":request.book,"schedule_sha256":arena::json_digest(&schedule())?,"templates":request.templates,"model_descriptors":request.model_descriptors,"weights_sha256":request.weights_sha256,"batch_configs":bindings,"planned_slots":512,"games_started":0,"prepared":false,"limitation":"Whole supported resource/private/source/backend/clock/physical/peer/finalization admission remains mandatory. Weight metadata is not actual loaded model proof."});
    write_new(&request.output, "campaign.json", &receipt)?;
    Ok(receipt)
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Family {
    pub family_id: usize,
    pub id: String,
    pub attempt_id: usize,
    pub seed: u64,
    pub prefix: Vec<u16>,
    /// Includes turn, stocks and all wall anchors; never the old geometry-only key.
    pub root_key: String,
    pub history_counts: Vec<(String, u16)>,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Attempt {
    pub family_id: usize,
    pub attempt_id: usize,
    pub seed: u64,
    pub requested_plies: usize,
    pub prefix: Vec<u16>,
    pub rejection: Option<String>,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct GeneratedBook {
    pub schema: String,
    pub plan_sha256: String,
    pub old_open8_sha256: String,
    pub old_open8_prefixes: Vec<Vec<u16>>,
    pub rules: String,
    pub action_encoding: String,
    pub compiled_sources: std::collections::BTreeMap<String, String>,
    pub complete: bool,
    pub attempted: usize,
    pub transitions: usize,
    pub attempts: Vec<Attempt>,
    pub families: Vec<Family>,
}
fn prefix_length(family: usize) -> usize {
    [4, 8, 12, 16][family / 32]
}
fn attempt_seed(family: usize, attempt: usize) -> u64 {
    SEED + 8 * family as u64 + attempt as u64
}
fn select_action(legal: &[u16], rng: &mut Rng) -> Result<u16> {
    let mut sorted = legal.to_vec();
    sorted.sort_unstable();
    if sorted.windows(2).any(|p| p[0] == p[1]) {
        return Err("START_DUPLICATE_LEGAL_ID".into());
    }
    let pawn = rng.next_u64() % 3 != 2;
    let selected: Vec<_> = sorted
        .iter()
        .copied()
        .filter(|&a| (a < 81) == pawn)
        .collect();
    let pool = if selected.is_empty() {
        &sorted
    } else {
        &selected
    };
    if pool.is_empty() {
        return Err("START_NO_LEGAL_ACTION".into());
    }
    Ok(pool[(rng.next_u64() % pool.len() as u64) as usize])
}
fn history(c: &SigmaContext) -> Vec<(String, u16)> {
    c.history_counts()
        .iter()
        .map(|(k, n)| (k.history_string(), *n))
        .collect()
}
fn identity(c: &SigmaContext) -> (String, Vec<(String, u16)>) {
    (HistoryKey::from(c.position()).history_string(), history(c))
}
/// Intended future native NN0 generation; calling this is NOT authorized by source preparation.
/// Every attempted prefix is retained, including all failed candidates. No retry beyond eight.
pub fn generate(old_open8: &[Vec<u16>], old_open8_sha256: String) -> Result<GeneratedBook> {
    if old_open8.len() != 8
        || old_open8.iter().enumerate().any(|(i, p)| p.len() != i * 2)
        || !arena::sha_valid(&old_open8_sha256)
        || arena::json_digest(&old_open8)? != OLD_PREFIX_SHA256
    {
        return Err("START_BOUND_OLD_OPEN8".into());
    }
    let rules = Ruleset::Standard2pThreefold;
    let mut result = GeneratedBook {
        schema: SCHEMA.into(),
        plan_sha256: PLAN_SHA256.into(),
        old_open8_sha256,
        old_open8_prefixes: old_open8.to_vec(),
        rules: rules.id().into(),
        action_encoding: "Rust ActionID: pawn0..80/horizontal81..144/vertical145..208".into(),
        compiled_sources: crate::compiled_source_bindings()
            .into_iter()
            .map(|(k, v)| (k.into(), v))
            .collect(),
        complete: false,
        attempted: 0,
        transitions: 0,
        attempts: Vec::new(),
        families: Vec::new(),
    };
    let mut prefixes = BTreeSet::new();
    let mut histories = BTreeSet::new();
    for family in 0..FAMILIES {
        let mut accepted = false;
        for attempt in 0..ATTEMPTS_PER_FAMILY {
            let seed = attempt_seed(family, attempt);
            let mut rng = Rng::new(seed);
            let mut c = SigmaContext::from_prefix_with_rules(&[], rules)?;
            let mut prefix = Vec::new();
            let mut rejection = None;
            for _ in 0..prefix_length(family) {
                let a = select_action(&c.legal_ids(), &mut rng)?;
                c = c.play(a)?;
                prefix.push(a);
                result.transitions += 1;
                if c.terminal_value().is_some() {
                    rejection = Some(
                        if c.is_repetition_draw() {
                            "legal_third_draw"
                        } else {
                            "terminal"
                        }
                        .into(),
                    );
                    break;
                }
            }
            let key = identity(&c);
            if rejection.is_none() {
                rejection = if old_open8.contains(&prefix) {
                    Some("old_OPEN8")
                } else if prefixes.contains(&prefix) {
                    Some("duplicate_action_prefix")
                } else if histories.contains(&key) {
                    Some("duplicate_full_key_history")
                } else {
                    None
                }
                .map(str::to_owned);
            }
            result.attempted += 1;
            result.attempts.push(Attempt {
                family_id: family,
                attempt_id: attempt,
                seed,
                requested_plies: prefix_length(family),
                prefix: prefix.clone(),
                rejection: rejection.clone(),
            });
            if rejection.is_none() {
                prefixes.insert(prefix.clone());
                histories.insert(key.clone());
                result.families.push(Family {
                    family_id: family,
                    id: format!("strength355-family-{family:03}"),
                    attempt_id: attempt,
                    seed,
                    prefix,
                    root_key: key.0,
                    history_counts: key.1,
                });
                accepted = true;
                break;
            }
        }
        if !accepted {
            return Ok(result);
        }
    }
    result.complete = true;
    Ok(result)
}
/// Consumers rederive actual full histories and the first-accepted-attempt census.
/// This replays geometry only at a separately supported future entry, never reads a model.
pub fn validate_book(book: &GeneratedBook) -> Result<()> {
    if book.schema != SCHEMA
        || book.plan_sha256 != PLAN_SHA256
        || book.rules != Ruleset::Standard2pThreefold.id()
        || !book.complete
        || book.families.len() != FAMILIES
        || book.attempted != book.attempts.len()
        || book.attempted > 1024
        || book.transitions > 16384
        || book.compiled_sources
            != crate::compiled_source_bindings()
                .into_iter()
                .map(|(k, v)| (k.into(), v))
                .collect()
    {
        return Err("START_BOOK_INCOMPLETE_IDENTITY".into());
    }
    let mut prefixes = BTreeSet::new();
    let mut histories = BTreeSet::new();
    let mut cursor = 0;
    let mut transitions = 0;
    for (i, f) in book.families.iter().enumerate() {
        if f.family_id != i
            || f.id != format!("strength355-family-{i:03}")
            || f.attempt_id >= 8
            || f.seed != attempt_seed(i, f.attempt_id)
            || f.prefix.len() != prefix_length(i)
        {
            return Err("START_FAMILY_ORDER_SEED".into());
        }
        for attempt in 0..=f.attempt_id {
            let a = book.attempts.get(cursor).ok_or("START_ATTEMPT_MISSING")?;
            cursor += 1;
            if a.family_id != i
                || a.attempt_id != attempt
                || a.seed != attempt_seed(i, attempt)
                || a.requested_plies != prefix_length(i)
                || a.prefix.len() > a.requested_plies
                || (a.rejection.is_none() != (attempt == f.attempt_id))
                || (attempt == f.attempt_id && a.prefix != f.prefix)
            {
                return Err("START_ATTEMPT_CENSUS".into());
            }
            transitions += a.prefix.len();
        }
        let c = SigmaContext::from_prefix(&f.prefix)?;
        let key = identity(&c);
        if c.terminal_value().is_some()
            || key != (f.root_key.clone(), f.history_counts.clone())
            || !prefixes.insert(f.prefix.clone())
            || !histories.insert(key)
        {
            return Err("START_HISTORY_DUPLICATE_TERMINAL".into());
        }
    }
    if cursor != book.attempts.len() || transitions != book.transitions {
        return Err("START_TOTAL_CENSUS".into());
    }
    let rederived = generate(&book.old_open8_prefixes, book.old_open8_sha256.clone())?;
    if serde_json::to_value(rederived)? != serde_json::to_value(book)? {
        return Err("START_SEEDED_ATTEMPT_REDERIVATION".into());
    }
    Ok(())
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ScheduledSlot {
    pub slot: usize,
    pub batch: usize,
    pub matchup: usize,
    pub family_id: usize,
    pub candidate_color: u8,
    pub local_game: usize,
}
/// Sixteen balanced batches; counts and ordering do not depend on generated starts or outcomes.
pub fn schedule() -> Vec<ScheduledSlot> {
    let mut out = Vec::with_capacity(512);
    for group in 0..8 {
        for order in 0..2 {
            let matchup = (group + order) % 2;
            let batch = 2 * group + order;
            for family in group * 16..group * 16 + 16 {
                for color_order in 0..2 {
                    out.push(ScheduledSlot {
                        slot: out.len(),
                        batch,
                        matchup,
                        family_id: family,
                        candidate_color: ((family + group + color_order) % 2) as u8,
                        local_game: 2 * (family % 16) + color_order,
                    });
                }
            }
        }
    }
    out
}
pub fn candidate_color(config: &Config, game: usize) -> u8 {
    let first = config
        .arena
        .as_ref()
        .and_then(|a| a.first_candidate_colors.get(game / 2))
        .copied()
        .unwrap_or(0);
    first ^ (game % 2) as u8
}
/// Materialize one frozen 32-slot config. Template carries ACTUAL future loaded/evaluator bindings.
/// Configs may be produced only from a complete book and exact supported current image template.
pub fn batch_config(template: &Config, book: &GeneratedBook, batch: usize) -> Result<Config> {
    validate_book(book)?;
    batch_config_validated(template, book, batch)
}
fn batch_config_validated(template: &Config, book: &GeneratedBook, batch: usize) -> Result<Config> {
    if batch >= 16
        || template.engines.len() != 2
        || template.engines[0].kind != "nnue"
        || template.engines[1].kind != "distance"
        || template.engines[1].distance_a.to_bits() != 0f32.to_bits()
        || template.engines[1].distance_b != 8.
        || template.inference.is_some()
        || template.inference_cpu_core.is_some()
        || template
            .engines
            .iter()
            .any(|e| e.depth != 64 || e.max_nodes != 1000000 || e.time_ms != Some(100) || e.simd)
        || template.cpu_cores != [0]
        || template.workers != 1
        || template.active_games != 1
        || template.max_batch != 1
        || template.max_plies != 200
        || template.wall_seconds.is_some()
        || template.deadline_unix_ms != 0
        || template.engines[1].model.is_some()
        || template.ruleset != Ruleset::Standard2pThreefold
        || template.simulations != 64
        || template.temperature != 1.
    {
        return Err("CAMPAIGN_FIXED_ENGINE_RESOURCE_SETTINGS".into());
    }
    let mut c = template.clone();
    c.games = 32;
    c.openings.clear();
    c.opening_plies = 0;
    c.seed = SEED;
    c.train_games = None;
    c.validation_games = None;
    c.cycle = None;
    c.run_id = format!("strength355-batch-{batch:02}");
    c.output = template.output.join(&c.run_id);
    c.max_output_bytes = BATCH_OUTPUT_BYTES;
    let a = c.arena.as_mut().ok_or("CAMPAIGN_ARENA_REQUIRED")?;
    if a.comparison != arena::Comparison::EvaluatorWallTime
        || a.clock_policy != arena::ClockPolicy::StrictUnknown
        || a.return_reserve_ms != 5
        || a.tt_entries != 4096
    {
        return Err("CAMPAIGN_FIXED_CLOCK_TT".into());
    }
    a.retained_outcome_bytes = Some(OUTCOME_BYTES);
    a.bootstrap_seed = 35520261010;
    a.bootstrap_resamples = 10000;
    a.book.id = format!("strength355-frozen128-subset-{batch:02}");
    a.book.usage = arena::BookUse::Main;
    a.book.frozen_before_candidate_results = true;
    a.book.independence="128 target-blind families share initial state/generator; modulo sampling and shared matchup lineage, not IID. Aggregate all eight batches per matchup at family level.".into();
    a.book.openings.clear();
    a.first_candidate_colors.clear();
    for f in &book.families[batch / 2 * 16..batch / 2 * 16 + 16] {
        a.first_candidate_colors
            .push(((f.family_id + batch / 2) % 2) as u8);
        a.book.openings.push(arena::Opening { id:f.id.clone(),cohort:arena::Cohort::Main,
            lineage:format!("canonical-initial/strength355/seed{}",f.seed),siblings:Vec::new(),original_seed:Some(f.seed),
            reference:Some(arena::Reference {source_sha256:arena::json_digest(book)?,model_sha256:None,
                settings:serde_json::json!({"root_key":f.root_key,"history_counts":f.history_counts,"family_id":f.family_id,"attempt_id":f.attempt_id,"plan_sha256":book.plan_sha256}),
                q_definition:None,q_perspective:None,q_aggregation:None,q:None}),
            selection_reason:"Prebound legal target-blind start; no model/value/game outcome selection.".into(),candidate_pool_size:(f.attempt_id+1) as u64,prefix:f.prefix.clone() });
    }
    c.validate().map_err(|e| format!("CAMPAIGN_CONFIG:{e}"))?;
    Ok(c)
}
/// No row truncation: overlarge records refuse complete capture and trigger the existing failure path.
pub fn retained_outcome(config: &Config, o: &crate::runtime::Outcome) -> Result<()> {
    if let Some(cap) = config.arena.as_ref().and_then(|a| a.retained_outcome_bytes) {
        if o.observations
            .iter()
            .any(|m| serde_json::to_vec(m).map_or(true, |b| b.len() > OBSERVATION_BYTES))
            || serde_json::to_vec(o)?.len() > cap
        {
            return Err("CAPTURE_OUTCOME_OR_OBSERVATION_LIMIT; no full-capture certificate".into());
        }
    }
    Ok(())
}

pub fn result_receipt(
    config: &Config,
    report: &crate::runtime::RunReport,
) -> Result<serde_json::Value> {
    let path = config.output.join("result.json");
    Ok(
        serde_json::json!({"run_id":report.run_id,"planned":report.planned,"stopped":report.stopped,
        "all_workers_joined":report.all_workers_joined,"result":{"path":path,"sha256":crate::arena_manifest::file_sha256(&path)?,"bytes":std::fs::metadata(&path)?.len()},
        "capture":"durable result/journal/manifest; stdout is this bounded pointer only",
        "external_finalization":"PENDING; require actual successful controller/direct waits/final cleanup"}),
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn strength355_schedule_exact_balance_and_alternating_matchup_order() {
        let slots = schedule();
        assert_eq!(slots.len(), 512);
        for batch in 0..16 {
            let rows: Vec<_> = slots.iter().filter(|s| s.batch == batch).collect();
            assert_eq!(rows.len(), 32);
            assert_eq!(rows.iter().filter(|s| s.candidate_color == 0).count(), 16);
            assert_eq!(rows[0].matchup, (batch / 2 + batch % 2) % 2);
            assert_eq!(rows[0].family_id, batch / 2 * 16);
        }
        for m in 0..2 {
            for family in 0..128 {
                let rows: Vec<_> = slots
                    .iter()
                    .filter(|s| s.matchup == m && s.family_id == family)
                    .collect();
                assert_eq!(rows.len(), 2);
                assert_ne!(rows[0].candidate_color, rows[1].candidate_color);
                assert_eq!(rows[0].candidate_color, ((family + family / 16) % 2) as u8);
            }
        }
    }
    #[test]
    fn strength355_attempt_streams_and_sorted_type_fallback() {
        assert_eq!(attempt_seed(127, 7), SEED + 1023);
        let mut a = Rng::new(SEED);
        let mut b = Rng::new(SEED);
        assert_eq!(
            select_action(&[145, 13, 81, 3], &mut a).unwrap(),
            select_action(&[3, 81, 145, 13], &mut b).unwrap()
        );
        assert_eq!(select_action(&[145], &mut a).unwrap(), 145);
        assert!(select_action(&[], &mut a).is_err());
        assert_eq!((0..128).map(prefix_length).sum::<usize>() * 8, 10240);
    }
    #[test]
    fn strength355_partial_and_tampered_books_refuse_before_geometry() {
        let book = GeneratedBook {
            schema: SCHEMA.into(),
            plan_sha256: PLAN_SHA256.into(),
            old_open8_sha256: "a".repeat(64),
            old_open8_prefixes: vec![],
            rules: Ruleset::Standard2pThreefold.id().into(),
            action_encoding: String::new(),
            compiled_sources: Default::default(),
            complete: false,
            attempted: 0,
            transitions: 0,
            attempts: vec![],
            families: vec![],
        };
        assert!(validate_book(&book).is_err());
        let mut changed = book;
        changed.complete = true;
        assert!(validate_book(&changed).is_err());
    }
    #[test]
    fn strength355_config_colour_order_changes_mapping_and_saved_slots_together() {
        let mut c: Config =
            serde_json::from_str(include_str!("../../../configs/arena/smoke.json")).unwrap();
        c.arena.as_mut().unwrap().first_candidate_colors = vec![1];
        assert_eq!(candidate_color(&c, 0), 1);
        assert_eq!(candidate_color(&c, 1), 0);
        let slots = crate::arena_manifest::slots(
            &c,
            &[(0, "family".into(), vec![]), (1, "family".into(), vec![])],
        )
        .unwrap();
        assert_eq!(slots[0].candidate_color, 1);
        assert_eq!(slots[1].candidate_color, 0);
        c.arena.as_mut().unwrap().first_candidate_colors = vec![2];
        assert!(c.validate().is_err());
    }
    #[test]
    fn strength355_oversized_capture_refuses_without_truncation_or_relabel() {
        let mut c: Config =
            serde_json::from_str(include_str!("../../../configs/arena/smoke.json")).unwrap();
        c.arena.as_mut().unwrap().retained_outcome_bytes = Some(4096);
        let mut o = crate::runtime::Outcome {
            game: 0,
            family: "f".into(),
            candidate_color: 0,
            status: "unknown".into(),
            winner: None,
            plies: 0,
            reason: Some("original-engine-error".into()),
            nn_calls: 0,
            moves: vec![],
            persistent_tt: vec![],
            advance_calls: 0,
            terminal_no_nn: 0,
            allocated_nodes_peak: 0,
            started: false,
            failure: None,
            observations: vec![],
        };
        assert!(retained_outcome(&c, &o).is_ok());
        o.reason = Some("original-engine-error".repeat(4096));
        let before = serde_json::to_vec(&o).unwrap();
        assert!(retained_outcome(&c, &o).is_err());
        assert_eq!(serde_json::to_vec(&o).unwrap(), before);
        assert_eq!(o.status, "unknown");
    }
    #[test]
    fn strength355_batch_forecast_keeps_four_copies_and_metadata_reserve() {
        let mut c: Config =
            serde_json::from_str(include_str!("../../../configs/arena/smoke.json")).unwrap();
        c.games = 32;
        c.max_output_bytes = BATCH_OUTPUT_BYTES;
        c.arena.as_mut().unwrap().retained_outcome_bytes = Some(OUTCOME_BYTES);
        assert!(crate::arena_manifest::preflight(&c, &[]).is_ok());
        c.max_output_bytes = (32 * OUTCOME_BYTES * 4) as u64;
        assert!(crate::arena_manifest::preflight(&c, &[]).is_err());
    }
    #[test]
    fn strength355_approved_full_models_pass_but_caller_scaler_identity_refuses() {
        for i in 0..2 {
            assert!(
                approved_model_identity(
                    i,
                    APPROVED_DESCRIPTOR_SHA256[i],
                    APPROVED_EVALUATOR_SHA256[i]
                )
                .is_ok()
            );
            // Same approved weights are insufficient if mu/sigma/distance_fit bytes change.
            assert!(
                approved_model_identity(i, &"f".repeat(64), APPROVED_EVALUATOR_SHA256[i]).is_err()
            );
            assert!(
                approved_model_identity(i, APPROVED_DESCRIPTOR_SHA256[i], &"f".repeat(64)).is_err()
            );
            assert!(
                approved_model_identity(
                    i,
                    APPROVED_DESCRIPTOR_SHA256[1 - i],
                    APPROVED_EVALUATOR_SHA256[1 - i]
                )
                .is_err()
            );
        }
        assert!(approved_model_identity(2, "", " ").is_err());
    }
    #[test]
    fn strength355_changed_metadata_with_approved_declared_digest_fails_actual_read() {
        use std::io::Write;
        let path = std::env::temp_dir().join(format!(
            "strength355-model-metadata-{}-{}.json",
            std::process::id(),
            crate::config::unix_ms()
        ));
        let mut f = std::fs::OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(&path)
            .unwrap();
        let changed = serde_json::json!({"weights_SHA":BEST51_WEIGHTS,"mu_f32":[17.,18.],"sigma_f32":[1.,1.],"distance_fit":{"a":0.,"b":8.}});
        f.write_all(&serde_json::to_vec(&changed).unwrap()).unwrap();
        drop(f);
        let bound = crate::sigma_qualification::BoundControl {
            path: path.clone(),
            sha256: APPROVED_DESCRIPTOR_SHA256[0].into(),
        };
        assert!(bounded_read::<serde_json::Value>(&bound).is_err());
        std::fs::remove_file(path).unwrap();
    }
}

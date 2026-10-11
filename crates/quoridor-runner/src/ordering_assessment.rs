//! Temporary inlet for the single prebound 360 assessment. Retire after its result.
//! No alternate evaluator, TT implementation, scheduler or admission registry.
use crate::{
    arena,
    research_manifest::{self, Experiment, FileRef},
    sigma_qualification::BoundControl,
};
use quoridor_ai::alphabeta::{
    self, OrderingProfile, SearchLimits, SearchNamespace, SearchResult, SearchSession,
    StaticEvaluator, StopReason,
};
use quoridor_core::research::{HistoryKey, SigmaContext};
use quoridor_data::Result;
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::{
    fs::{self, File, OpenOptions},
    io::{Read, Write},
    path::{Path, PathBuf},
    sync::{Arc, atomic::AtomicBool},
    time::Instant,
};

const RULES: &str = "research-standard-2p-threefold-goal-first-v1";
const DESCRIPTOR: &str = "46ec2c4708f96dcf9fad579c2fb0d1299c6663df27412f0faac98267467715e1";
const WEIGHTS: &str = "046fe926e56b955b0fb7de8f147a74ec33eace9cbc00a55c307f9b6541ab9841";
const EVALUATOR: &str = "96a5f41f875022d1752b9c999595ad58bfb2d42687a8f06de08d42b1c4215875";
const BOOK: &str = "a6abde1f3182ba0e876c9e7719d3389502a44b3406ca28b7af9a0456952a6878";
const COLD: [usize; 4] = [0, 34, 68, 102];
const CAPS: [u64; 2] = [2_000_000, 8_000_000];
const AGGREGATE: u64 = 1_800_000_000;
const RAW_BYTES: usize = 8 * 1048576;
const ROW_BYTES: usize = 8192;
const JOURNAL_BYTES: u64 = 4 * 1048576;

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Plan {
    pub schema: String,
    pub assessment: FileRef,
    pub resources: FileRef,
    pub book: FileRef,
    pub warm_origin: FileRef,
    pub warm_config: FileRef,
    pub warm_journal: FileRef,
    pub output: PathBuf,
}
#[derive(Clone, Copy, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
enum Profile {
    Prior,
    Continuation,
    Static,
}
impl Profile {
    fn native(self) -> OrderingProfile {
        match self {
            Self::Prior => OrderingProfile::UnsignedHistoryBaseline,
            Self::Continuation => OrderingProfile::CombinedSigned,
            Self::Static => OrderingProfile::CombinedSignedStatic,
        }
    }
}
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct Request {
    id: usize,
    pass: usize,
    diagnostic: bool,
    profile: Profile,
    depth: u16,
    root: usize,
    warm: bool,
    node_cap: u64,
}
fn schedule() -> Vec<Request> {
    let plain = [
        Profile::Prior,
        Profile::Continuation,
        Profile::Static,
        Profile::Static,
        Profile::Continuation,
        Profile::Prior,
    ];
    let diagnostic = [Profile::Prior, Profile::Continuation, Profile::Static];
    let mut rows = Vec::with_capacity(360);
    let mut pass = 0;
    for (observe, order) in [(false, plain.as_slice()), (true, diagnostic.as_slice())] {
        for (depth, cap) in [4, 6].into_iter().zip(CAPS) {
            for root in 0..4 {
                for &profile in order {
                    rows.push(Request {
                        id: rows.len(),
                        pass,
                        diagnostic: observe,
                        profile,
                        depth,
                        root,
                        warm: false,
                        node_cap: cap,
                    });
                    pass += 1;
                }
            }
            for &profile in order {
                for root in 4..20 {
                    rows.push(Request {
                        id: rows.len(),
                        pass,
                        diagnostic: observe,
                        profile,
                        depth,
                        root,
                        warm: true,
                        node_cap: cap,
                    });
                }
                pass += 1;
            }
        }
    }
    rows
}
fn validate(p: &Plan, e: &Experiment, requests: &[Request]) -> Result<()> {
    if p.schema != "quoridor.continuation360.plan.v1"
        || e.phase != "compare"
        || e.planned_slots != 360
        || e.batch.is_some()
        || e.numerical_qualification.is_none()
        || e.canonical_plan_sha256 != p.assessment.sha256
        || requests != schedule()
        || e.models.len() != 1
        || p.book.sha256 != BOOK
        || p.warm_journal.bytes > JOURNAL_BYTES
        || e.argv.len() != 6
        || e.argv[1..]
            != [
                "ordering-assess",
                "--experiment",
                "@EXPERIMENT@",
                "--experiment-sha256",
                "@EXPERIMENT_SHA256@",
            ]
        || e.inputs
            != [
                p.book.clone(),
                p.warm_origin.clone(),
                p.warm_config.clone(),
                p.warm_journal.clone(),
                p.assessment.clone(),
                p.resources.clone(),
            ]
    {
        return Err("360 exact capped schedule/input/caller prerequisite".into());
    }
    let m = &e.models[0];
    if m.descriptor.sha256 != DESCRIPTOR
        || m.descriptor.bytes != 677
        || m.descriptor.mode != "0600"
        || m.weights.sha256 != WEIGHTS
        || m.weights.bytes != 49284
        || m.evaluator_sha256 != EVALUATOR
    {
        return Err("360 selected unchanged BEST43 required".into());
    }
    Ok(())
}
#[derive(Clone, Debug)]
struct RootSpec {
    prefix: Vec<u16>,
    family: usize,
    local_ply: Option<usize>,
    expected: Option<Value>,
}
fn identity(c: &SigmaContext) -> Value {
    json!({"root_key":HistoryKey::from(c.position()).history_string(),"history_counts":c.history_counts().into_iter().map(|(k,n)|(k.history_string(),n)).collect::<Vec<_>>(),"ply":c.total_ply(),"rules":c.ruleset().id(),"synthetic":c.is_synthetic()})
}
fn derive_roots(book: &Value, game: Option<&Value>) -> Result<Vec<Option<RootSpec>>> {
    if book["schema"] != "quoridor.value-search-strength.book.v1"
        || book["complete"] != true
        || book["rules"] != RULES
    {
        return Err("360 original complete128 book required".into());
    }
    let families = book["families"].as_array().ok_or("360 families")?;
    if families.len() != 128 {
        return Err("360 original128 denominator".into());
    }
    let mut roots = Vec::with_capacity(20);
    for (slot, family) in COLD.into_iter().enumerate() {
        let f = &families[family];
        let prefix: Vec<u16> = serde_json::from_value(f["prefix"].clone())?;
        if f["family_id"] != family
            || f["id"] != format!("strength355-family-{family:03}")
            || prefix.len() != [4, 8, 12, 16][slot]
        {
            return Err("360 fixed stratum/full-prefix mismatch".into());
        }
        roots.push(Some(RootSpec {
            prefix,
            family,
            local_ply: None,
            expected: Some(json!({"root_key":f["root_key"],"history_counts":f["history_counts"]})),
        }));
    }
    let initial: Vec<u16> = serde_json::from_value(families[0]["prefix"].clone())?;
    let moves = if let Some(g) = game {
        if g["game"] != 0 || g["candidate_color"] != 0 || g["started"] != true {
            return Err("360 original batch00/localgame0 provenance".into());
        }
        let moves: Vec<u16> = serde_json::from_value(g["moves"].clone())?;
        if moves.len() > 200 || !moves.starts_with(&initial) {
            return Err("360 complete chronological opening mismatch".into());
        }
        Some(moves)
    } else {
        None
    };
    for local_ply in (0..32).step_by(2) {
        let end = initial.len() + local_ply;
        roots.push(moves.as_ref().filter(|m| m.len() >= end).map(|m| RootSpec {
            prefix: m[..end].to_vec(),
            family: 0,
            local_ply: Some(local_ply),
            expected: None,
        }));
    }
    Ok(roots)
}
fn replay(spec: &RootSpec) -> Result<SigmaContext> {
    let root = SigmaContext::from_prefix(&spec.prefix)?;
    root.validate_normal()?;
    if root.is_synthetic()
        || root.ruleset().id() != RULES
        || root.total_ply() as usize != spec.prefix.len()
        || root.terminal_value().is_some()
    {
        return Err("360 unsupported/terminal root, no replacement".into());
    }
    if let Some(expected) = &spec.expected {
        let actual = identity(&root);
        if actual["root_key"] != expected["root_key"]
            || actual["history_counts"] != expected["history_counts"]
        {
            return Err("360 exact counted-history/root mismatch".into());
        }
    }
    Ok(root)
}
fn warm_game(p: &Plan, book: &Value) -> Result<Option<Value>> {
    if p.warm_origin
        .path
        .file_name()
        .is_none_or(|n| n != "manifest.json")
        || p.warm_origin.path.with_file_name("INCOMPLETE").exists()
    {
        return Err("360 authoritative original warm origin required".into());
    }
    let origin: Value = p.warm_origin.read()?;
    if origin["status"] != "PASS"
        || origin["cleanup_complete"] != true
        || origin["remaining"] != json!([])
        || !origin["data"]["files"]
            .as_array()
            .is_some_and(|files| files.contains(&json!(p.warm_journal)))
    {
        return Err("360 exact stopped original journal custody".into());
    }
    let original: FileRef = serde_json::from_value(origin["experiment"].clone())?;
    let experiment: Experiment = original.read()?;
    if experiment.phase != "arena"
        || experiment.batch != Some(0)
        || experiment.planned_slots != 32
        || experiment.config != p.warm_config
    {
        return Err("360 original batch0 configuration provenance".into());
    }
    let config: Value = p.warm_config.read()?;
    let first = &config["arena"]["book"]["openings"][0];
    if first["reference"]["settings"]["family_id"] != 0
        || first["prefix"] != book["families"][0]["prefix"]
    {
        return Err("360 opening-to-global-family join".into());
    }
    p.warm_journal.verify()?;
    let mut raw = Vec::new();
    File::open(&p.warm_journal.path)?
        .take(p.warm_journal.bytes + 1)
        .read_to_end(&mut raw)?;
    if raw.len() as u64 != p.warm_journal.bytes
        || arena::digest(&raw) != p.warm_journal.sha256
        || !raw.ends_with(b"\n")
    {
        return Err("360 saved journal drift/partial tail".into());
    }
    let mut game = None;
    for line in raw.split(|b| *b == b'\n').filter(|s| !s.is_empty()) {
        if line.len() > 262144 {
            return Err("360 bounded original journal record".into());
        }
        let row: Value = serde_json::from_slice(line)?;
        if row["game"] == 0 {
            if game.is_some() {
                return Err("360 duplicate original game0".into());
            }
            game = Some(row);
        }
    }
    if let Some(g) = &game {
        let run_id = config["run_id"].as_str().ok_or("360 original run id")?;
        if g["family"] != format!("{run_id}-family-000000")
            || g["candidate_color"] != config["arena"]["first_candidate_colors"][0]
        {
            return Err("360 native local family/config global family correspondence".into());
        }
    }
    Ok(game)
}
fn fact(e: &dyn std::fmt::Display) -> Value {
    let raw = e.to_string();
    let mut end = raw.len().min(1024);
    while !raw.is_char_boundary(end) {
        end -= 1;
    }
    json!({"text":&raw[..end],"full_sha256":arena::digest(raw.as_bytes()),"full_bytes":raw.len(),"truncated":end!=raw.len()})
}
fn output_correspondence(p: &Plan) -> Result<()> {
    // load() already validates this same SHA-bound originating guardian intent.
    // Read its priced output root, without a second lock or admission path.
    let intent: Value = BoundControl {
        path: std::env::var("QUORIDOR_LIFECYCLE_INTENT_PATH")?.into(),
        sha256: std::env::var("QUORIDOR_LIFECYCLE_INTENT")?,
    }
    .read()?;
    let expected: PathBuf = serde_json::from_value(intent["data_root"].clone())?;
    if p.output != expected {
        return Err("360 same priced lifecycle data root required".into());
    }
    Ok(())
}
fn observed(r: &SearchResult) -> Value {
    let s = &r.stats;
    let o = &s.ordering;
    json!({"returned":"Ok","action":r.action,"value":r.value,"value_bits":r.value.map(f32::to_bits),"completed_depth":r.completed_depth,"PV":r.pv,"stop":format!("{:?}",r.stop),"Search_internal_elapsed_seconds":r.elapsed.as_secs_f64(),
        "work":{"nodes":s.nodes,"evaluations":s.evaluations,"terminal":s.terminal,"cutoffs":s.cutoffs,"TT_hits":s.tt_hits,"TT_probes":s.tt_probes,"TT_exact_hits":s.tt_exact_hits,"TT_key_builds":s.tt_key_builds,"tt_context_initial_items":s.tt_context_initial_items,"tt_context_transitions":s.tt_context_transitions,"tt_board_hash_reads":s.tt_board_hash_reads,"tt_board_hash_updates":s.tt_board_hash_updates,"tt_context_matches":s.tt_context_matches,"tt_context_misses":s.tt_context_misses,"tt_order_context_mismatch":s.tt_order_context_mismatch,"tt_hash_collisions":s.tt_hash_collisions,"tt_index_collisions":s.tt_index_collisions,"TT_hashes":s.tt_hashes,"TT_usable_depth":s.tt_usable_depth,"TT_order_only":s.tt_order_only,"TT_collisions":s.tt_collisions,"TT_replacements":s.tt_replacements,"TT_capacity_skips":s.tt_capacity_skips,"TT_illegal_moves":s.tt_illegal_moves,"TT_retained_bytes":s.tt_retained_bytes,"TT_generation":s.tt_generation,"TT_cutoffs":s.tt_cutoffs,"PVS_researches":s.pvs_researches,"delta_updates":s.delta_updates,"policy_calls":s.policy_calls},
        "ordering":{"ordered_nodes":o.ordered_nodes,"scored_actions":o.scored_actions,"nonzero_dynamic_actions":o.nonzero_dynamic_actions,"nonzero_combined_actions":o.nonzero_combined_actions,"nonzero_continuation_actions":o.nonzero_continuation_actions,"history_changed_nodes":o.history_changed_nodes,"completed_cutoff_events":o.completed_cutoff_events,"cutoff_rank_sum":o.cutoff_rank_sum,"first_child_cutoffs":o.first_child_cutoffs,"positive_actions":o.positive_actions,"negative_actions":o.negative_actions,"continuation_updates":o.continuation_updates,"age_passes":o.age_passes,"static_parents":o.static_parents,"borrowed_goal_maps":o.borrowed_goal_maps,"computed_goal_map_pairs":o.computed_goal_map_pairs,"nonzero_static_actions":o.nonzero_static_actions,"exact_goal_actions":o.exact_goal_actions,"static_changed_nodes":o.static_changed_nodes}})
}
fn validate_return(root: &SigmaContext, r: &SearchResult, request: &Request) -> Result<bool> {
    if r.stats.nodes > request.node_cap
        || r.pv.len() > 200
        || r.value.is_some_and(|v| !v.is_finite())
        || r.action.is_some_and(|a| !root.legal_ids().contains(&a))
    {
        return Err("360 returned observation outside canonical bound".into());
    }
    let mut pv = root.clone();
    for &action in &r.pv {
        pv = pv.play(action)?;
    }
    Ok(r.completed_depth == request.depth
        && r.stop == StopReason::DepthComplete
        && r.value.is_some()
        && r.action.is_some())
}
fn close_file(file: File) -> std::io::Result<()> {
    #[cfg(unix)]
    {
        use std::os::fd::IntoRawFd;
        if unsafe { libc::close(file.into_raw_fd()) } != 0 {
            return Err(std::io::Error::last_os_error());
        }
    }
    #[cfg(not(unix))]
    drop(file);
    Ok(())
}
struct Output {
    root: PathBuf,
    owned: bool,
    rows: Option<File>,
    costs: Option<File>,
    used: usize,
    close_errors: Vec<Value>,
}
impl Output {
    fn new(root: &Path) -> Self {
        Self {
            root: root.into(),
            owned: false,
            rows: None,
            costs: None,
            used: 4096,
            close_errors: Vec::new(),
        }
    }
    fn setup(&mut self, planned: &Value) -> Result<()> {
        self.setup_with(
            planned,
            |output, name, value, cap| output.file(name, value, cap),
            |path| OpenOptions::new().create_new(true).write(true).open(path),
        )
    }
    // Narrow setup ports exercise returned IO errors without model/Search calls.
    fn setup_with(
        &mut self,
        planned: &Value,
        mut write: impl FnMut(&mut Self, &str, &Value, usize) -> Result<()>,
        mut open: impl FnMut(&Path) -> std::io::Result<File>,
    ) -> Result<()> {
        if self.owned
            || !self.root.is_absolute()
            || self.root.exists()
            || self
                .root
                .parent()
                .is_none_or(|p| p.canonicalize().ok().as_deref() != Some(p))
        {
            return Err("360 fresh owned canonical output required".into());
        }
        fs::create_dir(&self.root)?;
        self.owned = true;
        write(
            self,
            "INCOMPLETE",
            &json!({"status":"INCOMPLETE","planned":360}),
            ROW_BYTES,
        )?;
        write(self, "planned.json", planned, 262144)?;
        self.rows = Some(open(&self.root.join("observations.jsonl"))?);
        self.costs = Some(open(&self.root.join("costs.jsonl"))?);
        self.directory()
    }
    fn bytes(&mut self, value: &Value, cap: usize) -> Result<Vec<u8>> {
        let mut raw = serde_json::to_vec(value)?;
        raw.push(b'\n');
        if raw.len() > cap
            || self
                .used
                .checked_add(raw.len())
                .is_none_or(|n| n > RAW_BYTES - 131072)
        {
            return Err("360 full capture/storage bound; no truncation or refill".into());
        }
        self.used += raw.len();
        Ok(raw)
    }
    fn file(&mut self, name: &str, value: &Value, cap: usize) -> Result<()> {
        if !self.owned {
            return Err("360 output directory not owned; no publication".into());
        }
        let raw = self.bytes(value, cap)?;
        let mut f = OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(self.root.join(name))?;
        let result = f.write_all(&raw).and_then(|()| f.sync_all());
        let closed = close_file(f);
        self.file_return(name, result, closed)
    }
    fn directory(&mut self) -> Result<()> {
        if !self.owned {
            return Err("360 output directory not owned; no sync".into());
        }
        let file = File::open(&self.root)?;
        let result = file.sync_all();
        let closed = close_file(file);
        self.file_return("directory", result, closed)
    }
    fn file_return(
        &mut self,
        name: &str,
        result: std::io::Result<()>,
        closed: std::io::Result<()>,
    ) -> Result<()> {
        if let Err(e) = &closed {
            self.close_errors
                .push(json!({"stage":format!("{name}_close"),"error":fact(e)}));
        }
        result?;
        closed?;
        Ok(())
    }
    fn row(&mut self, value: &Value, costs: bool) -> Result<()> {
        let raw = self.bytes(value, if costs { 2048 } else { ROW_BYTES })?;
        let f = if costs {
            &mut self.costs
        } else {
            &mut self.rows
        }
        .as_mut()
        .ok_or("360 journal already closed")?;
        f.write_all(&raw)?;
        f.sync_data()?;
        Ok(())
    }
    fn close(&mut self) -> (Option<std::io::Error>, Vec<Value>) {
        self.close_with(|_, file| {
            let synced = file.sync_all();
            let closed = close_file(file);
            (synced, closed)
        })
    }
    fn close_with(
        &mut self,
        mut finish: impl FnMut(&str, File) -> (std::io::Result<()>, std::io::Result<()>),
    ) -> (Option<std::io::Error>, Vec<Value>) {
        let mut errors = Vec::new();
        let mut primary = None;
        for (name, f) in [("observations", &mut self.rows), ("costs", &mut self.costs)] {
            if let Some(file) = f.take() {
                let (synced, closed) = finish(name, file);
                if let Err(e) = synced {
                    errors.push(json!({"stage":name,"error":fact(&e)}));
                    if primary.is_none() {
                        primary = Some(e);
                    }
                }
                // Consuming into OwnedFd permits explicit fallible close, not implicit success.
                if let Err(e) = closed {
                    errors.push(json!({"stage":format!("{name}_close"),"error":fact(&e)}));
                    if primary.is_none() {
                        primary = Some(e);
                    }
                }
            }
        }
        (primary, errors)
    }
    fn finalize(&mut self, outcome: Result<Value>, secondary: &mut Vec<Value>) -> Result<Value> {
        let closed = self.close();
        self.finalize_after_close(outcome, secondary, closed)
    }
    fn finalize_after_close(
        &mut self,
        outcome: Result<Value>,
        secondary: &mut Vec<Value>,
        (close_primary, close_secondary): (Option<std::io::Error>, Vec<Value>),
    ) -> Result<Value> {
        secondary.extend(close_secondary);
        let failed = match outcome {
            Ok(result) if secondary.is_empty() => {
                let commit: Result<()> = (|| {
                    self.file("result.json", &result, 524288)?;
                    self.directory()?;
                    // Outer lifecycle alone publishes authoritative completion.
                    fs::remove_file(self.root.join("INCOMPLETE"))?;
                    Ok(())
                })();
                match commit {
                    Ok(()) => return Ok(result),
                    Err(e) => e,
                }
            }
            Err(e) => e,
            Ok(_) => close_primary.map_or_else(
                || "360 owed journal finalizer failed".into(),
                |e| Box::new(e) as Box<dyn std::error::Error + Send + Sync>,
            ),
        };
        secondary.extend(std::mem::take(&mut self.close_errors));
        Err(failed)
    }
}
#[derive(Default)]
struct Census {
    session_setup_attempts: usize,
    session_setup_ok: usize,
    session_setup_err: usize,
    attempted: usize,
    invoked: usize,
    ok: usize,
    err: usize,
    complete: usize,
    published_complete: usize,
    liability: u64,
}
fn session(eval: Arc<dyn StaticEvaluator>, request: &Request) -> Result<SearchSession> {
    let session = SearchSession::new_for_ordering_assessment(
        eval,
        SearchNamespace {
            evaluator: format!("360:BEST43:{EVALUATOR}:wall-distance/80:a0b0:residual-tanh"),
            rules: RULES.into(),
            selectivity: "fullwidth-PVS".into(),
        },
        4096,
        quoridor_ai::score::ScoreDomain::LEGACY,
        request.profile.native(),
        request.diagnostic,
    )?;
    if session.tt_capacity() != (4096, 1048576) {
        return Err("360 same qualified TT4096/1MiB prerequisite".into());
    }
    Ok(session)
}
/// Uses the maintained generic Experiment/numerical/lifetime entry, not private TT access.
pub fn run(bound: &BoundControl) -> Result<Value> {
    let whole = Instant::now();
    let (e, _) = research_manifest::load(bound, "compare")?;
    let p: Plan = e.config.read()?;
    let requests: Vec<Request> = e.schedule.read()?;
    validate(&p, &e, &requests)?;
    output_correspondence(&p)?;
    let assessment: Value = p.assessment.read()?;
    if assessment["assessment"]["all_planned_root_calls"] != 360
        || assessment["assessment"]["selection_before_outcomes"]["cold_family_ids"] != json!(COLD)
    {
        return Err("360 exact pre-outcome canonical assessment required".into());
    }
    let support: Value = p.resources.read()?;
    if support["new_360_exclusive_whole_B"] != 134217728
        || support["components_B"]["assessment_raw"] != RAW_BYTES
    {
        return Err("360 actual issued source/whole raw allowance required".into());
    }
    let book: Value = p.book.read()?;
    let roots = derive_roots(&book, warm_game(&p, &book)?.as_ref())?;
    let inputs_seconds = whole.elapsed().as_secs_f64();
    let header = json!({"schema":"quoridor.continuation360.intent.v1","experiment_sha256":bound.sha256,"config_sha256":e.config.sha256,"schedule_sha256":e.schedule.sha256,"build_manifest":e.build_manifest,"compiled_sources":research_manifest::sources(),"model":e.models[0],"input_refs":e.inputs,"requests":requests,"planned":360,"plain":240,"diagnostic":120,"no_refill":true,"pre_root_continuation":"absent; actual speculative LIFO only"});
    let mut output = Output::new(&p.output);
    let mut count = Census::default();
    let mut pending = Value::Null;
    let mut secondary = Vec::new();
    let mut pass_costs = Vec::new();
    let mut root_costs = Vec::new();
    let outcome: Result<Value> = (|| {
        pending = json!({"stage":"output_setup","Search_invoked":false});
        output.setup(&header)?;
        pending = json!({"stage":"model_setup","Search_invoked":false});
        let model_start = Instant::now();
        let metadata: quoridor_nnue::residual::ResidualManifest = e.models[0].descriptor.read()?;
        if metadata.weights_sha != WEIGHTS
            || metadata.distance_fit.a.to_bits() != 0f32.to_bits()
            || metadata.distance_fit.b.to_bits() != 0f32.to_bits()
        {
            return Err("360 immutable BEST43 zero-bypass coefficients".into());
        }
        let model = Arc::new(quoridor_nnue::residual::ResidualModel::load(
            &e.models[0].descriptor.path,
        )?);
        // Same maintained typed_identity content digest as runtime's residual branch.
        if quoridor_data::hex_digest(&model.fingerprint()) != EVALUATOR {
            return Err("360 actual loaded evaluator identity mismatch".into());
        }
        let eval: Arc<dyn StaticEvaluator> = Arc::new(alphabeta::ResidualEvaluator::new(model));
        let model_setup_seconds = model_start.elapsed().as_secs_f64();
        let cancel = AtomicBool::new(false);
        let mut start = 0;
        while start < requests.len() {
            let first = &requests[start];
            let end = requests[start..]
                .iter()
                .position(|r| r.pass != first.pass)
                .map_or(requests.len(), |n| start + n);
            let pass_start = Instant::now();
            let setup = Instant::now();
            count.session_setup_attempts += 1;
            pending = json!({"request":first,"stage":"session_setup","invoked":false});
            let mut s = match session(eval.clone(), first) {
                Ok(s) => {
                    count.session_setup_ok += 1;
                    s
                }
                Err(error) => {
                    count.session_setup_err += 1;
                    pending["original_error"] = fact(&*error);
                    pending["session_setup_seconds"] = json!(setup.elapsed().as_secs_f64());
                    return Err(error);
                }
            };
            let setup_seconds = setup.elapsed().as_secs_f64();
            let retained = s.retained_memory_bytes();
            let mut last_root_started = pass_start;
            for request in &requests[start..end] {
                let body_start = Instant::now();
                let root_whole_start = if request.id == first.id {
                    pass_start
                } else {
                    body_start
                };
                last_root_started = root_whole_start;
                count.attempted += 1;
                pending = json!({"request":request,"stage":"root_replay","invoked":false});
                let root = roots[request.root].as_ref().map(replay).transpose();
                let root = match root {
                    Ok(Some(c)) => c,
                    other => {
                        pending["status"] = json!("UNKNOWN");
                        pending["reason"] = json!(
                            "original context missing/short/unsupported/terminal; no replacement"
                        );
                        if let Err(e) = other {
                            pending["original_error"] = fact(&*e);
                        }
                        output.row(&pending, false)?;
                        output.row(&json!({"request_id":request.id,"root_body_until_primary_publication_seconds":body_start.elapsed().as_secs_f64(),"Search_invocations":0}), true)?;
                        root_costs.push(json!({"request_id":request.id,"whole_interval_seconds":root_whole_start.elapsed().as_secs_f64(),"Search_invocations":0,"includes_setup":request.id==first.id,"includes_drop":false}));
                        continue;
                    }
                };
                let before = identity(&root);
                let cap = request.node_cap;
                if count
                    .liability
                    .checked_add(cap)
                    .is_none_or(|n| n > AGGREGATE)
                {
                    return Err("360 aggregate node liability exhausted; remaining UNKNOWN".into());
                }
                count.liability += cap;
                let limits = SearchLimits {
                    max_depth: request.depth,
                    max_nodes: cap,
                    time_limit: None,
                    tt_entries: 4096,
                    use_pvs: true,
                    use_tt: true,
                };
                count.invoked += 1;
                pending = json!({"request":request,"stage":"Search_invoked","root":before,"prefix_sha256":arena::json_digest(&roots[request.root].as_ref().unwrap().prefix)?,"family":roots[request.root].as_ref().unwrap().family,"local_ply":roots[request.root].as_ref().unwrap().local_ply,"invoked":true,"reserved_nodes":cap});
                // No observer, restoration check, serialization or clock nesting between these stamps.
                let search_start = Instant::now();
                let result = s.search(&root, &limits, &cancel);
                let search_seconds = search_start.elapsed().as_secs_f64();
                // Capture returned facts before restoration/finite/PV/census validation.
                pending["stage"] = json!("returned_before_validation");
                pending["Search_only_seconds"] = json!(search_seconds);
                match result {
                    Ok(r) => {
                        count.ok += 1;
                        pending["observed"] = observed(&r);
                        if identity(&root) != before {
                            return Err("360 full parent restoration mismatch".into());
                        }
                        let complete = validate_return(&root, &r, request)?;
                        count.liability -= cap - r.stats.nodes;
                        count.complete += usize::from(complete);
                        pending["status"] = json!(if complete { "COMPLETE" } else { "UNKNOWN" });
                    }
                    Err(error) => {
                        count.err += 1;
                        pending["status"] = json!("UNKNOWN");
                        pending["observed"] = json!({"returned":"Err","original_error":fact(&error),"work":"UNKNOWN; conservative reserved nodes retained"});
                        if identity(&root) != before {
                            secondary.push(json!({"stage":"parent_restoration","error":"root drift after Search Err"}));
                        }
                        if let Err(publication) = output.row(&pending, false) {
                            secondary.push(json!({"stage":"Search_Err_observation_publication","error":fact(&*publication)}));
                        }
                        return Err(Box::new(error));
                    }
                }
                output.row(&pending, false)?;
                count.published_complete += usize::from(pending["status"] == "COMPLETE");
                // Exact stopping point; cost-ledger publication is charged in pass/outer whole.
                let body_seconds = body_start.elapsed().as_secs_f64();
                output.row(&json!({"request_id":request.id,"Search_only_seconds":search_seconds,"root_body_until_primary_publication_seconds":body_seconds,"excludes":"session setup/drop and this cost-ledger publication; included in pass/outer whole"}), true)?;
                root_costs.push(json!({"request_id":request.id,"whole_interval_seconds":root_whole_start.elapsed().as_secs_f64(),"includes_setup":request.id==first.id,"includes_drop":false}));
            }
            let drop_start = Instant::now();
            drop(s);
            let drop_seconds = drop_start.elapsed().as_secs_f64();
            if let Some(last) = root_costs.last_mut() {
                last["whole_interval_seconds"] = json!(last_root_started.elapsed().as_secs_f64());
                last["includes_drop"] = json!(true);
            }
            pass_costs.push(json!({"pass":first.pass,"profile":first.profile,"diagnostic":first.diagnostic,"depth":first.depth,"warm":first.warm,"requests":end-start,"session_setup_seconds":setup_seconds,"session_drop_seconds":drop_seconds,"retained_TT_bytes":retained.0,"retained_session_metadata_and_history_bytes":retained.1,"pass_whole_until_cost_footer_seconds":pass_start.elapsed().as_secs_f64(),"includes":"setup/replay/Search/map-DAG-sort/aging/stats/observation+cost-ledger serialization and sync/drop; footer/finalization paid outer whole"}));
            start = end;
        }
        let model_drop = Instant::now();
        drop(eval);
        let model_drop_seconds = model_drop.elapsed().as_secs_f64();
        for input in &e.inputs {
            input.verify()?;
        }
        e.config.verify()?;
        e.schedule.verify()?;
        for m in &e.models {
            m.descriptor.verify()?;
            m.weights.verify()?;
        }
        Ok(
            json!({"schema":"quoridor.continuation360.result.v1","status":if count.complete==360 {"COMPLETE"} else {"COMPLETED_WITH_UNKNOWN"},"experiment_sha256":bound.sha256,"config_sha256":e.config.sha256,"schedule_sha256":e.schedule.sha256,"planned":360,"session_setup_attempts":count.session_setup_attempts,"session_setup_Ok":count.session_setup_ok,"session_setup_Err":count.session_setup_err,"root_replay_attempts":count.attempted,"attempted":count.attempted,"actual_Search_invocations":count.invoked,"returned_Ok":count.ok,"returned_Err":count.err,"completed_requested_depth":count.complete,"durably_published_complete_rows":count.published_complete,"planned_UNKNOWN":360-count.complete,"node_liability":count.liability,"input_verification_and_derivation_seconds":inputs_seconds,"model_setup_seconds":model_setup_seconds,"model_drop_seconds":model_drop_seconds,"passes":pass_costs,"root_whole_intervals":root_costs,"root_interval_cost_domain":"Actual interval includes primary+cost-journal serialization/sync, setup on first and drop on last root. Shared model/input/header/footer/outer-finalizer costs retained separately in outer whole; no invented perroot causal shares or use of Search-only as whole.","whole_until_result_publication_seconds":whole.elapsed().as_secs_f64(),"final_authoritative_whole":"outer lifecycle directwait/finalizer; native receipt alone not completion/benefit PASS","benefit_interpretation":"NOT_ASSESSED; prebound gates need saved matched results and honest cost domains"}),
        )
    })();
    let failed = match output.finalize(outcome, &mut secondary) {
        Ok(result) => return Ok(result),
        Err(e) => e,
    };
    let failure = json!({"schema":"quoridor.continuation360.failure.v1","status":"FAILED","experiment_sha256":bound.sha256,"config_sha256":e.config.sha256,"planned":360,"session_setup_attempts":count.session_setup_attempts,"session_setup_Ok":count.session_setup_ok,"session_setup_Err":count.session_setup_err,"root_replay_attempts":count.attempted,"attempted":count.attempted,"actual_Search_invocations":count.invoked,"returned_Ok":count.ok,"returned_Err":count.err,"completed_requested_depth":count.complete,"durably_published_complete_rows":count.published_complete,"remaining_unknown":360-count.published_complete,"node_liability":count.liability,"last_attempt_or_return":pending,"passes":pass_costs,"root_whole_intervals":root_costs,"primary":fact(&*failed),"secondary":secondary,"INCOMPLETE":true,"outer_completion":"NOT_FINALIZED"});
    // Independent best effort; publication/fallback failures never replace the object.
    if let Err(e) = output.file("failure.json", &failure, 524288) {
        let advisory = json!({"primary":fact(&*failed),"secondary":secondary,"failure_publication":fact(&*e),"failure_close_errors":output.close_errors});
        let _ = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            if let Ok(mut raw) = serde_json::to_vec(&advisory) {
                raw.push(b'\n');
                let _ = std::io::stderr().lock().write_all(&raw);
            }
        }));
    }
    Err(failed)
}

#[cfg(test)]
#[path = "ordering_assessment_tests.rs"]
mod tests;

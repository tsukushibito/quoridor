//! Finite compare-only public API inlet. Retire after the fixed comparison,
//! Git preservation and reader STOP; it is not a second TT implementation.
#![cfg(feature = "research")]

use quoridor_ai::alphabeta::{
    DistanceEvaluator, ResidualEvaluator, SearchLimits, SearchNamespace, SearchSession,
    SearchStats, StaticEvaluator, StopReason,
};
use quoridor_ai::score::ScoreDomain;
use quoridor_core::research::SigmaContext;
use quoridor_nnue::residual::{ResidualManifest, ResidualModel, RouteMode};
use serde_json::{Map, Value, json};
use sha2::{Digest, Sha256};
use std::{
    error::Error,
    fs::{self, File, OpenOptions},
    io::{self, Read, Write},
    path::{Path, PathBuf},
    sync::{Arc, atomic::AtomicBool},
    time::Instant,
};

type PortResult<T> = Result<T, Box<dyn Error>>;
const INPUT_MAX: u64 = 65536;
const JOURNAL_MAX: u64 = 2 * 1024 * 1024;
const PRIVATE_MAX: u64 = 16 * 1024 * 1024;
const RAW_ROOT: &str =
    "/workspaces/quoridor/.worktree/search-optimization/.artifacts/compact-tt359-v1/assessment-raw";
const MANIFEST: &str = "/workspaces/quoridor/.worktree/assets/checkpoints/public-no-bypass-v1/candidate-v1/output/best-model/manifest.json";
const CATALOG: &str = "/workspaces/quoridor/.worktree/search-optimization/.artifacts/compact-tt359-v1/software-controls/root-catalog-v1.json";
const MANIFEST_SHA: &str = "46ec2c4708f96dcf9fad579c2fb0d1299c6663df27412f0faac98267467715e1";
const WEIGHTS_SHA: &str = "046fe926e56b955b0fb7de8f147a74ec33eace9cbc00a55c307f9b6541ab9841";
const BEST43_TYPED: &str = "96a5f41f875022d1752b9c999595ad58bfb2d42687a8f06de08d42b1c4215875";
const WORKLOAD: &[u8] = include_bytes!("compact_tt359_workload.json");
// Root installs exactly one source-map file per serial image. Caller bytes
// are identical; this compile-time metadata is not a run-time algorithm mode.
const BUILT_MAP: &[u8] = include_bytes!(env!("QUORIDOR_TT359_SOURCE_MAP"));

fn sha(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}
fn object<'a>(v: &'a Value, keys: &[&str]) -> PortResult<&'a Map<String, Value>> {
    let m = v.as_object().ok_or("expected object")?;
    if m.len() != keys.len() || keys.iter().any(|k| !m.contains_key(*k)) {
        return Err("missing/extra fields".into());
    }
    Ok(m)
}
fn text<'a>(v: &'a Value, k: &str) -> PortResult<&'a str> {
    v[k].as_str()
        .ok_or_else(|| format!("string required: {k}").into())
}
fn sha_text<'a>(v: &'a Value, k: &str) -> PortResult<&'a str> {
    let s = text(v, k)?;
    if s.len() != 64
        || !s
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
    {
        return Err(format!("lowercase SHA256 required: {k}").into());
    }
    Ok(s)
}
fn decode_reader(reader: impl Read, metadata_len: u64) -> PortResult<Value> {
    if metadata_len > INPUT_MAX {
        return Err("request metadata exceeds cap".into());
    }
    let mut bytes = Vec::new();
    reader.take(INPUT_MAX + 1).read_to_end(&mut bytes)?;
    if bytes.len() as u64 > INPUT_MAX || bytes.len() as u64 != metadata_len {
        return Err("request size changed/exceeds cap".into());
    }
    let v: Value = serde_json::from_slice(&bytes)?;
    // One canonical byte spelling rejects duplicate keys and same-Value edits.
    if serde_json::to_vec(&v)? != bytes {
        return Err("request bytes are not canonical exact JSON".into());
    }
    object(
        &v,
        &[
            "schema",
            "source_map_sha256",
            "workload_sha256",
            "image_sha256",
            "catalog_sha256",
            "output",
        ],
    )?;
    if text(&v, "schema")? != "compact359-public-search-request.v1"
        || sha_text(&v, "source_map_sha256")? != sha(BUILT_MAP)
        || sha_text(&v, "workload_sha256")? != sha(WORKLOAD)
    {
        return Err("request/schema/compiled map/workload mismatch".into());
    }
    sha_text(&v, "image_sha256")?;
    sha_text(&v, "catalog_sha256")?;
    text(&v, "output")?;
    Ok(v)
}
fn read_request(path: &Path) -> PortResult<Value> {
    let m = fs::symlink_metadata(path)?;
    if !m.is_file() || m.len() > INPUT_MAX {
        return Err("request is not a bounded regular file".into());
    }
    decode_reader(File::open(path)?, m.len())
}
fn preflight_output(path: &Path) -> io::Result<()> {
    match fs::symlink_metadata(path) {
        Ok(_) => Err(io::Error::new(
            io::ErrorKind::AlreadyExists,
            "output entry already exists",
        )),
        Err(e) if e.kind() == io::ErrorKind::NotFound => Ok(()),
        Err(e) => Err(e),
    }
}
fn file_sha(path: &Path, maximum: u64) -> PortResult<String> {
    let metadata = fs::symlink_metadata(path)?;
    if !metadata.is_file() || metadata.len() > maximum {
        return Err("identity file is not bounded/regular".into());
    }
    let mut input = File::open(path)?.take(maximum + 1);
    let mut hash = Sha256::new();
    let mut total = 0u64;
    let mut buffer = [0u8; 8192];
    loop {
        let n = input.read(&mut buffer)?;
        if n == 0 {
            break;
        }
        total += n as u64;
        if total > maximum {
            return Err("identity file grew past cap".into());
        }
        hash.update(&buffer[..n]);
    }
    if total != metadata.len() {
        return Err("identity file size changed".into());
    }
    Ok(format!("{:x}", hash.finalize()))
}
fn built_source_map() -> PortResult<Value> {
    let v: Value = serde_json::from_slice(BUILT_MAP)?;
    object(
        &v,
        &[
            "schema",
            "role",
            "representation",
            "caller_sha256",
            "workload_sha256",
            "records",
            "custody",
        ],
    )?;
    if text(&v, "schema")? != "compact359-compiled-source-map.v1"
        || !matches!(text(&v, "role")?, "baseline" | "candidate")
        || sha_text(&v, "caller_sha256")? != sha(include_bytes!("compact_tt359_assessment.rs"))
        || sha_text(&v, "workload_sha256")? != sha(WORKLOAD)
    {
        return Err("compiled source/caller binding".into());
    }
    let records = v["records"].as_array().ok_or("source records array")?;
    if records.is_empty() || records.len() > 128 {
        return Err("source records count".into());
    }
    let mut paths = std::collections::BTreeSet::new();
    for r in records {
        object(r, &["relative", "sha256", "bytes", "mode"])?;
        let p = text(r, "relative")?;
        if !paths.insert(p)
            || Path::new(p).is_absolute()
            || Path::new(p)
                .components()
                .any(|c| !matches!(c, std::path::Component::Normal(_)))
            || r["bytes"].as_u64().is_none()
            || r["mode"].as_u64().is_none()
        {
            return Err("source map path/duplicate/type".into());
        }
        sha_text(r, "sha256")?;
    }
    // Actual embedded compiler inputs, rather than metadata labels alone.
    for (name, bytes) in [
        (
            "crates/quoridor-ai/src/alphabeta.rs",
            include_bytes!("../src/alphabeta.rs").as_slice(),
        ),
        (
            "crates/quoridor-ai/src/lib.rs",
            include_bytes!("../src/lib.rs").as_slice(),
        ),
        (
            "crates/quoridor-ai/src/score.rs",
            include_bytes!("../src/score.rs").as_slice(),
        ),
        (
            "crates/quoridor-core/src/research.rs",
            include_bytes!("../../quoridor-core/src/research.rs").as_slice(),
        ),
        (
            "crates/quoridor-nnue/src/residual.rs",
            include_bytes!("../../quoridor-nnue/src/residual.rs").as_slice(),
        ),
        (
            "crates/quoridor-ai/Cargo.toml",
            include_bytes!("../Cargo.toml").as_slice(),
        ),
        (
            "Cargo.lock",
            include_bytes!("../../../Cargo.lock").as_slice(),
        ),
    ] {
        let row = records
            .iter()
            .find(|r| r["relative"] == name)
            .ok_or("missing built input")?;
        if row["sha256"] != sha(bytes) || row["bytes"] != bytes.len() as u64 {
            return Err(format!("built source differs: {name}").into());
        }
    }
    Ok(v)
}
fn workload() -> PortResult<Value> {
    let v: Value = serde_json::from_slice(WORKLOAD)?;
    object(
        &v,
        &[
            "schema", "roots", "order", "limits", "model", "criteria", "clock",
        ],
    )?;
    if text(&v, "schema")? != "compact359-fixed28-workload.v1"
        || v["order"] != json!(["D", "BEST43"])
        || v["limits"]
            != json!({"depth":4,"nodes":3000000,"time_limit":null,"pvs":true,"tt":true,"slots":4096,"byte_limit":1048576})
        || v["roots"].as_array().is_none_or(|r| r.len() != 7)
        || v["model"]["manifest_sha256"] != MANIFEST_SHA
        || v["model"]["weights_sha256"] != WEIGHTS_SHA
        || v["model"]["typed_evaluator_sha256"] != BEST43_TYPED
    {
        return Err("fixed workload mismatch".into());
    }
    for root in v["roots"].as_array().ok_or("roots")? {
        object(root, &["name", "prefix"])?;
        text(root, "name")?;
        let actions = root["prefix"].as_array().ok_or("prefix")?;
        if actions.len() > 200 || actions.iter().any(|a| a.as_u64().is_none_or(|n| n > 208)) {
            return Err("prefix shape/id".into());
        }
    }
    Ok(v)
}
fn manifest_check(bytes: &[u8]) -> PortResult<ResidualManifest> {
    if bytes.len() != 677 || sha(bytes) != MANIFEST_SHA {
        return Err("BEST43 descriptor identity".into());
    }
    let m: ResidualManifest = serde_json::from_slice(bytes)?;
    if m.weights_sha != WEIGHTS_SHA
        || m.weights != "weights.f32"
        || m.weights_bytes != 49284
        || m.little_endian_f32 != 12321
        || m.topology.ft_width != 32
        || m.topology.hidden_width != 32
        || m.distance_fit.a.to_bits() != 0
        || m.distance_fit.b.to_bits() != 0
        || m.route_mode != RouteMode::Zero4
    {
        return Err("BEST43 no-output-bypass/frame contract".into());
    }
    Ok(m)
}
fn stats(stats: &SearchStats) -> PortResult<Value> {
    // Public Debug includes all numeric fields in both qualified versions.
    // It avoids a private Key dependency or a compatibility adapter for retired
    // counters. Schema/source identifies each counter's actual meaning.
    let debug = format!("{stats:?}");
    let body = debug
        .strip_prefix("SearchStats { ")
        .and_then(|s| s.strip_suffix(" }"))
        .ok_or("unexpected public SearchStats Debug shape")?;
    let mut out = Map::new();
    for field in body.split(", ") {
        let (name, value) = field.split_once(": ").ok_or("counter field")?;
        if name.is_empty()
            || !name.bytes().all(|b| b.is_ascii_lowercase() || b == b'_')
            || out
                .insert(name.into(), Value::from(value.parse::<u64>()?))
                .is_some()
        {
            return Err("counter name/duplicate".into());
        }
    }
    if out.get("nodes") != Some(&Value::from(stats.nodes))
        || out.get("evaluations") != Some(&Value::from(stats.evaluations))
    {
        return Err("counter capture disagreement".into());
    }
    Ok(Value::Object(out))
}
struct Journal {
    file: File,
    bytes: u64,
}
impl Journal {
    fn create(path: &Path) -> PortResult<Self> {
        // preflight refuses known entries/errors; create_new also handles races.
        preflight_output(path)?;
        Ok(Self {
            file: OpenOptions::new().write(true).create_new(true).open(path)?,
            bytes: 0,
        })
    }
    fn append(&mut self, v: &Value) -> PortResult<()> {
        let mut bytes = serde_json::to_vec(v)?;
        bytes.push(b'\n');
        if self
            .bytes
            .checked_add(bytes.len() as u64)
            .is_none_or(|n| n > JOURNAL_MAX)
        {
            return Err("full journal exceeds prospective bound".into());
        }
        self.file.write_all(&bytes)?;
        self.bytes += bytes.len() as u64;
        self.file.flush()?;
        Ok(())
    }
}
fn root_identity(c: &SigmaContext) -> Value {
    let p = c.position();
    json!({"pawns":p.pawns,"stocks":p.walls_remaining,"horizontal":p.horizontal,"vertical":p.vertical,
        "stm":p.turn,"winner":p.winner,"total_ply":c.total_ply(),"rules":c.ruleset().id(),"synthetic":c.is_synthetic(),
        "counted_history":c.history_counts().into_iter().map(|(k,n)|json!([k.history_string(),n])).collect::<Vec<_>>()})
}
fn canonical_catalog() -> PortResult<Value> {
    let w = workload()?;
    let mut roots = Vec::new();
    for fixture in w["roots"].as_array().ok_or("roots")? {
        let prefix: Vec<u16> = serde_json::from_value(fixture["prefix"].clone())?;
        let c = SigmaContext::from_prefix(&prefix)?;
        c.validate_normal()?;
        if c.is_synthetic()
            || c.terminal_value().is_some()
            || usize::from(c.total_ply()) != prefix.len()
        {
            return Err("catalogue root chronology/terminal/ply".into());
        }
        if c.history_counts()
            .iter()
            .map(|(_, n)| u64::from(*n))
            .sum::<u64>()
            != prefix.len() as u64 + 1
        {
            return Err("catalogue root counting".into());
        }
        if fixture["name"] == "genuine-second-occurrence" && c.count(c.position().into()) != 2 {
            return Err("prebound repetition root not second occurrence".into());
        }
        roots.push(json!({"name":fixture["name"],"identity":root_identity(&c)}));
    }
    Ok(
        json!({"schema":"compact359-canonical-root-catalog.v1","workload_sha256":sha(WORKLOAD),"roots":roots}),
    )
}
fn read_catalog(expected_sha: &str) -> PortResult<Value> {
    if file_sha(Path::new(CATALOG), INPUT_MAX)? != expected_sha {
        return Err("frozen catalogue SHA differs".into());
    }
    let m = fs::symlink_metadata(CATALOG)?;
    let mut b = Vec::new();
    File::open(CATALOG)?
        .take(INPUT_MAX + 1)
        .read_to_end(&mut b)?;
    if b.len() as u64 != m.len() || b.len() as u64 > INPUT_MAX || sha(&b) != expected_sha {
        return Err("catalogue changed/cap".into());
    }
    let v: Value = serde_json::from_slice(&b)?;
    if serde_json::to_vec(&v)? != b {
        return Err("catalogue canonical byte spelling".into());
    }
    object(&v, &["schema", "workload_sha256", "roots"])?;
    if text(&v, "schema")? != "compact359-canonical-root-catalog.v1"
        || v["workload_sha256"] != sha(WORKLOAD)
        || v["roots"].as_array().is_none_or(|r| r.len() != 7)
    {
        return Err("catalogue schema/workload/count".into());
    }
    // This is zero Search/evaluator work, charged to process setup; per-case
    // cold replay and equality/correctness are repeated inside each case clock.
    if v != canonical_catalog()? {
        return Err("actual prebound contexts differ from qualified catalogue".into());
    }
    Ok(v)
}
fn one_case(
    evaluator: &Arc<dyn StaticEvaluator>,
    evaluator_id: &str,
    fixture: &Value,
    expected_root: &Value,
    invocations: &mut u64,
) -> PortResult<Value> {
    let whole = Instant::now();
    let prefix: Vec<u16> = serde_json::from_value(fixture["prefix"].clone())?;
    let root = SigmaContext::from_prefix(&prefix)?;
    root.validate_normal()?;
    if root.is_synthetic() || root.terminal_value().is_some() {
        return Err("prebound root is not genuine nonterminal".into());
    }
    let before = root_identity(&root);
    if before != *expected_root {
        return Err("cold root does not match frozen catalogue".into());
    }
    let namespace = SearchNamespace {
        evaluator: evaluator_id.into(),
        rules: root.ruleset().id().into(),
        selectivity: "fullwidth-PVS:contact-solver-continuation-OFF:ScalarFT:guarded-residual-head"
            .into(),
    };
    let mut session = SearchSession::new_with_score_domain(
        evaluator.clone(),
        namespace,
        4096,
        ScoreDomain::LEGACY,
    )?;
    let limits = SearchLimits {
        max_depth: 4,
        max_nodes: 3000000,
        time_limit: None,
        tt_entries: 4096,
        use_pvs: true,
        use_tt: true,
    };
    if session.tt_capacity() != (4096, 1048576) {
        return Err("persistent TT envelope differs".into());
    }
    let initial_memory = session.retained_memory_bytes();
    let cancel = AtomicBool::new(false);
    *invocations += 1;
    let result = session.search(&root, &limits, &cancel)?;
    if result.stop != StopReason::DepthComplete
        || result.completed_depth != 4
        || result.value.is_none_or(|v| !v.is_finite())
        || result.action.is_none()
        || !root
            .legal_ids()
            .contains(&result.action.ok_or("missing action")?)
        || result.pv.first().copied() != result.action
        || result.pv.len() > 4
    {
        return Err(format!("incomplete/invalid returned search: {result:?}").into());
    }
    let mut pv = root.clone();
    for &action in &result.pv {
        if !pv.legal_ids().contains(&action) {
            return Err("illegal PV".into());
        }
        pv = pv.play(action)?;
    }
    drop(pv);
    let after = root_identity(&root);
    if before != after {
        return Err("caller root altered".into());
    }
    let memory = session.retained_memory_bytes();
    if memory.0 > 1048576 || result.stats.tt_retained_bytes > 1048576 {
        return Err("retained table exceeds bound".into());
    }
    let mut row = json!({"kind":"case","root":fixture["name"],"prefix":prefix,"evaluator_identity":evaluator_id,
        "root_identity":before,"requested_depth":4,"completed_depth":result.completed_depth,"stop":format!("{:?}",result.stop),
        "action":result.action,"value":result.value,"value_bits":result.value.map(f32::to_bits),"pv":result.pv,
        "stats":stats(&result.stats)?,"search_elapsed_ns":result.elapsed.as_nanos().to_string(),
        "session_table_before_bytes":initial_memory.0,"session_metadata_before_bytes":initial_memory.1,
        "session_table_after_bytes":memory.0,"session_metadata_after_bytes":memory.1,"root_restored":true});
    // Canonical replay/validation/full count capture/clone/TT/FT/scratch/Search/PV,
    // retained result capture and ephemeral teardown are all inside this clock.
    drop(result);
    drop(session);
    drop(root);
    drop(prefix);
    row["whole_case_ns"] = whole.elapsed().as_nanos().to_string().into();
    Ok(row)
}
fn run(path: &Path) -> PortResult<()> {
    let whole = Instant::now();
    let request = read_request(path)?;
    let built = built_source_map()?;
    let work = workload()?;
    let role = text(&built, "role")?;
    let output = PathBuf::from(text(&request, "output")?);
    let expected_name = format!("{role}.jsonl");
    if output.parent() != Some(Path::new(RAW_ROOT))
        || output.file_name().and_then(|p| p.to_str()) != Some(expected_name.as_str())
    {
        return Err("output not exact owned role path".into());
    }
    preflight_output(&output)?;
    let catalog = read_catalog(sha_text(&request, "catalog_sha256")?)?;
    if file_sha(&std::env::current_exe()?, PRIVATE_MAX)? != text(&request, "image_sha256")? {
        return Err("actual executable identity differs".into());
    }
    let mut journal = Journal::create(&output)?;
    journal.append(&json!({"kind":"header","schema":"compact359-public-search-journal.v1","source":built,
        "source_map_sha256":sha(BUILT_MAP),"workload_sha256":sha(WORKLOAD),"image_sha256":request["image_sha256"],"catalog_sha256":request["catalog_sha256"],
        "planned_returns_this_image":14,"planned_returns_whole":28,"retained_table_is_not_RSS":true,
        "counter_counts_not_machine_instructions":true,"order":["D","BEST43"]}))?;
    let mut completed = 0;
    let mut invocations = 0;
    let outcome: PortResult<()> = (|| {
        for name in ["D", "BEST43"] {
            let evaluator_whole = Instant::now();
            let model_load = Instant::now();
            let (evaluator, identity): (Arc<dyn StaticEvaluator>, String) = if name == "D" {
                let mut bytes = b"QF1-STM-distances-div80-affine-tanh-f32-v1\0".to_vec();
                bytes.extend(0f32.to_le_bytes());
                bytes.extend(8f32.to_le_bytes());
                (
                    Arc::new(DistanceEvaluator::new(0., 8.)),
                    format!("distance-tanh-f32:sha256:{}:LEGACY", sha(&bytes)),
                )
            } else {
                let metadata = fs::symlink_metadata(MANIFEST)?;
                if !metadata.is_file() || metadata.len() != 677 {
                    return Err("descriptor metadata differs".into());
                }
                let mut bytes = Vec::new();
                File::open(MANIFEST)?.take(678).read_to_end(&mut bytes)?;
                manifest_check(&bytes)?;
                let model = Arc::new(ResidualModel::load(MANIFEST)?);
                if sha(&model.fingerprint()) != BEST43_TYPED {
                    return Err("actual loaded typed BEST43 identity differs".into());
                }
                (
                    Arc::new(
                        ResidualEvaluator::new(model)
                            .with_mode(quoridor_nnue::EvaluationMode::Scalar),
                    ),
                    format!(
                        "nnue-residual-f32:sha256:{BEST43_TYPED}:weights={WEIGHTS_SHA}:ScalarFT:guarded-head:no-output-bypass:LEGACY"
                    ),
                )
            };
            journal.append(&json!({"kind":"evaluator_setup","name":name,"identity":identity,
                "setup_ns":model_load.elapsed().as_nanos().to_string(),"timing_not_added_to_nested_cases":true}))?;
            for (root_index, fixture) in work["roots"].as_array().ok_or("roots")?.iter().enumerate()
            {
                journal.append(&json!({"kind":"case_attempt","ordinal":completed,"root":fixture["name"],"prefix":fixture["prefix"],"evaluator":name}))?;
                let row = one_case(
                    &evaluator,
                    &identity,
                    fixture,
                    &catalog["roots"][root_index]["identity"],
                    &mut invocations,
                )?;
                journal.append(&row)?;
                completed += 1;
            }
            drop(evaluator);
            journal.append(&json!({"kind":"evaluator_footer","name":name,
                "whole_evaluator_ns":evaluator_whole.elapsed().as_nanos().to_string(),
                "includes_setup_all_cases_captures_serialization_and_evaluator_drop":true,
                "nested_case_and_search_clocks_not_added":true}))?;
        }
        Ok(())
    })();
    let final_record = journal.append(&json!({"kind":"footer","success":outcome.is_ok(),"completed":completed,"Search_invocations_attempted":invocations,
        "planned":14,"uncompleted":"UNKNOWN, no adaptive retry","primary":outcome.as_ref().err().map(ToString::to_string),
        "whole_before_footer_ns":whole.elapsed().as_nanos().to_string(),"case_clocks_nested_not_added":true,
        "retained_evidence_serialization_model_drop_and_output_cost_in_process":true}));
    let sync = journal.file.sync_all();
    let mut errors = Vec::new();
    if let Err(e) = outcome {
        errors.push(format!("primary: {e}"));
    }
    if let Err(e) = final_record {
        errors.push(format!("independent final-record: {e}"));
    }
    if let Err(e) = sync {
        errors.push(format!("independent sync: {e}"));
    }
    drop(journal);
    if !errors.is_empty() {
        return Err(errors.join("; ").into());
    }
    if completed != 14 {
        return Err("final census differs".into());
    }
    println!(
        "TT359_PUBLIC_RETURNS={completed};WHOLE_PROCESS_NS={}",
        whole.elapsed().as_nanos()
    );
    Ok(())
}

#[test]
#[ignore = "fixed28 numerical admission and qualified exact private/source/model/input required"]
fn compact_tt359_public_assessment() -> PortResult<()> {
    run(Path::new(&std::env::var("QUORIDOR_TT359_REQUEST")?))
}

#[test]
fn compact_tt359_request_exact_bytes_and_caps() -> PortResult<()> {
    let v = json!({"schema":"compact359-public-search-request.v1","source_map_sha256":sha(BUILT_MAP),
        "workload_sha256":sha(WORKLOAD),"image_sha256":"a".repeat(64),"catalog_sha256":"b".repeat(64),"output":"unused"});
    let b = serde_json::to_vec(&v)?;
    assert_eq!(decode_reader(b.as_slice(), b.len() as u64)?, v);
    let padded = format!(" {}", String::from_utf8(b.clone())?);
    assert!(decode_reader(padded.as_bytes(), padded.len() as u64).is_err());
    let duplicate = format!(
        "{{\"schema\":\"wrong\",{}",
        &String::from_utf8(b.clone())?[1..]
    );
    assert!(decode_reader(duplicate.as_bytes(), duplicate.len() as u64).is_err());
    struct MustNotRead;
    impl Read for MustNotRead {
        fn read(&mut self, _: &mut [u8]) -> io::Result<usize> {
            panic!("metadata refusal must precede read")
        }
    }
    assert!(decode_reader(MustNotRead, INPUT_MAX + 1).is_err());
    assert!(decode_reader(io::repeat(b'x'), 1).is_err());
    let mut extra = v;
    extra["extra"] = true.into();
    let b = serde_json::to_vec(&extra)?;
    assert!(decode_reader(b.as_slice(), b.len() as u64).is_err());
    Ok(())
}
#[test]
fn compact_tt359_output_entry_preflight() -> PortResult<()> {
    let base = PathBuf::from(std::env::var("TMPDIR")?)
        .join(format!("tt359-preflight-{}", std::process::id()));
    fs::create_dir(&base)?;
    let result = (|| -> PortResult<()> {
        let file = base.join("regular");
        OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(&file)?;
        let dir = base.join("directory");
        fs::create_dir(&dir)?;
        for p in [&file, &dir] {
            assert_eq!(
                preflight_output(p).unwrap_err().kind(),
                io::ErrorKind::AlreadyExists
            );
        }
        #[cfg(unix)]
        {
            let link = base.join("dangling");
            std::os::unix::fs::symlink(base.join("absent"), &link)?;
            assert_eq!(
                preflight_output(&link).unwrap_err().kind(),
                io::ErrorKind::AlreadyExists
            );
            fs::remove_file(link)?;
        }
        preflight_output(&base.join("unused"))?;
        assert!(preflight_output(&file.join("not-a-directory")).is_err());
        fs::remove_file(file)?;
        fs::remove_dir(dir)?;
        Ok(())
    })();
    // An error leaves owned partial fixtures for the external guardian census.
    result?;
    fs::remove_dir(base)?;
    Ok(())
}
#[test]
fn compact_tt359_compiled_workload_and_public_stats() -> PortResult<()> {
    built_source_map()?;
    let w = workload()?;
    assert_eq!(w["roots"][6]["prefix"].as_array().ok_or("root")?.len(), 200);
    let s = SearchStats {
        nodes: 7,
        evaluations: 3,
        ..Default::default()
    };
    let v = stats(&s)?;
    assert_eq!(v["nodes"], 7);
    assert_eq!(v["evaluations"], 3);
    assert_eq!(v["tt_retained_bytes"], 0);
    assert!(manifest_check(b"{}").is_err());
    // Fresh affected SOFTWARE definition creates the zero-Search catalogue
    // before numeric outcomes. It is frozen/hashed by the external controller.
    let catalog = canonical_catalog()?;
    let output = PathBuf::from(std::env::var("QUORIDOR_TT359_CATALOG_OUT")?);
    if output != Path::new(CATALOG) {
        return Err("owned catalogue path required".into());
    }
    preflight_output(&output)?;
    let bytes = serde_json::to_vec(&catalog)?;
    if bytes.len() as u64 > INPUT_MAX {
        return Err("catalogue cap".into());
    }
    let mut file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(output)?;
    file.write_all(&bytes)?;
    file.sync_all()?;
    drop(file);
    println!(
        "TT359_CATALOG_SHA256={};ROOTS=7;SEARCH_CALLS=0",
        sha(&bytes)
    );
    Ok(())
}

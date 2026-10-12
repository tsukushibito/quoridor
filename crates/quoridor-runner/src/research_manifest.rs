//! One adopted build plus one experiment. Source acceptance belongs to build adoption, not each run.
use crate::{arena, sigma_qualification::BoundControl};
use quoridor_data::Result;
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::{collections::BTreeMap, fs, io::Read, path::PathBuf};

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct FileRef {
    pub path: PathBuf,
    pub sha256: String,
    pub bytes: u64,
    pub mode: String,
}
impl FileRef {
    pub fn verify(&self) -> Result<()> {
        if !self.path.is_absolute()
            || self.path.canonicalize()? != self.path
            || !arena::sha_valid(&self.sha256)
            || fs::symlink_metadata(&self.path)?.file_type().is_symlink()
        {
            return Err("research absolute regular identity required".into());
        }
        let mut options = fs::OpenOptions::new();
        options.read(true);
        #[cfg(unix)]
        {
            use std::os::unix::fs::OpenOptionsExt;
            options.custom_flags(libc::O_NOFOLLOW);
        }
        let file = options.open(&self.path)?;
        let metadata = file.metadata()?;
        if !metadata.is_file() || metadata.len() != self.bytes {
            return Err("research input length/type drift".into());
        }
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            if format!("{:04o}", metadata.permissions().mode() & 0o777) != self.mode {
                return Err("research input custody mode drift".into());
            }
        }
        use sha2::{Digest, Sha256};
        let mut hash = Sha256::new();
        let mut read = 0;
        let mut block = [0u8; 65536];
        let mut file = file.take(self.bytes.saturating_add(1));
        loop {
            let n = file.read(&mut block)?;
            if n == 0 {
                break;
            }
            read += n as u64;
            hash.update(&block[..n]);
        }
        if read != self.bytes || format!("{:x}", hash.finalize()) != self.sha256 {
            return Err("research input hash drift".into());
        }
        Ok(())
    }
    pub fn read<T: serde::de::DeserializeOwned>(&self) -> Result<T> {
        if self.bytes > 1024 * 1024 {
            return Err("research control limit".into());
        }
        self.verify()?;
        BoundControl {
            path: self.path.clone(),
            sha256: self.sha256.clone(),
        }
        .read()
    }
}
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct ModelRef {
    pub descriptor: FileRef,
    pub weights: FileRef,
    pub evaluator_sha256: String,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct LibraryRef {
    pub file: FileRef,
    pub version: String,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Experiment {
    pub schema: String,
    pub phase: String,
    pub build_manifest: FileRef,
    pub config: FileRef,
    pub inputs: Vec<FileRef>,
    pub models: Vec<ModelRef>,
    pub dynamic_libraries: Vec<LibraryRef>,
    pub schedule: FileRef,
    #[serde(default)]
    pub numerical_qualification: Option<FileRef>,
    pub canonical_plan_sha256: String,
    pub rules: String,
    pub distance_units: String,
    pub value_perspective: String,
    pub planned_slots: usize,
    pub batch: Option<usize>,
    pub argv: Vec<String>,
}
pub fn sources() -> BTreeMap<&'static str, String> {
    let mut map = crate::sigma_qualification::sources();
    // Artifact qualification covers the temporary public caller too.
    #[cfg(feature = "ordering-assessment")]
    map.insert(
        "runner/ordering_assessment.rs",
        arena::digest(include_bytes!("ordering_assessment.rs")),
    );
    map.insert(
        "runner/value_search_compare.rs",
        arena::digest(include_bytes!("value_search_compare.rs")),
    );
    map.insert(
        "runner/research_manifest.rs",
        arena::digest(include_bytes!("research_manifest.rs")),
    );
    map
}
pub fn bindings() -> Result<Value> {
    Ok(
        json!({"schema":"quoridor.research.bindings.v1","compiled_sources":sources(),"generator_compiled_sources":crate::teacher_pilot_execution::compiled_sources(),"executable_sha256":crate::arena_manifest::file_sha256(&std::env::current_exe()?)?,"model_calls":0}),
    )
}
fn build_status(build: &Value) -> bool {
    build["schema"] == "quoridor.research.build-manifest.v1"
        && build["status"] == "PASS"
        && build["cleanup_complete"] == true
        && build["remaining"] == json!([])
        && build["checks"].as_array().is_some_and(|checks| {
            ["test", "lint", "build", "bindings"].iter().all(|role| {
                checks.iter().any(|c| {
                    c["role"] == *role
                        && c["guardian_return"]["exit_code"] == 0
                        && c["guardian_return"]["cleanup_complete"] == true
                })
            })
        })
}
/// Generation is a model-free bootstrap, never a numerical qualification.
fn phase_shape(e: &Experiment) -> bool {
    match e.phase.as_str() {
        "generation" => {
            e.numerical_qualification.is_none()
                && e.models.is_empty()
                && e.planned_slots == 0
                && e.batch.is_none()
                && e.argv.len() == 6
                && e.argv[1..]
                    == [
                        "strength-book",
                        "--experiment",
                        "@EXPERIMENT@",
                        "--experiment-sha256",
                        "@EXPERIMENT_SHA256@",
                    ]
        }
        "corpus" => {
            e.numerical_qualification.is_some()
                && e.models.is_empty()
                && e.planned_slots == 8
                && e.batch.is_none()
                && e.argv.len() == 6
                && e.argv[1..]
                    == [
                        "teacher-pilot",
                        "--experiment",
                        "@EXPERIMENT@",
                        "--experiment-sha256",
                        "@EXPERIMENT_SHA256@",
                    ]
        }
        "arena" => {
            e.numerical_qualification.is_some()
                && e.planned_slots > 0
                && e.batch.is_some()
                && e.argv.len() == 6
                && e.argv[1..]
                    == [
                        "arena",
                        "--experiment",
                        "@EXPERIMENT@",
                        "--experiment-sha256",
                        "@EXPERIMENT_SHA256@",
                    ]
        }
        "ordering-qualification" => {
            #[cfg(feature = "ordering-assessment")]
            {
                crate::ordering_assessment::qualification_shape(e)
            }
            #[cfg(not(feature = "ordering-assessment"))]
            {
                false
            }
        }
        "materialize" | "compare" | "analysis" => e.numerical_qualification.is_some(),
        _ => false,
    }
}
fn generation_inputs(e: &Experiment) -> Result<()> {
    let request: crate::value_search_strength::GenerationRequest = e.config.read()?;
    if e.inputs.len() != 2
        || request.plan.sha256 != e.canonical_plan_sha256
        || e.inputs[0].path != request.plan.path
        || e.inputs[0].sha256 != request.plan.sha256
        || e.inputs[1].path != request.old_prefixes.path
        || e.inputs[1].sha256 != request.old_prefixes.sha256
        || !request.output.is_absolute()
    {
        return Err("research generation exact plan/OPEN8 inputs required".into());
    }
    let _: Value = e.inputs[0].read()?;
    let prefixes: Vec<Vec<u16>> = e.inputs[1].read()?;
    let schedule: Value = e.schedule.read()?;
    if arena::json_digest(&prefixes)? != crate::value_search_strength::OLD_PREFIX_SHA256
        || schedule != serde_json::to_value(crate::value_search_strength::schedule())?
    {
        return Err("research generation fixed OPEN8/schedule required".into());
    }
    Ok(())
}

/// Parent authority is the Root-issued admission bound to the immutable RUN intent.
/// Experiment/plan/qualification agreement alone cannot select an approved plan.
fn approved_launch_plan(
    intent: &Value,
    admission: &Value,
    bound: &BoundControl,
    e: &Experiment,
) -> Result<FileRef> {
    let expected: FileRef = serde_json::from_value(intent["approved_plan"].clone())?;
    let experiment: FileRef = serde_json::from_value(intent["experiment"].clone())?;
    if intent["schema"] != "quoridor.research.lifecycle-intent.v1"
        || intent["kind"] != "run"
        || admission["schema"] != "quoridor.research.phase-admission.v1"
        || admission["ready"] != true
        || admission["owner"] != intent["owner"]
        || admission["limits"] != intent["limits"]
        || admission["support_sha256"] != intent["support"]["sha256"]
        || admission["spec_sha256"] != intent["intent_sha256"]
        || admission["approved_plan"] != intent["approved_plan"]
        || experiment.path != bound.path
        || experiment.sha256 != bound.sha256
        || expected.sha256 != e.canonical_plan_sha256
    {
        return Err("integration-issued launch/approved plan mismatch".into());
    }
    Ok(expected)
}
pub(crate) fn approved_arena_plan(bound: &BoundControl, e: &Experiment) -> Result<FileRef> {
    launch_plan(bound, e)
}

#[cfg(feature = "ordering-assessment")]
fn retained_ordering_source(
    current: &Value,
    original: &Value,
    adoption: &Value,
    qualification: &FileRef,
    original_ref: &FileRef,
) -> Result<()> {
    retained_ordering_source_impl(
        current,
        original,
        adoption,
        qualification,
        original_ref,
        None,
    )
}

#[cfg(feature = "ordering-assessment")]
fn retained_ordering_source_impl(
    current: &Value,
    original: &Value,
    adoption: &Value,
    qualification: &FileRef,
    original_ref: &FileRef,
    cost: Option<&Value>,
) -> Result<()> {
    // One source-adoption decision records the reviewed wrapper-only change.
    // Original numerical evidence still describes the ORIGINAL artifact and source.
    let reuse = &adoption["retained_ordering_numerical"];
    let changed = reuse["changed_compiled_sources"]
        .as_object()
        .ok_or("ordering source adoption lacks exact changed FileRefs")?;
    let mut wrappers = vec![
        "runner/ordering_assessment.rs",
        "runner/research_manifest.rs",
    ];
    if let Some(identity) = cost {
        if reuse["ordering372"] != *identity {
            return Err("372 reviewed current input/head reuse correspondence required".into());
        }
        wrappers.push("runner/main.rs");
        if identity["image_role"] == "B" {
            wrappers.extend([
                "ai/alphabeta.rs",
                "ai/static_ordering.rs",
                "ai/continuation_history.rs",
            ]);
        }
    }
    if adoption["schema"] != "quoridor.research.source-adoption.v1"
        || adoption["status"] != "ACCEPTED"
        || adoption["source"] != current["source"]
        || reuse["scope"] != "ordering20-input-and-head-v1"
        || reuse["qualification"] != serde_json::to_value(qualification)?
        || reuse["build_manifest"] != serde_json::to_value(original_ref)?
        || changed.len() != wrappers.len()
        || !wrappers.iter().all(|k| changed.contains_key(*k))
        || !build_status(original)
        || original["source"]["workspace"] != current["source"]["workspace"]
        || original["tools"] != current["tools"]
    {
        return Err("ordering retained numerical source adoption/subject mismatch".into());
    }
    for field in ["manifest", "lock", "cargo_configs"] {
        if original["source"][field] != current["source"][field] {
            return Err("ordering native build input changed".into());
        }
    }
    let release_commands = |subject: &Value| -> Result<Vec<Value>> {
        Ok(subject["checks"]
            .as_array()
            .ok_or("actual build commands")?
            .iter()
            .filter(|c| c["role"] == "build")
            .map(|c| c["argv"].clone())
            .collect())
    };
    if release_commands(original)? != release_commands(current)? {
        return Err("ordering actual release compiler flags changed".into());
    }
    let mut old_env = original["env"]
        .as_object()
        .ok_or("original build environment")?
        .clone();
    let mut new_env = current["env"]
        .as_object()
        .ok_or("current build environment")?
        .clone();
    old_env.remove("TMPDIR");
    new_env.remove("TMPDIR");
    if old_env != new_env {
        return Err("ordering compiler environment changed".into());
    }
    for key in wrappers {
        let pair = &changed[key];
        if pair["before"] != original["source"]["compiled_sources"][key]
            || pair["after"] != current["source"]["compiled_sources"][key]
            || pair["before"]["path"] != pair["after"]["path"]
            || pair["before"]["sha256"] == pair["after"]["sha256"]
        {
            return Err("ordering wrapper before/after source identity mismatch".into());
        }
    }
    for field in ["compiled_sources", "generator_compiled_sources"] {
        let old = original[field]
            .as_object()
            .ok_or("original full source map")?;
        let new = current[field]
            .as_object()
            .ok_or("current full source map")?;
        if old.len() != new.len() || old.keys().ne(new.keys()) {
            return Err("ordering full source domain changed".into());
        }
        for (key, old_sha) in old {
            let new_sha = &new[key];
            if original["source"][field][key]["sha256"] != *old_sha
                || current["source"][field][key]["sha256"] != *new_sha
            {
                return Err("ordering source projection differs from build provenance".into());
            }
            if old_sha != new_sha {
                let pair = changed
                    .get(key)
                    .ok_or("ordering underlying numerical source changed")?;
                if pair["before"]["sha256"] != *old_sha || pair["after"]["sha256"] != *new_sha {
                    return Err("ordering source map differs from adopted wrapper pair".into());
                }
            }
        }
    }
    // Retain all crate/toolchain witnesses, including members outside the embedded map.
    let native = |source: &Value| -> Result<BTreeMap<PathBuf, Value>> {
        let workspace = PathBuf::from(source["workspace"].as_str().ok_or("source workspace")?);
        let files = source["files"].as_array().ok_or("source files")?;
        let mut selected = BTreeMap::new();
        for file in files {
            let path = PathBuf::from(file["path"].as_str().ok_or("source FileRef path")?);
            if (path.starts_with(workspace.join("crates"))
                || path == workspace.join("rust-toolchain.toml"))
                && selected.insert(path, file.clone()).is_some()
            {
                return Err("duplicate numerical native source witness".into());
            }
        }
        Ok(selected)
    };
    let old_files = native(&original["source"])?;
    let new_files = native(&current["source"])?;
    let test_changes = reuse["changed_native_tests"].as_array();
    let reviewed_test = |before: Option<&Value>, after: Option<&Value>| {
        cost.is_some()
            && test_changes.is_some_and(|pairs| {
                pairs.iter().any(|pair| {
                    pair.get("before").filter(|v| !v.is_null()) == before
                        && pair.get("after").filter(|v| !v.is_null()) == after
                        && pair["after"]["path"].as_str().is_some_and(|path| {
                            [
                                "crates/quoridor-ai/src/static360_tests.rs",
                                "crates/quoridor-ai/src/static372_tests.rs",
                                "crates/quoridor-ai/src/continuation372_tests.rs",
                                "crates/quoridor-runner/src/ordering372_tests.rs",
                            ]
                            .iter()
                            .any(|suffix| PathBuf::from(path).ends_with(suffix))
                        })
                })
            })
    };
    if cost.is_none() && old_files.keys().ne(new_files.keys()) {
        return Err("ordering native source membership changed".into());
    }
    for (path, old) in &old_files {
        let Some(new) = new_files.get(path) else {
            return Err("372 native source removal refused".into());
        };
        if *old != *new
            && !reviewed_test(Some(old), Some(new))
            && !changed
                .values()
                .any(|p| p["before"] == *old && p["after"] == *new)
        {
            return Err("ordering native witness outside reviewed wrappers changed".into());
        }
    }
    for (path, new) in &new_files {
        if !old_files.contains_key(path) && !reviewed_test(None, Some(new)) {
            return Err("372 unreviewed native source addition".into());
        }
    }
    Ok(())
}

fn launch_plan(bound: &BoundControl, e: &Experiment) -> Result<FileRef> {
    let path = PathBuf::from(std::env::var("QUORIDOR_LIFECYCLE_INTENT_PATH")?);
    let sha256 = std::env::var("QUORIDOR_LIFECYCLE_INTENT")?;
    let parent = std::env::var("QUORIDOR_LIFECYCLE_PARENT_PID")?.parse::<u32>()?;
    if parent != unsafe { libc::getppid() } as u32 {
        return Err("immediate lifecycle parent required".into());
    }
    let args = fs::read(format!("/proc/{parent}/cmdline"))?;
    let args: Vec<_> = args.split(|&b| b == 0).filter(|s| !s.is_empty()).collect();
    let expected = [
        b"run".as_slice(),
        b"--intent",
        path.as_os_str().as_encoded_bytes(),
        b"--sha256",
        sha256.as_bytes(),
    ];
    if !args.ends_with(&expected) {
        return Err("parent immutable RUN intent argv required".into());
    }
    let intent: Value = BoundControl { path, sha256 }.read()?;
    let admission_ref: FileRef = serde_json::from_value(intent["admission"].clone())?;
    let admission: Value = admission_ref.read()?;
    approved_launch_plan(&intent, &admission, bound, e)
}

/// Validate all entry identities before resources/output/model factory. No recursive review controls.
pub fn load(bound: &BoundControl, phase: &str) -> Result<(Experiment, Value)> {
    let e: Experiment = bound.read()?;
    let approved = launch_plan(bound, &e)?;
    load_checked(
        e,
        bound,
        phase,
        &approved,
        &std::env::args().collect::<Vec<_>>(),
        &std::env::current_exe()?.canonicalize()?,
    )
}
/// Shared preflight; only load() supplies the production integration-issued expectation.
fn load_checked(
    e: Experiment,
    bound: &BoundControl,
    phase: &str,
    approved: &FileRef,
    caller_argv: &[String],
    executable: &std::path::Path,
) -> Result<(Experiment, Value)> {
    if e.schema != "quoridor.research.experiment.v1"
        || e.phase != phase
        || !phase_shape(&e)
        || !arena::sha_valid(&e.canonical_plan_sha256)
        || e.rules != "research-standard-2p-threefold-goal-first-v1"
        || e.distance_units != "wall-distance/80"
        || e.value_perspective != "side-to-move"
        || e.planned_slots > 4096
    {
        return Err("research fixed scientific experiment identity".into());
    }
    if e.canonical_plan_sha256 != approved.sha256 {
        return Err("integration-issued approved plan substitution".into());
    }
    approved.verify()?;
    let expected_argv: Vec<String> = e
        .argv
        .iter()
        .map(|a| {
            a.replace("@EXPERIMENT@", &bound.path.to_string_lossy())
                .replace("@EXPERIMENT_SHA256@", &bound.sha256)
        })
        .collect();
    if expected_argv.as_slice() != caller_argv {
        return Err("research exact prebound caller argv required".into());
    }
    let marker = e.build_manifest.path.with_file_name("INCOMPLETE");
    let build: Value = e.build_manifest.read()?;
    if marker.exists()
        || !build_status(&build)
        || build["compiled_sources"] != serde_json::to_value(sources())?
    {
        return Err("research authoritative matching build manifest required".into());
    }
    let artifact: FileRef = serde_json::from_value(build["artifact"].clone())?;
    artifact.verify()?;
    if artifact.path.as_path() != executable {
        return Err("research same qualified executable required".into());
    }
    e.config.verify()?;
    e.schedule.verify()?;
    for input in &e.inputs {
        input.verify()?;
    }
    for model in &e.models {
        model.descriptor.verify()?;
        model.weights.verify()?;
        let metadata: Value = model.descriptor.read()?;
        if metadata["weights_SHA"] != model.weights.sha256
            || !arena::sha_valid(&model.evaluator_sha256)
            || model.weights.path
                != model
                    .descriptor
                    .path
                    .parent()
                    .ok_or("model parent")?
                    .join("weights.f32")
        {
            return Err("research complete descriptor/weights/evaluator binding".into());
        }
    }
    for library in &e.dynamic_libraries {
        if library.version.trim().is_empty() {
            return Err("research loaded library version required".into());
        }
        library.file.verify()?;
    }
    if phase == "generation" {
        generation_inputs(&e)?;
        return Ok((e, Value::Null));
    }
    if phase == "ordering-qualification" {
        return Ok((e, Value::Null));
    }
    let q: Value = e
        .numerical_qualification
        .as_ref()
        .ok_or("research numerical qualification required")?
        .read()?;
    #[cfg(not(feature = "ordering-assessment"))]
    let numerical_build = build.clone();
    #[cfg(feature = "ordering-assessment")]
    let (q, numerical_build, numerical_subject) = {
        let mut q = q;
        let mut numerical_build = build.clone();
        let mut numerical_subject = None;
        let cost = e.argv.get(1).is_some_and(|a| a == "ordering-cost-assess");
        if cost || e.argv.get(1).is_some_and(|a| a == "ordering-assess") {
            let reference = e.numerical_qualification.as_ref().unwrap();
            if reference
                .path
                .file_name()
                .is_none_or(|n| n != "manifest.json")
                || reference.path.with_file_name("INCOMPLETE").exists()
                || q["schema"] != "quoridor.research.completion.v1"
                || q["status"] != "PASS"
                || q["cleanup_complete"] != true
                || q["remaining"] != json!([])
                || !q["primary"].is_null()
                || q["secondary"] != json!([])
                || q["data"]["status"] != "PASS"
            {
                return Err("360 authoritative finalized input qualification required".into());
            }
            let origin: FileRef = serde_json::from_value(q["experiment"].clone())?;
            let qualified: Experiment = origin.read()?;
            let correspondence = if cost {
                Some(crate::ordering_assessment::retained_cost_inputs(
                    &e, &qualified,
                )?)
            } else {
                None
            };
            if !crate::ordering_assessment::qualification_shape(&qualified)
                || (!cost
                    && (qualified.config != e.config
                        || qualified.schedule != e.schedule
                        || qualified.inputs != e.inputs
                        || qualified.models != e.models
                        || serde_json::to_value(&qualified.dynamic_libraries)?
                            != serde_json::to_value(&e.dynamic_libraries)?))
            {
                return Err("360 qualified experiment/input/model/library drift".into());
            }
            if qualified.build_manifest != e.build_manifest {
                if qualified
                    .build_manifest
                    .path
                    .file_name()
                    .is_none_or(|n| n != "manifest.json")
                    || qualified
                        .build_manifest
                        .path
                        .with_file_name("INCOMPLETE")
                        .exists()
                {
                    return Err("ordering original build is provisional".into());
                }
                let original: Value = qualified.build_manifest.read()?;
                let adoption_ref: FileRef =
                    serde_json::from_value(build["source_adoption"].clone())?;
                let workspace = build["source"]["workspace"]
                    .as_str()
                    .ok_or("source workspace")?;
                if !adoption_ref
                    .path
                    .starts_with(PathBuf::from(workspace).join("research-data"))
                {
                    return Err(
                        "ordering reuse must belong to normal integration source adoption".into(),
                    );
                }
                let adoption: Value = adoption_ref.read()?;
                if cost {
                    retained_ordering_source_impl(
                        &build,
                        &original,
                        &adoption,
                        reference,
                        &qualified.build_manifest,
                        correspondence.as_ref(),
                    )?;
                } else {
                    retained_ordering_source(
                        &build,
                        &original,
                        &adoption,
                        reference,
                        &qualified.build_manifest,
                    )?;
                }
                numerical_build = original;
            }
            if cost && qualified.build_manifest == e.build_manifest {
                return Err("372 new caller cannot use original20 artifact".into());
            }
            q = q["data"]["numerical_qualification"].clone();
            if cost {
                numerical_subject = Some(qualified);
            }
        }
        (q, numerical_build, numerical_subject)
    };
    #[cfg(feature = "ordering-assessment")]
    let subject = numerical_subject.as_ref().unwrap_or(&e);
    #[cfg(not(feature = "ordering-assessment"))]
    let subject = &e;
    if q["schema"] != "quoridor.research.numerical-qualification.v1"
        || q["status"] != "PASS"
        || q["phase"] != phase
        || q["artifact_sha256"] != numerical_build["artifact"]["sha256"]
        || q["compiled_sources_sha256"] != arena::json_digest(&numerical_build["compiled_sources"])?
        || q["config_sha256"] != subject.config.sha256
        || q["schedule_sha256"] != subject.schedule.sha256
        || q["input_sha256"] != json!(subject.inputs.iter().map(|r| &r.sha256).collect::<Vec<_>>())
        || q["descriptor_sha256"]
            != json!(
                subject
                    .models
                    .iter()
                    .map(|m| &m.descriptor.sha256)
                    .collect::<Vec<_>>()
            )
        || q["weights_sha256"]
            != json!(
                subject
                    .models
                    .iter()
                    .map(|m| &m.weights.sha256)
                    .collect::<Vec<_>>()
            )
        || q["evaluator_sha256"]
            != json!(
                subject
                    .models
                    .iter()
                    .map(|m| &m.evaluator_sha256)
                    .collect::<Vec<_>>()
            )
        || q["rules"] != subject.rules
        || q["distance_units"] != subject.distance_units
        || q["value_perspective"] != subject.value_perspective
        || q["remaining"] != json!([])
        || (e.argv.get(1).is_some_and(|a| a == "ordering-cost-assess")
            && q["canonical_plan_sha256"] != subject.canonical_plan_sha256)
        || ((matches!(phase, "arena" | "corpus")
            || e.argv.get(1).is_some_and(|a| a == "ordering-assess"))
            && q["canonical_plan_sha256"] != approved.sha256)
    {
        return Err("research current numerical/history/model/input qualification required".into());
    }
    Ok((e, q))
}
#[cfg(all(test, feature = "ordering-assessment"))]
mod ordering368_source_tests {
    use super::*;

    #[test]
    fn ordering368_reuse_keeps_original_subject_and_rejects_unreviewed_source_or_authority() {
        // Synthetic structural source/adoption facts, never model/numerical evidence.
        let file = |name: &str, sha: &str| json!({"path":format!("/synthetic368/crates/{name}"),"sha256":sha.repeat(64),"bytes":1,"mode":"0644"});
        let a = "runner/ordering_assessment.rs";
        let b = "runner/research_manifest.rs";
        let c = "nnue/residual.rs";
        let old_refs = json!({a:file(a,"1"),b:file(b,"2"),c:file(c,"3")});
        let new_refs = json!({a:file(a,"4"),b:file(b,"5"),c:file(c,"3")});
        let make = |refs: Value, artifact: &str| {
            let map = refs
                .as_object()
                .unwrap()
                .iter()
                .map(|(k, r)| (k.clone(), r["sha256"].clone()))
                .collect::<serde_json::Map<_, _>>();
            json!({"schema":"quoridor.research.build-manifest.v1","status":"PASS","cleanup_complete":true,"remaining":[],
                "checks":(["test","lint","build","bindings"].map(|r|json!({"role":r,"argv":["/synthetic/cargo",r],"guardian_return":{"exit_code":0,"cleanup_complete":true}}))),
                "artifact":{"sha256":artifact.repeat(64)},"compiled_sources":map,"generator_compiled_sources":map,
                "source":{"workspace":"/synthetic368","manifest":file("Cargo.toml","6"),"lock":file("Cargo.lock","7"),"cargo_configs":[],
                    "compiled_sources":refs,"generator_compiled_sources":refs,"files":refs.as_object().unwrap().values().collect::<Vec<_>>()},
                "tools":{"fixture":"UNCHANGED"},"env":{"RUSTFLAGS":"UNCHANGED","TMPDIR":artifact}})
        };
        let original = make(old_refs, "8");
        let current = make(new_refs, "9");
        let reference = |label: &str| FileRef {
            path: format!("/synthetic368/{label}/manifest.json").into(),
            sha256: "a".repeat(64),
            bytes: 1,
            mode: "0644".into(),
        };
        let qualification = reference("qualification");
        let original_ref = reference("original-build");
        let adoption = json!({"schema":"quoridor.research.source-adoption.v1","status":"ACCEPTED","source":current["source"],
            "retained_ordering_numerical":{"scope":"ordering20-input-and-head-v1","qualification":qualification,"build_manifest":original_ref,
                "changed_compiled_sources":{a:{"before":original["source"]["compiled_sources"][a],"after":current["source"]["compiled_sources"][a]},
                    b:{"before":original["source"]["compiled_sources"][b],"after":current["source"]["compiled_sources"][b]}}}});
        retained_ordering_source(
            &current,
            &original,
            &adoption,
            &qualification,
            &original_ref,
        )
        .unwrap();
        assert_ne!(original["artifact"], current["artifact"]);
        for key in [
            "scope",
            "qualification",
            "build_manifest",
            "changed_compiled_sources",
        ] {
            let mut bad = adoption.clone();
            bad["retained_ordering_numerical"]
                .as_object_mut()
                .unwrap()
                .remove(key);
            assert!(
                retained_ordering_source(&current, &original, &bad, &qualification, &original_ref)
                    .is_err()
            );
        }
        let mut bad = adoption.clone();
        bad["retained_ordering_numerical"]["changed_compiled_sources"][a]["after"]["sha256"] =
            json!("f".repeat(64));
        assert!(
            retained_ordering_source(&current, &original, &bad, &qualification, &original_ref)
                .is_err()
        );
        let mut drift = current.clone();
        drift["compiled_sources"][c] = json!("f".repeat(64));
        assert!(
            retained_ordering_source(&drift, &original, &adoption, &qualification, &original_ref)
                .is_err()
        );
        let mut bad = adoption.clone();
        bad["status"] = json!("PENDING");
        assert!(
            retained_ordering_source(&current, &original, &bad, &qualification, &original_ref)
                .is_err()
        );
    }
}

#[cfg(test)]
mod common_corpus_phase_tests {
    use super::*;
    #[test]
    fn corpus_requires_numerical_proof_exact_eight_and_maintained_caller() {
        let r =
            json!({"path":"/synthetic/control","sha256":"0".repeat(64),"bytes":1,"mode":"0644"});
        let mut e:Experiment=serde_json::from_value(json!({"schema":"quoridor.research.experiment.v1",
            "phase":"corpus","build_manifest":r,"config":r,"inputs":[r],"models":[],"dynamic_libraries":[],
            "schedule":r,"numerical_qualification":r,"canonical_plan_sha256":"0".repeat(64),
            "rules":"research-standard-2p-threefold-goal-first-v1","distance_units":"wall-distance/80",
            "value_perspective":"side-to-move","planned_slots":8,"batch":null,
            "argv":["/synthetic/native","teacher-pilot","--experiment","@EXPERIMENT@","--experiment-sha256","@EXPERIMENT_SHA256@"]})).unwrap();
        assert!(phase_shape(&e));
        e.numerical_qualification = None;
        assert!(!phase_shape(&e));
        e.numerical_qualification = Some(serde_json::from_value(r).unwrap());
        e.planned_slots = 0;
        assert!(!phase_shape(&e));
        e.planned_slots = 8;
        e.argv[1] = "strength-book".into();
        assert!(!phase_shape(&e));
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn provisional_or_partial_build_does_not_admit() {
        let mut b = json!({"schema":"quoridor.research.build-manifest.v1","status":"PASS","cleanup_complete":true,"remaining":[],"checks": (["test","lint","build","bindings"].map(|r|json!({"role":r,"guardian_return":{"exit_code":0,"cleanup_complete":true}})))});
        assert!(build_status(&b));
        b["status"] = json!("PENDING_FINALIZATION");
        assert!(!build_status(&b));
        b["status"] = json!("PASS");
        b["checks"][2]["guardian_return"]["cleanup_complete"] = json!(false);
        assert!(!build_status(&b));
    }
    #[test]
    fn missing_asset_refuses_before_any_factory() {
        let r = FileRef {
            path: PathBuf::from("/nonexistent/research-356-model"),
            sha256: "0".repeat(64),
            bytes: 1,
            mode: "0600".into(),
        };
        assert!(r.verify().is_err());
    }
    fn generation_fixture() -> Experiment {
        let r = json!({"path":"/bound/control","sha256":"0".repeat(64),"bytes":1,"mode":"0644"});
        serde_json::from_value(json!({"schema":"quoridor.research.experiment.v1",
            "phase":"generation","build_manifest":r,"config":r,"inputs":[],"models":[],
            "dynamic_libraries":[],"schedule":r,"canonical_plan_sha256":"0".repeat(64),
            "rules":"research-standard-2p-threefold-goal-first-v1","distance_units":"wall-distance/80",
            "value_perspective":"side-to-move","planned_slots":0,"batch":null,
            "argv":["/bound/runner","strength-book","--experiment","@EXPERIMENT@",
                    "--experiment-sha256","@EXPERIMENT_SHA256@"]})).unwrap()
    }
    #[test]
    fn generation_null_and_omitted_are_not_numerical_pass() {
        let e = generation_fixture();
        assert!(phase_shape(&e));
        let mut value = serde_json::to_value(&e).unwrap();
        assert!(value["numerical_qualification"].is_null());
        value
            .as_object_mut()
            .unwrap()
            .remove("numerical_qualification");
        assert!(phase_shape(&serde_json::from_value(value).unwrap()));
    }
    #[test]
    fn generation_option_cannot_escalate_phase_models_or_caller() {
        let e = generation_fixture();
        for phase in ["materialize", "compare", "arena", "analysis", "unknown"] {
            let mut other = e.clone();
            other.phase = phase.into();
            assert!(!phase_shape(&other));
        }
        let mut other = e.clone();
        other.argv[1] = "strength-arena".into();
        assert!(!phase_shape(&other));
        other = e.clone();
        other.planned_slots = 512;
        assert!(!phase_shape(&other));
        other = e.clone();
        other.batch = Some(0);
        assert!(!phase_shape(&other));
        other = e.clone();
        other.numerical_qualification = Some(e.config.clone());
        assert!(!phase_shape(&other));
        other = e.clone();
        other.models.push(ModelRef {
            descriptor: e.config.clone(),
            weights: e.config.clone(),
            evaluator_sha256: "0".repeat(64),
        });
        assert!(!phase_shape(&other));
    }
}

#[cfg(test)]
mod generic_arena_361_launch_tests {
    use super::*;
    use serde_json::json;
    #[test]
    fn generic_arena_361_consistent_substitution_cannot_select_expected_plan() {
        // Synthetic metadata only, no file/model factory. Actual authority helper used by load().
        let r = json!({"path":"/synthetic/plan","sha256":"a".repeat(64),"bytes":1,"mode":"0644"});
        let er =
            json!({"path":"/synthetic/experiment","sha256":"b".repeat(64),"bytes":1,"mode":"0644"});
        let mut e:Experiment=serde_json::from_value(json!({"schema":"quoridor.research.experiment.v1","phase":"arena","build_manifest":r,"config":r,"inputs":[],"models":[],"dynamic_libraries":[],"schedule":r,"numerical_qualification":r,"canonical_plan_sha256":"a".repeat(64),"rules":"research-standard-2p-threefold-goal-first-v1","distance_units":"wall-distance/80","value_perspective":"side-to-move","planned_slots":6,"batch":0,"argv":[]})).unwrap();
        let bound = BoundControl {
            path: "/synthetic/experiment".into(),
            sha256: "b".repeat(64),
        };
        let mut intent = json!({"schema":"quoridor.research.lifecycle-intent.v1","kind":"run","approved_plan":r,"experiment":er,"owner":"/synthetic","limits":{},"support":{"sha256":"c".repeat(64)},"intent_sha256":"d".repeat(64)});
        let admission = json!({"schema":"quoridor.research.phase-admission.v1","ready":true,"approved_plan":r,"owner":"/synthetic","limits":{},"support_sha256":"c".repeat(64),"spec_sha256":"d".repeat(64)});
        assert!(approved_launch_plan(&intent, &admission, &bound, &e).is_ok());
        e.canonical_plan_sha256 = "e".repeat(64);
        let _substituted_q = json!({"canonical_plan_sha256":e.canonical_plan_sha256});
        assert!(approved_launch_plan(&intent, &admission, &bound, &e).is_err());
        intent["approved_plan"]["sha256"] = json!(e.canonical_plan_sha256);
        assert!(approved_launch_plan(&intent, &admission, &bound, &e).is_err());
    }
}

#[cfg(test)]
mod generic_arena_361_bound_entry_tests {
    use super::*;
    use serde_json::json;
    /// Fake artifact/model/Q and caller/executable ports, never execution or qualification.
    #[test]
    fn generic_arena_361_two_bound_io_scopes_cross_actual_load_preflight() {
        let root = std::env::temp_dir().join(format!(
            "arena361-bound-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        fs::create_dir(&root).unwrap();
        struct Cleanup(PathBuf);
        impl Drop for Cleanup {
            fn drop(&mut self) {
                let _ = fs::remove_dir_all(&self.0);
            }
        }
        let _cleanup = Cleanup(root.clone());
        let file = |name: &str, bytes: &[u8]| {
            let path = root.join(name);
            fs::write(&path, bytes).unwrap();
            #[cfg(unix)]
            {
                use std::os::unix::fs::PermissionsExt;
                fs::set_permissions(&path, fs::Permissions::from_mode(0o644)).unwrap();
            }
            FileRef {
                path,
                sha256: arena::digest(bytes),
                bytes: bytes.len() as u64,
                mode: "0644".into(),
            }
        };
        let artifact = file("FAKE_NOT_EXECUTABLE", b"fake");
        let weights = file("weights.f32", b"not model weights");
        let schedule = file("schedule.json", b"[]");
        let book = file("book.json", b"{}");
        for (i, depth, count) in [(0, 4, 4), (1, 5, 6)] {
            let descriptor = file(
                &format!("descriptor-{i}.json"),
                &serde_json::to_vec(&json!({"weights_SHA":weights.sha256})).unwrap(),
            );
            let config = file(
                &format!("config-{i}.json"),
                &serde_json::to_vec(&json!({"fixture_only":true,"depth":depth})).unwrap(),
            );
            let approved = file(
                &format!("approved-{i}.json"),
                &serde_json::to_vec(
                    &json!({"fixture_only":true,"depth":depth,"planned_slots":count}),
                )
                .unwrap(),
            );
            let build=file(&format!("build-{i}.json"),&serde_json::to_vec(&json!({"schema":"quoridor.research.build-manifest.v1","status":"PASS","cleanup_complete":true,"remaining":[],"compiled_sources":sources(),"generator_compiled_sources":crate::teacher_pilot_execution::compiled_sources(),"artifact":artifact,
                "checks":(["test","lint","build","bindings"].map(|r|json!({"role":r,"guardian_return":{"exit_code":0,"cleanup_complete":true}})))})).unwrap());
            let evaluator = arena::digest(format!("fake-evaluator-{i}").as_bytes());
            let q=file(&format!("FAKE-Q-{i}.json"),&serde_json::to_vec(&json!({"fixture_only":"NOT NUMERICAL PROOF","schema":"quoridor.research.numerical-qualification.v1","status":"PASS","phase":"arena","artifact_sha256":artifact.sha256,"compiled_sources_sha256":arena::json_digest(&sources()).unwrap(),"config_sha256":config.sha256,"schedule_sha256":schedule.sha256,"input_sha256":[book.sha256],"descriptor_sha256":[descriptor.sha256],"weights_sha256":[weights.sha256],"evaluator_sha256":[evaluator],"rules":"research-standard-2p-threefold-goal-first-v1","distance_units":"wall-distance/80","value_perspective":"side-to-move","remaining":[],"canonical_plan_sha256":approved.sha256})).unwrap());
            let e = Experiment {
                schema: "quoridor.research.experiment.v1".into(),
                phase: "arena".into(),
                build_manifest: build,
                config,
                inputs: vec![book.clone()],
                models: vec![ModelRef {
                    descriptor,
                    weights: weights.clone(),
                    evaluator_sha256: evaluator,
                }],
                dynamic_libraries: vec![],
                schedule: schedule.clone(),
                numerical_qualification: Some(q),
                canonical_plan_sha256: approved.sha256.clone(),
                rules: "research-standard-2p-threefold-goal-first-v1".into(),
                distance_units: "wall-distance/80".into(),
                value_perspective: "side-to-move".into(),
                planned_slots: count,
                batch: Some(0),
                argv: vec![
                    artifact.path.to_string_lossy().into(),
                    "arena".into(),
                    "--experiment".into(),
                    "@EXPERIMENT@".into(),
                    "--experiment-sha256".into(),
                    "@EXPERIMENT_SHA256@".into(),
                ],
            };
            let er = file(
                &format!("experiment-{i}.json"),
                &serde_json::to_vec(&e).unwrap(),
            );
            let bound = BoundControl {
                path: er.path,
                sha256: er.sha256,
            };
            let argv = e
                .argv
                .iter()
                .map(|a| {
                    a.replace("@EXPERIMENT@", &bound.path.to_string_lossy())
                        .replace("@EXPERIMENT_SHA256@", &bound.sha256)
                })
                .collect::<Vec<_>>();
            let (actual, _) =
                load_checked(e.clone(), &bound, "arena", &approved, &argv, &artifact.path).unwrap();
            assert_eq!(actual.planned_slots, count);
            let other = file("wrong-expected-plan.json", b"substitution");
            assert!(load_checked(e, &bound, "arena", &other, &argv, &artifact.path).is_err());
        }
    }
}

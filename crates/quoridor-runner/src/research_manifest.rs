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
    let q: Value = e
        .numerical_qualification
        .as_ref()
        .ok_or("research numerical qualification required")?
        .read()?;
    if q["schema"] != "quoridor.research.numerical-qualification.v1"
        || q["status"] != "PASS"
        || q["phase"] != phase
        || q["artifact_sha256"] != artifact.sha256
        || q["compiled_sources_sha256"] != arena::json_digest(&sources())?
        || q["config_sha256"] != e.config.sha256
        || q["schedule_sha256"] != e.schedule.sha256
        || q["input_sha256"] != json!(e.inputs.iter().map(|r| &r.sha256).collect::<Vec<_>>())
        || q["descriptor_sha256"]
            != json!(
                e.models
                    .iter()
                    .map(|m| &m.descriptor.sha256)
                    .collect::<Vec<_>>()
            )
        || q["weights_sha256"]
            != json!(
                e.models
                    .iter()
                    .map(|m| &m.weights.sha256)
                    .collect::<Vec<_>>()
            )
        || q["evaluator_sha256"]
            != json!(
                e.models
                    .iter()
                    .map(|m| &m.evaluator_sha256)
                    .collect::<Vec<_>>()
            )
        || q["rules"] != e.rules
        || q["distance_units"] != e.distance_units
        || q["value_perspective"] != e.value_perspective
        || q["remaining"] != json!([])
        || (matches!(phase, "arena" | "corpus") && q["canonical_plan_sha256"] != approved.sha256)
    {
        return Err("research current numerical/history/model/input qualification required".into());
    }
    Ok((e, q))
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

//! One adopted build plus one experiment. Source acceptance belongs to build adoption, not each run.
use crate::{arena, sigma_qualification::BoundControl};
use quoridor_data::Result;
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::{collections::BTreeMap, fs, io::Read, path::PathBuf};

const FIXED_DEPTH_PLAN_SHA256: &str =
    "8bec5174a4f097ad66a870ef59ad6c3ad3e4a741c6d6d0eeedb98c862c3a9ef2";

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
#[derive(Clone, Debug, Serialize, Deserialize)]
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
        json!({"schema":"quoridor.research.bindings.v1","compiled_sources":sources(),"executable_sha256":crate::arena_manifest::file_sha256(&std::env::current_exe()?)?,"model_calls":0}),
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
        "materialize" | "compare" | "arena" | "analysis" => {
            e.numerical_qualification.is_some()
                && (e.planned_slots != 256
                    || (e.phase == "arena" && e.batch.is_some_and(|b| b < 8)))
        }
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
/// Validate all entry identities before resources/output/model factory. No recursive review controls.
pub fn load(bound: &BoundControl, phase: &str) -> Result<(Experiment, Value)> {
    let e: Experiment = bound.read()?;
    if e.schema != "quoridor.research.experiment.v1"
        || e.phase != phase
        || !phase_shape(&e)
        || !arena::sha_valid(&e.canonical_plan_sha256)
        || e.canonical_plan_sha256
            != if e.planned_slots == 256 {
                FIXED_DEPTH_PLAN_SHA256
            } else {
                crate::value_search_strength::PLAN_SHA256
            }
        || (e.planned_slots == 256
            && (e.inputs.len() != 3 || e.inputs[1].sha256 != e.canonical_plan_sha256))
        || e.rules != "research-standard-2p-threefold-goal-first-v1"
        || e.distance_units != "wall-distance/80"
        || e.value_perspective != "side-to-move"
        || !matches!(e.planned_slots, 0 | 256 | 512)
    {
        return Err("research fixed scientific experiment identity".into());
    }
    let expected_argv: Vec<String> = e
        .argv
        .iter()
        .map(|a| {
            a.replace("@EXPERIMENT@", &bound.path.to_string_lossy())
                .replace("@EXPERIMENT_SHA256@", &bound.sha256)
        })
        .collect();
    if expected_argv != std::env::args().collect::<Vec<_>>() {
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
    if artifact.path != std::env::current_exe()?.canonicalize()? {
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
        || (e.planned_slots == 256 && q["canonical_plan_sha256"] != e.canonical_plan_sha256)
    {
        return Err("research current numerical/history/model/input qualification required".into());
    }
    Ok((e, q))
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
    #[test]
    fn fixed_depth256_shape_requires_arena_nonnull_qualification_and_bounded_batch() {
        let mut e = generation_fixture();
        e.phase = "arena".into();
        e.planned_slots = 256;
        e.numerical_qualification = Some(e.config.clone());
        e.batch = Some(0);
        assert!(phase_shape(&e));
        e.batch = None;
        assert!(!phase_shape(&e));
        e.batch = Some(8);
        assert!(!phase_shape(&e));
        e.batch = Some(0);
        e.phase = "compare".into();
        assert!(!phase_shape(&e));
        e.phase = "arena".into();
        e.numerical_qualification = None;
        assert!(!phase_shape(&e));
    }
    #[test]
    fn fixed_depth256_rejects_substituted_actual_plan_with_matching_experiment_and_qualification() {
        use std::os::unix::fs::PermissionsExt;
        let nonce = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let directory =
            std::env::temp_dir().join(format!("research-plan358-{}-{nonce}", std::process::id()));
        fs::create_dir(&directory).unwrap();
        let write_ref = |name: &str, value: &Value| {
            let path = directory.join(name);
            let bytes = serde_json::to_vec(value).unwrap();
            fs::write(&path, &bytes).unwrap();
            FileRef {
                mode: format!(
                    "{:04o}",
                    fs::metadata(&path).unwrap().permissions().mode() & 0o777
                ),
                path,
                sha256: arena::digest(&bytes),
                bytes: bytes.len() as u64,
            }
        };
        let plan = FileRef {
            path: PathBuf::from(
                "/workspaces/quoridor/research-data/ai-sigma/fixed-depth-comparison358/plan.json",
            ),
            sha256: FIXED_DEPTH_PLAN_SHA256.into(),
            bytes: fs::metadata(
                "/workspaces/quoridor/research-data/ai-sigma/fixed-depth-comparison358/plan.json",
            )
            .unwrap()
            .len(),
            mode: "0644".into(),
        };
        plan.verify().unwrap();
        let mut e = generation_fixture();
        e.phase = "arena".into();
        e.planned_slots = 256;
        e.batch = Some(0);
        e.argv = [
            "/bound/runner",
            "arena",
            "--experiment",
            "@EXPERIMENT@",
            "--experiment-sha256",
            "@EXPERIMENT_SHA256@",
        ]
        .map(String::from)
        .to_vec();
        e.inputs = vec![e.config.clone(), plan, e.schedule.clone()];
        e.canonical_plan_sha256 = FIXED_DEPTH_PLAN_SHA256.into();
        e.numerical_qualification = Some(write_ref(
            "qualification.json",
            &json!({"canonical_plan_sha256":e.canonical_plan_sha256}),
        ));
        let attempt = |e: &Experiment| {
            let file = write_ref("experiment.json", &serde_json::to_value(e).unwrap());
            load(
                &BoundControl {
                    path: file.path,
                    sha256: file.sha256,
                },
                "arena",
            )
            .unwrap_err()
            .to_string()
        };
        // Only the early identity gate is exercised: the test harness cannot be the bound caller.
        assert_eq!(attempt(&e), "research exact prebound caller argv required");
        let replacement = write_ref("replacement-plan.json", &json!({"changed_plan":true}));
        replacement.verify().unwrap();
        e.canonical_plan_sha256 = replacement.sha256.clone();
        e.inputs[1] = replacement;
        let q = json!({"canonical_plan_sha256":e.canonical_plan_sha256});
        e.numerical_qualification = Some(write_ref("qualification.json", &q));
        assert_eq!(e.inputs[1].sha256, e.canonical_plan_sha256);
        assert_eq!(q["canonical_plan_sha256"], e.canonical_plan_sha256);
        assert_eq!(attempt(&e), "research fixed scientific experiment identity");
        fs::remove_dir_all(directory).unwrap();
    }
}

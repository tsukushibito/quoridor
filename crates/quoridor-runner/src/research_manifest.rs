//! One adopted build plus one experiment. Source acceptance belongs to build adoption, not each run.
use crate::arena;
use quoridor_data::Result;
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::{fs, io::Read, path::PathBuf};

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct BoundControl {
    pub path: PathBuf,
    pub sha256: String,
}
impl BoundControl {
    pub fn read<T: serde::de::DeserializeOwned>(&self) -> Result<T> {
        if self.sha256.len() != 64
            || !self
                .sha256
                .bytes()
                .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
        {
            return Err("exact lower-case SHA256 required".into());
        }
        if !self.path.is_absolute() || self.path.canonicalize()? != self.path {
            return Err("control path must be canonical absolute".into());
        }
        let mut options = std::fs::OpenOptions::new();
        options.read(true);
        #[cfg(unix)]
        {
            use std::os::unix::fs::OpenOptionsExt;
            options.custom_flags(libc::O_NOFOLLOW);
        }
        let file = options.open(&self.path)?;
        if !file.metadata()?.is_file() {
            return Err("regular control file required".into());
        }
        let mut raw = Vec::new();
        file.take(1024 * 1024 + 1).read_to_end(&mut raw)?;
        if raw.len() as u64 > 1024 * 1024 || crate::arena::digest(&raw) != self.sha256 {
            return Err("control size/SHA mismatch".into());
        }
        Ok(serde_json::from_slice(&raw)?)
    }
}

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
fn build_status(build: &Value) -> bool {
    build["schema"] == "quoridor.research.build-manifest.v1"
        && build["status"] == "PASS"
        && build["cleanup_complete"] == true
        && build["remaining"] == json!([])
        && build["checks"].as_array().is_some_and(|checks| {
            ["test", "lint", "build"].iter().all(|role| {
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
        "compare" if e.argv.get(1).is_some_and(|a| a == "decisions") => {
            e.numerical_qualification.is_some()
                && e.planned_slots > 0
                && e.planned_slots <= 288
                && e.batch.is_some()
                && e.argv.len() == 6
                && e.argv[1..]
                    == [
                        "decisions",
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
    launch_plan(bound, e).map(|(plan, _)| plan)
}

#[cfg(feature = "ordering-assessment")]
fn retained_ordering_source(
    current: &Value,
    original: &Value,
    adoption: &Value,
    qualification: &FileRef,
    original_ref: &FileRef,
    cheap: Option<&Value>,
) -> Result<()> {
    // One source-adoption decision records the reviewed wrapper-only change.
    // Original numerical evidence still describes the ORIGINAL artifact and source.
    let reuse = &adoption["retained_ordering_numerical"];
    if reuse.as_object().is_none_or(|fields| {
        fields.len() != 3 + usize::from(cheap.is_some())
            || !["scope", "qualification", "build_manifest"]
                .iter()
                .all(|key| fields.contains_key(*key))
            || (cheap.is_some() && !fields.contains_key("cheap_static376"))
    }) {
        return Err("single adopted numerical scope required; no source graph".into());
    }
    if adoption["schema"] != "quoridor.research.source-adoption.v1"
        || adoption["status"] != "ACCEPTED"
        || adoption["source"] != current["source"]
        || reuse["scope"] != "ordering20-input-and-head-v1"
        || reuse["qualification"] != serde_json::to_value(qualification)?
        || reuse["build_manifest"] != serde_json::to_value(original_ref)?
        || cheap.is_some_and(|identity| reuse["cheap_static376"] != *identity)
        || !build_status(original)
        || original["source"]["workspace"] != current["source"]["workspace"]
    {
        return Err("ordering retained numerical adoption/subject mismatch".into());
    }
    // This exact accepted Source owns the independently reviewed input/head scope
    // correspondence. Cargo and its artifact record own the new image, not a
    // second embedded source graph. The ORIGINAL numerical artifact stays original.
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
    // Keep the original input/head native compiler/codegen subject. Current
    // BUILD/RUN own other tools and runtime inputs, including controller Python.
    if !original["tools"]["RUSTC"].is_object()
        || !original["tools"]["RUSTC"]["file"].is_object()
        || original["tools"]["RUSTC"]["version"]
            .as_str()
            .is_none_or(|version| version.trim().is_empty())
        || original["tools"]["RUSTC"] != current["tools"]["RUSTC"]
    {
        return Err("ordering native compiler changed".into());
    }
    for flag in [
        "RUSTFLAGS",
        "CARGO_PROFILE_RELEASE_OPT_LEVEL",
        "CARGO_PROFILE_RELEASE_DEBUG",
    ] {
        if !original["env"][flag].is_string() || original["env"][flag] != current["env"][flag] {
            return Err("ordering native release flags changed".into());
        }
    }
    // Compare recorded Cargo/Rust configuration, not the runtime environment.
    // All profiles, target/compiler selectors, flags, wrappers and rustup
    // selection belong here. Conservatively require even non-codegen Cargo
    // settings to match; unrecorded effective configuration remains unknown.
    let native_environment = |subject: &Value| -> Result<serde_json::Map<String, Value>> {
        let env = subject["env"]
            .as_object()
            .ok_or("native build environment")?;
        let recorded: serde_json::Map<String, Value> = env
            .iter()
            .filter(|(key, _)| key.starts_with("CARGO") || key.starts_with("RUST"))
            .map(|(key, value)| (key.clone(), value.clone()))
            .collect();
        if recorded.values().any(|value| !value.is_string()) {
            return Err("recorded native configuration values".into());
        }
        Ok(recorded)
    };
    if native_environment(original)? != native_environment(current)? {
        return Err("ordering recorded native configuration changed".into());
    }
    Ok(())
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct LaunchIdentity {
    pid: u32,
    start_ticks: String,
    boot_id: String,
}
fn launch_identity(pid: u32) -> Result<(LaunchIdentity, u32)> {
    let raw = fs::read_to_string(format!("/proc/{pid}/stat"))?;
    let fields: Vec<_> = raw
        .rsplit_once(')')
        .ok_or("process stat")?
        .1
        .split_whitespace()
        .collect();
    let start = fields.get(19).ok_or("process start ticks")?.to_string();
    start.parse::<u64>()?;
    let parent = fields.get(1).ok_or("process parent")?.parse()?;
    Ok((
        LaunchIdentity {
            pid,
            start_ticks: start,
            boot_id: fs::read_to_string("/proc/sys/kernel/random/boot_id")?
                .trim()
                .to_string(),
        },
        parent,
    ))
}
fn launch_argv(pid: u32) -> Result<Vec<String>> {
    fs::read(format!("/proc/{pid}/cmdline"))?
        .split(|&b| b == 0)
        .filter(|s| !s.is_empty())
        .map(|s| String::from_utf8(s.to_vec()).map_err(Into::into))
        .collect()
}
fn check_perf_chain(
    identities: (&LaunchIdentity, &LaunchIdentity, &LaunchIdentity),
    parents: (u32, u32),
    executable: (&Path, &FileRef),
    arguments: (&[String], &[String]),
) -> Result<()> {
    let (expected_guardian, guardian, profiler) = identities;
    let (profiler_parent, immediate) = parents;
    let (executable, tool) = executable;
    let (actual_argv, argv) = arguments;
    if guardian.pid == immediate
        || profiler.pid != immediate
        || expected_guardian != guardian
        || profiler_parent != guardian.pid
        || executable != tool.path
        || actual_argv != argv
        || guardian.boot_id != profiler.boot_id
    {
        return Err("actual guardian/perf/native chain drift".into());
    }
    Ok(())
}
fn perf_launch_shape(
    intent: &Value,
    e: &Experiment,
    bound: &BoundControl,
) -> Result<Option<(FileRef, Vec<String>)>> {
    let native: Vec<String> = e
        .argv
        .iter()
        .map(|a| {
            a.replace("@EXPERIMENT@", &bound.path.to_string_lossy())
                .replace("@EXPERIMENT_SHA256@", &bound.sha256)
        })
        .collect();
    let config: Value = e.config.read()?;
    let selected = e.phase == "compare"
        && e.argv.get(1).is_some_and(|a| a == "ordering-cheap-assess")
        && config["schema"] == "quoridor.current-search-perf349.process.v1";
    let sampled = selected
        && config["process_index"]
            .as_u64()
            .is_some_and(|n| n < 6 && n % 3 == 1);
    if !sampled {
        if !intent["perf"].is_null() || intent["argv"] != json!(native) {
            return Err("direct native launch argv required".into());
        }
        return Ok(None);
    }
    if intent["perf"]
        .as_object()
        .is_none_or(|p| p.len() != 2 || !p.contains_key("tool") || !p.contains_key("output"))
        || intent["support"] != config["plan"]["resources"]
        || intent["support"]["sha256"]
            != "22e2138fe41ddbe142aa05f01ea1e30367219b2465195f4db5b4878e7dd1bf6b"
        || e.planned_slots != 6
        || e.batch.map(|n| json!(n)) != Some(config["process_index"].clone())
    {
        return Err("349 sampled launch authority required".into());
    }
    let tool: FileRef = serde_json::from_value(intent["perf"]["tool"].clone())?;
    let output =
        PathBuf::from(intent["output"].as_str().ok_or("owning operation path")?).join("perf.data");
    let owner = PathBuf::from(intent["owner"].as_str().ok_or("launch owner")?);
    if tool.path != PathBuf::from("/usr/bin/perf")
        || tool.bytes > 16 * 1048576
        || !output.is_absolute()
        || !output.starts_with(&owner)
        || intent["perf"]["output"] != json!(output)
        || output
            .parent()
            .ok_or("perf output parent")?
            .canonicalize()?
            .join("perf.data")
            != output
    {
        return Err("349 standard perf tool/output required".into());
    }
    let mut argv: Vec<String> = [
        "/usr/bin/perf",
        "record",
        "-e",
        "cpu-clock:u",
        "-F",
        "49",
        "--call-graph",
        "dwarf,8192",
        "-m",
        "64",
        "--max-size",
        "12M",
        "--no-buildid-cache",
        "-o",
    ]
    .map(str::to_string)
    .into();
    argv.push(output.to_string_lossy().to_string());
    argv.push("--".into());
    argv.extend(native);
    if intent["argv"] != json!(argv) {
        return Err("349 exact perf/native argv required".into());
    }
    Ok(Some((tool, argv)))
}
fn launch_plan(bound: &BoundControl, e: &Experiment) -> Result<(FileRef, Value)> {
    let path = PathBuf::from(std::env::var("QUORIDOR_LIFECYCLE_INTENT_PATH")?);
    let sha256 = std::env::var("QUORIDOR_LIFECYCLE_INTENT")?;
    let parent = std::env::var("QUORIDOR_LIFECYCLE_PARENT_PID")?.parse::<u32>()?;
    let intent: Value = BoundControl {
        path: path.clone(),
        sha256: sha256.clone(),
    }
    .read()?;
    let admission_ref: FileRef = serde_json::from_value(intent["admission"].clone())?;
    let admission: Value = admission_ref.read()?;
    let approved = approved_launch_plan(&intent, &admission, bound, e)?;
    let immediate = unsafe { libc::getppid() } as u32;
    let origin = if let Some((tool, argv)) = perf_launch_shape(&intent, e, bound)? {
        let expected: LaunchIdentity =
            serde_json::from_str(&std::env::var("QUORIDOR_LIFECYCLE_PARENT_IDENTITY")?)?;
        let (guardian, _) = launch_identity(parent)?;
        let (profiler, profiler_parent) = launch_identity(immediate)?;
        check_perf_chain(
            (&expected, &guardian, &profiler),
            (profiler_parent, immediate),
            (&fs::canonicalize(format!("/proc/{immediate}/exe"))?, &tool),
            (&launch_argv(immediate)?, &argv),
        )?;
        tool.verify()?;
        if launch_identity(immediate)?.0 != profiler || launch_identity(parent)?.0 != guardian {
            return Err("launch process identity changed during admission".into());
        }
        json!({"guardian":guardian,"profiler":profiler,"native":launch_identity(std::process::id())?.0,"perf_tool":tool,"perf_argv":argv})
    } else {
        if parent != immediate {
            return Err("immediate lifecycle parent required".into());
        }
        let config: Value = e.config.read()?;
        if config["schema"] == "quoridor.current-search-perf349.process.v1" {
            let expected: LaunchIdentity =
                serde_json::from_str(&std::env::var("QUORIDOR_LIFECYCLE_PARENT_IDENTITY")?)?;
            let guardian = launch_identity(parent)?.0;
            if expected != guardian {
                return Err("349 direct guardian identity drift".into());
            }
            json!({"guardian":guardian,"native":launch_identity(std::process::id())?.0})
        } else {
            Value::Null
        }
    };
    let args = launch_argv(parent)?;
    let expected = [
        "run".to_string(),
        "--intent".to_string(),
        path.to_string_lossy().to_string(),
        "--sha256".to_string(),
        sha256,
    ];
    if !args.ends_with(&expected) {
        return Err("parent immutable RUN intent argv required".into());
    }
    Ok((approved, origin))
}

/// Validate all entry identities before resources/output/model factory. No recursive review controls.
pub fn load(bound: &BoundControl, phase: &str) -> Result<(Experiment, Value)> {
    let e: Experiment = bound.read()?;
    let (approved, origin) = launch_plan(bound, &e)?;
    let (e, mut q) = load_checked(
        e,
        bound,
        phase,
        &approved,
        &std::env::args().collect::<Vec<_>>(),
        &std::env::current_exe()?.canonicalize()?,
    )?;
    if !origin.is_null() {
        q["runtime_launch_origin"] = origin;
    }
    Ok((e, q))
}
#[cfg(test)]
mod perf349_launch_tests {
    use super::*;
    #[test]
    fn perf349_exact_chain_rejects_pid_boot_start_executable_and_argv_drift() {
        let guardian = LaunchIdentity {
            pid: 10,
            start_ticks: "100".into(),
            boot_id: "boot".into(),
        };
        let profiler = LaunchIdentity {
            pid: 11,
            start_ticks: "101".into(),
            boot_id: "boot".into(),
        };
        let tool = FileRef {
            path: "/usr/bin/perf".into(),
            sha256: "a".repeat(64),
            bytes: 1,
            mode: "0750".into(),
        };
        let argv = vec!["/usr/bin/perf".to_string(), "record".into()];
        let check = |expected: &LaunchIdentity,
                     actual: &LaunchIdentity,
                     p: &LaunchIdentity,
                     parent,
                     exe: &Path,
                     args: &[String]| {
            check_perf_chain(
                (expected, actual, p),
                (parent, 11),
                (exe, &tool),
                (args, &argv),
            )
        };
        assert!(check(&guardian, &guardian, &profiler, 10, &tool.path, &argv).is_ok());
        let mut wrong = guardian.clone();
        wrong.start_ticks = "99".into();
        assert!(check(&wrong, &guardian, &profiler, 10, &tool.path, &argv).is_err());
        wrong = guardian.clone();
        wrong.boot_id = "other".into();
        assert!(check(&wrong, &guardian, &profiler, 10, &tool.path, &argv).is_err());
        let mut p = profiler.clone();
        p.pid = 12;
        assert!(check(&guardian, &guardian, &p, 10, &tool.path, &argv).is_err());
        p = profiler.clone();
        p.boot_id = "other".into();
        assert!(check(&guardian, &guardian, &p, 10, &tool.path, &argv).is_err());
        assert!(check(&guardian, &guardian, &profiler, 99, &tool.path, &argv).is_err());
        assert!(
            check(
                &guardian,
                &guardian,
                &profiler,
                10,
                Path::new("/fake/perf"),
                &argv
            )
            .is_err()
        );
        assert!(
            check(
                &guardian,
                &guardian,
                &profiler,
                10,
                &tool.path,
                &["wrong".into()]
            )
            .is_err()
        );
    }
    #[test]
    fn perf349_only_exact_sampled_wrapper_and_plain_direct_argv_admit() {
        struct Temp(PathBuf);
        impl Drop for Temp {
            fn drop(&mut self) {
                let _ = fs::remove_dir_all(&self.0);
            }
        }
        let stamp = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let dir =
            std::env::temp_dir().join(format!("perf349-metadata-{}-{stamp}", std::process::id()));
        fs::create_dir(&dir).unwrap();
        let _cleanup = Temp(dir.clone());
        let config_path = dir.join("config.json");
        let write_config = |process| {
            let raw = serde_json::to_vec(&json!({"schema":"quoridor.current-search-perf349.process.v1","process_index":process,"plan":{"resources":{"sha256":"22e2138fe41ddbe142aa05f01ea1e30367219b2465195f4db5b4878e7dd1bf6b"}}})).unwrap();
            fs::write(&config_path, &raw).unwrap();
            use std::os::unix::fs::PermissionsExt;
            fs::set_permissions(&config_path, fs::Permissions::from_mode(0o644)).unwrap();
            FileRef {
                path: config_path.clone(),
                sha256: arena::digest(&raw),
                bytes: raw.len() as u64,
                mode: "0644".into(),
            }
        };
        let mut e: Experiment = serde_json::from_value(json!({"schema":"quoridor.research.experiment.v1","phase":"compare","build_manifest":write_config(1),"config":write_config(1),"inputs":[],"models":[],"dynamic_libraries":[],"schedule":write_config(1),"numerical_qualification":null,"canonical_plan_sha256":"a".repeat(64),"rules":"unused","distance_units":"unused","value_perspective":"unused","planned_slots":6,"batch":1,"argv":["/fake/current-image","ordering-cheap-assess","--experiment","@EXPERIMENT@","--experiment-sha256","@EXPERIMENT_SHA256@"]})).unwrap();
        let bound = BoundControl {
            path: dir.join("experiment.json"),
            sha256: "b".repeat(64),
        };
        let config: Value = e.config.read().unwrap();
        let mut intent = json!({"owner":dir,"output":dir,"support":config["plan"]["resources"],"perf":{"tool":{"path":"/usr/bin/perf","sha256":"c".repeat(64),"bytes":1,"mode":"0750"},"output":dir.join("perf.data")}});
        let native: Vec<String> = e
            .argv
            .iter()
            .map(|a| {
                a.replace("@EXPERIMENT@", &bound.path.to_string_lossy())
                    .replace("@EXPERIMENT_SHA256@", &bound.sha256)
            })
            .collect();
        let mut argv: Vec<String> = [
            "/usr/bin/perf",
            "record",
            "-e",
            "cpu-clock:u",
            "-F",
            "49",
            "--call-graph",
            "dwarf,8192",
            "-m",
            "64",
            "--max-size",
            "12M",
            "--no-buildid-cache",
            "-o",
        ]
        .map(str::to_string)
        .into();
        argv.push(dir.join("perf.data").to_string_lossy().into());
        argv.push("--".into());
        argv.extend(native.clone());
        intent["argv"] = json!(argv);
        assert!(perf_launch_shape(&intent, &e, &bound).unwrap().is_some());
        for index in [5usize, 7, 11, 16] {
            let mut wrong = intent.clone();
            wrong["argv"][index] = json!("wrong");
            assert!(perf_launch_shape(&wrong, &e, &bound).is_err());
        }
        e.config = write_config(0);
        e.batch = Some(0);
        assert!(perf_launch_shape(&intent, &e, &bound).is_err());
        intent["perf"] = Value::Null;
        intent["argv"] = json!(native);
        assert!(perf_launch_shape(&intent, &e, &bound).unwrap().is_none());
        intent["argv"][0] = json!("/fake/other-image");
        assert!(perf_launch_shape(&intent, &e, &bound).is_err());
    }
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
    if marker.exists() || !build_status(&build) {
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
        let cheap = e.argv.get(1).is_some_and(|a| a == "ordering-cheap-assess");
        if cheap || e.argv.get(1).is_some_and(|a| a == "ordering-assess") {
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
            let correspondence = if cheap {
                Some(crate::ordering_assessment::retained_cheap_inputs(
                    &e, &qualified,
                )?)
            } else {
                None
            };
            if !crate::ordering_assessment::qualification_shape(&qualified)
                || (!cheap
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
                retained_ordering_source(
                    &build,
                    &original,
                    &adoption,
                    reference,
                    &qualified.build_manifest,
                    correspondence.as_ref(),
                )?;
                numerical_build = original;
            }
            if cheap {
                if qualified.build_manifest == e.build_manifest {
                    return Err("376 requires genuinely new caller/image; old20 is not80".into());
                }
                numerical_subject = Some(qualified);
            }
            q = q["data"]["numerical_qualification"].clone();
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
        || (e.argv.get(1).is_some_and(|a| a == "ordering-cheap-assess")
            && q["canonical_plan_sha256"] != subject.canonical_plan_sha256)
        || ((matches!(phase, "arena" | "corpus")
            || e.argv
                .get(1)
                .is_some_and(|a| matches!(a.as_str(), "ordering-assess" | "decisions")))
            && q["canonical_plan_sha256"] != approved.sha256)
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
        let mut b = json!({"schema":"quoridor.research.build-manifest.v1","status":"PASS","cleanup_complete":true,"remaining":[],"checks": (["test","lint","build"].map(|r|json!({"role":r,"guardian_return":{"exit_code":0,"cleanup_complete":true}})))});
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
            let build=file(&format!("build-{i}.json"),&serde_json::to_vec(&json!({"schema":"quoridor.research.build-manifest.v1","status":"PASS","cleanup_complete":true,"remaining":[],"artifact":artifact,
                "checks":(["test","lint","build"].map(|r|json!({"role":r,"guardian_return":{"exit_code":0,"cleanup_complete":true}})))})).unwrap());
            let evaluator = arena::digest(format!("fake-evaluator-{i}").as_bytes());
            let q=file(&format!("FAKE-Q-{i}.json"),&serde_json::to_vec(&json!({"fixture_only":"NOT NUMERICAL PROOF","schema":"quoridor.research.numerical-qualification.v1","status":"PASS","phase":"arena","artifact_sha256":artifact.sha256,"config_sha256":config.sha256,"schedule_sha256":schedule.sha256,"input_sha256":[book.sha256],"descriptor_sha256":[descriptor.sha256],"weights_sha256":[weights.sha256],"evaluator_sha256":[evaluator],"rules":"research-standard-2p-threefold-goal-first-v1","distance_units":"wall-distance/80","value_perspective":"side-to-move","remaining":[],"canonical_plan_sha256":approved.sha256})).unwrap());
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

#[cfg(all(test, feature = "ordering-assessment"))]
mod build379_provenance_tests {
    use super::*;
    #[test]
    fn build379_retained_input_scope_never_relabels_original_image() {
        let make = |commit: &str, artifact: &str| {
            json!({
                "schema":"quoridor.research.build-manifest.v1","status":"PASS",
                "cleanup_complete":true,"remaining":[],
                "checks":(["test","lint","build"].map(|r|json!({"role":r,"argv":["cargo",r],
                    "guardian_return":{"exit_code":0,"cleanup_complete":true}}))),
                "artifact":{"sha256":artifact.repeat(64)},
                "source":{"workspace":"/synthetic379","commit":commit.repeat(40),"patch":null,
                    "manifest":{"sha256":"1".repeat(64)},"lock":{"sha256":"2".repeat(64)},"cargo_configs":[]},
                "tools":{"RUSTC":{"file":{"path":"/synthetic379/rustc","sha256":"7".repeat(64),
                    "bytes":1,"mode":"0755"},"version":"fixed native compiler"},"PYTHON":"old-controller"},
                "env":{"RUSTFLAGS":"unchanged","CARGO_PROFILE_RELEASE_OPT_LEVEL":"3",
                    "CARGO_PROFILE_RELEASE_DEBUG":"0","TMPDIR":commit}
            })
        };
        let original = make("a", "3");
        let current = make("b", "4");
        let reference = |name: &str| FileRef {
            path: format!("/synthetic379/{name}/manifest.json").into(),
            sha256: "5".repeat(64),
            bytes: 1,
            mode: "0644".into(),
        };
        let qualification = reference("qualification");
        let original_ref = reference("original");
        let adoption = json!({"schema":"quoridor.research.source-adoption.v1","status":"ACCEPTED",
            "source":current["source"],"retained_ordering_numerical":{
                "scope":"ordering20-input-and-head-v1","qualification":qualification,"build_manifest":original_ref}});
        retained_ordering_source(
            &current,
            &original,
            &adoption,
            &qualification,
            &original_ref,
            None,
        )
        .unwrap();
        assert_ne!(original["artifact"], current["artifact"]);
        for key in ["scope", "qualification", "build_manifest"] {
            let mut bad = adoption.clone();
            bad["retained_ordering_numerical"]
                .as_object_mut()
                .unwrap()
                .remove(key);
            assert!(
                retained_ordering_source(
                    &current,
                    &original,
                    &bad,
                    &qualification,
                    &original_ref,
                    None
                )
                .is_err()
            );
        }
        for (key, value) in [
            ("status", json!("FAILED")),
            ("source", json!({"commit":"wrong"})),
        ] {
            let mut bad = adoption.clone();
            bad[key] = value;
            assert!(
                retained_ordering_source(
                    &current,
                    &original,
                    &bad,
                    &qualification,
                    &original_ref,
                    None
                )
                .is_err()
            );
        }
        let mut runtime_changed = current.clone();
        runtime_changed["tools"]["PYTHON"] = json!("current-controller");
        runtime_changed["env"]["OMP_NUM_THREADS"] = json!("1");
        runtime_changed["env"]["CUDA_VISIBLE_DEVICES"] = json!("");
        retained_ordering_source(
            &runtime_changed,
            &original,
            &adoption,
            &qualification,
            &original_ref,
            None,
        )
        .unwrap();
        assert_eq!(original["tools"]["PYTHON"], json!("old-controller"));
        assert!(original["env"]["OMP_NUM_THREADS"].is_null());
        for (section, key) in [
            ("tools", "RUSTC"),
            ("env", "RUSTFLAGS"),
            ("env", "CARGO_PROFILE_RELEASE_OPT_LEVEL"),
            ("env", "CARGO_PROFILE_RELEASE_DEBUG"),
        ] {
            let mut bad = runtime_changed.clone();
            bad[section][key] = json!("drift");
            assert!(
                retained_ordering_source(
                    &bad,
                    &original,
                    &adoption,
                    &qualification,
                    &original_ref,
                    None
                )
                .is_err()
            );
        }
        // The current-only LTO counterexample leaves every prior fact/ref equal.
        let mut lto = runtime_changed.clone();
        lto["env"]["CARGO_PROFILE_RELEASE_LTO"] = json!("fat");
        assert_eq!(lto["tools"], runtime_changed["tools"]);
        assert_eq!(lto["checks"], runtime_changed["checks"]);
        assert_eq!(lto["source"], runtime_changed["source"]);
        assert!(
            retained_ordering_source(
                &lto,
                &original,
                &adoption,
                &qualification,
                &original_ref,
                None
            )
            .is_err()
        );
        for channel in [
            "CARGO_ENCODED_RUSTFLAGS",
            "RUSTC_WRAPPER",
            "RUSTC_WORKSPACE_WRAPPER",
            "CARGO_BUILD_RUSTC_WRAPPER",
            "CARGO_BUILD_RUSTC_WORKSPACE_WRAPPER",
            "CARGO_TARGET_X86_64_UNKNOWN_LINUX_GNU_RUSTFLAGS",
            "CARGO_BUILD_TARGET",
            "RUSTUP_TOOLCHAIN",
            "CARGO_NET_OFFLINE",
        ] {
            for original_side in [false, true] {
                for value in ["-Ctarget-cpu=native", ""] {
                    let mut old = original.clone();
                    let mut now = runtime_changed.clone();
                    let subject = if original_side { &mut old } else { &mut now };
                    subject["env"][channel] = json!(value);
                    assert!(
                        retained_ordering_source(
                            &now,
                            &old,
                            &adoption,
                            &qualification,
                            &original_ref,
                            None
                        )
                        .is_err()
                    );
                }
            }
        }
        for (section, key) in [
            ("tools", "RUSTC"),
            ("env", "RUSTFLAGS"),
            ("env", "CARGO_PROFILE_RELEASE_OPT_LEVEL"),
            ("env", "CARGO_PROFILE_RELEASE_DEBUG"),
        ] {
            for original_side in [false, true] {
                let mut old = original.clone();
                let mut now = runtime_changed.clone();
                let subject = if original_side { &mut old } else { &mut now };
                subject[section].as_object_mut().unwrap().remove(key);
                assert!(
                    retained_ordering_source(
                        &now,
                        &old,
                        &adoption,
                        &qualification,
                        &original_ref,
                        None
                    )
                    .is_err()
                );
            }
        }
        // Equally malformed declarations must not satisfy typed correspondence.
        let mut malformed_old = original.clone();
        let mut malformed_now = runtime_changed.clone();
        malformed_old["tools"]["RUSTC"] = json!("not a ToolRef");
        malformed_now["tools"]["RUSTC"] = json!("not a ToolRef");
        assert!(
            retained_ordering_source(
                &malformed_now,
                &malformed_old,
                &adoption,
                &qualification,
                &original_ref,
                None
            )
            .is_err()
        );
        malformed_old = original.clone();
        malformed_now = runtime_changed.clone();
        malformed_old["env"]["CARGO_PROFILE_RELEASE_LTO"] = Value::Null;
        malformed_now["env"]["CARGO_PROFILE_RELEASE_LTO"] = Value::Null;
        assert!(
            retained_ordering_source(
                &malformed_now,
                &malformed_old,
                &adoption,
                &qualification,
                &original_ref,
                None
            )
            .is_err()
        );
        for field in ["manifest", "lock", "cargo_configs"] {
            let mut bad = runtime_changed.clone();
            bad["source"][field] = json!("drift");
            let mut adopted = adoption.clone();
            adopted["source"] = bad["source"].clone();
            assert!(
                retained_ordering_source(
                    &bad,
                    &original,
                    &adopted,
                    &qualification,
                    &original_ref,
                    None
                )
                .is_err()
            );
        }
        let mut bad_release = runtime_changed.clone();
        bad_release["checks"][2]["argv"] = json!(["cargo", "different-release"]);
        assert!(
            retained_ordering_source(
                &bad_release,
                &original,
                &adoption,
                &qualification,
                &original_ref,
                None
            )
            .is_err()
        );
        let identity = json!({"algorithm":"synthetic unchanged input/head scope"});
        assert!(
            retained_ordering_source(
                &current,
                &original,
                &adoption,
                &qualification,
                &original_ref,
                Some(&identity)
            )
            .is_err()
        );
        let mut paired = adoption.clone();
        paired["retained_ordering_numerical"]["cheap_static376"] = identity.clone();
        retained_ordering_source(
            &current,
            &original,
            &paired,
            &qualification,
            &original_ref,
            Some(&identity),
        )
        .unwrap();
        paired["retained_ordering_numerical"]["obsolete_source_graph"] = json!({});
        assert!(
            retained_ordering_source(
                &current,
                &original,
                &paired,
                &qualification,
                &original_ref,
                Some(&identity)
            )
            .is_err()
        );
    }
}

#[cfg(test)]
mod bound_control_tests {
    use super::*;
    #[test]
    fn bounded_control_uses_exact_hashed_bytes_and_refuses_growth() {
        use std::sync::atomic::{AtomicU64, Ordering};
        static SERIAL: AtomicU64 = AtomicU64::new(0);
        let root = std::env::temp_dir().join(format!(
            "sigma-control-{}-{}",
            std::process::id(),
            SERIAL.fetch_add(1, Ordering::Relaxed)
        ));
        std::fs::create_dir(&root).unwrap();
        let path = root.join("control.json");
        std::fs::write(&path, b"{}").unwrap();
        let bound = BoundControl {
            path: path.canonicalize().unwrap(),
            sha256: crate::arena::digest(b"{}"),
        };
        assert!(bound.read::<serde_json::Value>().is_ok());
        std::fs::write(&path, vec![b' '; (1024 * 1024 + 1) as usize]).unwrap();
        assert!(
            bound
                .read::<serde_json::Value>()
                .unwrap_err()
                .to_string()
                .contains("size/SHA")
        );
        std::fs::remove_file(path).unwrap();
        std::fs::remove_dir(root).unwrap();
    }
}

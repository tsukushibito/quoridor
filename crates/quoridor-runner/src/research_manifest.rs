//! One adopted build plus one experiment. Source acceptance belongs to build adoption, not each run.
use crate::arena;
use quoridor_data::Result;
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::{
    fs,
    io::Read,
    path::{Path, PathBuf},
};

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
    #[serde(default)]
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
        "compare" if e.argv.get(1).is_some_and(|a| a == "measure") => e.models.len() == 1,
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
    launch_plan(bound, e)?
        .0
        .ok_or_else(|| "arena approved plan missing".into())
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
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct PerfSettings {
    tool: FileRef,
    output: PathBuf,
    event: String,
    frequency_hz: u64,
    call_graph: String,
    ring_pages: u64,
    data_max_bytes: u64,
    no_buildid_cache: bool,
}
/// The caller has verified the actual tool/argv/parent chain. Bind RAW to that
/// live profiler's writable FD, not merely to a file left at the configured path.
fn profiler_open_raw(profiler: &LaunchIdentity, output: &std::path::Path) -> Result<Value> {
    use std::os::unix::fs::{MetadataExt, OpenOptionsExt};
    if launch_identity(profiler.pid)?.0 != *profiler
        || !fs::symlink_metadata(output)?.is_file()
        || output.canonicalize()? != output
    {
        return Err("live profiler regular RAW identity required".into());
    }
    let raw = fs::OpenOptions::new()
        .read(true)
        .custom_flags(libc::O_NOFOLLOW | libc::O_NONBLOCK | libc::O_CLOEXEC)
        .open(output)?;
    let metadata = raw.metadata()?;
    if !metadata.is_file() || metadata.uid() != unsafe { libc::geteuid() } {
        return Err("profiler RAW regular owner required".into());
    }
    for entry in fs::read_dir(format!("/proc/{}/fd", profiler.pid))? {
        let entry = entry?;
        let fd_path = entry.path();
        let Ok(target) = fs::read_link(&fd_path) else {
            continue;
        };
        if target != output {
            continue;
        }
        let Ok(opened) = fs::metadata(&fd_path) else {
            continue;
        };
        if !opened.is_file() || opened.dev() != metadata.dev() || opened.ino() != metadata.ino() {
            continue;
        }
        let fd = entry.file_name().to_string_lossy().parse::<u32>()?;
        let info = fs::read_to_string(format!("/proc/{}/fdinfo/{fd}", profiler.pid))?;
        let flags = u32::from_str_radix(
            info.lines()
                .find_map(|line| line.strip_prefix("flags:").map(str::trim))
                .ok_or("profiler FD flags")?,
            8,
        )?;
        let access = flags & libc::O_ACCMODE as u32;
        if access != libc::O_WRONLY as u32 && access != libc::O_RDWR as u32 {
            continue;
        }
        let current = fs::symlink_metadata(output)?;
        let still_open = fs::metadata(&fd_path)?;
        if !current.is_file()
            || current.dev() != metadata.dev()
            || current.ino() != metadata.ino()
            || still_open.dev() != metadata.dev()
            || still_open.ino() != metadata.ino()
            || fs::read_link(&fd_path)? != output
            || launch_identity(profiler.pid)?.0 != *profiler
        {
            return Err("profiler RAW/FD/process drift".into());
        }
        return Ok(
            json!({"path":output,"profiler":profiler,"fd":fd,"device":metadata.dev(),"inode":metadata.ino(),"uid":metadata.uid(),"flags_octal":format!("{flags:o}")}),
        );
    }
    Err("configured RAW is not open for writing by verified profiler".into())
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
    if intent["perf"].is_null() {
        if intent["argv"] != json!(native) {
            return Err("direct native launch argv required".into());
        }
        return Ok(None);
    }
    if !e.argv.get(1).is_some_and(|a| a == "measure") {
        return Err("standard profiling belongs to measurement entry".into());
    }
    let perf: PerfSettings = serde_json::from_value(intent["perf"].clone())?;
    let owner = PathBuf::from(intent["owner"].as_str().ok_or("launch owner")?);
    let output = &perf.output;
    let data_root = PathBuf::from(intent["data_root"].as_str().ok_or("native output root")?);
    if perf.event.is_empty()
        || perf.call_graph.is_empty()
        || perf.event.contains('\0')
        || perf.call_graph.contains('\0')
        || perf.frequency_hz == 0
        || !perf.ring_pages.is_power_of_two()
        || perf.data_max_bytes == 0
        || !output.is_absolute()
        || output == &owner
        || !output.starts_with(&owner)
        || output == &data_root
        || output.parent() != data_root.parent()
        || output
            .parent()
            .ok_or("perf output parent")?
            .canonicalize()?
            .join(output.file_name().ok_or("perf filename")?)
            != *output
    {
        return Err("standard perf settings/output shape".into());
    }
    let mut argv = vec![
        perf.tool.path.to_string_lossy().to_string(),
        "record".into(),
        "-e".into(),
        perf.event,
        "-F".into(),
        perf.frequency_hz.to_string(),
        "--call-graph".into(),
        perf.call_graph,
        "-m".into(),
        perf.ring_pages.to_string(),
        "--max-size".into(),
        perf.data_max_bytes.to_string(),
    ];
    if perf.no_buildid_cache {
        argv.push("--no-buildid-cache".into());
    }
    argv.extend([
        "-o".into(),
        output.to_string_lossy().to_string(),
        "--".into(),
    ]);
    argv.extend(native);
    if intent["argv"] != json!(argv) {
        return Err("actual configured perf/native argv required".into());
    }
    Ok(Some((perf.tool, argv)))
}
fn launch_plan(bound: &BoundControl, e: &Experiment) -> Result<(Option<FileRef>, Value)> {
    let path = PathBuf::from(std::env::var("QUORIDOR_LIFECYCLE_INTENT_PATH")?);
    let sha256 = std::env::var("QUORIDOR_LIFECYCLE_INTENT")?;
    let parent = std::env::var("QUORIDOR_LIFECYCLE_PARENT_PID")?.parse::<u32>()?;
    let intent: Value = BoundControl {
        path: path.clone(),
        sha256: sha256.clone(),
    }
    .read()?;
    let approved = if e.argv.get(1).is_some_and(|a| a == "measure") {
        let actual: FileRef = serde_json::from_value(intent["experiment"].clone())?;
        if intent["kind"] != "run" || actual.path != bound.path || actual.sha256 != bound.sha256 {
            return Err("actual measurement RUN settings identity".into());
        }
        None
    } else {
        let admission_ref: FileRef = serde_json::from_value(intent["admission"].clone())?;
        let admission: Value = admission_ref.read()?;
        Some(approved_launch_plan(&intent, &admission, bound, e)?)
    };
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
        let raw = profiler_open_raw(
            &profiler,
            &PathBuf::from(intent["perf"]["output"].as_str().ok_or("perf RAW output")?),
        )?;
        if launch_identity(immediate)?.0 != profiler || launch_identity(parent)?.0 != guardian {
            return Err("launch process identity changed during admission".into());
        }
        json!({"guardian":guardian,"profiler":profiler,"native":launch_identity(std::process::id())?.0,"perf_tool":tool,"perf_argv":argv,"perf_RAW_open":raw})
    } else {
        if parent != immediate {
            return Err("immediate lifecycle parent required".into());
        }
        if e.argv.get(1).is_some_and(|a| a == "measure") {
            let expected: LaunchIdentity =
                serde_json::from_str(&std::env::var("QUORIDOR_LIFECYCLE_PARENT_IDENTITY")?)?;
            let guardian = launch_identity(parent)?.0;
            if expected != guardian {
                return Err("direct guardian identity drift".into());
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
    Ok((
        approved,
        json!({"runtime_launch_origin":origin,"environment":intent["env"],"perf":intent["perf"]}),
    ))
}

/// Validate all entry identities before resources/output/model factory. No recursive review controls.
pub fn load(bound: &BoundControl, phase: &str) -> Result<(Experiment, Value)> {
    let e: Experiment = bound.read()?;
    let (approved, origin) = launch_plan(bound, &e)?;
    let (e, mut q) = load_checked(
        e,
        bound,
        phase,
        approved.as_ref(),
        &std::env::args().collect::<Vec<_>>(),
        &std::env::current_exe()?.canonicalize()?,
    )?;
    if e.argv.get(1).is_some_and(|a| a == "measure") {
        q = origin;
    } else if !origin["runtime_launch_origin"].is_null() {
        q["runtime_launch_origin"] = origin["runtime_launch_origin"].clone();
    }
    Ok((e, q))
}

#[cfg(test)]
mod measurement_launch_tests {
    use super::*;
    #[test]
    fn measurement_configured_perf_and_actual_chain_shape() {
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
            std::env::temp_dir().join(format!("measurement-origin-{}-{stamp}", std::process::id()));
        fs::create_dir(&dir).unwrap();
        let _temp = Temp(dir.clone());
        let reference = FileRef {
            path: dir.join("unread-control"),
            sha256: "0".repeat(64),
            bytes: 1,
            mode: "0644".into(),
        };
        let bound = BoundControl {
            path: dir.join("settings.json"),
            sha256: "1".repeat(64),
        };
        let e:Experiment=serde_json::from_value(json!({"schema":"quoridor.research.experiment.v1","phase":"compare","build_manifest":reference,"config":reference,"schedule":reference,"inputs":[],"models":[],"dynamic_libraries":[],"rules":"standard","distance_units":"wall-distance/80","value_perspective":"side-to-move","planned_slots":2,"batch":null,"argv":["/native","measure","--experiment","@EXPERIMENT@","--experiment-sha256","@EXPERIMENT_SHA256@"]})).unwrap();
        let native = e
            .argv
            .iter()
            .map(|a| {
                a.replace("@EXPERIMENT@", &bound.path.to_string_lossy())
                    .replace("@EXPERIMENT_SHA256@", &bound.sha256)
            })
            .collect::<Vec<_>>();
        let direct = json!({"argv":native});
        assert!(perf_launch_shape(&direct, &e, &bound).unwrap().is_none());
        for (frequency, pages, graph) in [(17, 8, "dwarf,4096"), (49, 64, "dwarf,8192")] {
            let tool = FileRef {
                path: "/usr/bin/perf".into(),
                sha256: "2".repeat(64),
                bytes: 1,
                mode: "0755".into(),
            };
            let output = dir.join("sample.data");
            let mut argv = vec![
                "/usr/bin/perf".to_string(),
                "record".into(),
                "-e".into(),
                "cpu-clock:u".into(),
                "-F".into(),
                frequency.to_string(),
                "--call-graph".into(),
                graph.into(),
                "-m".into(),
                pages.to_string(),
                "--max-size".into(),
                "12582912".into(),
                "--no-buildid-cache".into(),
                "-o".into(),
                output.to_string_lossy().to_string(),
                "--".into(),
            ];
            argv.extend(native.clone());
            let mut intent = json!({"owner":dir,"data_root":dir.join("native"),"perf":{"tool":tool,"output":output,"event":"cpu-clock:u","frequency_hz":frequency,"call_graph":graph,"ring_pages":pages,"data_max_bytes":12582912,"no_buildid_cache":true},"argv":argv});
            assert!(perf_launch_shape(&intent, &e, &bound).unwrap().is_some());
            intent["perf"]["frequency_hz"] = json!(0);
            assert!(perf_launch_shape(&intent, &e, &bound).is_err());
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
            assert!(
                check_perf_chain(
                    (&guardian, &guardian, &profiler),
                    (10, 11),
                    (&tool.path, &tool),
                    (&argv, &argv)
                )
                .is_ok()
            );
            assert!(
                check_perf_chain(
                    (&guardian, &guardian, &profiler),
                    (9, 11),
                    (&tool.path, &tool),
                    (&argv, &argv)
                )
                .is_err()
            );
            let mut wrong = profiler.clone();
            wrong.start_ticks = "previous".into();
            assert!(
                check_perf_chain(
                    (&wrong, &guardian, &profiler),
                    (10, 11),
                    (&tool.path, &tool),
                    (&argv, &argv)
                )
                .is_err()
            );
            assert!(
                check_perf_chain(
                    (&guardian, &guardian, &profiler),
                    (10, 11),
                    (Path::new("/other"), &tool),
                    (&argv, &argv)
                )
                .is_err()
            );
        }
    }
}
/// Shared preflight; only load() supplies the production integration-issued expectation.
fn load_checked(
    e: Experiment,
    bound: &BoundControl,
    phase: &str,
    approved: Option<&FileRef>,
    caller_argv: &[String],
    executable: &std::path::Path,
) -> Result<(Experiment, Value)> {
    let measurement = e.argv.get(1).is_some_and(|a| a == "measure");
    if e.schema != "quoridor.research.experiment.v1"
        || e.phase != phase
        || !phase_shape(&e)
        || (!measurement && !arena::sha_valid(&e.canonical_plan_sha256))
        || e.rules != "research-standard-2p-threefold-goal-first-v1"
        || e.distance_units != "wall-distance/80"
        || e.value_perspective != "side-to-move"
        || e.planned_slots > 4096
    {
        return Err("research fixed scientific experiment identity".into());
    }
    if !measurement {
        let approved = approved.ok_or("approved plan missing")?;
        if e.canonical_plan_sha256 != approved.sha256 {
            return Err("integration-issued approved plan substitution".into());
        }
        approved.verify()?;
    }
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
    if measurement {
        return Ok((e, Value::Null));
    }
    let q: Value = e
        .numerical_qualification
        .as_ref()
        .ok_or("research numerical qualification required")?
        .read()?;
    let numerical_build = build;
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
        || ((matches!(phase, "arena" | "corpus")
            || e.argv.get(1).is_some_and(|a| a.as_str() == "decisions"))
            && q["canonical_plan_sha256"] != approved.ok_or("approved plan missing")?.sha256)
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
            let (actual, _) = load_checked(
                e.clone(),
                &bound,
                "arena",
                Some(&approved),
                &argv,
                &artifact.path,
            )
            .unwrap();
            assert_eq!(actual.planned_slots, count);
            let other = file("wrong-expected-plan.json", b"substitution");
            assert!(load_checked(e, &bound, "arena", Some(&other), &argv, &artifact.path).is_err());
        }
    }
}

#[cfg(test)]
mod profiler_raw_tests {
    use super::*;
    #[test]
    fn measurement_profiler_raw_live_fd_stale_foreign_symlink_and_identity() {
        use std::os::fd::AsRawFd;
        use std::os::unix::fs::symlink;
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
        let dir = std::env::temp_dir().join(format!("profiler-raw-{}-{stamp}", std::process::id()));
        fs::create_dir(&dir).unwrap();
        let _temp = Temp(dir.clone());
        let output = dir.join("perf.data");
        let profiler = launch_identity(std::process::id()).unwrap().0;
        assert!(profiler_open_raw(&profiler, &output).is_err());
        let writer = fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&output)
            .unwrap();
        let evidence = profiler_open_raw(&profiler, &output).unwrap();
        assert_eq!(evidence["fd"], json!(writer.as_raw_fd()));
        let mut wrong = profiler.clone();
        wrong.start_ticks.push('0');
        assert!(profiler_open_raw(&wrong, &output).is_err());
        wrong.pid = 0;
        assert!(profiler_open_raw(&wrong, &output).is_err());
        drop(writer);
        assert!(profiler_open_raw(&profiler, &output).is_err());
        let reader = fs::File::open(&output).unwrap();
        assert!(profiler_open_raw(&profiler, &output).is_err());
        drop(reader);
        let other = dir.join("foreign.data");
        let foreign_writer = fs::File::create(&other).unwrap();
        assert!(profiler_open_raw(&profiler, &output).is_err());
        drop(foreign_writer);
        let stale_writer = fs::OpenOptions::new().write(true).open(&output).unwrap();
        fs::remove_file(&output).unwrap();
        fs::write(&output, b"replacement").unwrap();
        assert!(profiler_open_raw(&profiler, &output).is_err());
        drop(stale_writer);
        fs::remove_file(&output).unwrap();
        let live_writer = fs::OpenOptions::new().write(true).open(&other).unwrap();
        symlink(&other, &output).unwrap();
        assert!(profiler_open_raw(&profiler, &output).is_err());
        drop(live_writer);
        fs::remove_file(&output).unwrap();
        fs::create_dir(&output).unwrap();
        assert!(profiler_open_raw(&profiler, &output).is_err());
    }
}

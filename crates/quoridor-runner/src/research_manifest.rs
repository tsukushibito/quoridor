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
                && e.planned_slots > 0
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
/// Arena selection belongs to the finite job's settings. Preserve the actual
/// intent/experiment/plan identity without a separate admission for each pair.
fn configured_arena_plan(intent: &Value, bound: &BoundControl, e: &Experiment) -> Result<FileRef> {
    let plan: FileRef = serde_json::from_value(intent["approved_plan"].clone())?;
    let experiment: FileRef = serde_json::from_value(intent["experiment"].clone())?;
    if intent["schema"] != "quoridor.research.lifecycle-intent.v1"
        || intent["kind"] != "run"
        || (e.phase != "arena"
            && !(e.phase == "compare" && e.argv.get(1).is_some_and(|a| a == "decisions")))
        || experiment.path != bound.path
        || experiment.sha256 != bound.sha256
        || plan.sha256 != e.canonical_plan_sha256
    {
        return Err("actual arena settings/experiment/plan identity mismatch".into());
    }
    Ok(plan)
}
/// The finite job selects existing configured corpus RUNs once. Each actual
/// child retains the original config/input identity, without a batch admission file.
fn configured_run_plan(intent: &Value, bound: &BoundControl, e: &Experiment) -> Result<FileRef> {
    let settings_ref: FileRef = serde_json::from_value(intent["settings"].clone())?;
    let settings: Value = settings_ref.read()?;
    let index = intent["selection_index"]
        .as_u64()
        .ok_or("finite RUN index")? as usize;
    let template = settings["runs"]
        .as_array()
        .and_then(|runs| runs.get(index))
        .ok_or("selected finite RUN index")?;
    let original_ref: FileRef = serde_json::from_value(template["experiment"].clone())?;
    let original: Experiment = original_ref.read()?;
    let actual: FileRef = serde_json::from_value(intent["experiment"].clone())?;
    let plan: FileRef = serde_json::from_value(intent["approved_plan"].clone())?;
    if intent["schema"] != "quoridor.research.lifecycle-intent.v1"
        || settings["kind"] != "sequence"
        || intent["kind"] != "run"
        || e.phase != "corpus"
        || template["finalizers"] != json!([])
        || actual.path != bound.path
        || actual.sha256 != bound.sha256
        || serde_json::to_value(e)? != serde_json::to_value(original)?
        || plan.sha256 != e.canonical_plan_sha256
    {
        return Err("selected finite RUN experiment/config identity".into());
    }
    for key in [
        "owner",
        "cwd",
        "limits",
        "support",
        "artifact",
        "caller_sources",
        "approved_plan",
        "data_root",
        "data",
        "finalizers",
    ] {
        if intent[key] != template[key] {
            return Err(format!("selected finite RUN settings drift: {key}").into());
        }
    }
    Ok(plan)
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
fn profiler_io<T>(
    operation: &str,
    path: &Path,
    pid: u32,
    fd: Option<u32>,
    result: std::io::Result<T>,
) -> Result<T> {
    result.map_err(|error| {
        format!(
            "profiler origin {operation}: path={} pid={pid} fd={fd:?} errno={:?}: {error}",
            path.display(),
            error.raw_os_error(),
        )
        .into()
    })
}

/// The caller has verified the actual tool/argv/parent chain. Bind RAW to that
/// live profiler's writable FD, not merely to a file left at the configured path.
fn profiler_open_raw(profiler: &LaunchIdentity, output: &std::path::Path) -> Result<Value> {
    use std::os::unix::fs::{MetadataExt, OpenOptionsExt};
    if launch_identity(profiler.pid)?.0 != *profiler
        || !profiler_io(
            "symlink_metadata RAW",
            output,
            profiler.pid,
            None,
            fs::symlink_metadata(output),
        )?
        .is_file()
        || profiler_io(
            "canonicalize RAW",
            output,
            profiler.pid,
            None,
            output.canonicalize(),
        )? != output
    {
        return Err("live profiler regular RAW identity required".into());
    }
    let raw = profiler_io(
        "open RAW",
        output,
        profiler.pid,
        None,
        fs::OpenOptions::new()
            .read(true)
            .custom_flags(libc::O_NOFOLLOW | libc::O_NONBLOCK | libc::O_CLOEXEC)
            .open(output),
    )?;
    let metadata = profiler_io("fstat RAW", output, profiler.pid, None, raw.metadata())?;
    if !metadata.is_file() || metadata.uid() != unsafe { libc::geteuid() } {
        return Err("profiler RAW regular owner required".into());
    }
    let directory = PathBuf::from(format!("/proc/{}/fd", profiler.pid));
    let mut inaccessible_fd = None;
    for entry in profiler_io(
        "read_dir",
        &directory,
        profiler.pid,
        None,
        fs::read_dir(&directory),
    )? {
        let entry = profiler_io("read_dir entry", &directory, profiler.pid, None, entry)?;
        let fd_path = entry.path();
        let target = match fs::read_link(&fd_path) {
            Ok(target) => target,
            Err(error) => {
                if error.kind() == std::io::ErrorKind::PermissionDenied && inaccessible_fd.is_none()
                {
                    inaccessible_fd = profiler_io::<()>(
                        "read_link FD",
                        &fd_path,
                        profiler.pid,
                        entry.file_name().to_string_lossy().parse().ok(),
                        Err(error),
                    )
                    .err();
                }
                continue;
            }
        };
        if target != output {
            continue;
        }
        let opened = match fs::metadata(&fd_path) {
            Ok(opened) => opened,
            Err(error) => {
                if inaccessible_fd.is_none() {
                    inaccessible_fd = profiler_io::<()>(
                        "stat RAW FD",
                        &fd_path,
                        profiler.pid,
                        entry.file_name().to_string_lossy().parse().ok(),
                        Err(error),
                    )
                    .err();
                }
                continue;
            }
        };
        if !opened.is_file() || opened.dev() != metadata.dev() || opened.ino() != metadata.ino() {
            continue;
        }
        let fd = entry.file_name().to_string_lossy().parse::<u32>()?;
        let info_path = PathBuf::from(format!("/proc/{}/fdinfo/{fd}", profiler.pid));
        let info = profiler_io(
            "read fdinfo",
            &info_path,
            profiler.pid,
            Some(fd),
            fs::read_to_string(&info_path),
        )?;
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
        let current = profiler_io(
            "recheck RAW",
            output,
            profiler.pid,
            Some(fd),
            fs::symlink_metadata(output),
        )?;
        let still_open = profiler_io(
            "recheck FD",
            &fd_path,
            profiler.pid,
            Some(fd),
            fs::metadata(&fd_path),
        )?;
        if !current.is_file()
            || current.dev() != metadata.dev()
            || current.ino() != metadata.ino()
            || still_open.dev() != metadata.dev()
            || still_open.ino() != metadata.ino()
            || profiler_io(
                "recheck FD target",
                &fd_path,
                profiler.pid,
                Some(fd),
                fs::read_link(&fd_path),
            )? != output
            || launch_identity(profiler.pid)?.0 != *profiler
        {
            return Err("profiler RAW/FD/process drift".into());
        }
        return Ok(
            json!({"path":output,"profiler":profiler,"fd":fd,"device":metadata.dev(),"inode":metadata.ino(),"uid":metadata.uid(),"flags_octal":format!("{flags:o}")}),
        );
    }
    if let Some(error) = inaccessible_fd {
        return Err(error);
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
        format!("{}B", perf.data_max_bytes),
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
    } else if e.phase == "arena"
        || (e.phase == "compare" && e.argv.get(1).is_some_and(|a| a == "decisions"))
    {
        Some(configured_arena_plan(&intent, bound, e)?)
    } else if intent.get("selection_index").is_some() {
        Some(configured_run_plan(&intent, bound, e)?)
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
            (
                &profiler_io(
                    "canonicalize exe",
                    &PathBuf::from(format!("/proc/{immediate}/exe")),
                    immediate,
                    None,
                    fs::canonicalize(format!("/proc/{immediate}/exe")),
                )?,
                &tool,
            ),
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
    fn measurement_perf_max_size_requires_exact_byte_unit() {
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
        let native: Vec<String> = e
            .argv
            .iter()
            .map(|a| {
                a.replace("@EXPERIMENT@", &bound.path.to_string_lossy())
                    .replace("@EXPERIMENT_SHA256@", &bound.sha256)
            })
            .collect();
        for cap in [4096_u64, 12582912] {
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
                "49".into(),
                "--call-graph".into(),
                "dwarf,8192".into(),
                "-m".into(),
                "64".into(),
                "--max-size".into(),
                format!("{cap}B"),
                "--no-buildid-cache".into(),
                "-o".into(),
                output.to_string_lossy().to_string(),
                "--".into(),
            ];
            argv.extend(native.clone());
            let mut intent = json!({"owner":dir,"data_root":dir.join("native"),"perf":{"tool":tool,"output":output,"event":"cpu-clock:u","frequency_hz":49,"call_graph":"dwarf,8192","ring_pages":64,"data_max_bytes":cap,"no_buildid_cache":true},"argv":argv});
            assert!(perf_launch_shape(&intent, &e, &bound).unwrap().is_some());
            intent["argv"][12] = json!(cap.to_string());
            assert!(perf_launch_shape(&intent, &e, &bound).is_err());
            intent["argv"][12] = json!(format!("{}B", cap + 1));
            assert!(perf_launch_shape(&intent, &e, &bound).is_err());
            assert!(!output.exists());
        }
    }

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
                "12582912B".into(),
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
    fn configured_corpus_positive_quantity_preserves_model_free_and_maintained_caller() {
        let r =
            json!({"path":"/synthetic/control","sha256":"0".repeat(64),"bytes":1,"mode":"0644"});
        let mut e:Experiment=serde_json::from_value(json!({"schema":"quoridor.research.experiment.v1",
            "phase":"corpus","build_manifest":r,"config":r,"inputs":[r],"models":[],"dynamic_libraries":[],
            "schedule":r,"numerical_qualification":r,"canonical_plan_sha256":"0".repeat(64),
            "rules":"research-standard-2p-threefold-goal-first-v1","distance_units":"wall-distance/80",
            "value_perspective":"side-to-move","planned_slots":8,"batch":null,
            "argv":["/synthetic/native","teacher-pilot","--experiment","@EXPERIMENT@","--experiment-sha256","@EXPERIMENT_SHA256@"]})).unwrap();
        for quantity in [1, 3, 12, 320] {
            e.planned_slots = quantity;
            assert!(phase_shape(&e));
        }
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
mod arena_settings_launch_tests {
    use super::*;
    #[test]
    fn decisions_configuration_preserves_bound_plan_and_experiment_identity() {
        let plan =
            json!({"path":"/synthetic/plan","sha256":"a".repeat(64),"bytes":1,"mode":"0644"});
        let experiment =
            json!({"path":"/synthetic/experiment","sha256":"b".repeat(64),"bytes":1,"mode":"0644"});
        let mut e: Experiment = serde_json::from_value(json!({
            "schema":"quoridor.research.experiment.v1","phase":"compare",
            "build_manifest":plan,"config":plan,"inputs":[],"models":[],
            "dynamic_libraries":[],"schedule":plan,"numerical_qualification":plan,
            "canonical_plan_sha256":"a".repeat(64),"rules":"research-standard-2p-threefold-goal-first-v1",
            "distance_units":"wall-distance/80","value_perspective":"side-to-move",
            "planned_slots":1,"batch":0,"argv":["runner","decisions"]
        })).unwrap();
        let bound = BoundControl {
            path: "/synthetic/experiment".into(),
            sha256: "b".repeat(64),
        };
        let intent = json!({"schema":"quoridor.research.lifecycle-intent.v1","kind":"run",
            "approved_plan":plan,"experiment":experiment});
        assert!(intent.get("admission").is_none());
        assert_eq!(
            configured_arena_plan(&intent, &bound, &e).unwrap().sha256,
            e.canonical_plan_sha256
        );
        e.argv[1] = "other-operation".into();
        assert!(configured_arena_plan(&intent, &bound, &e).is_err());
        e.argv[1] = "decisions".into();
        e.canonical_plan_sha256 = "c".repeat(64);
        assert!(configured_arena_plan(&intent, &bound, &e).is_err());
        e.canonical_plan_sha256 = "a".repeat(64);
        let mut changed = intent.clone();
        changed["experiment"]["path"] = json!("/foreign/experiment");
        assert!(configured_arena_plan(&changed, &bound, &e).is_err());
        changed = intent.clone();
        changed["kind"] = json!("build");
        assert!(configured_arena_plan(&changed, &bound, &e).is_err());
    }
    #[test]
    fn arena_configuration_plan_and_experiment_identity_are_admission_free() {
        let plan =
            json!({"path":"/synthetic/plan","sha256":"a".repeat(64),"bytes":1,"mode":"0644"});
        let experiment =
            json!({"path":"/synthetic/experiment","sha256":"b".repeat(64),"bytes":1,"mode":"0644"});
        let mut e: Experiment = serde_json::from_value(json!({
            "schema":"quoridor.research.experiment.v1","phase":"arena",
            "build_manifest":plan,"config":plan,"inputs":[],"models":[],
            "dynamic_libraries":[],"schedule":plan,"numerical_qualification":plan,
            "canonical_plan_sha256":"a".repeat(64),"rules":"research-standard-2p-threefold-goal-first-v1",
            "distance_units":"wall-distance/80","value_perspective":"side-to-move",
            "planned_slots":6,"batch":1,"argv":[]
        })).unwrap();
        let bound = BoundControl {
            path: "/synthetic/experiment".into(),
            sha256: "b".repeat(64),
        };
        let intent = json!({"schema":"quoridor.research.lifecycle-intent.v1","kind":"run",
            "approved_plan":plan,"experiment":experiment});
        assert!(intent.get("admission").is_none());
        assert_eq!(
            configured_arena_plan(&intent, &bound, &e).unwrap().sha256,
            e.canonical_plan_sha256
        );
        for (key, value) in [("kind", json!("build")), ("schema", json!("invalid"))] {
            let mut changed = intent.clone();
            changed[key] = value;
            assert!(configured_arena_plan(&changed, &bound, &e).is_err());
        }
        for (key, value) in [
            ("path", json!("/other/experiment")),
            ("sha256", json!("c".repeat(64))),
        ] {
            let mut changed = intent.clone();
            changed["experiment"][key] = value;
            assert!(configured_arena_plan(&changed, &bound, &e).is_err());
        }
        e.canonical_plan_sha256 = "d".repeat(64);
        assert!(configured_arena_plan(&intent, &bound, &e).is_err());
        e.canonical_plan_sha256 = "a".repeat(64);
        e.phase = "compare".into();
        assert!(configured_arena_plan(&intent, &bound, &e).is_err());
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
    fn measurement_profiler_io_error_preserves_stage_path_pid_fd_errno() {
        for (operation, path, fd) in [
            ("canonicalize exe", "/proc/19/exe", None),
            ("read_dir", "/proc/19/fd", None),
            ("read fdinfo", "/proc/19/fdinfo/7", Some(7)),
        ] {
            let error = profiler_io::<()>(
                operation,
                Path::new(path),
                19,
                fd,
                Err(std::io::Error::from_raw_os_error(libc::EACCES)),
            )
            .unwrap_err()
            .to_string();
            assert!(error.contains(operation));
            assert!(error.contains(&format!("path={path}")));
            assert!(error.contains("pid=19"));
            assert!(error.contains(&format!("fd={fd:?}")));
            assert!(error.contains(&format!("errno=Some({})", libc::EACCES)));
            assert!(error.contains(&std::io::Error::from_raw_os_error(libc::EACCES).to_string()));
        }
        assert_eq!(
            profiler_io("fixture", Path::new("/unused"), 19, None, Ok(42)).unwrap(),
            42
        );
    }

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

#[cfg(test)]
mod configured_run_launch_tests {
    use super::*;
    #[test]
    fn configured_batch_settings_bind_original_experiment_and_reject_foreign_selection() {
        use sha2::{Digest, Sha256};
        struct Temp(PathBuf);
        impl Drop for Temp {
            fn drop(&mut self) {
                let _ = fs::remove_dir_all(&self.0);
            }
        }
        let dir = std::env::temp_dir().join(format!(
            "configured-runs-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        fs::create_dir(&dir).unwrap();
        let _temp = Temp(dir.clone());
        let write = |name: &str, value: &Value| {
            let path = dir.join(name);
            let bytes = serde_json::to_vec(value).unwrap();
            fs::write(&path, &bytes).unwrap();
            #[cfg(unix)]
            {
                use std::os::unix::fs::PermissionsExt;
                fs::set_permissions(&path, fs::Permissions::from_mode(0o600)).unwrap();
            }
            FileRef {
                path,
                sha256: format!("{:x}", Sha256::digest(&bytes)),
                bytes: bytes.len() as u64,
                mode: "0600".into(),
            }
        };
        let config = write(
            "config.json",
            &json!({"global_schedule":"shared", "batch_start":3, "batch_count":3}),
        );
        let e: Experiment = serde_json::from_value(json!({"schema":"quoridor.research.experiment.v1", "phase":"corpus", "build_manifest":config, "config":config, "inputs":[config], "models":[], "dynamic_libraries":[], "schedule":config, "numerical_qualification":config, "canonical_plan_sha256":config.sha256, "rules":"research-standard-2p-threefold-goal-first-v1", "distance_units":"wall-distance/80", "value_perspective":"side-to-move", "planned_slots":3, "batch":null, "argv":["runner","teacher-pilot","--experiment","@EXPERIMENT@","--experiment-sha256","@EXPERIMENT_SHA256@"]})).unwrap();
        let original = write(
            "original-experiment.json",
            &serde_json::to_value(&e).unwrap(),
        );
        let actual = write("actual-experiment.json", &serde_json::to_value(&e).unwrap());
        let template = json!({"kind":"run", "owner":dir, "cwd":dir, "limits":{"family_B":1024}, "support":config, "artifact":config, "caller_sources":[], "approved_plan":config, "data_root":dir.join("batch"), "data":[], "finalizers":[], "experiment":original});
        let selected = write(
            "settings.json",
            &json!({"kind":"sequence", "runs":[template]}),
        );
        let mut intent = template.clone();
        intent["schema"] = json!("quoridor.research.lifecycle-intent.v1");
        intent["settings"] = serde_json::to_value(selected).unwrap();
        intent["selection_index"] = json!(0);
        intent["experiment"] = serde_json::to_value(&actual).unwrap();
        let bound = BoundControl {
            path: actual.path,
            sha256: actual.sha256,
        };
        assert!(intent.get("admission").is_none());
        assert_eq!(
            configured_run_plan(&intent, &bound, &e).unwrap().sha256,
            config.sha256
        );
        for key in [
            "owner",
            "cwd",
            "limits",
            "support",
            "artifact",
            "caller_sources",
            "approved_plan",
            "data_root",
            "data",
            "finalizers",
        ] {
            let mut changed = intent.clone();
            changed[key] = Value::Null;
            assert!(configured_run_plan(&changed, &bound, &e).is_err());
        }
        intent["selection_index"] = json!(1);
        assert!(configured_run_plan(&intent, &bound, &e).is_err());
        intent["selection_index"] = json!(0);
        let mut different = e.clone();
        different.planned_slots = 4;
        assert!(configured_run_plan(&intent, &bound, &different).is_err());
        fs::write(&original.path, b"{}").unwrap();
        assert!(configured_run_plan(&intent, &bound, &e).is_err());
    }
}

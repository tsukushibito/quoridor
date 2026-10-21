//! Owning process adapter only. Common arena retains clocks, rules and publication.
use quoridor_data::Result;
use serde::{Deserialize, Serialize};
use std::{
    io::{Read, Write},
    os::{fd::AsRawFd, unix::process::CommandExt},
    path::PathBuf,
    process::{Command, Stdio},
    time::{Duration, Instant},
};

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Config {
    pub python: PathBuf,
    pub library: PathBuf,
    pub library_sha256: String,
    pub model_sha256: String,
    pub simulations: u32,
    pub c_puct: f64,
    pub max_head_calls: u64,
}

impl Config {
    pub fn validate(&self) -> Result<()> {
        if !self.python.is_absolute()
            || !self.library.is_absolute()
            || !crate::arena::sha_valid(&self.library_sha256)
            || !crate::arena::sha_valid(&self.model_sha256)
            || self.simulations == 0
            || !self.c_puct.is_finite()
            || self.c_puct <= 0.0
            || self.max_head_calls == 0
        {
            return Err("explicit bounded original Claustrophobia adapter config".into());
        }
        Ok(())
    }

    pub fn identity(&self) -> Result<String> {
        self.validate()?;
        Ok(crate::arena::digest(&serde_json::to_vec(
            &serde_json::json!({
                "kind":"claustrophobia-original-mcts", "upstream":"ae093653e62ad700e201706fa5ed767093d0d68e",
                "library":self.library_sha256,"model":self.model_sha256,
                "input":"upstream-encode20-STM","policy":"upstream-canonical209-mask-softmax",
                "precision":"CPU-FP32-single-row","outer_rules":"common-full-prefix-goal-first-threefold",
                "inner_rules":"original-upstream-board-only-goal-terminal"
            }),
        )?))
    }
}

#[derive(Debug, Deserialize)]
pub struct Reply {
    pub upstream: String,
    pub entry: String,
    pub action: u16,
    pub simulations: u32,
    pub head_calls: u64,
    pub root_value_stm: f32,
    pub inner_history: String,
    pub head: serde_json::Value,
    // Missing facts remain absent in failed/synthetic low-level calls. run()
    // requires this self-observed record; no older helper is admitted.
    pub execution: Option<Execution>,
}

#[derive(Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ExecutionPoint {
    pub pid: u32,
    pub ppid: u32,
    pub tid: u32,
    pub core: usize,
    pub affinity: Vec<usize>,
}

#[derive(Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Execution {
    pub started: ExecutionPoint,
    pub returned: ExecutionPoint,
}

impl Execution {
    fn matches(&self, child_pid: Option<u32>, core: usize) -> bool {
        child_pid.is_some_and(|pid| {
            [&self.started, &self.returned].iter().all(|point| {
                point.pid == pid
                    && point.tid == pid
                    && point.ppid == std::process::id()
                    && point.core == core
                    && point.affinity.len() == 1
                    && point.affinity[0] == core
            })
        })
    }
}

#[derive(Debug)]
pub struct Call {
    pub reply: Option<Reply>,
    pub primary: Option<String>,
    pub secondary: Vec<String>,
    pub child_pid: Option<u32>,
    pub direct_reaped: bool,
    pub child_handle_acquired_at: Option<Instant>,
    pub child_reaped_at: Option<Instant>,
    pub pipes_drained_at: Option<Instant>,
    pub stdout_eof: bool,
    pub stderr_eof: bool,
    pub exit_code: Option<i32>,
    pub stderr: String,
    pub stdout: String,
}

impl Call {
    /// No spawn or confirmed direct reap proves zero; failed wait is UNKNOWN.
    pub(crate) fn inflight_after_drain(&self) -> Option<u8> {
        (self.child_pid.is_none() || self.direct_reaped).then_some(0)
    }
}

fn nonblocking(fd: i32) -> std::io::Result<()> {
    let flags = unsafe { libc::fcntl(fd, libc::F_GETFL) };
    if flags < 0 || unsafe { libc::fcntl(fd, libc::F_SETFL, flags | libc::O_NONBLOCK) } < 0 {
        return Err(std::io::Error::last_os_error());
    }
    Ok(())
}

fn read_available<R: Read + ?Sized>(stream: &mut R, bytes: &mut Vec<u8>) -> std::io::Result<bool> {
    let mut buffer = [0u8; 4096];
    loop {
        match stream.read(&mut buffer) {
            Ok(0) => return Ok(true),
            Ok(n) if bytes.len() + n <= 128 * 1024 => bytes.extend_from_slice(&buffer[..n]),
            Ok(_) => return Err(std::io::Error::other("bounded Claustrophobia output")),
            Err(error) if error.kind() == std::io::ErrorKind::WouldBlock => return Ok(false),
            Err(error) => return Err(error),
        }
    }
}

/// One direct child/group; failure attempts kill/reap and retains any wait error.
fn child_call(
    command: &mut Command,
    request: &[u8],
    deadline: Instant,
    mut cancelled: impl FnMut() -> bool,
) -> Call {
    let mut call = Call {
        reply: None,
        primary: None,
        secondary: Vec::new(),
        child_pid: None,
        direct_reaped: false,
        child_handle_acquired_at: None,
        child_reaped_at: None,
        pipes_drained_at: None,
        stdout_eof: false,
        stderr_eof: false,
        exit_code: None,
        stderr: String::new(),
        stdout: String::new(),
    };
    if request.len() > 65536 || cancelled() || Instant::now() >= deadline {
        call.primary = Some("Claustrophobia request/cancel/deadline before launch".into());
        return call;
    }
    command
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .process_group(0);
    let parent = std::process::id();
    unsafe {
        command.pre_exec(move || {
            if libc::prctl(libc::PR_SET_PDEATHSIG, libc::SIGKILL) != 0
                || libc::getppid() != parent as i32
            {
                return Err(std::io::Error::other("Claustrophobia parent custody"));
            }
            Ok(())
        });
    }
    let mut child = match command.spawn() {
        Ok(child) => child,
        Err(error) => {
            call.primary = Some(format!("Claustrophobia spawn:{error}"));
            return call;
        }
    };
    call.child_pid = Some(child.id());
    call.child_handle_acquired_at = Some(Instant::now());
    let mut input = child.stdin.take().unwrap();
    let mut output = child.stdout.take().unwrap();
    let mut errors = child.stderr.take().unwrap();
    let mut stdout = Vec::new();
    let mut stderr = Vec::new();
    let mut sent = 0;
    let exchange = (|| -> Result<()> {
        nonblocking(input.as_raw_fd())?;
        nonblocking(output.as_raw_fd())?;
        nonblocking(errors.as_raw_fd())?;
        loop {
            if cancelled() {
                return Err("cancelled".into());
            }
            if Instant::now() >= deadline {
                return Err("deadline".into());
            }
            if sent < request.len() {
                match input.write(&request[sent..]) {
                    Ok(0) => return Err("Claustrophobia stdin closed".into()),
                    Ok(n) => sent += n,
                    Err(e) if e.kind() == std::io::ErrorKind::WouldBlock => (),
                    Err(e) => return Err(e.into()),
                }
            } else {
                // EOF is required before Python parses the bounded whole request.
                break;
            }
            read_available(&mut output, &mut stdout)?;
            read_available(&mut errors, &mut stderr)?;
            std::thread::sleep(Duration::from_millis(1));
        }
        Ok(())
    })();
    drop(input);
    let result = exchange.and_then(|()| -> Result<()> {
        loop {
            if cancelled() {
                return Err("cancelled".into());
            }
            if Instant::now() >= deadline {
                return Err("deadline".into());
            }
            read_available(&mut output, &mut stdout)?;
            read_available(&mut errors, &mut stderr)?;
            if let Some(status) = child.try_wait()? {
                call.exit_code = status.code();
                call.direct_reaped = true;
                call.child_reaped_at = Some(Instant::now());
                if !status.success() {
                    return Err(format!("Claustrophobia child failed:{status}").into());
                }
                break;
            }
            std::thread::sleep(Duration::from_millis(1));
        }
        read_available(&mut output, &mut stdout)?;
        read_available(&mut errors, &mut stderr)?;
        call.reply = Some(serde_json::from_slice(&stdout)?);
        Ok(())
    });
    call.primary = result.err().map(|error| error.to_string());
    if !call.direct_reaped {
        // No native/thread work survives a rejected turn. The single helper
        // does not spawn subprocesses; kill its group before direct wait.
        let killed = unsafe { libc::kill(-(child.id() as i32), libc::SIGKILL) };
        if killed != 0 {
            call.secondary.push(format!(
                "Claustrophobia group kill:{}",
                std::io::Error::last_os_error()
            ));
        }
        match child.wait() {
            Ok(status) => {
                call.direct_reaped = true;
                call.child_reaped_at = Some(Instant::now());
                call.exit_code = status.code();
            }
            Err(error) => call.secondary.push(format!("Claustrophobia wait:{error}")),
        }
    }
    for (stream, bytes, eof) in [
        (
            &mut output as &mut dyn Read,
            &mut stdout,
            &mut call.stdout_eof,
        ),
        (
            &mut errors as &mut dyn Read,
            &mut stderr,
            &mut call.stderr_eof,
        ),
    ] {
        match read_available(stream, bytes) {
            Ok(observed) => {
                *eof = observed;
                if !observed {
                    call.secondary
                        .push("Claustrophobia final pipe has no EOF".into());
                }
            }
            Err(error) => call
                .secondary
                .push(format!("Claustrophobia final drain:{error}")),
        }
    }
    if call.stdout_eof && call.stderr_eof {
        call.pipes_drained_at = Some(Instant::now());
    }
    call.stderr = String::from_utf8_lossy(&stderr).into_owned();
    call.stdout = String::from_utf8_lossy(&stdout).into_owned();
    if call.primary.is_some() || !call.secondary.is_empty() || !call.direct_reaped {
        call.reply = None;
    }
    call
}

pub fn run(
    settings: &Config,
    model: &std::path::Path,
    prefix: &[u16],
    legal: &[u16],
    core: usize,
    deadline: Instant,
    cancelled: impl FnMut() -> bool,
) -> Result<Call> {
    settings.validate()?;
    let request = serde_json::to_vec(&serde_json::json!({
        "prefix":prefix,"legal":legal,"model":model,"library":settings.library,
        "simulations":settings.simulations,"c_puct":settings.c_puct,
        "max_head_calls":settings.max_head_calls,
    }))?;
    let mut command = Command::new(&settings.python);
    unsafe {
        command.pre_exec(move || crate::resources::pin(core).map_err(std::io::Error::other));
    }
    command.args(["-B", "-m", "quoridor_training.claustrophobia"]);
    command
        .env("OMP_NUM_THREADS", "1")
        .env("MKL_NUM_THREADS", "1");
    let mut call = child_call(&mut command, &request, deadline, cancelled);
    if let Some(reply) = &call.reply
        && (reply.upstream != "ae093653e62ad700e201706fa5ed767093d0d68e"
            || reply.entry != "mcts::run_mcts"
            || reply
                .execution
                .as_ref()
                .is_none_or(|facts| !facts.matches(call.child_pid, core))
            || !legal.contains(&reply.action)
            || reply.simulations != settings.simulations
            || reply.head_calls == 0
            || reply.head_calls > settings.max_head_calls
            || reply.head["logical_rows_attempted"].as_u64() != Some(reply.head_calls)
            || reply.head["finite_rows_returned"].as_u64() != Some(reply.head_calls)
            || reply.head["failed_attempted_rows"].as_u64() != Some(0)
            || reply.head["head_seconds"]
                .as_f64()
                .is_none_or(|s| !s.is_finite() || s < 0.0)
            || !reply.root_value_stm.is_finite()
            || reply.root_value_stm.abs() > 1.0)
    {
        call.primary = Some("Claustrophobia reply identity/legality/budget".into());
        call.reply = None;
    }
    Ok(call)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn claustrophobia16_child_reply_is_complete_only_after_direct_reap() {
        let wire = serde_json::json!({
            "upstream":"synthetic-not-a-qualified-native", "entry":"synthetic",
            "action":13,"simulations":8,"head_calls":1,"root_value_stm":0.25,
            "inner_history":"synthetic","head":{}
        })
        .to_string();
        let mut command = Command::new("/bin/sh");
        command.args(["-c", r#"read -r line; printf '%s' "$1""#, "fixture", &wire]);
        let call = child_call(
            &mut command,
            b"{}\n",
            Instant::now() + Duration::from_secs(1),
            || false,
        );
        assert!(call.direct_reaped && call.primary.is_none() && call.secondary.is_empty());
        assert_eq!(call.exit_code, Some(0));
        assert_eq!(call.reply.as_ref().unwrap().action, 13);
        assert_eq!(call.stdout, wire);
    }

    #[test]
    fn claustrophobia16_typed_owner_rejects_unused_settings_and_wrong_arena() {
        let mut config: crate::config::Config =
            serde_json::from_str(include_str!("../tests/fixtures/sigma-clock-config.json"))
                .unwrap();
        let settings = Config {
            python: "/synthetic/python".into(),
            library: "/synthetic/bridge.so".into(),
            library_sha256: "a".repeat(64),
            model_sha256: "b".repeat(64),
            simulations: 8,
            c_puct: 1.5,
            max_head_calls: 9,
        };
        settings.validate().unwrap();
        config.engines[0].claustrophobia = Some(settings);
        assert_eq!(
            config.validate().unwrap_err(),
            "unused Claustrophobia settings"
        );
        config.engines[0].kind = "claustrophobia".into();
        config.engines[0].model = Some("/synthetic/champion.pt".into());
        assert!(
            config
                .validate()
                .unwrap_err()
                .starts_with("Claustrophobia requires whole-wall")
        );
        let mut wire = serde_json::to_value(&config.engines[0]).unwrap();
        wire["claustrophobia"]["simulations"] = true.into();
        assert!(serde_json::from_value::<crate::config::Engine>(wire).is_err());
    }

    #[test]
    fn claustrophobia16_cancel_and_deadline_direct_reap_without_partial_move() {
        let mut command = Command::new("/bin/sh");
        command.args(["-c", "exec sleep 5"]);
        let call = child_call(
            &mut command,
            b"{}",
            Instant::now() + Duration::from_millis(20),
            || false,
        );
        assert!(call.direct_reaped && call.reply.is_none());
        assert_eq!(call.primary.as_deref(), Some("deadline"));
        assert!(call.child_pid.is_some());
        assert_eq!(call.inflight_after_drain(), Some(0));
        // Synthetic returned wait-error facts, not an OS fault execution.
        let mut unreaped = call;
        unreaped.direct_reaped = false;
        unreaped.secondary.push("synthetic wait error".into());
        assert_eq!(unreaped.inflight_after_drain(), None);
        assert_eq!(unreaped.primary.as_deref(), Some("deadline"));
        assert!(unreaped.reply.is_none());
        assert_eq!(unreaped.secondary.last().unwrap(), "synthetic wait error");
        let mut command = Command::new("/bin/sh");
        let call = child_call(
            &mut command,
            b"{}",
            Instant::now() + Duration::from_secs(1),
            || true,
        );
        assert!(call.child_pid.is_none() && call.reply.is_none());
        assert!(!call.direct_reaped);
        assert_eq!(call.inflight_after_drain(), Some(0));
    }

    #[test]
    fn claustrophobia16_child_owned_lifecycle_events() {
        // Actual tiny child/pipe/wait only; payload is explicitly synthetic, NN0.
        let mut command = Command::new("/bin/sh");
        command.args([
            "-c",
            r#"read -r request; printf '%s' '{"upstream":"synthetic","entry":"synthetic","action":13,"simulations":1,"head_calls":1,"root_value_stm":0.0,"inner_history":"synthetic","head":{}}'"#,
        ]);
        let started = Instant::now();
        let call = child_call(
            &mut command,
            b"{}\n",
            started + Duration::from_secs(2),
            || false,
        );
        let returned = Instant::now();
        assert!(
            call.primary.is_none() && call.secondary.is_empty(),
            "{call:?}"
        );
        assert!(call.reply.is_some() && call.direct_reaped);
        assert_eq!(call.exit_code, Some(0));
        assert!(call.stdout_eof && call.stderr_eof);
        let acquired = call.child_handle_acquired_at.unwrap();
        let reaped = call.child_reaped_at.unwrap();
        let drained = call.pipes_drained_at.unwrap();
        assert!(started <= acquired && acquired <= reaped && reaped <= drained);
        assert!(drained <= returned);
        assert_eq!(call.inflight_after_drain(), Some(0));
    }

    #[test]
    fn claustrophobia16_execution_points_bind_real_handle_metadata() {
        // Synthetic identity ports; this does not certify any historical process.
        let point = || ExecutionPoint {
            pid: 9001,
            ppid: std::process::id(),
            tid: 9001,
            core: 16,
            affinity: vec![16],
        };
        let facts = || Execution {
            started: point(),
            returned: point(),
        };
        assert!(facts().matches(Some(9001), 16));
        assert!(!facts().matches(None, 16));
        assert!(!facts().matches(Some(9002), 16));
        assert!(!facts().matches(Some(9001), 17));
        for case in 0..6 {
            let mut bad = facts();
            match case {
                0 => bad.started.pid += 1,
                1 => bad.returned.ppid += 1,
                2 => bad.started.tid += 1,
                3 => bad.returned.core = 17,
                4 => bad.started.affinity = vec![16, 17],
                5 => bad.returned.affinity.clear(),
                _ => unreachable!(),
            }
            assert!(!bad.matches(Some(9001), 16));
        }
    }
}

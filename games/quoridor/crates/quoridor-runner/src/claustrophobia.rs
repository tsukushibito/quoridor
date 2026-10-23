//! Owning process adapter only. Common arena retains clocks, rules and publication.
mod session;
use quoridor_data::Result;
use serde::{Deserialize, Serialize};
pub use session::Session;
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
    pub session_sequence: Option<u64>,
    pub session_reply_received: bool,
    pub session_ready: Option<serde_json::Value>,
    /// Parent observation of exchange/validation outcome, before terminal cleanup.
    pub request_finished_at: Option<Instant>,
}

impl Call {
    fn empty() -> Self {
        Self {
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
            session_sequence: None,
            session_reply_received: false,
            session_ready: None,
            request_finished_at: None,
        }
    }
    /// No spawn or confirmed direct reap proves zero; failed wait is UNKNOWN.
    pub(crate) fn inflight_after_drain(&self) -> Option<u8> {
        (self.child_pid.is_none() || self.direct_reaped || self.session_reply_received).then_some(0)
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

fn check_reply(call: &mut Call, settings: &Config, legal: &[u16], core: usize) {
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
}

#[cfg(test)]
mod tests {
    use super::*;

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

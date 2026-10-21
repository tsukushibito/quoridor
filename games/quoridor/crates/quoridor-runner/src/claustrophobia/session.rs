//! One bounded child per engine, retained by the existing evaluation owner.
use super::*;
use std::process::{Child, ChildStderr, ChildStdin, ChildStdout, ExitStatus};

pub struct Session {
    child: Child,
    input: Option<ChildStdin>,
    output: ChildStdout,
    errors: ChildStderr,
    stdout: Vec<u8>,
    stderr: Vec<u8>,
    settings: Config,
    model: PathBuf,
    core: usize,
    sequence: u64,
    ready: serde_json::Value,
    closed: Option<serde_json::Value>,
    reaped: Option<ExitStatus>,
    group_settled: bool,
    group_kill_sent: bool,
    close_errors: Vec<String>,
}

impl Session {
    #[allow(clippy::too_many_arguments)]
    pub fn start(
        settings: &Config,
        model: &std::path::Path,
        core: usize,
        total_head_limit: u64,
        deadline: Instant,
        mut cancelled: impl FnMut() -> bool,
    ) -> Result<Self> {
        settings.validate()?;
        if total_head_limit == 0 || cancelled() || Instant::now() >= deadline {
            return Err("Claustrophobia session refused before spawn".into());
        }
        let mut command = Command::new(&settings.python);
        command.args(["-B", "-m", "quoridor_training.claustrophobia", "--session"]);
        command
            .env("OMP_NUM_THREADS", "1")
            .env("MKL_NUM_THREADS", "1")
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .process_group(0);
        let parent = std::process::id();
        unsafe {
            command.pre_exec(move || {
                crate::resources::pin(core).map_err(std::io::Error::other)?;
                if libc::prctl(libc::PR_SET_PDEATHSIG, libc::SIGKILL) != 0
                    || libc::getppid() != parent as i32
                {
                    return Err(std::io::Error::other("Claustrophobia parent custody"));
                }
                Ok(())
            });
        }
        let mut child = command.spawn()?;
        let input = child.stdin.take().unwrap();
        let output = child.stdout.take().unwrap();
        let errors = child.stderr.take().unwrap();
        let mut owned = Self {
            child,
            input: Some(input),
            output,
            errors,
            stdout: Vec::new(),
            stderr: Vec::new(),
            settings: settings.clone(),
            model: model.into(),
            core,
            sequence: 0,
            ready: serde_json::Value::Null,
            closed: None,
            reaped: None,
            group_settled: false,
            group_kill_sent: false,
            close_errors: Vec::new(),
        };
        let initialized = (|| -> Result<()> {
            nonblocking(owned.input.as_ref().unwrap().as_raw_fd())?;
            nonblocking(owned.output.as_raw_fd())?;
            nonblocking(owned.errors.as_raw_fd())?;
            let mut wire = serde_json::to_vec(&serde_json::json!({
                "library": settings.library, "model": model, "max_head_calls": total_head_limit,
            }))?;
            wire.push(b'\n');
            let raw = owned.exchange(&wire, deadline, &mut cancelled)?;
            let ready: serde_json::Value = serde_json::from_slice(&raw)?;
            let point: ExecutionPoint = serde_json::from_value(ready["execution"].clone())?;
            if ready["session"] != "ready"
                || ready["upstream"] != "ae093653e62ad700e201706fa5ed767093d0d68e"
                || point.pid != owned.child.id()
                || point.tid != owned.child.id()
                || point.ppid != std::process::id()
                || point.core != core
                || point.affinity != [core]
                || ready["head"]["logical_rows_attempted"] != 0
                || ready["head"]["constructor_model_calls"] != 0
                || ready["setup_seconds"]
                    .as_f64()
                    .is_none_or(|s| !s.is_finite() || s < 0.0)
            {
                return Err("Claustrophobia session ready identity/counter facts".into());
            }
            owned.ready = ready;
            Ok(())
        })();
        if let Err(error) = initialized {
            let cleanup = owned.close();
            return Err(format!("Claustrophobia initialization:{error}; cleanup={cleanup}").into());
        }
        Ok(owned)
    }

    /// One outstanding frame only. Parent clock includes input/search/reply.
    fn exchange(
        &mut self,
        wire: &[u8],
        deadline: Instant,
        cancelled: &mut impl FnMut() -> bool,
    ) -> Result<Vec<u8>> {
        if wire.len() > 65536 || self.closed.is_some() {
            return Err("Claustrophobia bounded closed session".into());
        }
        let mut sent = 0;
        loop {
            if cancelled() {
                return Err("cancelled".into());
            }
            if Instant::now() >= deadline {
                return Err("deadline".into());
            }
            if sent < wire.len() {
                match self
                    .input
                    .as_mut()
                    .ok_or("session stdin closed")?
                    .write(&wire[sent..])
                {
                    Ok(0) => return Err("session stdin closed".into()),
                    Ok(n) => sent += n,
                    Err(e) if e.kind() == std::io::ErrorKind::WouldBlock => (),
                    Err(e) => return Err(e.into()),
                }
            }
            let eof = read_available(&mut self.output, &mut self.stdout)?;
            read_available(&mut self.errors, &mut self.stderr)?;
            if self.leader_exited()? {
                return Err("Claustrophobia session exited before a complete frame".into());
            }
            if eof {
                return Err("Claustrophobia session unexpected EOF".into());
            }
            if sent == wire.len()
                && let Some(end) = self.stdout.iter().position(|b| *b == b'\n')
            {
                if end + 1 != self.stdout.len() {
                    return Err("Claustrophobia unsolicited session stdout".into());
                }
                let mut raw = std::mem::take(&mut self.stdout);
                raw.pop();
                return Ok(raw);
            }
            std::thread::sleep(Duration::from_millis(1));
        }
    }

    pub fn turn(
        &mut self,
        prefix: &[u16],
        legal: &[u16],
        deadline: Instant,
        mut cancelled: impl FnMut() -> bool,
    ) -> Call {
        let mut call = Call::empty();
        call.child_pid = Some(self.child.id());
        call.session_ready = Some(self.ready.clone());
        let before_stderr = self.stderr.len();
        self.sequence = match self.sequence.checked_add(1) {
            Some(n) => n,
            None => {
                call.primary = Some("session sequence overflow".into());
                return call;
            }
        };
        call.session_sequence = Some(self.sequence);
        let result = (|| -> Result<()> {
            let mut wire = serde_json::to_vec(&serde_json::json!({
                "sequence": self.sequence,
                "request": {"prefix": prefix, "legal": legal, "model": self.model,
                    "library": self.settings.library, "simulations": self.settings.simulations,
                    "c_puct": self.settings.c_puct, "max_head_calls": self.settings.max_head_calls},
            }))?;
            wire.push(b'\n');
            let raw = self.exchange(&wire, deadline, &mut cancelled)?;
            call.stdout = String::from_utf8_lossy(&raw).into_owned();
            #[derive(Deserialize)]
            #[serde(deny_unknown_fields)]
            struct Frame {
                sequence: u64,
                result: Reply,
            }
            let frame: Frame = serde_json::from_slice(&raw)?;
            if frame.sequence != self.sequence {
                return Err("Claustrophobia session sequence".into());
            }
            call.reply = Some(frame.result);
            check_reply(&mut call, &self.settings, legal, self.core);
            if call.reply.is_none() {
                return Err("Claustrophobia session reply refused".into());
            }
            call.session_reply_received = true;
            Ok(())
        })();
        if let Err(error) = result {
            if call.stdout.is_empty() {
                call.stdout = String::from_utf8_lossy(&self.stdout).into_owned();
            }
            call.primary.get_or_insert_with(|| error.to_string());
            call.reply = None;
            let closed = self.close();
            call.direct_reaped = closed["direct_child_reaped"] == true;
            call.exit_code = closed["exit_code"].as_i64().map(|v| v as i32);
            call.stdout_eof = closed["stdout_eof"] == true;
            call.stderr_eof = closed["stderr_eof"] == true;
            call.secondary.push(format!("session cleanup:{closed}"));
        }
        call.stderr = String::from_utf8_lossy(&self.stderr[before_stderr..]).into_owned();
        call
    }

    /// WNOWAIT leaves our child waitable: even an exited leader retains its PID
    /// and process-group identity until the final direct wait below.
    fn leader_exited(&self) -> std::io::Result<bool> {
        if self.reaped.is_some() {
            return Ok(true);
        }
        let mut info: libc::siginfo_t = unsafe { std::mem::zeroed() };
        let result = unsafe {
            libc::waitid(
                libc::P_PID,
                self.child.id() as libc::id_t,
                &mut info,
                libc::WEXITED | libc::WNOHANG | libc::WNOWAIT,
            )
        };
        if result != 0 {
            return Err(std::io::Error::last_os_error());
        }
        let pid = unsafe { info.si_pid() };
        if pid != 0 && pid != self.child.id() as i32 {
            return Err(std::io::Error::other(
                "unexpected direct-child wait identity",
            ));
        }
        Ok(pid != 0)
    }

    fn signal_owned_group(&mut self) -> std::io::Result<()> {
        if self.reaped.is_some() {
            return Err(std::io::Error::other(
                "refuse group signal after leader reap",
            ));
        }
        // ECHILD/other ownership uncertainty refuses the numeric group signal.
        self.leader_exited()?;
        if unsafe { libc::kill(-(self.child.id() as i32), libc::SIGKILL) } != 0 {
            return Err(std::io::Error::last_os_error());
        }
        self.group_kill_sent = true;
        Ok(())
    }

    /// Same bounded /proc group observation used by the normal process owner.
    /// Include zombies: a non-child's reap is not silently attributed to us.
    /// This is used only while the unreaped direct child anchors the group.
    fn remaining_group(&self) -> std::io::Result<Vec<u32>> {
        if self.reaped.is_some() {
            return Err(std::io::Error::other("group custody already released"));
        }
        let mut members = Vec::new();
        for entry in std::fs::read_dir("/proc")? {
            let entry = entry?;
            let Ok(pid) = entry.file_name().to_string_lossy().parse::<u32>() else {
                continue;
            };
            if pid == self.child.id() {
                continue;
            }
            let stat = match std::fs::read_to_string(entry.path().join("stat")) {
                Ok(stat) => stat,
                Err(error) if error.kind() == std::io::ErrorKind::NotFound => continue,
                Err(error) => return Err(error),
            };
            let tail = stat
                .rsplit_once(')')
                .ok_or_else(|| std::io::Error::other("process stat group unavailable"))?
                .1;
            let group = tail
                .split_whitespace()
                .nth(2)
                .and_then(|group| group.parse::<u32>().ok())
                .ok_or_else(|| std::io::Error::other("process stat group unavailable"))?;
            if group == self.child.id() {
                members.push(pid);
            }
        }
        members.sort_unstable();
        Ok(members)
    }

    fn close_error(&mut self, message: String) {
        if !self.close_errors.contains(&message) {
            self.close_errors.push(message);
        }
    }

    fn drain_close(&mut self, output_ready: bool, errors_ready: bool) -> (bool, bool) {
        let out = if output_ready {
            match read_available(&mut self.output, &mut self.stdout) {
                Ok(eof) => eof,
                Err(error) => {
                    self.close_error(format!("stdout drain:{error}"));
                    false
                }
            }
        } else {
            false
        };
        let err = if errors_ready {
            match read_available(&mut self.errors, &mut self.stderr) {
                Ok(eof) => eof,
                Err(error) => {
                    self.close_error(format!("stderr drain:{error}"));
                    false
                }
            }
        } else {
            false
        };
        (out, err)
    }

    /// Close stays within the existing five-second cleanup envelope. Reserve
    /// its last second for kill/drain; move-clock values are unchanged.
    pub fn close(&mut self) -> serde_json::Value {
        if let Some(record) = &self.closed {
            return record.clone();
        }
        let started = Instant::now();
        let until = started + Duration::from_secs(5);
        let kill_at = until - Duration::from_secs(1);
        drop(self.input.take());
        let output_ready = nonblocking(self.output.as_raw_fd()).is_ok();
        let errors_ready = nonblocking(self.errors.as_raw_fd()).is_ok();
        if !output_ready || !errors_ready {
            self.close_error("session cleanup pipe nonblocking setup failed".into());
        }
        let (mut out_eof, mut err_eof) = (false, false);
        let mut remaining = self.group_settled.then(Vec::<u32>::new);
        loop {
            let (out, err) = self.drain_close(output_ready, errors_ready);
            out_eof |= out;
            err_eof |= err;
            if self.reaped.is_none() {
                match self.leader_exited() {
                    Ok(exited) => {
                        // A last drain after observing exit avoids treating the
                        // ordinary read/exit race as an inherited-pipe fault.
                        if exited {
                            let (out, err) = self.drain_close(output_ready, errors_ready);
                            out_eof |= out;
                            err_eof |= err;
                        }
                        remaining = match self.remaining_group() {
                            Ok(members) => Some(members),
                            Err(error) => {
                                self.close_error(format!("group observation:{error}"));
                                None
                            }
                        };
                        if exited
                            && (!out_eof
                                || !err_eof
                                || remaining
                                    .as_ref()
                                    .is_some_and(|members| !members.is_empty()))
                        {
                            self.close_error(
                                "session leader exited with undrained pipes or remaining group members"
                                    .into(),
                            );
                        }
                        if Instant::now() >= kill_at && !exited {
                            self.close_error("session shutdown grace expired".into());
                        }
                        if !self.group_kill_sent
                            && (self.ready.is_null() || !self.close_errors.is_empty())
                            && let Err(error) = self.signal_owned_group()
                        {
                            self.close_error(format!("owned group kill:{error}"));
                        }
                        if exited && remaining.as_ref().is_some_and(Vec::is_empty) {
                            // No group member remains while the leader is still
                            // unreaped, so no later group action is necessary.
                            self.group_settled = true;
                            match self.child.wait() {
                                Ok(status) => self.reaped = Some(status),
                                Err(error) => self.close_error(format!("direct wait:{error}")),
                            }
                        }
                    }
                    Err(error) => {
                        remaining = None;
                        self.close_error(format!("direct-child custody:{error}"));
                    }
                }
            }
            if self.reaped.is_some() && self.group_settled && out_eof && err_eof {
                break;
            }
            if Instant::now() >= until {
                self.close_error("bounded session cleanup incomplete".into());
                break;
            }
            std::thread::sleep(Duration::from_millis(1));
        }
        if !self.stdout.is_empty() {
            self.close_error("unsolicited stdout at session close".into());
        }
        let settled = self.reaped.is_some() && self.group_settled && out_eof && err_eof;
        let record = serde_json::json!({
            "child_pid": self.child.id(), "direct_child_reaped": self.reaped.is_some(),
            "exit_code": self.reaped.as_ref().and_then(|status| status.code()),
            "stdout_eof": out_eof, "stderr_eof": err_eof,
            "errors": self.close_errors, "seconds": started.elapsed().as_secs_f64(),
            "ready": self.ready, "turns_requested": self.sequence,
            "unconsumed_stdout": String::from_utf8_lossy(&self.stdout),
            "stderr": String::from_utf8_lossy(&self.stderr),
            "group_kill_sent": self.group_kill_sent,
            "remaining_group_pids": remaining,
            "group_settled_before_direct_wait": self.group_settled,
            "cleanup_settled": settled,
            "success": settled && self.reaped.as_ref().is_some_and(|status| status.success())
                && self.close_errors.is_empty(),
        });
        // An incomplete observation does not release ownership. Drop retries
        // bounded cleanup, without any group signal once direct wait succeeded.
        if settled {
            self.closed = Some(record.clone());
        }
        record
    }
}

impl Drop for Session {
    fn drop(&mut self) {
        self.close();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn claustrophobia435_two_frames_keep_one_child_and_close_on_eof() {
        // Actual stdlib transport only; no Python, model, native ABI or Search.
        let mut child = Command::new("/bin/cat")
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .process_group(0)
            .spawn()
            .unwrap();
        let pid = child.id();
        let input = child.stdin.take().unwrap();
        let output = child.stdout.take().unwrap();
        let errors = child.stderr.take().unwrap();
        nonblocking(input.as_raw_fd()).unwrap();
        nonblocking(output.as_raw_fd()).unwrap();
        nonblocking(errors.as_raw_fd()).unwrap();
        let mut session = Session {
            child,
            input: Some(input),
            output,
            errors,
            stdout: vec![],
            stderr: vec![],
            settings: Config {
                python: "/synthetic/python".into(),
                library: "/synthetic/library".into(),
                library_sha256: "a".repeat(64),
                model_sha256: "b".repeat(64),
                simulations: 64,
                c_puct: 1.5,
                max_head_calls: 65,
            },
            model: "/synthetic/model".into(),
            core: 0,
            sequence: 0,
            ready: serde_json::json!({"synthetic_transport":true}),
            closed: None,
            reaped: None,
            group_settled: false,
            group_kill_sent: false,
            close_errors: Vec::new(),
        };
        for wire in [
            b"{\"sequence\":1}\n".as_slice(),
            b"{\"sequence\":2}\n".as_slice(),
        ] {
            let got = session
                .exchange(wire, Instant::now() + Duration::from_secs(1), &mut || false)
                .unwrap();
            assert_eq!(got, wire[..wire.len() - 1]);
            assert_eq!(session.child.id(), pid);
            assert!(!session.leader_exited().unwrap());
        }
        let closed = session.close();
        assert_eq!(closed["success"], true);
        assert_eq!(closed["direct_child_reaped"], true);
        assert_eq!(closed["stdout_eof"], true);
        assert_eq!(closed["stderr_eof"], true);
        assert_eq!(session.close(), closed);
    }
    #[test]
    fn claustrophobia435_exited_leader_pipe_holder_is_settled_without_stale_group_signal() {
        const ISOLATED: &str = "QUORIDOR435_ISOLATED_HOLDER_FAULT";
        if std::env::var_os(ISOLATED).is_none() {
            // Isolate the test-only subreaper setting from other harness tests.
            let output = Command::new(std::env::current_exe().unwrap())
                .args([
                    "--exact",
                    "claustrophobia::session::tests::claustrophobia435_exited_leader_pipe_holder_is_settled_without_stale_group_signal",
                    "--nocapture",
                    "--test-threads=1",
                ])
                .env(ISOLATED, "1")
                .output()
                .unwrap();
            eprint!("{}", String::from_utf8_lossy(&output.stderr));
            assert!(
                output.status.success(),
                "{}",
                String::from_utf8_lossy(&output.stdout)
            );
            return;
        }
        // Only this isolated software fixture adopts/reaps the actual holder.
        // Production ownership has not acquired a new subreaper or manager.
        assert_eq!(unsafe { libc::prctl(libc::PR_SET_CHILD_SUBREAPER, 1) }, 0);
        let mut child = Command::new("/bin/sh")
            .args(["-c", "sleep 30 & printf '%s\\n' \"$!\"; exit 0"])
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .process_group(0)
            .spawn()
            .unwrap();
        let input = child.stdin.take().unwrap();
        let output = child.stdout.take().unwrap();
        let errors = child.stderr.take().unwrap();
        nonblocking(input.as_raw_fd()).unwrap();
        nonblocking(output.as_raw_fd()).unwrap();
        nonblocking(errors.as_raw_fd()).unwrap();
        let mut session = Session {
            child,
            input: Some(input),
            output,
            errors,
            stdout: vec![],
            stderr: vec![],
            settings: Config {
                python: "/synthetic/python".into(),
                library: "/synthetic/library".into(),
                library_sha256: "a".repeat(64),
                model_sha256: "b".repeat(64),
                simulations: 64,
                c_puct: 1.5,
                max_head_calls: 65,
            },
            model: "/synthetic/model".into(),
            core: 0,
            sequence: 0,
            ready: serde_json::json!({"synthetic_transport":true}),
            closed: None,
            reaped: None,
            group_settled: false,
            group_kill_sent: false,
            close_errors: Vec::new(),
        };
        let until = Instant::now() + Duration::from_secs(2);
        while !session.stdout.contains(&b'\n') {
            read_available(&mut session.output, &mut session.stdout).unwrap();
            assert!(Instant::now() < until, "bounded fixture holder identity");
            std::thread::sleep(Duration::from_millis(1));
        }
        let holder_pid: i32 = std::str::from_utf8(&std::mem::take(&mut session.stdout))
            .unwrap()
            .trim()
            .parse()
            .unwrap();
        use std::os::fd::{FromRawFd, OwnedFd};
        struct Holder {
            fd: OwnedFd,
            pid: i32,
            reaped: bool,
        }
        impl Drop for Holder {
            fn drop(&mut self) {
                if !self.reaped {
                    // A pidfd, never a possibly reused numeric PID/group.
                    unsafe {
                        libc::syscall(
                            libc::SYS_pidfd_send_signal,
                            self.fd.as_raw_fd(),
                            libc::SIGKILL,
                            std::ptr::null::<libc::siginfo_t>(),
                            0,
                        );
                        let mut status = 0;
                        libc::waitpid(self.pid, &mut status, 0);
                    }
                }
            }
        }
        let raw_fd = unsafe { libc::syscall(libc::SYS_pidfd_open, holder_pid, 0) } as i32;
        assert!(raw_fd >= 0);
        let mut holder = Holder {
            fd: unsafe { OwnedFd::from_raw_fd(raw_fd) },
            pid: holder_pid,
            reaped: false,
        };
        while !session.leader_exited().unwrap() {
            assert!(Instant::now() < until, "bounded fixture leader exit");
            std::thread::sleep(Duration::from_millis(1));
        }
        assert_eq!(session.remaining_group().unwrap(), [holder_pid as u32]);
        let reap_holder = std::thread::spawn(move || {
            let mut status = 0;
            let pid = unsafe { libc::waitpid(holder_pid, &mut status, 0) };
            (pid, status)
        });
        let closed = session.close();
        let mut poll = libc::pollfd {
            fd: holder.fd.as_raw_fd(),
            events: libc::POLLIN,
            revents: 0,
        };
        let terminal_before_fixture_cleanup = unsafe { libc::poll(&mut poll, 1, 0) } == 1;
        if !terminal_before_fixture_cleanup {
            // Keep a regressing test from leaking its real holder; this cannot
            // satisfy the assertion about what production close actually did.
            unsafe {
                libc::syscall(
                    libc::SYS_pidfd_send_signal,
                    holder.fd.as_raw_fd(),
                    libc::SIGKILL,
                    std::ptr::null::<libc::siginfo_t>(),
                    0,
                );
            }
        }
        let (reaped_pid, status) = reap_holder.join().unwrap();
        holder.reaped = reaped_pid == holder_pid;
        assert!(terminal_before_fixture_cleanup);
        assert_eq!(reaped_pid, holder_pid);
        assert!(libc::WIFSIGNALED(status));
        assert_eq!(libc::WTERMSIG(status), libc::SIGKILL);
        assert_eq!(closed["direct_child_reaped"], true);
        assert_eq!(closed["exit_code"], 0);
        assert_eq!(closed["stdout_eof"], true);
        assert_eq!(closed["stderr_eof"], true);
        assert_eq!(closed["group_kill_sent"], true);
        assert_eq!(closed["cleanup_settled"], true);
        assert_eq!(closed["remaining_group_pids"], serde_json::json!([]));
        assert_eq!(closed["success"], false);
        assert!(
            closed["errors"]
                .as_array()
                .unwrap()
                .iter()
                .any(|error| { error.as_str().unwrap().starts_with("session leader exited") })
        );
        assert_eq!(session.close(), closed); // Settled failure, not retroactive success.
        assert!(session.signal_owned_group().is_err()); // No signal after leader reap.
        eprintln!(
            "C_HOLDER_FAULT_NN0={}",
            serde_json::json!({
                "leader": session.child.id(), "holder": holder_pid,
                "leader_direct_reaped": true, "holder_direct_reaped_by_isolated_fixture": true,
                "no_model_or_library_loaded": true, "closure": closed,
            })
        );
    }
}

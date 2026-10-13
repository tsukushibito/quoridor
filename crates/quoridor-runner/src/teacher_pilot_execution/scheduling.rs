//! At most one queued result per worker. Writer order cannot select inputs.
use quoridor_data::Result;
use serde::{Deserialize, Serialize};
use std::{
    panic::{AssertUnwindSafe, catch_unwind},
    sync::{
        atomic::{AtomicBool, Ordering},
        mpsc,
    },
    time::Instant,
};

#[derive(Debug, Serialize, Deserialize)]
#[serde(tag = "status", rename_all = "snake_case")]
pub(super) enum Outcome<R> {
    Returned { value: R, whole_ns: u64 },
    Failed { started: bool, reason: String },
}

#[derive(Debug, Default, Serialize, Deserialize)]
pub(super) struct Joined {
    pub workers_spawned: usize,
    pub workers_joined: usize,
    pub committed: usize,
    pub result_queue_slots_per_worker: usize,
}

#[derive(Debug)]
pub(super) struct ScheduleFailure {
    pub primary: Box<dyn std::error::Error + Send + Sync>,
    pub joined: Joined,
    pub cleanup_failures: Vec<String>,
}
impl std::fmt::Display for ScheduleFailure {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        std::fmt::Display::fmt(self.primary.as_ref(), f)
    }
}
impl std::error::Error for ScheduleFailure {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        Some(self.primary.as_ref())
    }
}

pub(super) fn ordered<T: Sync, R: Send>(
    jobs: &[T],
    workers: usize,
    cancel: &AtomicBool,
    run: impl Fn(usize, &T) -> Result<R> + Sync,
    mut consume: impl FnMut(usize, Outcome<R>) -> Result<()>,
) -> Result<Joined> {
    if workers == 0 || workers > jobs.len() {
        return Err("invalid finite game worker count".into());
    }
    std::thread::scope(|scope| -> Result<Joined> {
        let mut receivers = Vec::with_capacity(workers);
        let mut handles = Vec::with_capacity(workers);
        let mut primary = None;
        for worker in 0..workers {
            let (send, receive) = mpsc::sync_channel(1);
            let run = &run;
            match std::thread::Builder::new()
                .name(format!("teacher-game-{worker}"))
                .spawn_scoped(scope, move || {
                    for i in (worker..jobs.len()).step_by(workers) {
                        let outcome = if cancel.load(Ordering::Acquire) {
                            Outcome::Failed {
                                started: false,
                                reason: "cancelled_before_game".into(),
                            }
                        } else {
                            let begin = Instant::now();
                            match catch_unwind(AssertUnwindSafe(|| run(worker, &jobs[i]))) {
                                Ok(Ok(value)) => Outcome::Returned {
                                    value,
                                    whole_ns: begin.elapsed().as_nanos().min(u128::from(u64::MAX))
                                        as u64,
                                },
                                Ok(Err(e)) => {
                                    cancel.store(true, Ordering::Release);
                                    Outcome::Failed {
                                        started: true,
                                        reason: format!("game_error:{e}"),
                                    }
                                }
                                Err(_) => {
                                    cancel.store(true, Ordering::Release);
                                    Outcome::Failed {
                                        started: true,
                                        reason: "game_panic:partial_work_UNKNOWN".into(),
                                    }
                                }
                            }
                        };
                        if send.send((i, outcome)).is_err() {
                            break;
                        }
                    }
                }) {
                Ok(h) => {
                    handles.push(h);
                    receivers.push(receive);
                }
                Err(e) => {
                    primary = Some(e.into());
                    cancel.store(true, Ordering::Release);
                    break;
                }
            }
        }
        let mut joined = Joined {
            workers_spawned: handles.len(),
            result_queue_slots_per_worker: 1,
            ..Joined::default()
        };
        if primary.is_none() {
            for i in 0..jobs.len() {
                let result = match receivers[i % workers].recv() {
                    Ok((actual, v)) if actual == i => consume(i, v),
                    Ok(_) => Err("worker changed authoritative game order".into()),
                    Err(e) => Err(format!("worker result missing; remaining UNKNOWN:{e}").into()),
                };
                if let Err(e) = result {
                    primary = Some(e);
                    cancel.store(true, Ordering::Release);
                    break;
                }
                joined.committed += 1;
            }
        }
        // Release every bounded send before joining, including writer IO failure.
        drop(receivers);
        let mut cleanup_failures = Vec::new();
        for handle in handles {
            if handle.join().is_err() {
                cleanup_failures.push("worker_join_panic; partial_work_UNKNOWN".into());
                cancel.store(true, Ordering::Release);
                if primary.is_none() {
                    primary = Some("worker_join_panic; partial_work_UNKNOWN".into());
                }
            } else {
                joined.workers_joined += 1;
            }
        }
        if let Some(e) = primary {
            Err(Box::new(ScheduleFailure {
                primary: e,
                joined,
                cleanup_failures,
            }))
        } else {
            Ok(joined)
        }
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn depth6_scheduler_order_bound_failure_cancel_and_exact_join() {
        let jobs = [0, 1, 2, 3];
        for n in [1, 2] {
            let mut saved = vec![];
            let j = ordered(
                &jobs,
                n,
                &AtomicBool::new(false),
                |_, v| Ok(*v),
                |i, v| {
                    if let Outcome::Returned { value, .. } = v {
                        saved.push((i, value));
                    } else {
                        panic!("unexpected");
                    }
                    Ok(())
                },
            )
            .unwrap();
            assert_eq!(saved, vec![(0, 0), (1, 1), (2, 2), (3, 3)]);
            assert_eq!(j.workers_joined, n);
            assert_eq!(j.result_queue_slots_per_worker, 1);
        }
        let cancelled = AtomicBool::new(true);
        let mut skipped = 0;
        let j = ordered(
            &jobs,
            2,
            &cancelled,
            |_, _| -> Result<()> { panic!("no cancelled run") },
            |_, v| {
                assert!(matches!(v, Outcome::Failed { started: false, .. }));
                skipped += 1;
                Ok(())
            },
        )
        .unwrap();
        assert_eq!(skipped, 4);
        assert_eq!(j.workers_joined, 2);
        let flag = AtomicBool::new(false);
        let e = ordered(
            &jobs,
            2,
            &flag,
            |_, v| Ok(*v),
            |_, _| Err("primary write refusal".into()),
        )
        .unwrap_err();
        assert_eq!(e.to_string(), "primary write refusal");
        assert!(flag.load(Ordering::Acquire));
        let failure = e.downcast_ref::<ScheduleFailure>().unwrap();
        assert_eq!(failure.joined.workers_joined, 2);
        assert_eq!(failure.joined.committed, 0);
        let mut failed = vec![];
        let j = ordered(
            &jobs,
            1,
            &AtomicBool::new(false),
            |_, v| -> Result<u8> {
                if *v == 0 {
                    panic!("owned worker fixture");
                }
                Ok(*v)
            },
            |i, v| {
                failed.push((i, matches!(v, Outcome::Failed { .. })));
                Ok(())
            },
        )
        .unwrap();
        assert_eq!(j.workers_joined, 1);
        assert_eq!(failed, vec![(0, true), (1, true), (2, true), (3, true)]);
    }
    #[test]
    fn configured_slices_preserve_global_order_no_repeat_and_join_before_error_stop() {
        let global = [0u64, 1, 2, 3, 4, 5, 6];
        let cancel = AtomicBool::new(false);
        let mut published = Vec::new();
        for slice in [&global[..3], &global[3..]] {
            let j = ordered(
                slice,
                1,
                &cancel,
                |_, id| Ok(*id),
                |_, outcome| {
                    if let Outcome::Returned { value, .. } = outcome {
                        published.push(value);
                    } else {
                        return Err("unexpected synthetic outcome".into());
                    }
                    Ok(())
                },
            )
            .unwrap();
            assert_eq!(j.workers_spawned, j.workers_joined);
            assert_eq!(j.committed, slice.len());
        }
        assert_eq!(published, global);
        let mut later_entered = false;
        let mut saved = Vec::new();
        let e = ordered(
            &global[..3],
            1,
            &cancel,
            |_, id| Ok(*id),
            |i, outcome| {
                if i == 1 {
                    return Err("SYNTHETIC first publication error".into());
                }
                if let Outcome::Returned { value, .. } = outcome {
                    saved.push(value);
                }
                Ok(())
            },
        )
        .unwrap_err();
        if !cancel.load(Ordering::Acquire) {
            later_entered = true;
        }
        assert!(!later_entered);
        assert_eq!(saved, vec![0]);
        assert_eq!(e.to_string(), "SYNTHETIC first publication error");
        let failure = e.downcast_ref::<ScheduleFailure>().unwrap();
        assert_eq!(
            failure.joined.workers_spawned,
            failure.joined.workers_joined
        );
        assert_eq!(failure.joined.committed, 1);
        assert!(failure.cleanup_failures.is_empty());
    }
}

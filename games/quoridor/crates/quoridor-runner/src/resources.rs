//! Admission uses the actual affinity, physical siblings and cgroup limits.
use quoridor_data::Result;
use serde::Serialize;
use std::{
    collections::{BTreeMap, BTreeSet},
    fs,
    path::Path,
};
#[derive(Debug, Clone, Serialize)]
pub struct Admission {
    pub worker_cores: Vec<usize>,
    pub inference_core: Option<usize>,
    pub reserved_physical: Vec<usize>,
    pub memory_limit: u64,
    pub memory_available: u64,
    /// Evaluation main manages one game; the two worker cores own the engines.
    pub management_core: Option<usize>,
    #[serde(skip_serializing_if = "Vec::is_empty")]
    pub search_worker_cores: Vec<usize>,
}
fn number(path: &str) -> Option<u64> {
    fs::read_to_string(path).ok()?.trim().parse().ok()
}
fn cpu_list(s: &str) -> Result<Vec<usize>> {
    let mut cores = BTreeSet::new();
    for part in s.trim().split(',') {
        if let Some((a, b)) = part.split_once('-') {
            let a: usize = a.parse()?;
            let b: usize = b.parse()?;
            if b < a || b > 65535 {
                return Err("invalid cpu range".into());
            }
            cores.extend(a..=b)
        } else {
            cores.insert(part.parse()?);
        }
    }
    Ok(cores.into_iter().collect())
}
pub fn available_memory() -> u64 {
    let host = fs::read_to_string("/proc/meminfo")
        .ok()
        .and_then(|s| {
            s.lines()
                .find(|l| l.starts_with("MemAvailable:"))
                .and_then(|l| l.split_whitespace().nth(1))
                .and_then(|s| s.parse::<u64>().ok())
        })
        .unwrap_or(0)
        * 1024;
    let max = number("/sys/fs/cgroup/memory.max");
    let current = number("/sys/fs/cgroup/memory.current").unwrap_or(0);
    max.map(|n| host.min(n.saturating_sub(current)))
        .unwrap_or(host)
}
pub fn admit(
    workers: usize,
    requested: &[usize],
    inference: bool,
    reserve: u64,
    maximum: Option<u64>,
) -> Result<Admission> {
    let status = fs::read_to_string("/proc/self/status")?;
    let list = status
        .lines()
        .find_map(|l| l.strip_prefix("Cpus_allowed_list:"))
        .ok_or("CPU affinity unavailable")?;
    let allowed = cpu_list(list)?;
    let mut physical: BTreeMap<(u64, u64), usize> = BTreeMap::new();
    for cpu in allowed {
        let base = format!("/sys/devices/system/cpu/cpu{cpu}/topology");
        let package = number(&format!("{base}/physical_package_id")).unwrap_or(0);
        let core = number(&format!("{base}/core_id")).unwrap_or(cpu as u64);
        physical.entry((package, core)).or_insert(cpu);
    }
    let mut pool: Vec<_> = physical.values().copied().collect();
    pool.sort();
    let reserve_count = pool.len().saturating_sub(1).min(2);
    let reserved = pool.split_off(pool.len() - reserve_count);
    if let Ok(raw) = fs::read_to_string("/sys/fs/cgroup/cpu.max") {
        let v: Vec<_> = raw.split_whitespace().collect();
        if v.len() == 2
            && let (Ok(quota), Ok(period)) = (v[0].parse::<u64>(), v[1].parse::<u64>())
            && let Some(count) = quota.checked_div(period)
        {
            pool.truncate((count as usize).saturating_sub(2).max(1));
        }
    }
    let owner_core = if inference && pool.len() > 1 {
        pool.pop()
    } else {
        None
    };
    let candidates = if requested.is_empty() {
        pool.clone()
    } else {
        if requested.iter().collect::<BTreeSet<_>>().len() != requested.len()
            || requested.iter().any(|c| !pool.contains(c))
        {
            return Err("requested CPU unavailable/reserved/shared sibling".into());
        }
        requested.to_vec()
    };
    if workers > candidates.len() {
        return Err(format!(
            "{workers} workers exceeds {} available physical cores after host/inference reserve",
            candidates.len()
        )
        .into());
    }
    let available = available_memory();
    let usable = available.saturating_sub(reserve);
    let limit = maximum.map(|m| m.min(usable)).unwrap_or(usable);
    if limit < 64 * 1024 * 1024 {
        return Err("RAM/cgroup reserve leaves insufficient memory".into());
    }
    Ok(Admission {
        worker_cores: candidates.into_iter().take(workers).collect(),
        inference_core: owner_core,
        reserved_physical: reserved,
        memory_limit: limit,
        memory_available: available,
        management_core: None,
        search_worker_cores: Vec::new(),
    })
}
/// Explicit per-job allocation does not redefine host headroom as process affinity.
pub fn admit_explicit(
    workers: usize,
    requested: &[usize],
    inference_core: usize,
    reserve: u64,
    maximum: Option<u64>,
) -> Result<Admission> {
    admit_explicit_policy(workers, requested, inference_core, reserve, maximum)
}
/// One serial game retains two AI owners; identical A/B CPUs explicitly time-share that game.
/// The existing explicit allocator retains actual affinity/cpuset/SMT/quota/host guards.
pub fn admit_evaluation(
    requested: &[usize],
    management: Option<usize>,
    reserve: u64,
    maximum: Option<u64>,
    search_team: &[usize],
) -> Result<Admission> {
    let mut admission = if let Some(main) = management {
        let anchors = evaluation_search_cores(requested)?;
        let search = if search_team.is_empty() {
            anchors
        } else {
            if search_team.iter().collect::<BTreeSet<_>>().len() != search_team.len()
                || anchors.iter().any(|c| !search_team.contains(c))
            {
                return Err(
                    "complete distinct search team must contain actual engine owners".into(),
                );
            }
            search_team
        };
        let mut owned = admit_explicit(search.len(), search, main, reserve, maximum)?;
        // Both owners remain pinned; only one move may run before its matching drain.
        owned.worker_cores = requested.to_vec();
        owned.search_worker_cores = search_team.to_vec();
        owned
    } else {
        if !requested.is_empty() || !search_team.is_empty() {
            return Err("evaluation needs both engine cores and its management core".into());
        }
        // Fixtures select only from their genuine launch affinity. Host
        // reserves remain checked against the actual effective cgroup topology.
        let status = fs::read_to_string("/proc/self/status")?;
        let allowed = cpu_list(
            status
                .lines()
                .find_map(|line| line.strip_prefix("Cpus_allowed_list:"))
                .ok_or("CPU affinity unavailable")?,
        )?;
        let mut physical = BTreeMap::new();
        for cpu in allowed {
            let base = format!("/sys/devices/system/cpu/cpu{cpu}/topology");
            let pair = (
                number(&format!("{base}/physical_package_id"))
                    .ok_or("package topology unavailable")?,
                number(&format!("{base}/core_id")).ok_or("core topology unavailable")?,
            );
            physical.entry(pair).or_insert(cpu);
        }
        let mut selected: Vec<_> = physical.values().copied().collect();
        selected.sort_unstable();
        if selected.len() < 3 {
            return Err("evaluation launch needs three physical cores".into());
        }
        admit_explicit(2, &selected[..2], selected[2], reserve, maximum)?
    };
    admission.management_core = admission.inference_core.take();
    Ok(admission)
}
fn evaluation_search_cores(requested: &[usize]) -> Result<&[usize]> {
    if requested.len() != 2 {
        return Err("evaluation requires exactly two AI owner CPU bindings".into());
    }
    Ok(if requested[0] == requested[1] {
        &requested[..1]
    } else {
        requested
    })
}
fn admit_explicit_policy(
    workers: usize,
    requested: &[usize],
    inference_core: usize,
    reserve: u64,
    maximum: Option<u64>,
) -> Result<Admission> {
    let status = fs::read_to_string("/proc/self/status")?;
    let affinity = cpu_list(
        status
            .lines()
            .find_map(|l| l.strip_prefix("Cpus_allowed_list:"))
            .ok_or("CPU affinity unavailable")?,
    )?;
    let effective = cpu_list(&fs::read_to_string("/sys/fs/cgroup/cpuset.cpus.effective")?)?;
    let online = cpu_list(&fs::read_to_string("/sys/devices/system/cpu/online")?)?;
    let mut topology = BTreeMap::new();
    for cpu in online.into_iter().filter(|c| effective.contains(c)) {
        let base = format!("/sys/devices/system/cpu/cpu{cpu}/topology");
        topology.insert(
            cpu,
            (
                number(&format!("{base}/physical_package_id"))
                    .ok_or("package topology unavailable")?,
                number(&format!("{base}/core_id")).ok_or("core topology unavailable")?,
            ),
        );
    }
    let raw = fs::read_to_string("/sys/fs/cgroup/cpu.max")?;
    let values: Vec<_> = raw.split_whitespace().collect();
    let quota = if values.first() == Some(&"max") {
        None
    } else {
        if values.len() != 2 {
            return Err("invalid cgroup quota".into());
        }
        let period = values[1].parse::<u64>()?;
        if period == 0 {
            return Err("invalid cgroup quota period".into());
        }
        Some(values[0].parse::<u64>()? as f64 / period as f64)
    };
    let reserved = explicit_cpu_selection(
        workers,
        requested,
        inference_core,
        &affinity,
        &topology,
        quota,
    )?;
    let available = available_memory();
    let limit = admitted_memory(available, reserve, maximum)?;
    Ok(Admission {
        worker_cores: requested.to_vec(),
        inference_core: Some(inference_core),
        reserved_physical: reserved,
        memory_limit: limit,
        memory_available: available,
        management_core: None,
        search_worker_cores: Vec::new(),
    })
}
fn admitted_memory(available: u64, reserve: u64, maximum: Option<u64>) -> Result<u64> {
    let usable = available.saturating_sub(reserve);
    let limit = maximum.map(|m| m.min(usable)).unwrap_or(usable);
    if limit < 64 * 1024 * 1024 {
        return Err("RAM/cgroup reserve leaves insufficient memory".into());
    }
    Ok(limit)
}
fn explicit_cpu_selection(
    workers: usize,
    requested: &[usize],
    inference: usize,
    affinity: &[usize],
    topology: &BTreeMap<usize, (u64, u64)>,
    quota: Option<f64>,
) -> Result<Vec<usize>> {
    if workers == 0 || requested.len() != workers {
        return Err("explicit workers require exact cpu_cores".into());
    }
    let mut occupied = BTreeSet::new();
    for cpu in requested.iter().copied().chain(std::iter::once(inference)) {
        if !affinity.contains(&cpu) {
            return Err("explicit CPU outside process affinity".into());
        }
        let pair = topology
            .get(&cpu)
            .ok_or("explicit CPU outside effective cpuset")?;
        if !occupied.insert(*pair) {
            return Err("explicit CPU duplicates physical sibling".into());
        }
    }
    if quota.is_some_and(|q| !q.is_finite() || q < (workers + 3) as f64) {
        return Err("cgroup quota cannot retain two host cores".into());
    }
    let mut free = BTreeMap::new();
    for (cpu, pair) in topology {
        if !occupied.contains(pair) {
            free.entry(*pair).or_insert(*cpu);
        }
    }
    if free.len() < 2 {
        return Err("host topology cannot retain two physical cores".into());
    }
    Ok(free.values().copied().take(2).collect())
}

pub fn pin(core: usize) -> Result<()> {
    unsafe {
        let mut set: libc::cpu_set_t = std::mem::zeroed();
        if core >= libc::CPU_SETSIZE as usize {
            return Err("CPU affinity index exceeds system limit".into());
        }
        libc::CPU_ZERO(&mut set);
        libc::CPU_SET(core, &mut set);
        let code = libc::pthread_setaffinity_np(
            libc::pthread_self(),
            std::mem::size_of::<libc::cpu_set_t>(),
            &set,
        );
        if code != 0 {
            return Err(std::io::Error::from_raw_os_error(code).into());
        }
    }
    Ok(())
}
pub fn directory_bytes(path: &Path) -> Result<u64> {
    let mut total = 0;
    for e in fs::read_dir(path)? {
        let e = e?;
        let m = e.metadata()?;
        if m.is_dir() {
            total += directory_bytes(&e.path())?
        } else {
            total += m.len()
        }
    }
    Ok(total)
}
pub struct AffinityGuard {
    original: libc::cpu_set_t,
}
impl AffinityGuard {
    pub fn capture() -> Result<Self> {
        unsafe {
            let mut set = std::mem::zeroed();
            let code = libc::pthread_getaffinity_np(
                libc::pthread_self(),
                std::mem::size_of::<libc::cpu_set_t>(),
                &mut set,
            );
            if code != 0 {
                return Err(std::io::Error::from_raw_os_error(code).into());
            }
            Ok(Self { original: set })
        }
    }
}
impl Drop for AffinityGuard {
    fn drop(&mut self) {
        unsafe {
            libc::pthread_setaffinity_np(
                libc::pthread_self(),
                std::mem::size_of::<libc::cpu_set_t>(),
                &self.original,
            );
        }
    }
}

pub fn default_workers() -> usize {
    let allowed = fs::read_to_string("/proc/self/status")
        .ok()
        .and_then(|s| {
            s.lines()
                .find_map(|l| l.strip_prefix("Cpus_allowed_list:").map(str::to_owned))
        })
        .and_then(|s| cpu_list(&s).ok())
        .unwrap_or_else(|| vec![0]);
    let mut pairs = BTreeSet::new();
    for cpu in allowed {
        let base = format!("/sys/devices/system/cpu/cpu{cpu}/topology");
        pairs.insert((
            number(&format!("{base}/physical_package_id")).unwrap_or(0),
            number(&format!("{base}/core_id")).unwrap_or(cpu as u64),
        ));
    }
    let mut count = pairs.len().saturating_sub(3).max(1);
    if let Ok(raw) = fs::read_to_string("/sys/fs/cgroup/cpu.max") {
        let v: Vec<_> = raw.split_whitespace().collect();
        if v.len() == 2
            && let (Ok(quota), Ok(period)) = (v[0].parse::<u64>(), v[1].parse::<u64>())
            && let Some(cpus) = quota.checked_div(period)
        {
            count = count.min((cpus as usize).saturating_sub(3).max(1));
        }
    }
    count
}

#[cfg(test)]
mod explicit_tests {
    use super::*;
    fn topology() -> BTreeMap<usize, (u64, u64)> {
        [
            (0, (0, 0)),
            (1, (0, 1)),
            (2, (0, 2)),
            (3, (0, 3)),
            (12, (0, 2)),
        ]
        .into_iter()
        .collect()
    }
    #[test]
    fn narrowed_affinity_retains_host_headroom() {
        assert_eq!(
            explicit_cpu_selection(1, &[2], 3, &[2, 3], &topology(), Some(4.)).unwrap(),
            vec![0, 1]
        );
    }
    #[test]
    fn rejects_unavailable_siblings_and_quota() {
        assert!(explicit_cpu_selection(1, &[2], 0, &[2, 3], &topology(), None).is_err());
        assert!(explicit_cpu_selection(1, &[2], 12, &[2, 12], &topology(), None).is_err());
        assert!(explicit_cpu_selection(2, &[2], 3, &[2, 3], &topology(), None).is_err());
        assert!(explicit_cpu_selection(1, &[2], 3, &[2, 3], &topology(), Some(3.99)).is_err());
        assert!(
            explicit_cpu_selection(
                1,
                &[2],
                3,
                &[2, 3],
                &[(2, (0, 2)), (3, (0, 3))].into_iter().collect(),
                None
            )
            .is_err()
        );
        assert!(
            explicit_cpu_selection(
                1,
                &[2],
                3,
                &[2, 3],
                &[(0, (0, 0)), (1, (0, 1)), (2, (0, 2))]
                    .into_iter()
                    .collect(),
                None
            )
            .is_err()
        );
    }
    #[test]
    fn memory_guard_keeps_reserve() {
        assert_eq!(
            admitted_memory(
                1024 * 1024 * 1024,
                128 * 1024 * 1024,
                Some(256 * 1024 * 1024)
            )
            .unwrap(),
            256 * 1024 * 1024
        );
        assert!(admitted_memory(128 * 1024 * 1024, 128 * 1024 * 1024, None).is_err());
    }
    #[test]
    fn two_ai_374_three_core_allocation_preserves_affinity_smt_quota_and_host_reserve() {
        let t: BTreeMap<_, _> = (0..6).map(|n| (n, (0, n as u64))).collect();
        assert_eq!(
            explicit_cpu_selection(2, &[0, 1], 2, &[0, 1, 2], &t, Some(5.)).unwrap(),
            vec![3, 4]
        );
        assert!(explicit_cpu_selection(2, &[0, 1], 2, &[0, 1], &t, Some(5.)).is_err());
        assert!(explicit_cpu_selection(2, &[0, 1], 2, &[0, 1, 2], &t, Some(4.99)).is_err());
        let mut siblings = t.clone();
        siblings.insert(1, (0, 0));
        assert!(explicit_cpu_selection(2, &[0, 1], 2, &[0, 1, 2], &siblings, Some(5.)).is_err());
        let no_reserve = t.into_iter().take(4).collect();
        assert!(explicit_cpu_selection(2, &[0, 1], 2, &[0, 1, 2], &no_reserve, None).is_err());
    }
}

use std::sync::atomic::{AtomicU64, Ordering};

/// Shared finite work ceiling. Unreturned/error work retains its reservation.
pub(crate) struct NodeBudget {
    remaining: AtomicU64,
}
impl NodeBudget {
    pub(crate) fn remaining(&self) -> u64 {
        self.remaining.load(Ordering::Acquire)
    }
    pub(crate) fn new(nodes: u64) -> Self {
        Self {
            remaining: AtomicU64::new(nodes),
        }
    }
    pub(crate) fn reserve(&self, per_move: u64) -> Result<u64> {
        let mut old = self.remaining.load(Ordering::Acquire);
        loop {
            let take = old.min(per_move);
            if take == 0 {
                return Err("common_total_node_cap; remaining decisions UNKNOWN".into());
            }
            match self.remaining.compare_exchange_weak(
                old,
                old - take,
                Ordering::AcqRel,
                Ordering::Acquire,
            ) {
                Ok(_) => return Ok(take),
                Err(now) => old = now,
            }
        }
    }
    pub(crate) fn settle(&self, reserved: u64, returned: u64) -> Result<()> {
        if returned > reserved {
            return Err("returned nodes exceed reserved common ceiling".into());
        }
        self.remaining
            .fetch_add(reserved - returned, Ordering::AcqRel);
        Ok(())
    }
}
#[cfg(test)]
mod common_node_budget_tests {
    use super::*;
    #[test]
    fn parallel_reservations_returned_work_and_opaque_error_cannot_exceed_total() {
        let b = NodeBudget::new(11);
        let a = b.reserve(7).unwrap();
        let c = b.reserve(7).unwrap();
        assert_eq!((a, c), (7, 4));
        assert!(b.reserve(1).is_err());
        b.settle(a, 5).unwrap();
        assert_eq!(b.reserve(7).unwrap(), 2);
        // The second reservation represents an unreturned Err; no refund.
        assert!(b.reserve(1).is_err());
        assert!(b.settle(c, 5).is_err());
    }
}

#[cfg(test)]
mod alternating_evaluation_core_tests {
    use super::*;

    #[test]
    fn two_owners_share_only_an_identical_same_game_cpu() {
        let topology: BTreeMap<_, _> = [
            (0, (0, 0)),
            (2, (0, 1)),
            (3, (0, 1)),
            (4, (0, 2)),
            (6, (0, 3)),
            (8, (0, 4)),
        ]
        .into_iter()
        .collect();
        let declared = [4, 4];
        let search = evaluation_search_cores(&declared).unwrap();
        assert_eq!(search, &[4]);
        explicit_cpu_selection(search.len(), search, 2, &[2, 4], &topology, None).unwrap();
        // General duplicate/sibling and manager isolation policies are unchanged.
        assert!(explicit_cpu_selection(2, &declared, 2, &[2, 4], &topology, None).is_err());
        let siblings = evaluation_search_cores(&[2, 3]).unwrap();
        assert!(explicit_cpu_selection(2, siblings, 4, &[2, 3, 4], &topology, None).is_err());
        assert!(explicit_cpu_selection(1, search, 4, &[2, 4], &topology, None).is_err());
        assert!(explicit_cpu_selection(1, search, 2, &[2, 4], &topology, Some(3.9)).is_err());
        assert!(evaluation_search_cores(&[4]).is_err());
    }
}

#[cfg(feature = "measurement")]
pub(crate) fn process_cpu_seconds() -> Option<f64> {
    let raw = fs::read_to_string("/proc/self/stat").ok()?;
    let end = raw.rfind(')')?;
    let fields: Vec<_> = raw[end + 2..].split_whitespace().collect();
    let ticks = fields
        .get(11)?
        .parse::<u64>()
        .ok()?
        .checked_add(fields.get(12)?.parse::<u64>().ok()?)?;
    // Existing libc dependency; scalar OS metadata query, no shared memory or race.
    let hz = unsafe { libc::sysconf(libc::_SC_CLK_TCK) };
    (hz > 0).then(|| ticks as f64 / hz as f64)
}

#[cfg(feature = "measurement")]
pub(crate) fn process_peak_rss_bytes() -> Option<u64> {
    let raw = fs::read_to_string("/proc/self/status").ok()?;
    raw.lines()
        .find_map(|line| {
            line.strip_prefix("VmHWM:")?
                .split_whitespace()
                .next()?
                .parse::<u64>()
                .ok()
        })?
        .checked_mul(1024)
}

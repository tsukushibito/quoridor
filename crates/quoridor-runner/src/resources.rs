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
}

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

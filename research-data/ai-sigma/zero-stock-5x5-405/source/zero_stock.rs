//! Finite fixed-wall board-WDL experiment source; no product dependencies.
use std::error::Error;
use std::fs::{File, OpenOptions};
use std::io::{BufReader, BufWriter, Read, Seek, SeekFrom, Write};
use std::path::Path;
use std::time::Instant;

type Result<T> = std::result::Result<T, Box<dyn Error>>;
const MAX_CELLS: usize = 25;
const MAX_STATES: usize = MAX_CELLS * MAX_CELLS * 2;
const MAX_MOVES: usize = 8;
const MAX_EDGES: usize = MAX_STATES * MAX_MOVES;
const GOAL: u16 = u16::MAX;
const DRAW: u8 = 0;
const WIN: u8 = 1;
const LOSS: u8 = 2;
const INACTIVE: u8 = 255;
const MASK_MAGIC: &[u8; 8] = b"Q5MASK01";
const RECORD_MAGIC: &[u8; 8] = b"Q5REC001";
const FIXTURE_MAGIC: &[u8; 8] = b"Q5WDL001";
const RECORD_BYTES: u32 = 48;

fn require(condition: bool, message: &str) -> Result<()> {
    if condition {
        Ok(())
    } else {
        Err(message.into())
    }
}
fn fresh(path: &str) -> Result<File> {
    Ok(OpenOptions::new().write(true).create_new(true).open(path)?)
}
fn nanos(start: Instant) -> Result<u64> {
    Ok(start.elapsed().as_nanos().try_into()?)
}
fn peak_rss() -> String {
    std::fs::read_to_string("/proc/self/status")
        .ok()
        .and_then(|s| {
            s.lines()
                .find(|line| line.starts_with("VmHWM:"))?
                .split_whitespace()
                .nth(1)?
                .parse::<u64>()
                .ok()?
                .checked_mul(1024)
        })
        .map_or_else(|| "null".into(), |n| n.to_string())
}
fn candidates(n: usize) -> usize {
    2 * (n - 1) * (n - 1)
}
fn collisions(n: usize) -> [u32; 32] {
    let a = (n - 1) * (n - 1);
    let mut result = [0; 32];
    for i in 0..a {
        let (r, c) = (i / (n - 1), i % (n - 1));
        result[i] |= 1 << (a + i);
        result[a + i] |= 1 << i;
        if c > 0 {
            result[i] |= 1 << (i - 1);
        }
        if c + 1 < n - 1 {
            result[i] |= 1 << (i + 1);
        }
        if r > 0 {
            result[a + i] |= 1 << (a + i - (n - 1));
        }
        if r + 1 < n - 1 {
            result[a + i] |= 1 << (a + i + (n - 1));
        }
    }
    result
}
fn valid_mask(n: usize, mask: u32) -> bool {
    let count = candidates(n);
    let allowed = if count == 32 {
        u32::MAX
    } else {
        (1u32 << count) - 1
    };
    if mask & !allowed != 0 {
        return false;
    }
    let conflict = collisions(n);
    let mut bits = mask;
    while bits != 0 {
        let i = bits.trailing_zeros() as usize;
        bits &= bits - 1;
        if mask & conflict[i] != 0 {
            return false;
        }
    }
    true
}
// Highest bit first, excluded branch first: strictly ascending numeric masks.
fn independent_sets<F: FnMut(u32) -> Result<()>>(
    bit: i32,
    mask: u32,
    forbidden: u32,
    conflict: &[u32; 32],
    emit: &mut F,
) -> Result<()> {
    if bit < 0 {
        return emit(mask);
    }
    independent_sets(bit - 1, mask, forbidden, conflict, emit)?;
    let flag = 1u32 << bit;
    if forbidden & flag == 0 {
        independent_sets(
            bit - 1,
            mask | flag,
            forbidden | conflict[bit as usize],
            conflict,
            emit,
        )?;
    }
    Ok(())
}

struct Board {
    n: usize,
    mask: u32,
    adj: [u32; MAX_CELLS],
}
impl Board {
    fn new(n: usize, mask: u32) -> Result<Self> {
        require(n == 3 || n == 5, "side must be3(test)or5(full study)")?;
        require(valid_mask(n, mask), "overlap/cross/out-of-domain wall")?;
        let mut b = Self {
            n,
            mask,
            adj: [0; MAX_CELLS],
        };
        for cell in 0..n * n {
            let (r, c) = (cell / n, cell % n);
            if r > 0 {
                b.adj[cell] |= 1 << (cell - n);
            }
            if r + 1 < n {
                b.adj[cell] |= 1 << (cell + n);
            }
            if c > 0 {
                b.adj[cell] |= 1 << (cell - 1);
            }
            if c + 1 < n {
                b.adj[cell] |= 1 << (cell + 1);
            }
        }
        let a = (n - 1) * (n - 1);
        let mut bits = mask;
        while bits != 0 {
            let i = bits.trailing_zeros() as usize;
            bits &= bits - 1;
            let anchor = i % a;
            let (r, c) = (anchor / (n - 1), anchor % (n - 1));
            let x = r * n + c;
            if i < a {
                b.close(x, x + n);
                b.close(x + 1, x + n + 1);
            } else {
                b.close(x, x + 1);
                b.close(x + n, x + n + 1);
            }
        }
        Ok(b)
    }
    fn close(&mut self, a: usize, b: usize) {
        self.adj[a] &= !(1 << b);
        self.adj[b] &= !(1 << a);
    }
    fn goal(&self, player: usize, cell: usize) -> bool {
        cell / self.n == if player == 0 { self.n - 1 } else { 0 }
    }
    fn goal_mask(&self, player: usize) -> u32 {
        let row = (1u32 << self.n) - 1;
        if player == 0 {
            row << (self.n * (self.n - 1))
        } else {
            row
        }
    }
    fn flood(&self, seed: u32) -> u32 {
        let mut seen = seed;
        let mut frontier = seed;
        while frontier != 0 {
            let mut next = 0;
            let mut bits = frontier;
            while bits != 0 {
                let c = bits.trailing_zeros() as usize;
                bits &= bits - 1;
                next |= self.adj[c];
            }
            frontier = next & !seen;
            seen |= frontier;
        }
        seen
    }
    fn reach(&self, player: usize) -> u32 {
        self.flood(self.goal_mask(player))
    }
    fn components(&self) -> u8 {
        let mut unseen = (1u32 << (self.n * self.n)) - 1;
        let mut count = 0;
        while unseen != 0 {
            unseen &= !self.flood(1 << unseen.trailing_zeros());
            count += 1;
        }
        count
    }
    fn moves(&self, own: usize, other: usize) -> u32 {
        let mut moves = 0;
        let mut adjacent = self.adj[own];
        while adjacent != 0 {
            let q = adjacent.trailing_zeros() as usize;
            adjacent &= adjacent - 1;
            if q != other {
                moves |= 1 << q;
                continue;
            }
            let (dr, dc) = (
                (q / self.n) as i32 - (own / self.n) as i32,
                (q % self.n) as i32 - (own % self.n) as i32,
            );
            let (rr, cc) = ((q / self.n) as i32 + dr, (q % self.n) as i32 + dc);
            if rr >= 0 && cc >= 0 && rr < self.n as i32 && cc < self.n as i32 {
                let behind = rr as usize * self.n + cc as usize;
                if self.adj[q] & (1 << behind) != 0 {
                    moves |= 1 << behind;
                    continue;
                }
            }
            let mut sides = self.adj[q];
            while sides != 0 {
                let z = sides.trailing_zeros() as usize;
                sides &= sides - 1;
                let dot = ((z / self.n) as i32 - (q / self.n) as i32) * dr
                    + ((z % self.n) as i32 - (q % self.n) as i32) * dc;
                if dot == 0 {
                    moves |= 1 << z;
                }
            }
        }
        moves
    }
    fn state(&self, a: usize, b: usize, t: usize) -> usize {
        (a * self.n * self.n + b) * 2 + t
    }
    fn decode(&self, id: usize) -> (usize, usize, usize) {
        let cells = self.n * self.n;
        (id / 2 / cells, id / 2 % cells, id % 2)
    }
}

struct Graph {
    raw: usize,
    len: usize,
    edges: u32,
    ids: Vec<u16>,
    active: Vec<bool>,
    degree: Vec<u8>,
    next: Vec<[u16; MAX_MOVES]>,
    action: Vec<[u8; MAX_MOVES]>,
    status: Vec<u8>,
    rank: Vec<u16>,
    choice: Vec<u16>,
    remaining: Vec<u8>,
    max_rank: Vec<u16>,
    pred_count: Vec<u16>,
    offsets: Vec<usize>,
    cursor: Vec<usize>,
    reverse: Vec<u16>,
    queue: Vec<u16>,
}
impl Graph {
    fn new() -> Self {
        Self {
            raw: 0,
            len: 0,
            edges: 0,
            ids: vec![0; MAX_STATES],
            active: vec![false; MAX_STATES],
            degree: vec![0; MAX_STATES],
            next: vec![[0; MAX_MOVES]; MAX_STATES],
            action: vec![[0; MAX_MOVES]; MAX_STATES],
            status: vec![INACTIVE; MAX_STATES],
            rank: vec![0; MAX_STATES],
            choice: vec![GOAL; MAX_STATES],
            remaining: vec![0; MAX_STATES],
            max_rank: vec![0; MAX_STATES],
            pred_count: vec![0; MAX_STATES],
            offsets: vec![0; MAX_STATES + 1],
            cursor: vec![0; MAX_STATES],
            reverse: vec![0; MAX_EDGES],
            queue: vec![0; MAX_STATES],
        }
    }
    fn build(&mut self, b: &Board) -> Result<()> {
        self.raw = 2 * b.n * b.n * b.n * b.n;
        self.len = 0;
        self.edges = 0;
        self.active.fill(false);
        self.degree.fill(0);
        self.status.fill(INACTIVE);
        self.rank.fill(0);
        self.choice.fill(GOAL);
        let reach = [b.reach(0) & !b.goal_mask(0), b.reach(1) & !b.goal_mask(1)];
        for a in 0..b.n * b.n {
            for c in 0..b.n * b.n {
                if a == c || reach[0] & (1 << a) == 0 || reach[1] & (1 << c) == 0 {
                    continue;
                }
                for t in 0..2 {
                    let id = b.state(a, c, t);
                    self.active[id] = true;
                    self.status[id] = DRAW;
                    self.ids[self.len] = id.try_into()?;
                    self.len += 1;
                }
            }
        }
        for k in 0..self.len {
            let u = self.ids[k] as usize;
            let (a, c, t) = b.decode(u);
            let mut moves = b.moves(if t == 0 { a } else { c }, if t == 0 { c } else { a });
            while moves != 0 {
                let dest = moves.trailing_zeros() as usize;
                moves &= moves - 1;
                let j = self.degree[u] as usize;
                require(j < MAX_MOVES, "out-degree capacity")?;
                let v = if b.goal(t, dest) {
                    GOAL
                } else {
                    let v = if t == 0 {
                        b.state(dest, c, 1)
                    } else {
                        b.state(a, dest, 0)
                    };
                    require(
                        self.active[v],
                        "nonterminal successor outside eligible graph",
                    )?;
                    v.try_into()?
                };
                self.action[u][j] = dest.try_into()?;
                self.next[u][j] = v;
                self.degree[u] += 1;
                self.edges += 1;
            }
            require(
                self.degree[u] > 0,
                "valid nonterminal has no legal move; undefined draw semantics refused",
            )?;
        }
        self.propagate()
    }
    fn propagate(&mut self) -> Result<()> {
        self.pred_count.fill(0);
        self.max_rank.fill(0);
        for k in 0..self.len {
            let u = self.ids[k] as usize;
            self.remaining[u] = self.degree[u];
            for j in 0..self.degree[u] as usize {
                let v = self.next[u][j];
                if v != GOAL {
                    self.pred_count[v as usize] = self.pred_count[v as usize]
                        .checked_add(1)
                        .ok_or("predecessor overflow")?;
                }
            }
        }
        let mut sum = 0;
        for v in 0..self.raw {
            self.offsets[v] = sum;
            self.cursor[v] = sum;
            sum += self.pred_count[v] as usize;
        }
        self.offsets[self.raw] = sum;
        require(sum <= MAX_EDGES, "reverse edge capacity")?;
        for k in 0..self.len {
            let u = self.ids[k] as usize;
            for j in 0..self.degree[u] as usize {
                let v = self.next[u][j];
                if v != GOAL {
                    let v = v as usize;
                    self.reverse[self.cursor[v]] = u as u16;
                    self.cursor[v] += 1;
                }
            }
        }
        let (mut head, mut tail) = (0, 0);
        for k in 0..self.len {
            let u = self.ids[k] as usize;
            if self.next[u][..self.degree[u] as usize].contains(&GOAL) {
                self.status[u] = WIN;
                self.rank[u] = 1;
                self.choice[u] = GOAL;
                self.queue[tail] = u as u16;
                tail += 1;
            }
        }
        while head < tail {
            let v = self.queue[head] as usize;
            head += 1;
            for j in self.offsets[v]..self.offsets[v + 1] {
                let u = self.reverse[j] as usize;
                if self.status[u] != DRAW {
                    continue;
                }
                if self.status[v] == LOSS {
                    self.status[u] = WIN;
                    self.rank[u] = self.rank[v].checked_add(1).ok_or("rank overflow")?;
                    self.choice[u] = v as u16;
                } else {
                    require(self.remaining[u] > 0, "remaining-degree underflow")?;
                    self.remaining[u] -= 1;
                    self.max_rank[u] = self.max_rank[u].max(self.rank[v]);
                    if self.remaining[u] != 0 {
                        continue;
                    }
                    self.status[u] = LOSS;
                    self.rank[u] = self.max_rank[u].checked_add(1).ok_or("rank overflow")?;
                }
                require(tail < MAX_STATES, "queue capacity")?;
                self.queue[tail] = u as u16;
                tail += 1;
            }
        }
        Ok(())
    }
    fn verify(&mut self, b: &Board) -> Result<Record> {
        let mut r = Record {
            mask: b.mask,
            wall_count: b.mask.count_ones() as u8,
            components: b.components(),
            active: self.len.try_into()?,
            edges: self.edges,
            ..Record::default()
        };
        let start0 = b.n / 2;
        let start1 = (b.n - 1) * b.n + b.n / 2;
        r.initial_flags = u8::from(b.reach(0) & (1 << start0) != 0)
            | u8::from(b.reach(1) & (1 << start1) != 0) << 1;
        if b.flood(1 << start0) & (1 << start1) != 0 {
            r.initial_flags |= 4;
        }
        for k in 0..self.len {
            let u = self.ids[k] as usize;
            let (a, c, t) = b.decode(u);
            let expected = b.moves(if t == 0 { a } else { c }, if t == 0 { c } else { a });
            let mut seen = 0;
            let (mut winning, mut draw_child) = (false, None);
            for j in 0..self.degree[u] as usize {
                let dest = self.action[u][j] as usize;
                let bit = 1 << dest;
                require(
                    expected & bit != 0 && seen & bit == 0,
                    "missing/duplicate/illegal edge",
                )?;
                seen |= bit;
                let v = self.next[u][j];
                if b.goal(t, dest) {
                    require(v == GOAL, "goal priority")?;
                    winning |= self.choice[u] == GOAL && self.rank[u] == 1;
                    require(self.status[u] == WIN, "immediate goal not W")?;
                    continue;
                }
                let id = if t == 0 {
                    b.state(dest, c, 1)
                } else {
                    b.state(a, dest, 0)
                };
                require(v as usize == id && self.active[id], "edge/state identity")?;
                if self.status[id] == LOSS && self.choice[u] == v && self.rank[u] > self.rank[id] {
                    winning = true;
                }
                if self.status[id] == DRAW && draw_child.is_none() {
                    draw_child = Some(v);
                }
                match self.status[u] {
                    LOSS => require(
                        self.status[id] == WIN && self.rank[u] > self.rank[id],
                        "L must have all W children with strict ranks",
                    )?,
                    DRAW => require(self.status[id] != LOSS, "D has a winning move")?,
                    WIN => {}
                    _ => return Err("inactive status in active list".into()),
                }
            }
            require(seen == expected, "all legal actions required")?;
            match self.status[u] {
                WIN => {
                    require(winning && self.rank[u] > 0, "W witness/rank")?;
                    r.w += 1;
                }
                LOSS => {
                    require(self.rank[u] > 0, "L rank")?;
                    r.l += 1;
                }
                DRAW => {
                    require(self.rank[u] == 0, "D rank must remain0")?;
                    self.choice[u] = draw_child.ok_or("D without D successor")?;
                    r.d += 1;
                }
                _ => return Err("invalid classification".into()),
            }
            r.max_rank = r.max_rank.max(self.rank[u]);
        }
        require(
            u32::from(r.w) + u32::from(r.l) + u32::from(r.d) == u32::from(r.active),
            "WDL census",
        )?;
        Ok(r)
    }
    fn fixture(&self, b: &Board, path: &str) -> Result<()> {
        let mut out = BufWriter::new(fresh(path)?);
        out.write_all(FIXTURE_MAGIC)?;
        out.write_all(&[b.n as u8, candidates(b.n) as u8])?;
        out.write_all(&0u16.to_le_bytes())?;
        out.write_all(&b.mask.to_le_bytes())?;
        out.write_all(&(self.raw as u32).to_le_bytes())?;
        out.write_all(&(self.len as u32).to_le_bytes())?;
        out.write_all(&self.edges.to_le_bytes())?;
        for u in 0..self.raw {
            out.write_all(&[self.status[u], self.degree[u]])?;
            out.write_all(&self.rank[u].to_le_bytes())?;
            out.write_all(&self.choice[u].to_le_bytes())?;
            for j in 0..self.degree[u] as usize {
                out.write_all(&[self.action[u][j]])?;
                out.write_all(&self.next[u][j].to_le_bytes())?;
            }
        }
        out.flush()?;
        out.get_ref().sync_all()?;
        Ok(())
    }
}

#[derive(Default, Clone, Copy)]
struct Record {
    ordinal: u64,
    mask: u32,
    wall_count: u8,
    components: u8,
    initial_flags: u8,
    active: u16,
    max_rank: u16,
    edges: u32,
    w: u16,
    l: u16,
    d: u16,
    analysis_ns: u64,
    verification_ns: u64,
}
impl Record {
    fn bytes(self) -> [u8; 48] {
        let mut x = [0; 48];
        x[0..8].copy_from_slice(&self.ordinal.to_le_bytes());
        x[8..12].copy_from_slice(&self.mask.to_le_bytes());
        x[12] = self.wall_count;
        x[13] = self.components;
        x[14] = self.initial_flags;
        x[16..18].copy_from_slice(&self.active.to_le_bytes());
        x[18..20].copy_from_slice(&self.max_rank.to_le_bytes());
        x[20..24].copy_from_slice(&self.edges.to_le_bytes());
        x[24..26].copy_from_slice(&self.w.to_le_bytes());
        x[26..28].copy_from_slice(&self.l.to_le_bytes());
        x[28..30].copy_from_slice(&self.d.to_le_bytes());
        x[32..40].copy_from_slice(&self.analysis_ns.to_le_bytes());
        x[40..48].copy_from_slice(&self.verification_ns.to_le_bytes());
        x
    }
}
#[derive(Default, Clone, Copy)]
struct Stats {
    layouts: u64,
    active: u64,
    edges: u64,
    w: u64,
    l: u64,
    d: u64,
    analysis_ns: u128,
    verification_ns: u128,
}
impl Stats {
    // At most2^32 masks, each<=1250states/10000edges: integer totals fit u64.
    fn add(&mut self, r: Record) {
        self.layouts += 1;
        self.active += u64::from(r.active);
        self.edges += u64::from(r.edges);
        self.w += u64::from(r.w);
        self.l += u64::from(r.l);
        self.d += u64::from(r.d);
        self.analysis_ns += u128::from(r.analysis_ns);
        self.verification_ns += u128::from(r.verification_ns);
    }
    fn json(self) -> String {
        format!(
            "{{\"layouts\":{},\"active\":{},\"edges\":{},\"W\":{},\"L\":{},\"D\":{},\"analysis_ns\":{},\"verification_ns\":{}}}",
            self.layouts,
            self.active,
            self.edges,
            self.w,
            self.l,
            self.d,
            self.analysis_ns,
            self.verification_ns
        )
    }
}
fn pilot(ordinal: u64) -> bool {
    ordinal < 16 || ordinal % 4096 == 0
}
fn chosen(ordinal: u64, phase: &str, worker: u8, workers: u8) -> bool {
    if phase == "pilot" {
        pilot(ordinal)
    } else {
        !pilot(ordinal) && ordinal % u64::from(workers) == u64::from(worker)
    }
}
fn argument<'a>(args: &'a [String], name: &str) -> Result<&'a str> {
    let i = args
        .iter()
        .position(|a| a == name)
        .ok_or_else(|| format!("missing {name}"))?;
    args.get(i + 1)
        .map(String::as_str)
        .ok_or_else(|| format!("missing value for {name}").into())
}
fn optional<'a>(args: &'a [String], name: &str, default: &'a str) -> &'a str {
    args.iter()
        .position(|a| a == name)
        .and_then(|i| args.get(i + 1))
        .map_or(default, String::as_str)
}
fn options(args: &[String], allowed: &[&str]) -> Result<()> {
    require(args.len() % 2 == 0, "options need flag/value pairs")?;
    let mut seen = std::collections::BTreeSet::new();
    for pair in args.chunks_exact(2) {
        require(
            allowed.contains(&pair[0].as_str()) && seen.insert(pair[0].as_str()),
            "unknown/duplicate option",
        )?;
    }
    Ok(())
}
fn summary(path: &str, body: &str) -> Result<()> {
    let mut f = fresh(path)?;
    f.write_all(body.as_bytes())?;
    f.write_all(b"\n")?;
    f.sync_all()?;
    println!("{body}");
    Ok(())
}
fn enumerate(args: &[String]) -> Result<()> {
    options(args, &["--side", "--masks", "--summary"])?;
    let n = optional(args, "--side", "5").parse::<usize>()?;
    require(n == 3 || n == 5, "side domain")?;
    let masks = argument(args, "--masks")?;
    let summary_path = argument(args, "--summary")?;
    require(
        !Path::new(summary_path).exists(),
        "summary output must be fresh",
    )?;
    let start = Instant::now();
    let mut out = BufWriter::with_capacity(65536, fresh(masks)?);
    out.write_all(MASK_MAGIC)?;
    out.write_all(&(n as u32).to_le_bytes())?;
    out.write_all(&(candidates(n) as u32).to_le_bytes())?;
    out.write_all(&0u64.to_le_bytes())?;
    let mut count = 0u64;
    let mut by_wall = [0u64; 33];
    let traversal = Instant::now();
    independent_sets(
        candidates(n) as i32 - 1,
        0,
        0,
        &collisions(n),
        &mut |mask| {
            out.write_all(&mask.to_le_bytes())?;
            count += 1;
            by_wall[mask.count_ones() as usize] += 1;
            Ok(())
        },
    )?;
    let traversal_seconds = traversal.elapsed().as_secs_f64();
    let output = Instant::now();
    out.flush()?;
    out.seek(SeekFrom::Start(16))?;
    out.write_all(&count.to_le_bytes())?;
    out.flush()?;
    out.get_ref().sync_all()?;
    let output_finalize_seconds = output.elapsed().as_secs_f64();
    drop(out);
    summary(
        summary_path,
        &format!(
            "{{\"stage\":\"enumeration\",\"side\":{n},\"candidates\":{},\"layouts\":{count},\"by_wall_count\":{by_wall:?},\"traversal_including_stream_output_seconds\":{traversal_seconds},\"output_finalize_seconds\":{output_finalize_seconds},\"whole_before_summary_seconds\":{},\"peak_rss_B\":{}}}",
            candidates(n),
            start.elapsed().as_secs_f64(),
            peak_rss()
        ),
    )
}
fn u32_read(input: &mut impl Read) -> Result<u32> {
    let mut b = [0; 4];
    input.read_exact(&mut b)?;
    Ok(u32::from_le_bytes(b))
}
fn u64_read(input: &mut impl Read) -> Result<u64> {
    let mut b = [0; 8];
    input.read_exact(&mut b)?;
    Ok(u64::from_le_bytes(b))
}
fn solve(args: &[String]) -> Result<()> {
    options(
        args,
        &[
            "--masks",
            "--phase",
            "--worker-index",
            "--workers",
            "--records",
            "--summary",
            "--candidate",
        ],
    )?;
    let phase = argument(args, "--phase")?;
    require(
        phase == "pilot" || phase == "remaining",
        "pilot or remaining only",
    )?;
    let workers = optional(args, "--workers", "1").parse::<u8>()?;
    let worker = optional(args, "--worker-index", "0").parse::<u8>()?;
    require(
        (1..=4).contains(&workers) && worker < workers,
        "shard domain",
    )?;
    require(
        phase != "pilot" || (workers == 1 && worker == 0),
        "pilot single worker",
    )?;
    require(
        !Path::new(argument(args, "--summary")?).exists(),
        "summary output must be fresh",
    )?;
    let candidate = argument(args, "--candidate")?;
    require(
        !Path::new(candidate).exists(),
        "candidate output must be fresh even if no D occurs",
    )?;
    let start = Instant::now();
    let file = File::open(argument(args, "--masks")?)?;
    let file_bytes = file.metadata()?.len();
    let mut input = BufReader::new(file);
    let mut magic = [0; 8];
    input.read_exact(&mut magic)?;
    require(&magic == MASK_MAGIC, "mask magic")?;
    let n = u32_read(&mut input)? as usize;
    require(
        n == 5,
        "actual solve scope is5x5; smaller boards only fixtures/tests",
    )?;
    require(
        u32_read(&mut input)? as usize == candidates(n),
        "candidate header",
    )?;
    let count = u64_read(&mut input)?;
    require(count > 0 && count <= 1u64 << 32, "mask count range")?;
    require(
        file_bytes == 24 + count.checked_mul(4).ok_or("mask length overflow")?,
        "incomplete/trailing masks file",
    )?;
    let expected = (0..count)
        .filter(|&i| chosen(i, phase, worker, workers))
        .count() as u64;
    let mut out = fresh(argument(args, "--records")?)?;
    out.write_all(RECORD_MAGIC)?;
    out.write_all(&[
        n as u8,
        if phase == "pilot" { 1 } else { 2 },
        workers,
        worker,
    ])?;
    out.write_all(&count.to_le_bytes())?;
    out.write_all(&expected.to_le_bytes())?;
    out.write_all(&RECORD_BYTES.to_le_bytes())?;
    let mut graph = Graph::new();
    let mut total = Stats::default();
    let mut cold = Stats::default();
    let mut by_wall = [Stats::default(); 33];
    let mut by_components = [Stats::default(); 26];
    let mut by_initial_reach = [Stats::default(); 8];
    let mut first_d = None;
    let mut previous = None;
    let mut output_ns = 0u128;
    for ordinal in 0..count {
        let mask = u32_read(&mut input)?;
        require(
            previous.is_none_or(|last| last < mask),
            "masks must be strictly ascending/no duplicates",
        )?;
        previous = Some(mask);
        if !chosen(ordinal, phase, worker, workers) {
            continue;
        }
        let analysis = Instant::now();
        let board = Board::new(n, mask)?;
        graph.build(&board)?;
        let analysis_ns = nanos(analysis)?;
        let validation = Instant::now();
        let mut r = graph.verify(&board)?;
        r.ordinal = ordinal;
        r.analysis_ns = analysis_ns;
        r.verification_ns = nanos(validation)?;
        let output = Instant::now();
        out.write_all(&r.bytes())?;
        if r.d > 0 && first_d.is_none() {
            let state = graph.ids[..graph.len]
                .iter()
                .copied()
                .find(|&id| graph.status[id as usize] == DRAW)
                .ok_or("D census mismatch")?;
            graph.fixture(&board, candidate)?;
            first_d = Some((ordinal, mask, state));
        }
        output_ns += output.elapsed().as_nanos();
        total.add(r);
        if ordinal < 16 {
            cold.add(r);
        }
        by_wall[r.wall_count as usize].add(r);
        by_components[r.components as usize].add(r);
        by_initial_reach[r.initial_flags as usize].add(r);
    }
    require(total.layouts == expected, "selected complement census")?;
    let output = Instant::now();
    out.flush()?;
    out.sync_all()?;
    drop(out);
    output_ns += output.elapsed().as_nanos();
    let array = |items: &[Stats]| items.iter().map(|s| s.json()).collect::<Vec<_>>().join(",");
    let first = first_d.map_or_else(
        || "null".to_string(),
        |(id, mask, state)| format!("{{\"ordinal\":{id},\"mask\":{mask},\"raw_state\":{state}}}"),
    );
    summary(
        argument(args, "--summary")?,
        &format!(
            "{{\"stage\":\"analysis\",\"phase\":\"{phase}\",\"side\":5,\"workers\":{workers},\"worker_index\":{worker},\"input_layouts\":{count},\"expected_selected\":{expected},\"total\":{},\"cold_first16\":{},\"by_wall_count\":[{}],\"by_components\":[{}],\"by_initial_shape_flags\":[{}],\"first_D\":{first},\"output_ns\":{output_ns},\"whole_before_summary_seconds\":{},\"peak_rss_B\":{}}}",
            total.json(),
            cold.json(),
            array(&by_wall),
            array(&by_components),
            array(&by_initial_reach),
            start.elapsed().as_secs_f64(),
            peak_rss()
        ),
    )
}
fn fixture(args: &[String]) -> Result<()> {
    options(args, &["--side", "--mask", "--output"])?;
    let n = optional(args, "--side", "5").parse::<usize>()?;
    let text = argument(args, "--mask")?;
    let mask = if let Some(hex) = text.strip_prefix("0x") {
        u32::from_str_radix(hex, 16)?
    } else {
        text.parse::<u32>()?
    };
    let board = Board::new(n, mask)?;
    let mut graph = Graph::new();
    graph.build(&board)?;
    let r = graph.verify(&board)?;
    graph.fixture(&board, argument(args, "--output")?)?;
    println!(
        "{{\"stage\":\"fixture\",\"side\":{n},\"mask\":{mask},\"active\":{},\"edges\":{},\"W\":{},\"L\":{},\"D\":{}}}",
        r.active, r.edges, r.w, r.l, r.d
    );
    Ok(())
}
fn run() -> Result<()> {
    require(usize::BITS >= 64, "64-bit execution required")?;
    let args = std::env::args().skip(1).collect::<Vec<_>>();
    match args.first().map(String::as_str) {
        Some("enumerate") => enumerate(&args[1..]),
        Some("solve") => solve(&args[1..]),
        Some("fixture") => fixture(&args[1..]),
        _ => Err("expected enumerate | solve | fixture; all outputs fresh".into()),
    }
}
fn main() {
    if let Err(error) = run() {
        eprintln!("zero-stock finite analysis refused/failed: {error}");
        std::process::exit(1);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn collision405_boundaries_overlap_and_cross() {
        let h = Board::new(5, 1).unwrap();
        assert_eq!(h.adj[0] & (1 << 5), 0);
        assert_eq!(h.adj[1] & (1 << 6), 0);
        assert_ne!(h.adj[2] & (1 << 7), 0);
        let v = Board::new(5, 1 << 16).unwrap();
        assert_eq!(v.adj[0] & (1 << 1), 0);
        assert_eq!(v.adj[5] & (1 << 6), 0);
        assert_ne!(v.adj[10] & (1 << 11), 0);
        assert!(!valid_mask(5, 3));
        assert!(!valid_mask(5, (1 << 16) | (1 << 20)));
        assert!(!valid_mask(5, 1 | (1 << 16)));
        assert!(valid_mask(5, (1 << 3) | (1 << 4)));
        assert!(valid_mask(5, 1 << 31));
        let c = collisions(5);
        for i in 0..32 {
            for j in 0..32 {
                assert_eq!(c[i] & (1 << j) != 0, c[j] & (1 << i) != 0);
            }
        }
    }
    #[test]
    fn enumeration405_tiny_matches_pairwise_bruteforce() {
        let mut actual = Vec::new();
        independent_sets(7, 0, 0, &collisions(3), &mut |m| {
            actual.push(m);
            Ok(())
        })
        .unwrap();
        let literal = |i: usize, j: usize| {
            let (ai, aj) = (i % 4, j % 4);
            if i / 4 != j / 4 {
                ai == aj
            } else if i < 4 {
                ai / 2 == aj / 2 && (ai % 2).abs_diff(aj % 2) == 1
            } else {
                ai % 2 == aj % 2 && (ai / 2).abs_diff(aj / 2) == 1
            }
        };
        let expected = (0..256u32)
            .filter(|m| {
                !(0..8).any(|i| {
                    m & (1 << i) != 0 && (i + 1..8).any(|j| m & (1 << j) != 0 && literal(i, j))
                })
            })
            .collect::<Vec<_>>();
        assert_eq!(actual, expected);
        assert!(actual.windows(2).all(|w| w[0] < w[1]));
    }
    #[test]
    fn jumps405_straight_priority_side_and_goal() {
        let b = Board::new(5, 0).unwrap();
        let moves = b.moves(10, 11);
        assert_ne!(moves & (1 << 12), 0);
        assert_eq!(moves & ((1 << 6) | (1 << 16)), 0);
        let blocked = Board::new(5, 1 << 21).unwrap();
        let moves = blocked.moves(10, 11);
        assert_eq!(moves & (1 << 12), 0);
        assert_eq!(moves & ((1 << 6) | (1 << 16)), (1 << 6) | (1 << 16));
        let mut g = Graph::new();
        g.build(&b).unwrap();
        g.verify(&b).unwrap();
        let u = b.state(15, 24, 0);
        assert_eq!(g.status[u], WIN);
        assert_eq!(g.rank[u], 1);
        assert_eq!(g.choice[u], GOAL);
        // Occupied goal leaves can force retreat; wall distance is not monotone.
        for (mask, own, other, retreat, goal, turn) in
            [(1 << 28, 15, 20, 10, 20, 0), (1 << 16, 5, 0, 10, 0, 1)]
        {
            let leaf = Board::new(5, mask).unwrap();
            assert_eq!(leaf.moves(own, other), 1 << retreat);
            assert_eq!(leaf.moves(other, retreat), 1 << own);
            assert_ne!(leaf.moves(retreat, own) & (1 << goal), 0);
            g.build(&leaf).unwrap();
            g.verify(&leaf).unwrap();
            let state = if turn == 0 {
                leaf.state(own, other, turn)
            } else {
                leaf.state(other, own, turn)
            };
            assert_eq!(g.status[state], WIN);
            assert_eq!(g.rank[state], 3);
        }
    }
    #[test]
    fn wdl405_queue_handles_goal_loss_and_draw_cycle() {
        let mut g = Graph::new();
        g.raw = 7;
        g.len = 7;
        for i in 0..7 {
            g.ids[i] = i as u16;
            g.active[i] = true;
            g.status[i] = DRAW;
            g.degree[i] = 1;
        }
        g.next[0][0] = GOAL;
        g.next[1][0] = 0;
        g.next[2][0] = 1;
        g.next[3][0] = 3;
        g.next[4][0] = 3;
        g.next[5][0] = 0;
        g.next[5][1] = 3;
        g.degree[5] = 2;
        g.next[6][0] = 2;
        g.propagate().unwrap();
        assert_eq!(&g.status[..7], &[WIN, LOSS, WIN, DRAW, DRAW, DRAW, LOSS]);
        assert_eq!(&g.rank[..7], &[1, 2, 3, 0, 0, 0, 4]);
    }
    #[test]
    fn active405_has_no_initial_start_reachability_gate() {
        // Synthetic adjacency isolates start2; this tests the state filter, not a legal-wall claim.
        let mut b = Board::new(5, 0).unwrap();
        for q in [1, 3, 7] {
            b.close(2, q);
        }
        assert_eq!(b.reach(0) & (1 << 2), 0);
        let mut g = Graph::new();
        g.build(&b).unwrap();
        let r = g.verify(&b).unwrap();
        assert!(r.active > 0);
        assert!(g.active[b.state(0, 24, 0)]);
        assert!(!g.active[b.state(2, 24, 0)]);
    }
    #[test]
    fn selection405_pilot_complement_disjoint_and_record_width() {
        let mut seen = vec![0u8; 10000];
        for (i, x) in seen.iter_mut().enumerate() {
            if pilot(i as u64) {
                *x += 1;
            }
            for w in 0..4 {
                if chosen(i as u64, "remaining", w, 4) {
                    *x += 1;
                }
            }
        }
        assert!(seen.iter().all(|&x| x == 1));
        assert!(pilot(0) && pilot(15) && pilot(4096) && !pilot(16) && !pilot(4097));
        assert_eq!(Record::default().bytes().len(), 48);
    }
    #[test]
    fn certificate405_fixed_masks_verify_every_edge() {
        let mut g = Graph::new();
        for mask in [0, 1, (1 << 0) | (1 << 2) | (1 << 20) | (1 << 22)] {
            let b = Board::new(5, mask).unwrap();
            g.build(&b).unwrap();
            let r = g.verify(&b).unwrap();
            assert_eq!(
                u32::from(r.w) + u32::from(r.l) + u32::from(r.d),
                u32::from(r.active)
            );
        }
        let b = Board::new(5, 0).unwrap();
        g.build(&b).unwrap();
        let r = g.verify(&b).unwrap();
        assert_eq!(r.active, 770);
    }
}

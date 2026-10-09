//! Task351-only definitions. No Zobrist dispatch in production Search/Table.
use super::*;
use quoridor_core::research::{ContextUndo, HistoryKey, Ruleset};
use std::{collections::BTreeMap, rc::Rc};

// Frozen before outcomes. SplitMix64-generated feature table, random-access
// integer domains; no hardware RNG or HashMap iteration order participates.
const Z_VERSION: &str = "full-counted-key-zobrist351-v1";
const Z_SEED: u64 = 0x3510_2026_1009_a45b;
const Z_DOMAIN: u64 = 0x514b_4655_4c4c_0001;
fn mix(mut x: u64) -> u64 {
    x = x.wrapping_add(0x9e37_79b9_7f4a_7c15);
    x = (x ^ (x >> 30)).wrapping_mul(0xbf58_476d_1ce4_e5b9);
    x = (x ^ (x >> 27)).wrapping_mul(0x94d0_49bb_1331_11eb);
    x ^ (x >> 31)
}
fn feature(domain: u64, value: u64) -> u64 {
    mix(Z_SEED ^ mix(Z_DOMAIN ^ domain) ^ mix(value))
}
fn record_key(e: &CountedHistoryEntry) -> HistoryKey {
    HistoryKey {
        pawns: e.0,
        stocks: e.1,
        turn: e.2,
        horizontal: e.3,
        vertical: e.4,
    }
}
fn record(k: HistoryKey, n: u16) -> CountedHistoryEntry {
    (k.pawns, k.stocks, k.turn, k.horizontal, k.vertical, n)
}
fn position(k: &Key) -> Position {
    Position {
        pawns: k.pawns,
        walls_remaining: k.walls,
        horizontal: k.horizontal,
        vertical: k.vertical,
        turn: k.turn,
        winner: k.winner,
    }
}
fn overwrite_board(k: &mut Key, c: &SigmaContext) {
    let p = c.position();
    k.pawns = p.pawns;
    k.walls = p.walls_remaining;
    k.horizontal = p.horizontal;
    k.vertical = p.vertical;
    k.turn = p.turn;
    k.winner = p.winner;
    k.ply = c.total_ply();
}
fn board_hash(k: &Key) -> u64 {
    let rule = match k.ruleset {
        Ruleset::Standard2pThreefold => 1,
    };
    let mut h = feature(0, 1)
        ^ feature(1, rule)
        ^ feature(2, u64::from(k.pawns[0]))
        ^ feature(3, u64::from(k.pawns[1]))
        ^ feature(4, u64::from(k.walls[0]))
        ^ feature(5, u64::from(k.walls[1]))
        ^ feature(6, u64::from(k.turn))
        ^ feature(7, u64::from(k.winner.unwrap_or(2)))
        ^ feature(8, u64::from(k.ply))
        ^ feature(9, u64::from(k.synthetic));
    for bit in 0..64 {
        if k.horizontal & (1u64 << bit) != 0 {
            h ^= feature(10, bit);
        }
        if k.vertical & (1u64 << bit) != 0 {
            h ^= feature(11, bit);
        }
    }
    h
}
fn history_hash(e: &CountedHistoryEntry) -> u64 {
    // Mix a whole counted record before XORing records. Merely XORing each
    // field across records would cancel repeated pawn/stock/turn features.
    let values = [
        u64::from(e.0[0]),
        u64::from(e.0[1]),
        u64::from(e.1[0]),
        u64::from(e.1[1]),
        u64::from(e.2),
        e.3,
        e.4,
        u64::from(e.5),
    ];
    let mut h = feature(100, 1);
    for (i, value) in values.into_iter().enumerate() {
        h = mix(h ^ feature(101 + i as u64, value));
    }
    h
}
fn full_hash(k: &Key) -> u64 {
    k.history.iter().fold(
        board_hash(k) ^ feature(12, k.history.len() as u64),
        |h, e| h ^ history_hash(e),
    )
}
fn full_oracle(k: &Key) -> u64 {
    // Independent full traversal, not board_hash/history_hash/full_hash or an
    // update replay. Only the frozen feature table/PRNG primitive is shared.
    let ruleset = match k.ruleset {
        Ruleset::Standard2pThreefold => 1,
    };
    let scalars = [
        1,
        ruleset,
        k.pawns[0] as u64,
        k.pawns[1] as u64,
        k.walls[0] as u64,
        k.walls[1] as u64,
        k.turn as u64,
        k.winner.map_or(2, u64::from),
        k.ply as u64,
        k.synthetic as u64,
    ];
    let mut h = 0;
    for (domain, value) in scalars.into_iter().enumerate() {
        h ^= feature(domain as u64, value);
    }
    for (domain, mask) in [(10, k.horizontal), (11, k.vertical)] {
        let mut pending = mask;
        while pending != 0 {
            h ^= feature(domain, u64::from(pending.trailing_zeros()));
            pending &= pending - 1;
        }
    }
    h ^= feature(12, k.history.len() as u64);
    for e in &k.history {
        let mut encoded = feature(100, 1);
        for (domain, value) in [
            (101, e.0[0] as u64),
            (102, e.0[1] as u64),
            (103, e.1[0] as u64),
            (104, e.1[1] as u64),
            (105, e.2 as u64),
            (106, e.3),
            (107, e.4),
            (108, e.5 as u64),
        ] {
            encoded = mix(encoded ^ feature(domain, value));
        }
        h ^= encoded;
    }
    h
}
fn validate_numeric(k: &Key) -> std::result::Result<(), &'static str> {
    position(k).checked().map_err(|_| "board")?;
    if k.history.len() > usize::from(u16::MAX) + 1 {
        return Err("history length");
    }
    let mut previous = None;
    for e in &k.history {
        let hk = record_key(e);
        if e.5 == 0 || e.5 > 3 || previous.is_some_and(|p| p >= hk) {
            return Err("count/order/duplicate");
        }
        // Delegate geometry to maintained Position rather than copy its rules.
        let winner = if hk.pawns[0] / 9 == 8 {
            Some(0)
        } else if hk.pawns[1] / 9 == 0 {
            Some(1)
        } else {
            None
        };
        Position {
            pawns: hk.pawns,
            walls_remaining: hk.stocks,
            horizontal: hk.horizontal,
            vertical: hk.vertical,
            turn: hk.turn,
            winner,
        }
        .checked()
        .map_err(|_| "history geometry")?;
        previous = Some(hk);
    }
    if !k.synthetic {
        SigmaContext::from_counts_with_rules(
            position(k),
            k.ply,
            k.history.iter().map(|e| (record_key(e), e.5)).collect(),
            k.ruleset,
        )
        .map_err(|_| "normal representation")?;
    }
    Ok(())
}

#[derive(Debug, PartialEq, Eq)]
struct RestorationFailure {
    stage: &'static str,
    requested_parent_depth: usize,
    observed_depth: usize,
    cause: &'static str,
}
#[derive(Debug, PartialEq, Eq)]
struct BranchError {
    primary: &'static str,
    restorations: Vec<RestorationFailure>,
}
impl BranchError {
    fn primary(primary: &'static str) -> Self {
        Self {
            primary,
            restorations: Vec::new(),
        }
    }
}
struct ZScratch {
    // Exclusive private cursor. Consumers cannot mutate history behind it.
    cursor: SigmaContext,
    key: Key,
    hash: u64,
    owner: Rc<()>,
    depth: usize,
}
struct ZUndo {
    core: ContextUndo,
    arrival: HistoryKey,
    old_count: u16,
    parent_hash: u64,
    owner: Rc<()>,
    depth: usize,
}
impl ZScratch {
    fn new(c: &SigmaContext, reserve_path: usize) -> std::result::Result<Self, &'static str> {
        c.validate_normal().map_err(|_| "normal context")?;
        let mut key = Key::of(c);
        validate_numeric(&key)?;
        // This reserves only Key.history growth on the fixed private path.
        // The ordinary cloned canonical cursor may reserve its overlay during
        // make_move; that path allocation remains an update/whole cost.
        // Full owned key output still needs copying.
        key.history
            .try_reserve(reserve_path)
            .map_err(|_| "reserve")?;
        let hash = full_hash(&key);
        Ok(Self {
            cursor: c.clone(),
            key,
            hash,
            owner: Rc::new(()),
            depth: 0,
        })
    }
    fn make(&mut self, id: u16) -> std::result::Result<ZUndo, &'static str> {
        // Canonical make first; an exhausted private insertion reservation is
        // rolled back before any hash/history mutation. Existing arrivals do
        // not need a new slot. This is not a production history/depth policy.
        let core = self.cursor.make_move(id).map_err(|_| "canonical make")?;
        let arrival = HistoryKey::from(self.cursor.position());
        let i = self.key.history.binary_search_by_key(&arrival, record_key);
        if i.is_err() && self.key.history.len() == self.key.history.capacity() {
            self.cursor
                .unmake_move(core)
                .map_err(|_| "capacity rollback")?;
            return Err("scratch capacity");
        }
        let old_count = i.as_ref().ok().map_or(0, |&i| self.key.history[i].5);
        let undo = ZUndo {
            core,
            arrival,
            old_count,
            parent_hash: self.hash,
            owner: self.owner.clone(),
            depth: self.depth,
        };
        self.hash ^= board_hash(&self.key) ^ feature(12, self.key.history.len() as u64);
        match i {
            Ok(i) => {
                self.hash ^= history_hash(&self.key.history[i]);
                self.key.history[i].5 += 1;
                self.hash ^= history_hash(&self.key.history[i]);
            }
            Err(i) => {
                let e = record(arrival, 1);
                self.hash ^= history_hash(&e);
                self.key.history.insert(i, e);
            }
        }
        overwrite_board(&mut self.key, &self.cursor);
        self.hash ^= board_hash(&self.key) ^ feature(12, self.key.history.len() as u64);
        self.depth += 1;
        Ok(undo)
    }
    fn unmake(&mut self, u: ZUndo) -> std::result::Result<(), &'static str> {
        if !Rc::ptr_eq(&self.owner, &u.owner) || self.depth != u.depth + 1 {
            return Err("owner/LIFO");
        }
        let i = self
            .key
            .history
            .binary_search_by_key(&u.arrival, record_key)
            .map_err(|_| "arrival missing")?;
        if self.key.history[i].5 != u.old_count + 1 {
            return Err("arrival count");
        }
        // Canonical validation occurs before changing either cursor or hash.
        self.cursor
            .unmake_move(u.core)
            .map_err(|_| "canonical unmake")?;
        self.hash ^= board_hash(&self.key)
            ^ feature(12, self.key.history.len() as u64)
            ^ history_hash(&self.key.history[i]);
        if u.old_count == 0 {
            self.key.history.remove(i);
        } else {
            self.key.history[i].5 = u.old_count;
            self.hash ^= history_hash(&self.key.history[i]);
        }
        overwrite_board(&mut self.key, &self.cursor);
        self.hash ^= board_hash(&self.key) ^ feature(12, self.key.history.len() as u64);
        self.depth -= 1;
        debug_assert_eq!(self.hash, u.parent_hash);
        Ok(())
    }
    fn with_child<T>(
        &mut self,
        id: u16,
        f: impl FnOnce(&mut Self) -> std::result::Result<T, BranchError>,
    ) -> std::result::Result<T, BranchError> {
        let u = self.make(id).map_err(BranchError::primary)?;
        let requested_parent_depth = u.depth;
        let result = f(self);
        let restored = self.unmake(u);
        let restoration_fact = |cause| RestorationFailure {
            stage: "unmake",
            requested_parent_depth,
            observed_depth: self.depth,
            cause,
        };
        match (result, restored) {
            (Err(mut primary), Err(secondary)) => {
                // Keep inner stage facts in order; append this outer attempt.
                primary.restorations.push(restoration_fact(secondary));
                Err(primary)
            }
            (Err(primary), Ok(())) => Err(primary),
            (Ok(_), Err(secondary)) => {
                let mut error = BranchError::primary(secondary);
                error.restorations.push(restoration_fact(secondary));
                Err(error)
            }
            (Ok(v), Ok(())) => Ok(v),
        }
    }
    fn verify(&self) {
        assert_eq!(self.key, Key::of(&self.cursor));
        assert_eq!(self.hash, full_oracle(&self.key));
        validate_numeric(&self.key).unwrap();
    }
}
fn node(depth: u16) -> NodeValue {
    NodeValue {
        depth,
        value: 0.25,
        bound: Bound::Exact,
        best: Some(13),
    }
}
fn entry(key: Key, depth: u16) -> Entry {
    let n = node(depth);
    Entry {
        generation: 0,
        key,
        depth: n.depth,
        value: n.value,
        bound: n.bound,
        best: n.best,
    }
}

#[test]
fn tt351_paired_identity_counts_and_unpaired_pv() {
    let c = SigmaContext::from_prefix(&[]).unwrap();
    let key = Key::of(&c);
    let history_ptr = key.history.as_ptr();
    let capacity = key.history.capacity();
    let mut t = Table::new(1).unwrap();
    let mut stats = SearchStats::default();
    let (probe, hit) = t.probe_owned(key, &mut stats);
    assert!(hit.is_none());
    assert_eq!(stats.tt_hashes, 1);
    t.insert_probed(probe, node(2), &mut stats);
    let e = t.get(&Key::of(&c)).unwrap();
    assert_eq!(e.key.history.as_ptr(), history_ptr);
    assert_eq!(e.key.history.capacity(), capacity);
    assert_eq!(stats.tt_hashes, 1); // get/PV is still uninstrumented
    assert!(t.probe(&Key::of(&c), &mut stats).is_some());
    t.insert(entry(Key::of(&c), 2), &mut stats);
    assert_eq!((stats.tt_probes, stats.tt_hashes), (2, 3));
}
#[test]
fn tt351_pair_empty_disabled_early_drop_and_byte_refusal() {
    let c = SigmaContext::from_prefix(&[]).unwrap();
    let mut empty = Table::new(0).unwrap();
    let mut stats = SearchStats::default();
    let (probe, hit) = empty.probe_owned(Key::of(&c), &mut stats);
    assert!(hit.is_none());
    empty.insert_probed(probe, node(2), &mut stats);
    assert_eq!((stats.tt_probes, stats.tt_hashes), (1, 0));
    let mut t = Table::new(1).unwrap();
    let floor = t.retained_bytes();
    t.byte_limit = floor; // every nonempty history payload refused
    let (probe, _) = t.probe_owned(Key::of(&c), &mut stats);
    t.insert_probed(probe, node(2), &mut stats);
    assert_eq!(stats.tt_capacity_skips, 1);
    assert_eq!(t.retained_bytes(), floor);
    assert!(t.get(&Key::of(&c)).is_none());
    let before = stats.tt_hashes;
    let (unused, _) = t.probe_owned(Key::of(&c), &mut stats);
    drop(unused); // exact TT cutoff/cancel/error owns and drops unused key
    assert_eq!(stats.tt_hashes, before + 1);
    assert_eq!(t.retained_bytes(), floor);
}
#[test]
fn tt351_pair_index_collision_depth_protection_and_generation() {
    let c = SigmaContext::from_prefix(&[]).unwrap();
    let child = c.play(c.legal_ids()[0]).unwrap();
    let mut t = Table::new(1).unwrap(); // force same direct-map index
    let mut s = SearchStats::default();
    t.next_generation();
    t.insert(entry(Key::of(&c), 4), &mut s);
    let (p, hit) = t.probe_owned(Key::of(&child), &mut s);
    assert!(hit.is_none());
    assert_eq!(s.tt_collisions, 1);
    t.insert_probed(p, node(2), &mut s);
    assert!(t.get(&Key::of(&c)).is_some()); // deeper same-generation protected
    t.next_generation();
    let (p, _) = t.probe_owned(Key::of(&child), &mut s);
    t.insert_probed(p, node(2), &mut s);
    assert!(t.get(&Key::of(&c)).is_none());
    assert!(t.get(&Key::of(&child)).is_some());
    assert_eq!(s.tt_replacements, 1);
    t.discard_uncommitted();
    assert!(t.get(&Key::of(&child)).is_none());
    assert_eq!(t.heap_bytes, 0);
}
#[test]
fn tt351_layout_and_accounting_unchanged() {
    // Exact preimage field declarations, not candidate aliases.
    #[allow(dead_code)]
    struct OldTable {
        slots: Vec<Option<Entry>>,
        generation: u64,
        committed: u64,
        heap_bytes: usize,
        byte_limit: usize,
    }
    #[allow(dead_code)]
    struct OldEntry {
        generation: u64,
        key: Key,
        depth: u16,
        value: f32,
        bound: Bound,
        best: Option<u16>,
    }
    assert_eq!(
        std::mem::size_of::<Table>(),
        std::mem::size_of::<OldTable>()
    );
    assert_eq!(
        std::mem::align_of::<Table>(),
        std::mem::align_of::<OldTable>()
    );
    assert_eq!(
        std::mem::size_of::<Entry>(),
        std::mem::size_of::<OldEntry>()
    );
    let t = Table::persistent(4096).unwrap();
    assert_eq!(
        t.retained_bytes(),
        std::mem::size_of::<Table>() + t.slots.capacity() * std::mem::size_of::<Option<Entry>>()
    );
    assert_eq!(t.byte_limit, 1024 * 1024);
}
#[test]
fn tt351_zobrist_full_field_history_and_order_contract() {
    assert_eq!(Z_VERSION, "full-counted-key-zobrist351-v1");
    let c = SigmaContext::from_prefix(&[13, 75, 14, 76]).unwrap();
    let k = Key::of(&c);
    assert_eq!(full_hash(&k), full_oracle(&k));
    let reversed = c.history_counts().into_iter().rev().collect();
    let reconstructed = SigmaContext::from_counts(c.position(), c.total_ply(), reversed).unwrap();
    assert_eq!(Key::of(&reconstructed), k);
    assert_eq!(full_hash(&Key::of(&reconstructed)), full_hash(&k));
    // Counted history, ply and synthetic are independent encoded fields, not
    // proof that chosen unequal keys cannot collide. Lookup always needs Eq.
    let mutations: [fn(&mut Key); 3] = [
        |k: &mut Key| k.history[0].5 = 2,
        |k: &mut Key| k.ply += 2,
        |k: &mut Key| k.synthetic = !k.synthetic,
    ];
    for mutate in mutations {
        let mut other = k.clone();
        mutate(&mut other);
        assert_ne!(other, k);
        assert_eq!(full_hash(&other), full_oracle(&other));
    }
    let mut bad = k.clone();
    bad.history.push(bad.history[0]);
    assert!(validate_numeric(&bad).is_err());
    bad = k.clone();
    bad.history[0].5 = 0;
    assert!(validate_numeric(&bad).is_err());
    bad = k.clone();
    bad.turn = 2;
    assert!(validate_numeric(&bad).is_err());
    bad = k.clone();
    bad.winner = Some(2);
    assert!(validate_numeric(&bad).is_err());
    bad = k.clone();
    bad.pawns[0] = 81;
    assert!(validate_numeric(&bad).is_err());
    bad = k.clone();
    bad.walls[0] = 11;
    assert!(validate_numeric(&bad).is_err());
    assert!("unsupported".parse::<Ruleset>().is_err());
}
#[test]
fn tt351_zobrist_incremental_arrival_count_and_nested_restoration() {
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let mut z = ZScratch::new(&root, 16).unwrap();
    let initial = z.key.clone();
    let ptr = z.key.history.as_ptr();
    let mut stack = Vec::new();
    for id in [13, 75, 14, 76, 13, 75, 14, 76, 13] {
        stack.push(z.make(id).unwrap());
        z.verify();
        assert_eq!(z.key.history.as_ptr(), ptr);
    }
    assert!(z.cursor.is_repetition_draw());
    assert!(z.make(13).is_err());
    while let Some(u) = stack.pop() {
        z.unmake(u).unwrap();
        z.verify();
    }
    assert_eq!(z.key, initial);
    assert_eq!(z.depth, 0);
    let err = z.with_child(13, |child| {
        child.with_child(75, |nested| {
            nested.verify();
            Err::<(), _>(BranchError::primary("cancel"))
        })
    });
    assert_eq!(err, Err(BranchError::primary("cancel")));
    z.verify();
    assert_eq!(z.key, initial);
    assert!(z.make(u16::MAX).is_err());
    z.verify();
    assert_eq!(z.key, initial);
}
#[test]
fn tt351_zobrist_wall_transition_owner_and_lifo_refusal() {
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let mut z = ZScratch::new(&root, 4).unwrap();
    let wall = z
        .cursor
        .legal_ids()
        .into_iter()
        .find(|&id| id >= 81)
        .unwrap();
    let first = z.make(wall).unwrap();
    z.verify();
    let child = z.cursor.legal_ids()[0];
    let second = z.make(child).unwrap();
    z.verify();
    // Refusal consumes this wrong-order token, so this isolated fixture stops
    // here; separately test complete successful undo in another scratch.
    let before = z.key.clone();
    assert_eq!(z.unmake(first), Err("owner/LIFO"));
    assert_eq!(z.key, before);
    z.verify();
    z.unmake(second).unwrap();
    z.verify();
    let mut other = ZScratch::new(&root, 4).unwrap();
    let foreign = other.make(wall).unwrap();
    let before = z.key.clone();
    assert_eq!(z.unmake(foreign), Err("owner/LIFO"));
    assert_eq!(z.key, before);
    z.verify();
    let mut normal = ZScratch::new(&root, 4).unwrap();
    let u = normal.make(wall).unwrap();
    normal.verify();
    normal.unmake(u).unwrap();
    normal.verify();
    assert_eq!(normal.key, Key::of(&root));
}
#[test]
fn tt351_zobrist_forced_hash_and_index_collisions_use_full_key() {
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let child = root.play(root.legal_ids()[0]).unwrap();
    let a = Key::of(&root);
    let b = Key::of(&child);
    let mut t = Table::new(1).unwrap();
    let forced = 0xdead_beef;
    let mut s = SearchStats::default();
    // Private injection into the actual common lookup/admission body. This
    // NEVER installs Zobrist as the production algorithm or fakes counters.
    t.insert_hashed(entry(a.clone(), 2), forced, &mut s);
    assert!(t.probe_hashed(&a, forced, &mut s).is_some());
    assert!(t.probe_hashed(&b, forced, &mut s).is_none());
    let mut different_history = a.clone();
    different_history.history[0].5 = 2;
    // Raw counted-history-only equality fixture, not an admitted legal replay.
    // Restoring just history must reproduce every other field exactly.
    let mut same_other_fields = different_history.clone();
    same_other_fields.history = a.history.clone();
    assert_eq!(same_other_fields, a);
    assert!(t.probe_hashed(&different_history, forced, &mut s).is_none());
    assert!(t.probe_hashed(&b, forced + 1, &mut s).is_none()); // same index, different hash
    assert_eq!(s.tt_collisions, 3);
}
#[test]
fn tt351_zobrist_independent_path_count_oracle() {
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let mut z = ZScratch::new(&root, 12).unwrap();
    let mut independent = BTreeMap::from([(HistoryKey::from(root.position()), 1u16)]);
    let mut undos = Vec::new();
    for _ in 0..8 {
        let id = z.cursor.legal_ids()[0];
        undos.push(z.make(id).unwrap());
        *independent.entry(z.cursor.position().into()).or_default() += 1;
        assert_eq!(
            z.cursor.history_counts(),
            independent
                .iter()
                .map(|(&k, &n)| (k, n))
                .collect::<Vec<_>>()
        );
        z.verify();
    }
    while let Some(u) = undos.pop() {
        let arrival = HistoryKey::from(z.cursor.position());
        let n = independent.get_mut(&arrival).unwrap();
        *n -= 1;
        if *n == 0 {
            independent.remove(&arrival);
        }
        z.unmake(u).unwrap();
        z.verify();
        assert_eq!(
            z.cursor.history_counts(),
            independent
                .iter()
                .map(|(&k, &n)| (k, n))
                .collect::<Vec<_>>()
        );
    }
}

#[test]
fn tt351_paired_vs_original_table_trace_all_other_stats_exact() {
    let mut baseline = Table::persistent(4).unwrap();
    let mut candidate = Table::persistent(4).unwrap();
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let child = root.play(root.legal_ids()[0]).unwrap();
    let contexts = [&root, &child, &root, &child];
    let mut old = SearchStats::default();
    let mut new = SearchStats::default();
    for generation in 1..=3 {
        baseline.next_generation();
        candidate.next_generation();
        for (i, c) in contexts.into_iter().enumerate() {
            let old_hit = baseline.probe(&Key::of(c), &mut old);
            let (key, new_hit) = candidate.probe_owned(Key::of(c), &mut new);
            assert_eq!(format!("{old_hit:?}"), format!("{new_hit:?}"));
            baseline.insert(entry(Key::of(c), (i + generation) as u16), &mut old);
            candidate.insert_probed(key, node((i + generation) as u16), &mut new);
            assert_eq!(baseline.retained_bytes(), candidate.retained_bytes());
            assert_eq!(baseline.heap_bytes, candidate.heap_bytes);
            let hashes = new.tt_hashes;
            new.tt_hashes = old.tt_hashes;
            assert_eq!(format!("{old:?}"), format!("{new:?}"));
            new.tt_hashes = hashes;
        }
    }
    assert_eq!(old.tt_hashes, 2 * new.tt_hashes);
    // A replacement refunded payload on the direct slot. Test refusal retains
    // old entry, generation and heap charge, using the unchanged budget rule.
    baseline.byte_limit = baseline.retained_bytes();
    candidate.byte_limit = candidate.retained_bytes();
    let larger = SigmaContext::from_prefix(&[13, 75, 14, 76]).unwrap();
    let (p, _) = candidate.probe_owned(Key::of(&larger), &mut new);
    baseline.probe(&Key::of(&larger), &mut old);
    baseline.insert(entry(Key::of(&larger), 9), &mut old);
    candidate.insert_probed(p, node(9), &mut new);
    assert_eq!(baseline.heap_bytes, candidate.heap_bytes);
    assert_eq!(old.tt_capacity_skips, new.tt_capacity_skips);
}

#[test]
fn tt351_search_error_cancel_nested_and_parent_restoration() {
    struct Bad;
    impl StaticEvaluator for Bad {
        fn evaluate(&self, _: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
            Err(SearchError::Evaluation("351 injected error".into()))
        }
    }
    let root = SigmaContext::from_prefix(&[13, 75]).unwrap();
    let before = Key::of(&root);
    let limits = SearchLimits {
        max_depth: 2,
        max_nodes: 100_000,
        time_limit: None,
        tt_entries: 64,
        use_pvs: true,
        use_tt: true,
    };
    assert!(search(&root, &Bad, &limits, &AtomicBool::new(false)).is_err());
    assert_eq!(Key::of(&root), before);
    let evaluator = DistanceEvaluator::new(0.0, 8.0);
    let cancelled = search(&root, &evaluator, &limits, &AtomicBool::new(true)).unwrap();
    assert_eq!(cancelled.stop, StopReason::Cancelled);
    assert_eq!(cancelled.stats.tt_hashes, 0);
    let disabled = SearchLimits {
        use_tt: false,
        ..limits.clone()
    };
    let no_tt = search(&root, &evaluator, &disabled, &AtomicBool::new(false)).unwrap();
    assert_eq!((no_tt.stats.tt_probes, no_tt.stats.tt_hashes), (0, 0));
    let mut nested = 0;
    let result = search_with_updates(
        &root,
        &evaluator,
        &limits,
        &AtomicBool::new(false),
        &mut |_| {
            let one = SearchLimits {
                max_depth: 1,
                ..limits.clone()
            };
            let inner = search(&root, &evaluator, &one, &AtomicBool::new(false)).unwrap();
            assert_eq!(inner.completed_depth, 1);
            assert_eq!(Key::of(&root), before);
            nested += 1;
        },
    )
    .unwrap();
    assert_eq!(result.completed_depth, 2);
    assert_eq!(nested, 2);
    assert_eq!(
        result.value.map(f32::to_bits),
        no_tt.value.map(f32::to_bits)
    );
    assert_eq!(Key::of(&root), before);
}

#[test]
fn tt351_zobrist_every_represented_field_and_capacity_error() {
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let base = Key::of(&root);
    let mutations: [fn(&mut Key); 11] = [
        |k| k.pawns[0] += 1,
        |k| k.pawns[1] -= 1,
        |k| k.walls[0] -= 1,
        |k| k.walls[1] -= 1,
        |k| k.horizontal ^= 1,
        |k| k.vertical ^= 1,
        |k| k.turn ^= 1,
        |k| k.winner = Some(0),
        |k| k.ply += 1,
        |k| k.synthetic = true,
        |k| k.history[0].5 += 1,
    ];
    for mutation in mutations {
        let mut k = base.clone();
        mutation(&mut k);
        // Encoding-only raw Key mutations, not admitted legal contexts.
        assert_eq!(full_hash(&k), full_oracle(&k));
        assert_ne!(full_hash(&k), full_hash(&base)); // finite fixture, not collision proof
    }
    for index in 0..8 {
        let mut k = base.clone();
        match index {
            0 => k.history[0].0[0] += 1,
            1 => k.history[0].0[1] -= 1,
            2 => k.history[0].1[0] -= 1,
            3 => k.history[0].1[1] -= 1,
            4 => k.history[0].2 ^= 1,
            5 => k.history[0].3 ^= 1,
            6 => k.history[0].4 ^= 1,
            7 => k.history[0].5 += 1,
            _ => unreachable!(),
        }
        assert_eq!(full_hash(&k), full_oracle(&k));
        assert_ne!(full_hash(&k), full_hash(&base));
    }
    let mut z = ZScratch::new(&root, 0).unwrap();
    // Constrain this private fixture explicitly; never relabel as teacher cap.
    z.key.history.shrink_to_fit();
    if z.key.history.capacity() == z.key.history.len() {
        let before = z.key.clone();
        assert_eq!(z.make(root.legal_ids()[0]).err(), Some("scratch capacity"));
        z.verify();
        assert_eq!(z.key, before);
    }
}

#[test]
fn tt351_nested_failed_undo_preserves_all_stage_facts_and_partial_state() {
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let mut z = ZScratch::new(&root, 4).unwrap();
    let before = Key::of(&root);
    let error = z
        .with_child(13, |outer| {
            outer.with_child(75, |inner| {
                // Deliberate test-local corruption, no canonical token forgery.
                // Inner undo refuses arrival missing; outer undo then refuses
                // owner/LIFO because the canonical cursor is still at depth2.
                let arrival = HistoryKey::from(inner.cursor.position());
                let i = inner
                    .key
                    .history
                    .binary_search_by_key(&arrival, record_key)
                    .unwrap();
                inner.key.history.remove(i);
                Err::<(), _>(BranchError::primary("returned work error"))
            })
        })
        .unwrap_err();
    assert_eq!(error.primary, "returned work error");
    assert_eq!(
        error.restorations,
        vec![
            RestorationFailure {
                stage: "unmake",
                requested_parent_depth: 1,
                observed_depth: 2,
                cause: "arrival missing"
            },
            RestorationFailure {
                stage: "unmake",
                requested_parent_depth: 0,
                observed_depth: 2,
                cause: "owner/LIFO"
            },
        ]
    );
    assert_eq!(z.depth, 2);
    assert_eq!(z.cursor.total_ply(), root.total_ply() + 2);
    assert_ne!(Key::of(&z.cursor), before);
    assert_ne!(z.key, Key::of(&z.cursor));
    // Partial state is explicitly NOT restored/verified. Drop only this owned
    // private fixture; the original immutable root must remain untouched.
    drop(z);
    assert_eq!(Key::of(&root), before);
}

//! Opt-in native research clock. Fixed stack, no allocation by span bookkeeping.
//! Inclusive spans overlap; only exclusive_ns may be added across categories.
use std::cell::RefCell;
use std::marker::PhantomData;
use std::rc::Rc;
use std::time::Instant;

pub const COUNT: usize = 8;
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(usize)]
pub enum Kind {
    Search,
    Validation,
    Expand,
    Legal,
    Distance,
    Evaluate,
    Transition,
    Select,
}
pub const NAMES: [&str; COUNT] = [
    "search",
    "validation",
    "expand",
    "legal",
    "distance",
    "evaluate",
    "transition",
    "select",
];
#[derive(Clone, Copy, Default, Debug)]
pub struct Metric {
    pub calls: u64,
    pub inclusive_ns: u128,
    pub exclusive_ns: u128,
}
#[derive(Clone, Debug)]
pub struct Snapshot {
    pub metrics: [[Metric; COUNT]; COUNT],
    /// Same exclusive accounting, restricted to spans inside an Expand ancestor.
    pub metrics_in_expand: [[Metric; COUNT]; COUNT],
    pub depth_cap_hits: u64,
    pub node_cap_hits: u64,
    pub arena_cap_hits: u64,
}
#[derive(Clone, Copy)]
struct Frame {
    kind: Kind,
    child_ns: u128,
    in_expand: bool,
}
struct State {
    active: bool,
    distance_clock: bool,
    frames: [Frame; 32],
    depth: usize,
    result: Snapshot,
}
impl State {
    const fn new() -> Self {
        Self {
            active: false,
            distance_clock: true,
            frames: [Frame {
                kind: Kind::Search,
                child_ns: 0,
                in_expand: false,
            }; 32],
            depth: 0,
            result: Snapshot {
                metrics: [[Metric {
                    calls: 0,
                    inclusive_ns: 0,
                    exclusive_ns: 0,
                }; COUNT]; COUNT],
                metrics_in_expand: [[Metric {
                    calls: 0,
                    inclusive_ns: 0,
                    exclusive_ns: 0,
                }; COUNT]; COUNT],
                depth_cap_hits: 0,
                node_cap_hits: 0,
                arena_cap_hits: 0,
            },
        }
    }
}
thread_local! { static STATE: RefCell<State> = const { RefCell::new(State::new()) }; }
/// Start an independent sample. Coarse times the Legal/BFS union directly:
/// Distance nested directly inside Legal has no timer/counter; other Distance spans are timed.
/// Use the separate full run for BFS call counts, never infer omitted counts as zero.
pub fn reset(coarse: bool) {
    STATE.with(|s| {
        let mut s = s.borrow_mut();
        assert_eq!(s.depth, 0);
        *s = State::new();
        s.active = true;
        s.distance_clock = !coarse;
    });
}
pub fn snapshot() -> Snapshot {
    STATE.with(|s| {
        let mut s = s.borrow_mut();
        assert_eq!(s.depth, 0);
        s.active = false;
        s.result.clone()
    })
}
pub struct Span {
    start: Option<Instant>,
    kind: Kind,
    parent: Kind,
    in_expand: bool,
    _thread: PhantomData<Rc<()>>,
}
pub fn span(kind: Kind) -> Span {
    STATE.with(|state| {
        let mut s = state.borrow_mut();
        let parent = if s.depth == 0 {
            Kind::Search
        } else {
            s.frames[s.depth - 1].kind
        };
        let in_expand = kind == Kind::Expand || (s.depth > 0 && s.frames[s.depth - 1].in_expand);
        if !s.active {
            return Span {
                start: None,
                kind,
                parent,
                in_expand,
                _thread: PhantomData,
            };
        }
        if kind == Kind::Distance && !s.distance_clock && parent == Kind::Legal {
            return Span {
                start: None,
                kind,
                parent,
                in_expand,
                _thread: PhantomData,
            };
        }
        s.result.metrics[kind as usize][parent as usize].calls += 1;
        if in_expand {
            s.result.metrics_in_expand[kind as usize][parent as usize].calls += 1;
        }
        assert!(s.depth < s.frames.len(), "profiling stack overflow");
        let depth = s.depth;
        s.frames[depth] = Frame {
            kind,
            child_ns: 0,
            in_expand,
        };
        s.depth += 1;
        Span {
            start: Some(Instant::now()),
            kind,
            parent,
            in_expand,
            _thread: PhantomData,
        }
    })
}
impl Drop for Span {
    fn drop(&mut self) {
        if let Some(start) = self.start {
            let elapsed = start.elapsed().as_nanos();
            STATE.with(|state| {
                let mut s = state.borrow_mut();
                s.depth -= 1;
                let frame = s.frames[s.depth];
                assert_eq!(frame.kind, self.kind);
                let m = &mut s.result.metrics[self.kind as usize][self.parent as usize];
                m.inclusive_ns += elapsed;
                m.exclusive_ns += elapsed
                    .checked_sub(frame.child_ns)
                    .expect("nested times bounded by parent");
                if self.in_expand {
                    let m =
                        &mut s.result.metrics_in_expand[self.kind as usize][self.parent as usize];
                    m.inclusive_ns += elapsed;
                    m.exclusive_ns += elapsed
                        .checked_sub(frame.child_ns)
                        .expect("nested times bounded by parent");
                }
                if s.depth > 0 {
                    let i = s.depth - 1;
                    s.frames[i].child_ns += elapsed;
                }
            });
        }
    }
}
pub fn depth_cap_hit() {
    STATE.with(|s| {
        let mut s = s.borrow_mut();
        if s.active {
            s.result.depth_cap_hits += 1;
        }
    });
}
pub fn node_cap_hit() {
    STATE.with(|s| {
        let mut s = s.borrow_mut();
        if s.active {
            s.result.node_cap_hits += 1;
        }
    });
}
pub fn arena_cap_hit() {
    STATE.with(|s| {
        let mut s = s.borrow_mut();
        if s.active {
            s.result.arena_cap_hits += 1;
        }
    });
}

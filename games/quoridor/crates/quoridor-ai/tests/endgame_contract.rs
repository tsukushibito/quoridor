#![cfg(feature = "endgame")]
//! Independent finite graph oracle definitions; not a second Quoridor engine.
//! No production solver comparison or runtime qualification has happened yet.
use quoridor_ai::endgame::Wdl;

struct Fact {
    goal: Option<Wdl>,
    /// Frozen legal adjacency, independently supplied rather than generated here.
    children: &'static [usize],
}

fn oracle(facts: &[Fact], at: usize, counts: &mut [u8], fuel: usize) -> Option<Wdl> {
    // Precedence is an independent formula over facts, not pawn move code.
    if let Some(goal) = facts[at].goal {
        return Some(goal);
    }
    if counts[at] == 3 {
        return Some(Wdl::Draw);
    }
    if fuel == 0 || facts[at].children.is_empty() {
        return None;
    }
    let values: Vec<_> = facts[at]
        .children
        .iter()
        .map(|&child| {
            counts[child] += 1;
            let value = oracle(facts, child, counts, fuel - 1);
            counts[child] -= 1;
            value
        })
        .collect();
    if values.contains(&Some(Wdl::Loss)) {
        Some(Wdl::Win)
    } else if values.iter().any(Option::is_none) {
        None
    } else if values.contains(&Some(Wdl::Draw)) {
        Some(Wdl::Draw)
    } else {
        Some(Wdl::Loss)
    }
}

#[test]
fn independent_child_proof_formula_requires_complete_loss_and_draw() {
    let variants = [Some(Wdl::Win), Some(Wdl::Draw), Some(Wdl::Loss), None];
    for left in variants {
        for right in variants {
            let facts = [
                Fact {
                    goal: None,
                    children: &[1, 2],
                },
                Fact {
                    goal: left,
                    children: &[],
                },
                Fact {
                    goal: right,
                    children: &[],
                },
            ];
            let actual = oracle(&facts, 0, &mut [1, 0, 0], 1);
            // Separate finite expected relation, not production kernel reduction.
            let expected = match (left, right) {
                (Some(Wdl::Loss), _) | (_, Some(Wdl::Loss)) => Some(Wdl::Win),
                (None, _) | (_, None) => None,
                (Some(Wdl::Win), Some(Wdl::Win)) => Some(Wdl::Loss),
                _ => Some(Wdl::Draw),
            };
            assert_eq!(actual, expected, "children {left:?}, {right:?}");
        }
    }
}

#[test]
fn forced_cycle_counts_nonconsecutive_entries_and_never_adds_root_twice() {
    let facts = [
        Fact {
            goal: None,
            children: &[1],
        },
        Fact {
            goal: None,
            children: &[0],
        },
    ];
    let mut history = [1, 0];
    assert_eq!(oracle(&facts, 0, &mut history, 3), None);
    assert_eq!(history, [1, 0]);
    assert_eq!(oracle(&facts, 0, &mut history, 4), Some(Wdl::Draw));
    assert_eq!(history, [1, 0]);
    // Current root's second occurrence is not terminal; the next return is third.
    assert_eq!(oracle(&facts, 0, &mut [2, 1], 0), None);
    assert_eq!(oracle(&facts, 0, &mut [2, 1], 2), Some(Wdl::Draw));
    assert_eq!(oracle(&facts, 0, &mut [3, 2], 0), Some(Wdl::Draw));
}

#[test]
fn identical_board_different_history_can_change_exact_value() {
    let facts = [
        Fact {
            goal: None,
            children: &[1],
        },
        Fact {
            goal: None,
            children: &[2],
        },
        Fact {
            goal: Some(Wdl::Loss),
            children: &[],
        },
    ];
    assert_eq!(oracle(&facts, 0, &mut [1, 0, 0], 2), Some(Wdl::Loss));
    assert_eq!(oracle(&facts, 0, &mut [1, 2, 0], 2), Some(Wdl::Draw));
}

#[test]
fn goal_has_priority_over_third_entry_and_operational_fuel() {
    let facts = [Fact {
        goal: Some(Wdl::Loss),
        children: &[],
    }];
    assert_eq!(oracle(&facts, 0, &mut [3], 0), Some(Wdl::Loss));
}

#[test]
fn draw_option_cannot_hide_a_win_or_an_unresolved_option() {
    let facts = [
        Fact {
            goal: None,
            children: &[1, 2],
        },
        Fact {
            goal: None,
            children: &[0],
        },
        Fact {
            goal: Some(Wdl::Loss),
            children: &[],
        },
    ];
    assert_eq!(oracle(&facts, 0, &mut [1, 2, 0], 1), Some(Wdl::Win));
    let unresolved = [
        Fact {
            goal: None,
            children: &[1, 2],
        },
        Fact {
            goal: None,
            children: &[0],
        },
        Fact {
            goal: None,
            children: &[],
        },
    ];
    assert_eq!(oracle(&unresolved, 0, &mut [1, 2, 0], 1), None);
}

//! Diagnostic tree inspection. Nodes retain their normal layout; context follows paths.
use super::*;
#[derive(Debug, Clone)]
pub struct NodeSnapshot {
    pub index: usize,
    pub context: SigmaContext,
    pub expanded: bool,
    pub edges: Vec<(u16, f32, u32, f32)>,
    pub children: Vec<Option<usize>>,
    pub visits: u32,
}
impl<E: Evaluator> SearchSession<E> {
    pub fn research_tree_snapshot(&self) -> Vec<NodeSnapshot> {
        let mut output = Vec::new();
        let Some(root) = self.research_context.clone() else {
            return output;
        };
        let mut pending = vec![(0, root)];
        while let Some((index, context)) = pending.pop() {
            let n = &self.nodes[index];
            assert_eq!(n.position, context.position());
            let legal = context.legal_ids();
            if context.terminal_value().is_some() {
                assert!(n.edges.is_empty());
            } else if n.expanded {
                assert_eq!(n.edges.iter().map(|e| e.action).collect::<Vec<_>>(), legal);
            }
            for edge in &n.edges {
                assert!(legal.contains(&edge.action));
                if let Some(child) = edge.child {
                    pending.push((child, context.play(edge.action).unwrap()));
                }
            }
            output.push(NodeSnapshot {
                index,
                context,
                expanded: n.expanded,
                edges: n
                    .edges
                    .iter()
                    .map(|e| (e.action, e.prior, e.visits, e.value_sum))
                    .collect(),
                children: n.edges.iter().map(|e| e.child).collect(),
                visits: n.visits,
            });
        }
        output.sort_by_key(|n| n.index);
        output
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use quoridor_core::research::{HistoryKey, SigmaContext};
    use std::{cell::RefCell, rc::Rc};
    type Calls = Rc<RefCell<Vec<(Position, Vec<u16>)>>>;
    struct Spy {
        calls: Calls,
        preferred: Vec<(Position, u16)>,
        value: f32,
    }
    impl Evaluator for Spy {
        fn evaluate(&self, p: Position, legal: &[u16]) -> Evaluation {
            self.calls.borrow_mut().push((p, legal.to_vec()));
            let target = self
                .preferred
                .iter()
                .find(|(q, _)| *q == p)
                .map(|(_, a)| *a);
            Evaluation {
                weights: legal
                    .iter()
                    .map(|id| {
                        if target.is_none_or(|a| a == *id) {
                            1.
                        } else {
                            0.
                        }
                    })
                    .collect(),
                value: self.value,
            }
        }
    }
    fn limits(nodes: u32, depth: u8) -> SearchLimits {
        SearchLimits {
            simulations: 64,
            max_nodes: nodes,
            max_depth: depth,
        }
    }
    fn spy(preferred: Vec<(Position, u16)>, value: f32) -> (Spy, Calls) {
        let calls = Rc::new(RefCell::new(Vec::new()));
        (
            Spy {
                calls: calls.clone(),
                preferred,
                value,
            },
            calls,
        )
    }
    fn synthetic(p: Position, ply: u16) -> SigmaContext {
        SigmaContext::synthetic_diagnostic(p, ply, vec![(p.into(), 1)]).unwrap()
    }
    #[test]
    fn deep_overlay_excludes_third_return_and_siblings_restore_base() {
        let cycle = [13, 67, 4, 76];
        let root = SigmaContext::from_prefix(&[]).unwrap();
        let mut c = root.clone();
        let mut preferred = Vec::new();
        for &a in &cycle {
            preferred.push((c.position(), a));
            c = c.play(a).unwrap();
        }
        assert_eq!(c.position(), root.position());
        assert_eq!(c.count(root.position().into()), 2);
        let (eval, calls) = spy(preferred, 0.);
        let mut s = SearchSession::new_sigma(root.clone(), limits(128, 12), 1979, eval).unwrap();
        while !s.done() {
            s.step(4);
        }
        let nodes = s.research_tree_snapshot();
        let deep = nodes
            .iter()
            .find(|n| n.context.total_ply() == 7 && n.context.position().pawns == [4, 67])
            .expect("deep path reached");
        assert!(deep.expanded);
        assert!(!deep.context.legal_ids().contains(&76));
        assert!(!deep.edges.iter().any(|e| e.0 == 76));
        assert!(
            calls
                .borrow()
                .iter()
                .any(|(p, l)| p.pawns == [4, 67] && p.turn == 1 && !l.contains(&76))
        );
        assert_eq!(
            s.research_context.as_ref().unwrap().history_counts(),
            root.history_counts()
        );
        let a = root.play(13).unwrap();
        let b = root.play(81).unwrap();
        assert_eq!(b.count(a.position().into()), 0);
        assert_eq!(a.count(b.position().into()), 0);
        assert_eq!(root.count(root.position().into()), 1);
        let (eval, _) = spy(vec![], 0.);
        let mut siblings =
            SearchSession::new_sigma(root.clone(), limits(128, 4), 1979, eval).unwrap();
        siblings.step(32);
        let snapshot = siblings.research_tree_snapshot();
        assert!(
            snapshot
                .iter()
                .filter(|n| n.context.total_ply() == 1)
                .count()
                > 1
        );
        for n in &snapshot {
            assert_eq!(
                n.context
                    .history_counts()
                    .iter()
                    .map(|(_, n)| u32::from(*n))
                    .sum::<u32>(),
                u32::from(n.context.total_ply()) + 1
            );
        }
        assert_eq!(
            siblings.research_context.as_ref().unwrap().history_counts(),
            root.history_counts()
        );
        println!(
            "deep context nodes={} ply7 forbidden76; sibling nodes={} root/base unchanged",
            nodes.len(),
            snapshot.len()
        );
    }
    #[test]
    fn normal_input_rejects_root_double_count_synthetic_and_inconsistent_ply() {
        let p = Position::default();
        assert!(SigmaContext::from_counts(p, 0, vec![(p.into(), 2)]).is_err());
        assert!(SigmaContext::from_counts(p, 1, vec![(p.into(), 1)]).is_err());
        let c = synthetic(p, 198);
        let (eval, _) = spy(vec![], 0.);
        assert!(SearchSession::new_sigma(c, limits(8, 2), 1979, eval).is_err());
        let c = SigmaContext::from_prefix(&[13, 67, 4, 76, 13, 67, 4]);
        assert!(c.unwrap().play(76).is_err());
        assert!(HistoryKey::parse("4,0|4,8|0|1,2;1,2|").is_err());
    }
    #[test]
    fn ply200_goal_and_no_legal_draw_precede_caps_without_evaluation() {
        let p = Position {
            pawns: [4, 13],
            turn: 1,
            ..Position::default()
        };
        p.checked().unwrap();
        for (nodes, depth, arena) in [(1, 8, false), (16, 1, false), (16, 8, true)] {
            let root = synthetic(p, 199);
            let (eval, calls) = spy(vec![(p, 3)], 0.25);
            let mut s = SearchSession::new_sigma_diagnostic(root, limits(nodes, depth), 1979, eval)
                .unwrap();
            let cursor = s.root_cursor();
            s.expand(0, &cursor);
            calls.borrow_mut().clear();
            if arena {
                s.stats.arena_bytes = MAX_ARENA_BYTES;
            }
            s.simulate();
            assert_eq!(calls.borrow().len(), 0);
            let edge = s.nodes[0].edges.iter().find(|e| e.action == 3).unwrap();
            assert_eq!(edge.visits, 1);
            assert_eq!(edge.value_sum, 1.);
            if let Some(child) = edge.child {
                assert!(s.nodes[child].edges.is_empty());
            }
        }
        let goal = synthetic(p, 199).play(3).unwrap();
        assert_eq!(goal.total_ply(), 200);
        assert_eq!(goal.terminal_value(), Some(-1.));
        for context in [goal, synthetic(Position::default(), 200)] {
            let (eval, calls) = spy(vec![], 0.25);
            let mut s =
                SearchSession::new_sigma_diagnostic(context, limits(1, 1), 1979, eval).unwrap();
            assert!(s.done());
            s.step(4);
            assert_eq!(s.finish().action, None);
            assert_eq!(calls.borrow().len(), 0);
            assert_eq!(s.stats.edges, 0);
        }
        let mut c = synthetic(Position::default(), 198);
        c = c.play(13).unwrap();
        assert_eq!(c.total_ply(), 199);
        assert!(c.terminal_value().is_none());
        c = c.play(67).unwrap();
        assert_eq!(c.total_ply(), 200);
        assert_eq!(c.terminal_value(), Some(0.));
        let walls = [
            206, 181, 90, 129, 177, 191, 88, 167, 176, 82, 106, 95, 119, 132, 186, 190, 135, 164,
            205, 160,
        ];
        let c = SigmaContext::from_prefix(&walls).unwrap();
        let mut h = c.history_counts();
        for a in c.legal_ids() {
            h.push((c.play(a).unwrap().position().into(), 2));
        }
        let c = SigmaContext::synthetic_diagnostic(c.position(), 20, h).unwrap();
        assert!(c.raw_legal_ids().is_empty());
        let (eval, calls) = spy(vec![], 0.25);
        let mut s = SearchSession::new_sigma_diagnostic(c, limits(1, 1), 1979, eval).unwrap();
        assert!(s.done());
        assert_eq!(s.finish().action, None);
        assert!(calls.borrow().is_empty());
        assert_eq!(s.stats.edges, 0);
        println!(
            "terminal priority: goal at200/node/depth/arena; ply198→199→200; artificial no-legal draw; terminal evaluate calls0"
        );
    }
    #[test]
    fn cap_fallback_receives_context_mask_and_pawn_wall_backup_signs_match() {
        for (a, b) in [(13, 67), (81, 67), (13, 81), (81, 83)] {
            let root = SigmaContext::from_prefix(&[]).unwrap();
            let child = root.play(a).unwrap();
            let (eval, calls) = spy(vec![(root.position(), a), (child.position(), b)], 0.25);
            let mut s = SearchSession::new_sigma(root.clone(), limits(32, 4), 1979, eval).unwrap();
            s.step(2);
            let e = s.nodes[0].edges.iter().find(|e| e.action == a).unwrap();
            assert_eq!(e.value_sum, -0.25);
            s.step(1);
            let e = s.nodes[0].edges.iter().find(|e| e.action == a).unwrap();
            assert_eq!(e.value_sum, 0.);
            let ci = e.child.unwrap();
            let ce = s.nodes[ci].edges.iter().find(|e| e.action == b).unwrap();
            assert_eq!(ce.value_sum, -0.25);
            assert!(calls.borrow().iter().all(|(_, l)| !l.is_empty()));
        }
        let c = SigmaContext::from_prefix(&[13, 67, 4, 76, 13, 67, 4]).unwrap();
        let (eval, calls) = spy(vec![], 0.25);
        let mut s = SearchSession::new_sigma(c.clone(), limits(1, 1), 1979, eval).unwrap();
        let cursor = s.root_cursor();
        s.safe_value(c.position(), &cursor);
        assert_eq!(calls.borrow()[0].1, c.legal_ids());
        assert!(!calls.borrow()[0].1.contains(&76));
        for cap in ["node", "depth", "arena"] {
            let root = SigmaContext::from_prefix(&[]).unwrap();
            let (eval, calls) = spy(vec![(root.position(), 13)], 0.25);
            let mut s = SearchSession::new_sigma(
                root,
                limits(
                    if cap == "node" { 1 } else { 8 },
                    if cap == "depth" { 1 } else { 8 },
                ),
                1979,
                eval,
            )
            .unwrap();
            let cur = s.root_cursor();
            s.expand(0, &cur);
            if cap == "arena" {
                s.stats.arena_bytes = MAX_ARENA_BYTES;
            }
            calls.borrow_mut().clear();
            s.simulate();
            assert_eq!(calls.borrow().len(), 1);
            assert!(!calls.borrow()[0].1.is_empty());
            assert_eq!(
                s.nodes[0]
                    .edges
                    .iter()
                    .find(|e| e.action == 13)
                    .unwrap()
                    .value_sum,
                -0.25
            );
        }
        println!(
            "pawn/pawn, wall/pawn, pawn/wall, wall/wall1/2ply signs; node/depth/arena fallback context mask"
        );
    }
}

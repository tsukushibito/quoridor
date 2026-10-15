use super::*;

fn settings() -> (Settings, Vec<Request>) {
    let config = json!({"loss_leaf_419":true,"roots":IDS.iter().enumerate().map(|(i,id)|json!({
        "input":0,"pointer":format!("/parents/{i}"),"field":"from_prefix_actions","label":id})).collect::<Vec<_>>(),
        "profile":"control","tt_entries":1048576,"use_tt":true,"use_pvs":true,"lmr":false,
        "namespace":{"evaluator":EVALUATOR,"rules":"research-standard-2p-threefold-goal-first-v1","selectivity":"toy"},
        "output_bytes":100000,"record_bytes":10000});
    let requests = (0..12)
        .map(|i| {
            let depth = 2 + (i % 4) / 2;
            let id = format!("{}:{}:H{depth}:normal", IDS[i / 4], ["N", "D"][i % 2]);
            Request {
                session: id.clone(),
                id,
                root: i / 4,
                depth: depth as u16,
                node_cap: CALL_NODES,
                time_limit_ms: None,
                diagnostic: false,
                warmup: false,
                observe_completed_depths: false,
                observe_lmr: false,
            }
        })
        .collect();
    (serde_json::from_value(config).unwrap(), requests)
}

#[test]
fn loss419_protocol_and_chronology_reject_count_only_substitution() {
    let (mut config, mut requests) = settings();
    assert!(validate(&config, &requests).is_ok());
    config.lmr = true;
    assert!(validate(&config, &requests).is_err());
    config.lmr = false;
    requests[0].observe_lmr = true;
    assert!(validate(&config, &requests).is_err());
    let mut value = serde_json::to_value(config).unwrap();
    value["loss_leaf_419"] = Value::Null;
    assert!(serde_json::from_value::<Settings>(value.clone()).is_err());
    value.as_object_mut().unwrap().remove("loss_leaf_419");
    assert!(
        !serde_json::from_value::<Settings>(value)
            .unwrap()
            .loss_leaf_419
    );
    let prefix = [13, 67, 4, 76];
    let root = SigmaContext::from_prefix(&prefix).unwrap();
    let mut expected = json!({"from_prefix_actions":prefix,"rules":"research-standard-2p-threefold-goal-first-v1",
        "expected_native_history_key_from_maintained_rules_view":"4,0|4,8|0|||10,10",
        "expected_ordered_history_keys":["4,0|4,8|0|||10,10","4,1|4,8|1|||10,10",
            "4,1|4,7|0|||10,10","4,0|4,7|1|||10,10","4,0|4,8|0|||10,10"],
        "expected_history_multiset_for_comparison_only":[["4,0|4,8|0|||10,10",2],
            ["4,1|4,8|1|||10,10",1],["4,1|4,7|0|||10,10",1],["4,0|4,7|1|||10,10",1]],
        "expected_current_repetition_count":2,
        "expected_maintained_rules_view":{"pawns":[4,76],"wallsRemaining":[10,10],
            "turn":0,"horizontalWalls":[],"verticalWalls":[],"winner":null,"ply":4}});
    assert!(input_check(&prefix, &expected, &root).is_ok());
    let selector = RootInput {
        input: 0,
        jsonl_match: None,
        pointer: String::new(),
        field: "from_prefix_actions".into(),
        prefix_len: None,
        check_history: false,
        label: "toy".into(),
    };
    assert!(
        root_spec(&expected, &selector, false)
            .unwrap()
            .expected
            .is_none()
    );
    assert!(
        root_spec(&expected, &selector, true)
            .unwrap()
            .expected
            .is_some()
    );
    expected["expected_ordered_history_keys"]
        .as_array_mut()
        .unwrap()
        .remove(1);
    assert!(input_check(&prefix, &expected, &root).is_err());
}

#[test]
fn loss419_union_missing_anchor_and_all_stage_admission_are_bounded() {
    assert_eq!(candidate_union(156, [Some(156), Some(192)]), [156, 192]);
    assert_eq!(candidate_union(156, [None, Some(104)]), [104, 156]);
    assert_eq!(candidate_union(156, [None, None]), [156]);
    let mut count = Census::default();
    for _ in 0..24 {
        count.admit_search(true).unwrap();
    }
    assert!(count.admit_search(true).is_err());
    for _ in 0..24 {
        count.admit_search(false).unwrap();
    }
    assert!(count.admit_search(false).is_err());
    assert_eq!(count.search_calls_entered, 0);
    assert_eq!(
        count.nnue_logical_charge_including_unknown_reservations,
        24_000_000
    );
    count.nnue_logical_charge_including_unknown_reservations = LOGICAL_NN_LIMIT;
    assert!(count.charge_head(false).is_err());
    assert!(count.charge_head(true).is_err());
}

fn node(parent: Option<usize>, action: Option<u16>, ply: u8, children: Vec<usize>) -> Node {
    Node {
        parent,
        action,
        ply,
        terminal: None,
        terminal_kind: None,
        legal_children: children.len(),
        planned_children: children.len(),
        children,
        leaf: None,
        expansion_error: None,
        backup_bits: [[None; 2]; 2],
    }
}
fn leaf(parent: usize, action: u16, n: f32, d: f32) -> Node {
    let mut result = node(Some(parent), Some(action), 2, vec![]);
    result.leaf = Some(Leaf {
        baseline_bits: 0,
        residual_bits: n.to_bits(),
        pre_tanh_bits: n.to_bits(),
        nnue_post_bits: n.to_bits(),
        distance_post_bits: d.to_bits(),
        scaled_distance_bits: [0; 2],
    });
    result
}

#[test]
fn loss419_complete_frontier_signed_zero_and_partial_ancestor_semantics() {
    let mut tree = Tree {
        nodes: vec![
            node(None, None, 0, vec![1, 2]),
            node(Some(0), Some(10), 1, vec![3]),
            node(Some(0), Some(20), 1, vec![4]),
            leaf(1, 30, 0., 0.),
            leaf(2, 40, -0., -0.),
        ],
    };
    tree.nodes[3].planned_children = 2;
    tree.nodes[3].expansion_error = Some("partial H3".into());
    let h2 = backup(&tree, 2, 0, &BTreeMap::new());
    assert_eq!(h2[0].unwrap().to_bits(), 0_f32.to_bits());
    assert_eq!(ties(&tree, &h2, 0), [10, 20]);
    assert!(backup(&tree, 3, 0, &BTreeMap::new())[0].is_none());
    tree.nodes[2].children.clear();
    assert!(backup(&tree, 2, 0, &BTreeMap::new())[0].is_none());
    tree.nodes[1].terminal = Some(2.);
    tree.nodes[2].terminal = Some(-2.);
    let terminal = backup(&tree, 3, 0, &BTreeMap::new());
    assert_eq!(terminal[0], Some(2.));
    assert_eq!(ties(&tree, &terminal, 0), [20]);
}

#[test]
fn loss419_saved_intervention_switches_response_without_fixed_pv() {
    let mut tree = Tree {
        nodes: vec![
            node(None, None, 0, vec![1, 2]),
            node(Some(0), Some(10), 1, vec![3, 4]),
            node(Some(0), Some(20), 1, vec![5, 6]),
            leaf(1, 100, 0.8, 0.95),
            leaf(1, 101, 0.9, -0.5),
            leaf(2, 110, 0.6, 0.5),
            leaf(2, 111, 0.7, 0.6),
        ],
    };
    let original = backup(&tree, 2, 0, &BTreeMap::new());
    assert_eq!(path(&tree, &original, 2, 10).unwrap().0, [10, 100]);
    let mut count = Census::default();
    let (records, tracked) = saved_comparisons(&mut tree, &mut count).unwrap();
    assert_eq!(records[0]["N"]["canonical_action"], 10);
    assert_eq!(records[0]["D"]["canonical_action"], 20);
    let changed = records[0]["interventions"]
        .as_array()
        .unwrap()
        .iter()
        .find(|row| {
            row["replaced"].as_array().unwrap().len() == 1 && row["replaced"][0]["node"] == 3
        })
        .unwrap();
    assert_eq!(changed["PV"], json!([10, 101]));
    assert_eq!(changed["ranking"]["canonical_action"], 10);
    assert_eq!(count.saved_interventions, 4);
    assert_eq!(count.diagnostic_head_calls_started, 0);
    assert!(tracked.contains(&vec![10, 100]) && tracked.contains(&vec![10, 101]));
}

#[test]
fn loss419_toy_parity_uses_only_selected_states_and_restores_parent() {
    let t = quoridor_nnue::Topology {
        ft_width: 1,
        hidden_width: 1,
    };
    let model = ResidualModel::from_parts(
        t,
        vec![0.; ResidualModel::parameter_count(t).unwrap()],
        [0.; 2],
        [1.; 2],
        quoridor_nnue::DistanceFit { a: 0., b: 0. },
        quoridor_nnue::residual::RouteMode::Zero4,
        [0.; 4],
        [1.; 4],
    )
    .unwrap();
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let before = identity(&root);
    let mut count = Census::default();
    let rows = parity(
        &root,
        &BTreeSet::from([vec![], vec![13]]),
        &model,
        &mut count,
        &AtomicBool::new(false),
    )
    .unwrap();
    assert_eq!(rows.len(), 2);
    assert_eq!(count.parity_states, 2);
    assert_eq!(count.parity_nnue_logical_evaluations, 5);
    assert_eq!(count.diagnostic_full_contexts_started, 3);
    assert_eq!(count.diagnostic_delta_contexts_started, 1);
    assert_eq!(rows[1]["parent_exact"], true);
    assert_eq!(rows[1]["detail"]["features_exact"], true);
    assert_eq!(rows[1]["detail"]["FT_alert"], false);
    assert_eq!(rows[1]["detail"]["value_alert"], false);
    assert_eq!(identity(&root), before);
}

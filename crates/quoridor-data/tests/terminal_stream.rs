//! New intake fixtures only. Search values/counters are explicitly synthetic ports.
use quoridor_core::research::{HistoryKey, Ruleset, SigmaContext};
use quoridor_data::{
    Teacher, TeacherRow, file_sha,
    terminal::{
        TerminalProvenance, Termination, attach_terminal_targets, partition_families,
        reflect_action,
    },
    terminal_stream::{BoundJson, IntakeBinding, STREAM_SCHEMA, write_cache},
};
use serde_json::{Value, json};
use std::{
    fs,
    path::{Path, PathBuf},
    sync::atomic::{AtomicUsize, Ordering},
};
static SERIAL: AtomicUsize = AtomicUsize::new(0);
struct Fixture {
    root: PathBuf,
    binding: IntakeBinding,
    events: Vec<Value>,
}
impl Drop for Fixture {
    fn drop(&mut self) {
        fs::remove_dir_all(&self.root).unwrap();
    }
}
fn context(c: &SigmaContext) -> Value {
    let p = c.position();
    json!({"ruleset":c.ruleset().id(),"pawns":p.pawns,"horizontal":p.horizontal,
        "vertical":p.vertical,"stocks":p.walls_remaining,"stm":p.turn,"ply":c.total_ply(),
        "state_key":HistoryKey::from(p).history_string(),
        "history":c.history_counts().into_iter().map(|(k,n)|(k.history_string(),n)).collect::<Vec<_>>()})
}
fn control(path: &Path, value: &Value) -> BoundJson {
    fs::write(path, serde_json::to_vec(value).unwrap()).unwrap();
    BoundJson {
        path: path.into(),
        sha256: file_sha(path).unwrap(),
    }
}
impl Fixture {
    fn new(unknown: bool) -> Self {
        Self::with_case(unknown, false)
    }
    fn with_case(unknown: bool, goal: bool) -> Self {
        let root = PathBuf::from(std::env::var_os("TMPDIR").unwrap_or_else(|| "/tmp".into())).join(
            format!(
                "terminal-stream-synthetic-{}-{}",
                std::process::id(),
                SERIAL.fetch_add(1, Ordering::Relaxed)
            ),
        );
        fs::create_dir(&root).unwrap();
        let prefix = if goal {
            vec![13, 67, 22, 58, 31, 49, 40, 50, 49, 51, 58, 52, 67, 53]
        } else if unknown {
            vec![13, 75]
        } else {
            vec![13, 75, 14, 76, 13, 75, 14, 76]
        };
        let move_id = if goal {
            76
        } else if unknown {
            14
        } else {
            13
        };
        let c = SigmaContext::from_prefix(&prefix).unwrap();
        let partition =
            partition_families(&[("synthetic-game".into(), prefix.clone())], 20261008).unwrap();
        let assignment = &partition.assignments[0];
        let mut final_c = c.clone();
        final_c.make_move(move_id).unwrap();
        let mut final_prefix = prefix.clone();
        final_prefix.push(move_id);
        let reason = if goal {
            Termination::Goal
        } else if unknown {
            Termination::Unknown
        } else {
            Termination::Threefold
        };
        let detail = if goal {
            "canonical_goal"
        } else if unknown {
            "unaccepted_search:synthetic refused port"
        } else {
            "canonical_legal_third_occurrence"
        };
        let provenance =
            TerminalProvenance::from_context(&final_c, final_prefix.clone(), reason, detail.into())
                .unwrap();
        let row = TeacherRow::from_context(
            "synthetic-row".into(),
            "synthetic-game".into(),
            assignment.family.clone(),
            assignment.split.clone(),
            prefix.clone(),
            &c,
            Some(move_id),
            Teacher::AlphaBeta {
                value: 0.25,
                depth: 3,
                nodes: 1,
                bound: "completed_root".into(),
                pv: vec![move_id],
            },
            "original-distance-a0-b8-tanh".into(),
        )
        .unwrap();
        let mut rows = vec![row];
        attach_terminal_targets(&mut rows, &provenance).unwrap();
        let search = json!({"action":move_id,"raw_value":0.25,"raw_value_bits":0.25f32.to_bits(),
        "completed_depth":3,"pv":[move_id],"stop":"depth_cap","counters":{"nodes":1,"policy_calls":0,"tt_retained_bytes":0},
        "returned_search_wall_ns":0,"parent":context(&c),"accepted":true,"failure":null});
        let failed = if unknown {
            json!({"action":null,"raw_value":null,"raw_value_bits":null,"completed_depth":0,
        "pv":[],"stop":"synthetic_refusal","counters":{"nodes":9},"returned_search_wall_ns":0,
        "parent":context(&final_c),"accepted":false,"failure":"synthetic refused port"})
        } else {
            Value::Null
        };
        let config = json!({"phase":"synthetic_fixture","main_volume_n":null,"ruleset":Ruleset::Standard2pThreefold.config_name(),
        "planned_games":1,"prefix_seed":20261008,"attempts_per_prefix":32,"depth":3,"max_nodes":100000,"tt_slots":4096,
        "use_pvs":true,"solver_order_contact":false,"distance_a":0.0,"distance_b":8.0,"per_move_timeout_ms":null,"max_total_plies":200});
        let config_ref = control(&root.join("config.json"), &config);
        let request = json!({"type":"requests","schema":STREAM_SCHEMA,"generator_version":"synthetic-fixture-v1",
        "config":config,"config_sha256":config_ref.sha256,"planned":1,"requested_lengths":[prefix.len()]});
        let request_line = format!("{}\n", serde_json::to_string(&request).unwrap());
        let request_sha = quoridor_data::hex_digest(request_line.as_bytes());
        let canonical = std::cmp::min(
            prefix.clone(),
            prefix.iter().map(|a| reflect_action(*a).unwrap()).collect(),
        );
        let schedule = json!([{"game":0,"request_id":"synthetic-game","requested_prefix_length":prefix.len(),"prefix":prefix,
        "canonical_prefix":canonical,"root":context(&c),"attempts":[{"attempt":0,"prefix":prefix,"rejection":null}],"scheduled_failure":null}]);
        let sources = json!({"schema":STREAM_SCHEMA,"generator_version":"synthetic-fixture-v1","executable_sha256":"a".repeat(64),
        "compiled_sources":{"synthetic-port-source":"b".repeat(64)},"evaluator":"original-distance-a0-b8-tanh",
        "resource_admission":{"synthetic_fixture":true}});
        let source_ref = control(&root.join("sources.json"), &sources);
        let schedule_ref = control(
            &root.join("schedule.json"),
            &json!({"scheduled":schedule,"family_partition":partition,"requests_sha256":request_sha,
        "opened_pilot_inclusion":"excluded"}),
        );
        let mut header = sources;
        header["config"] = config;
        header["config_sha256"] = json!(config_ref.sha256);
        header["scheduled"] = schedule;
        header["family_partition"] = serde_json::to_value(&partition).unwrap();
        let game = json!({"game":0,"request_id":"synthetic-game","family":assignment.family,"initial_prefix":prefix,
        "final_prefix":final_prefix,"final_context":context(&final_c),"provenance":provenance,
        "termination":if goal{json!({"type":"goal"})}else if unknown{json!({"type":"unknown","reason":detail})}else{json!({"type":"threefold"})},
        "rows":[{"teacher":rows[0],"search":search}],"failed_search":failed,"attempted_search_calls":if unknown{2}else{1},"wall_ns":0});
        let footer = json!({"scheduled":1,"recorded":1,"goals":if goal{1}else{0},"draws":if unknown||goal{0}else{1},"unknown":if unknown{1}else{0},
        "rows":1,"eligible_rows":if unknown{0}else{1},"distinct_positions":1,"duplicate_positions":0,"contact_positions":0,
        "wall_stock_positions":{"10,10":1},"opening_positions":1,"endgame_positions":if goal{1}else{0},"search_nodes":if unknown{10}else{1},
        "search_calls":if unknown{2}else{1},"accepted_search_calls":1,"achieved_depths":{"3":1},
        "planned_prefix_lengths":{prefix.len().to_string():1},"committed_stream_bytes_before_footer":0,"native_whole_ns":0,"full_volume_n":null});
        Self {
            root: root.clone(),
            binding: IntakeBinding {
                schema: "quoridor-terminal-stream-intake-v1".into(),
                scope: "synthetic-fixture".into(),
                human_quantity_n: None,
                stream: BoundJson {
                    path: root.join("stream.jsonl"),
                    sha256: String::new(),
                },
                config: config_ref,
                sources: source_ref,
                schedule: schedule_ref,
                requests_sha256: request_sha,
                max_stream_bytes: 2 * 1024 * 1024,
                max_compressed_bytes: None,
                stream_content: None,
                max_line_bytes: 1024 * 1024,
            },
            events: vec![
                request,
                json!({"type":"header","record":header}),
                json!({"type":"game","record":game}),
                json!({"type":"footer","record":footer}),
            ],
        }
    }
    fn save(&mut self) -> BoundJson {
        if self.events.last().is_some_and(|v| v["type"] == "footer") {
            let bytes = self.events[..self.events.len() - 1]
                .iter()
                .map(|v| serde_json::to_vec(v).unwrap().len() + 1)
                .sum::<usize>();
            self.events.last_mut().unwrap()["record"]["committed_stream_bytes_before_footer"] =
                json!(bytes);
        }
        let mut raw = Vec::new();
        for e in &self.events {
            raw.extend(serde_json::to_vec(e).unwrap());
            raw.push(b'\n');
        }
        fs::write(&self.binding.stream.path, raw).unwrap();
        self.binding.stream.sha256 = file_sha(&self.binding.stream.path).unwrap();
        control(
            &self.root.join("intake.json"),
            &serde_json::to_value(&self.binding).unwrap(),
        )
    }
    fn run(&mut self) -> quoridor_data::Result<TensorCacheAlias> {
        let b = self.save();
        write_cache(
            &self.binding.stream.path,
            &self.root.join("output"),
            &b.path,
            &b.sha256,
        )
    }
    fn refused(&mut self) {
        let e = self.run().unwrap_err();
        assert!(e.source().is_some(), "primary must remain explicit: {e}");
        assert!(!self.root.join("output/cache.json").exists());
        let f: Value = serde_json::from_slice(
            &fs::read(self.root.join("output/intake-failure.json")).unwrap(),
        )
        .unwrap();
        assert_eq!(f["admitted"], false);
        assert!(!f["primary"].as_str().unwrap().is_empty());
    }
}
type TensorCacheAlias = quoridor_data::TensorCache;

#[test]
fn stream_valid_draw_and_unknown_keep_distinct_teachers_and_failed_census() {
    for unknown in [false, true] {
        let mut f = Fixture::new(unknown);
        let c = f.run().unwrap();
        assert_eq!(c.rows, 1);
        let path = f.root.join("output");
        let meta: Value =
            serde_json::from_slice(&fs::read(path.join("cache.json")).unwrap()).unwrap();
        assert_eq!(meta["stream_intake"]["status"], "complete");
        assert!(!path.join(".intake.partial").exists());
        let margin = f32::from_le_bytes(
            fs::read(path.join("terminal-margin.f32"))
                .unwrap()
                .try_into()
                .unwrap(),
        );
        let row: Value =
            serde_json::from_str(&fs::read_to_string(path.join("rows.jsonl")).unwrap()).unwrap();
        if unknown {
            assert!(margin.is_nan());
            assert_eq!(row["primary_eligible"], false);
            assert!(row["z"].is_null());
        } else {
            assert_eq!(margin, 0.0);
            assert_ne!(
                row["terminal_targets"]["terminal_geometric_margin_steps"],
                0
            );
        }
        let games = fs::read_to_string(path.join("stream-games.jsonl")).unwrap();
        assert!(games.contains("attempted_search_calls"));
        assert_eq!(
            file_sha(&path.join("stream-games.jsonl")).unwrap(),
            meta["stream_intake"]["provenance"]["games_file"]["sha256"]
        );
    }
}
#[test]
fn stream_partial_and_malformed_fail_without_cache_admission() {
    let mut f = Fixture::new(false);
    f.events.pop();
    f.refused();
    let mut f = Fixture::new(false);
    let b = f.save();
    fs::write(&f.binding.stream.path, b"{bad}\n").unwrap();
    f.binding.stream.sha256 = file_sha(&f.binding.stream.path).unwrap();
    let b2 = control(&b.path, &serde_json::to_value(&f.binding).unwrap());
    assert!(
        write_cache(
            &f.binding.stream.path,
            &f.root.join("output"),
            &b2.path,
            &b2.sha256
        )
        .is_err()
    );
    assert!(!f.root.join("output/cache.json").exists());
}
#[test]
fn stream_row_chronology_ids_and_action_must_match() {
    for field in ["ply", "ids", "action"] {
        let mut f = Fixture::new(false);
        f.events[2]["record"]["rows"][0]["teacher"][field] = match field {
            "ply" => json!(7),
            "ids" => json!([[], []]),
            _ => json!(12),
        };
        f.refused();
    }
}
#[test]
fn stream_unknown_cannot_disguise_true_terminal_or_lose_failed_return() {
    let mut f = Fixture::new(false);
    f.events[2]["record"]["termination"] = json!({"type":"unknown","reason":"synthetic"});
    f.refused();
    let mut f = Fixture::new(true);
    f.events[2]["record"]["failed_search"] = Value::Null;
    f.refused();
}
#[test]
fn stream_family_split_footer_and_parent_corruption_refuse() {
    for change in 0..4 {
        let mut f = Fixture::new(false);
        match change {
            0 => f.events[2]["record"]["family"] = json!("unrelated"),
            1 => f.events[2]["record"]["rows"][0]["teacher"]["split"] = json!("train"),
            2 => f.events[3]["record"]["search_calls"] = json!(99),
            _ => f.events[2]["record"]["rows"][0]["search"]["parent"]["history"] = json!([]),
        }
        f.refused();
    }
}
#[test]
fn stream_future_n_refuses_before_source_or_output() {
    let mut f = Fixture::new(false);
    f.binding.scope = "full-volume".into();
    f.binding.stream.path = f.root.join("never-read");
    let b = control(
        &f.root.join("intake.json"),
        &serde_json::to_value(&f.binding).unwrap(),
    );
    let e = write_cache(
        &f.binding.stream.path,
        &f.root.join("output"),
        &b.path,
        &b.sha256,
    )
    .unwrap_err();
    assert!(e.to_string().contains("N is unset"));
    assert!(!f.root.join("output").exists());
}
#[test]
fn stream_existing_output_is_not_overwritten() {
    let mut f = Fixture::new(false);
    fs::create_dir(f.root.join("output")).unwrap();
    fs::write(f.root.join("output/keep"), b"held").unwrap();
    assert!(f.run().is_err());
    assert_eq!(fs::read(f.root.join("output/keep")).unwrap(), b"held");
    assert!(!f.root.join("output/intake-failure.json").exists());
}

#[test]
fn stream_goal_priority_and_exhausted_input_requests_keep_true_census() {
    let mut goal = Fixture::with_case(false, true);
    goal.run().unwrap();
    let row: Value =
        serde_json::from_str(&fs::read_to_string(goal.root.join("output/rows.jsonl")).unwrap())
            .unwrap();
    assert_eq!(row["z"], 1.0);
    assert!(
        row["terminal_targets"]["margin_target_steps"]
            .as_i64()
            .unwrap()
            > 0
    );
    let mut disguised = Fixture::with_case(false, true);
    disguised.events[2]["record"]["termination"] = json!({"type":"unknown","reason":"fake"});
    disguised.refused();

    let mut f = Fixture::new(false);
    let terminal = vec![13, 75, 14, 76, 13, 75, 14, 76, 13];
    let slot = &mut f.events[1]["record"]["scheduled"][0];
    slot["prefix"] = Value::Null;
    slot["canonical_prefix"] = Value::Null;
    slot["root"] = Value::Null;
    slot["attempts"] = json!(
        (0..32)
            .map(|i| json!({"attempt":i,"prefix":terminal,"rejection":"terminal_prefix"}))
            .collect::<Vec<_>>()
    );
    slot["scheduled_failure"] = json!("prefix_attempts_exhausted");
    let partition = partition_families(&[], 20261008).unwrap();
    f.events[1]["record"]["family_partition"] = serde_json::to_value(partition).unwrap();
    f.binding.schedule = control(
        &f.root.join("schedule.json"),
        &json!({"scheduled":f.events[1]["record"]["scheduled"],
        "family_partition":f.events[1]["record"]["family_partition"],"requests_sha256":f.binding.requests_sha256,
        "opened_pilot_inclusion":"excluded"}),
    );
    f.events[2]["record"] = json!({"game":0,"request_id":"synthetic-game","family":null,"initial_prefix":null,
        "final_prefix":null,"final_context":null,"provenance":null,"termination":{"type":"unknown","reason":"prefix_attempts_exhausted"},
        "rows":[],"failed_search":null,"attempted_search_calls":0,"wall_ns":0});
    let footer = &mut f.events[3]["record"];
    for field in [
        "draws",
        "rows",
        "eligible_rows",
        "distinct_positions",
        "opening_positions",
        "search_nodes",
        "search_calls",
        "accepted_search_calls",
    ] {
        footer[field] = json!(0);
    }
    footer["unknown"] = json!(1);
    footer["wall_stock_positions"] = json!({});
    footer["achieved_depths"] = json!({});
    assert_eq!(f.run().unwrap().rows, 0);
    let manifest: Value =
        serde_json::from_slice(&fs::read(f.root.join("output/cache.json")).unwrap()).unwrap();
    assert_eq!(
        manifest["stream_intake"]["provenance"]["census"]["scheduled"],
        1
    );
    assert_eq!(
        manifest["stream_intake"]["provenance"]["census"]["unknown"],
        1
    );
}

#[test]
fn stream_repair_synthetic_cannot_be_relabelled_authoritative() {
    let mut f = Fixture::new(false);
    f.binding.scope = "full-volume".into();
    f.binding.human_quantity_n = Some(1);
    f.events[0]["config"]["main_volume_n"] = json!(1);
    f.events[1]["record"]["config"] = f.events[0]["config"].clone();
    f.binding.config = control(&f.root.join("config.json"), &f.events[0]["config"]);
    f.events[0]["config_sha256"] = json!(f.binding.config.sha256);
    f.events[1]["record"]["config_sha256"] = json!(f.binding.config.sha256);
    let line = format!("{}\n", serde_json::to_string(&f.events[0]).unwrap());
    f.binding.requests_sha256 = quoridor_data::hex_digest(line.as_bytes());
    let mut schedule: Value =
        serde_json::from_slice(&fs::read(&f.binding.schedule.path).unwrap()).unwrap();
    schedule["requests_sha256"] = json!(f.binding.requests_sha256);
    f.binding.schedule = control(&f.root.join("schedule.json"), &schedule);
    f.events[3]["record"]["full_volume_n"] = json!(1);
    let error = f.run().unwrap_err();
    assert!(error.to_string().contains("synthetic provenance"));
    assert!(!f.root.join("output").exists());
}

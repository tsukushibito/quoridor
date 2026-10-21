//! Complete configured gzip-to-cache fixtures. Search returns are synthetic, not model probes.
use quoridor_core::research::{HistoryKey, Ruleset, SigmaContext};
use quoridor_data::{
    Teacher, TeacherRow,
    common_corpus::{EVALUATOR, STREAM_SCHEMA, VERSION},
    file_sha, hex_digest,
    terminal::{
        TerminalProvenance, Termination, attach_terminal_targets, partition_families,
        reflect_action,
    },
    terminal_stream::{BoundJson, write_cache},
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
    events: Vec<Vec<Value>>,
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
    fn new() -> Self {
        let root = std::env::temp_dir().join(format!(
            "configured-stream-{}-{}",
            std::process::id(),
            SERIAL.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir(&root).unwrap();
        let prefixes = [
            vec![13, 67, 22, 58, 31, 49, 40, 50, 49, 51, 58, 52, 67, 53],
            vec![13, 75],
            vec![13, 75, 14, 76, 13, 75, 14, 76],
        ];
        let planned = prefixes
            .iter()
            .enumerate()
            .map(|(i, p)| (format!("fixed-d-family-{i:06}"), p.clone()))
            .collect::<Vec<_>>();
        let partition = partition_families(&planned, 91).unwrap();
        let schedule = prefixes.iter().enumerate().map(|(i,p)| {
            let c=SigmaContext::from_prefix(p).unwrap();
            let reflected=p.iter().map(|a|reflect_action(*a).unwrap()).collect::<Vec<_>>();
            json!({"game":i,"request_id":planned[i].0,"requested_prefix_length":p.len(),"prefix":p,
                "canonical_prefix":std::cmp::min(p.clone(),reflected),"root":context(&c),
                "attempts":[{"attempt":0,"prefix":p,"rejection":null}],"scheduled_failure":null})
        }).collect::<Vec<_>>();
        let global = control(
            &root.join("global-schedule.json"),
            &json!({"scheduled":schedule}),
        );
        let partition_ref = control(
            &root.join("partition.json"),
            &serde_json::to_value(&partition).unwrap(),
        );
        let mut events = vec![];
        for (i, prefix) in prefixes.iter().enumerate() {
            let dir = root.join(format!("batch-{i}"));
            fs::create_dir(&dir).unwrap();
            let unknown = i == 1;
            let goal = i == 0;
            let action = if goal {
                76
            } else if unknown {
                14
            } else {
                13
            };
            let raw = if goal {
                2.0f32
            } else if unknown {
                -0.0
            } else {
                -2.0
            };
            let c = SigmaContext::from_prefix(prefix).unwrap();
            let mut final_c = c.clone();
            final_c.make_move(action).unwrap();
            let mut final_prefix = prefix.clone();
            final_prefix.push(action);
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
            let provenance = TerminalProvenance::from_context(
                &final_c,
                final_prefix.clone(),
                reason,
                detail.into(),
            )
            .unwrap();
            let assignment = partition
                .assignments
                .iter()
                .find(|a| a.game == planned[i].0)
                .unwrap();
            let row = TeacherRow::from_context(
                format!("synthetic-row-{i}"),
                planned[i].0.clone(),
                assignment.family.clone(),
                assignment.split.clone(),
                prefix.clone(),
                &c,
                Some(action),
                Teacher::AlphaBeta {
                    value: raw,
                    depth: 6,
                    nodes: 1,
                    bound: "completed_root".into(),
                    pv: vec![action],
                },
                EVALUATOR.into(),
            )
            .unwrap();
            let mut rows = vec![row];
            attach_terminal_targets(&mut rows, &provenance).unwrap();
            let search = json!({"action":action,"raw_value":raw,"raw_value_bits":raw.to_bits(),"completed_depth":6,"pv":[action],"stop":"depth_cap","counters":{"nodes":1,"policy_calls":0,"tt_retained_bytes":0},"returned_search_wall_ns":0,"parent":context(&c),"accepted":true,"failure":null});
            let failed = if unknown {
                json!({"action":null,"raw_value":null,"raw_value_bits":null,"completed_depth":0,"pv":[],"stop":"synthetic_refusal","counters":{"nodes":9},"returned_search_wall_ns":0,"parent":context(&final_c),"accepted":false,"failure":"synthetic refused port"})
            } else {
                Value::Null
            };
            let config = json!({"ruleset":Ruleset::Standard2pThreefold.config_name(),"planned_games":1,"prefix_seed":90,"attempts_per_prefix":32,"depth":6,"strict_completed_depth":true,"max_nodes":100000,"game_workers":1,"tt_slots":4096,"use_pvs":true,"solver_order_contact":false,"distance_a":0.0,"distance_b":8.0,"per_move_timeout_ms":null,"max_total_plies":200,
                "common_study":{"families":3,"prefix_seed":90,"prefix_lengths":[14,2,8],"split_seed":91,"root_value_policy":"outcome_only","schedule":global,"partition":partition_ref,"batch_start":i,"batch_count":1,"excluded_books":[]}});
            let config_ref = control(&dir.join("config.json"), &config);
            let request = json!({"type":"requests","schema":STREAM_SCHEMA,"generator_version":VERSION,"config":config,"config_sha256":config_ref.sha256,"planned":1,"requested_lengths":[prefix.len()],"requested":[[planned[i].0,prefix.len()]]});
            let request_sha =
                hex_digest(format!("{}\n", serde_json::to_string(&request).unwrap()).as_bytes());
            let sources = json!({"schema":STREAM_SCHEMA,"generator_version":VERSION,"executable_sha256":"a".repeat(64),"evaluator":EVALUATOR,"resource_admission":{"synthetic_fixture":true}});
            control(&dir.join("sources.json"), &sources);
            control(
                &dir.join("schedule.json"),
                &json!({"scheduled":[schedule[i]],"family_partition":partition,"requests_sha256":request_sha}),
            );
            let mut header = sources;
            header["config"] = config;
            header["config_sha256"] = json!(config_ref.sha256);
            header["config_ref"] = serde_json::to_value(config_ref).unwrap();
            header["scheduled"] = json!([schedule[i]]);
            header["family_partition"] = serde_json::to_value(&partition).unwrap();
            let game = json!({"game":i,"request_id":planned[i].0,"family":assignment.family,"initial_prefix":prefix,"final_prefix":final_prefix,"final_context":context(&final_c),"provenance":provenance,"termination":if goal {json!({"type":"goal"})} else if unknown {json!({"type":"unknown","reason":detail})} else {json!({"type":"threefold"})},"rows":[{"teacher":rows[0],"search":search}],"failed_search":failed,"attempted_search_calls":if unknown {2} else {1},"wall_ns":0});
            let [a, b] = c.position().pawns;
            let contact = (a / 9).abs_diff(b / 9) + (a % 9).abs_diff(b % 9) == 1
                && c.position().is_edge_open(a, b);
            let endgame = c
                .position()
                .wall_distance(0)
                .unwrap()
                .min(c.position().wall_distance(1).unwrap())
                <= 2;
            let depth = json!({"policy":VERSION,"ordering":"control-no-policy-signed","requested_depth":6,"max_nodes":100000,"game_workers":1,"search_threads_per_game":1,"result_queue_capacity":1,"workers_joined":1,"started":1,"failed_workers_or_setup":0,"cancelled_before_start":0,"prefix_failures":0,"opaque_failed_work":0,"completed_indices":[0],"game_whole_ns":[0],"final_plies":[final_c.total_ply()],"returned_move_nodes":if unknown {json!([1,9])} else {json!([1])},"returned_depths":if unknown {json!([6,0])} else {json!([6])},"primary_interval":"NOT_RECORDED here: actual controller whole generation+serialization+savedonlyaudit+cleanup receipt required; native_whole_ns excludes final audit/cleanup","completed_games_per_hour":null,"eligible_rows_per_hour":null});
            let footer = json!({"scheduled":1,"recorded":1,"goals":usize::from(goal),"draws":usize::from(!unknown&&!goal),"unknown":usize::from(unknown),"rows":1,"eligible_rows":usize::from(!unknown),"distinct_positions":1,"duplicate_positions":0,"contact_positions":usize::from(contact),"wall_stock_positions":{"10,10":1},"opening_positions":1,"endgame_positions":usize::from(endgame),"search_nodes":if unknown {10} else {1},"search_calls":if unknown {2} else {1},"accepted_search_calls":1,"achieved_depths":{"6":1},"planned_prefix_lengths":{prefix.len().to_string():1},"committed_stream_bytes_before_footer":0,"native_whole_ns":0,"full_volume_n":3,"depth6":depth});
            events.push(vec![request,json!({"type":"header","record":header}),json!({"type":"game","record":{"index":0,"result":{"status":"returned","value":game,"whole_ns":0}}}),json!({"type":"footer","record":footer})]);
        }
        Self { root, events }
    }
    fn save(&mut self) -> Vec<PathBuf> {
        self.events
            .iter_mut()
            .enumerate()
            .map(|(i, events)| {
                if events.last().is_some_and(|v| v["type"] == "footer") {
                    let bytes = events[..events.len() - 1]
                        .iter()
                        .map(|e| serde_json::to_vec(e).unwrap().len() + 1)
                        .sum::<usize>();
                    events.last_mut().unwrap()["record"]["committed_stream_bytes_before_footer"] =
                        json!(bytes);
                }
                let path = self.root.join(format!("batch-{i}/stream.jsonl.gz"));
                let mut writer = quoridor_data::lossless_jsonl::Writer::create(
                    &path,
                    2 * 1024 * 1024,
                    2 * 1024 * 1024,
                )
                .unwrap();
                for e in events {
                    writer
                        .append(format!("{}\n", serde_json::to_string(e).unwrap()).as_bytes())
                        .unwrap();
                }
                let content = writer.finish().unwrap();
                control(
                    &path.parent().unwrap().join("stream-content.json"),
                    &serde_json::to_value(content).unwrap(),
                );
                path
            })
            .collect()
    }
}
#[test]
fn configured_compressed_batches_preserve_outcome_raw_bits_unknown_and_order() {
    let mut f = Fixture::new();
    let inputs = f.save();
    let output = f.root.join("cache");
    let cache = write_cache(&inputs, &output, None).unwrap();
    assert_eq!(cache.rows, 3);
    assert!(!output.join("intake-incomplete.json").exists());
    assert!(!output.join(".intake.partial").exists());
    assert_eq!(
        fs::read(output.join("common-eligible.u8")).unwrap(),
        [1, 0, 1]
    );
    let raw = fs::read(output.join("completed-root-raw.f32")).unwrap();
    assert_eq!(
        raw,
        [
            2.0f32.to_le_bytes(),
            (-0.0f32).to_le_bytes(),
            (-2.0f32).to_le_bytes()
        ]
        .concat()
    );
    let labels = fs::read(output.join("labels.f32")).unwrap();
    assert_eq!(f32::from_le_bytes(labels[4..8].try_into().unwrap()), 1.0);
    assert!(f32::from_le_bytes(labels[12..16].try_into().unwrap()).is_nan());
    assert_eq!(f32::from_le_bytes(labels[20..24].try_into().unwrap()), 0.0);
    let meta: Value =
        serde_json::from_slice(&fs::read(output.join("cache.json")).unwrap()).unwrap();
    assert_eq!(meta["source_binding"].as_array().unwrap().len(), 3);
    assert_eq!(meta["source_content"].as_array().unwrap().len(), 3);
    assert!(meta.get("model_scale_authority").is_none());
    for (i, input) in inputs.iter().enumerate() {
        assert_eq!(meta["source_binding"][i]["path"], input.to_str().unwrap());
        assert_eq!(meta["stream_intake"]["batches"][i]["batch_start"], i);
        assert_eq!(
            meta["sampling"]["games"][i]["game"],
            format!("fixed-d-family-{i:06}")
        );
    }
    let bindings = inputs
        .iter()
        .map(|path| BoundJson {
            path: path.clone(),
            sha256: file_sha(path).unwrap(),
        })
        .collect::<Vec<_>>();
    assert_eq!(
        cache.dataset_sha,
        hex_digest(&serde_json::to_vec(&bindings).unwrap())
    );
    assert!(!output.join("rows.jsonl").exists());
}
#[test]
fn configured_batches_refuse_overlap_gap_reverse_and_existing_output_before_publication() {
    let mut f = Fixture::new();
    let inputs = f.save();
    for (i, indices) in [vec![0, 0], vec![0, 2], vec![1, 0]].iter().enumerate() {
        let selected = indices
            .iter()
            .map(|n| inputs[*n].clone())
            .collect::<Vec<_>>();
        let output = f.root.join(format!("refused-{i}"));
        assert!(write_cache(&selected, &output, None).is_err());
        assert!(!output.exists());
    }
    let output = f.root.join("held");
    fs::create_dir(&output).unwrap();
    fs::write(output.join("keep"), b"held").unwrap();
    assert!(write_cache(&inputs, &output, None).is_err());
    assert_eq!(fs::read(output.join("keep")).unwrap(), b"held");
    assert!(!output.join("intake-incomplete.json").exists());
}
#[test]
fn configured_partial_and_foreign_row_keep_failure_and_incomplete_marker() {
    for partial in [true, false] {
        let mut f = Fixture::new();
        if partial {
            f.events[0].pop();
        } else {
            f.events[0][2]["record"]["result"]["value"]["rows"][0]["search"]["parent"]["history"] =
                json!([]);
        }
        let inputs = f.save();
        let output = f.root.join("failed");
        let error = write_cache(&inputs, &output, None).unwrap_err();
        assert!(error.source().is_some());
        assert!(output.join("intake-incomplete.json").exists());
        assert!(!output.join("cache.json").exists());
        let failure: Value =
            serde_json::from_slice(&fs::read(output.join("intake-failure.json")).unwrap()).unwrap();
        assert_eq!(failure["status"], "FAILED");
        assert!(failure["primary"].as_str().is_some_and(|e| !e.is_empty()));
    }
}

#[test]
fn configured_converter_cli_and_python_loader_share_actual_published_contract() {
    // The standard Cargo executable is usable in ordinary tests. The guarded integration
    // check selects its accepted immutable release image and current project interpreter.
    let converter = std::env::var_os("QUORIDOR_TEST_CONVERTER")
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from(env!("CARGO_BIN_EXE_terminal-cache")));
    let python = std::env::var_os("QUORIDOR_TEST_PYTHON")
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("python3"));
    let mut fixture = Fixture::new();
    let binding_path = std::env::var_os("QUORIDOR_TEST_INITIALIZER_BINDING")
        .map(PathBuf::from)
        .unwrap_or_else(|| {
            // Default software fixtures are explicitly synthetic. The configured
            // guarded check supplies the existing baseline's declared identities.
            let mut identities = Vec::new();
            for name in ["weights", "descriptor", "evaluator"] {
                let path = fixture.root.join(format!("synthetic-{name}.json"));
                control(&path, &json!({"fixture_only":true,"role":name}));
                identities.push(file_sha(&path).unwrap());
            }
            let path = fixture.root.join("synthetic-input-binding.json");
            control(
                &path,
                &json!({"fixture_only":true,"model_scale_authority":{
                "starting_weights_sha256":identities[0],"descriptor_sha256":identities[1],
                "evaluator_sha256":identities[2],"scale_policy":"incumbent_descriptor_T_only"}}),
            );
            path
        });
    let binding_sha = file_sha(&binding_path).unwrap();
    let inputs = fixture.save();
    let output = fixture.root.join("cli-cache");
    let mut command = std::process::Command::new(converter);
    for input in &inputs {
        command.arg("--input").arg(input);
    }
    let returned = command
        .arg("--output")
        .arg(&output)
        .arg("--input-binding")
        .arg(&binding_path)
        .arg("--binding-sha256")
        .arg(binding_sha)
        .output()
        .unwrap();
    assert!(
        returned.status.success(),
        "converter: {}",
        String::from_utf8_lossy(&returned.stderr)
    );
    let script = r#"
import json, sys
from pathlib import Path
import numpy as np
from quoridor_training.common import common_cache_config
from quoridor_training.terminal_cache import TerminalCorpus

path = Path(sys.argv[1])
meta = json.loads((path / "cache.json").read_text())
config = common_cache_config(meta)
assert config["prefix_lengths"] == [14, 2, 8]
assert config["batch_start"] == 0 and config["batch_count"] == 3
assert len(meta["source_content"]) == len(meta["source_binding"]) == 3
expected = json.loads(Path(sys.argv[2]).read_text())["model_scale_authority"]
assert meta["model_scale_authority"] == expected
corpus = TerminalCorpus(path)
assert corpus.row_count == 3
assert corpus.eligible.tolist() == [True, False, True]
assert (
    corpus.labels[0, 1] == 1
    and np.isnan(corpus.labels[1, 1])
    and corpus.labels[2, 1] == 0
)
assert (
    corpus.raw_root_scores.view("<u4").tolist()
    == np.array([2, -0.0, -2], dtype="<f4").view("<u4").tolist()
)
assert [corpus.rows[i]["game"] for i in range(3)] == [
    f"fixed-d-family-{i:06}" for i in range(3)
]
assert corpus.rows[1]["z"] is None
families = {}
for i in range(3):
    row = corpus.rows[i]
    assert families.setdefault(row["group"], row["split"]) == row["split"]
assert not (path / "intake-incomplete.json").exists()
(path / "intake-incomplete.json").write_text("synthetic interrupted publication")
try:
    TerminalCorpus(path)
except ValueError:
    pass
else:
    raise AssertionError("incomplete publication was accepted")
print(
    "actual converter/common_cache_config/TerminalCorpus: PASS; model forwards=0; fit updates=0"
)
"#;
    let returned = std::process::Command::new(python)
        .args(["-B", "-c", script])
        .arg(&output)
        .arg(binding_path)
        .env(
            "PYTHONPATH",
            std::env::join_paths([
                Path::new(env!("CARGO_MANIFEST_DIR"))
                    .join("../../python")
                    .canonicalize()
                    .unwrap(),
                Path::new(env!("CARGO_MANIFEST_DIR"))
                    .join("../../../../shared/python")
                    .canonicalize()
                    .unwrap(),
            ])
            .unwrap(),
        )
        .env("PYTHONSAFEPATH", "1")
        .env("OMP_NUM_THREADS", "1")
        .env("MKL_NUM_THREADS", "1")
        .env("CUDA_VISIBLE_DEVICES", "")
        .output()
        .unwrap();
    assert!(
        returned.status.success(),
        "Python loader: {}",
        String::from_utf8_lossy(&returned.stderr)
    );
    assert!(String::from_utf8_lossy(&returned.stdout).contains("fit updates=0"));
}

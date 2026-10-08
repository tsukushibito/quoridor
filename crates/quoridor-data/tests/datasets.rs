use quoridor_core::research::SigmaContext;
use quoridor_data::*;
use std::path::PathBuf;
fn dir(name: &str) -> PathBuf {
    std::env::temp_dir().join(format!(
        "quoridor-data-{name}-{}-{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ))
}
fn row(id: &str, split: Split) -> TeacherRow {
    let c = SigmaContext::from_prefix(&[]).unwrap();
    TeacherRow::from_context(
        id.into(),
        id.into(),
        id.into(),
        split,
        vec![],
        &c,
        Some(c.legal_ids()[0]),
        Teacher::AlphaBeta {
            value: 0.3,
            depth: 1,
            nodes: 130,
            bound: "exact".into(),
            pv: vec![],
        },
        "test-model".into(),
    )
    .unwrap()
}
#[test]
fn arrow_roundtrip_and_sealed_cache() {
    let d = dir("arrow");
    let mut rows = vec![
        row("train", Split::Train),
        row("val", Split::Validation),
        row("test", Split::Test),
    ];
    let manifest = write_dataset(&d, &mut rows, true, 1).unwrap();
    assert_eq!(manifest.rows, 3);
    assert_eq!(manifest.eligible_rows["train"], 1);
    assert!(!rows[1].eligible);
    assert!(!rows[2].eligible);
    assert_eq!(read_dataset(&d, false).unwrap().len(), 2);
    assert_eq!(read_dataset(&d, true).unwrap().len(), 3);
    let cache = dir("cache");
    let m = write_tensor_cache(&d, &cache, false).unwrap();
    assert_eq!(m.rows, 2);
    assert_eq!(
        std::fs::metadata(cache.join("x.f32")).unwrap().len(),
        2 * 2 * 312 * 4
    );
    std::fs::remove_dir_all(d).unwrap();
    std::fs::remove_dir_all(cache).unwrap();
}
#[test]
fn family_leak_rejected_and_eligibility_never_rescued() {
    let mut train = row("a", Split::Train);
    train.eligible = false;
    let mut val = row("b", Split::Validation);
    val.family = train.family.clone();
    assert!(apply_exposure(&mut [train.clone(), val]).is_err());
    apply_exposure(std::slice::from_mut(&mut train)).unwrap();
    assert!(!train.eligible);
}
#[test]
fn streamed_finalization_and_binding() {
    let d = dir("stream");
    let mut w = DatasetWriter::new(&d, true).unwrap();
    let mut train = row("a", Split::Train);
    train.eligible = false;
    w.push(&[train]).unwrap();
    w.push(&[row("b", Split::Validation)]).unwrap();
    let m = w.finish().unwrap();
    assert_eq!(m.rows, 2);
    assert!(m.eligible_rows.is_empty());
    assert!(read_dataset(&d, false).unwrap().iter().all(|r| !r.eligible));
    std::fs::write(d.join(&m.shards[0].path), b"bad").unwrap();
    assert!(read_dataset(&d, false).is_err());
    std::fs::remove_dir_all(d).unwrap();
}
#[test]
fn terminal_search_score_mapping_keeps_raw() {
    let mut r = row("terminal", Split::Train);
    r.teacher = Teacher::AlphaBeta {
        value: 2.0,
        depth: 1,
        nodes: 1,
        bound: "exact".into(),
        pv: vec![],
    };
    r.validate().unwrap();
    assert_eq!(r.teacher.value(), Some(1.0));
    assert!(matches!(r.teacher, Teacher::AlphaBeta { value: 2.0, .. }));
    r.teacher = Teacher::AlphaBeta {
        value: 1.5,
        depth: 1,
        nodes: 1,
        bound: "exact".into(),
        pv: vec![],
    };
    assert!(r.validate().is_err());
}

#[test]
fn old_alpha_teacher_has_legacy_empty_pv_and_new_pv_roundtrips() {
    let old: Teacher = serde_json::from_value(
        serde_json::json!({"type":"alpha_beta","value":0.3,"depth":1,"nodes":10,"bound":"exact"}),
    )
    .unwrap();
    assert!(matches!(old,Teacher::AlphaBeta{pv,..} if pv.is_empty()));
    let new = Teacher::AlphaBeta {
        value: 0.3,
        depth: 2,
        nodes: 20,
        bound: "completed_exact".into(),
        pv: vec![13, 67],
    };
    let restored: Teacher = serde_json::from_slice(&serde_json::to_vec(&new).unwrap()).unwrap();
    assert!(matches!(restored,Teacher::AlphaBeta{pv,..} if pv==vec![13,67]));
}

#[test]
fn research_threefold_cache_metadata_preserves_perspectives_tensor_bytes_and_missing_labels() {
    let d = dir("metadata");
    let c = SigmaContext::from_prefix(&[13]).unwrap();
    let mut p2 = TeacherRow::from_context(
        "p2".into(),
        "p2".into(),
        "p2".into(),
        Split::Validation,
        vec![13],
        &c,
        Some(c.legal_ids()[0]),
        Teacher::InputOnly,
        "model".into(),
    )
    .unwrap();
    p2.eligible = false;
    let mut rows = vec![row("p1", Split::Train), p2, row("sealed", Split::Test)];
    write_dataset(&d, &mut rows, true, 1).unwrap();
    for allow_test in [false, true] {
        let output = dir("metadata-cache");
        let cache = write_tensor_cache(&d, &output, allow_test).unwrap();
        let expected_rows = read_dataset(&d, allow_test).unwrap();
        assert_eq!(cache.rows, expected_rows.len());
        let mut legacy_x = Vec::new();
        let mut legacy_d = Vec::new();
        let mut legacy_labels = Vec::new();
        let metadata: Vec<serde_json::Value> = std::fs::read_to_string(output.join("rows.jsonl"))
            .unwrap()
            .lines()
            .map(|s| serde_json::from_str(s).unwrap())
            .collect();
        for (r, m) in expected_rows.iter().zip(&metadata) {
            let stm = usize::from(r.side - 1);
            for view in [stm, 1 - stm] {
                let mut dense = [0f32; FEATURE_COUNT];
                for id in &r.ids[view] {
                    dense[usize::from(*id)] = 1.0;
                }
                for value in dense {
                    legacy_x.extend(value.to_le_bytes());
                }
            }
            for value in r.distance {
                legacy_d.extend(value.to_le_bytes());
            }
            for value in [
                r.teacher.value().unwrap_or(f32::NAN),
                r.z.unwrap_or(f32::NAN),
            ] {
                legacy_labels.extend(value.to_le_bytes());
            }
            assert_eq!(
                m["metadata_schema"],
                "quoridor-tensor-row-v3-research-rules"
            );
            assert_eq!(
                m["research_ruleset"],
                r.research_ruleset.as_ref().unwrap().as_str()
            );
            assert_eq!(
                m["history_format"],
                "research-rule-and-stocks-history-SHA-v1"
            );
            assert_eq!(m["state_key"], r.state_key);
            assert_eq!(m["history_key"], r.history_key);
            assert_eq!(m["feature_signature"], r.signature());
            assert_eq!(m["ply"], r.ply);
            assert_eq!(m["side"], r.side);
            assert_eq!(m["ids"], serde_json::json!(r.ids));
            assert_eq!(m["ids_order"], "P1_then_P2");
            assert_eq!(m["distance"], serde_json::json!(r.distance));
            assert_eq!(m["distance_order"], "STM_then_opponent_f32");
            assert_eq!(m["primary_eligible"], r.eligible);
            assert!(m.get("full_history").is_none());
            if r.id == "p2" {
                assert_eq!(r.side, 2);
                assert!(m["rootmean"].is_null());
                assert!(m["z"].is_null());
                assert!(!r.eligible);
            }
        }
        assert_eq!(std::fs::read(output.join("x.f32")).unwrap(), legacy_x);
        assert_eq!(
            std::fs::read(output.join("distance.f32")).unwrap(),
            legacy_d
        );
        assert_eq!(
            std::fs::read(output.join("labels.f32")).unwrap(),
            legacy_labels
        );
        assert_eq!(metadata.iter().any(|m| m["id"] == "sealed"), allow_test);
        std::fs::remove_dir_all(output).unwrap();
    }
    std::fs::remove_dir_all(d).unwrap();
}

#[test]
fn research_threefold_record_provenance_never_promotes_legacy_counts() {
    let current = row("current-rule", Split::Train);
    assert_eq!(
        current.research_ruleset.as_deref(),
        Some("research-standard-2p-threefold-goal-first-v1")
    );
    assert_eq!(current.state_key.split('|').count(), 6);
    current.validate().unwrap();
    let mut encoded = serde_json::to_value(&current).unwrap();
    encoded.as_object_mut().unwrap().remove("research_ruleset");
    let missing: TeacherRow = serde_json::from_value(encoded.clone()).unwrap();
    assert!(missing.research_ruleset.is_none());
    assert!(missing.validate().is_err());
    encoded["state_key"] =
        quoridor_core::research::HistoryKey::from(quoridor_core::Position::default())
            .sigma_string()
            .into();
    let legacy: TeacherRow = serde_json::from_value(encoded).unwrap();
    assert!(legacy.research_ruleset.is_none());
    legacy.validate().unwrap();
    assert!(
        serde_json::to_value(&legacy)
            .unwrap()
            .get("research_ruleset")
            .is_none()
    );
    let mut wrong = current.clone();
    wrong.research_ruleset = Some("RuleA".into());
    assert!(wrong.validate().is_err());
    wrong = current;
    wrong.state_key = legacy.state_key;
    assert!(wrong.validate().is_err());
}

#[test]
fn failed_final_publication_keeps_all_streamed_raw_inputs() {
    for fail_manifest in [false, true] {
        let d = dir(if fail_manifest {
            "manifest-failure"
        } else {
            "shard-failure"
        });
        let mut writer = DatasetWriter::new(&d, false).unwrap();
        writer.push(&[row("first", Split::Train)]).unwrap();
        writer.push(&[row("second", Split::Train)]).unwrap();
        let raw_paths = [d.join("raw-000000.arrow"), d.join("raw-000001.arrow")];
        let before: Vec<_> = raw_paths
            .iter()
            .map(|p| std::fs::read(p).unwrap())
            .collect();
        let occupied = d.join(if fail_manifest {
            "manifest.json"
        } else {
            "train-000001.arrow"
        });
        std::fs::write(&occupied, b"owned fixture prevents exclusive publication").unwrap();
        assert!(writer.finish().is_err());
        for (path, bytes) in raw_paths.iter().zip(before) {
            assert_eq!(std::fs::read(path).unwrap(), bytes);
        }
        assert_eq!(
            std::fs::read(occupied).unwrap(),
            b"owned fixture prevents exclusive publication"
        );
        std::fs::remove_dir_all(d).unwrap();
    }
}

#[test]
fn collected_and_streamed_readers_share_malformed_row_errors() {
    use arrow2::{
        array::Array,
        chunk::Chunk,
        datatypes::Schema,
        io::ipc::write::{FileWriter, WriteOptions},
    };
    use sha2::{Digest, Sha256};
    let d = dir("missing-column");
    let mut rows = vec![row("first", Split::Train)];
    let mut manifest = write_dataset(&d, &mut rows, false, 1).unwrap();
    let shard = d.join(&manifest.shards[0].path);
    let mut writer = FileWriter::try_new(
        std::fs::File::create(&shard).unwrap(),
        Schema::from(Vec::new()),
        None,
        WriteOptions { compression: None },
    )
    .unwrap();
    writer
        .write(&Chunk::new(Vec::<Box<dyn Array>>::new()), None)
        .unwrap();
    writer.finish().unwrap();
    manifest.shards[0].sha256 = format!("{:x}", Sha256::digest(std::fs::read(&shard).unwrap()));
    std::fs::write(
        d.join("manifest.json"),
        serde_json::to_vec_pretty(&manifest).unwrap(),
    )
    .unwrap();
    let collected = read_dataset(&d, false).unwrap_err().to_string();
    let streamed = for_each_row(&d, false, |_| Ok(())).unwrap_err().to_string();
    assert_eq!(collected, streamed);
    // The same checked iterator feeds cache creation; it must also reject this shard.
    let cache = dir("missing-column-cache");
    assert!(write_tensor_cache(&d, &cache, false).is_err());
    std::fs::remove_dir_all(d).unwrap();
    if cache.exists() {
        std::fs::remove_dir_all(cache).unwrap();
    }
}

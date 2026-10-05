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

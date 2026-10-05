use quoridor_core::{Position, research::features};
use quoridor_data::{
    OutcomeImportConfig, Split, Teacher, file_sha, import_sigma_outcomes, read_dataset,
    sigma_plane_position, write_tensor_cache,
};
use std::{io::Cursor, path::PathBuf};
fn dir(name: &str) -> PathBuf {
    std::env::temp_dir().join(format!(
        "quoridor-outcome-{name}-{}-{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ))
}
fn asymmetric() -> Position {
    Position {
        horizontal: 1 << 3,
        vertical: 1 << (2 * 8 + 5),
        walls_remaining: [9, 9],
        ..Position::default()
    }
}
#[test]
fn original_and_p2_canonical_maps_and_lr_padding() {
    for turn in [0, 1] {
        let p = Position {
            turn,
            ..asymmetric()
        }
        .checked()
        .unwrap();
        let input = features(p);
        let decoded = sigma_plane_position(&input).unwrap();
        assert_eq!(features(decoded), input);
        assert_eq!(decoded.turn, 0); // canonicalSTM, not original actual side
        let mut naive = [0.; 648];
        for plane in 0..8 {
            for y in 0..9 {
                for x in 0..9 {
                    naive[plane * 81 + y * 9 + x] = input[plane * 81 + y * 9 + 8 - x];
                }
            }
        }
        // A shifted interior vertical wall can still describe a legal board,
        // and its full distance maps may match when that edge is immaterial.
        // Therefore naiveLR is not universally rejectable by validity alone.
        let mirror_bits = |bits: u64| {
            let mut out = 0;
            for a in 0..64 {
                if bits & (1 << a) != 0 {
                    out |= 1 << (a / 8 * 8 + 7 - a % 8);
                }
            }
            out
        };
        let mirror = Position {
            pawns: p.pawns.map(|c| c / 9 * 9 + 8 - c % 9),
            horizontal: mirror_bits(p.horizontal),
            vertical: mirror_bits(p.vertical),
            ..p
        };
        let correct = features(mirror.checked().unwrap());
        assert!(sigma_plane_position(&correct).is_ok());
        assert_ne!(naive, correct);
        let boundary = Position {
            vertical: 1 << (2 * 8),
            ..p
        };
        let original = features(boundary.checked().unwrap());
        let mut bad_padding = [0.; 648];
        for plane in 0..8 {
            for y in 0..9 {
                for x in 0..9 {
                    bad_padding[plane * 81 + y * 9 + x] = original[plane * 81 + y * 9 + 8 - x];
                }
            }
        }
        assert!(sigma_plane_position(&bad_padding).is_err());
    }
}
#[test]
fn external_z_only_availability_zero_exclusion_and_tensor_bytes() {
    let input = features(asymmetric());
    let mut raw = Vec::new();
    for (index, z) in [1f32, 0., -1.].into_iter().enumerate() {
        raw.extend((index as u64).to_le_bytes());
        for value in input {
            raw.extend(value.to_le_bytes());
        }
        raw.extend(z.to_le_bytes());
    }
    let output = dir("dataset");
    let cfg = OutcomeImportConfig {
        source: "fixed-source".into(),
        revision: "fixed-revision".into(),
        shard: "cycle".into(),
        split: Split::Train,
        records: 3,
        output: output.clone(),
    };
    let receipt = import_sigma_outcomes(Cursor::new(raw), &cfg).unwrap();
    assert_eq!(receipt["zero"], 1);
    let rows = read_dataset(&output, false).unwrap();
    assert_eq!(rows.len(), 3);
    for row in &rows {
        assert!(matches!(row.teacher, Teacher::ExternalOutcome { .. }));
        assert_eq!(row.teacher.value(), None);
        assert!(row.history_key.is_empty());
        assert_eq!(row.game, "UNAVAILABLE");
    }
    assert!(!rows[1].eligible);
    let mut invalid = rows[1].clone();
    invalid.eligible = true;
    assert!(invalid.validate().is_err());
    let mut fractional = rows[0].clone();
    fractional.z = Some(0.5);
    assert!(fractional.validate().is_err());
    let c1 = dir("cache1");
    let c2 = dir("cache2");
    write_tensor_cache(&output, &c1, false).unwrap();
    write_tensor_cache(&output, &c2, false).unwrap();
    for name in ["x.f32", "distance.f32", "labels.f32"] {
        assert_eq!(
            file_sha(&c1.join(name)).unwrap(),
            file_sha(&c2.join(name)).unwrap()
        );
    }
    let bytes = std::fs::read(c1.join("labels.f32")).unwrap();
    for index in 0..3 {
        assert!(f32::from_le_bytes(bytes[index * 8..index * 8 + 4].try_into().unwrap()).is_nan());
    }
    let meta = std::fs::read_to_string(c1.join("rows.jsonl")).unwrap();
    let m: serde_json::Value = serde_json::from_str(meta.lines().next().unwrap()).unwrap();
    assert!(m["game"].is_null());
    assert!(m["ply"].is_null());
    assert!(m["rootmean"].is_null());
    assert_eq!(m["teacher_type"], "external_terminal_outcome");
    for p in [output, c1, c2] {
        std::fs::remove_dir_all(p).unwrap();
    }
}

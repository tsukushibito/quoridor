//! Canonical board-only public input bridge. No histories, labels or inference.
//! Packed key is the existing geometry20 + two LE-f32 native distance inputs.
//! Sigma planes come from the sole core encoder; no plane formula lives here.
use quoridor_core::Position;

fn position(key: &[u8; 28]) -> Option<Position> {
    let board = Position {
        pawns: [key[0], key[1]],
        walls_remaining: [key[2], key[3]],
        horizontal: u64::from_le_bytes(key[4..12].try_into().ok()?),
        vertical: u64::from_le_bytes(key[12..20].try_into().ok()?),
        turn: 0, // canonical public STM view, not an inferred historical side
        winner: None,
    }
    .checked()
    .ok()?;
    let input = quoridor_nnue::encode_qf1(board).ok()?;
    let distance = [
        u32::from_le_bytes(key[20..24].try_into().ok()?),
        u32::from_le_bytes(key[24..28].try_into().ok()?),
    ];
    if input.distance.map(f32::to_bits) != distance {
        return None;
    }
    Some(board)
}

/// Reconstruct native Sigma8 inputs from already bound board-only model keys.
/// Status0 means checked exact geometry/distance; status1 rejects that row.
/// No terminal/history/repetition label is created. Invalid siblings stay local.
///
/// # Safety
/// key is live rows*28 bytes; output live rows*648 f32; status live rows bytes.
/// The three allocations must be nonoverlapping and output/status writable.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn quoridor_public_sigma_inputs(
    key: *const u8,
    rows: usize,
    output: *mut f32,
    status: *mut u8,
) -> i32 {
    if key.is_null() || output.is_null() || status.is_null() || rows == 0 || rows > 8192 {
        return 1;
    }
    let keys = unsafe { std::slice::from_raw_parts(key, rows * 28) };
    let output = unsafe { std::slice::from_raw_parts_mut(output, rows * 648) };
    let status = unsafe { std::slice::from_raw_parts_mut(status, rows) };
    output.fill(0.);
    status.fill(1);
    for (index, key) in keys.as_chunks::<28>().0.iter().enumerate() {
        if let Some(board) = position(key) {
            let encoded = quoridor_core::research::features(board);
            output[index * 648..(index + 1) * 648].copy_from_slice(&encoded);
            status[index] = 0;
        }
    }
    0
}

/// Board-only core209 mask for the SAME checked canonical STM public key.
/// No fabricated history/repetition/WDL or upstream mask classifier.
///
/// # Safety
/// key: rows*28 readable bytes; mask: rows*209 writable bytes; status: rows
/// writable bytes; all buffers nonoverlapping, each live for the full call.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn quoridor_public_policy_masks(
    key: *const u8,
    rows: usize,
    mask: *mut u8,
    status: *mut u8,
) -> i32 {
    if key.is_null() || mask.is_null() || status.is_null() || rows == 0 || rows > 8192 {
        return 1;
    }
    let keys = unsafe { std::slice::from_raw_parts(key, rows * 28) };
    let masks = unsafe { std::slice::from_raw_parts_mut(mask, rows * 209) };
    let status = unsafe { std::slice::from_raw_parts_mut(status, rows) };
    masks.fill(0);
    status.fill(1);
    for (i, key) in keys.as_chunks::<28>().0.iter().enumerate() {
        if let Some(board) = position(key) {
            // The existing checked public-key owner already refuses goal
            // geometry without a genuine winner; do not invent that history.
            let legal = board.legal_action_ids();
            if !legal.is_empty() {
                for id in legal {
                    masks[i * 209 + usize::from(id)] = 1;
                }
                status[i] = 0;
            }
        }
    }
    0
}

/// Normal native value and optional policy identity. Loads but performs zero heads.
/// Policy shared-fingerprint/SHA/shape/coordinates are checked by PolicyHead::load.
///
/// # Safety
/// path: path_len UTF-8 bytes; optional policy: policy_len UTF-8 bytes (NULL iff
/// policy_len=0); output: 64 writable bytes. All buffers live and disjoint.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn quoridor_public_nnue_identity(
    path: *const u8,
    path_len: usize,
    policy: *const u8,
    policy_len: usize,
    output: *mut u8,
) -> i32 {
    if path.is_null()
        || output.is_null()
        || path_len == 0
        || path_len > 4096
        || policy_len > 4096
        || (policy.is_null() != (policy_len == 0))
    {
        return 1;
    }
    let raw = unsafe { std::slice::from_raw_parts(path, path_len) };
    let Ok(path) = std::str::from_utf8(raw) else {
        return 1;
    };
    let path = std::path::Path::new(path);
    if !path.is_absolute() {
        return 1;
    }
    let Ok(model) = quoridor_nnue::residual::ResidualModel::load(path) else {
        return 2;
    };
    let mut identity = [0_u8; 64];
    identity[..32].copy_from_slice(&model.fingerprint());
    if policy_len != 0 {
        let raw = unsafe { std::slice::from_raw_parts(policy, policy_len) };
        let Ok(path) = std::str::from_utf8(raw) else {
            return 1;
        };
        if !std::path::Path::new(path).is_absolute() {
            return 1;
        }
        let Ok(head) = quoridor_nnue::policy::PolicyHead::load(path, &model) else {
            return 3;
        };
        identity[32..].copy_from_slice(&head.fingerprint());
    }
    unsafe { std::slice::from_raw_parts_mut(output, 64) }.copy_from_slice(&identity);
    0
}

fn model_key(board: Position) -> crate::Result<[u8; 28]> {
    let input = quoridor_nnue::encode_qf1(board)?;
    let mut key = [0; 28];
    key[..2].copy_from_slice(&board.pawns);
    key[2..4].copy_from_slice(&board.walls_remaining);
    key[4..12].copy_from_slice(&board.horizontal.to_le_bytes());
    key[12..20].copy_from_slice(&board.vertical.to_le_bytes());
    for (i, distance) in input.distance.iter().enumerate() {
        key[20 + i * 4..24 + i * 4].copy_from_slice(&distance.to_le_bytes());
    }
    Ok(key)
}

/// Opaque, SHA-bound unprotected public T/V input classes. No labels/history.
/// PAIR37 belongs to the completed static-public input owner, not a book codec.
pub struct StaticInputExclusions {
    keys: Vec<[u8; 28]>,
}
impl StaticInputExclusions {
    pub fn from_manifest(reference: &crate::terminal_stream::BoundJson) -> crate::Result<Self> {
        use sha2::{Digest, Sha256};
        use std::{
            fs::File,
            io::{BufReader, Read},
            path::Path,
        };

        let manifest = reference.read()?;
        if manifest["schema"] != "quoridor-public-static-input-classes-v1"
            || manifest["status"] != "COMPLETE"
            || manifest["original_only"] != true
            || manifest["pair_record_bytes"] != 37
            || reference
                .path
                .parent()
                .ok_or("input manifest parent")?
                .join("INCOMPLETE")
                .exists()
        {
            return Err("complete original unprotected PAIR37 input manifest required".into());
        }
        let entry = &manifest["class_pairs"];
        let path = Path::new(entry["path"].as_str().ok_or("PAIR37 path")?);
        let expected_bytes = entry["bytes"].as_u64().ok_or("PAIR37 bytes")?;
        let expected_rows = manifest["counts"]["pair_rows"]
            .as_u64()
            .ok_or("PAIR37 count")?;
        let expected_sha = entry["sha256"].as_str().ok_or("PAIR37 SHA")?;
        if !path.is_absolute()
            || !std::fs::symlink_metadata(path)?.file_type().is_file()
            || expected_bytes == 0
            || expected_bytes % 37 != 0
            || expected_bytes / 37 != expected_rows
            || expected_sha.len() != 64
            || !expected_sha
                .bytes()
                .all(|c| c.is_ascii_digit() || (b'a'..=b'f').contains(&c))
        {
            return Err("exact finite PAIR37 framing/custody required".into());
        }
        let file = File::open(path)?;
        if file.metadata()?.len() != expected_bytes {
            return Err("PAIR37 payload length differs".into());
        }
        let mut reader = BufReader::new(file);
        let mut digest = Sha256::new();
        let mut keys = Vec::new();
        keys.try_reserve_exact(usize::try_from(expected_rows)?)?;
        let mut observations = [0_u64; 2];
        for _ in 0..expected_rows {
            let mut row = [0; 37];
            reader.read_exact(&mut row)?;
            digest.update(row);
            let key: [u8; 28] = row[..28].try_into()?;
            let n = u64::from(u32::from_le_bytes(row[28..32].try_into()?))
                + u64::from(u32::from_le_bytes(row[32..36].try_into()?));
            if n == 0 || row[36] > 1 || keys.last().is_some_and(|previous| previous >= &key) {
                return Err(
                    "PAIR37 sorted unique unprotected class/multiplicity/split differs".into(),
                );
            }
            let split = usize::from(row[36]);
            observations[split] = observations[split]
                .checked_add(n)
                .ok_or("PAIR37 count overflow")?;
            keys.push(key);
        }
        let mut extra = [0];
        if reader.read(&mut extra)? != 0
            || format!("{:x}", digest.finalize()) != expected_sha
            || reader.get_ref().metadata()?.len() != expected_bytes
            || observations[0] != manifest["counts"]["train"].as_u64().ok_or("T count")?
            || observations[1] != manifest["counts"]["validation"].as_u64().ok_or("V count")?
        {
            return Err("PAIR37 complete SHA/multiplicity census differs".into());
        }
        Ok(Self { keys })
    }

    pub fn contains_prefix(&self, prefix: &[u16]) -> crate::Result<bool> {
        use quoridor_core::research::SigmaContext;

        // Reuse the sole full-prefix replay/LR action owner. No board-only
        // public input is assigned a fabricated history.
        let reflected = prefix
            .iter()
            .map(|&action| crate::terminal::reflect_action(action))
            .collect::<crate::Result<Vec<_>>>()?;
        for actions in [prefix, reflected.as_slice()] {
            let context = SigmaContext::from_prefix(actions)?;
            // The existing Sigma STM plane owner handles player exchange and
            // goal direction; its existing decoder supplies canonical player0.
            let canonical = crate::sigma_plane_position(&quoridor_core::research::features(
                context.position(),
            ))?;
            let key = model_key(canonical)?;
            if self.keys.binary_search(&key).is_ok() {
                return Ok(true);
            }
        }
        Ok(false)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn key(p: Position) -> [u8; 28] {
        let mut out = [0; 28];
        out[..2].copy_from_slice(&p.pawns);
        out[2..4].copy_from_slice(&p.walls_remaining);
        out[4..12].copy_from_slice(&p.horizontal.to_le_bytes());
        out[12..20].copy_from_slice(&p.vertical.to_le_bytes());
        for (i, d) in quoridor_nnue::encode_qf1(p)
            .unwrap()
            .distance
            .iter()
            .enumerate()
        {
            out[20 + i * 4..24 + i * 4].copy_from_slice(&d.to_le_bytes());
        }
        out
    }

    #[test]
    fn joint_policy_masks_use_core_jumps_and_all_wall_ids() {
        let boards = [
            Position::default(),
            Position {
                pawns: [40, 49],
                ..Position::default()
            }
            .checked()
            .unwrap(),
        ];
        let mut masks = [255_u8; 2 * 209];
        let mut status = [255_u8; 2];
        let packed = boards.map(key).concat();
        assert_eq!(
            unsafe {
                quoridor_public_policy_masks(
                    packed.as_ptr(),
                    2,
                    masks.as_mut_ptr(),
                    status.as_mut_ptr(),
                )
            },
            0
        );
        assert_eq!(status, [0, 0]);
        let pawn_ids = |row: &[u8]| {
            row[..81]
                .iter()
                .enumerate()
                .filter_map(|(i, &legal)| (legal == 1).then_some(i))
                .collect::<Vec<_>>()
        };
        assert_eq!(pawn_ids(&masks[..209]), vec![3, 5, 13]);
        assert_eq!(pawn_ids(&masks[209..]), vec![31, 39, 41, 58]);
        for row in masks.as_chunks::<209>().0 {
            assert!(row[81..].iter().all(|&legal| legal == 1));
            assert!(row.iter().all(|&legal| legal <= 1));
        }
    }

    #[test]
    fn joint_policy_mask_refuses_goal_or_bad_sibling_without_head() {
        let ordinary = key(Position::default());
        let mut goal = ordinary;
        goal[0] = 76;
        goal[1] = 67; // a board-only key may not fabricate the missing winner
        let mut malformed = ordinary;
        malformed[0] = 81;
        let packed = [ordinary, goal, malformed, ordinary].concat();
        let mut masks = [255_u8; 4 * 209];
        let mut status = [255_u8; 4];
        assert_eq!(
            unsafe {
                quoridor_public_policy_masks(
                    packed.as_ptr(),
                    4,
                    masks.as_mut_ptr(),
                    status.as_mut_ptr(),
                )
            },
            0
        );
        assert_eq!(status, [0, 1, 1, 0]);
        assert!(masks[209..3 * 209].iter().all(|&x| x == 0));
        assert_eq!(&masks[..209], &masks[3 * 209..]);
    }

    #[test]
    fn joint_input_identity_ffi_bounds_refuse_before_loading() {
        assert_eq!(
            unsafe {
                quoridor_public_policy_masks(
                    std::ptr::null(),
                    1,
                    std::ptr::null_mut(),
                    std::ptr::null_mut(),
                )
            },
            1
        );
        let path = *b"x";
        let mut out = [0_u8; 64];
        for size in [0, 4097, usize::MAX] {
            assert_eq!(
                unsafe {
                    quoridor_public_nnue_identity(
                        path.as_ptr(),
                        size,
                        std::ptr::null(),
                        0,
                        out.as_mut_ptr(),
                    )
                },
                1
            );
        }
        assert_eq!(
            unsafe {
                quoridor_public_nnue_identity(
                    path.as_ptr(),
                    1,
                    std::ptr::null(),
                    1,
                    out.as_mut_ptr(),
                )
            },
            1
        );
    }

    #[test]
    fn public_static_key_rejects_self_declared_distance_or_geometry() {
        let original = key(Position::default());
        assert!(position(&original).is_some());
        for replacement in [f32::NAN.to_bits(), 0_f32.to_bits()] {
            let mut bad = original;
            bad[20..24].copy_from_slice(&replacement.to_le_bytes());
            assert!(position(&bad).is_none());
        }
        let mut bad = original;
        bad[2] = 9; // no matching placed wall: total stock law must remain enforced
        assert!(position(&bad).is_none());
        let mut bad = original;
        bad[1] = bad[0];
        assert!(position(&bad).is_none());
    }

    #[test]
    fn public_static_batch_has_independent_status_and_canonical_stm() {
        let board = Position {
            pawns: [12, 68],
            ..Position::default()
        }
        .checked()
        .unwrap();
        let good = key(board);
        let mut bad = good;
        bad[0] = 81;
        let keys = [good, bad, good].concat();
        let mut planes = [f32::NAN; 3 * 648];
        let mut status = [255; 3];
        let result = unsafe {
            quoridor_public_sigma_inputs(keys.as_ptr(), 3, planes.as_mut_ptr(), status.as_mut_ptr())
        };
        assert_eq!(result, 0);
        assert_eq!(status, [0, 1, 0]);
        assert_eq!(planes[12], 1.);
        assert_eq!(planes[81 + 68], 1.);
        assert!(planes[648..1296].iter().all(|x| *x == 0.));
        assert_eq!(&planes[..648], &planes[1296..]);
        assert_eq!(
            quoridor_core::research::features(board).as_slice(),
            &planes[..648]
        );
    }

    #[test]
    fn public_static_input_ffi_rejects_invalid_batch_before_pointer_read() {
        assert_eq!(
            unsafe {
                quoridor_public_sigma_inputs(
                    std::ptr::null(),
                    1,
                    std::ptr::null_mut(),
                    std::ptr::null_mut(),
                )
            },
            1
        );
        let mut value = 0_f32;
        let mut status = 0_u8;
        let key = 0_u8;
        for rows in [0, 8193, usize::MAX] {
            assert_eq!(
                unsafe { quoridor_public_sigma_inputs(&key, rows, &mut value, &mut status) },
                1
            );
        }
    }

    fn endpoint_manifest(
        root: &std::path::Path,
        entries: &[([u8; 28], u32, u8)],
    ) -> crate::terminal_stream::BoundJson {
        std::fs::create_dir(root).unwrap();
        let mut raw = Vec::new();
        let mut counts = [0_u64; 2];
        for (key, n, split) in entries {
            raw.extend(key);
            raw.extend(n.to_le_bytes());
            raw.extend(0_u32.to_le_bytes());
            raw.push(*split);
            counts[usize::from(*split == 1)] += u64::from(*n);
        }
        let pairs = root.join("pairs.bin");
        std::fs::write(&pairs, &raw).unwrap();
        let path = root.join("cache.json");
        std::fs::write(
            &path,
            serde_json::to_vec(&serde_json::json!({
                "schema":"quoridor-public-static-input-classes-v1","status":"COMPLETE",
                "original_only":true,"pair_record_bytes":37,
                "class_pairs":{"path":pairs,"bytes":raw.len(),"sha256":crate::hex_digest(&raw)},
                "counts":{"pair_rows":entries.len(),"train":counts[0],"validation":counts[1]}
            }))
            .unwrap(),
        )
        .unwrap();
        crate::terminal_stream::BoundJson {
            sha256: crate::file_sha(&path).unwrap(),
            path,
        }
    }

    fn endpoint_key(prefix: &[u16]) -> [u8; 28] {
        use quoridor_core::research::SigmaContext;
        let reflected = prefix
            .iter()
            .map(|&a| crate::terminal::reflect_action(a).unwrap())
            .collect::<Vec<_>>();
        [prefix, reflected.as_slice()]
            .iter()
            .map(|actions| {
                let p = SigmaContext::from_prefix(actions).unwrap().position();
                let canonical =
                    crate::sigma_plane_position(&quoridor_core::research::features(p)).unwrap();
                let k = model_key(canonical).unwrap();
                assert_eq!(k, key(canonical)); // independent pre-existing packing reference
                k
            })
            .min()
            .unwrap()
    }

    #[test]
    fn public_static_endpoint_pair37_binding_and_canonical_turn_lr() {
        let root = std::env::temp_dir().join(format!(
            "public-static-endpoint-positive-{}",
            std::process::id()
        ));
        let mut entries = vec![(endpoint_key(&[3]), 2, 0), (endpoint_key(&[13, 67]), 3, 1)];
        entries.sort_by_key(|entry| entry.0);
        let reference = endpoint_manifest(&root, &entries);
        let bank = StaticInputExclusions::from_manifest(&reference).unwrap();
        assert!(bank.contains_prefix(&[3]).unwrap()); // P1 STM becomes public canonical P0
        assert!(bank.contains_prefix(&[5]).unwrap()); // native true LR
        assert!(bank.contains_prefix(&[13, 67]).unwrap()); // P0 STM / V class also excluded
        assert!(!bank.contains_prefix(&[]).unwrap());
        assert!(bank.contains_prefix(&[0]).is_err()); // illegal prefix is not "not found"
        std::fs::write(root.join("INCOMPLETE"), b"original failed publication").unwrap();
        assert!(StaticInputExclusions::from_manifest(&reference).is_err());
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn public_static_endpoint_refuses_hash_order_split_and_multiplicity_mismatch() {
        let base = std::env::temp_dir().join(format!(
            "public-static-endpoint-negative-{}",
            std::process::id()
        ));
        std::fs::create_dir(&base).unwrap();
        let k = endpoint_key(&[3]);
        for (name, entries) in [
            ("duplicate", vec![(k, 1, 0), (k, 1, 1)]),
            ("zero", vec![(k, 0, 0)]),
            ("split", vec![(k, 1, 2)]),
        ] {
            let reference = endpoint_manifest(&base.join(name), &entries);
            assert!(StaticInputExclusions::from_manifest(&reference).is_err());
        }
        let reference = endpoint_manifest(&base.join("hash"), &[(k, 1, 0)]);
        let mut raw = std::fs::read(base.join("hash/pairs.bin")).unwrap();
        raw[0] ^= 1;
        std::fs::write(base.join("hash/pairs.bin"), raw).unwrap();
        assert!(StaticInputExclusions::from_manifest(&reference).is_err());
        let reference = endpoint_manifest(&base.join("counts"), &[(k, 1, 0)]);
        let mut metadata = reference.read().unwrap();
        metadata["counts"]["train"] = serde_json::json!(2);
        std::fs::write(&reference.path, serde_json::to_vec(&metadata).unwrap()).unwrap();
        let changed = crate::terminal_stream::BoundJson {
            sha256: crate::file_sha(&reference.path).unwrap(),
            path: reference.path,
        };
        assert!(StaticInputExclusions::from_manifest(&changed).is_err());
        std::fs::remove_dir_all(base).unwrap();
    }
}

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

/// The existing full-history and STM owners supply the sole packed input key.
fn context_model_key(context: &quoridor_core::research::SigmaContext) -> crate::Result<[u8; 28]> {
    let canonical =
        crate::sigma_plane_position(&quoridor_core::research::features(context.position()))?;
    model_key(canonical)
}

/// Legally replay bounded prefixes and their true LR histories, with no model.
/// Each successful row contains original key28 followed by reflected key28.
/// Status1 rejects illegal or terminal histories; invalid siblings remain local.
///
/// # Safety
/// actions: actions_len readable u16 (nonnull even if empty); offsets: rows+1
/// readable usize; output: rows*56 writable bytes; status: rows writable bytes.
/// All allocations are live and nonoverlapping throughout the call.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn quoridor_public_prefix_keys(
    actions: *const u16,
    actions_len: usize,
    offsets: *const usize,
    rows: usize,
    output: *mut u8,
    status: *mut u8,
) -> i32 {
    if actions.is_null()
        || offsets.is_null()
        || output.is_null()
        || status.is_null()
        || rows == 0
        || rows > 64
        || actions_len > rows * 200
    {
        return 1;
    }
    let actions = unsafe { std::slice::from_raw_parts(actions, actions_len) };
    let offsets = unsafe { std::slice::from_raw_parts(offsets, rows + 1) };
    if offsets[0] != 0
        || offsets[rows] != actions_len
        || offsets.windows(2).any(|v| v[0] > v[1] || v[1] - v[0] > 200)
    {
        return 2;
    }
    let output = unsafe { std::slice::from_raw_parts_mut(output, rows * 56) };
    let status = unsafe { std::slice::from_raw_parts_mut(status, rows) };
    output.fill(0);
    status.fill(1);
    for i in 0..rows {
        let prefix = &actions[offsets[i]..offsets[i + 1]];
        let result = (|| -> crate::Result<[[u8; 28]; 2]> {
            let reflected = prefix
                .iter()
                .map(|&a| crate::terminal::reflect_action(a))
                .collect::<crate::Result<Vec<_>>>()?;
            let mut keys = [[0; 28]; 2];
            for (j, history) in [prefix, reflected.as_slice()].into_iter().enumerate() {
                let context = quoridor_core::research::SigmaContext::from_prefix(history)?;
                if context.terminal_value().is_some() {
                    return Err("prefix class input must be genuinely nonterminal".into());
                }
                keys[j] = context_model_key(&context)?;
            }
            Ok(keys)
        })();
        if let Ok(keys) = result {
            output[i * 56..i * 56 + 28].copy_from_slice(&keys[0]);
            output[i * 56 + 28..(i + 1) * 56].copy_from_slice(&keys[1]);
            status[i] = 0;
        }
    }
    0
}

/// One actual chronological input view. The key uses the existing Sigma STM
/// owner; QF1/side are the actual absolute board used by normal NNUE. These are
/// deliberately separate frames, not an assertion of learned LR invariance.
#[repr(C)]
#[derive(Clone, Copy)]
pub struct PublicPrefixView {
    pub key: [u8; 28],
    pub side: u8,
    pub qf1: [u8; 624],
    pub distance: [f32; 2],
    /// Absolute core ActionID -> this public key's canonical STM ActionID.
    pub action_to_key: [u16; 209],
    pub legal_in_key: [u8; 209],
    pub prefix: [u16; 200],
    pub prefix_len: u16,
}
impl PublicPrefixView {
    fn from_context(history: &[u16]) -> crate::Result<Self> {
        let context = quoridor_core::research::SigmaContext::from_prefix(history)?;
        if context.terminal_value().is_some() {
            return Err("diagnostic prefix must be genuinely nonterminal".into());
        }
        let board = context.position();
        let input = quoridor_nnue::encode_qf1(board)?;
        let mut view = Self {
            key: context_model_key(&context)?,
            side: input.side,
            qf1: [0; 624],
            distance: input.distance,
            action_to_key: [0; 209],
            legal_in_key: [0; 209],
            prefix: [0; 200],
            prefix_len: history.len() as u16,
        };
        view.prefix[..history.len()].copy_from_slice(history);
        for (player, ids) in input.ids.iter().enumerate() {
            for &id in ids {
                view.qf1[player * 312 + usize::from(id)] = 1;
            }
        }
        for action in 0..209_u16 {
            // Sigma features normalize the goal direction by a row reflection.
            // Compose the maintained rotation and LR owners; no new geometry.
            view.action_to_key[usize::from(action)] = if board.turn == 0 {
                action
            } else {
                crate::terminal::reflect_action(quoridor_nnue::policy::rotate_action(action)?)?
            };
        }
        for action in board.legal_action_ids() {
            view.legal_in_key[usize::from(view.action_to_key[usize::from(action)])] = 1;
        }
        let canonical = position(&view.key).ok_or("native diagnostic key refused")?;
        let mut expected = [0_u8; 209];
        for action in canonical.legal_action_ids() {
            expected[usize::from(action)] = 1;
        }
        if expected != view.legal_in_key || !expected.contains(&1) {
            return Err("actual/public action frame legal-mask mismatch".into());
        }
        Ok(view)
    }
}

/// Native actual inputs plus original/true-LR histories, at most16 parents.
/// Successful parent i writes views 2*i and 2*i+1; status is per parent.
/// A rejected sibling never supplies a usable view. No model or search is loaded.
///
/// # Safety
/// actions: actions_len live u16 (nonnull even empty); offsets: rows+1 usize;
/// output: 2*rows writable PublicPrefixView; status: rows writable bytes.
/// All buffers must be disjoint and live for the call.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn quoridor_public_prefix_views(
    actions: *const u16,
    actions_len: usize,
    offsets: *const usize,
    rows: usize,
    output: *mut PublicPrefixView,
    status: *mut u8,
) -> i32 {
    if actions.is_null()
        || offsets.is_null()
        || output.is_null()
        || status.is_null()
        || rows == 0
        || rows > 16
        || actions_len > rows * 200
    {
        return 1;
    }
    let actions = unsafe { std::slice::from_raw_parts(actions, actions_len) };
    let offsets = unsafe { std::slice::from_raw_parts(offsets, rows + 1) };
    if offsets[0] != 0
        || offsets[rows] != actions_len
        || offsets.windows(2).any(|v| v[0] > v[1] || v[1] - v[0] > 200)
    {
        return 2;
    }
    let status = unsafe { std::slice::from_raw_parts_mut(status, rows) };
    status.fill(1);
    for i in 0..rows {
        let result = (|| -> crate::Result<[PublicPrefixView; 2]> {
            let prefix = &actions[offsets[i]..offsets[i + 1]];
            let reflected = prefix
                .iter()
                .map(|&a| crate::terminal::reflect_action(a))
                .collect::<crate::Result<Vec<_>>>()?;
            Ok([
                PublicPrefixView::from_context(prefix)?,
                PublicPrefixView::from_context(&reflected)?,
            ])
        })();
        if let Ok(views) = result {
            unsafe {
                output.add(2 * i).write(views[0]);
                output.add(2 * i + 1).write(views[1]);
            }
            status[i] = 0;
        }
    }
    0
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
        // These are the two current publisher declarations, not interchangeable
        // flags added to an already published cache. Both payloads contain only
        // unprotected T/V originals; full-public also reports excluded originals.
        let prefix_fixture =
            manifest["source_mode"] == "prefix-fixture" && manifest.get("original_only").is_none();
        let full_public =
            manifest.get("source_mode").is_none() && manifest["original_only"] == true;
        let counts = &manifest["counts"];
        let train = counts["train"].as_u64().ok_or("T count")?;
        let validation = counts["validation"].as_u64().ok_or("V count")?;
        let protected = counts["protected_original_observations"]
            .as_u64()
            .ok_or("protected original count")?;
        let qualified = counts["qualified_original_observations"]
            .as_u64()
            .ok_or("qualified original count")?;
        let originals = manifest["original_observations"]
            .as_u64()
            .ok_or("original observation count")?;
        let protected_bits = ["1", "2", "3"].into_iter().try_fold(0_u64, |sum, bit| {
            sum.checked_add(counts["protected_by_bits"][bit].as_u64()?)
        });
        let complete_count = train
            .checked_add(validation)
            .and_then(|n| n.checked_add(protected));
        if manifest["schema"] != "quoridor-public-static-input-classes-v1"
            || manifest["status"] != "COMPLETE"
            || !(prefix_fixture || full_public)
            || counts["protected_by_bits"]
                .as_object()
                .map(|bits| bits.len())
                != Some(3)
            || protected_bits != Some(protected)
            || complete_count != Some(qualified)
            || qualified == 0
            || originals < qualified
            || (prefix_fixture && (originals != qualified || protected != 0))
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
            || observations[0] != train
            || observations[1] != validation
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
            let key = context_model_key(&context)?;
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

    #[test]
    fn diagnostic_prefix_views_bind_actual_stm_and_public_action_frame_nn0() {
        let histories = [vec![3], vec![3, 67]];
        let actions: Vec<_> = histories.iter().flatten().copied().collect();
        let offsets = [0, 1, 3];
        let mut views = std::mem::MaybeUninit::<[PublicPrefixView; 4]>::uninit();
        let mut status = [255_u8; 2];
        assert_eq!(
            unsafe {
                quoridor_public_prefix_views(
                    actions.as_ptr(),
                    actions.len(),
                    offsets.as_ptr(),
                    2,
                    views.as_mut_ptr().cast(),
                    status.as_mut_ptr(),
                )
            },
            0
        );
        assert_eq!(status, [0, 0]);
        let views = unsafe { views.assume_init() };
        assert_eq!(views[0].side, 1);
        assert_eq!(views[2].side, 0);
        assert_eq!(&views[0].prefix[..1], &[3]);
        assert_eq!(&views[1].prefix[..1], &[5]);
        for view in &views {
            let prefix = &view.prefix[..usize::from(view.prefix_len)];
            let context = quoridor_core::research::SigmaContext::from_prefix(prefix).unwrap();
            let native = quoridor_nnue::encode_qf1(context.position()).unwrap();
            assert_eq!(view.side, native.side);
            assert_eq!(view.distance, native.distance);
            assert_eq!(view.key, context_model_key(&context).unwrap());
            let permutation: std::collections::BTreeSet<_> =
                view.action_to_key.into_iter().collect();
            assert_eq!(permutation.len(), 209);
            for action in 0..209_u16 {
                let in_key = view.action_to_key[usize::from(action)];
                assert_eq!(
                    view.legal_in_key[usize::from(in_key)] == 1,
                    context.play(action).is_ok()
                );
            }
            for (player, ids) in native.ids.iter().enumerate() {
                for id in 0..312_u16 {
                    assert_eq!(
                        view.qf1[player * 312 + usize::from(id)] == 1,
                        ids.contains(&id)
                    );
                }
            }
        }
        assert_eq!(
            unsafe {
                quoridor_public_prefix_views(
                    std::ptr::null(),
                    0,
                    offsets.as_ptr(),
                    2,
                    std::ptr::null_mut(),
                    status.as_mut_ptr(),
                )
            },
            1
        );
        let bad = [209_u16];
        let mut sentinel = std::mem::MaybeUninit::<[PublicPrefixView; 2]>::uninit();
        assert_eq!(
            unsafe {
                quoridor_public_prefix_views(
                    bad.as_ptr(),
                    1,
                    [0, 1].as_ptr(),
                    1,
                    sentinel.as_mut_ptr().cast(),
                    status.as_mut_ptr(),
                )
            },
            0
        );
        assert_eq!(status[0], 1); // rejected output is never read
    }

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
                "source_mode":"prefix-fixture","pair_record_bytes":37,
                "original_observations":counts[0]+counts[1],
                "class_pairs":{"path":pairs,"bytes":raw.len(),"sha256":crate::hex_digest(&raw)},
                "counts":{"pair_rows":entries.len(),"train":counts[0],"validation":counts[1],
                    "qualified_original_observations":counts[0]+counts[1],
                    "protected_original_observations":0,"protected_by_bits":{"1":0,"2":0,"3":0}}
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
    fn public_static_endpoint_current_publisher_declarations_and_census() {
        let root = std::env::temp_dir().join(format!(
            "public-static-publisher-census-{}",
            std::process::id()
        ));
        // Opaque synthetic PAIR37 key only: no geometry/model/feature execution.
        let reference = endpoint_manifest(&root, &[([1; 28], 2, 0), ([2; 28], 3, 1)]);
        let original = reference.read().unwrap();
        assert!(original.get("original_only").is_none());
        let read = |metadata: &serde_json::Value| {
            std::fs::write(&reference.path, serde_json::to_vec(metadata).unwrap()).unwrap();
            StaticInputExclusions::from_manifest(&crate::terminal_stream::BoundJson {
                path: reference.path.clone(),
                sha256: crate::file_sha(&reference.path).unwrap(),
            })
        };
        assert_eq!(read(&original).unwrap().keys.len(), 2);
        // Full-public retains its distinct current declaration and may census
        // protected/rejected source originals outside the unprotected payload.
        let mut public = original.clone();
        public.as_object_mut().unwrap().remove("source_mode");
        public["original_only"] = serde_json::json!(true);
        public["original_observations"] = serde_json::json!(8);
        public["counts"]["qualified_original_observations"] = serde_json::json!(7);
        public["counts"]["protected_original_observations"] = serde_json::json!(2);
        public["counts"]["protected_by_bits"]["1"] = serde_json::json!(2);
        assert_eq!(read(&public).unwrap().keys.len(), 2);

        for (field, value) in [
            ("source_mode", serde_json::json!("unknown")),
            ("status", serde_json::json!("INCOMPLETE")),
            ("schema", serde_json::json!("wrong")),
            ("pair_record_bytes", serde_json::json!(38)),
            ("original_only", serde_json::json!(false)),
            ("original_observations", serde_json::json!(6)),
            ("original_observations", serde_json::json!(4)),
        ] {
            let mut bad = original.clone();
            bad[field] = value;
            assert!(read(&bad).is_err(), "{field}");
        }
        for (field, value) in [
            ("qualified_original_observations", serde_json::json!(6)),
            ("protected_original_observations", serde_json::json!(1)),
            ("protected_by_bits", serde_json::json!({"1":1,"2":0,"3":0})),
            ("protected_by_bits", serde_json::json!({"1":0,"2":0})),
            (
                "protected_by_bits",
                serde_json::json!({"1":0,"2":0,"3":0,"4":1}),
            ),
            ("train", serde_json::json!(3)),
            ("train", serde_json::json!(u64::MAX)),
            ("pair_rows", serde_json::json!(3)),
        ] {
            let mut bad = original.clone();
            bad["counts"][field] = value;
            assert!(read(&bad).is_err(), "{field}");
        }
        let mut protected_fixture = original.clone();
        protected_fixture["original_observations"] = serde_json::json!(6);
        protected_fixture["counts"]["qualified_original_observations"] = serde_json::json!(6);
        protected_fixture["counts"]["protected_original_observations"] = serde_json::json!(1);
        protected_fixture["counts"]["protected_by_bits"]["1"] = serde_json::json!(1);
        assert!(read(&protected_fixture).is_err());
        let mut bad_public = public.clone();
        bad_public["counts"]["protected_by_bits"]["1"] = serde_json::json!(1);
        assert!(read(&bad_public).is_err());

        // A consistent declaration still cannot override streamed multiplicity.
        let mut wrong_stream_count = original.clone();
        wrong_stream_count["original_observations"] = serde_json::json!(6);
        wrong_stream_count["counts"]["qualified_original_observations"] = serde_json::json!(6);
        wrong_stream_count["counts"]["train"] = serde_json::json!(3);
        assert!(read(&wrong_stream_count).is_err());

        // The same reader still owns the complete stream SHA and split checks.
        read(&original).unwrap();
        let pairs = root.join("pairs.bin");
        let raw = std::fs::read(&pairs).unwrap();
        let mut corrupt = raw.clone();
        corrupt[0] ^= 1;
        std::fs::write(&pairs, corrupt).unwrap();
        assert!(read(&original).is_err());
        let mut protected_row = raw;
        protected_row[36] = 2;
        std::fs::write(&pairs, &protected_row).unwrap();
        let mut rebound = original.clone();
        rebound["class_pairs"]["sha256"] = serde_json::json!(crate::hex_digest(&protected_row));
        assert!(read(&rebound).is_err());
        std::fs::remove_dir_all(root).unwrap();
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

    #[test]
    fn prefix_key_ffi_preserves_native_stm_lr_and_rejects_terminal_history() {
        let histories: &[&[u16]] = &[&[], &[3], &[13, 67], &[0], &[13, 67, 4, 76, 13, 67, 4, 76]];
        let actions: Vec<u16> = histories.iter().flat_map(|p| p.iter().copied()).collect();
        let mut offsets = vec![0];
        for p in histories {
            offsets.push(offsets.last().unwrap() + p.len());
        }
        let mut output = vec![255; histories.len() * 56];
        let mut status = vec![255; histories.len()];
        assert_eq!(
            unsafe {
                quoridor_public_prefix_keys(
                    actions.as_ptr(),
                    actions.len(),
                    offsets.as_ptr(),
                    histories.len(),
                    output.as_mut_ptr(),
                    status.as_mut_ptr(),
                )
            },
            0
        );
        assert_eq!(status, [0, 0, 0, 1, 1]);
        for (i, p) in histories[..3].iter().enumerate() {
            let lr = p
                .iter()
                .map(|&a| crate::terminal::reflect_action(a).unwrap())
                .collect::<Vec<_>>();
            for (j, history) in [*p, lr.as_slice()].into_iter().enumerate() {
                let c = quoridor_core::research::SigmaContext::from_prefix(history).unwrap();
                let canonical =
                    crate::sigma_plane_position(&quoridor_core::research::features(c.position()))
                        .unwrap();
                let expected = key(canonical); // pre-existing independent packing reference
                assert_eq!(&output[i * 56 + j * 28..i * 56 + (j + 1) * 28], &expected);
            }
        }
        assert_eq!(&output[..28], &output[28..56]); // self LR is observable
        assert!(output[3 * 56..].iter().all(|v| *v == 0));
    }

    #[test]
    fn prefix_key_ffi_refuses_invalid_framing_before_output() {
        let actions = [3_u16];
        let mut output = [255_u8; 56];
        let mut status = [255_u8];
        for offsets in [[1_usize, 1], [0, 2], [1, 0]] {
            assert_eq!(
                unsafe {
                    quoridor_public_prefix_keys(
                        actions.as_ptr(),
                        1,
                        offsets.as_ptr(),
                        1,
                        output.as_mut_ptr(),
                        status.as_mut_ptr(),
                    )
                },
                2
            );
            assert_eq!(output, [255; 56]);
        }
        assert_eq!(
            unsafe {
                quoridor_public_prefix_keys(
                    std::ptr::null(),
                    0,
                    std::ptr::null(),
                    1,
                    output.as_mut_ptr(),
                    status.as_mut_ptr(),
                )
            },
            1
        );
        assert_eq!(
            unsafe {
                quoridor_public_prefix_keys(
                    actions.as_ptr(),
                    1,
                    [0_usize, 1].as_ptr(),
                    65,
                    output.as_mut_ptr(),
                    status.as_mut_ptr(),
                )
            },
            1
        );
    }
}

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
}

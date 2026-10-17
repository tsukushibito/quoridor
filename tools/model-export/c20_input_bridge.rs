//! Bounded C20 batch bridge over the exact pinned v1.3.1 encoder closure.
//! The caller first checks every same 28-byte key with the canonical core
//! board/distance bridge. No history, Search, teacher or value formula is added.
//! Build with the five source files bound by the original encoder closure.
mod bitboard;
mod encode;
mod endgame;
mod movegen;
mod state;
pub use bitboard::*;
pub use movegen::is_wall_path_legal;
pub use state::{GameState, Move};

/// Native C20 encoder only, with the same setup as the qualified input reference.
///
/// # Safety
/// keys: rows*28 live bytes. output: rows*1620 live f32. status: rows live bytes.
/// Buffers are nonoverlapping. Caller has core-qualified every exact key first.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn quoridor_public_c20_inputs(
    keys: *const u8,
    rows: usize,
    output: *mut f32,
    status: *mut u8,
) -> i32 {
    if keys.is_null() || output.is_null() || status.is_null() || rows == 0 || rows > 8192 {
        return 1;
    }
    let keys = unsafe { std::slice::from_raw_parts(keys, rows * 28) };
    let output = unsafe { std::slice::from_raw_parts_mut(output, rows * 1620) };
    let status = unsafe { std::slice::from_raw_parts_mut(status, rows) };
    output.fill(0.);
    status.fill(1);
    for (index, key) in keys.as_chunks::<28>().0.iter().enumerate() {
        let (a, b, sa, sb) = (key[0], key[1], key[2], key[3]);
        let h = u64::from_le_bytes(key[4..12].try_into().expect("fixed geometry"));
        let v = u64::from_le_bytes(key[12..20].try_into().expect("fixed geometry"));
        if a >= 81
            || b >= 81
            || a == b
            || sa > 10
            || sb > 10
            || u32::from(sa) + u32::from(sb) + h.count_ones() + v.count_ones() != 20
        {
            continue;
        }
        let mut state = GameState::with_pawns(a, b, 0);
        for slot in 0..64 {
            if h & (1u64 << slot) != 0 {
                state.setup_wall(slot, true);
            }
            if v & (1u64 << slot) != 0 {
                state.setup_wall(slot, false);
            }
        }
        state.walls_left = [sa, sb];
        let encoded = encode::encode20(&state);
        if encoded.len() != 1620 || encoded.iter().any(|x| !x.is_finite()) {
            continue;
        }
        output[index * 1620..(index + 1) * 1620].copy_from_slice(&encoded);
        status[index] = 0;
    }
    0
}

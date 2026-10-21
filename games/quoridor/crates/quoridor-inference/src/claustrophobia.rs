//! Narrow callback ABI over the pinned upstream's own rules, encoder and MCTS.
//! No libtorch dependency: the owning Python process supplies the joint head.
use claustrophobia_upstream as upstream;
use std::{ffi::c_void, panic::AssertUnwindSafe};

#[cfg(not(panic = "unwind"))]
compile_error!("Claustrophobia callback failure funnel requires panic=unwind");

pub const COMMIT: &str = "ae093653e62ad700e201706fa5ed767093d0d68e";
pub const ABI: u32 = 1;
type Head = unsafe extern "C" fn(*mut c_void, *const f32, *const u8, *mut f32, *mut f32) -> i32;

#[unsafe(no_mangle)]
pub extern "C" fn quoridor_claustrophobia_commit_v1() -> *const std::ffi::c_char {
    c"ae093653e62ad700e201706fa5ed767093d0d68e".as_ptr()
}

#[repr(C)]
pub struct Output {
    pub abi: u32,
    pub action: u32,
    pub simulations: u32,
    pub head_calls: u64,
    pub root_value: f32,
    pub legal_absolute: [u8; 209],
}

/// Upstream policy indices are STM-canonical; common arena IDs are absolute.
fn rotate(action: usize, side: u8) -> usize {
    if side == 0 {
        action
    } else if action < 81 {
        80 - action
    } else if action < 145 {
        81 + 63 - (action - 81)
    } else {
        145 + 63 - (action - 145)
    }
}

fn root(prefix: &[u16]) -> Result<upstream::GameState, ()> {
    let mut state = upstream::GameState::start();
    for &action in prefix {
        if action >= 209 || state.is_terminal() {
            return Err(());
        }
        let canonical = rotate(usize::from(action), state.side);
        let movement = upstream::index_to_move(&state, canonical).ok_or(())?;
        let mut legal = upstream::MoveBuf::new();
        upstream::generate_all_moves(&state, &mut legal);
        if !legal.as_slice().contains(&movement) {
            return Err(());
        }
        state.make_move(movement);
    }
    if state.is_terminal() {
        return Err(());
    }
    Ok(state)
}

#[derive(Debug)]
struct HeadFailure;

/// # Safety
/// Non-null arrays must contain the declared elements; callback must not unwind.
/// A nonzero return leaves output non-authoritative. No partial success fallback.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn quoridor_claustrophobia_search_v1(
    prefix: *const u16,
    length: usize,
    simulations: u32,
    c_puct: f64,
    max_head_calls: u64,
    expected_legal: *const u8,
    head: Head,
    user: *mut c_void,
    output: *mut Output,
) -> i32 {
    if output.is_null()
        || expected_legal.is_null()
        || prefix.is_null()
        || length > u16::MAX as usize
        || !c_puct.is_finite()
        || c_puct <= 0.0
        || max_head_calls == 0
    {
        return 1;
    }
    let run = std::panic::catch_unwind(AssertUnwindSafe(|| {
        let prefix = unsafe { std::slice::from_raw_parts(prefix, length) };
        let state = root(prefix).map_err(|_| 2)?;
        let calls = std::cell::Cell::new(0u64);
        let root_value = std::cell::Cell::new(f32::NAN);
        let evaluate = |leaf: &upstream::GameState| {
            let abort = || std::panic::resume_unwind(Box::new(HeadFailure));
            if calls.get() >= max_head_calls {
                abort();
            }
            calls.set(calls.get() + 1);
            let mut tensor = [0f32; 20 * 81];
            upstream::encode20_into(leaf, &mut tensor);
            let mut mask = [false; 209];
            upstream::legal_mask_into(leaf, &mut mask);
            let wire_mask = mask.map(u8::from);
            let mut policy = [f32::NAN; 209];
            let mut value = f32::NAN;
            let code = unsafe {
                head(
                    user,
                    tensor.as_ptr(),
                    wire_mask.as_ptr(),
                    policy.as_mut_ptr(),
                    &mut value,
                )
            };
            if code != 0 || !value.is_finite() || value.abs() > 1.0 {
                abort();
            }
            let mut priors = Vec::new();
            let mut sum = 0.0f64;
            for (action, &p) in policy.iter().enumerate() {
                if !p.is_finite() || p < 0.0 || (!mask[action] && p != 0.0) {
                    abort();
                }
                if mask[action] {
                    priors.push((action, p));
                    sum += f64::from(p);
                }
            }
            if priors.is_empty() || (sum - 1.0).abs() > 1e-4 {
                abort();
            }
            if calls.get() == 1 {
                root_value.set(value);
            }
            (priors, value)
        };
        let mut mask = [false; 209];
        upstream::legal_mask_into(&state, &mut mask);
        let mut legal_absolute = [0u8; 209];
        for (action, legal) in mask.into_iter().enumerate() {
            legal_absolute[rotate(action, state.side)] = u8::from(legal);
        }
        if unsafe { std::slice::from_raw_parts(expected_legal, 209) } != legal_absolute {
            return Err(5);
        }
        let (action, completed) = if simulations == 0 {
            evaluate(&state);
            (u32::MAX, 0)
        } else {
            // This is the original play.rs sequential entry, not Sigma MCTS,
            // webserve's extra endgame/ponder stack, or a reimplementation.
            let result = upstream::mcts::run_mcts(state, &evaluate, simulations, c_puct);
            if result.best_action >= 209 || result.total_simulations != simulations {
                return Err(3);
            }
            (
                rotate(result.best_action, state.side) as u32,
                result.total_simulations,
            )
        };
        unsafe {
            output.write(Output {
                abi: ABI,
                action,
                simulations: completed,
                head_calls: calls.get(),
                root_value: root_value.get(),
                legal_absolute,
            });
        }
        Ok(())
    }));
    match run {
        Ok(Ok(())) => 0,
        Ok(Err(code)) => code,
        Err(_) => 4,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn claustrophobia16_absolute_canonical_roundtrip_all209_both_sides() {
        for side in [0, 1] {
            let mapped: std::collections::BTreeSet<_> = (0..209).map(|a| rotate(a, side)).collect();
            assert_eq!(mapped.len(), 209);
            for action in 0..209 {
                assert_eq!(rotate(rotate(action, side), side), action);
                assert_eq!(action < 81, rotate(action, side) < 81);
                assert_eq!(
                    (81..145).contains(&action),
                    (81..145).contains(&rotate(action, side))
                );
            }
        }
    }

    #[test]
    fn claustrophobia16_replay_owns_stock_side_legal_jump_and_illegal_prefix() {
        let state = root(&[81, 163]).unwrap();
        assert_eq!(state.walls_left, [9, 9]);
        assert_eq!(state.side, 0);
        assert!(root(&[209]).is_err());
        assert!(root(&[80]).is_err());
        let jumped = root(&[13, 67, 22, 58, 31, 49, 40, 31, 22]).unwrap();
        assert_eq!(jumped.pawn[0], 22);
    }

    #[test]
    fn claustrophobia16_wrong_common_legal_mask_refuses_before_head() {
        unsafe extern "C" fn forbidden(
            _user: *mut c_void,
            _input: *const f32,
            _mask: *const u8,
            _policy: *mut f32,
            _value: *mut f32,
        ) -> i32 {
            if !_user.is_null() {
                unsafe {
                    *(_user as *mut u64) += 1;
                }
            }
            99
        }
        let prefix = [0u16; 1];
        let mask = [0u8; 209];
        let mut result = std::mem::MaybeUninit::<Output>::uninit();
        let mut calls = 0u64;
        let code = unsafe {
            quoridor_claustrophobia_search_v1(
                prefix.as_ptr(),
                0,
                8,
                1.5,
                9,
                mask.as_ptr(),
                forbidden,
                &mut calls as *mut u64 as *mut c_void,
                result.as_mut_ptr(),
            )
        };
        assert_eq!(code, 5);
        assert_eq!(calls, 0);
        assert_eq!(std::mem::size_of::<Output>(), 240);
        assert_eq!(std::mem::offset_of!(Output, head_calls), 16);
        assert_eq!(std::mem::offset_of!(Output, root_value), 24);
        assert_eq!(std::mem::offset_of!(Output, legal_absolute), 28);
    }
}

//! Initial non-learning evaluation, separate from the simple corner/flip policy.
//! Values are centidiscs from the side-to-move perspective. Phase is occupied
//! discs (0..64); only the disc term changes at phase 48. This is not a model.

use crate::bitboard::Position;

const CORNERS: u64 = 0x8100000000000081;

pub fn evaluate(position: Position) -> i32 {
    let (own, opponent) = position.sides();
    let mobility = position.legal_moves().count_ones() as i32
        - position.switched().legal_moves().count_ones() as i32;
    let corners = (own & CORNERS).count_ones() as i32 - (opponent & CORNERS).count_ones() as i32;
    let phase = position.occupied().count_ones();
    let disc_weight = if phase < 48 { 1 } else { 20 };
    100 * mobility + 800 * corners + disc_weight * position.disc_difference()
}

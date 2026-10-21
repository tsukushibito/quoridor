// SPDX-License-Identifier: GPL-3.0-or-later
// Egaroucid Console 7.8.1 load_unzip_egev2 / evaluation table layout.

use std::io::{self, Read};

use super::{N_PHASES, STONE_VALUES, geometry::TABLE_OFFSETS};

pub const PATTERN_VALUES: usize = TABLE_OFFSETS[16];
pub const PHASE_VALUES: usize = PATTERN_VALUES + STONE_VALUES;
pub const MIDGAME_VALUES: usize = N_PHASES * PHASE_VALUES;
pub const ORDERING_VALUES: usize = 4 * 59049;

/// One compact immutable raw view. No color-reversed or max-cell padded copy.
/// The input weights remain caller supplied; this module embeds no weight body.
pub struct FullWeights {
    pub(super) midgame: Box<[i16]>,
    pub(super) ordering: Box<[i16]>,
}

impl FullWeights {
    /// Native callers should supply buffered readers. On Wasm a byte slice is
    /// already a reader, so the same decoder consumes both platforms' inputs.
    /// The pinned files encode little-endian signed words (native x86 upstream).
    pub fn read(midgame: impl Read, ordering: impl Read) -> io::Result<Self> {
        Ok(Self {
            midgame: decode_egev2(midgame, MIDGAME_VALUES)?.into_boxed_slice(),
            ordering: read_ordering(ordering)?.into_boxed_slice(),
        })
    }

    pub fn from_bytes(midgame: &[u8], ordering: &[u8]) -> io::Result<Self> {
        Self::read(midgame, ordering)
    }

    pub fn decoded_bytes(&self) -> usize {
        (self.midgame.len() + self.ordering.len()) * size_of::<i16>()
    }
}

fn invalid(message: &'static str) -> io::Error {
    io::Error::new(io::ErrorKind::InvalidData, message)
}

fn allocate(count: usize) -> io::Result<Vec<i16>> {
    let mut values = Vec::new();
    values.try_reserve_exact(count).map_err(io::Error::other)?;
    Ok(values)
}

fn word(input: &mut impl Read) -> io::Result<i16> {
    let mut bytes = [0; 2];
    input.read_exact(&mut bytes)?;
    Ok(i16::from_le_bytes(bytes))
}

fn eof(input: &mut impl Read) -> io::Result<()> {
    let mut byte = [0];
    if input.read(&mut byte)? != 0 {
        return Err(invalid("trailing weight bytes"));
    }
    Ok(())
}

/// Header is the compressed token count, not the decoded element count.
/// 4096 is a valid zero-length run; negative words are literal weights.
/// Decode directly into the final allocation; malformed runs cannot grow it.
pub(super) fn decode_egev2(mut input: impl Read, expected: usize) -> io::Result<Vec<i16>> {
    let mut header = [0; 4];
    input.read_exact(&mut header)?;
    let count = i32::from_le_bytes(header);
    if count < 0 {
        return Err(invalid("negative compressed token count"));
    }
    let mut values = allocate(expected)?;
    for _ in 0..count {
        let token = word(&mut input)?;
        if token >= 4096 {
            let end = values.len() + (token - 4096) as usize;
            if end > expected {
                return Err(invalid("zero run exceeds exact decoded length"));
            }
            values.resize(end, 0);
        } else {
            if values.len() == expected {
                return Err(invalid("literal exceeds exact decoded length"));
            }
            values.push(token);
        }
    }
    if values.len() != expected {
        return Err(invalid("wrong decoded weight length"));
    }
    eof(&mut input)?;
    Ok(values)
}

fn read_ordering(mut input: impl Read) -> io::Result<Vec<i16>> {
    // No header/compression: four consecutive 3^10 tables for shapes 8..11.
    let mut values = allocate(ORDERING_VALUES)?;
    for _ in 0..ORDERING_VALUES {
        values.push(word(&mut input)?);
    }
    eof(&mut input)?;
    Ok(values)
}

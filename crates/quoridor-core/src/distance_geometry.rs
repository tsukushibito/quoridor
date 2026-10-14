//! Immutable exact wall geometry. Only canonical BFS or exact deletion repair constructs it.
use super::{Position, WallEdges, neighbors};

/// Whole distances and shortest-path descent links for one exact wall key.
/// Fields are private: public mutable NNUE features cannot supply trusted maps.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct WallDistanceGeometry {
    horizontal: u64,
    vertical: u64,
    edges: WallEdges,
    distances: [[u8; 81]; 2],
    // Source cells with an open descending edge, in N, S, E, W order.
    descent: [[u128; 4]; 2],
}

// Partial repair initializes81 buckets and inspects up to4 neighbors per marked
// cell. Above half the board, prefer the same canonical bit-frontier BFS.
// One predetermined policy, not a measured crossover or a tuning parameter.
const FULL_REBUILD_MARKED: u32 = 40;

impl WallDistanceGeometry {
    pub(super) fn of(position: Position) -> Self {
        let edges = WallEdges::of(position);
        let mut descent = [[0; 4]; 2];
        let distances = std::array::from_fn(|player| {
            edges.distance_map_with_descent(player, Some(&mut descent[player]))
        });
        Self {
            horizontal: position.horizontal,
            vertical: position.vertical,
            edges,
            distances,
            descent,
        }
    }

    /// Readonly rows; goal rows are0 and unreachable cells81. No position validation.
    pub fn distances(&self) -> &[[u8; 81]; 2] {
        &self.distances
    }

    pub fn distances_for(&self, position: Position) -> Option<&[[u8; 81]; 2]> {
        (self.horizontal == position.horizontal && self.vertical == position.vertical)
            .then_some(&self.distances)
    }

    /// Strictly one wall-bit addition to this genuine immutable parent key.
    /// Non-additions return None; the caller uses canonical construction. This
    /// is wall-only geometry, not legal-move or mutable-accumulator validation.
    pub fn after_addition(&self, after: Position) -> Option<Self> {
        let added_h = after.horizontal & !self.horizontal;
        let added_v = after.vertical & !self.vertical;
        let (horizontal, anchor) = if after.vertical == self.vertical
            && after.horizontal & self.horizontal == self.horizontal
            && added_h.is_power_of_two()
        {
            (true, added_h.trailing_zeros() as u8)
        } else if after.horizontal == self.horizontal
            && after.vertical & self.vertical == self.vertical
            && added_v.is_power_of_two()
        {
            (false, added_v.trailing_zeros() as u8)
        } else {
            return None;
        };
        let cell = u32::from(anchor / 8) * 9 + u32::from(anchor % 8);
        let removed = if horizontal {
            let south = 3u128 << cell;
            [south << 9, south, 0, 0]
        } else {
            let east = ((1u128 << 9) | 1) << cell;
            [0, 0, east, east << 1]
        };
        let mut result = self.clone();
        result.horizontal = after.horizontal;
        result.vertical = after.vertical;
        result.edges = self.edges.with_wall(horizontal, anchor);
        for player in 0..2 {
            let marked = invalidate(&mut result.descent[player], removed);
            if marked.count_ones() > FULL_REBUILD_MARKED {
                result.distances[player] = result
                    .edges
                    .distance_map_with_descent(player, Some(&mut result.descent[player]));
            } else if marked != 0 {
                repair(
                    &result.edges,
                    &mut result.distances[player],
                    &mut result.descent[player],
                    marked,
                );
            }
        }
        Some(result)
    }
}

fn supported(descent: &[u128; 4]) -> u128 {
    descent[0] | descent[1] | descent[2] | descent[3]
}

/// Clear both wall segments first, then remove supports pointing into the old
/// strictly-descending DAG's invalid region. Goals/unreachable cells have no
/// links to lose; alternate surviving descents stop propagation.
fn invalidate(descent: &mut [u128; 4], removed: [u128; 4]) -> u128 {
    let mut lost = 0;
    for direction in 0..4 {
        lost |= descent[direction] & removed[direction];
        descent[direction] &= !removed[direction];
    }
    let mut frontier = lost & !supported(descent);
    let mut marked = frontier;
    while frontier != 0 {
        if marked.count_ones() > FULL_REBUILD_MARKED {
            return marked;
        }
        // Source cells whose N/S/E/W destination is in this invalid frontier.
        // Existing link masks already exclude borders and bits outside the board.
        let sources = [frontier << 9, frontier >> 9, frontier >> 1, frontier << 1];
        let mut affected = 0;
        for direction in 0..4 {
            affected |= descent[direction] & sources[direction];
            descent[direction] &= !sources[direction];
        }
        frontier = affected & !supported(descent) & !marked;
        marked |= frontier;
    }
    marked
}

/// Multi-source shortest paths from unequal fixed boundary distances. A bucket
/// bitmask pops the least distance, never an unordered mixed-distance FIFO.
fn repair(edges: &WallEdges, distances: &mut [u8; 81], descent: &mut [u128; 4], marked: u128) {
    let mut cells = marked;
    while cells != 0 {
        distances[cells.trailing_zeros() as usize] = 81;
        cells &= cells - 1;
    }
    for direction in descent.iter_mut() {
        *direction &= !marked;
    }
    let mut buckets = [0u128; 81];
    let mut pending = 0u128;
    cells = marked;
    while cells != 0 {
        let cell = cells.trailing_zeros() as usize;
        let bit = 1u128 << cell;
        let mut boundary = edges.expand(bit) & !marked;
        let mut seed = 81;
        while boundary != 0 {
            let neighbor = boundary.trailing_zeros() as usize;
            seed = seed.min(distances[neighbor].saturating_add(1));
            boundary &= boundary - 1;
        }
        if seed < 81 {
            buckets[usize::from(seed)] |= bit;
            pending |= 1u128 << seed;
        }
        cells &= cells - 1;
    }
    let mut unsettled = marked;
    while pending != 0 {
        let distance = pending.trailing_zeros() as usize;
        pending &= pending - 1;
        let frontier = buckets[distance] & unsettled;
        if frontier == 0 {
            continue;
        }
        unsettled &= !frontier;
        cells = frontier;
        while cells != 0 {
            distances[cells.trailing_zeros() as usize] = distance as u8;
            cells &= cells - 1;
        }
        // Only settled marked cells are inspected, not an81-cell post-map scan.
        cells = frontier;
        while cells != 0 {
            let cell = cells.trailing_zeros() as u8;
            let bit = 1u128 << cell;
            let open = edges.expand(bit);
            for (direction, neighbor) in neighbors(cell).into_iter().enumerate() {
                if let Some(neighbor) = neighbor
                    && open & (1u128 << neighbor) != 0
                    && usize::from(distances[usize::from(neighbor)]) + 1 == distance
                {
                    descent[direction] |= bit;
                }
            }
            cells &= cells - 1;
        }
        if distance < 80 {
            let next = edges.expand(frontier) & unsettled;
            if next != 0 {
                buckets[distance + 1] |= next;
                pending |= 1u128 << (distance + 1);
            }
        }
    }
    // Unmarked distances cannot decrease after edge deletion. Any former
    // unmarked descent into a marked cell was cleared during invalidation;
    // the strictly-increased repaired value cannot create a new such descent.
    // Still-unsettled cells remain81 with no supports.
}

#[cfg(test)]
#[path = "distance_geometry_tests.rs"]
mod tests;

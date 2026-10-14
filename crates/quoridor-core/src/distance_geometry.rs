//! Exact immutable cached geometry with a bounded label repair, no bucket array.
use super::{Position, WallEdges, neighbors};

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct WallDistanceGeometry {
    horizontal: u64,
    vertical: u64,
    edges: WallEdges,
    distances: [[u8; 81]; 2],
    descent: [[u128; 4]; 2],
}

// One source-work policy, not a measured time crossover. A small repair has at
// most m(m+1)/2 unsettled-label visits plus16m neighbor/support operations.
// Use it only while that bound is <= the81-cell full-row preparation size.
// Thus m<=4; no sweep, heap,81-bucket initialization or generation machinery.
const PARTIAL_WORK_BUDGET: u32 = 81;

fn partial_work(marked: u128) -> bool {
    let count = marked.count_ones();
    count * (count + 1) / 2 + 16 * count <= PARTIAL_WORK_BUDGET
}

/// Source cells whose N/S/E/W open edge points into `lower`. Also serves full
/// BFS layer construction, so repair never derives individual neighbors again
/// at settlement. The union is precisely the undirected open-edge expansion.
pub(super) fn descent_sources(edges: &WallEdges, lower: u128) -> [u128; 4] {
    const BOARD: u128 = (1u128 << 81) - 1;
    const COL8: u128 = (1u128 << 8)
        | (1u128 << 17)
        | (1u128 << 26)
        | (1u128 << 35)
        | (1u128 << 44)
        | (1u128 << 53)
        | (1u128 << 62)
        | (1u128 << 71)
        | (1u128 << 80);
    [
        ((lower & !edges.south) << 9) & BOARD,
        (lower >> 9) & !edges.south,
        (lower >> 1) & !edges.east & !COL8,
        ((lower & !edges.east & !COL8) << 1) & BOARD,
    ]
}

impl WallDistanceGeometry {
    pub(super) fn of(position: Position) -> Self {
        let edges = WallEdges::of(position);
        let first = edges.distance_map_and_descent(0);
        let second = edges.distance_map_and_descent(1);
        Self {
            horizontal: position.horizontal,
            vertical: position.vertical,
            edges,
            distances: [first.0, second.0],
            descent: [first.1, second.1],
        }
    }

    pub fn distances(&self) -> &[[u8; 81]; 2] {
        &self.distances
    }

    pub fn distances_for(&self, position: Position) -> Option<&[[u8; 81]; 2]> {
        (self.horizontal == position.horizontal && self.vertical == position.vertical)
            .then_some(&self.distances)
    }

    /// Only a genuine immutable parent's strictly one H/V wall-bit addition.
    /// Game/accumulator validity remains the existing caller's responsibility.
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
        let edges = self.edges.with_wall(horizontal, anchor);
        // Decide each row before copying its parent distances. Full fallback
        // does no small-region label preparation or whole-parent clone.
        let first = self.updated_row(0, &edges, removed);
        let second = self.updated_row(1, &edges, removed);
        Some(Self {
            horizontal: after.horizontal,
            vertical: after.vertical,
            edges,
            distances: [first.0, second.0],
            descent: [first.1, second.1],
        })
    }

    fn updated_row(
        &self,
        player: usize,
        edges: &WallEdges,
        removed: [u128; 4],
    ) -> ([u8; 81], [u128; 4]) {
        let mut descent = self.descent[player];
        let marked = invalidate(&mut descent, removed);
        if !partial_work(marked) {
            return edges.distance_map_and_descent(player);
        }
        let mut distances = self.distances[player];
        if marked != 0 {
            repair_small(edges, &mut distances, &mut descent, marked);
        }
        (distances, descent)
    }
}

fn supported(descent: &[u128; 4]) -> u128 {
    descent[0] | descent[1] | descent[2] | descent[3]
}

fn invalidate(descent: &mut [u128; 4], removed: [u128; 4]) -> u128 {
    let mut lost = 0;
    for direction in 0..4 {
        lost |= descent[direction] & removed[direction];
        descent[direction] &= !removed[direction];
    }
    let mut frontier = lost & !supported(descent);
    let mut marked = frontier;
    while frontier != 0 {
        if !partial_work(marked) {
            return marked;
        }
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

/// Unmarked distances are exact boundaries. Candidate labels live in the
/// required output row; only a pending bitmask is additional scratch. At most
/// four cells take this path. Unequal seeds are always popped by minimum label.
fn repair_small(
    edges: &WallEdges,
    distances: &mut [u8; 81],
    descent: &mut [u128; 4],
    marked: u128,
) {
    for direction in descent.iter_mut() {
        *direction &= !marked;
    }
    let mut cells = marked;
    while cells != 0 {
        let cell = cells.trailing_zeros() as u8;
        let bit = 1u128 << cell;
        let open = edges.expand(bit) & !marked;
        let mut best = 81;
        let mut directions = 0u8;
        // One scan combines initial label, boundary and supporting directions.
        for (direction, neighbor) in neighbors(cell).into_iter().enumerate() {
            if let Some(neighbor) = neighbor
                && open & (1u128 << neighbor) != 0
            {
                let seed = distances[usize::from(neighbor)].saturating_add(1);
                if seed < best {
                    best = seed;
                    directions = 0;
                }
                if seed == best && seed < 81 {
                    directions |= 1 << direction;
                }
            }
        }
        distances[usize::from(cell)] = best;
        for (direction, links) in descent.iter_mut().enumerate() {
            if directions & (1 << direction) != 0 {
                *links |= bit;
            }
        }
        cells &= cells - 1;
    }
    let mut pending = marked;
    while pending != 0 {
        let mut minimum = 81;
        let mut frontier = 0;
        cells = pending;
        while cells != 0 {
            let bit = 1u128 << cells.trailing_zeros();
            let value = distances[cells.trailing_zeros() as usize];
            if value < minimum {
                minimum = value;
                frontier = 0;
            }
            if value == minimum && value < 81 {
                frontier |= bit;
            }
            cells &= cells - 1;
        }
        if minimum == 81 {
            break;
        }
        pending &= !frontier;
        let sources = descent_sources(edges, frontier);
        let adjacent = (sources[0] | sources[1] | sources[2] | sources[3]) & pending;
        let next = minimum + 1;
        let mut accepted = 0;
        cells = adjacent;
        while cells != 0 {
            let cell = cells.trailing_zeros() as usize;
            let bit = 1u128 << cell;
            if next < distances[cell] {
                distances[cell] = next;
                for links in descent.iter_mut() {
                    *links &= !bit;
                }
            }
            if next == distances[cell] && next < 81 {
                accepted |= bit;
            }
            cells &= cells - 1;
        }
        // The same frontier routes supply relaxation and all equal-best links.
        // No settled-cell neighbor reconstruction or distance assignment scan.
        for direction in 0..4 {
            descent[direction] |= sources[direction] & accepted;
        }
    }
    // Still81 cells have no support. An actually invalidated finite old-DAG
    // vertex increases strictly; cleared unmarked->marked old descents cannot
    // become new descents after deleting edges. No unmarked post-map scan.
}

#[cfg(test)]
#[path = "distance_geometry398_tests.rs"]
mod tests;

export const PITCH = 1;
export type Orientation = 'horizontal' | 'vertical';
export type Target = { kind: 'pawn'; id: number } | { kind: 'wall'; id: number; anchor: number; orientation: Orientation };

export function cellPoint(cell: number): { x: number; z: number } {
  return { x: (cell % 9 - 4) * PITCH, z: (4 - Math.floor(cell / 9)) * PITCH };
}
export function wallPoint(anchor: number): { x: number; z: number } {
  return { x: (anchor % 8 - 3.5) * PITCH, z: (3.5 - Math.floor(anchor / 8)) * PITCH };
}
export function targetFromPlane(x: number, z: number, mode: 'move' | 'wall', orientation: Orientation): Target | null {
  if (Math.abs(x) > 4.5 || Math.abs(z) > 4.5) return null;
  if (mode === 'move') {
    const col = Math.round(x / PITCH + 4);
    const row = Math.round(4 - z / PITCH);
    return col >= 0 && col < 9 && row >= 0 && row < 9 ? { kind: 'pawn', id: row * 9 + col } : null;
  }
  const col = Math.round(x / PITCH + 3.5);
  const row = Math.round(3.5 - z / PITCH);
  if (col < 0 || col > 7 || row < 0 || row > 7) return null;
  const anchor = row * 8 + col;
  return { kind: 'wall', anchor, orientation, id: (orientation === 'horizontal' ? 81 : 145) + anchor };
}

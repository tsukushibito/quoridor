import * as THREE from 'three/webgpu';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { TabletopAssets } from './tabletop-assets';
import type { GameView } from '@quoridor/engine-bridge';
import { cellPoint, wallPoint, type Target } from './board-coordinates';

export const GI_STATIC = 1;
export const AO_GEOMETRY = 2;
const TILE_TOP = 0.14;
const TILE_THICKNESS = 0.16;
const PAWN_FOOT_RADIUS = 0.29;
const wallKey = (orientation: 'horizontal' | 'vertical', anchor: number): string => `${orientation}:${anchor}`;
function mark(mesh: THREE.Mesh, kind: string, isStatic: boolean): THREE.Mesh {
  mesh.userData.kind = kind;
  if (isStatic) mesh.layers.enable(GI_STATIC);
  if (['board', 'wall', 'pawn', 'table'].includes(kind)) mesh.layers.enable(AO_GEOMETRY);
  return mesh;
}

export class BoardScene {
  readonly scene = new THREE.Scene();
  readonly camera = new THREE.PerspectiveCamera(38, 1, 0.1, 100);
  private readonly walls = new Map<string, THREE.Mesh>();
  private readonly pawns: THREE.Group[] = [];
  private readonly hints = new THREE.Group();
  private readonly wallGeometry = new RoundedBoxGeometry(1.84, 0.66, 0.16, 2, 0.025);
  private readonly wallMaterial = new THREE.MeshPhysicalMaterial({ color: '#fff0cf', metalness: 0, roughness: 0.68, clearcoat: 0.16, clearcoatRoughness: 0.45 });
  readonly assets: TabletopAssets;
  private readonly hintGeometry = new THREE.TorusGeometry(0.27, 0.055, 8, 28);
  private readonly hintMaterial = new THREE.MeshBasicMaterial({ color: '#52d5bd' });
  private readonly previewPawn = mark(new THREE.Mesh(new THREE.TorusGeometry(0.39, 0.065, 8, 32),
    new THREE.MeshBasicMaterial({ color: '#54d5b5' })), 'preview', false);
  private readonly previewWall = mark(new THREE.Mesh(this.wallGeometry,
    new THREE.MeshStandardMaterial({ color: '#54d5b5', transparent: true, opacity: 0.72, depthWrite: false })), 'preview', false);

  constructor() {
    this.scene.background = new THREE.Color('#30251e');
    this.camera.position.set(11, 14, 17);
    this.camera.lookAt(0, 0, 0);
    this.camera.layers.enable(GI_STATIC);
    const finish = (color: string, roughness: number, clearcoat: number): THREE.MeshPhysicalMaterial =>
      new THREE.MeshPhysicalMaterial({ color, roughness, metalness: 0, clearcoat, clearcoatRoughness: 0.36 });
    const edge = finish('#684139', 0.47, 0.35);
    const insetWood = finish('#79473a', 0.56, 0.22);
    const tileWood = finish('#51403a', 0.48, 0.32);
    const pawnPaint = [finish('#257887', 0.43, 0.38), finish('#b84e35', 0.43, 0.38)];
    const tableWood = finish('#ad8257', 0.62, 0.18);
    // All box UVs use local/world distances, so fibers don't stretch with object size.
    const box = (w: number, h: number, d: number, radius: number, x = 0, z = 0): THREE.BufferGeometry => {
      const geometry = new RoundedBoxGeometry(w, h, d, 2, radius);
      const positions = geometry.getAttribute('position'), normals = geometry.getAttribute('normal'), uv = geometry.getAttribute('uv');
      for (let i = 0; i < positions.count; i++) {
        const nx = Math.abs(normals.getX(i)), ny = Math.abs(normals.getY(i)), nz = Math.abs(normals.getZ(i));
        const u = nx > ny && nx > nz ? positions.getZ(i) + z : positions.getX(i) + x;
        const v = ny >= nx && ny >= nz ? positions.getZ(i) + z : positions.getY(i);
        uv.setXY(i, u / 4.5, v / 4.5);
      }
      return geometry;
    };
    const base = mark(new THREE.Mesh(box(10.5, 0.45, 10.5, 0.14), edge), 'board', true);
    base.position.y = -0.42; base.castShadow = true; base.receiveShadow = true;
    this.scene.add(base);
    const inset = mark(new THREE.Mesh(box(9.7, 0.16, 9.7, 0.045), insetWood), 'board', true);
    inset.position.y = -0.10; inset.receiveShadow = true;
    this.scene.add(inset);
    for (let row = 0; row < 9; row++) for (let col = 0; col < 9; col++) {
      const tile = mark(new THREE.Mesh(box(0.88, TILE_THICKNESS, 0.88, 0.035, col - 4, 4 - row), tileWood), 'board', true);
      tile.position.set(col - 4, TILE_TOP - TILE_THICKNESS / 2, 4 - row);
      tile.castShadow = true; tile.receiveShadow = true;
      this.scene.add(tile);
    }
    const footHeight = 0.10;
    const footGeometries = [32, 6].map(segments => new THREE.CylinderGeometry(0.25, PAWN_FOOT_RADIUS, footHeight, segments));
    const pawnProfile = [[0.20, 0], [0.24, 0.04], [0.23, 0.12], [0.18, 0.32], [0.10, 0.48],
      [0.10, 0.53], [0.17, 0.58], [0.20, 0.67], [0.18, 0.75], [0.10, 0.82], [0, 0.85]];
    const bodyGeometries = [40, 6].map(segments =>
      new THREE.LatheGeometry(pawnProfile.map(([r, y]) => new THREE.Vector2(r, y)), segments));
    for (let player = 0; player < 2; player++) {
      const group = new THREE.Group();
      const foot = mark(new THREE.Mesh(footGeometries[player], pawnPaint[player]), 'pawn', false);
      foot.position.y = TILE_TOP + footHeight / 2; foot.castShadow = true; foot.receiveShadow = true; group.add(foot);
      const body = mark(new THREE.Mesh(bodyGeometries[player], pawnPaint[player]), 'pawn', false);
      body.position.y = TILE_TOP + footHeight; body.castShadow = true; body.receiveShadow = true; group.add(body);
      this.pawns.push(group); this.scene.add(group);
    }
    // A decorative starting position before an authoritative game is created.
    this.setPawn(0, 4); this.setPawn(1, 76);
    // The board bottom is -0.645; the finite table top touches it exactly.
    const tabletop = mark(new THREE.Mesh(box(24, 0.65, 18, 0.15), tableWood), 'table', false);
    tabletop.position.y = -0.97; tabletop.receiveShadow = true; tabletop.castShadow = true;
    this.scene.add(tabletop);
    const legGeometry = box(1.1, 27, 1.1, 0.08);
    for (const x of [-10, 10]) for (const z of [-7, 7]) {
      const leg = mark(new THREE.Mesh(legGeometry, tableWood), 'table', false);
      leg.position.set(x, -14.75, z); leg.castShadow = true; leg.receiveShadow = true;
      this.scene.add(leg);
    }
    const fallback = new THREE.AmbientLight('#e5c5a3', 1.05);
    this.scene.add(fallback);
    // The HDR loader sets direction/color only after finding an upper-hemisphere source.
    const key = new THREE.DirectionalLight('#ffffff', 0);
    key.castShadow = true;
    key.shadow.mapSize.set(2048, 2048);
    Object.assign(key.shadow.camera, { left: -8, right: 8, top: 8, bottom: -8, near: 0.1, far: 40 });
    key.shadow.camera.updateProjectionMatrix();
    key.shadow.bias = -0.0001;
    key.shadow.normalBias = 0.012;
    key.shadow.radius = 5;
    // Keep depth-only shadow draws independent of diagnostic / AO camera layers.
    key.shadow.camera.layers.set(AO_GEOMETRY);
    this.scene.add(key, key.target);
    this.assets = new TabletopAssets(this.scene, [edge, insetWood, tileWood, this.wallMaterial, ...pawnPaint, tableWood], fallback, key);
    this.scene.add(this.hints, this.previewPawn, this.previewWall);
    this.previewPawn.rotation.x = -Math.PI / 2;
    this.previewPawn.visible = false; this.previewWall.visible = false;
  }
  setPawn(player: number, cell: number): void {
    const point = cellPoint(cell);
    this.pawns[player]?.position.set(point.x, 0, point.z);
  }
  setPawnInterpolated(player: number, from: number, to: number, progress: number): void {
    const a = cellPoint(from), b = cellPoint(to);
    this.pawns[player]?.position.set(a.x + (b.x - a.x) * progress, Math.sin(progress * Math.PI) * 0.17,
      a.z + (b.z - a.z) * progress);
  }
  private createWall(orientation: 'horizontal' | 'vertical', anchor: number, staticLayer: boolean): THREE.Mesh {
    const mesh = mark(new THREE.Mesh(this.wallGeometry, this.wallMaterial), 'wall', staticLayer);
    const point = wallPoint(anchor);
    mesh.position.set(point.x, 0.38, point.z);
    mesh.rotation.y = orientation === 'horizontal' ? 0 : Math.PI / 2;
    mesh.castShadow = true; mesh.receiveShadow = true;
    this.scene.add(mesh);
    return mesh;
  }
  sync(view: GameView, deferredWall?: string): void {
    view.pawns.forEach((cell, player) => this.setPawn(player, cell));
    const needed = new Set<string>();
    for (const [orientation, anchors] of [['horizontal', view.horizontalWalls], ['vertical', view.verticalWalls]] as const) {
      for (const anchor of anchors) {
        const key = wallKey(orientation, anchor);
        needed.add(key);
        if (!this.walls.has(key)) this.walls.set(key, this.createWall(orientation, anchor, key !== deferredWall));
        const mesh = this.walls.get(key)!;
        mesh.scale.y = key === deferredWall ? 0.04 : 1;
        if (key === deferredWall) mesh.layers.disable(GI_STATIC); else mesh.layers.enable(GI_STATIC);
      }
    }
    for (const [key, mesh] of this.walls) if (!needed.has(key)) { this.scene.remove(mesh); this.walls.delete(key); }
  }
  animateWall(orientation: 'horizontal' | 'vertical', anchor: number, progress: number): void {
    const mesh = this.walls.get(wallKey(orientation, anchor));
    if (mesh) mesh.scale.y = Math.max(0.04, progress);
  }
  finalizeWall(orientation: 'horizontal' | 'vertical', anchor: number): void {
    const mesh = this.walls.get(wallKey(orientation, anchor));
    if (mesh) { mesh.scale.y = 1; mesh.layers.enable(GI_STATIC); }
  }
  setHints(view: GameView | null, show: boolean): void {
    this.hints.clear();
    if (!view || !show || view.winner !== null) return;
    for (let cell = 0; cell < 81; cell++) if (view.legalMask[cell] === 1) {
      const hint = mark(new THREE.Mesh(this.hintGeometry, this.hintMaterial), 'hint', false);
      const point = cellPoint(cell);
      hint.position.set(point.x, 0.17, point.z); hint.rotation.x = -Math.PI / 2;
      this.hints.add(hint);
    }
  }
  setPreview(target: Target | null, legal: boolean): void {
    this.previewPawn.visible = false; this.previewWall.visible = false;
    if (!target) return;
    const color = legal ? '#54d5b5' : '#e88472';
    if (target.kind === 'pawn') {
      const point = cellPoint(target.id);
      this.previewPawn.position.set(point.x, 0.19, point.z);
      (this.previewPawn.material as THREE.MeshBasicMaterial).color.set(color);
      this.previewPawn.visible = true;
    } else {
      const point = wallPoint(target.anchor);
      this.previewWall.position.set(point.x, 0.38, point.z);
      this.previewWall.rotation.y = target.orientation === 'horizontal' ? 0 : Math.PI / 2;
      (this.previewWall.material as THREE.MeshStandardMaterial).color.set(color);
      this.previewWall.visible = true;
    }
  }
  diagnostics(): { board: number; walls: number; pawns: number; previews: number; hints: number; staticWalls: number; nonWallStatic: number; canvasLayer: number } {
    const counts = { board: 0, walls: 0, pawns: 0, previews: 0, hints: 0, staticWalls: 0, nonWallStatic: 0, canvasLayer: GI_STATIC };
    this.scene.traverse(object => {
      if (!(object instanceof THREE.Mesh)) return;
      const kind = object.userData.kind as string | undefined;
      if (kind === 'board') counts.board++;
      if (kind === 'wall') { counts.walls++; if (object.layers.isEnabled(GI_STATIC)) counts.staticWalls++; }
      if (kind !== 'wall' && kind !== 'board' && object.layers.isEnabled(GI_STATIC)) counts.nonWallStatic++;
      if (kind === 'pawn') counts.pawns++;
      if (kind === 'preview' && object.visible) counts.previews++;
      if (kind === 'hint') counts.hints++;
    });
    return counts;
  }
  dispose(): void {
    this.assets.dispose();
    const geometries = new Set<THREE.BufferGeometry>();
    const materials = new Set<THREE.Material>();
    this.scene.traverse(object => {
      if (object instanceof THREE.DirectionalLight || object instanceof THREE.SpotLight) object.shadow.dispose();
      if (!(object instanceof THREE.Mesh)) return;
      geometries.add(object.geometry);
      const material = object.material;
      if (Array.isArray(material)) material.forEach(item => materials.add(item)); else materials.add(material);
    });
    geometries.add(this.wallGeometry);
    materials.add(this.wallMaterial);
    geometries.add(this.hintGeometry);
    materials.add(this.hintMaterial);
    geometries.forEach(item => item.dispose()); materials.forEach(item => item.dispose());
    this.scene.clear(); this.walls.clear(); this.pawns.length = 0;
  }
}
export { wallKey };

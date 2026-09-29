import * as THREE from 'three/webgpu';
import type { GameView } from '@quoridor/engine-bridge';
import { cellPoint, wallPoint, type Target } from './board-coordinates';

export const GI_STATIC = 1;
const wallKey = (orientation: 'horizontal' | 'vertical', anchor: number): string => `${orientation}:${anchor}`;
function mark(mesh: THREE.Mesh, kind: string, isStatic: boolean): THREE.Mesh {
  mesh.userData.kind = kind;
  if (isStatic) mesh.layers.enable(GI_STATIC);
  return mesh;
}

export class BoardScene {
  readonly scene = new THREE.Scene();
  readonly camera = new THREE.PerspectiveCamera(38, 1, 0.1, 100);
  private readonly walls = new Map<string, THREE.Mesh>();
  private readonly pawns: THREE.Group[] = [];
  private readonly hints = new THREE.Group();
  private readonly wallGeometry = new THREE.BoxGeometry(1.84, 0.66, 0.16);
  private readonly wallMaterial = new THREE.MeshStandardMaterial({ color: '#c8a36e', metalness: 0.25, roughness: 0.58 });
  private readonly hintGeometry = new THREE.TorusGeometry(0.27, 0.055, 8, 28);
  private readonly hintMaterial = new THREE.MeshBasicMaterial({ color: '#52d5bd' });
  private readonly previewPawn = mark(new THREE.Mesh(new THREE.TorusGeometry(0.39, 0.065, 8, 32),
    new THREE.MeshBasicMaterial({ color: '#54d5b5' })), 'preview', false);
  private readonly previewWall = mark(new THREE.Mesh(this.wallGeometry,
    new THREE.MeshStandardMaterial({ color: '#54d5b5', transparent: true, opacity: 0.72, depthWrite: false })), 'preview', false);

  constructor() {
    this.scene.background = new THREE.Color('#111b24');
    this.camera.position.set(11, 14, 17);
    this.camera.lookAt(0, 0, 0);
    this.camera.layers.enable(GI_STATIC);
    const edge = new THREE.MeshStandardMaterial({ color: '#241f22', roughness: 0.75 });
    const wood = new THREE.MeshStandardMaterial({ color: '#5c3c2c', roughness: 0.85 });
    const tileLight = new THREE.MeshStandardMaterial({ color: '#d8c6a1', roughness: 0.87 });
    const tileDark = new THREE.MeshStandardMaterial({ color: '#bba982', roughness: 0.89 });
    const base = mark(new THREE.Mesh(new THREE.BoxGeometry(10.5, 0.45, 10.5), edge), 'board', true);
    base.position.y = -0.42;
    this.scene.add(base);
    const inset = mark(new THREE.Mesh(new THREE.BoxGeometry(9.7, 0.16, 9.7), wood), 'board', true);
    inset.position.y = -0.12;
    this.scene.add(inset);
    const tileGeometry = new THREE.BoxGeometry(0.88, 0.16, 0.88);
    for (let row = 0; row < 9; row++) for (let col = 0; col < 9; col++) {
      const tile = mark(new THREE.Mesh(tileGeometry, (row + col) % 2 ? tileDark : tileLight), 'board', true);
      tile.position.set(col - 4, 0.06, 4 - row);
      tile.receiveShadow = true;
      this.scene.add(tile);
    }
    const blue = new THREE.MeshStandardMaterial({ color: '#1f87a5', roughness: 0.42 });
    const coral = new THREE.MeshStandardMaterial({ color: '#dc785a', roughness: 0.42 });
    const brass = new THREE.MeshStandardMaterial({ color: '#bd9659', metalness: 0.5, roughness: 0.4 });
    for (let player = 0; player < 2; player++) {
      const group = new THREE.Group();
      const foot = mark(new THREE.Mesh(new THREE.CylinderGeometry(0.28, 0.38, 0.18, 32), brass), 'pawn', false);
      foot.position.y = 0.25; foot.castShadow = true; group.add(foot);
      const body = mark(player === 0
        ? new THREE.Mesh(new THREE.SphereGeometry(0.33, 24, 20), blue)
        : new THREE.Mesh(new THREE.ConeGeometry(0.34, 0.68, 6), coral), 'pawn', false);
      body.position.y = player === 0 ? 0.58 : 0.66;
      body.castShadow = true; group.add(body);
      this.pawns.push(group); this.scene.add(group);
    }
    const plane = mark(new THREE.Mesh(new THREE.PlaneGeometry(200, 200),
      new THREE.MeshStandardMaterial({ color: '#172633', roughness: 1 })), 'floor', false);
    plane.rotation.x = -Math.PI / 2; plane.position.y = -0.68; plane.receiveShadow = true; this.scene.add(plane);
    const light = new THREE.DirectionalLight('#fff0d5', 3.2);
    light.position.set(-5, 12, 7); light.castShadow = true; light.shadow.mapSize.set(1024, 1024);
    light.shadow.camera.left = -12; light.shadow.camera.right = 12;
    light.shadow.camera.top = 12; light.shadow.camera.bottom = -12;
    this.scene.add(light, new THREE.AmbientLight('#b3c7df', 1.25));
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
    mesh.castShadow = true;
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
    const geometries = new Set<THREE.BufferGeometry>();
    const materials = new Set<THREE.Material>();
    this.scene.traverse(object => {
      if (!(object instanceof THREE.Mesh)) return;
      geometries.add(object.geometry);
      const material = object.material;
      if (Array.isArray(material)) material.forEach(item => materials.add(item)); else materials.add(material);
    });
    geometries.add(this.hintGeometry);
    materials.add(this.hintMaterial);
    geometries.forEach(item => item.dispose()); materials.forEach(item => item.dispose());
    this.scene.clear(); this.walls.clear(); this.pawns.length = 0;
  }
}
export { wallKey };

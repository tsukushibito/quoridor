import * as THREE from 'three/webgpu';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import type { GameView } from '@quoridor/engine-bridge';
import { BoardScene, wallKey } from './board-scene';
import { cellPoint, wallPoint } from './board-coordinates';

export type Backend = 'webgpu' | 'webgl2' | 'unknown';
export type RendererFault = 'deviceLost' | 'backendError' | 'renderError';
type Tween = { started: number; duration: number; update: (fraction: number) => void; complete: () => void };
export class BoardRenderer {
  readonly board = new BoardScene();
  readonly renderer = new THREE.WebGPURenderer({ antialias: true,
    forceWebGL: new URLSearchParams(location.search).get('forceWebGL') === '1' });
  readonly canvas = this.renderer.domElement;
  readonly controls: OrbitControls;
  backend: Backend = 'unknown';
  private readonly resizeObserver: ResizeObserver;
  private readonly ray = new THREE.Raycaster();
  private readonly pickPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), -0.17);
  private frame = 0;
  private tween: Tween | null = null;
  private disposed = false;
  private faulted = false;
  private reducedMotion = false;

  private constructor(private readonly element: HTMLElement,
    private readonly onFault: (kind: RendererFault) => void) {
    // Renderer r186 calls these for both WebGPU device loss and WebGL context loss.
    this.renderer.onDeviceLost = () => this.fail('deviceLost');
    this.renderer.onError = () => this.fail('backendError');
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
    this.renderer.shadowMap.enabled = true;
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.canvas.setAttribute('tabindex', '0');
    this.canvas.style.touchAction = 'none';
    this.element.appendChild(this.canvas);
    this.controls = new OrbitControls(this.board.camera, this.canvas);
    this.controls.enableDamping = true;
    this.controls.enablePan = false;
    this.controls.minDistance = 10;
    this.controls.maxDistance = 32;
    this.controls.minPolarAngle = 0.35;
    this.controls.maxPolarAngle = 1.43;
    this.controls.mouseButtons.LEFT = THREE.MOUSE.PAN;
    this.controls.mouseButtons.RIGHT = THREE.MOUSE.ROTATE;
    this.resizeObserver = new ResizeObserver(() => this.resize());
    this.resizeObserver.observe(element);
  }
  static async create(element: HTMLElement, onFault: (kind: RendererFault) => void = () => {}): Promise<BoardRenderer> {
    const board = new BoardRenderer(element, onFault);
    try {
      await board.renderer.init();
      board.resize();
      if (board.faulted) throw new Error('Renderer failed during initialization');
      board.backend = board.renderer.coordinateSystem === THREE.WebGPUCoordinateSystem ? 'webgpu'
        : board.renderer.coordinateSystem === THREE.WebGLCoordinateSystem ? 'webgl2' : 'unknown';
      board.loop();
      return board;
    } catch (error) { board.dispose(); throw error; }
  }
  private resize(): void {
    if (this.disposed || this.faulted) return;
    try {
      const width = Math.max(1, this.element.clientWidth), height = Math.max(1, this.element.clientHeight);
      this.board.camera.aspect = width / height;
      this.board.camera.updateProjectionMatrix();
      this.renderer.setSize(width, height);
    } catch { this.fail('renderError'); }
  }
  private loop = (): void => {
    if (this.disposed || this.faulted) return;
    try {
      this.controls.update();
      if (this.tween) {
        const current = this.tween;
        const fraction = Math.min(1, (performance.now() - current.started) / current.duration);
        current.update(fraction);
        if (fraction >= 1 && this.tween === current) {
          this.tween = null;
          current.complete();
        }
      }
      this.renderer.render(this.board.scene, this.board.camera);
      this.frame = requestAnimationFrame(this.loop);
    } catch { this.fail('renderError'); }
  };
  private fail(kind: RendererFault): void {
    if (this.disposed || this.faulted) return;
    this.faulted = true;
    this.cancelAnimation();
    cancelAnimationFrame(this.frame);
    this.onFault(kind);
  }
  setReducedMotion(value: boolean): void { this.reducedMotion = value; }
  setView(view: GameView): void { this.cancelAnimation(); this.board.sync(view); }
  setHints(view: GameView | null, enabled: boolean): void { this.board.setHints(view, enabled); }
  setPreview(target: Parameters<BoardScene['setPreview']>[0], legal: boolean): void { this.board.setPreview(target, legal); }
  cancelAnimation(): void { this.tween = null; }
  animate(before: GameView, after: GameView, actionId: number, complete: () => void): void {
    this.cancelAnimation();
    const player = before.turn;
    const isWall = actionId >= 81;
    const orientation = actionId < 145 ? 'horizontal' : 'vertical';
    const anchor = actionId < 145 ? actionId - 81 : actionId - 145;
    this.board.sync(after, isWall ? wallKey(orientation, anchor) : undefined);
    if (!isWall) this.board.setPawn(player, before.pawns[player]!);
    const finish = (): void => {
      if (isWall) this.board.finalizeWall(orientation, anchor);
      else this.board.setPawn(player, after.pawns[player]!);
      complete();
    };
    if (this.reducedMotion || matchMedia('(prefers-reduced-motion: reduce)').matches) { finish(); return; }
    this.tween = { started: performance.now(), duration: 190,
      update: fraction => {
        if (isWall) this.board.animateWall(orientation, anchor, fraction);
        else this.board.setPawnInterpolated(player, before.pawns[player]!, after.pawns[player]!, fraction);
      }, complete: finish };
  }
  planePoint(clientX: number, clientY: number): { x: number; z: number } | null {
    const rect = this.canvas.getBoundingClientRect();
    if (clientX < rect.left || clientX > rect.right || clientY < rect.top || clientY > rect.bottom) return null;
    const pointer = new THREE.Vector2((clientX - rect.left) / rect.width * 2 - 1,
      -((clientY - rect.top) / rect.height * 2 - 1));
    this.ray.setFromCamera(pointer, this.board.camera);
    const hit = this.ray.ray.intersectPlane(this.pickPlane, new THREE.Vector3());
    return hit ? { x: hit.x, z: hit.z } : null;
  }
  projectCell(cell: number): { x: number; y: number } {
    const point = cellPoint(cell); return this.project(point.x, point.z);
  }
  projectWall(anchor: number): { x: number; y: number } {
    const point = wallPoint(anchor); return this.project(point.x, point.z);
  }
  private project(x: number, z: number): { x: number; y: number } {
    const rect = this.canvas.getBoundingClientRect();
    const clip = new THREE.Vector3(x, 0.17, z).project(this.board.camera);
    return { x: rect.left + (clip.x + 1) * rect.width / 2, y: rect.top + (1 - clip.y) * rect.height / 2 };
  }
  flipCamera(): void {
    const camera = this.board.camera;
    camera.position.set(-camera.position.x, camera.position.y, -camera.position.z);
    camera.lookAt(0, 0, 0); this.controls.update();
  }
  resetCamera(): void {
    this.board.camera.position.set(11, 14, 17);
    this.board.camera.lookAt(0, 0, 0); this.controls.update();
  }
  cameraPosition(): [number, number, number] {
    return this.board.camera.position.toArray() as [number, number, number];
  }
  diagnostics(): ReturnType<BoardScene['diagnostics']> & { canvasCount: number; disposed: boolean; animating: boolean } {
    return { ...this.board.diagnostics(), canvasCount: this.element.querySelectorAll('canvas').length,
      disposed: this.disposed, animating: this.tween !== null };
  }
  dispose(): void {
    if (this.disposed) return;
    this.disposed = true;
    this.cancelAnimation(); cancelAnimationFrame(this.frame);
    this.resizeObserver.disconnect(); this.controls.dispose();
    this.board.dispose(); this.renderer.dispose(); this.canvas.remove();
  }
}

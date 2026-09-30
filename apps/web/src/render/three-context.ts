import * as THREE from 'three/webgpu';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import type { GameView } from '@quoridor/engine-bridge';
import type { TabletopAssets } from './tabletop-assets';
import { BoardScene, wallKey } from './board-scene';
import { cellPoint, wallPoint } from './board-coordinates';
import { AmbientOcclusion } from './ambient-occlusion';

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
  private animationStarted = false;
  private tween: Tween | null = null;
  private disposed = false;
  private faulted = false;
  private reducedMotion = false;
  private presetFlipped = false;
  private needsRender = true;
  private submittedFrames = 0;
  private occlusion: AmbientOcclusion | null = null;

  private constructor(private readonly element: HTMLElement,
    private readonly onFault: (kind: RendererFault) => void) {
    // Renderer r186 calls these for both WebGPU device loss and WebGL context loss.
    this.renderer.onDeviceLost = () => this.fail('deviceLost');
    this.renderer.onError = () => this.fail('backendError');
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.AgXToneMapping;
    this.renderer.toneMappingExposure = 0.9;
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFShadowMap;
    this.canvas.setAttribute('tabindex', '0');
    this.canvas.style.touchAction = 'none';
    this.element.appendChild(this.canvas);
    this.controls = new OrbitControls(this.board.camera, this.canvas);
    this.controls.addEventListener('change', () => { this.needsRender = true; });
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
      board.board.camera.position.set(0, 14, 18);
      board.resize();
      if (board.faulted) throw new Error('Renderer failed during initialization');
      board.backend = board.renderer.coordinateSystem === THREE.WebGPUCoordinateSystem ? 'webgpu'
        : board.renderer.coordinateSystem === THREE.WebGLCoordinateSystem ? 'webgl2' : 'unknown';
      board.occlusion = new AmbientOcclusion(board.renderer, board.board.scene, board.board.camera);
      board.animationStarted = true;
      await board.renderer.setAnimationLoop(board.loop);
      void board.board.assets.load(board.renderer, () => { board.needsRender = true; });
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
      this.fitCamera(this.presetDirection());
      this.needsRender = true;
    } catch (error) { console.error('Board resize failed', error); this.fail('renderError'); }
  }
  private presetDirection(): THREE.Vector3 {
    const narrow = this.element.clientWidth / Math.max(1, this.element.clientHeight) < 1;
    return new THREE.Vector3(0, narrow ? 26 : 14, (this.presetFlipped ? -1 : 1) * (narrow ? 12 : 18));
  }
  private fitCamera(direction: THREE.Vector3): void {
    const camera = this.board.camera;
    const ray = direction.clone().normalize();
    if (ray.lengthSq() < 0.5) ray.set(11, 14, 17).normalize();
    const canvas = this.canvas.getBoundingClientRect();
    const overlay = (selector: string): DOMRect | undefined =>
      this.element.ownerDocument.querySelector<HTMLElement>(selector)?.getBoundingClientRect();
    const top = Math.max(canvas.top + 10, (overlay('.status-island')?.bottom ?? canvas.top) + 10,
      (overlay('.top-actions')?.bottom ?? canvas.top) + 10);
    const bottom = Math.min(canvas.bottom - 10, (overlay('.action-hud')?.top ?? canvas.bottom) - 10);
    const left = canvas.left + 10, right = canvas.right - 10;
    const fits = (distance: number): boolean => {
      camera.position.copy(ray).multiplyScalar(distance);
      camera.lookAt(0, 0, 0);
      camera.updateMatrixWorld();
      for (const x of [-5.3, 5.3]) for (const z of [-5.3, 5.3]) for (const y of [-0.7, 1.1]) {
        const clip = new THREE.Vector3(x, y, z).project(camera);
        const px = canvas.left + (clip.x + 1) * canvas.width / 2;
        const py = canvas.top + (1 - clip.y) * canvas.height / 2;
        if (px < left || px > right || py < top || py > bottom || clip.z > 1) return false;
      }
      return true;
    };
    let near = 7, far = 60;
    for (let i = 0; i < 22; i++) {
      const middle = (near + far) / 2;
      if (fits(middle)) far = middle;
      else near = middle;
    }
    fits(far);
    this.controls.minDistance = Math.max(7, far * 0.78);
    this.controls.maxDistance = Math.max(32, far * 1.6);
    this.controls.update();
  }
  private loop = (): void => {
    if (this.disposed || this.faulted) return;
    try {
      this.controls.update();
      if (this.tween) {
        this.needsRender = true;
        const current = this.tween;
        const fraction = Math.min(1, (performance.now() - current.started) / current.duration);
        current.update(fraction);
        if (fraction >= 1 && this.tween === current) {
          this.tween = null;
          current.complete();
        }
      }
      // PBR/IBL and spatially filtered GTAO have no temporal accumulation. Keep RAF for controls/tweens,
      // but avoid submitting identical expensive frames while the board is idle.
      // VXGI/TRAA will require a separate convergence policy when enabled.
      if (this.needsRender) {
        this.needsRender = false;
        this.occlusion!.render();
        this.submittedFrames++;
      }
    } catch (error) { console.error('Board render failed', error); this.fail('renderError'); }
  };
  private fail(kind: RendererFault): void {
    if (this.disposed || this.faulted) return;
    this.faulted = true;
    this.cancelAnimation();
    if (this.animationStarted) void this.renderer.setAnimationLoop(null);
    this.onFault(kind);
  }
  setReducedMotion(value: boolean): void { this.reducedMotion = value; }
  setView(view: GameView): void { this.cancelAnimation(); this.board.sync(view); this.needsRender = true; }
  setHints(view: GameView | null, enabled: boolean): void { this.board.setHints(view, enabled); this.needsRender = true; }
  setPreview(target: Parameters<BoardScene['setPreview']>[0], legal: boolean): void {
    this.board.setPreview(target, legal); this.needsRender = true;
  }
  cancelAnimation(): void { this.tween = null; }
  animate(before: GameView, after: GameView, actionId: number, complete: () => void): void {
    this.cancelAnimation();
    const player = before.turn;
    const isWall = actionId >= 81;
    const orientation = actionId < 145 ? 'horizontal' : 'vertical';
    const anchor = actionId < 145 ? actionId - 81 : actionId - 145;
    this.board.sync(after, isWall ? wallKey(orientation, anchor) : undefined);
    this.needsRender = true;
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
  projectBoardBounds(): { left: number; top: number; right: number; bottom: number } {
    const points = [-5.3, 5.3].flatMap(x => [-5.3, 5.3].flatMap(z =>
      [-0.7, 1.1].map(y => this.project(x, z, y))));
    return { left: Math.min(...points.map(point => point.x)), top: Math.min(...points.map(point => point.y)),
      right: Math.max(...points.map(point => point.x)), bottom: Math.max(...points.map(point => point.y)) };
  }
  private project(x: number, z: number, y = 0.17): { x: number; y: number } {
    const rect = this.canvas.getBoundingClientRect();
    const clip = new THREE.Vector3(x, y, z).project(this.board.camera);
    return { x: rect.left + (clip.x + 1) * rect.width / 2, y: rect.top + (1 - clip.y) * rect.height / 2 };
  }
  flipCamera(): void {
    this.presetFlipped = !this.presetFlipped;
    this.fitCamera(this.presetDirection());
  }
  resetCamera(): void {
    this.presetFlipped = false;
    this.fitCamera(this.presetDirection());
  }
  cameraPosition(): [number, number, number] {
    return this.board.camera.position.toArray() as [number, number, number];
  }
  diagnostics(): ReturnType<BoardScene['diagnostics']> & { canvasCount: number; disposed: boolean; animating: boolean; submittedFrames: number } & ReturnType<TabletopAssets['diagnostics']> & ReturnType<AmbientOcclusion['diagnostics']> {
    return { ...this.board.diagnostics(), ...this.board.assets.diagnostics(),
      ...(this.occlusion?.diagnostics() ?? { aoEnabled: false, aoSize: [0, 0] as [number, number] }), canvasCount: this.element.querySelectorAll('canvas').length,
      disposed: this.disposed, animating: this.tween !== null, submittedFrames: this.submittedFrames };
  }
  dispose(): void {
    if (this.disposed) return;
    this.disposed = true;
    this.cancelAnimation();
    if (this.animationStarted) void this.renderer.setAnimationLoop(null);
    this.resizeObserver.disconnect(); this.controls.dispose();
    this.occlusion?.dispose();
    this.board.dispose(); this.renderer.dispose(); this.canvas.remove();
  }
}

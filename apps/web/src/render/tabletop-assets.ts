import * as THREE from 'three/webgpu';
import { HDRLoader } from 'three/addons/loaders/HDRLoader.js';
import { environmentLight, type EnvironmentLight } from './environment-light';
import { DEFAULT_ENVIRONMENT, environmentPreset, type EnvironmentId } from '../environment-presets';

export type AssetState = 'loading' | 'ready' | 'error' | 'fallback' | 'disposed';

/** Local assets are optional: a failed download must never stop a match. */
export class TabletopAssets {
  environment: AssetState = 'loading';
  wood: AssetState = 'loading';
  requestedEnvironment: EnvironmentId = DEFAULT_ENVIRONMENT;
  activeEnvironment: EnvironmentId | null = null;
  private readonly abort = new AbortController(); // Wood lifetime, independent of environment switches.
  private environmentAbort: AbortController | null = null;
  private generation = 0;
  private hdr: THREE.DataTexture | null = null;
  private renderer: THREE.WebGPURenderer | null = null;
  private onUpdate: () => void = () => {};
  private readonly textures = new Set<THREE.Texture>();
  private bitmap: ImageBitmap | null = null;
  private pmrem: THREE.RenderTarget | null = null;
  private disposed = false;
  private source: EnvironmentLight | null = null;

  constructor(private readonly scene: THREE.Scene, private readonly materials: THREE.MeshPhysicalMaterial[],
    private readonly fallbackLight: THREE.AmbientLight, private readonly keyLight: THREE.DirectionalLight) {}

  async load(renderer: THREE.WebGPURenderer, onUpdate: () => void,
    initialEnvironment: EnvironmentId = DEFAULT_ENVIRONMENT): Promise<void> {
    if (this.disposed) return;
    this.renderer = renderer;
    this.onUpdate = onUpdate;
    const timeout = window.setTimeout(() => this.abort.abort(), 10_000);
    await Promise.allSettled([this.setEnvironment(initialEnvironment),
      this.loadWood().finally(() => { if (!this.disposed) onUpdate(); })]);
    window.clearTimeout(timeout);
  }
  private async fetchAsset(path: string, signal: AbortSignal): Promise<Response> {
    const response = await fetch(`${import.meta.env.BASE_URL}${path}`, { signal });
    if (!response.ok) throw new Error(`Asset unavailable: ${path}`);
    return response;
  }
  /** Keep the last complete environment visible until the newest candidate is ready. */
  async setEnvironment(id: EnvironmentId): Promise<void> {
    if (this.disposed || !this.renderer) return;
    const generation = ++this.generation;
    this.environmentAbort?.abort();
    this.environmentAbort = null;
    this.requestedEnvironment = id;
    if (this.activeEnvironment === id) {
      this.environment = 'ready'; this.onUpdate(); return;
    }
    const abort = new AbortController();
    this.environmentAbort = abort;
    const timeout = window.setTimeout(() => abort.abort(), 10_000);
    this.environment = 'loading'; this.onUpdate();
    let hdr: THREE.DataTexture | null = null;
    let pmrem: THREE.RenderTarget | null = null;
    let generator: THREE.PMREMGenerator | null = null;
    try {
      const preset = environmentPreset(id);
      const buffer = await (await this.fetchAsset(preset.asset, abort.signal)).arrayBuffer();
      if (this.disposed || generation !== this.generation) return;
      abort.signal.throwIfAborted();
      const image = new HDRLoader().parse(buffer);
      if (!(image.data instanceof Uint16Array || image.data instanceof Float32Array) || image.width === undefined || image.height === undefined) {
        throw new Error('Unsupported HDR data');
      }
      const rotation = new THREE.Euler(0, preset.rotationY, 0);
      const source = environmentLight({ data: image.data, width: image.width, height: image.height }, rotation);
      hdr = new THREE.DataTexture(image.data, image.width, image.height, THREE.RGBAFormat, THREE.HalfFloatType);
      hdr.colorSpace = THREE.LinearSRGBColorSpace;
      hdr.mapping = THREE.EquirectangularReflectionMapping;
      hdr.minFilter = hdr.magFilter = THREE.LinearFilter;
      hdr.flipY = true;
      hdr.needsUpdate = true;
      generator = new THREE.PMREMGenerator(this.renderer);
      pmrem = generator.fromEquirectangular(hdr);
      if (this.disposed || generation !== this.generation) return;
      abort.signal.throwIfAborted();
      const previousHdr = this.hdr, previousPmrem = this.pmrem;
      // Background, reflection, and direct light are applied in the same synchronous turn.
      this.scene.background = this.scene.environment = pmrem.texture;
      this.scene.backgroundIntensity = preset.backgroundIntensity;
      this.scene.backgroundBlurriness = 0.045;
      this.scene.backgroundRotation.copy(rotation);
      this.scene.environmentRotation.copy(rotation);
      this.scene.environmentIntensity = source ? preset.environmentIntensity : 1;
      this.keyLight.intensity = source ? preset.keyIntensity : 0;
      if (source) {
        this.keyLight.position.copy(source.direction).multiplyScalar(20);
        this.keyLight.color.copy(source.color);
      }
      this.source = source;
      this.fallbackLight.intensity = 0;
      this.hdr = hdr; this.pmrem = pmrem;
      hdr = null; pmrem = null; // Ownership transferred only after successful application.
      previousHdr?.dispose(); previousPmrem?.dispose();
      this.activeEnvironment = id;
      this.environment = 'ready';
    } catch {
      if (!this.disposed && generation === this.generation)
        this.environment = this.activeEnvironment ? 'error' : 'fallback';
    } finally {
      window.clearTimeout(timeout);
      generator?.dispose(); pmrem?.dispose(); hdr?.dispose();
      if (!this.disposed && generation === this.generation) {
        this.environmentAbort = null;
        this.onUpdate();
      }
    }
  }
  private async loadWood(): Promise<void> {
    let bitmap: ImageBitmap | null = null;
    try {
      bitmap = await createImageBitmap(await (await this.fetchAsset('assets/tabletop/beech-albedo.png', this.abort.signal)).blob(),
        { colorSpaceConversion: 'none', imageOrientation: 'flipY' });
      if (this.disposed) { bitmap.close(); return; }
      this.bitmap = bitmap;
      const albedo = new THREE.Texture(bitmap);
      albedo.colorSpace = THREE.SRGBColorSpace;
      albedo.wrapS = albedo.wrapT = THREE.RepeatWrapping;
      albedo.anisotropy = 4;
      albedo.needsUpdate = true;
      this.textures.add(albedo);
      // Fine sanded fibers, not height inferred from shadows in an RGB photograph.
      const size = 256, pixels = new Uint8Array(size * size * 4);
      for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
        const grain = Math.sin(x * Math.PI * 2 * 37 / size + 0.45 * Math.sin(y * Math.PI * 2 / size));
        const value = Math.round(172 + grain * 22 + Math.sin(x * Math.PI * 2 * 61 / size) * 7);
        pixels.set([value, value, value, 255], (y * size + x) * 4);
      }
      const fibers = new THREE.DataTexture(pixels, size, size);
      fibers.wrapS = fibers.wrapT = THREE.RepeatWrapping;
      fibers.minFilter = THREE.LinearMipmapLinearFilter;
      fibers.magFilter = THREE.LinearFilter;
      fibers.generateMipmaps = true;
      fibers.needsUpdate = true;
      this.textures.add(fibers);
      for (const material of this.materials) {
        material.map = albedo;
        material.bumpMap = fibers;
        material.bumpScale = 0.008;
        material.roughnessMap = fibers;
        material.needsUpdate = true;
      }
      this.wood = 'ready';
    } catch {
      bitmap?.close();
      if (!this.disposed) this.wood = 'fallback';
    }
  }
  diagnostics() {
    return { environment: this.environment, wood: this.wood, assetTextures: this.textures.size + (this.pmrem ? 1 : 0) + (this.hdr ? 1 : 0),
      requestedEnvironment: this.requestedEnvironment, activeEnvironment: this.activeEnvironment,
      environmentIntensity: this.scene.environmentIntensity, keyIntensity: this.keyLight.intensity,
      keyDirection: this.source?.direction.toArray() ?? null, keyEnergyShare: this.source?.energyShare ?? null,
      keyShadowSize: this.keyLight.shadow.map ? [this.keyLight.shadow.map.width, this.keyLight.shadow.map.height] : null };
  }
  dispose(): void {
    if (this.disposed) return;
    this.disposed = true;
    this.abort.abort(); this.environmentAbort?.abort(); this.environmentAbort = null; ++this.generation;
    this.scene.background = null;
    this.scene.environment = null;
    this.keyLight.intensity = 0; this.source = null;
    this.pmrem?.dispose(); this.pmrem = null; this.hdr?.dispose(); this.hdr = null;
    this.activeEnvironment = null; this.renderer = null; this.onUpdate = () => {};
    this.textures.forEach(texture => texture.dispose()); this.textures.clear();
    this.bitmap?.close(); this.bitmap = null;
    this.environment = this.wood = 'disposed';
  }
}

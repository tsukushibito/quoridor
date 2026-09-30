import * as THREE from 'three/webgpu';
import { HDRLoader } from 'three/addons/loaders/HDRLoader.js';
import { environmentLight, type EnvironmentLight } from './environment-light';

export type AssetState = 'loading' | 'ready' | 'fallback' | 'disposed';

/** Local assets are optional: a failed download must never stop a match. */
export class TabletopAssets {
  environment: AssetState = 'loading';
  wood: AssetState = 'loading';
  private readonly abort = new AbortController();
  private readonly textures = new Set<THREE.Texture>();
  private bitmap: ImageBitmap | null = null;
  private pmrem: THREE.RenderTarget | null = null;
  private disposed = false;
  private source: EnvironmentLight | null = null;

  constructor(private readonly scene: THREE.Scene, private readonly materials: THREE.MeshPhysicalMaterial[],
    private readonly fallbackLight: THREE.AmbientLight, private readonly keyLight: THREE.DirectionalLight) {}

  async load(renderer: THREE.WebGPURenderer, onUpdate: () => void): Promise<void> {
    // Bound requests even if a local asset server stalls. Disposal also cancels them.
    const timeout = window.setTimeout(() => this.abort.abort(), 10_000);
    await Promise.allSettled([this.loadEnvironment(renderer).finally(onUpdate), this.loadWood().finally(onUpdate)]);
    window.clearTimeout(timeout);
  }
  private async fetchAsset(name: string): Promise<Response> {
    const response = await fetch(`${import.meta.env.BASE_URL}assets/tabletop/${name}`, { signal: this.abort.signal });
    if (!response.ok) throw new Error(`Asset unavailable: ${name}`);
    return response;
  }
  private async loadEnvironment(renderer: THREE.WebGPURenderer): Promise<void> {
    let hdr: THREE.DataTexture | null = null;
    let generator: THREE.PMREMGenerator | null = null;
    try {
      const buffer = await (await this.fetchAsset('comfy-cafe-2k.hdr')).arrayBuffer();
      if (this.disposed) return;
      const image = new HDRLoader().parse(buffer);
      if (!(image.data instanceof Uint16Array || image.data instanceof Float32Array) || image.width === undefined || image.height === undefined) {
        throw new Error('Unsupported HDR data');
      }
      hdr = new THREE.DataTexture(image.data, image.width, image.height, THREE.RGBAFormat, THREE.HalfFloatType);
      hdr.colorSpace = THREE.LinearSRGBColorSpace;
      hdr.mapping = THREE.EquirectangularReflectionMapping;
      hdr.minFilter = hdr.magFilter = THREE.LinearFilter;
      hdr.flipY = true;
      hdr.needsUpdate = true;
      generator = new THREE.PMREMGenerator(renderer);
      this.pmrem = generator.fromEquirectangular(hdr);
      this.textures.add(hdr);
      // Reuse the filtered cube for the background too. Blurring the original
      // equirectangular texture would make Three.js build a second PMREM cube.
      this.scene.background = this.pmrem.texture;
      this.scene.environment = this.pmrem.texture;
      this.scene.backgroundIntensity = 0.55;
      this.scene.backgroundBlurriness = 0.045;
      this.scene.backgroundRotation.y = Math.PI / 2;
      this.scene.environmentRotation.y = Math.PI / 2;
      this.source = environmentLight({ data: image.data, width: image.width, height: image.height }, this.scene.environmentRotation);
      this.scene.environmentIntensity = this.source ? 0.65 : 1;
      if (this.source) {
        this.keyLight.position.copy(this.source.direction).multiplyScalar(20);
        this.keyLight.color.copy(this.source.color);
        this.keyLight.intensity = 4;
      }
      this.fallbackLight.intensity = 0;
      this.environment = 'ready';
    } catch {
      hdr?.dispose();
      if (!this.disposed) this.environment = 'fallback';
    } finally { generator?.dispose(); }
  }
  private async loadWood(): Promise<void> {
    let bitmap: ImageBitmap | null = null;
    try {
      bitmap = await createImageBitmap(await (await this.fetchAsset('beech-albedo.png')).blob(),
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
  diagnostics(): { environment: AssetState; wood: AssetState; assetTextures: number; keyDirection: number[] | null; keyEnergyShare: number | null; keyShadowSize: number[] | null } {
    return { environment: this.environment, wood: this.wood, assetTextures: this.textures.size + (this.pmrem ? 1 : 0),
      keyDirection: this.source?.direction.toArray() ?? null, keyEnergyShare: this.source?.energyShare ?? null,
      keyShadowSize: this.keyLight.shadow.map ? [this.keyLight.shadow.map.width, this.keyLight.shadow.map.height] : null };
  }
  dispose(): void {
    if (this.disposed) return;
    this.disposed = true;
    this.abort.abort();
    this.scene.background = null;
    this.scene.environment = null;
    this.keyLight.intensity = 0; this.source = null;
    this.pmrem?.dispose(); this.pmrem = null;
    this.textures.forEach(texture => texture.dispose()); this.textures.clear();
    this.bitmap?.close(); this.bitmap = null;
    this.environment = this.wood = 'disposed';
  }
}

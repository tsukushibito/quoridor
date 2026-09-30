import * as THREE from 'three/webgpu';
import { builtinAOContext, mix, mrt, normalView, pass, screenUV, uniform } from 'three/tsl';
import { ao } from 'three/addons/tsl/display/GTAONode.js';
import { bilateralBlur } from 'three/addons/tsl/display/BilateralBlurNode.js';
import { AO_GEOMETRY } from './board-scene';

/** AO changes material lighting; the background and unlit move markers stay intact. */
export class AmbientOcclusion {
  private readonly prePass;
  private readonly aoPass;
  private readonly filtered;
  private readonly scenePass;
  private readonly pipeline;
  private readonly occlusionPipeline;
  private readonly preparationTarget = new THREE.RenderTarget(1, 1, { depthBuffer: false });
  private readonly preCamera;
  private disposed = false;
  private readonly strength = uniform(0.65);

  constructor(private readonly renderer: THREE.WebGPURenderer, scene: THREE.Scene, private readonly camera: THREE.PerspectiveCamera) {
    // Passes filter different layers. A separate camera keeps Three's cached render
    // lists separate when the AO dependency renders during the beauty pass.
    this.preCamera = camera.clone();
    this.prePass = pass(scene, this.preCamera, { samples: 0 });
    this.prePass.name = 'AO normals and depth';
    this.prePass.transparent = false;
    const layers = new THREE.Layers(); layers.set(AO_GEOMETRY);
    this.prePass.setLayers(layers);
    this.prePass.setMRT(mrt({ output: normalView }));
    const normal = this.prePass.getTextureNode();
    const depth = this.prePass.getTextureNode('depth');
    this.aoPass = ao(depth, normal, camera);
    this.aoPass.resolutionScale = 0.5;
    this.aoPass.radius.value = 0.45; // One board cell is one world unit.
    this.aoPass.thickness.value = 0.75;
    this.aoPass.samples.value = 16;
    this.aoPass.useTemporalFiltering = false;
    const raw = this.aoPass.getTextureNode();
    this.filtered = bilateralBlur(raw, undefined, 1, 0.1);
    this.scenePass = pass(scene, camera);
    this.scenePass.name = 'IBL with contact occlusion';
    // Keep even the most occluded corners readable, rather than multiplying the final image.
    this.scenePass.contextNode = builtinAOContext(mix(1, this.filtered.getTextureNode().sample(screenUV).r, this.strength));
    this.pipeline = new THREE.RenderPipeline(renderer);
    this.pipeline.outputNode = this.scenePass;
    // Evaluate the AO dependencies before entering the beauty scene. In particular,
    // nested passes must not overwrite screen-size uniforms while a mesh is drawn.
    this.occlusionPipeline = new THREE.RenderPipeline(renderer, this.filtered.getTextureNode());
    this.occlusionPipeline.outputColorTransform = false;
  }

  render(): void {
    this.preCamera.copy(this.camera, false);
    const previous = this.renderer.getRenderTarget();
    // The preparatory quad only needs to trigger dependencies, not fill the screen.
    this.renderer.setRenderTarget(this.preparationTarget);
    try { this.occlusionPipeline.render(); }
    finally { this.renderer.setRenderTarget(previous); }
    this.pipeline.render();
  }
  diagnostics(): { aoEnabled: boolean; aoSize: [number, number] } {
    const image = this.filtered.getTextureNode().value.image as { width: number; height: number };
    return { aoEnabled: !this.disposed, aoSize: [image.width, image.height] };
  }
  dispose(): void {
    if (this.disposed) return;
    this.disposed = true;
    this.pipeline.dispose();
    this.occlusionPipeline.dispose();
    this.preparationTarget.dispose();
    this.scenePass.dispose();
    this.filtered.dispose();
    this.aoPass.dispose();
    this.prePass.dispose();
  }
}

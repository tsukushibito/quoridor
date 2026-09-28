import * as THREE from 'three/webgpu';
import {
  builtinGIContext,
  mrt,
  normalView,
  packNormalToRGB,
  pass,
  sample,
  screenUV,
  unpackRGBToNormal,
} from 'three/tsl';
import { vxgi } from 'three/addons/lighting/vxgi/VXGINode.js';
import './style.css';

type Backend = 'webgpu' | 'webgl2' | 'unknown';
type Phase = 'initializing' | 'ready' | 'failed';

interface Diagnostics {
  phase: Phase;
  webgpuAvailable: boolean;
  webgpuAdapterAvailable: boolean;
  rendererBackend: Backend;
  vxgiEnabled: boolean;
  frameRendered: boolean;
  error?: string;
}

declare global {
  interface Window {
    __QUORIDOR_DIAGNOSTICS__?: Diagnostics;
  }
}

const diagnostics: Diagnostics = {
  phase: 'initializing',
  webgpuAvailable: Boolean(navigator.gpu),
  webgpuAdapterAvailable: false,
  rendererBackend: 'unknown',
  vxgiEnabled: false,
  frameRendered: false,
};
window.__QUORIDOR_DIAGNOSTICS__ = diagnostics;

function requiredElement<T extends Element>(selector: string): T {
  const element = document.querySelector<T>(selector);
  if (!element) throw new Error(`Smoke page element is missing: ${selector}`);
  return element;
}

const status = requiredElement<HTMLParagraphElement>('#status');
const canvasMount = requiredElement<HTMLDivElement>('#canvas');

function fail(error: unknown): void {
  diagnostics.phase = 'failed';
  diagnostics.error = error instanceof Error ? error.message : String(error);
  status.textContent = `Failed: ${diagnostics.error}`;
  console.error(error);
}

function makeScene(): { scene: THREE.Scene; camera: THREE.PerspectiveCamera } {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color('#171b24');

  const camera = new THREE.PerspectiveCamera(45, 960 / 540, 0.1, 50);
  camera.position.set(0, 3.2, 8);
  camera.lookAt(0, 1.5, 0);

  const white = new THREE.MeshPhysicalMaterial({ color: '#dedede', roughness: 0.8 });
  const red = new THREE.MeshPhysicalMaterial({ color: '#c54439', roughness: 0.8 });
  const green = new THREE.MeshPhysicalMaterial({ color: '#398d6a', roughness: 0.8 });

  const floor = new THREE.Mesh(new THREE.PlaneGeometry(7, 7), white);
  floor.rotation.x = -Math.PI / 2;
  floor.receiveShadow = true;
  scene.add(floor);

  const back = new THREE.Mesh(new THREE.PlaneGeometry(7, 4), white);
  back.position.set(0, 2, -3.5);
  back.receiveShadow = true;
  scene.add(back);

  const left = new THREE.Mesh(new THREE.PlaneGeometry(7, 4), red);
  left.rotation.y = Math.PI / 2;
  left.position.set(-3.5, 2, 0);
  left.receiveShadow = true;
  scene.add(left);

  const right = new THREE.Mesh(new THREE.PlaneGeometry(7, 4), green);
  right.rotation.y = -Math.PI / 2;
  right.position.set(3.5, 2, 0);
  right.receiveShadow = true;
  scene.add(right);

  const box = new THREE.Mesh(new THREE.BoxGeometry(1.8, 2.2, 1.8), white);
  box.position.set(-0.5, 1.1, 0.1);
  box.rotation.y = Math.PI / 7;
  box.castShadow = true;
  box.receiveShadow = true;
  scene.add(box);

  const light = new THREE.PointLight('#ffffff', 80);
  light.position.set(0.5, 3.5, 1);
  light.castShadow = true;
  light.shadow.mapSize.set(512, 512);
  scene.add(light);
  scene.add(new THREE.AmbientLight('#202020'));

  return { scene, camera };
}

async function main(): Promise<void> {
  if (navigator.gpu) {
    diagnostics.webgpuAdapterAvailable = (await navigator.gpu.requestAdapter()) !== null;
  }

  const forceWebGL = new URLSearchParams(location.search).get('forceWebGL') === '1';
  const { scene, camera } = makeScene();
  const renderer = new THREE.WebGPURenderer({ antialias: false, forceWebGL });
  renderer.setPixelRatio(1);
  renderer.setSize(960, 540);
  renderer.shadowMap.enabled = true;
  renderer.onError = fail;
  canvasMount.appendChild(renderer.domElement);

  await renderer.init();
  diagnostics.rendererBackend = renderer.coordinateSystem === THREE.WebGPUCoordinateSystem
    ? 'webgpu'
    : renderer.coordinateSystem === THREE.WebGLCoordinateSystem
      ? 'webgl2'
      : 'unknown';

  if (diagnostics.rendererBackend !== 'webgpu') {
    await renderer.renderAsync(scene, camera);
    diagnostics.frameRendered = true;
    diagnostics.phase = 'ready';
    status.textContent = `${diagnostics.rendererBackend}: scene rendered without VXGI`;
    return;
  }

  const pipeline = new THREE.RenderPipeline(renderer);
  const prePass = pass(scene, camera);
  prePass.transparent = false;
  prePass.setMRT(mrt({ output: packNormalToRGB(normalView) }));
  prePass.getTexture('output').type = THREE.UnsignedByteType;

  const normal = sample((uv) => unpackRGBToNormal(prePass.getTextureNode().sample(uv)));
  const depth = prePass.getTextureNode('depth');
  const giPass = vxgi(depth, normal, scene, camera, 32);
  giPass.useTemporalFiltering = false;

  const scenePass = pass(scene, camera);
  scenePass.contextNode = builtinGIContext(
    giPass.getAONode().sample(screenUV).r,
    giPass.getGINode().sample(screenUV).rgb,
  );
  pipeline.outputNode = scenePass;

  await pipeline.renderAsync();
  diagnostics.frameRendered = true;
  diagnostics.vxgiEnabled = true;
  diagnostics.phase = 'ready';
  status.textContent = 'WebGPU backend: VXGI frame rendered';

  renderer.setAnimationLoop(() => {
    try {
      pipeline.render();
    } catch (error) {
      renderer.setAnimationLoop(null);
      fail(error);
    }
  });
}

void main().catch(fail);

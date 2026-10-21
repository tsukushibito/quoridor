import test from 'node:test';
import assert from 'node:assert/strict';
import { loadTs } from './ts-fixture.mjs';

test('abort during actual BoardRenderer.create removes local resources and releases late backend', async () => {
  const events = [];
  let finishInit;
  const initialized = new Promise((resolve) => {
    finishInit = resolve;
  });
  class WebGPURenderer {
    domElement = {
      style: {},
      setAttribute() {},
      remove() {
        events.push('canvas-remove');
      },
    };
    shadowMap = {};
    setPixelRatio() {}
    init() {
      return initialized;
    }
    dispose() {
      events.push('renderer-dispose');
    }
  }
  class OrbitControls {
    mouseButtons = {};
    addEventListener() {}
    dispose() {
      events.push('controls-dispose');
    }
  }
  class ResizeObserver {
    observe() {}
    disconnect() {
      events.push('observer-disconnect');
    }
  }
  class BoardScene {
    camera = {};
    dispose() {
      events.push('scene-dispose');
    }
  }
  const { BoardRenderer } = await loadTs(
    new URL('../../apps/web/src/games/quoridor/render/three-context.ts', import.meta.url),
    {
      'three/webgpu': {
        WebGPURenderer,
        Raycaster: class {},
        Plane: class {},
        Vector3: class {},
        MOUSE: {},
      },
      'three/addons/controls/OrbitControls.js': { OrbitControls },
      '../environment-presets': { DEFAULT_ENVIRONMENT: 'fixture' },
      './board-scene': { BoardScene, wallKey() {} },
      './board-coordinates': { cellPoint() {}, wallPoint() {} },
      './ambient-occlusion': { AmbientOcclusion: class {} },
    },
    {
      ResizeObserver,
      devicePixelRatio: 1,
      location: { search: '' },
      URLSearchParams,
      DOMException,
    },
  );
  const lifetime = new AbortController();
  const opening = BoardRenderer.create({ appendChild() {} }, () => events.push('fault'), {
    signal: lifetime.signal,
  });
  lifetime.abort();
  assert.deepEqual(events, [
    'observer-disconnect',
    'controls-dispose',
    'scene-dispose',
    'renderer-dispose',
    'canvas-remove',
  ]);
  finishInit();
  await assert.rejects(opening, { name: 'AbortError' });
  assert.equal(events.filter((e) => e === 'renderer-dispose').length, 2);
  assert.equal(events.includes('fault'), false);
});

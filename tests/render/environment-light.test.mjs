import { test } from 'node:test';
import assert from 'node:assert/strict';
import { DataUtils, Euler, Vector3 } from 'three/webgpu';
import { environmentLight } from '../../apps/web/src/render/environment-light.ts';

function panorama() {
  const width = 128, height = 64;
  const data = new Float32Array(width * height * 4).fill(1);
  const image = { width, height, data };
  const patch = (x, y, value, size = 5) => {
    for (let dy = 0; dy < size; dy++) for (let dx = 0; dx < size; dx++) {
      const offset = ((y + dy) * width + (x + dx) % width) * 4;
      data.set([value, value, value, 1], offset);
    }
  };
  return { image, patch };
}

// Expected world directions come from geometric landmarks, rather than copying the extraction steps.
test('a source above +X rotates to -Z with the environment; lower hemisphere fill is ignored', () => {
  const { image, patch } = panorama();
  patch(62, 18, 30); patch(5, 42, 1000);
  const light = environmentLight(image, new Euler(0, Math.PI / 2, 0));
  const expected = new Vector3(0, Math.sin(Math.PI * 0.18), -Math.cos(Math.PI * 0.18));
  assert.ok(light.direction.dot(expected) > 0.995);
  assert.ok(Math.abs(light.direction.length() - 1) < 1e-10);
});

test('a source straddling the panorama seam remains one source toward -X', () => {
  const { image, patch } = panorama();
  patch(126, 18, 30);
  const light = environmentLight(image, new Euler());
  assert.ok(light.direction.x < -0.8 && light.direction.y > 0.4 && Math.abs(light.direction.z) < 0.1);
  assert.ok(light.energyShare > 0.99);
});

test('opposing lights do not average into a fictitious overhead source', () => {
  const { image, patch } = panorama();
  patch(62, 18, 30); patch(126, 18, 6);
  const light = environmentLight(image, new Euler());
  assert.ok(light.direction.x > 0.8 && light.direction.y < 0.65);
});

test('equal radiance pixel patches near the pole carry less energy than near the horizon', () => {
  const { image, patch } = panorama();
  patch(5, 0, 30); patch(62, 25, 30);
  const light = environmentLight(image, new Euler());
  assert.ok(light.direction.x > 0.9 && light.direction.y < 0.4);
});

test('decoded half float and float radiance give the same source', () => {
  const { image, patch } = panorama(); patch(62, 18, 30);
  const half = { ...image, data: Uint16Array.from(image.data, DataUtils.toHalfFloat) };
  assert.ok(environmentLight(image, new Euler()).direction.distanceTo(environmentLight(half, new Euler()).direction) < 1e-10);
});

test('uniform or unusable HDR data does not invent a directional light', () => {
  const { image } = panorama();
  assert.equal(environmentLight(image, new Euler()), null);
  image.data.fill(NaN);
  assert.equal(environmentLight(image, new Euler()), null);
});

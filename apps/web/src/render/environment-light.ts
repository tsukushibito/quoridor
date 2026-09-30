import { Color, DataUtils, Euler, Vector3 } from 'three/webgpu';

type HDRImage = { data: Uint16Array | Float32Array; width: number; height: number };
type Sample = { direction: Vector3; luminance: number; area: number; rgb: [number, number, number] };
export type EnvironmentLight = { direction: Vector3; color: Color; energyShare: number };

/** Estimate one dominant source, rather than averaging opposing windows into a ceiling light. */
export function environmentLight(image: HDRImage, rotation: Euler): EnvironmentLight | null {
  if (image.width < 1 || image.height < 1 || image.data.length < image.width * image.height * 4) return null;
  const samples: Sample[] = [];
  // Bound CPU work independently of asset resolution. Pixel centers match equirectUV;
  // HDRLoader.flipY=true means the first decoded row is the upper hemisphere.
  const stride = Math.max(1, Math.floor(image.width / 512));
  for (let y = 0; y < image.height / 2; y += stride) {
    const latitude = (0.5 - (y + 0.5) / image.height) * Math.PI;
    const area = Math.cos(latitude);
    for (let x = 0; x < image.width; x += stride) {
      const offset = (y * image.width + x) * 4;
      const rgb = [0, 1, 2].map(channel => image.data instanceof Uint16Array
        ? DataUtils.fromHalfFloat(image.data[offset + channel]!) : image.data[offset + channel]!) as [number, number, number];
      const luminance = rgb[0] * 0.2126 + rgb[1] * 0.7152 + rgb[2] * 0.0722;
      if (!Number.isFinite(luminance) || luminance <= 0) continue;
      const longitude = ((x + 0.5) / image.width - 0.5) * Math.PI * 2;
      samples.push({ direction: new Vector3(area * Math.cos(longitude), Math.sin(latitude), area * Math.sin(longitude)), luminance, area, rgb });
    }
  }
  if (!samples.length) return null;
  // Solid-angle weighted percentile excludes the diffuse room fill. The common
  // d(longitude)*d(latitude) factor cancels in averages and energy ratios.
  samples.sort((a, b) => a.luminance - b.luminance);
  const totalArea = samples.reduce((sum, sample) => sum + sample.area, 0);
  let accumulated = 0, threshold = 0;
  for (const sample of samples) {
    accumulated += sample.area;
    if (accumulated >= totalArea * 0.95) { threshold = sample.luminance; break; }
  }
  const bright = samples.filter(sample => sample.luminance > threshold);
  if (!bright.length) return null; // A uniform map has no defensible source direction.
  const bins = new Map<number, { energy: number; sum: Vector3 }>();
  let totalEnergy = 0;
  for (const sample of bright) {
    const longitude = Math.atan2(sample.direction.z, sample.direction.x);
    const column = Math.min(31, Math.floor((longitude / (Math.PI * 2) + 0.5) * 32));
    const row = Math.min(7, Math.floor(Math.asin(sample.direction.y) / (Math.PI / 2) * 8));
    const key = row * 32 + column;
    const bin = bins.get(key) ?? { energy: 0, sum: new Vector3() };
    const energy = (sample.luminance - threshold) * sample.area;
    bin.energy += energy; bin.sum.addScaledVector(sample.direction, energy);
    bins.set(key, bin); totalEnergy += energy;
  }
  const seed = [...bins.values()].sort((a, b) => b.energy - a.energy)[0]!.sum.normalize();
  const direction = new Vector3(), colorSum = new Vector3();
  let sourceEnergy = 0;
  // Collect the source's neighbors across bin boundaries, including the panorama seam.
  const cone = Math.cos(Math.PI / 6);
  for (const sample of bright) {
    if (sample.direction.dot(seed) < cone) continue;
    const energy = (sample.luminance - threshold) * sample.area;
    direction.addScaledVector(sample.direction, energy);
    colorSum.addScaledVector(new Vector3(...sample.rgb), energy);
    sourceEnergy += energy;
  }
  direction.normalize().applyEuler(rotation);
  colorSum.divideScalar(Math.max(colorSum.x, colorSum.y, colorSum.z));
  return { direction, color: new Color().setRGB(colorSum.x, colorSum.y, colorSum.z), energyShare: sourceEnergy / totalEnergy };
}

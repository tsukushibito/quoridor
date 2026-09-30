/** Runtime assets are local; IDs are stable persisted settings. No renderer dependency. */
export const ENVIRONMENT_PRESETS = [
  { id: 'warm-room', label: '暖かい室内', asset: 'assets/tabletop/comfy-cafe-2k.hdr',
    rotationY: Math.PI / 2, environmentIntensity: 0.65, keyIntensity: 4, backgroundIntensity: 0.55 },
  { id: 'dark-room', label: '暗めの室内', asset: 'assets/environments/warm-restaurant-night-2k.hdr',
    rotationY: Math.PI / 2, environmentIntensity: 0.35, keyIntensity: 1.5, backgroundIntensity: 0.35 },
  { id: 'forest', label: '森の中', asset: 'assets/environments/epping-forest-02-2k.hdr',
    rotationY: Math.PI / 2, environmentIntensity: 0.55, keyIntensity: 2.5, backgroundIntensity: 0.55 },
  { id: 'mountain', label: '山の上', asset: 'assets/environments/qwantani-noon-2k.hdr',
    rotationY: Math.PI / 2, environmentIntensity: 0.45, keyIntensity: 4, backgroundIntensity: 0.55 },
] as const;
export type EnvironmentId = typeof ENVIRONMENT_PRESETS[number]['id'];
export const DEFAULT_ENVIRONMENT: EnvironmentId = 'warm-room';
export function isEnvironmentId(value: unknown): value is EnvironmentId {
  return ENVIRONMENT_PRESETS.some(preset => preset.id === value);
}
export function environmentPreset(id: EnvironmentId): typeof ENVIRONMENT_PRESETS[number] {
  return ENVIRONMENT_PRESETS.find(preset => preset.id === id)!;
}

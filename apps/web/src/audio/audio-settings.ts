export const AUDIO_SETTINGS_KEY = 'quoridor.audio.settings.v1';
export type AudioSettings = Readonly<{
  schemaVersion: 1; muted: boolean; sfxEnabled: boolean; bgmEnabled: boolean;
  sfxVolume: number; bgmVolume: number;
}>;
export const DEFAULT_AUDIO_SETTINGS: AudioSettings = Object.freeze({ schemaVersion: 1,
  muted: false, sfxEnabled: true, bgmEnabled: true, sfxVolume: 55, bgmVolume: 20 });
type StoragePort = Pick<Storage, 'getItem' | 'setItem'>;
export function validateAudioSettings(value: unknown): AudioSettings {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Invalid audio settings');
  const v = value as Record<string, unknown>;
  const fields = Object.keys(DEFAULT_AUDIO_SETTINGS);
  if (Object.keys(v).length !== fields.length || !fields.every(key => Object.hasOwn(v, key)) ||
    v.schemaVersion !== 1 || ['muted', 'sfxEnabled', 'bgmEnabled'].some(key => typeof v[key] !== 'boolean') ||
    ['sfxVolume', 'bgmVolume'].some(key => typeof v[key] !== 'number' || !Number.isInteger(v[key]) ||
      (v[key] as number) < 0 || (v[key] as number) > 100)) throw new Error('Invalid audio settings');
  return { schemaVersion: 1, muted: v.muted as boolean, sfxEnabled: v.sfxEnabled as boolean,
    bgmEnabled: v.bgmEnabled as boolean, sfxVolume: v.sfxVolume as number, bgmVolume: v.bgmVolume as number };
}
export class AudioSettingsRepository {
  private readonly storage: () => StoragePort;
  constructor(storage: () => StoragePort = () => window.localStorage) { this.storage = storage; }
  read(): { value: AudioSettings; warning: 'invalid' | 'unavailable' | null } {
    let raw: string | null;
    try { raw = this.storage().getItem(AUDIO_SETTINGS_KEY); }
    catch { return { value: DEFAULT_AUDIO_SETTINGS, warning: 'unavailable' }; }
    if (raw === null) return { value: DEFAULT_AUDIO_SETTINGS, warning: null };
    try {
      if (raw.length > 1024) throw new Error('Audio settings too large');
      return { value: validateAudioSettings(JSON.parse(raw)), warning: null };
    } catch { return { value: DEFAULT_AUDIO_SETTINGS, warning: 'invalid' }; }
  }
  write(value: AudioSettings): boolean {
    try { this.storage().setItem(AUDIO_SETTINGS_KEY, JSON.stringify(validateAudioSettings(value))); return true; }
    catch { return false; }
  }
}

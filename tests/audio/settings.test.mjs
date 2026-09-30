import { test } from 'node:test';
import assert from 'node:assert/strict';
import { AUDIO_SETTINGS_KEY, AudioSettingsRepository, DEFAULT_AUDIO_SETTINGS, validateAudioSettings }
  from '../../apps/web/src/audio/audio-settings.ts';

test('audio settings persist independently without touching existing game/display settings', () => {
  const saved = new Map([['quoridor.m1.settings.v1', '{"existing":true}']]);
  const repository = new AudioSettingsRepository(() => ({ getItem: key => saved.get(key) ?? null,
    setItem: (key, value) => saved.set(key, value) }));
  assert.deepEqual(repository.read(), { value: DEFAULT_AUDIO_SETTINGS, warning: null });
  const settings = { ...DEFAULT_AUDIO_SETTINGS, muted: true, sfxVolume: 0, bgmVolume: 100, bgmEnabled: false };
  assert.equal(repository.write(settings), true);
  assert.deepEqual(repository.read(), { value: settings, warning: null });
  assert.equal(saved.get('quoridor.m1.settings.v1'), '{"existing":true}');
  assert.ok(saved.has(AUDIO_SETTINGS_KEY));
});
test('malformed, oversized and future settings use defaults without destroying stored data', () => {
  for (const raw of ['{', 'null', '[]', JSON.stringify({ ...DEFAULT_AUDIO_SETTINGS, schemaVersion: 2 }),
    JSON.stringify({ ...DEFAULT_AUDIO_SETTINGS, sfxVolume: 101 }), ' '.repeat(1025)]) {
    const repository = new AudioSettingsRepository(() => ({ getItem: () => raw, setItem: () => assert.fail() }));
    assert.deepEqual(repository.read(), { value: DEFAULT_AUDIO_SETTINGS, warning: 'invalid' });
  }
  for (const value of [NaN, Infinity, -1, 100.1, '55'])
    assert.throws(() => validateAudioSettings({ ...DEFAULT_AUDIO_SETTINGS, bgmVolume: value }));
});
test('storage failures do not throw, and invalid writes never reach storage', () => {
  const repository = new AudioSettingsRepository(() => { throw new Error('Storage disabled'); });
  assert.deepEqual(repository.read(), { value: DEFAULT_AUDIO_SETTINGS, warning: 'unavailable' });
  assert.equal(repository.write(DEFAULT_AUDIO_SETTINGS), false);
  const rejecting = new AudioSettingsRepository(() => ({ getItem: () => null,
    setItem: () => { throw new Error('Quota exceeded'); } }));
  assert.equal(rejecting.write(DEFAULT_AUDIO_SETTINGS), false);
  let writes = 0;
  const working = new AudioSettingsRepository(() => ({ getItem: () => null, setItem: () => writes++ }));
  assert.equal(working.write({ ...DEFAULT_AUDIO_SETTINGS, sfxVolume: -1 }), false);
  assert.equal(writes, 0);
});

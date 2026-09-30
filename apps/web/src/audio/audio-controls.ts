import { AudioController } from './audio-controller';
import { AudioSettingsRepository, type AudioSettings } from './audio-settings';
import { ja } from '../ui/strings';
import { setIconButton } from '../ui/icons';

export function installAudioControls(actions: HTMLElement, menu: HTMLDialogElement,
  signal: AbortSignal, base: string): AudioController {
  const repository = new AudioSettingsRepository();
  const read = repository.read();
  const audio = new AudioController(read.value, base);
  let warning = read.warning === 'invalid' ? ja.audioInvalid : read.warning === 'unavailable' ? ja.audioStorage : '';
  const button = document.createElement('button');
  button.type = 'button'; button.id = 'sound-mute'; setIconButton(button, 'sound', ja.muteAll);
  actions.prepend(button);
  const panel = document.createElement('section');
  panel.className = 'panel sound-panel'; panel.setAttribute('aria-labelledby', 'sound-heading');
  panel.innerHTML = `<h3 id="sound-heading">${ja.sound}</h3>
    <label class="sound-toggle"><input id="sound-muted" type="checkbox">${ja.muteAll}</label>
    <div class="sound-channel"><label class="sound-toggle"><input id="sfx-enabled" type="checkbox">${ja.sfx}<span id="sfx-state"></span></label>
      <label class="sound-volume" for="sfx-volume">${ja.sfxVolume}<output id="sfx-value" for="sfx-volume"></output></label>
      <input id="sfx-volume" type="range" min="0" max="100" step="1" aria-label="${ja.sfxVolume}">
      <button id="sound-preview" type="button">${ja.soundPreview}</button></div>
    <div class="sound-channel"><label class="sound-toggle"><input id="bgm-enabled" type="checkbox">${ja.bgm}<span id="bgm-state"></span></label>
      <label class="sound-volume" for="bgm-volume">${ja.bgmVolume}<output id="bgm-value" for="bgm-volume"></output></label>
      <input id="bgm-volume" type="range" min="0" max="100" step="1" aria-label="${ja.bgmVolume}"></div>
    <p id="sound-status" role="status"></p><p id="sound-storage" role="status"></p>
    <button id="sound-retry" type="button" hidden>${ja.soundRetry}</button>
    <details class="sound-credits"><summary>${ja.soundCredits}</summary><p>${ja.soundCreditText}
      <a href="https://kenney.nl/assets/impact-sounds" target="_blank" rel="noopener noreferrer">Kenney — Impact Sounds</a> ·
      <a href="https://kenney.nl/assets/interface-sounds" target="_blank" rel="noopener noreferrer">Interface Sounds</a> ·
      <a href="https://opengameart.org/content/cozy-puzzle-in-game-1" target="_blank" rel="noopener noreferrer">MintoDog — Cozy Puzzle In-Game 1</a> ·
      <a href="https://freesound.org/people/el_boss/sounds/677858/" target="_blank" rel="noopener noreferrer">el_boss — Game Success Fanfare Short</a> ·
      <a href="https://freesound.org/people/el_boss/sounds/677855/" target="_blank" rel="noopener noreferrer">Game Fail Fanfare</a>
      <span>CC0 1.0</span></p></details>`;
  menu.querySelector('.dialog-head')!.after(panel);
  const get = <T extends HTMLElement>(id: string): T => panel.querySelector<T>(`#${id}`)!;
  const muted = get<HTMLInputElement>('sound-muted');
  const sfx = get<HTMLInputElement>('sfx-enabled'), bgm = get<HTMLInputElement>('bgm-enabled');
  const sfxVolume = get<HTMLInputElement>('sfx-volume'), bgmVolume = get<HTMLInputElement>('bgm-volume');
  const preview = get<HTMLButtonElement>('sound-preview'), retry = get<HTMLButtonElement>('sound-retry');
  let renderedSettings: AudioSettings | null = null;
  const render = (): void => {
    const settings = audio.settings;
    const silent = settings.muted || (!settings.sfxEnabled || settings.sfxVolume === 0) &&
      (!settings.bgmEnabled || settings.bgmVolume === 0);
    button.setAttribute('aria-pressed', String(settings.muted));
    button.setAttribute('aria-label', settings.muted ? ja.unmuteAll : ja.muteAll);
    button.classList.toggle('sound-silent', silent);
    button.querySelector('.icon-tooltip')!.textContent = settings.muted ? ja.unmuteAll : ja.muteAll;
    // Status notifications may run between a checkbox's click and its change event.
    // Only overwrite form values when preferences actually change, preserving that native interaction.
    if (renderedSettings !== settings) {
      muted.checked = settings.muted; sfx.checked = settings.sfxEnabled; bgm.checked = settings.bgmEnabled;
      sfxVolume.value = String(settings.sfxVolume); bgmVolume.value = String(settings.bgmVolume);
      renderedSettings = settings;
    }
    get<HTMLOutputElement>('sfx-value').value = `${settings.sfxVolume}%`;
    get<HTMLOutputElement>('bgm-value').value = `${settings.bgmVolume}%`;
    sfxVolume.setAttribute('aria-valuetext', `${settings.sfxVolume}%`);
    bgmVolume.setAttribute('aria-valuetext', `${settings.bgmVolume}%`);
    get('sfx-state').textContent = settings.sfxEnabled ? 'ON' : 'OFF';
    get('bgm-state').textContent = settings.bgmEnabled ? 'ON' : 'OFF';
    const status = audio.status;
    preview.disabled = settings.muted || !settings.sfxEnabled || settings.sfxVolume === 0 ||
      !audio.diagnostics().loaded.includes('move') || status === 'disposed' || status === 'unavailable';
    const message = { waiting: ja.audioWaiting, loading: ja.audioLoading, ready: '', blocked: ja.audioBlocked,
      unavailable: ja.audioUnavailable, failed: ja.audioFailed, disposed: '' }[status];
    get('sound-status').textContent = settings.muted || silent ? (status === 'failed' || status === 'unavailable' ? message : '') : message;
    get('sound-storage').textContent = warning;
    retry.hidden = !['failed', 'blocked', 'unavailable'].includes(status);
  };
  const update = (patch: Partial<AudioSettings>): void => {
    audio.configure({ ...audio.settings, ...patch });
    warning = repository.write(audio.settings) ? '' : ja.audioStorage;
    render();
  };
  button.addEventListener('click', () => update({ muted: !audio.settings.muted }), { signal });
  muted.addEventListener('change', () => update({ muted: muted.checked }), { signal });
  sfx.addEventListener('change', () => update({ sfxEnabled: sfx.checked }), { signal });
  bgm.addEventListener('change', () => update({ bgmEnabled: bgm.checked }), { signal });
  sfxVolume.addEventListener('input', () => update({ sfxVolume: Number(sfxVolume.value) }), { signal });
  bgmVolume.addEventListener('input', () => update({ bgmVolume: Number(bgmVolume.value) }), { signal });
  preview.addEventListener('click', () => audio.play('move'), { signal });
  retry.addEventListener('click', () => { void audio.retry(); }, { signal });
  const unlock = (event: Event): void => { if (event.isTrusted) void audio.unlock(); };
  document.addEventListener('click', unlock, { capture: true, signal });
  document.addEventListener('keydown', unlock, { capture: true, signal });
  document.addEventListener('visibilitychange', () => audio.setHidden(document.hidden), { signal });
  audio.setHidden(document.hidden);
  // Explicit allowlist avoids sounds for disabled controls, input, previews and muting itself.
  const clickIds = new Set(['open-menu', 'close-menu', 'mode-move', 'mode-wall', 'orientation', 'new-game',
    'restart-game', 'dialog-start', 'dialog-cancel', 'startup-new-game', 'flip', 'reset-camera', 'save-now',
    'clear-save', 'cancel-ai', 'retry-ai', 'take-control', 'title-help', 'open-help', 'close-help',
    'close-help-bottom', 'return-title', 'restart-cancel', 'restart-confirm', 'resume-game-choice']);
  document.addEventListener('click', event => {
    const target = event.target instanceof Element ? event.target.closest('button') : null;
    if (target && !target.disabled && clickIds.has(target.id)) audio.play('click');
  }, { signal });
  const unsubscribe = audio.subscribe(render);
  signal.addEventListener('abort', () => { unsubscribe(); audio.dispose(); }, { once: true });
  return audio;
}

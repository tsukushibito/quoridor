import { validateAudioSettings, type AudioSettings } from './audio-settings';

const FILES = { move: 'pawn.wav', wall: 'wall.wav', click: 'click.wav', undo: 'undo.wav',
  win: 'win.wav', lose: 'lose.wav', bgm: 'cozy-puzzle.mp3' } as const;
export type SoundCue = Exclude<keyof typeof FILES, 'bgm'>;
type Asset = keyof typeof FILES;
export type AudioStatus = 'waiting' | 'loading' | 'ready' | 'blocked' | 'unavailable' | 'failed' | 'disposed';

/** One owner per app, independent of renderer/game replacements. Never queues missed SE. */
export class AudioController {
  private settingsValue: AudioSettings;
  private context: AudioContext | null = null;
  private sfxGain: GainNode | null = null;
  private bgmGain: GainNode | null = null;
  private buffers = new Map<Asset, AudioBuffer>();
  private pending = new Map<Asset, Promise<void>>();
  private failures = new Set<Asset>();
  private requests = new Set<AbortController>();
  private sources = new Set<AudioBufferSourceNode>();
  private bgm: AudioBufferSourceNode | null = null;
  private fadingBgm = new Set<AudioBufferSourceNode>();
  private musicActive = true;
  private bgmOffset = 0;
  private bgmStartedAt = 0;
  private hidden = false;
  private disposed = false;
  private unavailable = false;
  private blocked = false;
  private unlocking: Promise<void> | null = null;
  private resumeTimer: ReturnType<typeof setTimeout> | null = null;
  private cancelResume: (() => void) | null = null;
  private envelopes = new Map<GainNode, { start: number; from: number; to: number; duration: number }>();
  private counts: Record<Asset, number> = { move: 0, wall: 0, click: 0, undo: 0, win: 0, lose: 0, bgm: 0 };
  private listeners = new Set<() => void>();
  constructor(settings: AudioSettings, private readonly base: string,
    private readonly createContext: () => AudioContext = () => new AudioContext()) {
    this.settingsValue = validateAudioSettings(settings);
  }
  get settings(): AudioSettings { return this.settingsValue; }
  get status(): AudioStatus {
    if (this.disposed) return 'disposed';
    if (this.unavailable) return 'unavailable';
    if (this.failures.size) return 'failed';
    if (this.blocked) return 'blocked';
    if (this.pending.size || this.unlocking) return 'loading';
    if (!this.context || this.context.state !== 'running') return 'waiting';
    return 'ready';
  }
  subscribe(listener: () => void): () => void {
    this.listeners.add(listener); listener(); return () => this.listeners.delete(listener);
  }
  private notify(): void { for (const listener of this.listeners) listener(); }
  /** Call directly from a trusted gesture, before any await, including after iOS interruptions. */
  unlock(): Promise<void> {
    if (this.disposed || this.unavailable) return Promise.resolve();
    if (this.context?.state === 'running' && !this.blocked) return Promise.resolve();
    if (this.unlocking) return this.unlocking;
    try {
      if (!this.context) {
        this.context = this.createContext();
        this.sfxGain = this.context.createGain(); this.sfxGain.gain.value = 0;
        this.bgmGain = this.context.createGain(); this.bgmGain.gain.value = 0;
        this.sfxGain.connect(this.context.destination); this.bgmGain.connect(this.context.destination);
        this.context.onstatechange = () => {
          if (this.disposed) return;
          this.sync(); this.notify();
        };
      }
      const resume = this.context.resume();
      const deadline = new Promise<never>((_, reject) => {
        this.cancelResume = () => reject(new Error('Audio resume timeout'));
        this.resumeTimer = setTimeout(this.cancelResume, 8000);
      });
      this.unlocking = Promise.race([resume, deadline]).then(() => {
        if (this.disposed) return;
        this.blocked = this.context?.state !== 'running';
        this.sync(); this.notify();
      }).catch(() => { if (!this.disposed) { this.blocked = true; this.notify(); } })
        .finally(() => {
          if (this.resumeTimer) clearTimeout(this.resumeTimer);
          this.resumeTimer = null; this.cancelResume = null; this.unlocking = null;
          if (!this.disposed) this.notify();
        });
      this.loadEnabled();
      return this.unlocking;
    } catch {
      this.unavailable = true; this.notify(); return Promise.resolve();
    }
  }
  configure(settings: AudioSettings): void {
    if (this.disposed) return;
    this.settingsValue = validateAudioSettings(settings);
    if (this.context) this.loadEnabled();
    this.sync(); this.notify();
  }
  private loadEnabled(): void {
    const settings = this.settingsValue;
    if (settings.muted) return;
    if (settings.sfxEnabled && settings.sfxVolume > 0)
      for (const cue of ['move', 'wall', 'click', 'undo', 'win', 'lose'] as const) void this.load(cue);
    if (settings.bgmEnabled && settings.bgmVolume > 0) void this.load('bgm');
  }
  private async load(asset: Asset): Promise<void> {
    if (!this.context || this.disposed || this.buffers.has(asset) || this.failures.has(asset)) return;
    const current = this.pending.get(asset); if (current) return current;
    const context = this.context;
    const request = new AbortController(); this.requests.add(request);
    let timeout: ReturnType<typeof setTimeout>;
    const deadline = new Promise<never>((_, reject) => {
      timeout = setTimeout(() => { request.abort(); reject(new Error('Audio load timeout')); }, 8000);
    });
    const task = (async () => {
      try {
        const buffer = await Promise.race([deadline, (async () => {
          const response = await fetch(`${this.base}assets/audio/${FILES[asset]}`, { signal: request.signal });
          if (!response.ok) throw new Error(`Audio HTTP ${response.status}`);
          return context.decodeAudioData(await response.arrayBuffer());
        })()]);
        if (!this.disposed) this.buffers.set(asset, buffer);
      } catch { if (!this.disposed) this.failures.add(asset); }
      finally {
        clearTimeout(timeout!); this.requests.delete(request); this.pending.delete(asset);
        if (!this.disposed) { this.sync(); this.notify(); }
      }
    })();
    this.pending.set(asset, task); this.notify(); return task;
  }
  retry(): Promise<void> {
    this.failures.clear(); this.unavailable = false; this.blocked = false;
    const resume = this.unlock();
    this.loadEnabled(); return resume;
  }
  private ramp(node: GainNode | null, value: number, duration = 0.025): void {
    if (!node || !this.context) return;
    const now = this.context.currentTime;
    const envelope = this.envelopes.get(node);
    if (envelope?.to === value) return;
    const current = this.level(node);
    node.gain.cancelScheduledValues(now); node.gain.setValueAtTime(current, now);
    node.gain.linearRampToValueAtTime(value, now + duration);
    this.envelopes.set(node, { start: now, from: current, to: value, duration });
  }
  private level(node: GainNode | null): number {
    if (!node || !this.context) return 0;
    const envelope = this.envelopes.get(node);
    if (!envelope) return 0;
    const fraction = Math.min(1, Math.max(0, (this.context.currentTime - envelope.start) / envelope.duration));
    return envelope.from + (envelope.to - envelope.from) * fraction;
  }
  private sync(bgmFade = 0.025): void {
    if (this.disposed) return;
    const settings = this.settingsValue;
    const audible = !settings.muted && !this.hidden && !this.blocked && this.context?.state === 'running';
    this.ramp(this.sfxGain, audible && settings.sfxEnabled ? settings.sfxVolume / 100 : 0);
    this.ramp(this.bgmGain, audible && this.musicActive && settings.bgmEnabled ? settings.bgmVolume / 100 : 0, bgmFade);
    if (!audible || !settings.sfxEnabled || settings.sfxVolume === 0) this.stopEffects();
    if (!audible || !this.musicActive || !settings.bgmEnabled || settings.bgmVolume === 0) this.pauseBgm(bgmFade);
    else this.startBgm();
  }
  private startBgm(): void {
    const buffer = this.buffers.get('bgm');
    if (this.bgm || !buffer || !this.context || !this.bgmGain) return;
    this.stopFadingBgm();
    const source = this.context.createBufferSource(); source.buffer = buffer;
    source.loop = true; source.loopStart = 0; source.loopEnd = buffer.duration;
    source.connect(this.bgmGain);
    this.bgmOffset %= source.loopEnd; this.bgmStartedAt = this.context.currentTime;
    source.onended = () => { this.fadingBgm.delete(source); source.disconnect(); };
    source.start(0, this.bgmOffset); this.bgm = source; this.counts.bgm++;
  }
  private pauseBgm(fade = 0.025): void {
    const immediate = this.disposed || this.hidden || this.context?.state !== 'running';
    if (immediate) this.stopFadingBgm();
    if (!this.bgm || !this.context) return;
    this.bgmOffset = (this.bgmOffset + this.context.currentTime - this.bgmStartedAt) % this.bgm.loopEnd;
    this.bgm.stop(this.context.currentTime + (immediate ? 0 : fade));
    if (immediate) this.bgm.disconnect(); else this.fadingBgm.add(this.bgm);
    this.bgm = null;
  }
  private stopFadingBgm(): void {
    for (const source of this.fadingBgm) { source.stop(); source.disconnect(); }
    this.fadingBgm.clear();
  }
  setMusicActive(active: boolean, fade = 0.025): void {
    if (this.musicActive === active || this.disposed) return;
    this.musicActive = active; this.sync(fade); this.notify();
  }
  playPlacement(cue: 'move' | 'wall', outcome: 'win' | 'lose' | null): void {
    this.play(cue);
    if (outcome) {
      this.setMusicActive(false, 0.6);
      this.play(outcome, Math.max(0.6, this.buffers.get(cue)?.duration ?? 0));
    }
  }
  private startEffect(cue: SoundCue, delay: number): void {
    const settings = this.settingsValue;
    if (this.disposed || this.hidden || this.blocked || settings.muted || !settings.sfxEnabled || settings.sfxVolume === 0 ||
      !this.context || this.context.state !== 'running' || !this.sfxGain) return;
    const buffer = this.buffers.get(cue); if (!buffer) return;
    // Bound rapid UI clicks. There is no delayed queue to burst on unlock/return to the tab.
    if (this.sources.size >= 6) {
      if (cue === 'click') return;
      const oldest = this.sources.values().next().value;
      if (oldest) { oldest.stop(); oldest.disconnect(); this.sources.delete(oldest); }
    }
    const source = this.context.createBufferSource(); source.buffer = buffer; source.connect(this.sfxGain);
    source.onended = () => { this.sources.delete(source); source.disconnect(); };
    source.start(this.context.currentTime + delay); this.sources.add(source); this.counts[cue]++;
  }
  play(cue: SoundCue, delay = 0): void { this.startEffect(cue, delay); }
  private stopEffects(): void {
    for (const source of this.sources) { source.stop(); source.disconnect(); }
    this.sources.clear();
  }
  setHidden(hidden: boolean): void {
    if (this.disposed || this.hidden === hidden) return;
    this.hidden = hidden; this.sync(); this.notify();
  }
  cancelEffects(): void { this.stopEffects(); }
  diagnostics() {
    return { status: this.status, contextState: this.context?.state ?? null, settings: { ...this.settingsValue },
      loaded: [...this.buffers.keys()], failures: [...this.failures], pending: this.pending.size,
      activeBgm: this.bgm ? 1 : 0, activeEffects: this.sources.size, counts: { ...this.counts },
      bgmPosition: this.bgmOffset + (this.bgm && this.context ? this.context.currentTime - this.bgmStartedAt : 0),
      musicActive: this.musicActive, fadingBgm: this.fadingBgm.size,
      bgmDuration: this.buffers.get('bgm')?.duration ?? null, hidden: this.hidden,
      sfxLevel: this.level(this.sfxGain), bgmLevel: this.level(this.bgmGain) };
  }
  dispose(): void {
    if (this.disposed) return;
    this.disposed = true;
    this.cancelResume?.();
    if (this.resumeTimer) clearTimeout(this.resumeTimer);
    for (const request of this.requests) request.abort();
    this.pauseBgm(); this.stopEffects(); this.buffers.clear(); this.envelopes.clear();
    this.sfxGain?.disconnect(); this.bgmGain?.disconnect();
    if (this.context) { this.context.onstatechange = null; void this.context.close().catch(() => {}); }
    this.notify(); this.listeners.clear();
  }
}

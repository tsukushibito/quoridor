export type IconName = 'sound' | 'restart' | 'newGame' | 'help' | 'settings';
const shapes: Record<IconName, string> = {
  sound: '<path d="M11 4 6 8H3v8h3l5 4z"/><path class="sound-waves" d="M15 8a6 6 0 0 1 0 8m3-11a10 10 0 0 1 0 14"/><path class="sound-cross" d="m15 9 6 6m0-6-6 6"/>',
  restart: '<path d="M3 9a9 9 0 1 1 0 6M3 3v6h6"/>',
  newGame: '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M12 7v10M7 12h10"/>',
  help: '<circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 1 1 3.3 2.4c-.8.3-.8.8-.8 1.6M12 16v.1"/>',
  settings: '<path d="m9 3-.6 2.4-1.8 1L4.2 6l-2 3.5L4 11v2l-1.8 1.5L4.2 18l2.4-.4 1.8 1L9 21h6l.6-2.4 1.8-1 2.4.4 2-3.5L20 13v-2l1.8-1.5-2-3.5-2.4.4-1.8-1L15 3z"/><circle cx="12" cy="12" r="3"/>',
};
export function icon(name: IconName): string {
  return `<svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${shapes[name]}</svg>`;
}
export function setIconButton(button: HTMLButtonElement, name: IconName, label: string): void {
  button.classList.add('icon-button');
  button.setAttribute('aria-label', label);
  button.innerHTML = `${icon(name)}<span class="icon-tooltip" aria-hidden="true">${label}</span>`;
}

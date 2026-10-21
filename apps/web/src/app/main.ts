import { createNavigation } from './navigation';
import { showHome } from '../pages/home';
import './style.css';

const root = document.querySelector<HTMLElement>('#app');
if (!root) throw new Error('App root is missing');
const app = root;
const navigation = createNavigation({
  hash: () => location.hash,
  home: (warning) => showHome(app, warning),
  loading: (route) => {
    const game = document.createElement('div');
    game.innerHTML = `<section class="app-loading"><a href="#/">ゲーム一覧</a><p role="status">${route === 'othello' ? 'Othello' : 'Quoridor'} を読み込んでいます…</p></section>`;
    app.replaceChildren(game);
    return game;
  },
  load: async (route) => {
    if (route === 'othello') {
      const game = await import('../games/othello');
      return { mount: game.mountOthello };
    }
    const game = await import('../games/quoridor');
    return { mount: game.mountQuoridor };
  },
  failed: (error, route) => {
    app.innerHTML = `<section class="app-loading"><a href="#/">ゲーム一覧</a><h1>${route === 'othello' ? 'Othello' : 'Quoridor'} を開けませんでした</h1><p role="alert"></p><button type="button">再読み込み</button></section>`;
    app.querySelector('[role="alert"]')!.textContent =
      error instanceof Error ? error.message : String(error);
    app.querySelector('button')!.onclick = () => location.reload();
  },
});
window.addEventListener('hashchange', () => void navigation.update());
window.addEventListener('pagehide', (event) => {
  if (!event.persisted) navigation.dispose();
});
void navigation.update();

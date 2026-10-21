import './style.css';

export function showHome(root: HTMLElement, warning?: string): void {
  root.innerHTML = `<main class="home-page">
    <p class="home-eyebrow">BOARD GAMES</p><h1>ゲームを選ぶ</h1>
    <div class="home-choices">
      <section><h2>Quoridor</h2><p>駒と壁で競うボードゲーム。新しい対局や保存した対局の再開を選べます。</p>
        <a id="choose-quoridor" href="#/quoridor">Quoridor を開く</a></section>
      <section><h2>Othello</h2><p>まだ利用できません。</p><button type="button" disabled>準備中</button></section>
    </div><p id="home-save-warning" role="status"></p></main>`;
  root.querySelector('#home-save-warning')!.textContent = warning ?? '';
}

import './style.css';

export function showHome(root: HTMLElement, warning?: string): void {
  root.innerHTML = `<main class="home-page">
    <p class="home-eyebrow">BOARD GAMES</p><h1>ゲームを選ぶ</h1>
    <div class="home-choices">
      <section><h2>Quoridor</h2><p>駒と壁で競うボードゲーム。新しい対局や保存した対局の再開を選べます。</p>
        <a id="choose-quoridor" href="#/quoridor">Quoridor を開く</a></section>
      <section><h2>Othello</h2><p>8 × 8 の盤で石を挟んで反転。ローカル2人または簡易AI（非学習）と対戦できます。</p><a id="choose-othello" href="#/othello">Othello を開く</a></section>
    </div><p id="home-save-warning" role="status"></p></main>`;
  root.querySelector('#home-save-warning')!.textContent = warning ?? '';
}

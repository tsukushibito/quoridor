import type { Mode } from './storage';
import type { Side } from '../../../../../games/othello/bridge/src';
import type { SessionView } from './session';

type Actions = {
  start(mode: Mode, side: Side): void;
  resume(): void;
  play(index: number): void;
  pass(): void;
  save(): void;
  retryAI(): void;
};
const color = (side: number) => (side === 1 ? '黒' : side === 2 ? '白' : '空き');
const coordinate = (index: number) =>
  `${String.fromCharCode(65 + (index % 8))}${Math.floor(index / 8) + 1}`;

export function createView(root: HTMLElement, signal: AbortSignal, actions: Actions) {
  root.classList.add('othello');
  root.innerHTML = `<main class="othello-page">
    <header><div><p class="othello-eyebrow">BOARD GAMES</p><h1 tabindex="-1">Othello</h1></div><a href="#/">ゲーム一覧へ戻る</a></header>
    <section class="othello-setup" aria-labelledby="othello-setup-title"><h2 id="othello-setup-title">対局を選ぶ</h2>
      <label>対戦方式<select id="othello-mode"><option value="local">ローカル2人</option><option value="ai">簡易AI（非学習）と対戦</option></select></label>
      <label id="othello-side-label" hidden>人間が担当する色<select id="othello-human-side"><option value="1">黒（先手）</option><option value="2">白（後手）</option></select></label>
      <p>簡易AIは決定的なルールで手を選びます。学習・モデルは使用しません。</p>
      <p>新しく始めると、この端末のOthello保存枠を置き換えます。</p>
      <div class="othello-actions"><button id="othello-new" type="button">新しい対局</button><button id="othello-resume" type="button">続きから／再試行</button></div>
    </section>
    <p id="othello-error" role="alert"></p>
    <section class="othello-match" aria-label="Othelloの対局" hidden>
      <div class="othello-summary"><h2 id="othello-turn" tabindex="-1" aria-live="polite"></h2><p id="othello-players"></p><p id="othello-score"></p></div>
      <p id="othello-notice" role="status"></p><p id="othello-guide"></p>
      <div class="othello-board" role="group" aria-label="Othello 8行8列の盤。列AからH、行1から8。合法手に印があります。"></div>
      <div class="othello-actions"><button id="othello-pass" type="button" hidden>合法手がないためパス</button><button id="othello-retry-ai" type="button" hidden>簡易AIを再試行</button><button id="othello-save" type="button">今すぐ保存</button></div>
    </section><p id="othello-save-status" role="status"></p></main>`;
  const $ = <T extends HTMLElement>(selector: string) => root.querySelector<T>(selector)!;
  const mode = $<HTMLSelectElement>('#othello-mode');
  const side = $<HTMLSelectElement>('#othello-human-side');
  const board = $('.othello-board');
  const cells = Array.from({ length: 64 }, (_, index) => {
    const cell = document.createElement('button');
    cell.type = 'button';
    cell.dataset.index = String(index);
    cell.className = 'othello-cell';
    cell.setAttribute('aria-label', `${coordinate(index)} 空き`);
    cell.addEventListener('click', () => actions.play(index), { signal });
    cell.addEventListener(
      'keydown',
      (event) => {
        const shifts: Record<string, number> = {
          ArrowRight: 1,
          ArrowLeft: -1,
          ArrowDown: 8,
          ArrowUp: -8,
        };
        const shift = shifts[event.key];
        if (shift === undefined) return;
        event.preventDefault();
        const next = index + shift;
        if (
          next >= 0 &&
          next < 64 &&
          (Math.abs(shift) === 8 || Math.floor(next / 8) === Math.floor(index / 8))
        )
          cells[next]?.focus();
      },
      { signal },
    );
    board.append(cell);
    return cell;
  });
  mode.addEventListener(
    'change',
    () => {
      $('#othello-side-label').hidden = mode.value !== 'ai';
    },
    { signal },
  );
  $('#othello-new').addEventListener(
    'click',
    () => actions.start(mode.value as Mode, Number(side.value) as Side),
    { signal },
  );
  $('#othello-resume').addEventListener('click', actions.resume, { signal });
  $('#othello-pass').addEventListener('click', actions.pass, { signal });
  $('#othello-save').addEventListener('click', actions.save, { signal });
  $('#othello-retry-ai').addEventListener('click', actions.retryAI, { signal });
  $('h1').focus();
  let previousState: SessionView['game'];
  return {
    render(view: SessionView): void {
      $('#othello-error').textContent = view.error;
      $('#othello-save-status').textContent = view.saveMessage;
      const { game, status } = view;
      $('.othello-match').hidden = !game;
      $('#othello-resume').textContent =
        view.busy && !game ? '読み込んでいます…' : '続きから／再試行';
      if (!game || !status) return;
      const humanTurn = game.mode === 'local' || game.state.toMove === game.humanSide;
      $('#othello-turn').textContent = status.terminal
        ? status.winner === null
          ? '終局：引分け'
          : `終局：${color(status.winner)}の勝ち`
        : `${color(game.state.toMove)}の手番${view.thinking ? ' · 簡易AIが考えています…' : ''}`;
      $('#othello-players').textContent =
        game.mode === 'local'
          ? 'ローカル2人 · 黒：人間 ／ 白：人間'
          : `簡易AI（非学習）と対戦 · 人間：${color(game.humanSide)} ／ 簡易AI：${color(game.humanSide === 1 ? 2 : 1)}`;
      $('#othello-score').textContent = `黒 ${status.black} 石 ／ 白 ${status.white} 石`;
      $('#othello-notice').textContent = view.notice;
      $('#othello-guide').textContent = status.terminal
        ? '対局が終わりました。新しい対局を選べます。'
        : status.mustPass
          ? `${color(game.state.toMove)}には合法手がありません。パスが必要です。`
          : '印のあるマスに置けます。Tabまたは矢印キーで移動し、Enter・Spaceで置きます。';
      $('#othello-pass').hidden = !status.mustPass || !humanTurn;
      $<HTMLButtonElement>('#othello-pass').disabled = view.busy;
      $('#othello-retry-ai').hidden = !view.error || humanTurn || status.terminal;
      for (const [index, cell] of cells.entries()) {
        const value = game.state.board[index]!;
        const legal = status.legalMoves.includes(index);
        const enabled = legal && humanTurn && !view.busy && !status.terminal;
        cell.dataset.stone = String(value);
        cell.dataset.legal = String(legal);
        cell.setAttribute(
          'aria-label',
          `${coordinate(index)} ${color(value)}${legal ? ' 合法手' : ''}`,
        );
        // Keep all cells focusable so a keyboard user can inspect the complete board.
        cell.setAttribute('aria-disabled', String(!enabled));
        cell.textContent = value === 1 ? '●' : value === 2 ? '○' : legal ? '·' : '';
      }
      if (game !== previousState) $('#othello-turn').focus();
      previousState = game;
    },
    dispose(): void {
      board.replaceChildren();
    },
  };
}

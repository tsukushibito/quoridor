import type {
  Side,
  UiAction,
  UiMode,
  UiStrategy,
  UiView,
} from '../../../../../games/othello/bridge/src';

import type { ModelFiles } from './ai-client';

// DOM projection only. Labels, legality, transitions and enabled controls come from Rust.
export function createView(
  root: HTMLElement,
  signal: AbortSignal,
  action: (event: UiAction) => void,
  selectFiles: (value: ModelFiles) => void,
) {
  root.classList.add('othello');
  root.innerHTML = `<main class="othello-page">
    <header><div><p class="othello-eyebrow">BOARD GAMES</p><h1 tabindex="-1">Othello</h1></div><a href="#/">ゲーム一覧へ戻る</a></header>
    <section class="othello-setup" aria-labelledby="othello-setup-title"><h2 id="othello-setup-title">対局を選ぶ</h2>
      <label>対戦方式<select id="othello-mode"><option value="local">ローカル2人</option><option value="ai">AIと対戦</option></select></label>
      <label id="othello-side-label" hidden>人間が担当する色<select id="othello-human-side"><option value="1">黒（先手）</option><option value="2">白（後手）</option></select></label>
      <label id="othello-strategy-label" hidden>AIの方式<select id="othello-strategy"><option value="simple">簡易AI（非学習）</option><option value="searchV1">探索AI（非学習・1秒）</option><option value="fullModel">フル探索AI（評価ファイル使用・1秒）</option></select></label>
      <p>既定は簡易AIです。探索AI（非学習）はモデルを使いません。フル探索AIは指定のローカル評価ファイルを使い、準備完了後に1手1秒を予算に探索します。</p>
      <div id="othello-full-files" hidden>
        <label>主評価ファイル<input id="othello-full-main" type="file" /></label>
        <label>終盤手順評価ファイル<input id="othello-full-ending" type="file" /></label>
        <button id="othello-load-full" type="button">評価ファイルを確認・準備</button>
        <button id="othello-cancel-model" type="button" hidden>準備を中断</button>
        <p id="othello-model-status" role="status">指定の2ファイルをこの端末から選択してください。</p>
        <p>ファイルはこのブラウザ内で使用し、送信・保存しません。Egaroucid Console 7.8.1由来の評価を使用します。元ソースのライセンスと評価ファイルの配布許諾は別です。このアプリは評価ファイルを配布しません。</p>
      </div>
      <p>新しく始めると、この端末のOthello保存枠を置き換えます。開始・再開時に確認します。</p>
      <div class="othello-actions"><button id="othello-new" type="button">新しい対局</button><button id="othello-resume" type="button">続きから／再試行</button></div>
    </section><p id="othello-error" role="alert"></p>
    <section class="othello-match" aria-label="Othelloの対局" hidden>
      <div class="othello-summary"><h2 id="othello-turn" tabindex="-1" aria-live="polite"></h2><p id="othello-players"></p><p id="othello-score"></p></div>
      <p id="othello-notice" role="status"></p><p id="othello-guide"></p>
      <div class="othello-board" role="group" aria-label="Othello 8行8列の盤。列AからH、行1から8。合法手に印があります。"></div>
      <div class="othello-actions"><button id="othello-pass" type="button" hidden>合法手がないためパス</button><button id="othello-cancel" type="button" hidden>思考を中断</button><button id="othello-retry-ai" type="button" hidden>AIを再試行</button><button id="othello-save" type="button">今すぐ保存</button></div>
    </section><p id="othello-save-status" role="status"></p></main>`;
  const $ = <T extends HTMLElement>(selector: string) => root.querySelector<T>(selector)!;
  const mode = $<HTMLSelectElement>('#othello-mode');
  const side = $<HTMLSelectElement>('#othello-human-side');
  const strategy = $<HTMLSelectElement>('#othello-strategy');
  const board = $('.othello-board');
  const mainFile = $<HTMLInputElement>('#othello-full-main');
  const endingFile = $<HTMLInputElement>('#othello-full-ending');
  const changedFiles = () =>
    selectFiles({
      main: mainFile.files?.item(0) ?? null,
      ending: endingFile.files?.item(0) ?? null,
    });
  mainFile.addEventListener('change', changedFiles, { signal });
  endingFile.addEventListener('change', changedFiles, { signal });
  $('#othello-cancel-model').addEventListener('click', () => action({ kind: 'cancel' }), {
    signal,
  });
  $('#othello-load-full').addEventListener('click', () => action({ kind: 'loadModel' }), {
    signal,
  });

  const cells = Array.from({ length: 64 }, (_, index) => {
    const cell = document.createElement('button');
    cell.type = 'button';
    cell.dataset.index = String(index);
    cell.className = 'othello-cell';
    cell.addEventListener('click', () => action({ kind: 'play', index }), { signal });
    cell.addEventListener(
      'keydown',
      (event) => {
        const shift = (
          { ArrowRight: 1, ArrowLeft: -1, ArrowDown: 8, ArrowUp: -8 } as Record<string, number>
        )[event.key];
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
  const setup = () => ({
    mode: mode.value as UiMode,
    humanSide: Number(side.value) as Side,
    strategy: strategy.value as UiStrategy,
  });
  mode.addEventListener('change', () => action({ kind: 'setup', ...setup() }), { signal });
  side.addEventListener('change', () => action({ kind: 'setup', ...setup() }), { signal });
  strategy.addEventListener('change', () => action({ kind: 'setup', ...setup() }), { signal });
  $('#othello-new').addEventListener('click', () => action({ kind: 'new', ...setup() }), {
    signal,
  });
  for (const [id, kind] of [
    ['resume', 'resume'],
    ['pass', 'pass'],
    ['save', 'save'],
    ['retry-ai', 'retryAi'],
    ['cancel', 'cancel'],
  ] as const) {
    $(`#othello-${id}`).addEventListener('click', () => action({ kind }), { signal });
  }
  $('h1').focus();
  return {
    clearModelFiles() {
      mainFile.value = '';
      endingFile.value = '';
    },
    failure(message: string) {
      $('#othello-error').textContent = message;
    },
    render(view: UiView) {
      $('main').dataset.aiPhase = view.aiPhase;
      $('main').dataset.modelStatus = view.modelStatus;
      $('main').dataset.strategy = view.strategy;
      $('#othello-full-files').hidden = !view.modelRequired;
      $('#othello-model-status').textContent = view.modelMessage;
      $('#othello-cancel-model').hidden = view.modelStatus !== 'loading' || !view.cancelVisible;
      $<HTMLButtonElement>('#othello-load-full').disabled = view.modelStatus === 'loading';
      $('#othello-error').textContent = view.error;
      $('#othello-save-status').textContent = view.saveMessage;
      $('.othello-match').hidden = !view.hasGame;
      mode.value = view.mode;
      side.value = String(view.humanSide);
      strategy.value = view.strategy;
      $('#othello-side-label').hidden = view.mode !== 'ai';
      $('#othello-strategy-label').hidden = view.mode !== 'ai';
      $('#othello-resume').textContent =
        view.busy && !view.hasGame ? '読み込んでいます…' : '続きから／再試行';
      for (const [id, value] of [
        ['turn', view.title],
        ['players', view.players],
        ['score', view.score],
        ['notice', view.notice],
        ['guide', view.guide],
      ])
        $(`#othello-${id}`).textContent = value!;
      $('#othello-pass').hidden = !view.passVisible;
      $<HTMLButtonElement>('#othello-pass').disabled = view.passDisabled;
      $('#othello-retry-ai').hidden = !view.retryAiVisible;
      $('#othello-cancel').hidden = !view.cancelVisible;
      $<HTMLButtonElement>('#othello-save').disabled = view.saveDisabled;
      for (const value of view.cells) {
        const cell = cells[value.index]!;
        cell.dataset.stone = String(value.stone);
        cell.dataset.legal = String(value.legal);
        cell.setAttribute('aria-label', value.label);
        cell.setAttribute('aria-disabled', String(!value.enabled));
        cell.textContent = value.text;
      }
      if (view.focusTurn) $('#othello-turn').focus();
    },
    dispose() {
      board.replaceChildren();
    },
  };
}
